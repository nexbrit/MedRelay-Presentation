"""
Order Manager - Confirmation, validation, and execution control.

Provides critical safety mechanisms for order execution:
- Order confirmation flow with preview
- Margin and position limit validation
- Portfolio heat impact calculation
- High-value order warnings
- Order execution logging and audit trail
"""

from datetime import datetime
from typing import Any, Optional, Dict, List
from enum import Enum
from dataclasses import dataclass
import logging

from data.services.capital_service import CapitalService
from data.services.order_service import OrderService
from data.services.market_data_service import ExpiryDayManager
from data.persistence.state_manager import StateManager

logger = logging.getLogger(__name__)


class OrderValidationStatus(Enum):
    """Order validation result status."""
    VALID = "valid"
    WARNING = "warning"
    BLOCKED = "blocked"


class OrderBlockReason(Enum):
    """Reasons for blocking an order."""
    INSUFFICIENT_MARGIN = "insufficient_margin"
    POSITION_SIZE_EXCEEDED = "position_size_exceeded"
    PORTFOLIO_HEAT_EXCEEDED = "portfolio_heat_exceeded"
    DAILY_ORDER_LIMIT = "daily_order_limit"
    EXPIRY_DAY_RESTRICTION = "expiry_day_restriction"
    TRADING_HOURS_VIOLATION = "trading_hours_violation"
    CONSECUTIVE_LOSS_LIMIT = "consecutive_loss_limit"
    RULE_VIOLATION = "rule_violation"


@dataclass
class OrderPreview:
    """Order preview with all calculated values."""
    symbol: str
    quantity: int
    order_type: str
    transaction_type: str  # BUY/SELL
    price: float
    product_type: str  # MIS/NRML/CNC

    # Calculated values
    order_value: float
    estimated_margin: float
    position_size_percent: float
    portfolio_heat_before: float
    portfolio_heat_after: float
    max_loss: float
    risk_reward_ratio: Optional[float]

    # Validation
    validation_status: OrderValidationStatus
    warnings: List[str]
    block_reasons: List[OrderBlockReason]

    # Metadata
    created_at: datetime
    instrument_type: str


class OrderManager:
    """
    Central order management with confirmation and validation.

    Safety features:
    - Pre-execution order preview with margin/risk calculation
    - Position size limit enforcement
    - Portfolio heat limit enforcement
    - High-value order warnings
    - Expiry day restrictions
    - Complete audit logging

    Example:
        manager = OrderManager(capital_service, order_service)

        # Create order preview
        preview = manager.create_order_preview(
            symbol='NIFTY24JAN21000CE',
            quantity=50,
            order_type='LIMIT',
            transaction_type='BUY',
            price=150.0
        )

        if preview.validation_status == OrderValidationStatus.VALID:
            # User confirms
            result = manager.execute_confirmed_order(preview)
    """

    # Position size warnings
    HIGH_VALUE_THRESHOLD_PERCENT = 5.0  # Warn if > 5% of capital
    VERY_HIGH_VALUE_THRESHOLD_PERCENT = 8.0  # Extra warning if > 8%

    # Daily limits
    MAX_ORDERS_PER_DAY = 20  # Default daily order limit
    MAX_CONSECUTIVE_LOSSES = 4  # Block after 4 consecutive losses (oz-fno-wizard recommendation)

    def __init__(
        self,
        capital_service: Optional[CapitalService] = None,
        order_service: Optional[OrderService] = None,
        state_manager: Optional[StateManager] = None
    ):
        """
        Initialize order manager.

        Args:
            capital_service: Capital service for position sizing
            order_service: Order service for execution and logging
            state_manager: State manager for persistence
        """
        self._capital = capital_service or CapitalService()
        self._orders = order_service or OrderService(None)
        self._state = state_manager or StateManager()

        # Trading session tracking
        self._today_order_count = 0
        self._consecutive_losses = 0
        self._last_order_date = None

    def _reset_daily_counters_if_needed(self) -> None:
        """Reset daily counters if it's a new day."""
        today = datetime.now().date()
        if self._last_order_date != today:
            self._today_order_count = 0
            self._last_order_date = today

    def _get_instrument_type(self, symbol: str) -> str:
        """
        Determine instrument type from symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Instrument type (INDEX_OPTION, STOCK_OPTION, etc.)
        """
        symbol_upper = symbol.upper()

        # Check for index options/futures
        if 'NIFTY' in symbol_upper or 'BANKNIFTY' in symbol_upper:
            if 'CE' in symbol_upper or 'PE' in symbol_upper:
                return 'INDEX_OPTION'
            elif 'FUT' in symbol_upper:
                return 'INDEX_FUTURE'

        # Check for other options
        if 'CE' in symbol_upper or 'PE' in symbol_upper:
            return 'STOCK_OPTION'

        # Check for futures
        if 'FUT' in symbol_upper:
            return 'STOCK_FUTURE'

        return 'EQUITY'

    def _calculate_estimated_margin(
        self,
        symbol: str,
        quantity: int,
        price: float,
        product_type: str
    ) -> float:
        """
        Estimate margin requirement for an order.

        This is a simplified estimation. For accurate margins,
        use Upstox margin API.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Order price
            product_type: Product type (MIS/NRML/CNC)

        Returns:
            Estimated margin requirement
        """
        order_value = quantity * price

        # MIS orders have reduced margin (typically 20-40%)
        if product_type == 'MIS':
            margin_percent = 0.25  # 25% margin for intraday
        else:
            margin_percent = 1.0  # 100% for delivery

        # Options require lower margin (premium only for buyers)
        instrument_type = self._get_instrument_type(symbol)
        if instrument_type in ['INDEX_OPTION', 'STOCK_OPTION']:
            # Option buyers pay full premium
            return order_value
        elif instrument_type in ['INDEX_FUTURE', 'STOCK_FUTURE']:
            # Futures require SPAN margin (estimate 15%)
            return order_value * 0.15

        return order_value * margin_percent

    def _calculate_max_loss(
        self,
        symbol: str,
        quantity: int,
        price: float,
        transaction_type: str,
        stop_loss: Optional[float] = None
    ) -> float:
        """
        Calculate maximum potential loss for an order.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Entry price
            transaction_type: BUY or SELL
            stop_loss: Stop loss price if defined

        Returns:
            Maximum potential loss
        """
        instrument_type = self._get_instrument_type(symbol)

        # For option buyers, max loss is premium paid
        if instrument_type in ['INDEX_OPTION', 'STOCK_OPTION']:
            if transaction_type == 'BUY':
                return quantity * price  # Max loss = premium
            else:
                # Option sellers have theoretically unlimited risk
                # Use 3x premium as estimate
                return quantity * price * 3

        # For futures and equity, use stop loss or assume 5%
        if stop_loss:
            if transaction_type == 'BUY':
                loss_per_unit = price - stop_loss
            else:
                loss_per_unit = stop_loss - price
            return abs(loss_per_unit) * quantity

        # Default: assume 5% move against position
        return quantity * price * 0.05

    def _get_current_portfolio_heat(self) -> float:
        """
        Get current portfolio heat percentage.

        Returns:
            Current portfolio heat as percentage
        """
        capital = self._capital.get_current_capital()
        if capital <= 0:
            return 0.0

        # Get all open positions and calculate total risk
        # For now, return a placeholder
        # TODO: Integrate with portfolio service for actual calculation
        return 2.0  # Placeholder

    def create_order_preview(
        self,
        symbol: str,
        quantity: int,
        order_type: str,
        transaction_type: str,
        price: float,
        product_type: str = 'NRML',
        stop_loss: Optional[float] = None
    ) -> OrderPreview:
        """
        Create an order preview with validation.

        This method calculates all risk metrics and validates
        the order against trading rules WITHOUT executing.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            order_type: LIMIT, MARKET, SL-M, SL
            transaction_type: BUY or SELL
            price: Order price
            product_type: MIS, NRML, or CNC
            stop_loss: Stop loss price for risk calculation

        Returns:
            OrderPreview with all calculated values and validation
        """
        self._reset_daily_counters_if_needed()

        warnings: List[str] = []
        block_reasons: List[OrderBlockReason] = []

        instrument_type = self._get_instrument_type(symbol)
        order_value = quantity * price

        # Get capital information
        capital = self._capital.get_current_capital()
        position_sizing = self._capital.get_position_sizing_capital(
            instrument_type=instrument_type
        )

        # Calculate metrics
        estimated_margin = self._calculate_estimated_margin(
            symbol, quantity, price, product_type
        )
        position_size_percent = (order_value / capital * 100) if capital > 0 else 100
        max_position_percent = position_sizing['max_position_percent']

        portfolio_heat_before = self._get_current_portfolio_heat()
        max_loss = self._calculate_max_loss(
            symbol, quantity, price, transaction_type, stop_loss
        )
        heat_impact = (max_loss / capital * 100) if capital > 0 else 100
        portfolio_heat_after = portfolio_heat_before + heat_impact

        # Validation checks

        # 1. Position size limit
        if position_size_percent > max_position_percent:
            block_reasons.append(OrderBlockReason.POSITION_SIZE_EXCEEDED)
            warnings.append(
                f"Position size ({position_size_percent:.1f}%) exceeds "
                f"limit ({max_position_percent:.1f}%) for {instrument_type}"
            )

        # 2. Portfolio heat limit (6%)
        if portfolio_heat_after > 6.0:
            block_reasons.append(OrderBlockReason.PORTFOLIO_HEAT_EXCEEDED)
            warnings.append(
                f"Portfolio heat would exceed 6% limit "
                f"(current: {portfolio_heat_before:.1f}%, "
                f"after: {portfolio_heat_after:.1f}%)"
            )

        # 3. Margin check
        available_capital = self._capital.get_available_capital()
        if estimated_margin > available_capital:
            block_reasons.append(OrderBlockReason.INSUFFICIENT_MARGIN)
            warnings.append(
                f"Insufficient margin: need ₹{estimated_margin:,.0f}, "
                f"available ₹{available_capital:,.0f}"
            )

        # 4. Daily order limit
        if self._today_order_count >= self.MAX_ORDERS_PER_DAY:
            block_reasons.append(OrderBlockReason.DAILY_ORDER_LIMIT)
            warnings.append(
                f"Daily order limit ({self.MAX_ORDERS_PER_DAY}) reached"
            )

        # 5. Consecutive loss limit
        if self._consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            block_reasons.append(OrderBlockReason.CONSECUTIVE_LOSS_LIMIT)
            warnings.append(
                f"Trading paused after {self._consecutive_losses} "
                f"consecutive losses (cooldown required)"
            )

        # 6. Expiry day restrictions
        if ExpiryDayManager.is_last_hour_of_expiry():
            restrictions = ExpiryDayManager.get_expiry_day_restrictions()
            if position_size_percent > 2.0:  # Stricter on expiry day
                warnings.append(
                    "Expiry day last hour: Consider reduced position size"
                )
            warnings.append(restrictions['warning'])

        # 7. High value warnings (not blocking)
        if position_size_percent > self.VERY_HIGH_VALUE_THRESHOLD_PERCENT:
            warnings.append(
                f"VERY HIGH VALUE ORDER: {position_size_percent:.1f}% of capital. "
                f"Consider reducing position size."
            )
        elif position_size_percent > self.HIGH_VALUE_THRESHOLD_PERCENT:
            warnings.append(
                f"High value order: {position_size_percent:.1f}% of capital"
            )

        # Determine overall validation status
        if block_reasons:
            validation_status = OrderValidationStatus.BLOCKED
        elif warnings:
            validation_status = OrderValidationStatus.WARNING
        else:
            validation_status = OrderValidationStatus.VALID

        # Calculate risk/reward ratio if stop loss provided
        risk_reward_ratio = None
        if stop_loss and transaction_type == 'BUY':
            risk = price - stop_loss
            if risk > 0:
                # Assume 2:1 target
                risk_reward_ratio = 2.0

        return OrderPreview(
            symbol=symbol,
            quantity=quantity,
            order_type=order_type,
            transaction_type=transaction_type,
            price=price,
            product_type=product_type,
            order_value=order_value,
            estimated_margin=estimated_margin,
            position_size_percent=position_size_percent,
            portfolio_heat_before=portfolio_heat_before,
            portfolio_heat_after=portfolio_heat_after,
            max_loss=max_loss,
            risk_reward_ratio=risk_reward_ratio,
            validation_status=validation_status,
            warnings=warnings,
            block_reasons=block_reasons,
            created_at=datetime.now(),
            instrument_type=instrument_type
        )

    def execute_confirmed_order(
        self,
        preview: OrderPreview,
        user_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Execute an order that has been confirmed by the user.

        Args:
            preview: The order preview that was shown to user
            user_confirmed: Whether user explicitly confirmed

        Returns:
            Dictionary with execution result
        """
        # Safety check: must be confirmed
        if not user_confirmed:
            return {
                'success': False,
                'error': 'Order not confirmed by user',
                'order_id': None
            }

        # Safety check: cannot execute blocked orders
        if preview.validation_status == OrderValidationStatus.BLOCKED:
            return {
                'success': False,
                'error': f"Order blocked: {', '.join(str(r.value) for r in preview.block_reasons)}",
                'order_id': None
            }

        # Log the order attempt
        self._orders.log_order_action(
            order_id=f"preview_{preview.created_at.timestamp()}",
            action='CONFIRMED',
            details={
                'symbol': preview.symbol,
                'quantity': preview.quantity,
                'price': preview.price,
                'order_value': preview.order_value,
                'warnings_acknowledged': len(preview.warnings),
                'user_confirmed': True
            }
        )

        # Update daily counter
        self._today_order_count += 1

        # Here we would actually place the order via Upstox
        # For now, return a success placeholder
        # TODO: Integrate with actual order placement

        logger.info(
            f"Order confirmed: {preview.transaction_type} "
            f"{preview.quantity} {preview.symbol} @ {preview.price}"
        )

        return {
            'success': True,
            'order_id': f"confirmed_{datetime.now().timestamp()}",
            'preview': preview,
            'message': 'Order confirmed and ready for execution'
        }

    def record_trade_result(
        self,
        order_id: str,
        is_profit: bool,
        pnl_amount: float
    ) -> None:
        """
        Record the result of a closed trade.

        Updates consecutive loss counter for circuit breaker.

        Args:
            order_id: The order/trade ID
            is_profit: Whether trade was profitable
            pnl_amount: P&L amount (positive for profit, negative for loss)
        """
        if is_profit:
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1

        # Log to capital service
        self._capital.record_trade_pnl(
            pnl=pnl_amount,
            reference_id=order_id
        )

        # Log the result
        self._orders.log_order_action(
            order_id=order_id,
            action='TRADE_CLOSED',
            details={
                'is_profit': is_profit,
                'pnl_amount': pnl_amount,
                'consecutive_losses': self._consecutive_losses
            }
        )

    def get_trading_status(self) -> Dict[str, Any]:
        """
        Get current trading status for UI display.

        Returns:
            Dictionary with trading status
        """
        self._reset_daily_counters_if_needed()

        return {
            'orders_today': self._today_order_count,
            'max_orders_per_day': self.MAX_ORDERS_PER_DAY,
            'orders_remaining': self.MAX_ORDERS_PER_DAY - self._today_order_count,
            'consecutive_losses': self._consecutive_losses,
            'max_consecutive_losses': self.MAX_CONSECUTIVE_LOSSES,
            'is_blocked': self._consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES,
            'expiry_day': ExpiryDayManager.is_expiry_day(),
            'last_hour_expiry': ExpiryDayManager.is_last_hour_of_expiry(),
            'expiry_restrictions': (
                ExpiryDayManager.get_expiry_day_restrictions()
                if ExpiryDayManager.is_expiry_day() else None
            )
        }

    def reset_consecutive_losses(self, reason: str = "Manual reset") -> None:
        """
        Manually reset the consecutive loss counter.

        Should only be called after cooling off period or explicit user action.

        Args:
            reason: Reason for reset (for audit trail)
        """
        old_count = self._consecutive_losses
        self._consecutive_losses = 0

        logger.info(
            f"Consecutive losses reset from {old_count} to 0. "
            f"Reason: {reason}"
        )

        self._orders.log_order_action(
            order_id='system',
            action='LOSS_COUNTER_RESET',
            details={
                'previous_count': old_count,
                'reason': reason
            }
        )

    def format_preview_for_display(
        self,
        preview: OrderPreview
    ) -> Dict[str, Any]:
        """
        Format order preview for UI display.

        Args:
            preview: OrderPreview object

        Returns:
            Dictionary formatted for UI
        """
        return {
            'order_details': {
                'symbol': preview.symbol,
                'action': preview.transaction_type,
                'quantity': preview.quantity,
                'price': f"₹{preview.price:,.2f}",
                'order_type': preview.order_type,
                'product': preview.product_type
            },
            'risk_metrics': {
                'order_value': f"₹{preview.order_value:,.0f}",
                'estimated_margin': f"₹{preview.estimated_margin:,.0f}",
                'position_size': f"{preview.position_size_percent:.1f}%",
                'max_loss': f"₹{preview.max_loss:,.0f}",
                'portfolio_heat_before': f"{preview.portfolio_heat_before:.1f}%",
                'portfolio_heat_after': f"{preview.portfolio_heat_after:.1f}%"
            },
            'validation': {
                'status': preview.validation_status.value,
                'is_valid': preview.validation_status == OrderValidationStatus.VALID,
                'has_warnings': len(preview.warnings) > 0,
                'is_blocked': preview.validation_status == OrderValidationStatus.BLOCKED,
                'warnings': preview.warnings,
                'block_reasons': [r.value for r in preview.block_reasons]
            },
            'instrument_type': preview.instrument_type,
            'created_at': preview.created_at.isoformat()
        }
