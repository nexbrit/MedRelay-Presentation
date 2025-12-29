"""
Iceberg Order System
Hide large orders by showing only small visible portions
Professional stealth trading for institutional-size positions
"""

import pandas as pd
from typing import Dict, Optional, Callable, List
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IcebergStatus(Enum):
    """Iceberg order status"""
    ACTIVE = "ACTIVE"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class IcebergOrder:
    """
    Iceberg Order: Hide large orders by showing small visible portions

    Example: Want to buy 100 lots but show only 5 lots at a time
    Market only sees 5 lots, once filled, next 5 lots appear

    Benefits:
    - Prevents market impact from large orders
    - Avoids signaling intentions to other traders
    - Gets better average fill price
    """

    def __init__(
        self,
        instrument: str,
        total_quantity: int,  # Total size (e.g., 100 lots)
        visible_quantity: int,  # Visible size (e.g., 5 lots)
        price: float,
        order_type: str = 'LIMIT',  # 'LIMIT' or 'MARKET'
        transaction_type: str = 'BUY',  # 'BUY' or 'SELL'
        order_id: Optional[str] = None,
        place_order_callback: Optional[Callable] = None,
        cancel_order_callback: Optional[Callable] = None
    ):
        """
        Initialize iceberg order

        Args:
            instrument: Instrument to trade
            total_quantity: Total order size
            visible_quantity: Visible portion size
            price: Limit price (ignored for market orders)
            order_type: 'LIMIT' or 'MARKET'
            transaction_type: 'BUY' or 'SELL'
            order_id: Unique order ID
            place_order_callback: Function to place orders with broker
            cancel_order_callback: Function to cancel orders with broker
        """
        self.instrument = instrument
        self.total_quantity = total_quantity
        self.visible_quantity = visible_quantity
        self.price = price
        self.order_type = order_type
        self.transaction_type = transaction_type
        self.order_id = order_id or f"ICEBERG_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.place_order_callback = place_order_callback
        self.cancel_order_callback = cancel_order_callback

        # Validate
        if visible_quantity >= total_quantity:
            raise ValueError(
                f"Visible quantity ({visible_quantity}) must be less than "
                f"total quantity ({total_quantity})"
            )

        # Calculate slices
        self.num_slices = (total_quantity + visible_quantity - 1) // visible_quantity
        self.slices = self._create_slices()

        # Tracking
        self.current_slice_index = 0
        self.current_order = None
        self.filled_quantity = 0
        self.filled_slices = []
        self.status = IcebergStatus.ACTIVE
        self.average_fill_price = 0.0
        self.total_fill_value = 0.0

        logger.info(
            f"Iceberg order created: {self.order_id} - {instrument} {transaction_type} "
            f"{total_quantity} lots, showing {visible_quantity} lots at a time "
            f"({self.num_slices} slices)"
        )

    def _create_slices(self) -> List[Dict]:
        """Create order slices"""
        slices = []
        remaining = self.total_quantity

        while remaining > 0:
            slice_qty = min(self.visible_quantity, remaining)
            slices.append({
                'slice_id': len(slices),
                'quantity': slice_qty,
                'status': 'PENDING',
                'order_id': None,
                'filled_price': None,
                'filled_time': None
            })
            remaining -= slice_qty

        return slices

    def place_next_slice(self) -> Optional[Dict]:
        """
        Place next visible slice

        Returns:
            Order details or None if completed
        """
        if self.current_slice_index >= len(self.slices):
            self.status = IcebergStatus.COMPLETED
            logger.info(f"✅ Iceberg order completed: {self.order_id}")
            return None

        slice_info = self.slices[self.current_slice_index]

        if self.place_order_callback is None:
            # Simulated order
            self.current_order = {
                'order_id': f"{self.order_id}_SLICE_{self.current_slice_index}",
                'status': 'PLACED',
                'simulated': True
            }
        else:
            # Place actual order
            self.current_order = self.place_order_callback(
                instrument=self.instrument,
                quantity=slice_info['quantity'],
                price=self.price if self.order_type == 'LIMIT' else None,
                order_type=self.order_type,
                transaction_type=self.transaction_type
            )

        slice_info['order_id'] = self.current_order.get('order_id')
        slice_info['status'] = 'PLACED'

        logger.info(
            f"Slice {self.current_slice_index + 1}/{self.num_slices} placed: "
            f"{slice_info['quantity']} lots (Order: {slice_info['order_id']})"
        )

        return self.current_order

    def on_slice_filled(self, filled_price: float, filled_time: datetime):
        """
        Callback when current slice fills

        Args:
            filled_price: Actual fill price
            filled_time: Fill timestamp
        """
        if self.current_slice_index >= len(self.slices):
            logger.warning("No active slice to fill")
            return

        slice_info = self.slices[self.current_slice_index]
        slice_info['filled_price'] = filled_price
        slice_info['filled_time'] = filled_time
        slice_info['status'] = 'FILLED'

        # Update totals
        self.filled_quantity += slice_info['quantity']
        self.total_fill_value += filled_price * slice_info['quantity']
        self.average_fill_price = self.total_fill_value / self.filled_quantity

        self.filled_slices.append(slice_info)

        logger.info(
            f"Slice {self.current_slice_index + 1}/{self.num_slices} filled @ {filled_price:.2f} "
            f"({self.filled_quantity}/{self.total_quantity} lots filled, "
            f"Avg: {self.average_fill_price:.2f})"
        )

        # Update status
        if self.filled_quantity < self.total_quantity:
            self.status = IcebergStatus.PARTIALLY_FILLED
        else:
            self.status = IcebergStatus.COMPLETED
            logger.info(
                f"✅ ICEBERG COMPLETED: {self.instrument} {self.transaction_type} "
                f"{self.filled_quantity} lots @ avg {self.average_fill_price:.2f}"
            )
            return

        # Place next slice automatically
        self.current_slice_index += 1
        self.place_next_slice()

    def cancel_current_slice(self):
        """Cancel currently active slice"""
        if self.current_order:
            logger.info(f"Cancelling current slice: {self.current_order.get('order_id')}")
            if self.cancel_order_callback:
                self.cancel_order_callback(self.current_order.get('order_id'))

            slice_info = self.slices[self.current_slice_index]
            slice_info['status'] = 'CANCELLED'

    def cancel_all(self):
        """Cancel iceberg order (current slice only, filled slices remain)"""
        self.cancel_current_slice()
        self.status = IcebergStatus.CANCELLED

        logger.info(
            f"Iceberg order cancelled: {self.order_id} "
            f"({self.filled_quantity}/{self.total_quantity} lots filled)"
        )

    def modify_price(self, new_price: float):
        """
        Modify limit price for remaining slices

        Args:
            new_price: New limit price
        """
        if self.order_type != 'LIMIT':
            logger.warning("Cannot modify price for market orders")
            return

        old_price = self.price
        self.price = new_price

        # Cancel current slice and replace with new price
        self.cancel_current_slice()
        self.place_next_slice()

        logger.info(f"Price modified: {old_price:.2f} → {new_price:.2f}")

    def get_progress(self) -> Dict:
        """Get order progress details"""
        completion_pct = (self.filled_quantity / self.total_quantity) * 100

        return {
            'total_quantity': self.total_quantity,
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': self.total_quantity - self.filled_quantity,
            'completion_percent': completion_pct,
            'slices_completed': len(self.filled_slices),
            'total_slices': self.num_slices,
            'average_fill_price': self.average_fill_price,
            'current_slice': self.current_slice_index + 1,
            'status': self.status.value
        }

    def get_order_details(self) -> Dict:
        """Get comprehensive iceberg order details"""
        progress = self.get_progress()

        details = {
            'iceberg_id': self.order_id,
            'instrument': self.instrument,
            'transaction_type': self.transaction_type,
            'order_type': self.order_type,
            'total_quantity': self.total_quantity,
            'visible_quantity': self.visible_quantity,
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': progress['remaining_quantity'],
            'completion_percent': progress['completion_percent'],
            'num_slices': self.num_slices,
            'slices_completed': len(self.filled_slices),
            'limit_price': self.price,
            'average_fill_price': self.average_fill_price,
            'status': self.status.value,
            'slices': self.slices,
            'current_order_id': self.current_order.get('order_id') if self.current_order else None
        }

        return details

    def get_fill_quality(self) -> Dict:
        """
        Analyze fill quality (price improvement/slippage)

        Returns:
            Fill quality metrics
        """
        if not self.filled_slices:
            return {'status': 'No fills yet'}

        fills_df = pd.DataFrame(self.filled_slices)

        analysis = {
            'average_fill_price': self.average_fill_price,
            'limit_price': self.price,
            'best_fill': fills_df['filled_price'].min() if self.transaction_type == 'BUY' else fills_df['filled_price'].max(),
            'worst_fill': fills_df['filled_price'].max() if self.transaction_type == 'BUY' else fills_df['filled_price'].min(),
            'fill_price_range': fills_df['filled_price'].max() - fills_df['filled_price'].min(),
            'fill_price_std': fills_df['filled_price'].std(),
            'num_fills': len(self.filled_slices)
        }

        # Calculate slippage vs limit price
        if self.order_type == 'LIMIT':
            if self.transaction_type == 'BUY':
                slippage = self.average_fill_price - self.price
            else:
                slippage = self.price - self.average_fill_price

            analysis['slippage'] = slippage
            analysis['slippage_percent'] = (slippage / self.price) * 100

            if slippage < 0:
                analysis['assessment'] = f"✅ Price improvement: ₹{abs(slippage):.2f} ({abs(analysis['slippage_percent']):.2%})"
            elif slippage > 0:
                analysis['assessment'] = f"⚠️ Slippage: ₹{slippage:.2f} ({analysis['slippage_percent']:.2%})"
            else:
                analysis['assessment'] = "✅ Filled at limit price"

        return analysis

    def __repr__(self):
        """String representation"""
        return (
            f"IcebergOrder({self.instrument}, {self.transaction_type}, "
            f"Total: {self.total_quantity}, Visible: {self.visible_quantity}, "
            f"Filled: {self.filled_quantity}/{self.total_quantity}, "
            f"Status: {self.status.value})"
        )


def create_iceberg_from_position_size(
    instrument: str,
    total_quantity: int,
    price: float,
    transaction_type: str = 'BUY',
    max_market_impact_pct: float = 5.0  # Show max 5% of total size
) -> IcebergOrder:
    """
    Create iceberg order with automatic visible quantity calculation

    Args:
        instrument: Instrument name
        total_quantity: Total order size
        price: Limit price
        transaction_type: 'BUY' or 'SELL'
        max_market_impact_pct: Max visible quantity as % of total

    Returns:
        IcebergOrder instance
    """
    visible_quantity = max(1, int(total_quantity * max_market_impact_pct / 100))

    return IcebergOrder(
        instrument=instrument,
        total_quantity=total_quantity,
        visible_quantity=visible_quantity,
        price=price,
        transaction_type=transaction_type
    )
