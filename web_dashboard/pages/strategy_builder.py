"""
Strategy Builder Page - Interactive option and directional strategy builder
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from strategies import OptionsStrategyBuilder, DirectionalStrategies, SpreadBuilder

def show():
    st.title("🎯 Strategy Builder")

    # Strategy type selector
    strategy_type = st.radio(
        "Strategy Type",
        ["📊 Options Strategies", "📈 Directional Strategies", "🔧 Custom Spread Builder"],
        horizontal=True
    )

    st.markdown("---")

    if strategy_type == "📊 Options Strategies":
        show_options_strategies()
    elif strategy_type == "📈 Directional Strategies":
        show_directional_strategies()
    else:
        show_spread_builder()


def show_options_strategies():
    st.subheader("📊 Options Strategy Builder")

    # Input parameters
    col1, col2, col3 = st.columns(3)

    with col1:
        spot_price = st.number_input("Spot Price", value=23950.0, step=50.0)
        lot_size = st.number_input("Lot Size", value=50, step=25)

    with col2:
        iv_rank = st.slider("IV Rank (%)", 0, 100, 50)
        expiry_days = st.number_input("Days to Expiry", value=30, step=1)

    with col3:
        market_outlook = st.selectbox(
            "Market Outlook",
            ["Bullish", "Bearish", "Neutral", "High Volatility Expected"]
        )

    st.markdown("---")

    # Strategy selection
    strategy_name = st.selectbox(
        "Select Strategy",
        [
            "Iron Condor (Range-bound)",
            "Bull Call Spread (Moderately Bullish)",
            "Bear Put Spread (Moderately Bearish)",
            "Long Straddle (Big Move Expected)",
            "Short Strangle (Low Volatility)",
            "Calendar Spread (Time Decay)",
            "Butterfly Spread (Narrow Range)"
        ]
    )

    # Build strategy
    builder = OptionsStrategyBuilder(spot_price=spot_price, lot_size=lot_size)

    if "Iron Condor" in strategy_name:
        strategy = builder.iron_condor(iv_rank=iv_rank, expiry_days=expiry_days)
    elif "Bull Call" in strategy_name:
        strategy = builder.bull_call_spread(expiry_days=expiry_days)
    elif "Bear Put" in strategy_name:
        strategy = builder.bear_put_spread(expiry_days=expiry_days)
    elif "Long Straddle" in strategy_name:
        strategy = builder.long_straddle(iv_rank=iv_rank, expiry_days=expiry_days)
    elif "Short Strangle" in strategy_name:
        strategy = builder.short_strangle(iv_rank=iv_rank, expiry_days=expiry_days)
    elif "Calendar" in strategy_name:
        strategy = builder.calendar_spread()
    else:  # Butterfly
        strategy = builder.butterfly_spread(expiry_days=expiry_days)

    # Display strategy details
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Strategy Details")

        if 'warning' in strategy:
            st.warning(f"⚠️ {strategy['warning']}")

        if strategy.get('recommended', True):
            st.success("✅ Recommended for current conditions")
        else:
            st.error("❌ Not recommended for current IV levels")

        st.markdown(f"**Market Outlook:** {strategy.get('market_outlook', 'N/A')}")

        # Legs
        st.markdown("#### Strategy Legs")
        legs_data = []
        for i, leg in enumerate(strategy.get('legs', []), 1):
            qty = leg.get('quantity', 1)
            legs_data.append({
                '#': i,
                'Action': leg['action'],
                'Type': leg['type'],
                'Strike': f"₹{leg['strike']:,.2f}",
                'Premium': f"₹{leg.get('premium', 0):.2f}",
                'Qty': qty
            })

        if legs_data:
            st.dataframe(pd.DataFrame(legs_data), hide_index=True, use_container_width=True)

        # P&L Profile
        st.markdown("#### P&L Profile")

        metrics_col1, metrics_col2 = st.columns(2)

        with metrics_col1:
            if 'net_debit' in strategy:
                st.metric("Net Debit", f"₹{strategy['net_debit']:,.2f}")
            if 'net_premium_collected' in strategy:
                st.metric("Premium Collected", f"₹{strategy['net_premium_collected']:,.2f}")

        with metrics_col2:
            if 'max_profit' in strategy:
                max_profit = strategy['max_profit']
                if isinstance(max_profit, str):
                    st.metric("Max Profit", max_profit)
                else:
                    st.metric("Max Profit", f"₹{max_profit:,.2f}")

            if 'max_loss' in strategy:
                max_loss = strategy['max_loss']
                if isinstance(max_loss, str):
                    st.metric("Max Loss", max_loss)
                else:
                    st.metric("Max Loss", f"₹{max_loss:,.2f}")

        if 'risk_reward_ratio' in strategy and strategy['risk_reward_ratio']:
            st.metric("Risk:Reward Ratio", f"1:{strategy['risk_reward_ratio']:.2f}")

        # Breakevens
        if 'breakeven' in strategy:
            st.info(f"**Breakeven:** ₹{strategy['breakeven']:,.2f}")
        elif 'breakeven_upper' in strategy:
            st.info(f"**Breakeven Upper:** ₹{strategy['breakeven_upper']:,.2f}")
            st.info(f"**Breakeven Lower:** ₹{strategy['breakeven_lower']:,.2f}")

    with col2:
        st.markdown("### Payoff Diagram")

        # Generate payoff diagram
        if strategy.get('legs'):
            spread_builder = SpreadBuilder(spot_price=spot_price, lot_size=lot_size)

            # Add legs to spread builder
            for leg in strategy['legs']:
                spread_builder.add_leg(
                    action=leg['action'],
                    instrument_type=leg['type'],
                    strike=leg['strike'],
                    premium=leg.get('premium'),
                    quantity=leg.get('quantity', 1)
                )

            # Get payoff data
            payoff_data = spread_builder.visualize_payoff()

            if payoff_data:
                fig = go.Figure()

                # Payoff line
                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=payoff_data['pnl'],
                    mode='lines',
                    name='P&L',
                    line=dict(color='blue', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(31, 119, 180, 0.1)'
                ))

                # Zero line
                fig.add_hline(y=0, line_dash="dash", line_color="gray")

                # Current spot price line
                fig.add_vline(x=spot_price, line_dash="dot", line_color="green",
                             annotation_text="Current Spot")

                # Breakeven points
                if 'breakeven_upper' in strategy:
                    fig.add_vline(x=strategy['breakeven_upper'], line_dash="dot",
                                 line_color="orange", annotation_text="BE Upper")
                    fig.add_vline(x=strategy['breakeven_lower'], line_dash="dot",
                                 line_color="orange", annotation_text="BE Lower")

                fig.update_layout(
                    xaxis_title="Underlying Price (₹)",
                    yaxis_title="Profit / Loss (₹)",
                    height=500,
                    hovermode='x unified',
                    showlegend=False
                )

                st.plotly_chart(fig, use_container_width=True)

    # Action buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📝 Save Strategy", use_container_width=True):
            st.success("Strategy saved to watchlist!")

    with col2:
        if st.button("🎯 Execute Strategy", use_container_width=True):
            st.info("Order placement interface would open here")

    with col3:
        if st.button("📊 Backtest", use_container_width=True):
            st.info("Backtesting this strategy...")

    with col4:
        if st.button("📧 Get Alert", use_container_width=True):
            st.success("Alert configured!")


def show_directional_strategies():
    st.subheader("📈 Directional Strategy Analyzer")

    # Strategy selection
    strategy_type = st.selectbox(
        "Select Strategy",
        [
            "Supertrend Trend Following",
            "Breakout with Volume",
            "Mean Reversion (BB + RSI)",
            "Opening Range Breakout (ORB)",
            "Support/Resistance Bounce"
        ]
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Strategy Rules")

        if "Supertrend" in strategy_type:
            st.markdown("""
            **Supertrend Trend Following**

            **Entry Rules:**
            - BUY: Price crosses above Supertrend line
            - SELL: Price crosses below Supertrend line

            **Exit Rules:**
            - Stop Loss: Supertrend line
            - Target: 2x risk (2:1 R:R)

            **Best For:** Strong trending markets
            """)

        elif "Breakout" in strategy_type:
            st.markdown("""
            **Breakout with Volume Confirmation**

            **Entry Rules:**
            - BUY: Price breaks above 20-day high with 1.5x volume
            - SELL: Price breaks below 20-day low with 1.5x volume

            **Exit Rules:**
            - Stop Loss: 10% below/above breakout level
            - Target: Measured move (range projection)

            **Best For:** Range breakouts, consolidation exits
            """)

        elif "Mean Reversion" in strategy_type:
            st.markdown("""
            **Mean Reversion (Bollinger Bands + RSI)**

            **Entry Rules:**
            - BUY: Price at lower BB AND RSI < 30
            - SELL: Price at upper BB AND RSI > 70

            **Exit Rules:**
            - Target: Middle Bollinger Band
            - Stop Loss: Below/above BB band

            **Best For:** Range-bound, oscillating markets
            """)

        elif "ORB" in strategy_type:
            st.markdown("""
            **Opening Range Breakout (15-min)**

            **Entry Rules:**
            - Identify first 15-min high/low
            - BUY: Breakout above OR high
            - SELL: Breakdown below OR low

            **Exit Rules:**
            - Stop Loss: Opposite side of OR
            - Target: OR range projection

            **Best For:** Intraday trending days
            """)

        else:  # S/R Bounce
            st.markdown("""
            **Support/Resistance Bounce**

            **Entry Rules:**
            - BUY: Bounce from support with reversal pattern
            - SELL: Rejection at resistance

            **Exit Rules:**
            - Target: Next S/R level or 2:1 R:R
            - Stop Loss: 1% beyond S/R level

            **Best For:** Trading zones, key levels
            """)

    with col2:
        st.markdown("### Signal Status")

        # Demo signal
        st.success("✅ Active BUY Signal")

        st.metric("Entry", "₹23,945")
        st.metric("Target", "₹24,150", delta="+205")
        st.metric("Stop Loss", "₹23,850", delta="-95")
        st.metric("Risk:Reward", "1:2.16")

        st.markdown("#### Current Status")
        st.info("📊 **Condition:** Supertrend uptrend confirmed")
        st.info("📈 **Momentum:** Strong bullish momentum")
        st.info("🔊 **Volume:** Above average")

        if st.button("🎯 Execute Trade", use_container_width=True):
            st.success("Trade executed!")


def show_spread_builder():
    st.subheader("🔧 Custom Spread Builder")

    st.info("💡 Build custom multi-leg option spreads with precise control")

    # Spread configuration
    col1, col2 = st.columns(2)

    with col1:
        spot_price = st.number_input("Spot Price", value=23950.0, step=50.0, key="spread_spot")
        lot_size = st.number_input("Lot Size", value=50, step=25, key="spread_lot")

    with col2:
        spread_type = st.selectbox(
            "Spread Type",
            ["Vertical Spread", "Horizontal Spread", "Diagonal Spread",
             "Ratio Spread", "Custom Multi-leg"]
        )

    st.markdown("---")

    # Leg builder
    st.markdown("### Add Legs")

    num_legs = st.number_input("Number of Legs", min_value=1, max_value=6, value=2)

    legs = []
    for i in range(num_legs):
        with st.expander(f"Leg {i+1}", expanded=(i<2)):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                action = st.selectbox(f"Action", ["BUY", "SELL"], key=f"action_{i}")

            with col2:
                option_type = st.selectbox(f"Type", ["CALL", "PUT"], key=f"type_{i}")

            with col3:
                strike = st.number_input(f"Strike", value=24000.0+(i*100), step=50.0, key=f"strike_{i}")

            with col4:
                premium = st.number_input(f"Premium", value=150.0-(i*25), step=5.0, key=f"premium_{i}")

            quantity = st.number_input(f"Quantity (lots)", value=1, min_value=1, max_value=10, key=f"qty_{i}")

            legs.append({
                'action': action,
                'type': option_type,
                'strike': strike,
                'premium': premium,
                'quantity': quantity
            })

    st.markdown("---")

    # Build and analyze spread
    if st.button("📊 Build Spread", use_container_width=True, type="primary"):
        builder = SpreadBuilder(spot_price=spot_price, lot_size=lot_size)

        for leg in legs:
            builder.add_leg(
                action=leg['action'],
                instrument_type=leg['type'],
                strike=leg['strike'],
                premium=leg['premium'],
                quantity=leg['quantity']
            )

        analysis = builder.analyze_spread()

        # Display results
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Spread Analysis")

            st.write(f"**Spread Type:** {analysis['spread_type'].upper()}")
            st.write(f"**Total Legs:** {analysis['total_legs']}")

            if analysis['is_debit_spread']:
                st.error(f"**Net Debit:** ₹{abs(analysis['net_cashflow']):,.2f}")
            else:
                st.success(f"**Net Credit:** ₹{analysis['net_cashflow']:,.2f}")

            if isinstance(analysis['max_profit'], (int, float)):
                st.metric("Max Profit", f"₹{analysis['max_profit']:,.2f}")

            if isinstance(analysis['max_loss'], (int, float)):
                st.metric("Max Loss", f"₹{analysis['max_loss']:,.2f}")

            if analysis.get('risk_reward'):
                st.metric("Risk:Reward", f"1:{analysis['risk_reward']:.2f}")

        with col2:
            st.markdown("### Payoff Diagram")

            payoff_data = builder.visualize_payoff()

            if payoff_data:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=payoff_data['pnl'],
                    mode='lines',
                    name='P&L',
                    line=dict(color='purple', width=3),
                    fill='tozeroy'
                ))

                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                fig.add_vline(x=spot_price, line_dash="dot", line_color="green",
                             annotation_text="Spot")

                fig.update_layout(
                    xaxis_title="Price at Expiry (₹)",
                    yaxis_title="P&L (₹)",
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)
