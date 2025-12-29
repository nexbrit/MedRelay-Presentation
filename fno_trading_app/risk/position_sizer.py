"""
Advanced Risk Management System
Position sizing, portfolio heat monitoring, and risk controls
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Calculate optimal position sizes using multiple methods
    Professional-grade position sizing for F&O trading
    """

    def __init__(self, account_balance: float):
        """
        Initialize position sizer

        Args:
            account_balance: Total account balance in INR
        """
        self.account_balance = account_balance
        logger.info(f"Position Sizer initialized with balance: ₹{account_balance:,.2f}")

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        safety_factor: float = 0.5
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion

        Kelly % = (Win Rate × Win/Loss Ratio - (1 - Win Rate)) / Win/Loss Ratio

        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            safety_factor: Safety multiplier (default 0.5 = half Kelly)

        Returns:
            Optimal position size as percentage of account (0.0 to 1.0)

        Example:
            >>> sizer = PositionSizer(500000)
            >>> kelly_pct = sizer.kelly_criterion(0.55, 1000, 600)
            >>> print(f"Kelly suggests risking {kelly_pct*100:.1f}% of account")
        """
        if avg_loss <= 0:
            logger.error("Average loss must be positive")
            return 0.0

        if not 0 <= win_rate <= 1:
            logger.error(f"Invalid win rate: {win_rate}")
            return 0.0

        win_loss_ratio = avg_win / avg_loss
        kelly_percent = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        # Apply safety factor (usually 0.5 for half-Kelly)
        safe_kelly = kelly_percent * safety_factor

        # Cap at 25% maximum (even Kelly can be aggressive)
        safe_kelly = max(0.0, min(safe_kelly, 0.25))

        logger.debug(
            f"Kelly Criterion: Win Rate={win_rate:.2%}, "
            f"W/L Ratio={win_loss_ratio:.2f}, "
            f"Kelly={kelly_percent:.2%}, "
            f"Safe Kelly={safe_kelly:.2%}"
        )

        return safe_kelly

    def fixed_fractional(
        self,
        risk_percent: float,
        entry_price: float,
        stop_loss: float,
        lot_size: int = 1
    ) -> int:
        """
        Calculate position size using Fixed Fractional method

        Position Size = (Account × Risk%) / (Entry - Stop Loss) / Lot Size

        Args:
            risk_percent: Percentage of account to risk (e.g., 2.0 for 2%)
            entry_price: Entry price per unit
            stop_loss: Stop loss price per unit
            lot_size: Contract lot size (e.g., 50 for Nifty)

        Returns:
            Number of lots to trade

        Example:
            >>> sizer = PositionSizer(500000)
            >>> lots = sizer.fixed_fractional(2.0, 21500, 21300, lot_size=50)
            >>> print(f"Trade {lots} lots")
        """
        if risk_percent <= 0 or risk_percent > 100:
            logger.error(f"Invalid risk percent: {risk_percent}")
            return 0

        risk_amount = self.account_balance * (risk_percent / 100)
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            logger.error("Entry and stop loss are the same")
            return 0

        # Calculate number of units
        units = risk_amount / risk_per_unit

        # Convert to lots
        lots = int(units / lot_size)

        # Ensure at least 1 lot if risk allows
        if lots == 0 and risk_amount >= risk_per_unit * lot_size:
            lots = 1

        actual_risk = lots * lot_size * risk_per_unit
        actual_risk_pct = (actual_risk / self.account_balance) * 100

        logger.info(
            f"Fixed Fractional Sizing: Risk={risk_percent}%, "
            f"Entry={entry_price}, SL={stop_loss}, "
            f"Calculated Lots={lots}, "
            f"Actual Risk=₹{actual_risk:,.0f} ({actual_risk_pct:.2f}%)"
        )

        return lots

    def volatility_adjusted(
        self,
        base_position_size: int,
        current_atr: float,
        average_atr: float,
        max_adjustment: float = 0.5
    ) -> int:
        """
        Adjust position size based on volatility (ATR)

        Higher volatility → Smaller position
        Lower volatility → Larger position

        Args:
            base_position_size: Base position size in lots
            current_atr: Current Average True Range
            average_atr: Historical average ATR
            max_adjustment: Maximum adjustment factor (default 0.5 = ±50%)

        Returns:
            Volatility-adjusted position size

        Example:
            >>> sizer = PositionSizer(500000)
            >>> adjusted = sizer.volatility_adjusted(10, 150, 100)
            >>> # ATR is 50% higher, so position reduced
        """
        if average_atr <= 0:
            logger.warning("Invalid average ATR, returning base size")
            return base_position_size

        volatility_ratio = current_atr / average_atr

        # Inverse relationship: higher vol = smaller size
        adjustment_factor = 1 / volatility_ratio

        # Limit adjustment
        adjustment_factor = max(
            1 - max_adjustment,
            min(1 + max_adjustment, adjustment_factor)
        )

        adjusted_size = int(base_position_size * adjustment_factor)
        adjusted_size = max(1, adjusted_size)  # At least 1 lot

        logger.info(
            f"Volatility Adjustment: ATR ratio={volatility_ratio:.2f}, "
            f"Adjustment={adjustment_factor:.2f}, "
            f"Base={base_position_size} → Adjusted={adjusted_size}"
        )

        return adjusted_size

    def calculate_position(
        self,
        method: str,
        entry_price: float,
        stop_loss: float,
        lot_size: int = 50,
        **kwargs
    ) -> Dict:
        """
        Unified position sizing calculator

        Args:
            method: 'fixed_fractional', 'kelly', or 'volatility_adjusted'
            entry_price: Entry price
            stop_loss: Stop loss price
            lot_size: Contract lot size
            **kwargs: Additional parameters for specific methods

        Returns:
            Dictionary with position sizing details
        """
        result = {
            'method': method,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'lot_size': lot_size,
            'recommended_lots': 0,
            'risk_amount': 0,
            'risk_percent': 0
        }

        if method == 'fixed_fractional':
            risk_percent = kwargs.get('risk_percent', 2.0)
            lots = self.fixed_fractional(risk_percent, entry_price, stop_loss, lot_size)
            result['recommended_lots'] = lots

        elif method == 'kelly':
            win_rate = kwargs.get('win_rate', 0.5)
            avg_win = kwargs.get('avg_win', 1000)
            avg_loss = kwargs.get('avg_loss', 600)
            kelly_pct = self.kelly_criterion(win_rate, avg_win, avg_loss)

            # Convert Kelly % to position size
            risk_amount = self.account_balance * kelly_pct
            risk_per_unit = abs(entry_price - stop_loss)
            lots = int((risk_amount / risk_per_unit) / lot_size)
            result['recommended_lots'] = lots
            result['kelly_percent'] = kelly_pct * 100

        elif method == 'volatility_adjusted':
            base_lots = kwargs.get('base_lots', 1)
            current_atr = kwargs.get('current_atr', 100)
            average_atr = kwargs.get('average_atr', 100)
            lots = self.volatility_adjusted(base_lots, current_atr, average_atr)
            result['recommended_lots'] = lots

        # Calculate actual risk
        if result['recommended_lots'] > 0:
            risk_per_unit = abs(entry_price - stop_loss)
            result['risk_amount'] = result['recommended_lots'] * lot_size * risk_per_unit
            result['risk_percent'] = (result['risk_amount'] / self.account_balance) * 100

        return result

    def update_balance(self, new_balance: float):
        """Update account balance after trades"""
        old_balance = self.account_balance
        self.account_balance = new_balance
        pnl = new_balance - old_balance
        pnl_pct = (pnl / old_balance) * 100

        logger.info(
            f"Balance updated: ₹{old_balance:,.2f} → ₹{new_balance:,.2f} "
            f"({pnl_pct:+.2f}%)"
        )


class PortfolioHeatMonitor:
    """
    Monitor total risk exposure across all positions
    Prevents over-leveraging and account blow-ups
    """

    def __init__(
        self,
        account_balance: float,
        max_portfolio_heat: float = 6.0,
        max_single_position: float = 2.0
    ):
        """
        Initialize portfolio heat monitor

        Args:
            account_balance: Total account balance
            max_portfolio_heat: Maximum total portfolio risk % (default 6%)
            max_single_position: Maximum single position risk % (default 2%)
        """
        self.account_balance = account_balance
        self.max_portfolio_heat = max_portfolio_heat
        self.max_single_position = max_single_position
        self.positions = []

        logger.info(
            f"Portfolio Heat Monitor initialized: "
            f"Max Heat={max_portfolio_heat}%, "
            f"Max Single Position={max_single_position}%"
        )

    def add_position(
        self,
        instrument: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        lot_size: int = 1
    ) -> Tuple[bool, str]:
        """
        Add a new position and check if it's within risk limits

        Args:
            instrument: Instrument name
            quantity: Number of lots
            entry_price: Entry price per unit
            stop_loss: Stop loss price per unit
            lot_size: Contract lot size

        Returns:
            Tuple of (allowed: bool, message: str)
        """
        # Calculate position risk
        risk_per_unit = abs(entry_price - stop_loss)
        position_risk = quantity * lot_size * risk_per_unit
        position_risk_pct = (position_risk / self.account_balance) * 100

        # Check single position limit
        if position_risk_pct > self.max_single_position:
            msg = (
                f"❌ REJECTED: Position risk {position_risk_pct:.2f}% "
                f"exceeds limit {self.max_single_position}%"
            )
            logger.warning(msg)
            return False, msg

        # Calculate new portfolio heat
        current_heat = self.calculate_portfolio_heat()
        new_heat = current_heat + position_risk_pct

        # Check portfolio heat limit
        if new_heat > self.max_portfolio_heat:
            msg = (
                f"❌ REJECTED: New portfolio heat {new_heat:.2f}% "
                f"exceeds limit {self.max_portfolio_heat}% "
                f"(current: {current_heat:.2f}%)"
            )
            logger.warning(msg)
            return False, msg

        # Add position
        position = {
            'instrument': instrument,
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'lot_size': lot_size,
            'risk_amount': position_risk,
            'risk_percent': position_risk_pct
        }
        self.positions.append(position)

        msg = (
            f"✅ APPROVED: {instrument} position added. "
            f"Risk: ₹{position_risk:,.0f} ({position_risk_pct:.2f}%). "
            f"Portfolio Heat: {current_heat:.2f}% → {new_heat:.2f}%"
        )
        logger.info(msg)
        return True, msg

    def remove_position(self, instrument: str):
        """Remove a position when closed"""
        self.positions = [p for p in self.positions if p['instrument'] != instrument]
        logger.info(f"Position removed: {instrument}")

    def calculate_portfolio_heat(self) -> float:
        """
        Calculate total portfolio heat (risk across all positions)

        Returns:
            Portfolio heat as percentage of account balance
        """
        total_risk = sum(pos['risk_amount'] for pos in self.positions)
        heat = (total_risk / self.account_balance) * 100
        return heat

    def get_portfolio_summary(self) -> Dict:
        """
        Get portfolio risk summary

        Returns:
            Dictionary with portfolio statistics
        """
        heat = self.calculate_portfolio_heat()
        total_risk = sum(pos['risk_amount'] for pos in self.positions)

        summary = {
            'account_balance': self.account_balance,
            'positions_count': len(self.positions),
            'total_risk_amount': total_risk,
            'portfolio_heat': heat,
            'max_portfolio_heat': self.max_portfolio_heat,
            'heat_utilization': (heat / self.max_portfolio_heat) * 100,
            'available_risk': self.max_portfolio_heat - heat,
            'positions': self.positions.copy()
        }

        return summary

    def can_add_position(self, risk_amount: float) -> Tuple[bool, str]:
        """
        Check if a new position can be added given its risk

        Args:
            risk_amount: Risk amount for new position

        Returns:
            Tuple of (allowed: bool, message: str)
        """
        current_heat = self.calculate_portfolio_heat()
        new_position_risk_pct = (risk_amount / self.account_balance) * 100
        new_heat = current_heat + new_position_risk_pct

        if new_heat > self.max_portfolio_heat:
            return False, f"Would exceed max heat: {new_heat:.2f}% > {self.max_portfolio_heat}%"

        return True, f"OK to add. New heat: {new_heat:.2f}%"

    def update_balance(self, new_balance: float):
        """Update account balance and recalculate all percentages"""
        self.account_balance = new_balance
        logger.info(f"Balance updated to ₹{new_balance:,.2f}")

    def get_riskiest_position(self) -> Optional[Dict]:
        """Get the position with highest risk"""
        if not self.positions:
            return None
        return max(self.positions, key=lambda x: x['risk_percent'])

    def force_reduce_risk(self) -> str:
        """Emergency risk reduction - close riskiest position"""
        riskiest = self.get_riskiest_position()
        if riskiest:
            self.remove_position(riskiest['instrument'])
            return f"Closed riskiest position: {riskiest['instrument']}"
        return "No positions to close"
