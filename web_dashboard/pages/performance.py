"""
Performance Analytics Page - Comprehensive performance analysis and visualizations
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

def show():
    st.title("📈 Performance Analytics")

    # Time period selector
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        period = st.selectbox(
            "Time Period",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year", "All Time"]
        )

    with col2:
        if st.button("📊 Generate Report", use_container_width=True):
            st.success("Report generated!")

    with col3:
        if st.button("📥 Export Data", use_container_width=True):
            st.download_button(
                "Download CSV",
                pd.DataFrame().to_csv(),
                "performance_report.csv"
            )

    st.markdown("---")

    # Key Metrics
    st.subheader("🎯 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total P&L", "₹25,000", delta="+15.2%")
        st.metric("Win Rate", "65.5%", delta="+5.2%")

    with col2:
        st.metric("Profit Factor", "1.85", delta="+0.15")
        st.metric("Sharpe Ratio", "1.42", delta="+0.22")

    with col3:
        st.metric("Max Drawdown", "4.2%", delta="-1.1%", delta_color="inverse")
        st.metric("Avg Win", "₹850", delta="+₹120")

    with col4:
        st.metric("Total Trades", "100", delta="+12")
        st.metric("Avg Loss", "₹420", delta="-₹50", delta_color="inverse")

    st.markdown("---")

    # Charts row 1
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Equity Curve")

        # Generate demo equity curve
        dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
        equity = [100000]
        for i in range(89):
            change = np.random.normal(300, 600)
            equity.append(max(equity[-1] + change, 90000))

        equity_df = pd.DataFrame({
            'Date': dates,
            'Equity': equity
        })

        # Calculate drawdown
        equity_df['Peak'] = equity_df['Equity'].cummax()
        equity_df['Drawdown'] = (equity_df['Equity'] - equity_df['Peak']) / equity_df['Peak'] * 100

        # Create figure with subplots
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=("Equity", "Drawdown %")
        )

        # Equity curve
        fig.add_trace(
            go.Scatter(
                x=equity_df['Date'],
                y=equity_df['Equity'],
                mode='lines',
                name='Equity',
                line=dict(color='blue', width=2),
                fill='tozeroy'
            ),
            row=1, col=1
        )

        # Initial capital line
        fig.add_hline(y=100000, line_dash="dash", line_color="gray",
                     annotation_text="Initial", row=1, col=1)

        # Drawdown
        fig.add_trace(
            go.Scatter(
                x=equity_df['Date'],
                y=equity_df['Drawdown'],
                mode='lines',
                name='Drawdown',
                line=dict(color='red', width=1),
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.1)'
            ),
            row=2, col=1
        )

        fig.update_layout(height=500, showlegend=False, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📅 Monthly Returns Heatmap")

        # Generate demo monthly returns
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        returns_2024 = np.random.normal(2, 3, 12)

        heatmap_data = pd.DataFrame({
            'Month': months,
            'Returns': returns_2024
        }).pivot_table(values='Returns', index=['Month'], aggfunc='mean')

        fig = go.Figure(data=go.Heatmap(
            z=[heatmap_data['Returns'].values],
            x=months,
            y=['2024'],
            colorscale='RdYlGn',
            zmid=0,
            text=[[f"{v:.1f}%" for v in returns_2024]],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Returns %")
        ))

        fig.update_layout(height=150, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # P&L Distribution
        st.subheader("📊 P&L Distribution")

        # Generate demo P&L data
        wins = np.random.normal(850, 200, 65)
        losses = -np.abs(np.random.normal(420, 150, 35))

        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=wins,
            name='Winners',
            marker_color='green',
            opacity=0.7,
            nbinsx=20
        ))

        fig.add_trace(go.Histogram(
            x=losses,
            name='Losers',
            marker_color='red',
            opacity=0.7,
            nbinsx=20
        ))

        fig.update_layout(
            barmode='overlay',
            xaxis_title='P&L (₹)',
            yaxis_title='Frequency',
            height=300,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Charts row 2
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⏰ Performance by Hour of Day")

        hours = list(range(9, 16))
        avg_pnl = [300, 450, 200, -100, 350, 500, 250]
        win_rate = [70, 65, 55, 45, 68, 72, 60]

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.5, 0.5]
        )

        # Avg P&L
        colors = ['green' if x > 0 else 'red' for x in avg_pnl]
        fig.add_trace(
            go.Bar(x=hours, y=avg_pnl, name='Avg P&L', marker_color=colors),
            row=1, col=1
        )

        # Win Rate
        fig.add_trace(
            go.Scatter(x=hours, y=win_rate, mode='lines+markers',
                      name='Win Rate', line=dict(color='blue')),
            row=2, col=1
        )

        fig.add_hline(y=50, line_dash="dash", line_color="gray", row=2, col=1)

        fig.update_xaxes(title_text="Hour of Day", row=2, col=1)
        fig.update_yaxes(title_text="Avg P&L (₹)", row=1, col=1)
        fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)

        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 Strategy Performance Comparison")

        strategies = ['Supertrend', 'Breakout', 'Mean Reversion', 'ORB', 'Iron Condor']
        returns = [12.5, 8.3, 15.2, 6.8, 10.1]
        trades = [25, 18, 30, 15, 12]
        win_rates = [68, 61, 72, 55, 70]

        strategy_df = pd.DataFrame({
            'Strategy': strategies,
            'Return %': returns,
            'Trades': trades,
            'Win Rate %': win_rates
        })

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=strategies,
            y=returns,
            name='Return %',
            marker_color='lightblue'
        ))

        fig.update_layout(
            xaxis_title='Strategy',
            yaxis_title='Return (%)',
            height=250
        )

        st.plotly_chart(fig, use_container_width=True)

        # Strategy table
        st.dataframe(
            strategy_df.style.background_gradient(subset=['Return %'], cmap='RdYlGn'),
            hide_index=True,
            use_container_width=True
        )

    st.markdown("---")

    # Trade Analysis
    st.subheader("📋 Recent Trades")

    trades_data = {
        'Date': [datetime.now() - timedelta(days=i) for i in range(10)],
        'Instrument': ['NIFTY CE', 'BANKNIFTY PE', 'NIFTY CE', 'FINNIFTY CE', 'NIFTY PE',
                       'BANKNIFTY CE', 'NIFTY CE', 'MIDCPNIFTY PE', 'NIFTY CE', 'BANKNIFTY PE'],
        'Direction': ['LONG', 'SHORT', 'LONG', 'LONG', 'SHORT', 'LONG', 'SHORT', 'LONG', 'LONG', 'SHORT'],
        'Entry': [250, 180, 245, 120, 190, 310, 255, 95, 260, 175],
        'Exit': [275, 160, 230, 135, 185, 335, 240, 105, 280, 165],
        'P&L': [1250, 500, -750, 750, 250, 1250, -750, 500, 1000, 250],
        'Return %': [10.0, 11.1, -6.1, 12.5, 2.6, 8.1, -5.9, 10.5, 7.7, 5.7],
        'Strategy': ['Supertrend', 'Iron Condor', 'Breakout', 'ORB', 'Mean Rev',
                    'Supertrend', 'Breakout', 'ORB', 'Supertrend', 'Iron Condor']
    }

    trades_df = pd.DataFrame(trades_data)
    trades_df['Date'] = trades_df['Date'].dt.strftime('%Y-%m-%d')

    def highlight_pnl(row):
        if row['P&L'] > 0:
            return ['background-color: #d4edda'] * len(row)
        elif row['P&L'] < 0:
            return ['background-color: #f8d7da'] * len(row)
        return [''] * len(row)

    st.dataframe(
        trades_df.style.apply(highlight_pnl, axis=1),
        hide_index=True,
        use_container_width=True
    )

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info(f"**Avg Hold Time:** 4.5 hours")
    with col2:
        st.info(f"**Best Trade:** ₹1,250")
    with col3:
        st.info(f"**Worst Trade:** -₹750")
    with col4:
        st.info(f"**Consecutive Wins:** 3")
