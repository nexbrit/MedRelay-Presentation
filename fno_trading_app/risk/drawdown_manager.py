"""
Drawdown Management Protocol - Protect capital during losing streaks
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum


class DrawdownSeverity(Enum):
    """Drawdown severity levels"""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class DrawdownAction(Enum):
    """Recommended actions based on drawdown"""
    CONTINUE_NORMAL = "continue_normal"
    REDUCE_SIZE_50 = "reduce_size_50"
    REDUCE_SIZE_75 = "reduce_size_75"
    STOP_1_DAY = "stop_1_day"
    STOP_1_WEEK = "stop_1_week"
    REASSESS_STRATEGY = "reassess_strategy"


class DrawdownManager:
    """
    Manage drawdown and protect capital during losing periods

    Actions based on drawdown:
    - < 5%: Normal trading
    - 5-10%: Reduce position size by 50%
    - 10-15%: Reduce position size by 75%
    - 15-20%: Stop trading for 1 week, analyze trades
    - > 20%: Stop all trading, reassess strategy
    """

    def __init__(self, initial_capital: float, max_dd_threshold: float = 15.0):
        """
        Initialize drawdown manager

        Args:
            initial_capital: Starting capital
            max_dd_threshold: Maximum acceptable drawdown % (default: 15%)
        """
        self.initial_capital = initial_capital
        self.peak_capital = initial_capital
        self.current_capital = initial_capital
        self.max_dd_threshold = max_dd_threshold

        # Drawdown history
        self.dd_history = []

        # Current drawdown state
        self.current_dd_pct = 0.0
        self.current_severity = DrawdownSeverity.NORMAL
        self.trading_paused = False
        self.pause_until = None

    def update(self, current_capital: float, timestamp: datetime = None) -> Dict:
        """
        Update capital and calculate drawdown status

        Args:
            current_capital: Current account capital
            timestamp: Current timestamp (defaults to now)

        Returns:
            Dictionary with drawdown status and recommendations
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.current_capital = current_capital

        # Update peak capital
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital

        # Calculate drawdown percentage
        dd_percentage = ((self.peak_capital - current_capital) / self.peak_capital) * 100

        self.current_dd_pct = dd_percentage

        # Determine severity and action
        severity, action = self._get_action(dd_percentage)
        self.current_severity = severity

        # Record in history
        self.dd_history.append({
            'timestamp': timestamp,
            'capital': current_capital,
            'peak': self.peak_capital,
            'dd_pct': dd_percentage,
            'severity': severity.value,
        })

        # Check if trading pause is required
        if action in [DrawdownAction.STOP_1_DAY, DrawdownAction.STOP_1_WEEK, DrawdownAction.REASSESS_STRATEGY]:
            self._initiate_trading_pause(action, timestamp)

        return {
            'current_capital': current_capital,
            'peak_capital': self.peak_capital,
            'drawdown_pct': round(dd_percentage, 2),
            'drawdown_amount': round(self.peak_capital - current_capital, 2),
            'severity': severity.value,
            'recommended_action': action.value,
            'trading_paused': self.trading_paused,
            'pause_until': self.pause_until,
            'message': self._get_message(severity, action, dd_percentage)
        }

    def _get_action(self, dd_percentage: float) -> Tuple[DrawdownSeverity, DrawdownAction]:
        """
        Determine severity and recommended action based on drawdown

        Args:
            dd_percentage: Current drawdown percentage

        Returns:
            Tuple of (severity, action)
        """
        if dd_percentage < 5:
            return DrawdownSeverity.NORMAL, DrawdownAction.CONTINUE_NORMAL

        elif dd_percentage < 10:
            return DrawdownSeverity.CAUTION, DrawdownAction.REDUCE_SIZE_50

        elif dd_percentage < 15:
            return DrawdownSeverity.WARNING, DrawdownAction.REDUCE_SIZE_75

        elif dd_percentage < 20:
            return DrawdownSeverity.CRITICAL, DrawdownAction.STOP_1_WEEK

        else:
            return DrawdownSeverity.EMERGENCY, DrawdownAction.REASSESS_STRATEGY

    def _get_message(
        self,
        severity: DrawdownSeverity,
        action: DrawdownAction,
        dd_pct: float
    ) -> str:
        """Get message for current drawdown state"""
        messages = {
            DrawdownSeverity.NORMAL: "✅ Trading normally. Drawdown under control.",
            DrawdownSeverity.CAUTION: f"⚠️  Drawdown at {dd_pct:.1f}%. REDUCE position size by 50%.",
            DrawdownSeverity.WARNING: f"🔴 Drawdown at {dd_pct:.1f}%. REDUCE position size by 75%. Review strategy.",
            DrawdownSeverity.CRITICAL: f"🚨 CRITICAL: Drawdown at {dd_pct:.1f}%. STOP trading for 1 week. Analyze what went wrong.",
            DrawdownSeverity.EMERGENCY: f"🆘 EMERGENCY: Drawdown at {dd_pct:.1f}%. STOP ALL TRADING. Reassess entire strategy."
        }

        return messages.get(severity, "Unknown state")

    def _initiate_trading_pause(self, action: DrawdownAction, current_time: datetime):
        """Initiate trading pause based on action"""
        self.trading_paused = True

        if action == DrawdownAction.STOP_1_DAY:
            self.pause_until = current_time + timedelta(days=1)

        elif action == DrawdownAction.STOP_1_WEEK:
            self.pause_until = current_time + timedelta(weeks=1)

        elif action == DrawdownAction.REASSESS_STRATEGY:
            # Indefinite pause - manual restart required
            self.pause_until = current_time + timedelta(days=30)

    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on drawdown

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check if trading is paused
        if self.trading_paused:
            if self.pause_until and datetime.now() < self.pause_until:
                remaining = self.pause_until - datetime.now()
                days = remaining.days
                hours = remaining.seconds // 3600

                return False, f"Trading paused due to drawdown. Resume in {days}d {hours}h"

            else:
                # Pause period expired - can resume
                self.trading_paused = False
                self.pause_until = None

        # Check current drawdown level
        if self.current_dd_pct >= 20:
            return False, "Emergency: Drawdown > 20%. Trading not allowed."

        elif self.current_dd_pct >= 15:
            return False, "Critical: Drawdown > 15%. Take a break and review."

        return True, "Drawdown within acceptable limits"

    def get_position_size_multiplier(self) -> float:
        """
        Get position size multiplier based on drawdown

        Returns:
            Multiplier (0.25 to 1.0)
        """
        if self.current_dd_pct < 5:
            return 1.0  # Normal size

        elif self.current_dd_pct < 10:
            return 0.5  # 50% reduction

        elif self.current_dd_pct < 15:
            return 0.25  # 75% reduction

        else:
            return 0.0  # No trading

    def get_drawdown_report(self) -> Dict:
        """
        Get comprehensive drawdown report

        Returns:
            Dictionary with drawdown analysis
        """
        if not self.dd_history:
            return {}

        # Calculate statistics
        all_dd = [entry['dd_pct'] for entry in self.dd_history]

        max_dd = max(all_dd) if all_dd else 0
        current_dd = self.current_dd_pct
        avg_dd = sum(all_dd) / len(all_dd) if all_dd else 0

        # Time in drawdown
        in_drawdown_count = sum(1 for dd in all_dd if dd > 0)
        total_entries = len(all_dd)
        time_in_dd_pct = (in_drawdown_count / total_entries * 100) if total_entries > 0 else 0

        # Recovery analysis
        recovery_status = "Recovered" if current_dd == 0 else "In Drawdown"

        return {
            'current_drawdown_pct': round(current_dd, 2),
            'max_drawdown_pct': round(max_dd, 2),
            'average_drawdown_pct': round(avg_dd, 2),
            'peak_capital': round(self.peak_capital, 2),
            'current_capital': round(self.current_capital, 2),
            'capital_lost': round(self.peak_capital - self.current_capital, 2),
            'recovery_needed': round(current_dd, 2),
            'recovery_status': recovery_status,
            'time_in_drawdown_pct': round(time_in_dd_pct, 2),
            'severity': self.current_severity.value,
            'trading_paused': self.trading_paused
        }

    def reset_peak(self):
        """Reset peak capital to current (manual recovery declaration)"""
        self.peak_capital = self.current_capital
        self.current_dd_pct = 0
        self.current_severity = DrawdownSeverity.NORMAL
        self.trading_paused = False
        self.pause_until = None

    def resume_trading(self):
        """Manually resume trading (use with caution)"""
        self.trading_paused = False
        self.pause_until = None

    def print_status(self):
        """Print formatted drawdown status"""
        status = self.update(self.current_capital)

        print("\n" + "=" * 70)
        print("DRAWDOWN MANAGEMENT STATUS")
        print("=" * 70)

        print(f"\nCapital Status:")
        print(f"  Peak Capital:    ₹{status['peak_capital']:,.2f}")
        print(f"  Current Capital: ₹{status['current_capital']:,.2f}")
        print(f"  Drawdown:        {status['drawdown_pct']:.2f}% (₹{status['drawdown_amount']:,.2f})")

        # Severity indicator
        severity_emoji = {
            'normal': '🟢',
            'caution': '🟡',
            'warning': '🟠',
            'critical': '🔴',
            'emergency': '🆘'
        }

        emoji = severity_emoji.get(status['severity'], '⚪')
        print(f"\nSeverity: {emoji} {status['severity'].upper()}")

        print(f"\nRecommended Action:")
        print(f"  {status['message']}")

        if status['trading_paused']:
            print(f"\n⛔ TRADING PAUSED")
            if status['pause_until']:
                print(f"  Resume at: {status['pause_until'].strftime('%Y-%m-%d %H:%M')}")

        # Position sizing
        multiplier = self.get_position_size_multiplier()
        print(f"\nPosition Size Multiplier: {multiplier:.0%}")

        print("\n" + "=" * 70)

    def get_recovery_plan(self) -> Dict:
        """
        Generate recovery plan based on current drawdown

        Returns:
            Dictionary with recovery recommendations
        """
        if self.current_dd_pct == 0:
            return {'message': 'No recovery needed - at peak capital'}

        # Calculate required return to recover
        required_return_pct = (self.peak_capital / self.current_capital - 1) * 100

        plan = {
            'current_dd_pct': round(self.current_dd_pct, 2),
            'capital_to_recover': round(self.peak_capital - self.current_capital, 2),
            'required_return_pct': round(required_return_pct, 2),
            'recommendations': []
        }

        # Generate recommendations based on severity
        if self.current_dd_pct < 5:
            plan['recommendations'] = [
                "Continue trading normally",
                "Maintain current strategy",
                "Monitor risk per trade"
            ]

        elif self.current_dd_pct < 10:
            plan['recommendations'] = [
                "Reduce position size by 50%",
                "Focus on high-probability setups only",
                "Review recent losing trades",
                "Tighten stop losses"
            ]

        elif self.current_dd_pct < 15:
            plan['recommendations'] = [
                "Reduce position size by 75%",
                "Take a break for 2-3 days",
                "Analyze what went wrong",
                "Backtest your strategy",
                "Consider paper trading to regain confidence"
            ]

        else:
            plan['recommendations'] = [
                "STOP all trading immediately",
                "Conduct full strategy review",
                "Analyze all losing trades",
                "Consider re-educating yourself",
                "Seek mentor feedback",
                "Start with paper trading when ready",
                f"You need {required_return_pct:.1f}% return to recover - be realistic"
            ]

        return plan

    def get_dd_history_df(self):
        """Get drawdown history as pandas DataFrame"""
        import pandas as pd

        if not self.dd_history:
            return pd.DataFrame()

        return pd.DataFrame(self.dd_history)
