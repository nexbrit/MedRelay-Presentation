"""
Performance Metrics Calculator for trading analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class PerformanceMetrics:
    """
    Calculate comprehensive performance metrics for trading strategies

    Includes:
    - Profitability metrics (Returns, CAGR, Profit Factor)
    - Risk metrics (Sharpe, Sortino, Max Drawdown)
    - Trade statistics (Win rate, Expectancy)
    - Consistency metrics (Monthly returns, Streaks)
    """

    def __init__(self, trades_df: pd.DataFrame = None):
        """
        Initialize performance calculator

        Args:
            trades_df: DataFrame with trade history
        """
        self.trades_df = trades_df
        self.metrics = {}

    def set_trades(self, trades_df: pd.DataFrame):
        """Set or update trades DataFrame"""
        self.trades_df = trades_df

    def calculate_all_metrics(self, initial_capital: float = 100000) -> Dict:
        """
        Calculate all performance metrics

        Args:
            initial_capital: Starting capital

        Returns:
            Dictionary with all metrics
        """
        if self.trades_df is None or self.trades_df.empty:
            return {}

        # Filter closed trades only
        closed_trades = self.trades_df[
            (self.trades_df['status'] == 'CLOSED') &
            (self.trades_df['pnl'].notna())
        ].copy()

        if closed_trades.empty:
            return {}

        self.metrics = {
            **self._calculate_profitability_metrics(closed_trades, initial_capital),
            **self._calculate_risk_metrics(closed_trades, initial_capital),
            **self._calculate_trade_statistics(closed_trades),
            **self._calculate_consistency_metrics(closed_trades),
            **self._calculate_execution_quality(closed_trades),
        }

        return self.metrics

    def _calculate_profitability_metrics(
        self,
        trades: pd.DataFrame,
        initial_capital: float
    ) -> Dict:
        """Calculate profitability metrics"""
        total_pnl = trades['pnl'].sum()
        total_return_pct = (total_pnl / initial_capital) * 100

        # Calculate CAGR
        trades_sorted = trades.sort_values('timestamp')
        if len(trades_sorted) > 0:
            start_date = pd.to_datetime(trades_sorted.iloc[0]['timestamp'])
            end_date = pd.to_datetime(trades_sorted.iloc[-1]['timestamp'])
            days = (end_date - start_date).days
            years = days / 365.25 if days > 0 else 1

            final_capital = initial_capital + total_pnl
            cagr = (((final_capital / initial_capital) ** (1 / years)) - 1) * 100 if years > 0 else 0
        else:
            cagr = 0

        # Profit factor
        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

        # Expectancy
        win_rate = self._calculate_win_rate(trades)
        avg_win = trades[trades['pnl'] > 0]['pnl'].mean() if len(trades[trades['pnl'] > 0]) > 0 else 0
        avg_loss = abs(trades[trades['pnl'] < 0]['pnl'].mean()) if len(trades[trades['pnl'] < 0]) > 0 else 0

        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)

        return {
            'total_pnl': round(total_pnl, 2),
            'total_return_pct': round(total_return_pct, 2),
            'cagr': round(cagr, 2),
            'profit_factor': round(profit_factor, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'expectancy': round(expectancy, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
        }

    def _calculate_risk_metrics(
        self,
        trades: pd.DataFrame,
        initial_capital: float
    ) -> Dict:
        """Calculate risk-adjusted metrics"""
        # Create equity curve
        trades_sorted = trades.sort_values('timestamp')
        equity_curve = initial_capital + trades_sorted['pnl'].cumsum()

        # Maximum drawdown
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max * 100
        max_drawdown = abs(drawdown.min())

        # Drawdown duration
        dd_duration = self._calculate_drawdown_duration(equity_curve)

        # Calculate returns for Sharpe/Sortino
        returns = trades_sorted['pnl'] / initial_capital

        # Sharpe Ratio (assuming 6% risk-free rate)
        risk_free_rate = 0.06 / 252  # Daily risk-free rate
        excess_returns = returns - risk_free_rate
        sharpe_ratio = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if len(excess_returns) > 0 and excess_returns.std() != 0 else 0

        # Sortino Ratio (only considers downside volatility)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino_ratio = (excess_returns.mean() / downside_std * np.sqrt(252)) if downside_std != 0 else 0

        # Calmar Ratio (Return / Max Drawdown)
        annual_return = trades_sorted['pnl'].sum() / initial_capital
        calmar_ratio = annual_return / (max_drawdown / 100) if max_drawdown != 0 else 0

        return {
            'max_drawdown_pct': round(max_drawdown, 2),
            'max_drawdown_duration_days': dd_duration,
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'calmar_ratio': round(calmar_ratio, 2),
        }

    def _calculate_trade_statistics(self, trades: pd.DataFrame) -> Dict:
        """Calculate trade statistics"""
        total_trades = len(trades)
        winning_trades = len(trades[trades['pnl'] > 0])
        losing_trades = len(trades[trades['pnl'] < 0])
        breakeven_trades = len(trades[trades['pnl'] == 0])

        win_rate = self._calculate_win_rate(trades)

        # Largest win/loss
        largest_win = trades['pnl'].max() if len(trades) > 0 else 0
        largest_loss = trades['pnl'].min() if len(trades) > 0 else 0

        # Average holding period
        avg_hold_time = trades['hold_time'].mean() if 'hold_time' in trades.columns and trades['hold_time'].notna().any() else 0

        # Winners vs Losers holding time
        winners = trades[trades['pnl'] > 0]
        losers = trades[trades['pnl'] < 0]

        avg_winner_hold_time = winners['hold_time'].mean() if len(winners) > 0 and 'hold_time' in winners.columns else 0
        avg_loser_hold_time = losers['hold_time'].mean() if len(losers) > 0 and 'hold_time' in losers.columns else 0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'breakeven_trades': breakeven_trades,
            'win_rate': round(win_rate, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2),
            'avg_hold_time_minutes': round(avg_hold_time, 2),
            'avg_winner_hold_time': round(avg_winner_hold_time, 2),
            'avg_loser_hold_time': round(avg_loser_hold_time, 2),
        }

    def _calculate_consistency_metrics(self, trades: pd.DataFrame) -> Dict:
        """Calculate consistency and streaks"""
        # Winning/Losing streaks
        winning_streak, losing_streak = self._calculate_streaks(trades)

        # Monthly returns
        trades_copy = trades.copy()
        trades_copy['timestamp'] = pd.to_datetime(trades_copy['timestamp'])
        trades_copy['month'] = trades_copy['timestamp'].dt.to_period('M')

        monthly_pnl = trades_copy.groupby('month')['pnl'].sum()
        winning_months = len(monthly_pnl[monthly_pnl > 0])
        losing_months = len(monthly_pnl[monthly_pnl < 0])
        total_months = len(monthly_pnl)

        return {
            'longest_winning_streak': winning_streak,
            'longest_losing_streak': losing_streak,
            'winning_months': winning_months,
            'losing_months': losing_months,
            'total_months': total_months,
            'monthly_win_rate': round((winning_months / total_months * 100) if total_months > 0 else 0, 2),
        }

    def _calculate_execution_quality(self, trades: pd.DataFrame) -> Dict:
        """Calculate execution quality metrics"""
        # Average slippage
        avg_slippage = trades['slippage'].mean() if 'slippage' in trades.columns and trades['slippage'].notna().any() else 0

        # Total commission
        total_commission = trades['commission'].sum() if 'commission' in trades.columns else 0

        return {
            'avg_slippage': round(avg_slippage, 4),
            'total_commission': round(total_commission, 2),
        }

    def _calculate_win_rate(self, trades: pd.DataFrame) -> float:
        """Calculate win rate percentage"""
        if len(trades) == 0:
            return 0
        winning_trades = len(trades[trades['pnl'] > 0])
        return (winning_trades / len(trades)) * 100

    def _calculate_drawdown_duration(self, equity_curve: pd.Series) -> int:
        """Calculate maximum drawdown duration in days"""
        running_max = equity_curve.cummax()
        is_drawdown = equity_curve < running_max

        if not is_drawdown.any():
            return 0

        # Find longest consecutive True sequence
        dd_periods = []
        current_period = 0

        for in_dd in is_drawdown:
            if in_dd:
                current_period += 1
            else:
                if current_period > 0:
                    dd_periods.append(current_period)
                current_period = 0

        if current_period > 0:
            dd_periods.append(current_period)

        return max(dd_periods) if dd_periods else 0

    def _calculate_streaks(self, trades: pd.DataFrame) -> Tuple[int, int]:
        """Calculate longest winning and losing streaks"""
        trades_sorted = trades.sort_values('timestamp')
        pnl_series = trades_sorted['pnl']

        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0

        for pnl in pnl_series:
            if pnl > 0:
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            elif pnl < 0:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
            else:  # breakeven
                current_win_streak = 0
                current_loss_streak = 0

        return max_win_streak, max_loss_streak

    def get_daily_summary(self, date: datetime = None) -> Dict:
        """
        Get performance summary for a specific day

        Args:
            date: Date to analyze (default: today)

        Returns:
            Dictionary with daily metrics
        """
        if self.trades_df is None or self.trades_df.empty:
            return {}

        if date is None:
            date = datetime.now()

        # Filter trades for the day
        trades_copy = self.trades_df.copy()
        trades_copy['timestamp'] = pd.to_datetime(trades_copy['timestamp'])

        daily_trades = trades_copy[
            (trades_copy['timestamp'].dt.date == date.date()) &
            (trades_copy['status'] == 'CLOSED')
        ]

        if daily_trades.empty:
            return {
                'date': date.date(),
                'total_trades': 0,
                'pnl': 0,
                'win_rate': 0,
            }

        return {
            'date': date.date(),
            'total_trades': len(daily_trades),
            'winning_trades': len(daily_trades[daily_trades['pnl'] > 0]),
            'losing_trades': len(daily_trades[daily_trades['pnl'] < 0]),
            'pnl': round(daily_trades['pnl'].sum(), 2),
            'win_rate': round(self._calculate_win_rate(daily_trades), 2),
            'largest_win': round(daily_trades['pnl'].max(), 2),
            'largest_loss': round(daily_trades['pnl'].min(), 2),
        }

    def get_weekly_summary(self) -> Dict:
        """Get performance summary for the current week"""
        if self.trades_df is None or self.trades_df.empty:
            return {}

        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())

        trades_copy = self.trades_df.copy()
        trades_copy['timestamp'] = pd.to_datetime(trades_copy['timestamp'])

        weekly_trades = trades_copy[
            (trades_copy['timestamp'] >= week_start) &
            (trades_copy['status'] == 'CLOSED')
        ]

        if weekly_trades.empty:
            return {'week_start': week_start.date(), 'total_trades': 0, 'pnl': 0}

        return {
            'week_start': week_start.date(),
            'total_trades': len(weekly_trades),
            'pnl': round(weekly_trades['pnl'].sum(), 2),
            'win_rate': round(self._calculate_win_rate(weekly_trades), 2),
        }

    def get_monthly_summary(self) -> Dict:
        """Get performance summary for the current month"""
        if self.trades_df is None or self.trades_df.empty:
            return {}

        today = datetime.now()
        month_start = today.replace(day=1)

        trades_copy = self.trades_df.copy()
        trades_copy['timestamp'] = pd.to_datetime(trades_copy['timestamp'])

        monthly_trades = trades_copy[
            (trades_copy['timestamp'] >= month_start) &
            (trades_copy['status'] == 'CLOSED')
        ]

        if monthly_trades.empty:
            return {'month': month_start.strftime('%B %Y'), 'total_trades': 0, 'pnl': 0}

        return {
            'month': month_start.strftime('%B %Y'),
            'total_trades': len(monthly_trades),
            'pnl': round(monthly_trades['pnl'].sum(), 2),
            'win_rate': round(self._calculate_win_rate(monthly_trades), 2),
            'profit_factor': self._calculate_profitability_metrics(
                monthly_trades, 100000
            )['profit_factor'],
        }

    def print_report(self):
        """Print formatted performance report"""
        if not self.metrics:
            print("No metrics available. Run calculate_all_metrics() first.")
            return

        print("\n" + "=" * 60)
        print("PERFORMANCE REPORT")
        print("=" * 60)

        print("\n📊 PROFITABILITY METRICS")
        print(f"  Total P&L:           ₹{self.metrics.get('total_pnl', 0):,.2f}")
        print(f"  Total Return:        {self.metrics.get('total_return_pct', 0):.2f}%")
        print(f"  CAGR:               {self.metrics.get('cagr', 0):.2f}%")
        print(f"  Profit Factor:       {self.metrics.get('profit_factor', 0):.2f}")
        print(f"  Expectancy:         ₹{self.metrics.get('expectancy', 0):.2f}")

        print("\n⚠️  RISK METRICS")
        print(f"  Max Drawdown:        {self.metrics.get('max_drawdown_pct', 0):.2f}%")
        print(f"  DD Duration:         {self.metrics.get('max_drawdown_duration_days', 0)} trades")
        print(f"  Sharpe Ratio:        {self.metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  Sortino Ratio:       {self.metrics.get('sortino_ratio', 0):.2f}")
        print(f"  Calmar Ratio:        {self.metrics.get('calmar_ratio', 0):.2f}")

        print("\n📈 TRADE STATISTICS")
        print(f"  Total Trades:        {self.metrics.get('total_trades', 0)}")
        print(f"  Winners:            {self.metrics.get('winning_trades', 0)}")
        print(f"  Losers:             {self.metrics.get('losing_trades', 0)}")
        print(f"  Win Rate:           {self.metrics.get('win_rate', 0):.2f}%")
        print(f"  Avg Win:            ₹{self.metrics.get('avg_win', 0):.2f}")
        print(f"  Avg Loss:           ₹{self.metrics.get('avg_loss', 0):.2f}")
        print(f"  Largest Win:        ₹{self.metrics.get('largest_win', 0):.2f}")
        print(f"  Largest Loss:       ₹{self.metrics.get('largest_loss', 0):.2f}")

        print("\n🔄 CONSISTENCY METRICS")
        print(f"  Winning Streak:      {self.metrics.get('longest_winning_streak', 0)}")
        print(f"  Losing Streak:       {self.metrics.get('longest_losing_streak', 0)}")
        print(f"  Winning Months:      {self.metrics.get('winning_months', 0)}/{self.metrics.get('total_months', 0)}")

        print("\n" + "=" * 60)
