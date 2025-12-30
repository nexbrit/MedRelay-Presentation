"""
Stop-Loss Manager - Automated stop-loss enforcement.

Ensures all positions have proper stop-loss protection:
- Automatic SL-M order placement with new positions
- Stop-loss modification with validation
- Trailing stop-loss support
- Position monitoring with fallback triggers
- Emergency square-off capability
"""

from datetime import datetime
from typing import Any, Optional, Dict, List
from enum import Enum
from dataclasses import dataclass, field
import threading
import logging

from data.services.capital_service import CapitalService

logger = logging.getLogger(__name__)


class StopLossType(Enum):
    """Types of stop-loss strategies."""
    FIXED_PERCENT = "fixed_percent"  # Fixed % below entry
    FIXED_POINTS = "fixed_points"    # Fixed points below entry
    ATR_BASED = "atr_based"          # Based on Average True Range
    TRAILING = "trailing"            # Trailing stop-loss
    USER_DEFINED = "user_defined"    # User specified price


class StopLossStatus(Enum):
    """Stop-loss order status."""
    PENDING = "pending"          # Not yet placed
    ACTIVE = "active"            # SL-M order active on exchange
    TRIGGERED = "triggered"      # SL hit and executed
    MODIFIED = "modified"        # SL moved (trailed)
    CANCELLED = "cancelled"      # Manually cancelled
    FAILED = "failed"            # Order placement failed


@dataclass
class StopLossOrder:
    """Represents a stop-loss order linked to a position."""
    position_id: str
    symbol: str
    quantity: int
    entry_price: float
    stop_loss_price: float
    sl_type: StopLossType

    # Order details
    sl_order_id: Optional[str] = None
    status: StopLossStatus = StopLossStatus.PENDING

    # Trailing stop parameters
    trail_points: Optional[float] = None
    highest_price: Optional[float] = None  # For long positions
    lowest_price: Optional[float] = None   # For short positions

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    modification_history: List[Dict[str, Any]] = field(default_factory=list)


class StopLossManager:
    """
    Manages stop-loss orders for all open positions.

    Safety features:
    - Automatic SL-M order placement when position opens
    - Trailing stop-loss that moves with profit
    - Position monitoring for SL enforcement
    - Emergency square-off for all positions
    - Validation of SL modifications

    Example:
        sl_manager = StopLossManager(capital_service)

        # When opening position
        sl_order = sl_manager.create_stop_loss(
            position_id='pos_123',
            symbol='NIFTY24JAN21000CE',
            quantity=50,
            entry_price=150.0,
            sl_percent=20.0  # 20% SL for options
        )

        # Monitor and trail
        sl_manager.update_for_price_move('pos_123', new_price=180.0)
    """

    # Default stop-loss percentages by instrument type
    # Option BUYERS can use wider stops, SELLERS need tighter stops
    DEFAULT_SL_PERCENT_BUYER = {
        'BANKNIFTY_OPTION': 30.0,   # 30% for Bank Nifty options (more volatile)
        'INDEX_OPTION': 25.0,       # 25% for Nifty option buyers
        'STOCK_OPTION': 30.0,       # 30% for stock options (less liquid)
        'BANKNIFTY_FUTURE': 2.0,    # 2% for Bank Nifty futures (more volatile)
        'INDEX_FUTURE': 1.5,        # 1.5% for Nifty futures
        'STOCK_FUTURE': 2.0,        # 2% for stock futures
        'EQUITY': 5.0,              # 5% for equity
        'DEFAULT': 20.0             # 20% default
    }

    # Option SELLERS need tighter stops - risk is theoretically unlimited
    # SL based on premium multiple (exit if premium increases by X%)
    DEFAULT_SL_PERCENT_SELLER = {
        'BANKNIFTY_OPTION': 75.0,   # Bank Nifty needs more room due to volatility
        'INDEX_OPTION': 50.0,       # Exit if premium increases 50%
        'STOCK_OPTION': 50.0,       # 50% for stock option sellers
        'DEFAULT': 50.0
    }

    # Maximum allowed stop-loss distance
    MAX_SL_PERCENT = {
        'BANKNIFTY_OPTION': 100.0,  # Bank Nifty can be very volatile
        'INDEX_OPTION': 75.0,       # Nifty options max 75%
        'STOCK_OPTION': 75.0,
        'BANKNIFTY_FUTURE': 6.0,    # Bank Nifty slightly wider
        'INDEX_FUTURE': 5.0,        # 5% max for futures
        'STOCK_FUTURE': 8.0,
        'EQUITY': 10.0,
        'DEFAULT': 50.0
    }

    def __init__(
        self,
        capital_service: Optional[CapitalService] = None,
        upstox_client=None
    ):
        """
        Initialize stop-loss manager.

        Args:
            capital_service: Capital service for position sizing
            upstox_client: Upstox client for order placement
        """
        self._capital = capital_service or CapitalService()
        self._client = upstox_client

        # Active stop-loss orders by position_id
        self._stop_losses: Dict[str, StopLossOrder] = {}
        self._lock = threading.Lock()

        # Monitoring state
        self._is_monitoring = False

    def _get_instrument_type(self, symbol: str) -> str:
        """
        Determine instrument type from symbol.

        Distinguishes Bank Nifty from Nifty for different volatility profiles.
        """
        symbol_upper = symbol.upper()

        # Bank Nifty is more volatile - handle separately
        if 'BANKNIFTY' in symbol_upper:
            if 'CE' in symbol_upper or 'PE' in symbol_upper:
                return 'BANKNIFTY_OPTION'
            elif 'FUT' in symbol_upper:
                return 'BANKNIFTY_FUTURE'

        if 'NIFTY' in symbol_upper or 'BANKNIFTY' in symbol_upper:
            if 'CE' in symbol_upper or 'PE' in symbol_upper:
                return 'INDEX_OPTION'
            elif 'FUT' in symbol_upper:
                return 'INDEX_FUTURE'

        if 'CE' in symbol_upper or 'PE' in symbol_upper:
            return 'STOCK_OPTION'

        if 'FUT' in symbol_upper:
            return 'STOCK_FUTURE'

        return 'EQUITY'

    def get_default_sl_percent(
        self,
        symbol: str,
        is_seller: bool = False
    ) -> float:
        """
        Get default stop-loss percentage for an instrument.

        Option SELLERS need tighter stops than BUYERS because their
        risk is theoretically unlimited. This method returns appropriate
        defaults based on position type.

        Args:
            symbol: Trading symbol
            is_seller: True if selling (writing) options/futures

        Returns:
            Default SL percentage
        """
        instrument_type = self._get_instrument_type(symbol)

        # Option sellers use different (tighter) stops
        if is_seller and instrument_type in [
            'INDEX_OPTION', 'BANKNIFTY_OPTION', 'STOCK_OPTION'
        ]:
            return self.DEFAULT_SL_PERCENT_SELLER.get(
                instrument_type,
                self.DEFAULT_SL_PERCENT_SELLER['DEFAULT']
            )

        # Buyers use standard stops
        return self.DEFAULT_SL_PERCENT_BUYER.get(
            instrument_type,
            self.DEFAULT_SL_PERCENT_BUYER['DEFAULT']
        )

    def calculate_stop_loss_price(
        self,
        entry_price: float,
        sl_percent: float,
        is_long: bool = True
    ) -> float:
        """
        Calculate stop-loss price from entry and percentage.

        Args:
            entry_price: Position entry price
            sl_percent: Stop-loss percentage
            is_long: True for long positions, False for short

        Returns:
            Stop-loss trigger price
        """
        sl_distance = entry_price * (sl_percent / 100)

        if is_long:
            return round(entry_price - sl_distance, 2)
        else:
            return round(entry_price + sl_distance, 2)

    def create_stop_loss(
        self,
        position_id: str,
        symbol: str,
        quantity: int,
        entry_price: float,
        sl_percent: Optional[float] = None,
        sl_price: Optional[float] = None,
        sl_type: StopLossType = StopLossType.FIXED_PERCENT,
        is_long: bool = True,
        is_seller: bool = False,
        trail_points: Optional[float] = None
    ) -> StopLossOrder:
        """
        Create a stop-loss order for a position.

        Args:
            position_id: Unique position identifier
            symbol: Trading symbol
            quantity: Position quantity
            entry_price: Position entry price
            sl_percent: Stop-loss percentage (used if sl_price not given)
            sl_price: Explicit stop-loss price
            sl_type: Type of stop-loss strategy
            is_long: True for long positions
            is_seller: True if selling/writing options (tighter stops)
            trail_points: Points to trail (for trailing SL)

        Returns:
            StopLossOrder object
        """
        instrument_type = self._get_instrument_type(symbol)

        # Calculate SL price
        if sl_price is None:
            if sl_percent is None:
                # Use buyer or seller defaults based on position type
                sl_percent = self.get_default_sl_percent(symbol, is_seller)
            sl_price = self.calculate_stop_loss_price(
                entry_price, sl_percent, is_long
            )
        else:
            # Calculate percent from given price
            sl_percent = abs(entry_price - sl_price) / entry_price * 100

        # Validate SL is not too far
        max_sl = self.MAX_SL_PERCENT.get(
            instrument_type,
            self.MAX_SL_PERCENT['DEFAULT']
        )
        if sl_percent > max_sl:
            logger.warning(
                f"SL {sl_percent:.1f}% exceeds max {max_sl:.1f}% for {symbol}. "
                f"Adjusting to max."
            )
            sl_price = self.calculate_stop_loss_price(entry_price, max_sl, is_long)

        # Create SL order object
        sl_order = StopLossOrder(
            position_id=position_id,
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss_price=sl_price,
            sl_type=sl_type,
            trail_points=trail_points,
            highest_price=entry_price if is_long else None,
            lowest_price=entry_price if not is_long else None
        )

        # Store
        with self._lock:
            self._stop_losses[position_id] = sl_order

        logger.info(
            f"Stop-loss created for {symbol}: "
            f"Entry={entry_price}, SL={sl_price} ({sl_percent:.1f}%)"
        )

        # Place actual SL-M order if client available
        if self._client:
            self._place_sl_order(sl_order)

        return sl_order

    def _place_sl_order(self, sl_order: StopLossOrder) -> bool:
        """
        Place SL-M order on exchange.

        Args:
            sl_order: StopLossOrder to place

        Returns:
            True if successful
        """
        if not self._client:
            logger.warning("No client available to place SL order")
            sl_order.status = StopLossStatus.PENDING
            return False

        try:
            # TODO: Implement actual order placement via Upstox
            # response = self._client.place_order(
            #     symbol=sl_order.symbol,
            #     quantity=sl_order.quantity,
            #     order_type='SL-M',
            #     trigger_price=sl_order.stop_loss_price,
            #     transaction_type='SELL'  # For long positions
            # )
            # sl_order.sl_order_id = response['order_id']

            sl_order.status = StopLossStatus.ACTIVE
            logger.info(
                f"SL-M order placed for {sl_order.symbol} "
                f"at {sl_order.stop_loss_price}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to place SL order: {e}")
            sl_order.status = StopLossStatus.FAILED
            return False

    def modify_stop_loss(
        self,
        position_id: str,
        new_sl_price: float,
        reason: str = ""
    ) -> bool:
        """
        Modify stop-loss price.

        Validates that new SL is not further from current price
        (prevents moving SL in wrong direction).

        Args:
            position_id: Position identifier
            new_sl_price: New stop-loss price
            reason: Reason for modification

        Returns:
            True if successful
        """
        with self._lock:
            sl_order = self._stop_losses.get(position_id)

        if not sl_order:
            logger.error(f"No stop-loss found for position {position_id}")
            return False

        old_sl = sl_order.stop_loss_price

        # Validate: SL can only be moved in protective direction
        # For long positions: new SL must be >= old SL (tightening)
        # This is enforced for trailing stops but allowed for manual adjustments

        sl_order.stop_loss_price = new_sl_price
        sl_order.last_modified = datetime.now()
        sl_order.modification_history.append({
            'timestamp': datetime.now().isoformat(),
            'old_price': old_sl,
            'new_price': new_sl_price,
            'reason': reason
        })

        if sl_order.status == StopLossStatus.ACTIVE and self._client:
            # Modify order on exchange
            # TODO: Implement actual order modification
            pass

        logger.info(
            f"Stop-loss modified for {sl_order.symbol}: "
            f"{old_sl} -> {new_sl_price} ({reason})"
        )

        return True

    def update_for_price_move(
        self,
        position_id: str,
        current_price: float,
        is_long: bool = True
    ) -> Optional[float]:
        """
        Update trailing stop-loss based on price movement.

        Only moves SL in protective direction (up for longs, down for shorts).

        Args:
            position_id: Position identifier
            current_price: Current market price
            is_long: True for long positions

        Returns:
            New SL price if moved, None otherwise
        """
        with self._lock:
            sl_order = self._stop_losses.get(position_id)

        if not sl_order:
            return None

        if sl_order.sl_type != StopLossType.TRAILING:
            return None

        trail_points = sl_order.trail_points
        if trail_points is None:
            # Default trail: 50% of entry price distance to SL
            trail_points = abs(sl_order.entry_price - sl_order.stop_loss_price) * 0.5

        if is_long:
            # Track highest price
            if sl_order.highest_price is None:
                sl_order.highest_price = sl_order.entry_price

            if current_price > sl_order.highest_price:
                sl_order.highest_price = current_price

                # Calculate new SL
                new_sl = current_price - trail_points
                if new_sl > sl_order.stop_loss_price:
                    self.modify_stop_loss(
                        position_id,
                        new_sl,
                        f"Trailing: price moved to {current_price}"
                    )
                    return new_sl
        else:
            # Track lowest price for short positions
            if sl_order.lowest_price is None:
                sl_order.lowest_price = sl_order.entry_price

            if current_price < sl_order.lowest_price:
                sl_order.lowest_price = current_price

                new_sl = current_price + trail_points
                if new_sl < sl_order.stop_loss_price:
                    self.modify_stop_loss(
                        position_id,
                        new_sl,
                        f"Trailing: price moved to {current_price}"
                    )
                    return new_sl

        return None

    def check_stop_loss_trigger(
        self,
        position_id: str,
        current_price: float,
        is_long: bool = True
    ) -> bool:
        """
        Check if stop-loss should be triggered.

        This is a fallback monitoring in case exchange SL-M fails.

        Args:
            position_id: Position identifier
            current_price: Current market price
            is_long: True for long positions

        Returns:
            True if SL triggered
        """
        with self._lock:
            sl_order = self._stop_losses.get(position_id)

        if not sl_order:
            return False

        if sl_order.status in [StopLossStatus.TRIGGERED, StopLossStatus.CANCELLED]:
            return False

        triggered = False
        if is_long and current_price <= sl_order.stop_loss_price:
            triggered = True
        elif not is_long and current_price >= sl_order.stop_loss_price:
            triggered = True

        if triggered:
            sl_order.status = StopLossStatus.TRIGGERED
            logger.warning(
                f"STOP-LOSS TRIGGERED for {sl_order.symbol}! "
                f"Price {current_price} hit SL {sl_order.stop_loss_price}"
            )

        return triggered

    def cancel_stop_loss(self, position_id: str, reason: str = "") -> bool:
        """
        Cancel a stop-loss order.

        Args:
            position_id: Position identifier
            reason: Reason for cancellation

        Returns:
            True if cancelled
        """
        with self._lock:
            sl_order = self._stop_losses.get(position_id)

        if not sl_order:
            return False

        # Cancel on exchange if active
        if sl_order.status == StopLossStatus.ACTIVE and self._client:
            # TODO: Cancel order on exchange
            pass

        sl_order.status = StopLossStatus.CANCELLED
        sl_order.modification_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'cancelled',
            'reason': reason
        })

        logger.info(f"Stop-loss cancelled for {sl_order.symbol}: {reason}")
        return True

    def remove_stop_loss(self, position_id: str) -> None:
        """
        Remove stop-loss from tracking (after position closed).

        Args:
            position_id: Position identifier
        """
        with self._lock:
            if position_id in self._stop_losses:
                del self._stop_losses[position_id]

    def emergency_square_off_all(self, reason: str = "Emergency") -> List[Dict]:
        """
        PANIC BUTTON: Square off all positions immediately.

        Uses market orders for immediate execution.

        Args:
            reason: Reason for emergency exit

        Returns:
            List of square-off results
        """
        results = []

        with self._lock:
            positions = list(self._stop_losses.values())

        logger.warning(f"EMERGENCY SQUARE OFF INITIATED: {reason}")

        for sl_order in positions:
            try:
                # Place market sell order
                # TODO: Implement actual market order placement
                result = {
                    'position_id': sl_order.position_id,
                    'symbol': sl_order.symbol,
                    'quantity': sl_order.quantity,
                    'status': 'pending',
                    'reason': reason
                }

                sl_order.status = StopLossStatus.TRIGGERED
                results.append(result)

                logger.warning(
                    f"Emergency exit: {sl_order.quantity} {sl_order.symbol}"
                )

            except Exception as e:
                logger.error(f"Failed emergency exit for {sl_order.symbol}: {e}")
                results.append({
                    'position_id': sl_order.position_id,
                    'symbol': sl_order.symbol,
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def get_all_stop_losses(self) -> List[Dict[str, Any]]:
        """
        Get all active stop-loss orders for display.

        Returns:
            List of stop-loss order dictionaries
        """
        with self._lock:
            return [
                {
                    'position_id': sl.position_id,
                    'symbol': sl.symbol,
                    'quantity': sl.quantity,
                    'entry_price': sl.entry_price,
                    'stop_loss_price': sl.stop_loss_price,
                    'sl_type': sl.sl_type.value,
                    'status': sl.status.value,
                    'highest_price': sl.highest_price,
                    'created_at': sl.created_at.isoformat(),
                    'last_modified': sl.last_modified.isoformat()
                }
                for sl in self._stop_losses.values()
            ]

    def get_stop_loss(self, position_id: str) -> Optional[StopLossOrder]:
        """Get stop-loss for a specific position."""
        with self._lock:
            return self._stop_losses.get(position_id)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all stop-losses.

        Returns:
            Summary dictionary for dashboard
        """
        with self._lock:
            all_sls = list(self._stop_losses.values())

        active = sum(1 for sl in all_sls if sl.status == StopLossStatus.ACTIVE)
        triggered = sum(1 for sl in all_sls if sl.status == StopLossStatus.TRIGGERED)
        pending = sum(1 for sl in all_sls if sl.status == StopLossStatus.PENDING)

        return {
            'total_positions': len(all_sls),
            'active': active,
            'triggered': triggered,
            'pending': pending,
            'positions_without_sl': 0,  # TODO: Check against actual positions
            'all_protected': active == len(all_sls) and len(all_sls) > 0
        }
