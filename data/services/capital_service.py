"""
Capital Service for persistent capital management.

Provides capital tracking, adjustment history, and time-weighted return
calculations with full persistence to survive application restarts.
"""

from datetime import datetime
from typing import Any, Optional, List, Dict
import logging
import math

from data.persistence.state_manager import StateManager

logger = logging.getLogger(__name__)


class CapitalService:
    """
    Service for capital management and tracking.

    Features:
    - Persistent capital storage (survives restarts)
    - Deposit and withdrawal tracking
    - Time-Weighted Return (TWR) calculation
    - Capital adjustment history with audit trail
    - Integration with position sizing

    Example:
        capital = CapitalService()
        capital.initialize(500000)  # First-time setup
        capital.deposit(100000, "Monthly deposit")
        current = capital.get_current_capital()
        twr = capital.calculate_twr()
    """

    def __init__(self, state_manager: Optional[StateManager] = None):
        """
        Initialize capital service.

        Args:
            state_manager: Optional state manager for persistence
        """
        self._state = state_manager or StateManager()

    def is_initialized(self) -> bool:
        """
        Check if capital has been initialized.

        Returns:
            True if capital is initialized
        """
        state = self._state.get_capital_state()
        return state is not None

    def initialize(
        self,
        initial_capital: float,
        reason: str = "Initial capital setup"
    ) -> bool:
        """
        Initialize capital for first-time setup.

        Args:
            initial_capital: Starting capital amount
            reason: Reason for initialization

        Returns:
            True if successful, False if already initialized

        Raises:
            ValueError: If initial_capital is invalid
        """
        if initial_capital <= 0:
            raise ValueError("Initial capital must be positive")

        if self.is_initialized():
            logger.warning("Capital already initialized. Use adjust() instead.")
            return False

        success = self._state.initialize_capital(initial_capital, reason)

        if success:
            logger.info(f"Capital initialized: {initial_capital:,.2f}")

        return success

    def get_current_capital(self) -> float:
        """
        Get current capital amount.

        Returns:
            Current capital or 0 if not initialized
        """
        state = self._state.get_capital_state()
        return state['current_capital'] if state else 0.0

    def get_initial_capital(self) -> float:
        """
        Get initial capital amount.

        Returns:
            Initial capital or 0 if not initialized
        """
        state = self._state.get_capital_state()
        return state['initial_capital'] if state else 0.0

    def get_available_capital(self) -> float:
        """
        Get available (unallocated) capital.

        Returns:
            Available capital amount
        """
        state = self._state.get_capital_state()
        return state['available_capital'] if state else 0.0

    def get_capital_state(self) -> Optional[Dict[str, Any]]:
        """
        Get full capital state.

        Returns:
            Dictionary with all capital state information
        """
        state = self._state.get_capital_state()
        if state:
            # Add calculated fields
            state['absolute_return'] = (
                state['current_capital'] - state['initial_capital']
            )
            state['return_percent'] = (
                (state['absolute_return'] / state['initial_capital'] * 100)
                if state['initial_capital'] > 0 else 0
            )
        return state

    def deposit(
        self,
        amount: float,
        reason: str = ""
    ) -> bool:
        """
        Record a capital deposit.

        Args:
            amount: Deposit amount (must be positive)
            reason: Reason for deposit

        Returns:
            True if successful
        """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")

        success = self._state.adjust_capital(
            amount=amount,
            adjustment_type='DEPOSIT',
            reason=reason
        )

        if success:
            new_capital = self.get_current_capital()
            logger.info(
                f"Deposit: +{amount:,.2f} | New capital: {new_capital:,.2f}"
            )

        return success

    def withdraw(
        self,
        amount: float,
        reason: str = ""
    ) -> bool:
        """
        Record a capital withdrawal.

        Args:
            amount: Withdrawal amount (must be positive)
            reason: Reason for withdrawal

        Returns:
            True if successful
        """
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        current = self.get_current_capital()
        if amount > current:
            raise ValueError(
                f"Withdrawal amount ({amount:,.2f}) exceeds "
                f"current capital ({current:,.2f})"
            )

        success = self._state.adjust_capital(
            amount=amount,
            adjustment_type='WITHDRAWAL',
            reason=reason
        )

        if success:
            new_capital = self.get_current_capital()
            logger.info(
                f"Withdrawal: -{amount:,.2f} | New capital: {new_capital:,.2f}"
            )

        return success

    def record_trade_pnl(
        self,
        pnl: float,
        reference_id: str = None,
        reason: str = ""
    ) -> bool:
        """
        Record P&L from a trade.

        Args:
            pnl: Profit/loss amount (positive for profit, negative for loss)
            reference_id: Order ID or trade reference
            reason: Trade description

        Returns:
            True if successful
        """
        if pnl >= 0:
            adjustment_type = 'TRADE_PROFIT'
        else:
            adjustment_type = 'TRADE_LOSS'

        success = self._state.adjust_capital(
            amount=abs(pnl),
            adjustment_type=adjustment_type,
            reason=reason,
            reference_id=reference_id
        )

        if success:
            logger.info(f"Trade P&L recorded: {pnl:+,.2f}")

        return success

    def adjust(
        self,
        amount: float,
        reason: str = ""
    ) -> bool:
        """
        Make a manual capital adjustment.

        Args:
            amount: Adjustment amount (positive or negative)
            reason: Reason for adjustment

        Returns:
            True if successful
        """
        return self._state.adjust_capital(
            amount=amount,
            adjustment_type='MANUAL_ADJUSTMENT',
            reason=reason
        )

    def get_history(
        self,
        limit: int = 50,
        adjustment_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get capital adjustment history.

        Args:
            limit: Maximum records to return
            adjustment_type: Filter by type (DEPOSIT, WITHDRAWAL, etc.)

        Returns:
            List of adjustment records
        """
        return self._state.get_capital_history(
            limit=limit,
            adjustment_type=adjustment_type
        )

    def calculate_twr(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> float:
        """
        Calculate Time-Weighted Return (TWR).

        TWR accounts for external cash flows (deposits/withdrawals)
        to show true investment performance.

        Args:
            start_date: Start of calculation period
            end_date: End of calculation period

        Returns:
            TWR as a percentage
        """
        history = self.get_history(limit=1000)

        if not history:
            state = self.get_capital_state()
            if state:
                return state['return_percent']
            return 0.0

        # Sort by timestamp ascending
        history = sorted(history, key=lambda x: x['timestamp'])

        # Filter by date range if specified
        if start_date:
            history = [
                h for h in history
                if datetime.fromisoformat(str(h['timestamp'])) >= start_date
            ]
        if end_date:
            history = [
                h for h in history
                if datetime.fromisoformat(str(h['timestamp'])) <= end_date
            ]

        if len(history) < 2:
            state = self.get_capital_state()
            if state:
                return state['return_percent']
            return 0.0

        # Calculate TWR using sub-period returns
        twr = 1.0

        for i in range(1, len(history)):
            prev = history[i - 1]
            curr = history[i]

            prev_capital = prev['new_capital']
            curr_capital_before = prev_capital

            # Adjust for cash flow (if any)
            if curr['adjustment_type'] in ['DEPOSIT', 'WITHDRAWAL']:
                curr_capital_before = prev_capital

            curr_capital_after = curr['new_capital']

            # Skip if division would be by zero
            if curr_capital_before == 0:
                continue

            # Calculate sub-period return
            sub_return = curr_capital_after / curr_capital_before
            twr *= sub_return

        # Convert to percentage
        twr_percent = (twr - 1) * 100

        return round(twr_percent, 2)

    def calculate_cagr(self, years: float = None) -> float:
        """
        Calculate Compound Annual Growth Rate (CAGR).

        Args:
            years: Number of years (auto-calculated if None)

        Returns:
            CAGR as a percentage
        """
        state = self.get_capital_state()
        if not state:
            return 0.0

        history = self.get_history(limit=1000)
        if not history:
            return 0.0

        # Get first and current capital
        first_record = min(history, key=lambda x: x['timestamp'])
        start_capital = first_record['previous_capital'] or first_record['new_capital']
        end_capital = state['current_capital']

        if start_capital <= 0:
            return 0.0

        # Calculate years if not provided
        if years is None:
            start_date = datetime.fromisoformat(str(first_record['timestamp']))
            days = (datetime.now() - start_date).days
            years = max(days / 365.25, 0.001)  # Minimum 1 day

        # CAGR formula: (End/Start)^(1/years) - 1
        if years > 0:
            cagr = (math.pow(end_capital / start_capital, 1 / years) - 1) * 100
            return round(cagr, 2)

        return 0.0

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive capital summary.

        Returns:
            Dictionary with capital metrics
        """
        state = self.get_capital_state()

        if not state:
            return {
                'initialized': False,
                'current_capital': 0,
                'initial_capital': 0,
                'available_capital': 0,
                'absolute_return': 0,
                'return_percent': 0,
                'twr_percent': 0,
                'cagr_percent': 0,
                'total_deposits': 0,
                'total_withdrawals': 0,
                'total_trading_pnl': 0,
                'timestamp': datetime.now().isoformat()
            }

        # Get adjustment totals
        history = self.get_history(limit=1000)

        total_deposits = sum(
            h['amount'] for h in history
            if h['adjustment_type'] == 'DEPOSIT'
        )
        total_withdrawals = sum(
            h['amount'] for h in history
            if h['adjustment_type'] == 'WITHDRAWAL'
        )
        total_profits = sum(
            h['amount'] for h in history
            if h['adjustment_type'] == 'TRADE_PROFIT'
        )
        total_losses = sum(
            h['amount'] for h in history
            if h['adjustment_type'] == 'TRADE_LOSS'
        )

        return {
            'initialized': True,
            'current_capital': state['current_capital'],
            'initial_capital': state['initial_capital'],
            'available_capital': state['available_capital'],
            'allocated_capital': state.get('allocated_capital', 0),
            'absolute_return': state['absolute_return'],
            'return_percent': state['return_percent'],
            'twr_percent': self.calculate_twr(),
            'cagr_percent': self.calculate_cagr(),
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'total_trading_pnl': total_profits - total_losses,
            'total_trading_profits': total_profits,
            'total_trading_losses': total_losses,
            'net_cash_flow': total_deposits - total_withdrawals,
            'last_updated': state.get('last_updated'),
            'timestamp': datetime.now().isoformat()
        }

    def validate_trade_size(
        self,
        trade_value: float,
        max_position_percent: float = 10.0
    ) -> Dict[str, Any]:
        """
        Validate if a trade size is within acceptable limits.

        Args:
            trade_value: Total value of proposed trade
            max_position_percent: Maximum position size as % of capital

        Returns:
            Dictionary with validation result and details
        """
        current = self.get_current_capital()

        if current <= 0:
            return {
                'valid': False,
                'reason': 'Capital not initialized',
                'trade_value': trade_value,
                'current_capital': current,
                'max_allowed': 0
            }

        max_allowed = current * (max_position_percent / 100)
        position_percent = (trade_value / current) * 100

        is_valid = trade_value <= max_allowed

        return {
            'valid': is_valid,
            'reason': None if is_valid else (
                f'Trade exceeds {max_position_percent}% position limit'
            ),
            'trade_value': trade_value,
            'current_capital': current,
            'max_allowed': max_allowed,
            'position_percent': round(position_percent, 2),
            'max_position_percent': max_position_percent
        }

    def get_position_sizing_capital(
        self,
        risk_percent: float = 2.0
    ) -> Dict[str, float]:
        """
        Get capital amounts for position sizing calculations.

        Args:
            risk_percent: Risk per trade as percentage

        Returns:
            Dictionary with position sizing parameters
        """
        current = self.get_current_capital()

        return {
            'total_capital': current,
            'risk_per_trade': current * (risk_percent / 100),
            'max_position_value': current * 0.10,  # 10% max position
            'max_portfolio_heat': current * 0.06,  # 6% max heat
            'suggested_position_value': current * 0.05  # 5% suggested
        }
