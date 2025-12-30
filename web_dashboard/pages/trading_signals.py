"""
Trading Signals Page - Advanced signal analysis and generation

Enhanced with professional UI components (Phase 4.3.1 & 4.3.2)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

# Add parent for theme imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from web_dashboard.theme import (  # noqa: E402
    get_signal_css,
    render_signal_card,
    COLORS,
)


def show():
    st.title("Trading Signals")

    # Apply signal-specific CSS
    st.markdown(get_signal_css(), unsafe_allow_html=True)

    # Signal Type Selector
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        instruments = st.multiselect(
            "Select Instruments",
            ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"],
            default=["NIFTY", "BANKNIFTY"]
        )

    with col2:
        # Timeframe selector - used for signal generation context
        st.selectbox(
            "Timeframe",
            ["1 min", "5 min", "15 min", "30 min", "1 hour", "1 day"],
            index=2,  # Default to 15 min
            key="signal_timeframe"
        )

    with col3:
        signal_strength = st.slider("Min Strength", 1, 10, 5)

    st.markdown("---")

    # Demo signal data with timestamps
    signals_data = [
        {
            'instrument': 'NIFTY',
            'signal': 'STRONG_BUY',
            'strength': 8,
            'price': 23950.00,
            'entry': 23945.00,
            'target': 24150.00,
            'stop_loss': 23850.00,
            'indicators': ['RSI', 'MACD', 'Supertrend'],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'category': 'Nifty'
        },
        {
            'instrument': 'BANKNIFTY',
            'signal': 'BUY',
            'strength': 6,
            'price': 47200.00,
            'entry': 47190.00,
            'target': 47500.00,
            'stop_loss': 47000.00,
            'indicators': ['EMA', 'BB'],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'category': 'Bank Nifty'
        },
        {
            'instrument': 'FINNIFTY',
            'signal': 'HOLD',
            'strength': 5,
            'price': 21500.00,
            'entry': None,
            'target': None,
            'stop_loss': None,
            'indicators': ['Mixed'],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'category': 'Others'
        },
        {
            'instrument': 'MIDCPNIFTY',
            'signal': 'SELL',
            'strength': 7,
            'price': 12300.00,
            'entry': 12305.00,
            'target': 12100.00,
            'stop_loss': 12400.00,
            'indicators': ['RSI', 'MACD'],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'category': 'Others'
        },
        {
            'instrument': 'SENSEX',
            'signal': 'STRONG_SELL',
            'strength': 9,
            'price': 78500.00,
            'entry': 78490.00,
            'target': 78000.00,
            'stop_loss': 78700.00,
            'indicators': ['RSI', 'MACD', 'VWAP'],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'category': 'Others'
        }
    ]

    # Filter by selected instruments and strength
    filtered_signals = [
        s for s in signals_data
        if s['instrument'] in instruments and s['strength'] >= signal_strength
    ]

    # Tabs for grouping by underlying (Phase 4.3.1)
    st.subheader("Live Signals")

    tab_nifty, tab_banknifty, tab_others = st.tabs(["Nifty", "Bank Nifty", "Others"])

    with tab_nifty:
        nifty_signals = [s for s in filtered_signals if s['category'] == 'Nifty']
        if nifty_signals:
            for sig in nifty_signals:
                st.markdown(render_signal_card(
                    instrument=sig['instrument'],
                    signal=sig['signal'],
                    strength=sig['strength'],
                    price=sig['price'],
                    entry=sig['entry'],
                    target=sig['target'],
                    stop_loss=sig['stop_loss'],
                    timestamp=sig['timestamp'],
                    indicators=sig['indicators']
                ), unsafe_allow_html=True)

                # Trade This Signal button (Phase 4.3.2)
                if sig['entry']:
                    if st.button(f"Trade {sig['instrument']}", key=f"trade_{sig['instrument']}", use_container_width=True):
                        st.info(f"Opening order form for {sig['instrument']}...")
        else:
            st.info("No Nifty signals matching your criteria")

    with tab_banknifty:
        bn_signals = [s for s in filtered_signals if s['category'] == 'Bank Nifty']
        if bn_signals:
            for sig in bn_signals:
                st.markdown(render_signal_card(
                    instrument=sig['instrument'],
                    signal=sig['signal'],
                    strength=sig['strength'],
                    price=sig['price'],
                    entry=sig['entry'],
                    target=sig['target'],
                    stop_loss=sig['stop_loss'],
                    timestamp=sig['timestamp'],
                    indicators=sig['indicators']
                ), unsafe_allow_html=True)

                if sig['entry']:
                    if st.button(f"Trade {sig['instrument']}", key=f"trade_{sig['instrument']}", use_container_width=True):
                        st.info(f"Opening order form for {sig['instrument']}...")
        else:
            st.info("No Bank Nifty signals matching your criteria")

    with tab_others:
        other_signals = [s for s in filtered_signals if s['category'] == 'Others']
        if other_signals:
            for sig in other_signals:
                st.markdown(render_signal_card(
                    instrument=sig['instrument'],
                    signal=sig['signal'],
                    strength=sig['strength'],
                    price=sig['price'],
                    entry=sig['entry'],
                    target=sig['target'],
                    stop_loss=sig['stop_loss'],
                    timestamp=sig['timestamp'],
                    indicators=sig['indicators']
                ), unsafe_allow_html=True)

                if sig['entry']:
                    if st.button(f"Trade {sig['instrument']}", key=f"trade_{sig['instrument']}", use_container_width=True):
                        st.info(f"Opening order form for {sig['instrument']}...")
        else:
            st.info("No other signals matching your criteria")

    st.markdown("---")

    # Detailed Signal Analysis (Phase 4.3.2)
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Signal Breakdown")

        if filtered_signals:
            selected_instrument = st.selectbox(
                "Analyze Signal For:",
                [s['instrument'] for s in filtered_signals]
            )

            signal = next((s for s in filtered_signals if s['instrument'] == selected_instrument), None)

            if signal:
                st.markdown(f"### {signal['instrument']}")

                # Signal type with color
                signal_colors = {
                    'STRONG_BUY': COLORS['profit'],
                    'BUY': '#4ade80',
                    'HOLD': COLORS['neutral'],
                    'SELL': '#f87171',
                    'STRONG_SELL': COLORS['loss']
                }
                sig_color = signal_colors.get(signal['signal'], COLORS['neutral'])

                st.markdown(f"""
                <div style="margin-bottom: 1rem;">
                    <span style="color: {sig_color}; font-size: 1.5rem; font-weight: 700;">
                        {signal['signal'].replace('_', ' ')}
                    </span>
                </div>
                """, unsafe_allow_html=True)

                st.metric("Current Price", f"₹{signal['price']:,.2f}")
                st.metric("Strength", f"{signal['strength']}/10")

                if signal['entry']:
                    st.success(f"**Entry:** ₹{signal['entry']:,.2f}")
                    st.info(f"**Target:** ₹{signal['target']:,.2f}")
                    st.warning(f"**Stop Loss:** ₹{signal['stop_loss']:,.2f}")

                    # Calculate R:R
                    risk = abs(signal['entry'] - signal['stop_loss'])
                    reward = abs(signal['target'] - signal['entry'])
                    if risk > 0:
                        st.metric("Risk:Reward", f"1:{reward/risk:.2f}")

                # Indicator details (Phase 4.3.2)
                st.markdown("#### Contributing Indicators")
                for ind in signal['indicators']:
                    if ind == 'RSI':
                        st.write("**RSI:** Oversold (28) - Bullish divergence detected")
                    elif ind == 'MACD':
                        st.write("**MACD:** Bullish crossover above signal line")
                    elif ind == 'Supertrend':
                        st.write("**Supertrend:** Buy signal, uptrend confirmed")
                    elif ind == 'EMA':
                        st.write("**EMA:** Golden cross (9 > 21 > 50)")
                    elif ind == 'BB':
                        st.write("**Bollinger Bands:** Bounce from lower band")
                    elif ind == 'VWAP':
                        st.write("**VWAP:** Price below VWAP, bearish")
                    else:
                        st.write(f"**{ind}:** Mixed signals")
        else:
            st.info("Select instruments to see signal breakdown")

    with col2:
        st.subheader("Technical Chart")

        if filtered_signals:
            # Generate demo OHLC data
            import numpy as np

            dates = pd.date_range(end=datetime.now(), periods=50, freq='H')
            base_price = filtered_signals[0]['price'] if filtered_signals else 24000
            close = base_price + np.cumsum(np.random.randn(50) * 30)
            high = close + np.random.rand(50) * 20
            low = close - np.random.rand(50) * 20
            open_price = close + np.random.randn(50) * 10

            # Calculate indicators
            sma20 = pd.Series(close).rolling(20).mean()
            upper_bb = sma20 + 2 * pd.Series(close).rolling(20).std()
            lower_bb = sma20 - 2 * pd.Series(close).rolling(20).std()

            # Create candlestick chart
            fig = go.Figure()

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=dates,
                open=open_price,
                high=high,
                low=low,
                close=close,
                name='Price',
                increasing_line_color=COLORS['profit'],
                decreasing_line_color=COLORS['loss']
            ))

            # Bollinger Bands
            fig.add_trace(go.Scatter(
                x=dates, y=upper_bb,
                name='Upper BB',
                line=dict(color='rgba(156, 163, 175, 0.5)', dash='dash')
            ))

            fig.add_trace(go.Scatter(
                x=dates, y=sma20,
                name='SMA 20',
                line=dict(color=COLORS['info'], width=2)
            ))

            fig.add_trace(go.Scatter(
                x=dates, y=lower_bb,
                name='Lower BB',
                line=dict(color='rgba(156, 163, 175, 0.5)', dash='dash'),
                fill='tonexty',
                fillcolor='rgba(59, 130, 246, 0.05)'
            ))

            fig.update_layout(
                height=400,
                xaxis_rangeslider_visible=False,
                hovermode='x unified',
                legend=dict(x=0, y=1, bgcolor='rgba(0,0,0,0)'),
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)'),
                yaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)')
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select instruments to see chart")

    st.markdown("---")

    # Signal History
    st.subheader("Recent Signal History")

    history_data = {
        'Timestamp': [
            datetime.now().replace(hour=15, minute=0).strftime('%Y-%m-%d %H:%M'),
            datetime.now().replace(hour=14, minute=30).strftime('%Y-%m-%d %H:%M'),
            datetime.now().replace(hour=14, minute=0).strftime('%Y-%m-%d %H:%M'),
            datetime.now().replace(hour=13, minute=30).strftime('%Y-%m-%d %H:%M'),
        ],
        'Instrument': ['NIFTY', 'BANKNIFTY', 'NIFTY', 'FINNIFTY'],
        'Signal': ['BUY', 'SELL', 'BUY', 'HOLD'],
        'Entry': ['₹23,900', '₹47,300', '₹23,850', '-'],
        'Exit': ['₹23,950', '₹47,250', 'Active', '-'],
        'P&L': ['+₹2,500', '+₹1,250', 'Active', 'N/A'],
        'Status': ['Closed', 'Closed', 'Active', 'Missed']
    }

    history_df = pd.DataFrame(history_data)

    def color_status(val):
        if val == 'Closed':
            return f'background-color: rgba(34, 197, 94, 0.2); color: {COLORS["profit"]}'
        elif val == 'Active':
            return f'background-color: rgba(59, 130, 246, 0.2); color: {COLORS["info"]}'
        elif val == 'Missed':
            return f'background-color: rgba(239, 68, 68, 0.2); color: {COLORS["loss"]}'
        return ''

    st.dataframe(
        history_df.style.map(color_status, subset=['Status']),
        use_container_width=True,
        hide_index=True
    )

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Refresh Signals", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("Email Alerts", use_container_width=True):
            st.info("Email alerts configured!")

    with col3:
        if st.button("Enable Notifications", use_container_width=True):
            st.info("Notifications enabled!")

    with col4:
        # Export signals
        if filtered_signals:
            export_df = pd.DataFrame([{
                'Instrument': s['instrument'],
                'Signal': s['signal'],
                'Strength': s['strength'],
                'Price': s['price'],
                'Entry': s['entry'],
                'Target': s['target'],
                'Stop Loss': s['stop_loss'],
                'Timestamp': s['timestamp']
            } for s in filtered_signals])

            st.download_button(
                "Export Signals",
                export_df.to_csv(index=False),
                "signals.csv",
                "text/csv",
                use_container_width=True
            )
