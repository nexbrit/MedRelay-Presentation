"""
OCO (One Cancels Other) Order System
Bidirectional breakout trading - one order execution cancels the other
Professional breakout/breakdown trading
"""

import pandas as pd
from typing import Dict, Optional, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OCOStatus(Enum):
    """OCO order status"""
    PENDING = "PENDING"
    PRIMARY_FILLED = "PRIMARY_FILLED"  # Buy stop filled
    SECONDARY_FILLED = "SECONDARY_FILLED"  # Sell stop filled
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class OCOOrder:
    """
    OCO (One Cancels Other) Order
    Perfect for range breakouts - buy above resistance OR sell below support
    When one executes, the other cancels automatically
    """

    def __init__(
        self,
        instrument: str,
        quantity: int,
        primary_trigger: float,  # Buy stop trigger (above current price)
        secondary_trigger: float,  # Sell stop trigger (below current price)
        primary_stop_loss: Optional[float] = None,
        secondary_stop_loss: Optional[float] = None,
        order_id: Optional[str] = None,
        place_order_callback: Optional[Callable] = None,
        cancel_order_callback: Optional[Callable] = None
    ):
        """
        Initialize OCO order

        Args:
            instrument: Instrument to trade
            quantity: Number of lots
            primary_trigger: Buy stop trigger price (breakout above)
            secondary_trigger: Sell stop trigger price (breakdown below)
            primary_stop_loss: Stop-loss if primary fills (below primary trigger)
            secondary_stop_loss: Stop-loss if secondary fills (above secondary trigger)
            order_id: Unique order ID
            place_order_callback: Function to place orders with broker
            cancel_order_callback: Function to cancel orders with broker
        """
        self.instrument = instrument
        self.quantity = quantity
        self.primary_trigger = primary_trigger
        self.secondary_trigger = secondary_trigger
        self.order_id = order_id or f"OCO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.place_order_callback = place_order_callback
        self.cancel_order_callback = cancel_order_callback

        # Validate
        if primary_trigger <= secondary_trigger:
            raise ValueError(
                f"Invalid OCO: Primary trigger ({primary_trigger}) must be above "
                f"secondary trigger ({secondary_trigger})"
            )

        # Set default stop-losses
        range_size = primary_trigger - secondary_trigger
        self.primary_stop_loss = primary_stop_loss or (primary_trigger - range_size * 0.5)
        self.secondary_stop_loss = secondary_stop_loss or (secondary_trigger + range_size * 0.5)

        # Order tracking
        self.primary_order = None
        self.secondary_order = None
        self.filled_order = None
        self.stop_loss_order = None

        # Status
        self.status = OCOStatus.PENDING
        self.filled_price = None
        self.filled_direction = None
        self.filled_time = None

        logger.info(
            f"OCO order created: {self.order_id} - {instrument}, "
            f"Buy Stop: {primary_trigger}, Sell Stop: {secondary_trigger}, "
            f"Range: {range_size:.2f} points"
        )

    def place_oco_orders(self) -> Dict:
        """
        Place both OCO orders simultaneously

        Returns:
            Order placement details
        """
        if self.place_order_callback is None:
            logger.warning("No order placement callback - simulated OCO")
            self.primary_order = {
                'order_id': f"{self.order_id}_PRIMARY",
                'status': 'PLACED',
                'simulated': True
            }
            self.secondary_order = {
                'order_id': f"{self.order_id}_SECONDARY",
                'status': 'PLACED',
                'simulated': True
            }
        else:
            # Place primary order (buy stop)
            self.primary_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=self.quantity,
                price=self.primary_trigger,
                order_type='STOP',
                transaction_type='BUY'
            )

            # Place secondary order (sell stop)
            self.secondary_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=self.quantity,
                price=self.secondary_trigger,
                order_type='STOP',
                transaction_type='SELL'
            )

        logger.info(
            f"OCO orders placed: Primary={self.primary_order.get('order_id')}, "
            f"Secondary={self.secondary_order.get('order_id')}"
        )

        return {
            'oco_id': self.order_id,
            'primary_order': self.primary_order,
            'secondary_order': self.secondary_order,
            'status': self.status.value
        }

    def on_primary_filled(self, filled_price: float, filled_time: datetime):
        """
        Callback when primary (buy stop) order fills

        Args:
            filled_price: Actual fill price
            filled_time: Fill timestamp
        """
        self.filled_price = filled_price
        self.filled_direction = 'LONG'
        self.filled_time = filled_time
        self.status = OCOStatus.PRIMARY_FILLED

        logger.info(
            f"✅ PRIMARY FILLED (BREAKOUT): {self.instrument} @ {filled_price} "
            f"(Trigger: {self.primary_trigger})"
        )

        # Cancel secondary order
        self._cancel_secondary()

        # Place stop-loss for long position
        self._place_primary_stop_loss()

    def on_secondary_filled(self, filled_price: float, filled_time: datetime):
        """
        Callback when secondary (sell stop) order fills

        Args:
            filled_price: Actual fill price
            filled_time: Fill timestamp
        """
        self.filled_price = filled_price
        self.filled_direction = 'SHORT'
        self.filled_time = filled_time
        self.status = OCOStatus.SECONDARY_FILLED

        logger.info(
            f"⬇️ SECONDARY FILLED (BREAKDOWN): {self.instrument} @ {filled_price} "
            f"(Trigger: {self.secondary_trigger})"
        )

        # Cancel primary order
        self._cancel_primary()

        # Place stop-loss for short position
        self._place_secondary_stop_loss()

    def _cancel_primary(self):
        """Cancel primary order"""
        if self.primary_order:
            logger.info(f"Cancelling primary order: {self.primary_order.get('order_id')}")
            if self.cancel_order_callback:
                self.cancel_order_callback(self.primary_order.get('order_id'))
            self.primary_order['status'] = 'CANCELLED'

    def _cancel_secondary(self):
        """Cancel secondary order"""
        if self.secondary_order:
            logger.info(f"Cancelling secondary order: {self.secondary_order.get('order_id')}")
            if self.cancel_order_callback:
                self.cancel_order_callback(self.secondary_order.get('order_id'))
            self.secondary_order['status'] = 'CANCELLED'

    def _place_primary_stop_loss(self):
        """Place stop-loss for primary (long) position"""
        if self.place_order_callback is None:
            self.stop_loss_order = {
                'order_id': f"{self.order_id}_PRIMARY_SL",
                'status': 'PLACED',
                'simulated': True
            }
        else:
            self.stop_loss_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=self.quantity,
                price=self.primary_stop_loss,
                order_type='STOP',
                transaction_type='SELL'
            )

        logger.info(
            f"Stop-loss placed for LONG position: {self.primary_stop_loss:.2f} "
            f"(SL order: {self.stop_loss_order.get('order_id')})"
        )

    def _place_secondary_stop_loss(self):
        """Place stop-loss for secondary (short) position"""
        if self.place_order_callback is None:
            self.stop_loss_order = {
                'order_id': f"{self.order_id}_SECONDARY_SL",
                'status': 'PLACED',
                'simulated': True
            }
        else:
            self.stop_loss_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=self.quantity,
                price=self.secondary_stop_loss,
                order_type='STOP',
                transaction_type='BUY'
            )

        logger.info(
            f"Stop-loss placed for SHORT position: {self.secondary_stop_loss:.2f} "
            f"(SL order: {self.stop_loss_order.get('order_id')})"
        )

    def cancel_all(self):
        """Cancel all pending orders"""
        self._cancel_primary()
        self._cancel_secondary()
        self.status = OCOStatus.CANCELLED
        logger.info(f"OCO order cancelled: {self.order_id}")

    def get_risk_reward(self) -> Tuple[float, float]:
        """
        Calculate risk-reward for both scenarios

        Returns:
            Tuple of (primary_rr, secondary_rr)
        """
        # Primary (breakout) risk-reward
        primary_risk = abs(self.primary_trigger - self.primary_stop_loss)
        # Assume target at same distance as range size
        range_size = self.primary_trigger - self.secondary_trigger
        primary_reward = range_size
        primary_rr = primary_reward / primary_risk if primary_risk > 0 else 0

        # Secondary (breakdown) risk-reward
        secondary_risk = abs(self.secondary_stop_loss - self.secondary_trigger)
        secondary_reward = range_size
        secondary_rr = secondary_reward / secondary_risk if secondary_risk > 0 else 0

        return primary_rr, secondary_rr

    def get_order_details(self) -> Dict:
        """Get comprehensive OCO order details"""
        primary_rr, secondary_rr = self.get_risk_reward()

        details = {
            'oco_id': self.order_id,
            'instrument': self.instrument,
            'quantity': self.quantity,
            'primary_trigger': self.primary_trigger,
            'secondary_trigger': self.secondary_trigger,
            'primary_stop_loss': self.primary_stop_loss,
            'secondary_stop_loss': self.secondary_stop_loss,
            'range_size': self.primary_trigger - self.secondary_trigger,
            'primary_rr': primary_rr,
            'secondary_rr': secondary_rr,
            'status': self.status.value,
            'filled_price': self.filled_price,
            'filled_direction': self.filled_direction,
            'filled_time': self.filled_time,
            'primary_order_id': self.primary_order.get('order_id') if self.primary_order else None,
            'secondary_order_id': self.secondary_order.get('order_id') if self.secondary_order else None,
            'sl_order_id': self.stop_loss_order.get('order_id') if self.stop_loss_order else None
        }

        return details

    def __repr__(self):
        """String representation"""
        return (
            f"OCOOrder({self.instrument}, "
            f"Buy Stop: {self.primary_trigger}, Sell Stop: {self.secondary_trigger}, "
            f"Range: {self.primary_trigger - self.secondary_trigger:.2f}, "
            f"Status: {self.status.value})"
        )


def create_oco_from_range(
    instrument: str,
    quantity: int,
    support: float,
    resistance: float,
    stop_loss_ratio: float = 0.5  # SL at 50% of range
) -> OCOOrder:
    """
    Create OCO order from support/resistance levels

    Args:
        instrument: Instrument name
        quantity: Position size
        support: Support level (secondary trigger will be below this)
        resistance: Resistance level (primary trigger will be above this)
        stop_loss_ratio: Stop-loss as ratio of range size

    Returns:
        OCOOrder instance
    """
    range_size = resistance - support

    # Place triggers slightly beyond levels to confirm breakout
    buffer = range_size * 0.02  # 2% buffer
    primary_trigger = resistance + buffer
    secondary_trigger = support - buffer

    # Calculate stop-losses
    primary_stop_loss = primary_trigger - (range_size * stop_loss_ratio)
    secondary_stop_loss = secondary_trigger + (range_size * stop_loss_ratio)

    return OCOOrder(
        instrument=instrument,
        quantity=quantity,
        primary_trigger=primary_trigger,
        secondary_trigger=secondary_trigger,
        primary_stop_loss=primary_stop_loss,
        secondary_stop_loss=secondary_stop_loss
    )


def create_oco_from_current_price(
    instrument: str,
    quantity: int,
    current_price: float,
    breakout_distance: float,  # Points above/below for triggers
    stop_loss_distance: float  # Points for stop-loss
) -> OCOOrder:
    """
    Create OCO order around current price

    Args:
        instrument: Instrument name
        quantity: Position size
        current_price: Current market price
        breakout_distance: Distance for breakout triggers
        stop_loss_distance: Distance for stop-losses

    Returns:
        OCOOrder instance
    """
    primary_trigger = current_price + breakout_distance
    secondary_trigger = current_price - breakout_distance

    primary_stop_loss = primary_trigger - stop_loss_distance
    secondary_stop_loss = secondary_trigger + stop_loss_distance

    return OCOOrder(
        instrument=instrument,
        quantity=quantity,
        primary_trigger=primary_trigger,
        secondary_trigger=secondary_trigger,
        primary_stop_loss=primary_stop_loss,
        secondary_stop_loss=secondary_stop_loss
    )
