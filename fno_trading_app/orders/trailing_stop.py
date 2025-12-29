"""
Trailing Stop-Loss System
Automatically moves stop-loss as price moves favorably
Professional profit protection
"""

import pandas as pd
from typing import Dict, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrailingStopType(Enum):
    """Trailing stop types"""
    PERCENTAGE = "PERCENTAGE"  # Trail by percentage
    ABSOLUTE = "ABSOLUTE"  # Trail by absolute points
    ATR = "ATR"  # Trail by ATR multiple


class TrailingStop:
    """
    Trailing Stop-Loss: Locks in profits as price moves favorably
    Professional profit protection system
    """

    def __init__(
        self,
        instrument: str,
        entry_price: float,
        direction: str,  # 'LONG' or 'SHORT'
        trailing_type: TrailingStopType = TrailingStopType.PERCENTAGE,
        trail_amount: float = 1.0,  # 1% or 10 points or 1x ATR
        initial_stop_loss: Optional[float] = None,
        quantity: int = 1,
        modify_order_callback: Optional[Callable] = None
    ):
        """
        Initialize trailing stop

        Args:
            instrument: Instrument to trade
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            trailing_type: Type of trailing (PERCENTAGE, ABSOLUTE, ATR)
            trail_amount: Trail distance (percentage, points, or ATR multiple)
            initial_stop_loss: Initial stop-loss price
            quantity: Position size
            modify_order_callback: Function to modify stop-loss with broker
        """
        self.instrument = instrument
        self.entry_price = entry_price
        self.direction = direction
        self.trailing_type = trailing_type
        self.trail_amount = trail_amount
        self.quantity = quantity
        self.modify_order_callback = modify_order_callback

        # Initialize stop-loss
        if initial_stop_loss is None:
            # Default: 2% below entry for LONG, 2% above for SHORT
            if direction == 'LONG':
                self.current_stop = entry_price * 0.98
            else:
                self.current_stop = entry_price * 1.02
        else:
            self.current_stop = initial_stop_loss

        # Tracking
        self.highest_price = entry_price if direction == 'LONG' else None
        self.lowest_price = entry_price if direction == 'SHORT' else None
        self.stop_modifications = 0
        self.is_active = True
        self.stop_hit_price = None

        logger.info(
            f"Trailing stop created: {instrument} {direction} @ {entry_price}, "
            f"Trail: {trail_amount} {trailing_type.value}, Initial SL: {self.current_stop:.2f}"
        )

    def update(self, current_price: float, atr: Optional[float] = None) -> Dict:
        """
        Update trailing stop based on current price

        Args:
            current_price: Current market price
            atr: Current ATR (required for ATR-based trailing)

        Returns:
            Dictionary with update details
        """
        if not self.is_active:
            return {'modified': False, 'reason': 'Stop already hit'}

        old_stop = self.current_stop
        modified = False

        if self.direction == 'LONG':
            # Update highest price seen
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price

                # Calculate new stop
                new_stop = self._calculate_trail_stop(self.highest_price, atr)

                # Only move stop up (never down)
                if new_stop > self.current_stop:
                    self.current_stop = new_stop
                    modified = True

            # Check if stop hit
            if current_price <= self.current_stop:
                return self._stop_hit(current_price)

        else:  # SHORT
            # Update lowest price seen
            if self.lowest_price is None or current_price < self.lowest_price:
                self.lowest_price = current_price

                # Calculate new stop
                new_stop = self._calculate_trail_stop(self.lowest_price, atr)

                # Only move stop down (never up)
                if new_stop < self.current_stop:
                    self.current_stop = new_stop
                    modified = True

            # Check if stop hit
            if current_price >= self.current_stop:
                return self._stop_hit(current_price)

        # Modify broker order if stop changed
        if modified:
            self.stop_modifications += 1

            if self.modify_order_callback is not None:
                self.modify_order_callback(
                    instrument=self.instrument,
                    new_stop_price=self.current_stop
                )

            logger.info(
                f"Trailing stop moved: {old_stop:.2f} → {self.current_stop:.2f} "
                f"(#{self.stop_modifications})"
            )

        return {
            'modified': modified,
            'old_stop': old_stop,
            'new_stop': self.current_stop,
            'current_price': current_price,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'stop_modifications': self.stop_modifications,
            'unrealized_pnl': self._calculate_unrealized_pnl(current_price),
            'protected_profit': self._calculate_protected_profit()
        }

    def _calculate_trail_stop(self, reference_price: float, atr: Optional[float] = None) -> float:
        """Calculate trailing stop based on type"""
        if self.trailing_type == TrailingStopType.PERCENTAGE:
            # Percentage-based trail
            if self.direction == 'LONG':
                return reference_price * (1 - self.trail_amount / 100)
            else:
                return reference_price * (1 + self.trail_amount / 100)

        elif self.trailing_type == TrailingStopType.ABSOLUTE:
            # Absolute points trail
            if self.direction == 'LONG':
                return reference_price - self.trail_amount
            else:
                return reference_price + self.trail_amount

        elif self.trailing_type == TrailingStopType.ATR:
            # ATR-based trail
            if atr is None:
                logger.warning("ATR required for ATR-based trailing - using percentage instead")
                return self._calculate_trail_stop(reference_price, None)

            if self.direction == 'LONG':
                return reference_price - (self.trail_amount * atr)
            else:
                return reference_price + (self.trail_amount * atr)

        return self.current_stop

    def _stop_hit(self, hit_price: float) -> Dict:
        """Handle stop-loss hit"""
        self.is_active = False
        self.stop_hit_price = hit_price

        pnl = self._calculate_pnl(hit_price)

        logger.warning(
            f"🛑 TRAILING STOP HIT: {self.instrument} @ {hit_price:.2f}, "
            f"P&L: ₹{pnl:,.2f}"
        )

        return {
            'modified': False,
            'stop_hit': True,
            'hit_price': hit_price,
            'pnl': pnl,
            'stop_modifications': self.stop_modifications,
            'reason': f'Trailing stop hit at {hit_price:.2f}'
        }

    def _calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.direction == 'LONG':
            return (current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - current_price) * self.quantity

    def _calculate_pnl(self, exit_price: float) -> float:
        """Calculate realized P&L"""
        if self.direction == 'LONG':
            return (exit_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - exit_price) * self.quantity

    def _calculate_protected_profit(self) -> float:
        """Calculate profit protected by current stop"""
        if self.direction == 'LONG':
            return (self.current_stop - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_stop) * self.quantity

    def force_move_stop(self, new_stop_price: float):
        """
        Manually force stop to a specific level

        Args:
            new_stop_price: New stop-loss price
        """
        # Validate: stop can only move in favorable direction
        if self.direction == 'LONG' and new_stop_price <= self.current_stop:
            logger.warning(f"LONG position: New stop must be higher than current ({self.current_stop:.2f})")
            return
        elif self.direction == 'SHORT' and new_stop_price >= self.current_stop:
            logger.warning(f"SHORT position: New stop must be lower than current ({self.current_stop:.2f})")
            return

        old_stop = self.current_stop
        self.current_stop = new_stop_price
        self.stop_modifications += 1

        if self.modify_order_callback is not None:
            self.modify_order_callback(
                instrument=self.instrument,
                new_stop_price=new_stop_price
            )

        logger.info(f"Stop manually moved: {old_stop:.2f} → {new_stop_price:.2f}")

    def move_to_breakeven(self, buffer: float = 0):
        """
        Move stop to breakeven (entry price + buffer)

        Args:
            buffer: Points above/below entry (positive for buffer)
        """
        if self.direction == 'LONG':
            breakeven_stop = self.entry_price + buffer
            if breakeven_stop > self.current_stop:
                self.force_move_stop(breakeven_stop)
                logger.info(f"✅ Stop moved to breakeven + {buffer:.2f}")
        else:
            breakeven_stop = self.entry_price - buffer
            if breakeven_stop < self.current_stop:
                self.force_move_stop(breakeven_stop)
                logger.info(f"✅ Stop moved to breakeven - {buffer:.2f}")

    def get_status(self) -> Dict:
        """Get comprehensive trailing stop status"""
        return {
            'instrument': self.instrument,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'current_stop': self.current_stop,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'trailing_type': self.trailing_type.value,
            'trail_amount': self.trail_amount,
            'stop_modifications': self.stop_modifications,
            'is_active': self.is_active,
            'stop_hit_price': self.stop_hit_price,
            'protected_profit': self._calculate_protected_profit(),
            'quantity': self.quantity
        }

    def __repr__(self):
        """String representation"""
        status = "ACTIVE" if self.is_active else "HIT"
        return (
            f"TrailingStop({self.instrument}, {self.direction}, "
            f"Entry: {self.entry_price:.2f}, Stop: {self.current_stop:.2f}, "
            f"Trail: {self.trail_amount} {self.trailing_type.value}, "
            f"Modifications: {self.stop_modifications}, Status: {status})"
        )


def create_trailing_stop_from_position(
    position: Dict,
    trailing_type: TrailingStopType = TrailingStopType.PERCENTAGE,
    trail_amount: float = 1.0
) -> TrailingStop:
    """
    Create trailing stop from an existing position

    Args:
        position: Position dictionary with instrument, entry_price, direction, quantity
        trailing_type: Type of trailing
        trail_amount: Trail distance

    Returns:
        TrailingStop instance
    """
    return TrailingStop(
        instrument=position['instrument'],
        entry_price=position['entry_price'],
        direction=position['direction'],
        quantity=position.get('quantity', 1),
        trailing_type=trailing_type,
        trail_amount=trail_amount
    )
