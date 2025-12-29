"""
Performance Visualizations using Plotly
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px


class PerformanceVisualizer:
    """
    Create interactive performance visualizations

    Charts:
    - Equity curve with drawdown overlay
    - Monthly returns heatmap
    - Win rate by time of day
    - P&L distribution histogram
    - Holding period vs P&L scatter plot
    """

    def __init__(self, trades_df: pd.DataFrame = None):
        """
        Initialize visualizer

        Args:
            trades_df: DataFrame with trade history
        """
        self.trades_df = trades_df

    def set_trades(self, trades_df: pd.DataFrame):
        """Set or update trades DataFrame"""
        self.trades_df = trades_df

    def plot_equity_curve(
        self,
        initial_capital: float = 100000,
        show_drawdown: bool = True,
        save_html: str = None
    ) -> go.Figure:
        """
        Plot equity curve with optional drawdown overlay

        Args:
            initial_capital: Starting capital
            show_drawdown: Whether to show drawdown subplot
            save_html: Path to save HTML file

        Returns:
            Plotly figure object
        """
        if self.trades_df is None or self.trades_df.empty:
            return go.Figure()

        # Filter closed trades and sort by timestamp
        trades = self.trades_df[
            (self.trades_df['status'] == 'CLOSED') &
            (self.trades_df['pnl'].notna())
        ].copy()

        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        trades = trades.sort_values('timestamp')

        # Calculate equity curve
        trades['equity'] = initial_capital + trades['pnl'].cumsum()

        # Calculate drawdown
        trades['running_max'] = trades['equity'].cummax()
        trades['drawdown_pct'] = (trades['equity'] - trades['running_max']) / trades['running_max'] * 100

        # Create figure
        if show_drawdown:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=('Equity Curve', 'Drawdown %'),
                row_heights=[0.7, 0.3]
            )

            # Equity curve
            fig.add_trace(
                go.Scatter(
                    x=trades['timestamp'],
                    y=trades['equity'],
                    mode='lines',
                    name='Equity',
                    line=dict(color='#2E86AB', width=2),
                    hovertemplate='%{y:,.0f}<extra></extra>'
                ),
                row=1, col=1
            )

            # Baseline
            fig.add_trace(
                go.Scatter(
                    x=trades['timestamp'],
                    y=[initial_capital] * len(trades),
                    mode='lines',
                    name='Initial Capital',
                    line=dict(color='gray', width=1, dash='dash'),
                    hovertemplate='%{y:,.0f}<extra></extra>'
                ),
                row=1, col=1
            )

            # Drawdown
            fig.add_trace(
                go.Scatter(
                    x=trades['timestamp'],
                    y=trades['drawdown_pct'],
                    mode='lines',
                    name='Drawdown',
                    fill='tozeroy',
                    line=dict(color='#E63946', width=1),
                    hovertemplate='%{y:.2f}%<extra></extra>'
                ),
                row=2, col=1
            )

            fig.update_yaxes(title_text="Equity (₹)", row=1, col=1)
            fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)

        else:
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=trades['timestamp'],
                    y=trades['equity'],
                    mode='lines',
                    name='Equity',
                    line=dict(color='#2E86AB', width=2),
                    hovertemplate='%{y:,.0f}<extra></extra>'
                )
            )

            fig.update_yaxes(title_text="Equity (₹)")

        fig.update_layout(
            title='Equity Curve & Drawdown',
            xaxis_title='Date',
            template='plotly_white',
            hovermode='x unified',
            height=600 if show_drawdown else 400
        )

        if save_html:
            fig.write_html(save_html)

        return fig

    def plot_monthly_returns_heatmap(self, save_html: str = None) -> go.Figure:
        """
        Plot monthly returns as heatmap

        Args:
            save_html: Path to save HTML file

        Returns:
            Plotly figure object
        """
        if self.trades_df is None or self.trades_df.empty:
            return go.Figure()

        trades = self.trades_df[
            (self.trades_df['status'] == 'CLOSED') &
            (self.trades_df['pnl'].notna())
        ].copy()

        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        trades['year'] = trades['timestamp'].dt.year
        trades['month'] = trades['timestamp'].dt.month

        # Group by year and month
        monthly_pnl = trades.groupby(['year', 'month'])['pnl'].sum().reset_index()

        # Pivot to create heatmap data
        heatmap_data = monthly_pnl.pivot(index='year', columns='month', values='pnl')

        # Month names
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=month_names,
            y=heatmap_data.index,
            colorscale='RdYlGn',
            zmid=0,
            text=heatmap_data.values,
            texttemplate='%{text:,.0f}',
            textfont={"size": 10},
            colorbar=dict(title="P&L (₹)")
        ))

        fig.update_layout(
            title='Monthly Returns Heatmap',
            xaxis_title='Month',
            yaxis_title='Year',
            template='plotly_white',
            height=400
        )

        if save_html:
            fig.write_html(save_html)

        return fig

    def plot_pnl_distribution(self, save_html: str = None) -> go.Figure:
        """
        Plot P&L distribution histogram

        Args:
            save_html: Path to save HTML file

        Returns:
            Plotly figure object
        """
        if self.trades_df is None or self.trades_df.empty:
            return go.Figure()

        trades = self.trades_df[
            (self.trades_df['status'] == 'CLOSED') &
            (self.trades_df['pnl'].notna())
        ]

        winners = trades[trades['pnl'] > 0]['pnl']
        losers = trades[trades['pnl'] < 0]['pnl']

        fig = go.Figure()

        # Winners
        fig.add_trace(go.Histogram(
            x=winners,
            name='Winners',
            marker_color='#2E7D32',
            opacity=0.7,
            nbinsx=30
        ))

        # Losers
        fig.add_trace(go.Histogram(
            x=losers,
            name='Losers',
            marker_color='#C62828',
            opacity=0.7,
            nbinsx=30
        ))

        fig.update_layout(
            title='P&L Distribution',
            xaxis_title='P&L (₹)',
            yaxis_title='Frequency',
            barmode='overlay',
            template='plotly_white',
            height=400
        )

        if save_html:
            fig.write_html(save_html)

        return fig

    def plot_hourly_performance(self, save_html: str = None) -> go.Figure:
        """
        Plot performance by hour of day

        Args:
            save_html: Path to save HTML file

        Returns:
            Plotly figure object
        """
        if self.trades_df is None or self.trades_df.empty:
            return go.Figure()

        trades = self.trades_df[
            (self.trades_df['status'] == 'CLOSED') &
            (self.trades_df['pnl'].notna())
        ].copy()

        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        trades['hour'] = trades['timestamp'].dt.hour

        # Group by hour
        hourly_stats = trades.groupby('hour').agg({
            'pnl': ['sum', 'mean', 'count']
        }).reset_index()

        hourly_stats.columns = ['hour', 'total_pnl', 'avg_pnl', 'trade_count']

        # Calculate win rate by hour
        hourly_wins = trades[trades['pnl'] > 0].groupby('hour').size()
        hourly_total = trades.groupby('hour').size()
        hourly_stats['win_rate'] = (hourly_wins / hourly_total * 100).fillna(0).values

        # Create subplot
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Average P&L by Hour', 'Win Rate by Hour'),
            vertical_spacing=0.15,
            row_heights=[0.5, 0.5]
        )

        # Average P&L bar chart
        colors = ['#2E7D32' if x > 0 else '#C62828' for x in hourly_stats['avg_pnl']]

        fig.add_trace(
            go.Bar(
                x=hourly_stats['hour'],
                y=hourly_stats['avg_pnl'],
                name='Avg P&L',
                marker_color=colors,
                hovertemplate='Hour: %{x}<br>Avg P&L: ₹%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        # Win rate line chart
        fig.add_trace(
            go.Scatter(
                x=hourly_stats['hour'],
                y=hourly_stats['win_rate'],
                mode='lines+markers',
                name='Win Rate',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Hour: %{x}<br>Win Rate: %{y:.1f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Add 50% reference line
        fig.add_trace(
            go.Scatter(
                x=hourly_stats['hour'],
                y=[50] * len(hourly_stats),
                mode='lines',
                name='50% Ref',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=False
            ),
            row=2, col=1
        )

        fig.update_xaxes(title_text="Hour of Day", row=2, col=1)
        fig.update_yaxes(title_text="Avg P&L (₹)", row=1, col=1)
        fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)

        fig.update_layout(
            title='Performance by Hour of Day',
            template='plotly_white',
            height=600,
            showlegend=False
        )

        if save_html:
            fig.write_html(save_html)

        return fig

    def plot_holding_period_vs_pnl(self, save_html: str = None) -> go.Figure:
        """
        Plot holding period vs P&L scatter plot

        Args:
            save_html: Path to save HTML file

        Returns:
            Plotly figure object
        """
        if self.trades_df is None or self.trades_df.empty:
            return go.Figure()

        trades = self.trades_df[
            (self.trades_df['status'] == 'CLOSED') &
            (self.trades_df['pnl'].notna()) &
            (self.trades_df['hold_time'].notna())
        ].copy()

        if trades.empty:
            return go.Figure()

        # Convert hold time to hours
        trades['hold_hours'] = trades['hold_time'] / 60

        # Separate winners and losers
        winners = trades[trades['pnl'] > 0]
        losers = trades[trades['pnl'] < 0]

        fig = go.Figure()

        # Winners
        fig.add_trace(go.Scatter(
            x=winners['hold_hours'],
            y=winners['pnl'],
            mode='markers',
            name='Winners',
            marker=dict(
                color='#2E7D32',
                size=8,
                opacity=0.6
            ),
            hovertemplate='Hold: %{x:.1f}h<br>P&L: ₹%{y:,.2f}<extra></extra>'
        ))

        # Losers
        fig.add_trace(go.Scatter(
            x=losers['hold_hours'],
            y=losers['pnl'],
            mode='markers',
            name='Losers',
            marker=dict(
                color='#C62828',
                size=8,
                opacity=0.6
            ),
            hovertemplate='Hold: %{x:.1f}h<br>P&L: ₹%{y:,.2f}<extra></extra>'
        ))

        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

        fig.update_layout(
            title='Holding Period vs P&L',
            xaxis_title='Holding Period (hours)',
            yaxis_title='P&L (₹)',
            template='plotly_white',
            height=500
        )

        if save_html:
            fig.write_html(save_html)

        return fig

    def plot_cumulative_pnl_by_strategy(self, save_html: str = None) -> go.Figure:
        """
        Plot cumulative P&L by strategy

        Args:
            save_html: Path to save HTML file

        Returns:
            Plotly figure object
        """
        if self.trades_df is None or self.trades_df.empty:
            return go.Figure()

        trades = self.trades_df[
            (self.trades_df['status'] == 'CLOSED') &
            (self.trades_df['pnl'].notna()) &
            (self.trades_df['strategy'].notna())
        ].copy()

        if trades.empty:
            return go.Figure()

        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        trades = trades.sort_values('timestamp')

        fig = go.Figure()

        # Plot cumulative P&L for each strategy
        for strategy in trades['strategy'].unique():
            strategy_trades = trades[trades['strategy'] == strategy].copy()
            strategy_trades['cumulative_pnl'] = strategy_trades['pnl'].cumsum()

            fig.add_trace(go.Scatter(
                x=strategy_trades['timestamp'],
                y=strategy_trades['cumulative_pnl'],
                mode='lines',
                name=strategy,
                hovertemplate='%{y:,.2f}<extra></extra>'
            ))

        fig.update_layout(
            title='Cumulative P&L by Strategy',
            xaxis_title='Date',
            yaxis_title='Cumulative P&L (₹)',
            template='plotly_white',
            height=500,
            hovermode='x unified'
        )

        if save_html:
            fig.write_html(save_html)

        return fig

    def create_performance_dashboard(
        self,
        initial_capital: float = 100000,
        save_html: str = "performance_dashboard.html"
    ):
        """
        Create comprehensive performance dashboard with all charts

        Args:
            initial_capital: Starting capital
            save_html: Path to save HTML file
        """
        if self.trades_df is None or self.trades_df.empty:
            print("No trades data available")
            return

        # Generate all charts
        print("Generating performance dashboard...")

        print("  - Equity curve...")
        equity_fig = self.plot_equity_curve(initial_capital, show_drawdown=True)

        print("  - Monthly returns heatmap...")
        heatmap_fig = self.plot_monthly_returns_heatmap()

        print("  - P&L distribution...")
        dist_fig = self.plot_pnl_distribution()

        print("  - Hourly performance...")
        hourly_fig = self.plot_hourly_performance()

        print("  - Holding period analysis...")
        holding_fig = self.plot_holding_period_vs_pnl()

        # Save individual charts
        equity_fig.write_html(save_html.replace('.html', '_equity.html'))
        heatmap_fig.write_html(save_html.replace('.html', '_heatmap.html'))
        dist_fig.write_html(save_html.replace('.html', '_distribution.html'))
        hourly_fig.write_html(save_html.replace('.html', '_hourly.html'))
        holding_fig.write_html(save_html.replace('.html', '_holding.html'))

        print(f"\n✅ Performance dashboard saved!")
        print(f"   Main charts saved with prefix: {save_html.replace('.html', '_')}")
