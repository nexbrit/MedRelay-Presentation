"""
Bracket Order System
One-click risk-defined trading with entry, target, and stop-loss
"""

import pandas as pd
from typing import Dict, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class BracketOrder:
    """
    Bracket Order: Entry + Target + Stop-Loss in one order
    Professional risk-defined trading
    """

    def __init__(
        self,
        instrument: str,
        quantity: int,
        entry_price: float,
        target_price: float,
        stop_loss_price: float,
        order_id: Optional[str] = None,
        place_order_callback: Optional[Callable] = None
    ):
        """
        Initialize bracket order

        Args:
            instrument: Instrument to trade
            quantity: Number of lots
            entry_price: Entry price (limit order)
            target_price: Target price (limit order)
            stop_loss_price: Stop loss price (stop order)
            order_id: Unique order ID
            place_order_callback: Function to place orders with broker
        """
        self.instrument = instrument
        self.quantity = quantity
        self.entry_price = entry_price
        self.target_price = target_price
        self.stop_loss_price = stop_loss_price
        self.order_id = order_id or f"BRACKET_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.place_order_callback = place_order_callback

        # Order tracking
        self.entry_order = None
        self.target_order = None
        self.stop_loss_order = None

        # Status
        self.status = OrderStatus.PENDING
        self.entry_filled_price = None
        self.exit_filled_price = None
        self.exit_reason = None

        # Validate
        self._validate_prices()

        # Calculate risk-reward
        self.risk_reward_ratio = self._calculate_risk_reward()

        logger.info(
            f"Bracket order created: {self.order_id} - "
            f"{instrument} @ {entry_price}, Target: {target_price}, SL: {stop_loss_price}, "
            f"R:R = 1:{self.risk_reward_ratio:.2f}"
        )

    def _validate_prices(self):
        """Validate price levels"""
        # Long position
        if self.target_price > self.entry_price:
            if self.stop_loss_price >= self.entry_price:
                raise ValueError(
                    f"Invalid LONG bracket: SL ({self.stop_loss_price}) must be below entry ({self.entry_price})"
                )
            self.direction = "LONG"

        # Short position
        elif self.target_price < self.entry_price:
            if self.stop_loss_price <= self.entry_price:
                raise ValueError(
                    f"Invalid SHORT bracket: SL ({self.stop_loss_price}) must be above entry ({self.entry_price})"
                )
            self.direction = "SHORT"

        else:
            raise ValueError("Target price cannot equal entry price")

    def _calculate_risk_reward(self) -> float:
        """Calculate risk-reward ratio"""
        risk = abs(self.entry_price - self.stop_loss_price)
        reward = abs(self.target_price - self.entry_price)

        return reward / risk if risk > 0 else 0

    def place_entry_order(self) -> Dict:
        """
        Place entry order

        Returns:
            Order details
        """
        if self.place_order_callback is None:
            logger.warning("No order placement callback provided - simulated order")
            self.entry_order = {
                'order_id': f"{self.order_id}_ENTRY",
                'status': OrderStatus.PLACED,
                'simulated': True
            }
        else:
            # Place actual order via broker API
            self.entry_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=self.quantity,
                price=self.entry_price,
                order_type='LIMIT',
                transaction_type='BUY' if self.direction == 'LONG' else 'SELL'
            )

        self.status = OrderStatus.PLACED

        logger.info(f"Entry order placed: {self.entry_order.get('order_id')}")
        return self.entry_order

    def on_entry_filled(self, filled_price: float, filled_time: datetime):
        """
        Callback when entry order is filled

        Args:
            filled_price: Actual fill price
            filled_time: Fill timestamp
        """
        self.entry_filled_price = filled_price
        self.status = OrderStatus.FILLED

        logger.info(
            f"Entry filled: {self.instrument} @ {filled_price} "
            f"(Expected: {self.entry_price}, Slippage: {abs(filled_price - self.entry_price):.2f})"
        )

        # Place target and stop-loss orders (OCO - One Cancels Other)
        self._place_exit_orders()

    def _place_exit_orders(self):
        """Place target and stop-loss orders (OCO)"""
        if self.place_order_callback is None:
            # Simulated
            self.target_order = {
                'order_id': f"{self.order_id}_TARGET",
                'status': OrderStatus.PLACED,
                'simulated': True
            }
            self.stop_loss_order = {
                'order_id': f"{self.order_id}_SL",
                'status': OrderStatus.PLACED,
                'simulated': True
            }
        else:
            # Place target order (limit)
            self.target_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=self.quantity,
                price=self.target_price,
                order_type='LIMIT',
                transaction_type='SELL' if self.direction == 'LONG' else 'BUY'
            )

            # Place stop-loss order (stop)
            self.stop_loss_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=self.quantity,
                price=self.stop_loss_price,
                order_type='STOP',
                transaction_type='SELL' if self.direction == 'LONG' else 'BUY'
            )

        logger.info(
            f"Exit orders placed: Target={self.target_order.get('order_id')}, "
            f"SL={self.stop_loss_order.get('order_id')}"
        )

    def on_target_hit(self, filled_price: float, filled_time: datetime):
        """
        Callback when target is hit

        Args:
            filled_price: Actual fill price
            filled_time: Fill timestamp
        """
        self.exit_filled_price = filled_price
        self.exit_reason = 'TARGET'

        # Cancel stop-loss order
        self._cancel_stop_loss()

        # Calculate P&L
        pnl = self._calculate_pnl()

        logger.info(
            f"✅ TARGET HIT: {self.instrument} @ {filled_price}, "
            f"P&L: ₹{pnl:,.2f}"
        )

    def on_stop_loss_hit(self, filled_price: float, filled_time: datetime):
        """
        Callback when stop-loss is hit

        Args:
            filled_price: Actual fill price
            filled_time: Fill timestamp
        """
        self.exit_filled_price = filled_price
        self.exit_reason = 'STOP_LOSS'

        # Cancel target order
        self._cancel_target()

        # Calculate P&L
        pnl = self._calculate_pnl()

        logger.warning(
            f"❌ STOP LOSS HIT: {self.instrument} @ {filled_price}, "
            f"P&L: ₹{pnl:,.2f}"
        )

    def _cancel_target(self):
        """Cancel target order"""
        if self.target_order:
            logger.info(f"Cancelling target order: {self.target_order.get('order_id')}")
            # Would call broker API to cancel
            self.target_order['status'] = OrderStatus.CANCELLED

    def _cancel_stop_loss(self):
        """Cancel stop-loss order"""
        if self.stop_loss_order:
            logger.info(f"Cancelling stop-loss order: {self.stop_loss_order.get('order_id')}")
            # Would call broker API to cancel
            self.stop_loss_order['status'] = OrderStatus.CANCELLED

    def _calculate_pnl(self) -> float:
        """Calculate P&L"""
        if self.entry_filled_price is None or self.exit_filled_price is None:
            return 0.0

        if self.direction == 'LONG':
            pnl = (self.exit_filled_price - self.entry_filled_price) * self.quantity
        else:  # SHORT
            pnl = (self.entry_filled_price - self.exit_filled_price) * self.quantity

        return pnl

    def modify_target(self, new_target_price: float):
        """
        Modify target price (trailing profit)

        Args:
            new_target_price: New target price
        """
        if self.status != OrderStatus.FILLED:
            logger.warning("Cannot modify target - position not open")
            return

        old_target = self.target_price
        self.target_price = new_target_price

        # Recalculate R:R
        self.risk_reward_ratio = self._calculate_risk_reward()

        logger.info(
            f"Target modified: {old_target} → {new_target_price}, "
            f"New R:R = 1:{self.risk_reward_ratio:.2f}"
        )

        # Would modify order with broker
        if self.place_order_callback is not None:
            # Cancel old target and place new
            self._cancel_target()
            # Place new target order
            # self.target_order = self.place_order_callback(...)

    def modify_stop_loss(self, new_sl_price: float):
        """
        Modify stop-loss price (trailing stop)

        Args:
            new_sl_price: New stop-loss price
        """
        if self.status != OrderStatus.FILLED:
            logger.warning("Cannot modify SL - position not open")
            return

        # Validate: SL can only move in favorable direction
        if self.direction == 'LONG' and new_sl_price <= self.stop_loss_price:
            logger.warning(f"LONG position: New SL must be higher than current ({self.stop_loss_price})")
            return
        elif self.direction == 'SHORT' and new_sl_price >= self.stop_loss_price:
            logger.warning(f"SHORT position: New SL must be lower than current ({self.stop_loss_price})")
            return

        old_sl = self.stop_loss_price
        self.stop_loss_price = new_sl_price

        # Recalculate R:R
        self.risk_reward_ratio = self._calculate_risk_reward()

        logger.info(
            f"Stop-loss modified: {old_sl} → {new_sl_price}, "
            f"New R:R = 1:{self.risk_reward_ratio:.2f}"
        )

        # Would modify order with broker
        if self.place_order_callback is not None:
            # Cancel old SL and place new
            self._cancel_stop_loss()
            # Place new SL order
            # self.stop_loss_order = self.place_order_callback(...)

    def cancel_all(self):
        """Cancel all orders (manual exit)"""
        self._cancel_target()
        self._cancel_stop_loss()

        self.status = OrderStatus.CANCELLED

        logger.info(f"Bracket order cancelled: {self.order_id}")

    def get_order_details(self) -> Dict:
        """Get comprehensive order details"""
        details = {
            'order_id': self.order_id,
            'instrument': self.instrument,
            'quantity': self.quantity,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'target_price': self.target_price,
            'stop_loss_price': self.stop_loss_price,
            'risk_reward_ratio': self.risk_reward_ratio,
            'status': self.status.value,
            'entry_filled_price': self.entry_filled_price,
            'exit_filled_price': self.exit_filled_price,
            'exit_reason': self.exit_reason,
            'pnl': self._calculate_pnl() if self.exit_filled_price else None,
            'entry_order_id': self.entry_order.get('order_id') if self.entry_order else None,
            'target_order_id': self.target_order.get('order_id') if self.target_order else None,
            'sl_order_id': self.stop_loss_order.get('order_id') if self.stop_loss_order else None
        }

        return details

    def __repr__(self):
        """String representation"""
        return (
            f"BracketOrder({self.instrument}, "
            f"{self.direction}, "
            f"Qty: {self.quantity}, "
            f"Entry: {self.entry_price}, "
            f"Target: {self.target_price}, "
            f"SL: {self.stop_loss_price}, "
            f"R:R 1:{self.risk_reward_ratio:.2f}, "
            f"Status: {self.status.value})"
        )


def create_bracket_order_from_signal(
    signal: Dict,
    instrument: str,
    quantity: int,
    atr: float,
    risk_reward_ratio: float = 2.0
) -> BracketOrder:
    """
    Create bracket order from trading signal

    Args:
        signal: Signal dictionary with entry price and direction
        instrument: Instrument name
        quantity: Position size
        atr: Current ATR for stop-loss calculation
        risk_reward_ratio: Desired risk-reward ratio

    Returns:
        BracketOrder instance
    """
    entry = signal['entry_price']
    direction = signal['direction']  # 'LONG' or 'SHORT'

    # Calculate stop-loss based on ATR
    if direction == 'LONG':
        stop_loss = entry - (2 * atr)  # 2x ATR below entry
        target = entry + (2 * atr * risk_reward_ratio)  # R:R times risk
    else:  # SHORT
        stop_loss = entry + (2 * atr)
        target = entry - (2 * atr * risk_reward_ratio)

    return BracketOrder(
        instrument=instrument,
        quantity=quantity,
        entry_price=entry,
        target_price=target,
        stop_loss_price=stop_loss
    )
