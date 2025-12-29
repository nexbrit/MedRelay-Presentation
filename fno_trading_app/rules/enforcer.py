"""
Trading Rules Enforcer - Hard-coded discipline

Prevents emotional and impulsive trading decisions
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple, Optional
from enum import Enum


class RuleViolation(Enum):
    """Rule violation types"""
    MAX_TRADES_EXCEEDED = "max_trades_exceeded"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    TIME_RESTRICTION = "time_restriction"
    PORTFOLIO_HEAT_EXCEEDED = "portfolio_heat_exceeded"
    WEEKEND_TRADING = "weekend_trading"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    REVENGE_TRADING = "revenge_trading"


class TradingRulesEnforcer:
    """
    Enforce trading rules to prevent emotional and impulsive decisions

    Rules:
    - Max trades per day
    - Stop after consecutive losses
    - Time-based restrictions
    - Daily loss limits
    - Mandatory breaks
    - Prevent revenge trading
    """

    def __init__(self, rules_config: Dict = None):
        """
        Initialize trading rules enforcer

        Args:
            rules_config: Dictionary with rule configurations
        """
        # Default rules
        self.rules = {
            'max_trades_per_day': 5,
            'max_consecutive_losses': 3,
            'no_trade_first_15min': True,
            'no_trade_last_15min': True,
            'max_portfolio_heat': 6.0,
            'max_daily_loss': 5000,  # In rupees
            'mandatory_weekend': True,
            'revenge_trading_cooldown_minutes': 60,
            'min_time_between_trades_minutes': 5,
        }

        # Override with custom config
        if rules_config:
            self.rules.update(rules_config)

        # Trading stats (reset daily)
        self.daily_stats = {
            'date': datetime.now().date(),
            'trades_count': 0,
            'consecutive_losses': 0,
            'consecutive_wins': 0,
            'last_trade_time': None,
            'last_trade_result': None,  # 'WIN' or 'LOSS'
            'daily_pnl': 0.0,
            'last_loss_time': None,
        }

        self.violations = []

    def can_trade(
        self,
        current_time: datetime = None,
        portfolio_heat: float = 0
    ) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on all rules

        Args:
            current_time: Current datetime (defaults to now)
            portfolio_heat: Current portfolio heat percentage

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        if current_time is None:
            current_time = datetime.now()

        # Reset stats if new day
        self._check_and_reset_daily_stats(current_time)

        # Check each rule
        checks = [
            self._check_max_trades_per_day(),
            self._check_consecutive_losses(),
            self._check_time_restrictions(current_time),
            self._check_portfolio_heat(portfolio_heat),
            self._check_weekend_restriction(current_time),
            self._check_daily_loss_limit(),
            self._check_revenge_trading(current_time),
            self._check_min_time_between_trades(current_time),
        ]

        # Return first failed check
        for allowed, reason in checks:
            if not allowed:
                return False, reason

        return True, "All checks passed - OK to trade"

    def _check_max_trades_per_day(self) -> Tuple[bool, str]:
        """Check if max daily trades limit reached"""
        if self.daily_stats['trades_count'] >= self.rules['max_trades_per_day']:
            return False, f"Maximum {self.rules['max_trades_per_day']} trades per day reached"
        return True, "OK"

    def _check_consecutive_losses(self) -> Tuple[bool, str]:
        """Check for consecutive losses"""
        if self.daily_stats['consecutive_losses'] >= self.rules['max_consecutive_losses']:
            return False, f"Stop trading after {self.rules['max_consecutive_losses']} consecutive losses. Take a break!"
        return True, "OK"

    def _check_time_restrictions(self, current_time: datetime) -> Tuple[bool, str]:
        """Check time-based trading restrictions"""
        current_time_only = current_time.time()

        # Market hours: 9:15 AM to 3:30 PM IST
        market_open = time(9, 15)
        market_close = time(15, 30)

        # Check if market is open
        if current_time_only < market_open:
            return False, "Market not open yet (opens at 9:15 AM)"

        if current_time_only > market_close:
            return False, "Market closed (closes at 3:30 PM)"

        # Avoid first 15 minutes
        if self.rules['no_trade_first_15min']:
            no_trade_until = time(9, 30)
            if market_open <= current_time_only < no_trade_until:
                return False, "Avoid trading in first 15 minutes (9:15-9:30 AM)"

        # Avoid last 15 minutes
        if self.rules['no_trade_last_15min']:
            no_trade_after = time(15, 15)
            if no_trade_after < current_time_only <= market_close:
                return False, "Avoid trading in last 15 minutes (3:15-3:30 PM)"

        return True, "OK"

    def _check_portfolio_heat(self, portfolio_heat: float) -> Tuple[bool, str]:
        """Check portfolio heat limit"""
        if portfolio_heat >= self.rules['max_portfolio_heat']:
            return False, f"Portfolio heat {portfolio_heat:.1f}% exceeds max {self.rules['max_portfolio_heat']:.1f}%"
        return True, "OK"

    def _check_weekend_restriction(self, current_time: datetime) -> Tuple[bool, str]:
        """Check weekend restriction"""
        if self.rules['mandatory_weekend']:
            # Saturday = 5, Sunday = 6
            if current_time.weekday() >= 5:
                return False, "No trading on weekends. Take a break!"
        return True, "OK"

    def _check_daily_loss_limit(self) -> Tuple[bool, str]:
        """Check if daily loss limit exceeded"""
        if self.daily_stats['daily_pnl'] <= -self.rules['max_daily_loss']:
            return False, f"Daily loss limit of ₹{self.rules['max_daily_loss']:,.0f} reached. Stop trading for today."
        return True, "OK"

    def _check_revenge_trading(self, current_time: datetime) -> Tuple[bool, str]:
        """Check for potential revenge trading"""
        last_loss_time = self.daily_stats.get('last_loss_time')

        if last_loss_time:
            cooldown_minutes = self.rules['revenge_trading_cooldown_minutes']
            time_since_loss = (current_time - last_loss_time).total_seconds() / 60

            if time_since_loss < cooldown_minutes:
                remaining = int(cooldown_minutes - time_since_loss)
                return False, f"Wait {remaining} minutes after a loss to avoid revenge trading"

        return True, "OK"

    def _check_min_time_between_trades(self, current_time: datetime) -> Tuple[bool, str]:
        """Check minimum time between trades"""
        last_trade_time = self.daily_stats.get('last_trade_time')

        if last_trade_time:
            min_minutes = self.rules['min_time_between_trades_minutes']
            time_since_trade = (current_time - last_trade_time).total_seconds() / 60

            if time_since_trade < min_minutes:
                remaining = int(min_minutes - time_since_trade)
                return False, f"Wait {remaining} more minutes before next trade"

        return True, "OK"

    def record_trade(
        self,
        pnl: float,
        trade_time: datetime = None
    ):
        """
        Record a trade and update stats

        Args:
            pnl: Trade P&L
            trade_time: Trade timestamp (defaults to now)
        """
        if trade_time is None:
            trade_time = datetime.now()

        # Reset if new day
        self._check_and_reset_daily_stats(trade_time)

        # Update trade count
        self.daily_stats['trades_count'] += 1
        self.daily_stats['last_trade_time'] = trade_time
        self.daily_stats['daily_pnl'] += pnl

        # Update win/loss streaks
        if pnl > 0:
            self.daily_stats['last_trade_result'] = 'WIN'
            self.daily_stats['consecutive_wins'] += 1
            self.daily_stats['consecutive_losses'] = 0
        elif pnl < 0:
            self.daily_stats['last_trade_result'] = 'LOSS'
            self.daily_stats['consecutive_losses'] += 1
            self.daily_stats['consecutive_wins'] = 0
            self.daily_stats['last_loss_time'] = trade_time
        else:
            # Breakeven
            self.daily_stats['consecutive_wins'] = 0
            self.daily_stats['consecutive_losses'] = 0

    def _check_and_reset_daily_stats(self, current_time: datetime):
        """Reset stats if new day"""
        current_date = current_time.date()

        if self.daily_stats['date'] != current_date:
            self.daily_stats = {
                'date': current_date,
                'trades_count': 0,
                'consecutive_losses': 0,
                'consecutive_wins': 0,
                'last_trade_time': None,
                'last_trade_result': None,
                'daily_pnl': 0.0,
                'last_loss_time': None,
            }

    def get_daily_summary(self) -> Dict:
        """Get summary of daily trading stats"""
        return {
            'date': self.daily_stats['date'],
            'trades_taken': self.daily_stats['trades_count'],
            'trades_remaining': max(0, self.rules['max_trades_per_day'] - self.daily_stats['trades_count']),
            'consecutive_wins': self.daily_stats['consecutive_wins'],
            'consecutive_losses': self.daily_stats['consecutive_losses'],
            'daily_pnl': round(self.daily_stats['daily_pnl'], 2),
            'loss_limit_remaining': round(self.rules['max_daily_loss'] + self.daily_stats['daily_pnl'], 2),
        }

    def override_rule(self, rule_name: str, new_value):
        """
        Override a specific rule

        Args:
            rule_name: Name of the rule to override
            new_value: New value for the rule
        """
        if rule_name in self.rules:
            old_value = self.rules[rule_name]
            self.rules[rule_name] = new_value
            print(f"Rule '{rule_name}' changed from {old_value} to {new_value}")
        else:
            print(f"Warning: Rule '{rule_name}' not found")

    def add_custom_rule(
        self,
        rule_name: str,
        check_function,
        description: str
    ):
        """
        Add custom rule with check function

        Args:
            rule_name: Name for the rule
            check_function: Function that returns (allowed: bool, reason: str)
            description: Rule description
        """
        # Store custom rule
        if not hasattr(self, 'custom_rules'):
            self.custom_rules = {}

        self.custom_rules[rule_name] = {
            'check': check_function,
            'description': description
        }

    def get_all_rules(self) -> Dict:
        """Get all active rules"""
        return self.rules.copy()

    def print_rules_summary(self):
        """Print formatted summary of all rules"""
        print("\n" + "=" * 70)
        print("TRADING RULES ENFORCER")
        print("=" * 70)

        print("\n📋 ACTIVE RULES:")

        print(f"\n  1. Max Trades Per Day: {self.rules['max_trades_per_day']}")
        print(f"  2. Max Consecutive Losses: {self.rules['max_consecutive_losses']}")
        print(f"  3. No Trade First 15 Min: {self.rules['no_trade_first_15min']}")
        print(f"  4. No Trade Last 15 Min: {self.rules['no_trade_last_15min']}")
        print(f"  5. Max Portfolio Heat: {self.rules['max_portfolio_heat']:.1f}%")
        print(f"  6. Max Daily Loss: ₹{self.rules['max_daily_loss']:,.0f}")
        print(f"  7. Mandatory Weekend: {self.rules['mandatory_weekend']}")
        print(f"  8. Revenge Trading Cooldown: {self.rules['revenge_trading_cooldown_minutes']} min")
        print(f"  9. Min Time Between Trades: {self.rules['min_time_between_trades_minutes']} min")

        print("\n📊 TODAY'S STATS:")
        summary = self.get_daily_summary()

        print(f"  Trades: {summary['trades_taken']}/{self.rules['max_trades_per_day']}")
        print(f"  Consecutive Wins: {summary['consecutive_wins']}")
        print(f"  Consecutive Losses: {summary['consecutive_losses']}")
        print(f"  Daily P&L: ₹{summary['daily_pnl']:,.2f}")

        # Color-code loss limit
        loss_limit = summary['loss_limit_remaining']
        if loss_limit > 2500:
            status = "🟢 Healthy"
        elif loss_limit > 1000:
            status = "🟡 Caution"
        else:
            status = "🔴 Warning"

        print(f"  Loss Limit Remaining: ₹{loss_limit:,.2f} {status}")

        print("\n" + "=" * 70)

    def reset_daily_stats(self):
        """Manually reset daily stats"""
        self.daily_stats = {
            'date': datetime.now().date(),
            'trades_count': 0,
            'consecutive_losses': 0,
            'consecutive_wins': 0,
            'last_trade_time': None,
            'last_trade_result': None,
            'daily_pnl': 0.0,
            'last_loss_time': None,
        }

    def get_trading_status(self) -> Dict:
        """
        Get current trading status and recommendations

        Returns:
            Dictionary with trading status
        """
        allowed, reason = self.can_trade()

        status = {
            'can_trade': allowed,
            'reason': reason,
            'daily_stats': self.get_daily_summary(),
            'recommendations': []
        }

        # Add recommendations
        if self.daily_stats['consecutive_losses'] >= 2:
            status['recommendations'].append("Consider reducing position size - on losing streak")

        if self.daily_stats['trades_count'] >= self.rules['max_trades_per_day'] - 1:
            status['recommendations'].append("Last trade of the day - make it count!")

        if self.daily_stats['daily_pnl'] < 0:
            status['recommendations'].append("You're down for the day - trade defensively")

        if self.daily_stats['consecutive_wins'] >= 3:
            status['recommendations'].append("Great streak! But don't get overconfident")

        return status
