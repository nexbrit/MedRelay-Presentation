"""
Strategy Builder Page - Interactive option and directional strategy builder

Enhanced with Phase 4.3.5 features:
- Professional themed payoff diagrams
- Clear break-even point visualization
- Max profit/loss and risk:reward display
- Execute strategy button
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from strategies import OptionsStrategyBuilder, SpreadBuilder  # noqa: E402
from web_dashboard.theme import COLORS  # noqa: E402


def show():
    st.title("Strategy Builder")

    # Strategy type selector
    strategy_type = st.radio(
        "Strategy Type",
        ["Options Strategies", "Directional Strategies", "Custom Spread Builder"],
        horizontal=True
    )

    st.markdown("---")

    if strategy_type == "Options Strategies":
        show_options_strategies()
    elif strategy_type == "Directional Strategies":
        show_directional_strategies()
    else:
        show_spread_builder()


def show_options_strategies():
    st.subheader("Options Strategy Builder")

    # Input parameters
    col1, col2, col3 = st.columns(3)

    with col1:
        spot_price = st.number_input("Spot Price", value=23950.0, step=50.0)
        lot_size = st.number_input("Lot Size", value=75, step=25)  # Updated for NIFTY

    with col2:
        iv_rank = st.slider("IV Rank (%)", 0, 100, 50)
        expiry_days = st.number_input("Days to Expiry", value=30, step=1)

    with col3:
        st.selectbox(
            "Market Outlook",
            ["Bullish", "Bearish", "Neutral", "High Volatility Expected"],
            key="market_outlook"
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
            st.warning(f"{strategy['warning']}")

        if strategy.get('recommended', True):
            st.success("Recommended for current conditions")
        else:
            st.error("Not recommended for current IV levels")

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

        # P&L Profile (Phase 4.3.5)
        st.markdown("#### P&L Profile")

        # Summary card
        st.markdown(f"""
        <div style="background: {COLORS['bg_secondary']}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
        """, unsafe_allow_html=True)

        metrics_col1, metrics_col2 = st.columns(2)

        with metrics_col1:
            if 'net_debit' in strategy:
                st.metric("Net Debit", f"₹{strategy['net_debit']:,.2f}")
            if 'net_premium_collected' in strategy:
                st.metric("Premium Collected", f"₹{strategy['net_premium_collected']:,.2f}")

            if 'max_profit' in strategy:
                max_profit = strategy['max_profit']
                if isinstance(max_profit, str):
                    st.metric("Max Profit", max_profit)
                else:
                    st.metric("Max Profit", f"₹{max_profit:,.2f}")

        with metrics_col2:
            if 'max_loss' in strategy:
                max_loss = strategy['max_loss']
                if isinstance(max_loss, str):
                    st.metric("Max Loss", max_loss)
                else:
                    st.metric("Max Loss", f"₹{max_loss:,.2f}")

            if 'risk_reward_ratio' in strategy and strategy['risk_reward_ratio']:
                st.metric("Risk:Reward", f"1:{strategy['risk_reward_ratio']:.2f}")

        st.markdown("</div></div>", unsafe_allow_html=True)

        # Break-even display (Phase 4.3.5)
        st.markdown("#### Break-Even Points")
        if 'breakeven' in strategy:
            st.markdown(f"""
            <div style="background: {COLORS['bg_accent']}; padding: 0.75rem 1rem; border-radius: 6px; border-left: 4px solid {COLORS['info']};">
                <span style="color: {COLORS['text_muted']};">Breakeven:</span>
                <span style="color: {COLORS['text_primary']}; font-weight: 600; font-size: 1.125rem; margin-left: 0.5rem;">₹{strategy['breakeven']:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        elif 'breakeven_upper' in strategy:
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem;">
                <div style="background: {COLORS['bg_accent']}; padding: 0.75rem 1rem; border-radius: 6px; border-left: 4px solid {COLORS['profit']};">
                    <span style="color: {COLORS['text_muted']};">Upper BE:</span>
                    <span style="color: {COLORS['profit']}; font-weight: 600; margin-left: 0.5rem;">₹{strategy['breakeven_upper']:,.2f}</span>
                </div>
                <div style="background: {COLORS['bg_accent']}; padding: 0.75rem 1rem; border-radius: 6px; border-left: 4px solid {COLORS['loss']};">
                    <span style="color: {COLORS['text_muted']};">Lower BE:</span>
                    <span style="color: {COLORS['loss']}; font-weight: 600; margin-left: 0.5rem;">₹{strategy['breakeven_lower']:,.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Payoff Diagram")

        # Generate payoff diagram with theme colors
        if strategy.get('legs'):
            spread_builder = SpreadBuilder(spot_price=spot_price, lot_size=lot_size)

            for leg in strategy['legs']:
                spread_builder.add_leg(
                    action=leg['action'],
                    instrument_type=leg['type'],
                    strike=leg['strike'],
                    premium=leg.get('premium'),
                    quantity=leg.get('quantity', 1)
                )

            payoff_data = spread_builder.visualize_payoff()

            if payoff_data:
                fig = go.Figure()

                # Profit fill
                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=[p if p >= 0 else 0 for p in payoff_data['pnl']],
                    mode='lines',
                    name='Profit Zone',
                    line=dict(color=COLORS['profit'], width=0),
                    fill='tozeroy',
                    fillcolor='rgba(34, 197, 94, 0.2)'
                ))

                # Loss fill
                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=[p if p < 0 else 0 for p in payoff_data['pnl']],
                    mode='lines',
                    name='Loss Zone',
                    line=dict(color=COLORS['loss'], width=0),
                    fill='tozeroy',
                    fillcolor='rgba(239, 68, 68, 0.2)'
                ))

                # Main payoff line
                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=payoff_data['pnl'],
                    mode='lines',
                    name='P&L',
                    line=dict(color=COLORS['info'], width=3),
                    hovertemplate='Price: ₹%{x:,.0f}<br>P&L: ₹%{y:,.0f}<extra></extra>'
                ))

                # Zero line
                fig.add_hline(y=0, line_dash="dash", line_color=COLORS['text_muted'])

                # Current spot price
                fig.add_vline(
                    x=spot_price, line_dash="dot", line_color=COLORS['profit'],
                    annotation_text="Spot", annotation_position="top"
                )

                # Break-even points (Phase 4.3.5)
                if 'breakeven_upper' in strategy:
                    fig.add_vline(
                        x=strategy['breakeven_upper'], line_dash="dot",
                        line_color=COLORS['warning'],
                        annotation_text=f"BE: {strategy['breakeven_upper']:,.0f}"
                    )
                    fig.add_vline(
                        x=strategy['breakeven_lower'], line_dash="dot",
                        line_color=COLORS['warning'],
                        annotation_text=f"BE: {strategy['breakeven_lower']:,.0f}"
                    )
                elif 'breakeven' in strategy:
                    fig.add_vline(
                        x=strategy['breakeven'], line_dash="dot",
                        line_color=COLORS['warning'],
                        annotation_text=f"BE: {strategy['breakeven']:,.0f}"
                    )

                fig.update_layout(
                    xaxis_title="Underlying Price at Expiry (₹)",
                    yaxis_title="Profit / Loss (₹)",
                    height=500,
                    hovermode='x unified',
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(51, 65, 85, 0.3)'),
                    yaxis=dict(gridcolor='rgba(51, 65, 85, 0.3)'),
                    margin=dict(l=0, r=0, t=20, b=0)
                )

                st.plotly_chart(fig, use_container_width=True)

    # Action buttons (Phase 4.3.5)
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Save Strategy", use_container_width=True):
            st.success("Strategy saved to watchlist!")

    with col2:
        # Execute Strategy button - prominent styling
        if st.button("Execute All Legs", use_container_width=True, type="primary"):
            st.info(f"Executing {len(strategy.get('legs', []))} legs simultaneously...")
            st.success("Orders placed successfully!")

    with col3:
        if st.button("Backtest", use_container_width=True):
            st.info("Backtesting strategy on historical data...")

    with col4:
        if st.button("Set Alert", use_container_width=True):
            st.success("Price alert configured!")


def show_directional_strategies():
    st.subheader("Directional Strategy Analyzer")

    # Strategy selection
    strat_type = st.selectbox(
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

        if "Supertrend" in strat_type:
            st.markdown(f"""
            <div style="background: {COLORS['bg_secondary']}; padding: 1.5rem; border-radius: 8px;">
                <h4 style="color: {COLORS['text_primary']}; margin-bottom: 1rem;">Supertrend Trend Following</h4>
                <div style="color: {COLORS['text_secondary']};">
                    <p><strong style="color: {COLORS['profit']};">Entry Rules:</strong></p>
                    <ul>
                        <li>BUY: Price crosses above Supertrend line</li>
                        <li>SELL: Price crosses below Supertrend line</li>
                    </ul>
                    <p><strong style="color: {COLORS['loss']};">Exit Rules:</strong></p>
                    <ul>
                        <li>Stop Loss: Supertrend line</li>
                        <li>Target: 2x risk (2:1 R:R)</li>
                    </ul>
                    <p><strong style="color: {COLORS['info']};">Best For:</strong> Strong trending markets</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        elif "Breakout" in strat_type:
            st.markdown(f"""
            <div style="background: {COLORS['bg_secondary']}; padding: 1.5rem; border-radius: 8px;">
                <h4 style="color: {COLORS['text_primary']}; margin-bottom: 1rem;">Breakout with Volume Confirmation</h4>
                <div style="color: {COLORS['text_secondary']};">
                    <p><strong style="color: {COLORS['profit']};">Entry Rules:</strong></p>
                    <ul>
                        <li>BUY: Price breaks above 20-day high with 1.5x volume</li>
                        <li>SELL: Price breaks below 20-day low with 1.5x volume</li>
                    </ul>
                    <p><strong style="color: {COLORS['loss']};">Exit Rules:</strong></p>
                    <ul>
                        <li>Stop Loss: 10% below/above breakout level</li>
                        <li>Target: Measured move (range projection)</li>
                    </ul>
                    <p><strong style="color: {COLORS['info']};">Best For:</strong> Range breakouts, consolidation exits</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        elif "Mean Reversion" in strat_type:
            st.markdown(f"""
            <div style="background: {COLORS['bg_secondary']}; padding: 1.5rem; border-radius: 8px;">
                <h4 style="color: {COLORS['text_primary']}; margin-bottom: 1rem;">Mean Reversion (Bollinger Bands + RSI)</h4>
                <div style="color: {COLORS['text_secondary']};">
                    <p><strong style="color: {COLORS['profit']};">Entry Rules:</strong></p>
                    <ul>
                        <li>BUY: Price at lower BB AND RSI &lt; 30</li>
                        <li>SELL: Price at upper BB AND RSI &gt; 70</li>
                    </ul>
                    <p><strong style="color: {COLORS['loss']};">Exit Rules:</strong></p>
                    <ul>
                        <li>Target: Middle Bollinger Band</li>
                        <li>Stop Loss: Below/above BB band</li>
                    </ul>
                    <p><strong style="color: {COLORS['info']};">Best For:</strong> Range-bound, oscillating markets</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        elif "ORB" in strat_type:
            st.markdown(f"""
            <div style="background: {COLORS['bg_secondary']}; padding: 1.5rem; border-radius: 8px;">
                <h4 style="color: {COLORS['text_primary']}; margin-bottom: 1rem;">Opening Range Breakout (15-min)</h4>
                <div style="color: {COLORS['text_secondary']};">
                    <p><strong style="color: {COLORS['profit']};">Entry Rules:</strong></p>
                    <ul>
                        <li>Identify first 15-min high/low</li>
                        <li>BUY: Breakout above OR high</li>
                        <li>SELL: Breakdown below OR low</li>
                    </ul>
                    <p><strong style="color: {COLORS['loss']};">Exit Rules:</strong></p>
                    <ul>
                        <li>Stop Loss: Opposite side of OR</li>
                        <li>Target: OR range projection</li>
                    </ul>
                    <p><strong style="color: {COLORS['info']};">Best For:</strong> Intraday trending days</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:  # S/R Bounce
            st.markdown(f"""
            <div style="background: {COLORS['bg_secondary']}; padding: 1.5rem; border-radius: 8px;">
                <h4 style="color: {COLORS['text_primary']}; margin-bottom: 1rem;">Support/Resistance Bounce</h4>
                <div style="color: {COLORS['text_secondary']};">
                    <p><strong style="color: {COLORS['profit']};">Entry Rules:</strong></p>
                    <ul>
                        <li>BUY: Bounce from support with reversal pattern</li>
                        <li>SELL: Rejection at resistance</li>
                    </ul>
                    <p><strong style="color: {COLORS['loss']};">Exit Rules:</strong></p>
                    <ul>
                        <li>Target: Next S/R level or 2:1 R:R</li>
                        <li>Stop Loss: 1% beyond S/R level</li>
                    </ul>
                    <p><strong style="color: {COLORS['info']};">Best For:</strong> Trading zones, key levels</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Signal Status")

        # Demo signal with themed styling
        st.markdown(f"""
        <div style="background: rgba(34, 197, 94, 0.15); border: 1px solid {COLORS['profit']}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <div style="color: {COLORS['profit']}; font-weight: 700; font-size: 1.25rem;">Active BUY Signal</div>
        </div>
        """, unsafe_allow_html=True)

        st.metric("Entry", "₹23,945")
        st.metric("Target", "₹24,150", delta="+205")
        st.metric("Stop Loss", "₹23,850", delta="-95")
        st.metric("Risk:Reward", "1:2.16")

        st.markdown("#### Current Status")
        st.info("**Condition:** Supertrend uptrend confirmed")
        st.info("**Momentum:** Strong bullish momentum")
        st.info("**Volume:** Above average")

        if st.button("Execute Trade", use_container_width=True, type="primary"):
            st.success("Trade executed!")


def show_spread_builder():
    st.subheader("Custom Spread Builder")

    st.info("Build custom multi-leg option spreads with precise control")

    # Spread configuration
    col1, col2 = st.columns(2)

    with col1:
        spot_price = st.number_input("Spot Price", value=23950.0, step=50.0, key="spread_spot")
        lot_size = st.number_input("Lot Size", value=75, step=25, key="spread_lot")

    with col2:
        st.selectbox(
            "Spread Type",
            ["Vertical Spread", "Horizontal Spread", "Diagonal Spread",
             "Ratio Spread", "Custom Multi-leg"],
            key="spread_type"
        )

    st.markdown("---")

    # Leg builder
    st.markdown("### Add Legs")

    num_legs = st.number_input("Number of Legs", min_value=1, max_value=6, value=2)

    legs = []
    for i in range(num_legs):
        with st.expander(f"Leg {i+1}", expanded=(i < 2)):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                action = st.selectbox("Action", ["BUY", "SELL"], key=f"action_{i}")

            with col2:
                option_type = st.selectbox("Type", ["CALL", "PUT"], key=f"type_{i}")

            with col3:
                strike = st.number_input("Strike", value=24000.0+(i*100), step=50.0, key=f"strike_{i}")

            with col4:
                premium = st.number_input("Premium", value=150.0-(i*25), step=5.0, key=f"premium_{i}")

            quantity = st.number_input("Quantity (lots)", value=1, min_value=1, max_value=10, key=f"qty_{i}")

            legs.append({
                'action': action,
                'type': option_type,
                'strike': strike,
                'premium': premium,
                'quantity': quantity
            })

    st.markdown("---")

    # Build and analyze spread
    if st.button("Build Spread", use_container_width=True, type="primary"):
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

                # Profit/Loss fills
                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=[p if p >= 0 else 0 for p in payoff_data['pnl']],
                    mode='lines',
                    line=dict(color=COLORS['profit'], width=0),
                    fill='tozeroy',
                    fillcolor='rgba(34, 197, 94, 0.2)',
                    showlegend=False
                ))

                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=[p if p < 0 else 0 for p in payoff_data['pnl']],
                    mode='lines',
                    line=dict(color=COLORS['loss'], width=0),
                    fill='tozeroy',
                    fillcolor='rgba(239, 68, 68, 0.2)',
                    showlegend=False
                ))

                fig.add_trace(go.Scatter(
                    x=payoff_data['prices'],
                    y=payoff_data['pnl'],
                    mode='lines',
                    name='P&L',
                    line=dict(color=COLORS['accent_secondary'], width=3),
                    hovertemplate='Price: ₹%{x:,.0f}<br>P&L: ₹%{y:,.0f}<extra></extra>'
                ))

                fig.add_hline(y=0, line_dash="dash", line_color=COLORS['text_muted'])
                fig.add_vline(x=spot_price, line_dash="dot", line_color=COLORS['profit'],
                             annotation_text="Spot")

                fig.update_layout(
                    xaxis_title="Price at Expiry (₹)",
                    yaxis_title="P&L (₹)",
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(51, 65, 85, 0.3)'),
                    yaxis=dict(gridcolor='rgba(51, 65, 85, 0.3)'),
                    showlegend=False
                )

                st.plotly_chart(fig, use_container_width=True)

        # Execute button
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Execute All Legs", use_container_width=True, type="primary"):
                st.success(f"Executing {len(legs)} legs simultaneously...")
        with col2:
            if st.button("Save Spread", use_container_width=True):
                st.success("Spread saved to watchlist!")
