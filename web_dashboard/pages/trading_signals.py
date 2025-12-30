"""
Trading Signals Page - Advanced signal analysis and generation
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

def show():
    st.title("📊 Trading Signals")

    # Signal Type Selector
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        instruments = st.multiselect(
            "Select Instruments",
            ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"],
            default=["NIFTY", "BANKNIFTY"]
        )

    with col2:
        timeframe = st.selectbox(
            "Timeframe",
            ["1 min", "5 min", "15 min", "30 min", "1 hour", "1 day"]
        )

    with col3:
        signal_strength = st.slider("Min Strength", 1, 10, 5)

    st.markdown("---")

    # Live Signals Table
    st.subheader("🎯 Live Signals")

    # Demo data
    signals_data = {
        'Instrument': ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'],
        'Signal': ['STRONG_BUY', 'BUY', 'HOLD', 'SELL'],
        'Strength': [8, 6, 5, 7],
        'Price': [23950.00, 47200.00, 21500.00, 12300.00],
        'Entry': [23945.00, 47190.00, None, 12305.00],
        'Target': [24150.00, 47500.00, None, 12100.00],
        'Stop Loss': [23850.00, 47000.00, None, 12400.00],
        'Risk:Reward': ['1:2.05', '1:1.63', None, '1:2.15'],
        'Indicators': ['RSI+MACD+ST', 'EMA+BB', 'Mixed', 'RSI+MACD']
    }

    signals_df = pd.DataFrame(signals_data)

    # Filter by selected instruments
    if instruments:
        signals_df = signals_df[signals_df['Instrument'].isin(instruments)]

    # Display with color coding
    def highlight_signal(row):
        if row['Signal'] == 'STRONG_BUY':
            return ['background-color: #d4edda'] * len(row)
        elif row['Signal'] == 'BUY':
            return ['background-color: #d1ecf1'] * len(row)
        elif row['Signal'] == 'SELL':
            return ['background-color: #fff3cd'] * len(row)
        elif row['Signal'] == 'STRONG_SELL':
            return ['background-color: #f8d7da'] * len(row)
        else:
            return [''] * len(row)

    st.dataframe(
        signals_df.style.apply(highlight_signal, axis=1),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # Detailed Signal Analysis
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Signal Breakdown")

        selected_instrument = st.selectbox(
            "Analyze Signal For:",
            signals_df['Instrument'].tolist()
        )

        if selected_instrument:
            signal_row = signals_df[signals_df['Instrument'] == selected_instrument].iloc[0]

            st.markdown(f"""
            ### {selected_instrument}
            **Signal:** {signal_row['Signal']}
            **Strength:** {signal_row['Strength']}/10
            **Current Price:** ₹{signal_row['Price']:,.2f}
            """)

            if signal_row['Entry']:
                st.success(f"**Entry:** ₹{signal_row['Entry']:,.2f}")
                st.info(f"**Target:** ₹{signal_row['Target']:,.2f}")
                st.warning(f"**Stop Loss:** ₹{signal_row['Stop Loss']:,.2f}")
                st.metric("Risk:Reward", signal_row['Risk:Reward'])

            # Indicator details
            st.markdown("#### Contributing Indicators")
            indicators = signal_row['Indicators'].split('+')
            for ind in indicators:
                if ind == 'RSI':
                    st.write(f"✅ **RSI:** Oversold (28) - Bullish")
                elif ind == 'MACD':
                    st.write(f"✅ **MACD:** Bullish crossover")
                elif ind == 'ST':
                    st.write(f"✅ **Supertrend:** Uptrend confirmed")
                elif ind == 'EMA':
                    st.write(f"✅ **EMA:** Golden cross (9>21>50)")
                elif ind == 'BB':
                    st.write(f"✅ **Bollinger Bands:** Bounce from lower band")
                else:
                    st.write(f"⚠️ **{ind}:** Mixed signals")

    with col2:
        st.subheader("📊 Technical Indicators")

        # Demo chart with indicators
        import numpy as np

        # Generate demo OHLC data
        dates = pd.date_range(end=datetime.now(), periods=50, freq='H')
        close = 23900 + np.cumsum(np.random.randn(50) * 30)
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
            name='Price'
        ))

        # Bollinger Bands
        fig.add_trace(go.Scatter(
            x=dates, y=upper_bb,
            name='Upper BB',
            line=dict(color='gray', dash='dash')
        ))

        fig.add_trace(go.Scatter(
            x=dates, y=sma20,
            name='SMA 20',
            line=dict(color='blue')
        ))

        fig.add_trace(go.Scatter(
            x=dates, y=lower_bb,
            name='Lower BB',
            line=dict(color='gray', dash='dash'),
            fill='tonexty',
            fillcolor='rgba(128,128,128,0.1)'
        ))

        fig.update_layout(
            height=400,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            legend=dict(x=0, y=1),
            margin=dict(l=0, r=0, t=0, b=0)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Signal History
    st.subheader("📜 Recent Signal History")

    history_data = {
        'Timestamp': [
            datetime.now().replace(hour=15, minute=0),
            datetime.now().replace(hour=14, minute=30),
            datetime.now().replace(hour=14, minute=0),
            datetime.now().replace(hour=13, minute=30),
        ],
        'Instrument': ['NIFTY', 'BANKNIFTY', 'NIFTY', 'FINNIFTY'],
        'Signal': ['BUY', 'SELL', 'BUY', 'HOLD'],
        'Entry': [23900, 47300, 23850, None],
        'Exit': [23950, 47250, None, None],
        'P&L': ['+₹2,500', '+₹1,250', 'Active', 'N/A'],
        'Status': ['Closed', 'Closed', 'Active', 'Missed']
    }

    history_df = pd.DataFrame(history_data)

    def color_status(val):
        if val == 'Closed':
            return 'background-color: #d4edda'
        elif val == 'Active':
            return 'background-color: #d1ecf1'
        elif val == 'Missed':
            return 'background-color: #f8d7da'
        return ''

    st.dataframe(
        history_df.style.applymap(color_status, subset=['Status']),
        use_container_width=True,
        hide_index=True
    )

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Refresh Signals", use_container_width=True):
            st.success("Signals refreshed!")

    with col2:
        if st.button("📧 Email Alerts", use_container_width=True):
            st.info("Email alerts configured!")

    with col3:
        if st.button("🔔 Enable Notifications", use_container_width=True):
            st.info("Notifications enabled!")

    with col4:
        if st.button("📊 Export Signals", use_container_width=True):
            st.download_button(
                "Download CSV",
                signals_df.to_csv(index=False),
                "signals.csv",
                "text/csv"
            )
