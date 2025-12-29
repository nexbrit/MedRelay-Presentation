"""
Performance Metrics Calculator
Calculate comprehensive trading performance metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Calculate professional-grade performance metrics
    Used by hedge funds and prop trading firms
    """

    def __init__(self, risk_free_rate: float = 6.0):
        """
        Initialize performance metrics calculator

        Args:
            risk_free_rate: Annual risk-free rate (%) - typically 10-year govt bond yield
        """
        self.risk_free_rate = risk_free_rate / 100  # Convert to decimal

    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe Ratio

        Sharpe = (Return - Risk Free Rate) / Standard Deviation

        Args:
            returns: Series of period returns
            periods_per_year: Trading periods per year (252 for daily, 52 for weekly)

        Returns:
            Sharpe ratio
        """
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / periods_per_year)
        sharpe = np.sqrt(periods_per_year) * (excess_returns.mean() / excess_returns.std())

        return sharpe if not np.isnan(sharpe) else 0.0

    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sortino Ratio (like Sharpe, but only considers downside volatility)

        Sortino = (Return - Risk Free Rate) / Downside Deviation

        Args:
            returns: Series of period returns
            periods_per_year: Trading periods per year

        Returns:
            Sortino ratio
        """
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / periods_per_year)

        # Only consider negative returns for downside deviation
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return float('inf')  # No downside = infinite Sortino

        downside_std = downside_returns.std()

        sortino = np.sqrt(periods_per_year) * (excess_returns.mean() / downside_std)

        return sortino if not np.isnan(sortino) else 0.0

    def calculate_calmar_ratio(
        self,
        total_return: float,
        max_drawdown: float,
        years: float = 1.0
    ) -> float:
        """
        Calculate Calmar Ratio

        Calmar = Annualized Return / Maximum Drawdown

        Args:
            total_return: Total return as decimal
            max_drawdown: Maximum drawdown as decimal
            years: Number of years in the period

        Returns:
            Calmar ratio
        """
        if max_drawdown == 0:
            return float('inf')

        annualized_return = (1 + total_return) ** (1/years) - 1

        calmar = annualized_return / max_drawdown

        return calmar

    def calculate_max_drawdown(self, equity_curve: pd.Series) -> Dict:
        """
        Calculate maximum drawdown and related metrics

        Args:
            equity_curve: Series of equity values over time

        Returns:
            Dictionary with drawdown metrics
        """
        # Calculate running maximum
        running_max = equity_curve.expanding().max()

        # Calculate drawdown at each point
        drawdown = (equity_curve - running_max) / running_max

        # Maximum drawdown
        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()

        # Find peak before max drawdown
        peak_idx = equity_curve[:max_dd_idx].idxmax()
        peak_value = equity_curve[peak_idx]

        # Find recovery point (when equity exceeds peak again)
        recovery_idx = None
        recovery_days = None

        if max_dd_idx < len(equity_curve) - 1:
            future_equity = equity_curve[max_dd_idx:]
            recovery_mask = future_equity >= peak_value

            if recovery_mask.any():
                recovery_idx = recovery_mask.idxmax()
                recovery_days = (recovery_idx - peak_idx).days

        return {
            'max_drawdown': abs(max_dd),
            'max_drawdown_percent': abs(max_dd) * 100,
            'peak_date': peak_idx,
            'trough_date': max_dd_idx,
            'recovery_date': recovery_idx,
            'drawdown_duration_days': (max_dd_idx - peak_idx).days if peak_idx else 0,
            'recovery_duration_days': recovery_days,
            'peak_value': peak_value,
            'trough_value': equity_curve[max_dd_idx]
        }

    def calculate_win_streak_stats(self, trades: List[Dict]) -> Dict:
        """
        Calculate winning and losing streak statistics

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary with streak statistics
        """
        if not trades:
            return {}

        # Get win/loss sequence
        results = [1 if t['net_pnl'] > 0 else -1 for t in trades]

        # Calculate streaks
        current_streak = 1
        max_win_streak = 0
        max_loss_streak = 0
        current_type = results[0]

        for i in range(1, len(results)):
            if results[i] == current_type:
                current_streak += 1
            else:
                if current_type == 1:
                    max_win_streak = max(max_win_streak, current_streak)
                else:
                    max_loss_streak = max(max_loss_streak, current_streak)

                current_type = results[i]
                current_streak = 1

        # Check final streak
        if current_type == 1:
            max_win_streak = max(max_win_streak, current_streak)
        else:
            max_loss_streak = max(max_loss_streak, current_streak)

        return {
            'max_consecutive_wins': max_win_streak,
            'max_consecutive_losses': max_loss_streak,
            'current_streak': current_streak,
            'current_streak_type': 'WIN' if current_type == 1 else 'LOSS'
        }

    def calculate_monthly_returns(self, equity_curve: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate monthly returns for heatmap visualization

        Args:
            equity_curve: DataFrame with timestamp and capital columns

        Returns:
            DataFrame with monthly returns
        """
        df = equity_curve.copy()
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month

        # Get capital at end of each month
        monthly = df.groupby(['year', 'month'])['capital'].last()

        # Calculate monthly returns
        monthly_returns = monthly.pct_change()

        # Pivot for heatmap
        heatmap = monthly_returns.reset_index()
        heatmap['month_name'] = pd.to_datetime(heatmap['month'], format='%m').dt.month_name()

        pivot = heatmap.pivot(index='year', columns='month_name', values=0)

        return pivot

    def calculate_comprehensive_metrics(
        self,
        trades: List[Dict],
        equity_curve: List[Dict],
        initial_capital: float
    ) -> Dict:
        """
        Calculate all performance metrics in one go

        Args:
            trades: List of completed trades
            equity_curve: List of equity points
            initial_capital: Starting capital

        Returns:
            Comprehensive metrics dictionary
        """
        if not trades or not equity_curve:
            return {'error': 'No trades or equity data'}

        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_curve)

        # Basic metrics
        final_capital = equity_df['capital'].iloc[-1]
        total_return = (final_capital - initial_capital) / initial_capital

        # Calculate returns series
        equity_df['returns'] = equity_df['capital'].pct_change()
        returns = equity_df['returns'].dropna()

        # Risk-adjusted returns
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)

        # Drawdown metrics
        dd_metrics = self.calculate_max_drawdown(equity_df.set_index('timestamp')['capital'])
        calmar = self.calculate_calmar_ratio(
            total_return,
            dd_metrics['max_drawdown'],
            years=1.0  # Adjust based on backtest period
        )

        # Trade statistics
        winning_trades = trades_df[trades_df['net_pnl'] > 0]
        losing_trades = trades_df[trades_df['net_pnl'] < 0]

        win_rate = (len(winning_trades) / len(trades_df)) * 100
        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0

        # Profit factor
        gross_profit = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Expectancy (average profit per trade)
        expectancy = trades_df['net_pnl'].mean()

        # Win/Loss streak
        streak_stats = self.calculate_win_streak_stats(trades)

        # Hold time analysis
        avg_hold_time_winners = winning_trades['hold_time_hours'].mean() if len(winning_trades) > 0 else 0
        avg_hold_time_losers = losing_trades['hold_time_hours'].mean() if len(losing_trades) > 0 else 0

        # Risk metrics
        avg_risk_per_trade = trades_df['costs'].sum() / len(trades_df)

        # Compile comprehensive metrics
        metrics = {
            # Capital metrics
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_pnl': final_capital - initial_capital,
            'total_return_percent': total_return * 100,

            # Risk-adjusted returns
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'calmar_ratio': calmar,

            # Drawdown
            **dd_metrics,

            # Trade statistics
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'loss_rate': 100 - win_rate,

            # P&L statistics
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': winning_trades['net_pnl'].max() if len(winning_trades) > 0 else 0,
            'largest_loss': losing_trades['net_pnl'].min() if len(losing_trades) > 0 else 0,

            # Hold time
            'avg_hold_time_hours': trades_df['hold_time_hours'].mean(),
            'avg_hold_time_winners': avg_hold_time_winners,
            'avg_hold_time_losers': avg_hold_time_losers,
            'hold_time_ratio': (avg_hold_time_winners / avg_hold_time_losers
                                if avg_hold_time_losers > 0 else 0),

            # Streaks
            **streak_stats,

            # Cost analysis
            'total_costs': trades_df['costs'].sum(),
            'avg_cost_per_trade': avg_risk_per_trade,
            'costs_as_percent_of_profit': (trades_df['costs'].sum() / gross_profit * 100
                                            if gross_profit > 0 else 0),

            # Consistency metrics
            'profitable_months': self._count_profitable_periods(equity_df, 'M'),
            'total_months': self._count_total_periods(equity_df, 'M'),

            # Recovery metrics
            'recovery_factor': abs(total_return / dd_metrics['max_drawdown']
                                    if dd_metrics['max_drawdown'] != 0 else float('inf')),
        }

        return metrics

    def _count_profitable_periods(self, equity_df: pd.DataFrame, period: str = 'M') -> int:
        """Count number of profitable periods"""
        resampled = equity_df.set_index('timestamp')['capital'].resample(period).last()
        returns = resampled.pct_change().dropna()
        return (returns > 0).sum()

    def _count_total_periods(self, equity_df: pd.DataFrame, period: str = 'M') -> int:
        """Count total number of periods"""
        resampled = equity_df.set_index('timestamp')['capital'].resample(period).last()
        return len(resampled) - 1  # -1 for the pct_change

    def generate_performance_report(self, metrics: Dict) -> str:
        """
        Generate human-readable performance report

        Args:
            metrics: Dictionary of performance metrics

        Returns:
            Formatted report string
        """
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                   BACKTEST PERFORMANCE REPORT                 ║
╠══════════════════════════════════════════════════════════════╣

📊 CAPITAL PERFORMANCE
   Initial Capital:     ₹{metrics['initial_capital']:>15,.2f}
   Final Capital:       ₹{metrics['final_capital']:>15,.2f}
   Total P&L:           ₹{metrics['total_pnl']:>15,.2f}
   Total Return:        {metrics['total_return_percent']:>15.2f}%

📈 RISK-ADJUSTED RETURNS
   Sharpe Ratio:        {metrics['sharpe_ratio']:>15.2f}  {'✅ Excellent' if metrics['sharpe_ratio'] > 1.5 else '⚠️  Needs Work' if metrics['sharpe_ratio'] > 1.0 else '❌ Poor'}
   Sortino Ratio:       {metrics['sortino_ratio']:>15.2f}
   Calmar Ratio:        {metrics['calmar_ratio']:>15.2f}

📉 DRAWDOWN ANALYSIS
   Maximum Drawdown:    {metrics['max_drawdown_percent']:>15.2f}%  {'✅ Good' if metrics['max_drawdown_percent'] < 15 else '⚠️  Moderate' if metrics['max_drawdown_percent'] < 25 else '❌ High'}
   Drawdown Duration:   {metrics['drawdown_duration_days']:>15} days
   Recovery Duration:   {metrics.get('recovery_duration_days', 'N/A'):>15} days
   Recovery Factor:     {metrics['recovery_factor']:>15.2f}

🎯 TRADE STATISTICS
   Total Trades:        {metrics['total_trades']:>15}
   Winning Trades:      {metrics['winning_trades']:>15} ({metrics['win_rate']:.1f}%)
   Losing Trades:       {metrics['losing_trades']:>15} ({metrics['loss_rate']:.1f}%)
   Win Rate:            {metrics['win_rate']:>15.2f}%  {'✅ Good' if metrics['win_rate'] > 50 else '⚠️  Acceptable' if metrics['win_rate'] > 40 else '❌ Low'}

💰 PROFIT ANALYSIS
   Gross Profit:        ₹{metrics['gross_profit']:>15,.2f}
   Gross Loss:          ₹{metrics['gross_loss']:>15,.2f}
   Profit Factor:       {metrics['profit_factor']:>15.2f}  {'✅ Excellent' if metrics['profit_factor'] > 2.0 else '⚠️  Good' if metrics['profit_factor'] > 1.5 else '❌ Poor'}
   Expectancy:          ₹{metrics['expectancy']:>15,.2f}

   Average Win:         ₹{metrics['avg_win']:>15,.2f}
   Average Loss:        ₹{metrics['avg_loss']:>15,.2f}
   Win/Loss Ratio:      {abs(metrics['avg_win']/metrics['avg_loss']) if metrics['avg_loss'] != 0 else 0:>15.2f}

   Largest Win:         ₹{metrics['largest_win']:>15,.2f}
   Largest Loss:        ₹{metrics['largest_loss']:>15,.2f}

⏱️  HOLD TIME ANALYSIS
   Avg Hold (All):      {metrics['avg_hold_time_hours']:>15.2f} hours
   Avg Hold (Winners):  {metrics['avg_hold_time_winners']:>15.2f} hours
   Avg Hold (Losers):   {metrics['avg_hold_time_losers']:>15.2f} hours
   Ratio (W/L):         {metrics['hold_time_ratio']:>15.2f}  {'✅ Good - Cutting losers fast' if metrics['hold_time_ratio'] > 1.5 else '⚠️  Warning - Holding losers too long' if metrics['hold_time_ratio'] < 0.7 else '➖ Neutral'}

🎲 STREAKS
   Max Winning Streak:  {metrics['max_consecutive_wins']:>15}
   Max Losing Streak:   {metrics['max_consecutive_losses']:>15}
   Current Streak:      {metrics['current_streak']:>15} ({metrics['current_streak_type']})

💸 COST ANALYSIS
   Total Costs:         ₹{metrics['total_costs']:>15,.2f}
   Avg Cost/Trade:      ₹{metrics['avg_cost_per_trade']:>15,.2f}
   Costs % of Profit:   {metrics['costs_as_percent_of_profit']:>15.2f}%

📅 CONSISTENCY
   Profitable Months:   {metrics['profitable_months']:>15} / {metrics['total_months']:>15}
   Monthly Win Rate:    {(metrics['profitable_months']/metrics['total_months']*100) if metrics['total_months'] > 0 else 0:>15.1f}%

╚══════════════════════════════════════════════════════════════╝

🎯 OVERALL GRADE: {self._calculate_grade(metrics)}

💡 KEY TAKEAWAYS:
{self._generate_insights(metrics)}
"""
        return report

    def _calculate_grade(self, metrics: Dict) -> str:
        """Calculate overall strategy grade"""
        score = 0

        # Sharpe ratio (max 30 points)
        if metrics['sharpe_ratio'] > 2.0:
            score += 30
        elif metrics['sharpe_ratio'] > 1.5:
            score += 25
        elif metrics['sharpe_ratio'] > 1.0:
            score += 15
        elif metrics['sharpe_ratio'] > 0.5:
            score += 5

        # Win rate (max 20 points)
        if metrics['win_rate'] > 55:
            score += 20
        elif metrics['win_rate'] > 50:
            score += 15
        elif metrics['win_rate'] > 45:
            score += 10
        elif metrics['win_rate'] > 40:
            score += 5

        # Profit factor (max 25 points)
        if metrics['profit_factor'] > 2.5:
            score += 25
        elif metrics['profit_factor'] > 2.0:
            score += 20
        elif metrics['profit_factor'] > 1.5:
            score += 10
        elif metrics['profit_factor'] > 1.2:
            score += 5

        # Max drawdown (max 25 points)
        if metrics['max_drawdown_percent'] < 10:
            score += 25
        elif metrics['max_drawdown_percent'] < 15:
            score += 20
        elif metrics['max_drawdown_percent'] < 20:
            score += 10
        elif metrics['max_drawdown_percent'] < 30:
            score += 5

        # Grade based on score
        if score >= 85:
            return "A+ (EXCELLENT - Trade with confidence)"
        elif score >= 75:
            return "A (VERY GOOD - Minor tweaks needed)"
        elif score >= 65:
            return "B+ (GOOD - Some improvements needed)"
        elif score >= 55:
            return "B (ACCEPTABLE - Requires optimization)"
        elif score >= 45:
            return "C (MARGINAL - Needs significant work)"
        else:
            return "F (FAIL - Do NOT trade this strategy)"

    def _generate_insights(self, metrics: Dict) -> str:
        """Generate key insights from metrics"""
        insights = []

        # Sharpe ratio insights
        if metrics['sharpe_ratio'] > 1.5:
            insights.append("✅ Excellent risk-adjusted returns (Sharpe > 1.5)")
        elif metrics['sharpe_ratio'] < 1.0:
            insights.append("⚠️  Low risk-adjusted returns - strategy needs optimization")

        # Win rate insights
        if metrics['win_rate'] < 40:
            insights.append("⚠️  Low win rate - ensure average wins are much larger than losses")
        elif metrics['win_rate'] > 60:
            insights.append("✅ High win rate - profitable strategy foundation")

        # Drawdown insights
        if metrics['max_drawdown_percent'] > 20:
            insights.append("❌ High drawdown - reduce position sizes or improve stop losses")
        elif metrics['max_drawdown_percent'] < 12:
            insights.append("✅ Excellent drawdown control")

        # Hold time insights
        if metrics['hold_time_ratio'] < 0.8:
            insights.append("⚠️  Holding losers longer than winners - cut losses faster!")
        elif metrics['hold_time_ratio'] > 1.5:
            insights.append("✅ Good discipline - cutting losses quickly")

        # Profit factor insights
        if metrics['profit_factor'] < 1.5:
            insights.append("⚠️  Profit factor < 1.5 - strategy barely profitable after costs")
        elif metrics['profit_factor'] > 2.0:
            insights.append("✅ Excellent profit factor (> 2.0)")

        # Cost insights
        if metrics['costs_as_percent_of_profit'] > 30:
            insights.append("⚠️  High costs eating into profits - consider reducing trade frequency")

        return '\n'.join(f"   {insight}" for insight in insights)
