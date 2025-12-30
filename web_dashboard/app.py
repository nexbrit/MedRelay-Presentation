"""
F&O Trading Dashboard - Main App
Web-based interface using Streamlit for user-friendly trading
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from analytics import TradeJournal
from news import EconomicCalendar, SentimentAnalyzer
from rules import TradingRulesEnforcer
from risk import DrawdownManager
from web_dashboard.data_provider import get_data_provider

# Page configuration
st.set_page_config(
    page_title="F&O Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .success-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
    }
    .danger-card {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
    }
    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
    }
    .connection-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 5px;
    }
    .connected { background-color: #22c55e; }
    .disconnected { background-color: #ef4444; }
    .reconnecting { background-color: #f59e0b; }
    .token-warning {
        background-color: #f59e0b;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .token-expired {
        background-color: #ef4444;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize data provider
data_provider = get_data_provider()

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.trades_today = 0
    st.session_state.portfolio_heat = 0.0

    # Initialize components
    st.session_state.journal = TradeJournal("data/trade_journal.db")
    st.session_state.calendar = EconomicCalendar()
    st.session_state.rules = TradingRulesEnforcer()
    st.session_state.sentiment = SentimentAnalyzer()

# Get live data
capital_summary = data_provider.get_capital_summary()
current_capital = capital_summary.get('current_capital', 100000)
initial_capital = capital_summary.get('initial_capital', 100000)

# Initialize drawdown manager with actual capital
if 'dd_manager' not in st.session_state or st.session_state.get('dd_capital') != initial_capital:
    st.session_state.dd_manager = DrawdownManager(initial_capital=initial_capital)
    st.session_state.dd_capital = initial_capital

# Get positions and calculate P&L
positions = data_provider.get_positions()
portfolio_summary = data_provider.get_portfolio_summary()
unrealized_pnl = portfolio_summary.get('unrealized_pnl', {})
daily_pnl = unrealized_pnl.get('total', 0)

# Update session state with live data
st.session_state.capital = current_capital
st.session_state.daily_pnl = daily_pnl

# Calculate portfolio heat from positions
position_risks = sum(
    abs(p.get('quantity', 0)) * p.get('average_price', 0) * 0.02
    for p in positions
)
portfolio_heat = (position_risks / current_capital * 100) if current_capital > 0 else 0
st.session_state.portfolio_heat = min(portfolio_heat, 100)

# Sidebar
with st.sidebar:
    st.markdown("### F&O Trading Platform")

    # Connection status indicator
    connection_status = data_provider.get_connection_status()
    conn_state = connection_status.get('state', 'unknown')
    conn_class = 'connected' if conn_state == 'connected' else 'disconnected' if conn_state == 'disconnected' else 'reconnecting'
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span class="connection-dot {conn_class}"></span>
            <span>API: {conn_state.capitalize()}</span>
        </div>
    """, unsafe_allow_html=True)

    # Token status warning
    token_status = data_provider.get_token_status()
    if token_status.get('status') == 'WARNING':
        st.markdown(f"""
            <div class="token-warning">
                ⚠️ Token expires in {token_status.get('hours_remaining', 0):.1f}h
            </div>
        """, unsafe_allow_html=True)
    elif token_status.get('status') in ['EXPIRED', 'CRITICAL']:
        st.markdown(f"""
            <div class="token-expired">
                🔴 {token_status.get('message', 'Token expired')}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📊 Trading Signals", "🎯 Strategy Builder",
         "📈 Performance", "💼 Positions", "⚙️ Settings"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Quick Stats from live data
    st.markdown("### Quick Stats")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Capital", f"₹{current_capital:,.0f}")
    with col2:
        pnl_delta = daily_pnl
        st.metric("Today's P&L", f"₹{abs(pnl_delta):,.0f}",
                 delta=f"{pnl_delta:+,.0f}", delta_color="normal")

    st.metric("Portfolio Heat", f"{st.session_state.portfolio_heat:.1f}%",
             delta=f"{st.session_state.portfolio_heat - 6.0:.1f}%",
             delta_color="inverse")

    orders_summary = data_provider.get_orders_summary()
    trades_today = orders_summary.get('completed_orders', st.session_state.trades_today)
    st.metric("Trades Today", f"{trades_today}/5")

    st.markdown("---")

    # Market Status
    st.markdown("### Market Status")
    market_time = datetime.now().time()
    if market_time.hour < 9 or (market_time.hour == 9 and market_time.minute < 15):
        st.info("🌅 Pre-market")
    elif market_time.hour >= 15 and market_time.minute >= 30:
        st.info("🌆 Market Closed")
    else:
        st.success("🟢 Market Open")

    # Index quotes
    st.markdown("### Market Indices")
    index_quotes = data_provider.get_index_quotes()

    for name, quote in index_quotes.items():
        if quote:
            price = quote.get('last_price', 0)
            change = quote.get('change', 0) or (price - quote.get('open', price))
            change_pct = quote.get('change_percent', 0) or (
                (change / quote.get('open', price) * 100) if quote.get('open', 0) else 0
            )
            delta_color = "normal" if change >= 0 else "inverse"
            st.metric(name, f"₹{price:,.2f}", delta=f"{change:+.2f} ({change_pct:+.2f}%)",
                     delta_color=delta_color)

    # Show demo data indicator if applicable
    if any(q.get('demo', False) for q in index_quotes.values()):
        st.caption("📊 Demo data - Authenticate for live")

    st.markdown("---")

    # Current regime
    st.markdown("### Market Regime")
    regime = st.selectbox("", ["STRONG_UPTREND", "WEAK_UPTREND", "RANGING",
                                 "WEAK_DOWNTREND", "STRONG_DOWNTREND"],
                          label_visibility="collapsed")

    if regime in ["STRONG_UPTREND", "WEAK_UPTREND"]:
        st.success(f"📈 {regime}")
    elif regime == "RANGING":
        st.warning(f"↔️ {regime}")
    else:
        st.error(f"📉 {regime}")

    # Last updated timestamp
    st.caption(f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}")

# Main content based on selected page
if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">📊 Trading Dashboard</p>', unsafe_allow_html=True)

    # Capital initialization check
    if not data_provider.is_capital_initialized():
        st.warning("⚠️ **Capital not initialized!** Go to Settings to set your trading capital.")

    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
            <div class="metric-card">
                <h4>💰 Account Balance</h4>
                <h2>₹{:,.2f}</h2>
                <p>Initial: ₹{:,.0f}</p>
            </div>
        """.format(current_capital, initial_capital), unsafe_allow_html=True)

    with col2:
        pnl = daily_pnl
        card_class = "success-card" if pnl >= 0 else "danger-card"
        return_pct = (pnl / current_capital * 100) if current_capital > 0 else 0
        st.markdown("""
            <div class="{}">
                <h4>📊 Today's P&L</h4>
                <h2>₹{:+,.2f}</h2>
                <p>Return: {:.2f}%</p>
            </div>
        """.format(card_class, pnl, return_pct), unsafe_allow_html=True)

    with col3:
        heat = st.session_state.portfolio_heat
        card_class = "success-card" if heat < 3 else "warning-card" if heat < 5 else "danger-card"
        st.markdown("""
            <div class="{}">
                <h4>🔥 Portfolio Heat</h4>
                <h2>{:.1f}%</h2>
                <p>Max: 6.0%</p>
            </div>
        """.format(card_class, heat), unsafe_allow_html=True)

    with col4:
        trades = trades_today
        st.markdown("""
            <div class="metric-card">
                <h4>📈 Trades Today</h4>
                <h2>{}/5</h2>
                <p>Remaining: {}</p>
            </div>
        """.format(trades, 5-trades), unsafe_allow_html=True)

    st.markdown("---")

    # Trading Rules Status
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🛡️ Trading Rules Status")

        can_trade, reason = st.session_state.rules.can_trade(
            portfolio_heat=st.session_state.portfolio_heat
        )

        if can_trade:
            st.success(f"✅ **Trading Allowed** - {reason}")
        else:
            st.error(f"⛔ **Trading Blocked** - {reason}")

        # Show rule details
        with st.expander("📋 View All Rules"):
            rules = st.session_state.rules.get_all_rules()

            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Daily Limits:**")
                st.write(f"• Max Trades: {rules['max_trades_per_day']}")
                st.write(f"• Max Losses: {rules['max_consecutive_losses']}")
                st.write(f"• Max Loss: ₹{rules['max_daily_loss']:,}")

            with col_b:
                st.write("**Time Restrictions:**")
                st.write(f"• First 15 min: {'Blocked' if rules['no_trade_first_15min'] else 'Allowed'}")
                st.write(f"• Last 15 min: {'Blocked' if rules['no_trade_last_15min'] else 'Allowed'}")
                st.write(f"• Cooldown: {rules['revenge_trading_cooldown_minutes']} min")

    with col2:
        st.subheader("📅 Upcoming Events")

        upcoming = st.session_state.calendar.get_upcoming_events(days=7)

        if not upcoming.empty:
            for _, event in upcoming.head(5).iterrows():
                date_str = pd.to_datetime(event['date']).strftime('%b %d')
                st.write(f"**{date_str}** - {event['event']}")
        else:
            st.info("No upcoming events")

    st.markdown("---")

    # Active Positions & Signals
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💼 Active Positions")

        if positions:
            # Convert positions to DataFrame
            positions_data = {
                'Instrument': [p.get('symbol', p.get('instrument', '')) for p in positions],
                'Type': [p.get('direction', 'LONG') for p in positions],
                'Qty': [abs(p.get('quantity', 0)) for p in positions],
                'Entry': [p.get('average_price', 0) for p in positions],
                'LTP': [p.get('last_price', 0) for p in positions],
                'P&L': [p.get('unrealized_pnl', p.get('pnl', 0)) for p in positions]
            }

            positions_df = pd.DataFrame(positions_data)

            # Style the dataframe
            def color_pnl(val):
                color = 'green' if val > 0 else 'red' if val < 0 else 'black'
                return f'color: {color}'

            st.dataframe(
                positions_df.style.map(color_pnl, subset=['P&L']),
                use_container_width=True,
                hide_index=True
            )

            total_pnl = positions_df['P&L'].sum()
            if total_pnl > 0:
                st.success(f"Total Unrealized P&L: ₹{total_pnl:,.2f}")
            else:
                st.error(f"Total Unrealized P&L: ₹{total_pnl:,.2f}")

            # Show demo indicator
            if any(p.get('demo', False) for p in positions):
                st.caption("📊 Demo positions - Authenticate for live data")
        else:
            st.info("No active positions")

    with col2:
        st.subheader("🎯 Live Signals")

        # Generate signals from live index data
        signals = []
        for name, quote in index_quotes.items():
            if name != 'VIX' and quote:
                price = quote.get('last_price', 0)
                open_price = quote.get('open', price)

                if open_price > 0:
                    change_pct = (price - open_price) / open_price * 100
                else:
                    change_pct = 0

                # Simple signal logic based on price change
                if change_pct > 0.5:
                    signal = 'STRONG_BUY'
                elif change_pct > 0.2:
                    signal = 'BUY'
                elif change_pct < -0.5:
                    signal = 'STRONG_SELL'
                elif change_pct < -0.2:
                    signal = 'SELL'
                else:
                    signal = 'HOLD'

                signals.append({
                    'Instrument': name,
                    'Signal': signal,
                    'Price': price,
                    'Change': change_pct
                })

        for sig in signals:
            sig_type = sig['Signal']
            if sig_type == 'STRONG_BUY':
                st.success(f"🚀 **{sig['Instrument']}** - {sig_type} @ ₹{sig['Price']:,.2f}")
            elif sig_type == 'BUY':
                st.info(f"📈 **{sig['Instrument']}** - {sig_type} @ ₹{sig['Price']:,.2f}")
            elif sig_type in ['SELL', 'STRONG_SELL']:
                st.warning(f"📉 **{sig['Instrument']}** - {sig_type} @ ₹{sig['Price']:,.2f}")
            else:
                st.write(f"⏸️ **{sig['Instrument']}** - {sig_type} @ ₹{sig['Price']:,.2f}")

    st.markdown("---")

    # Portfolio Greeks (for options positions)
    greeks = data_provider.get_portfolio_greeks()
    if portfolio_summary.get('options_positions', 0) > 0:
        st.subheader("📐 Portfolio Greeks")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Delta", f"{greeks.get('delta', 0):.2f}")
        with col2:
            st.metric("Gamma", f"{greeks.get('gamma', 0):.4f}")
        with col3:
            st.metric("Theta", f"₹{greeks.get('theta', 0):.2f}/day")
        with col4:
            st.metric("Vega", f"{greeks.get('vega', 0):.2f}")

        st.markdown("---")

    # Performance Chart
    st.subheader("📈 Equity Curve (Last 30 Days)")

    # Get capital history for equity curve
    capital_history = data_provider.get_capital_history(limit=30)

    if capital_history:
        # Build equity curve from history
        history_df = pd.DataFrame(capital_history)
        history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
        history_df = history_df.sort_values('timestamp')

        dates = history_df['timestamp'].tolist()
        equity = history_df['new_capital'].tolist()
    else:
        # Demo equity curve based on current capital
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        np.random.seed(42)  # Consistent demo data
        equity = [initial_capital]
        for i in range(29):
            change = np.random.normal(200, 500)
            equity.append(equity[-1] + change)
        equity[-1] = current_capital  # End at current capital

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=equity,
        mode='lines',
        name='Equity',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))

    fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray",
                  annotation_text="Initial Capital")

    fig.update_layout(
        height=400,
        hovermode='x unified',
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

elif page == "📊 Trading Signals":
    from pages import trading_signals
    trading_signals.show()

elif page == "🎯 Strategy Builder":
    from pages import strategy_builder
    strategy_builder.show()

elif page == "📈 Performance":
    from pages import performance
    performance.show()

elif page == "💼 Positions":
    from pages import positions
    positions.show()

elif page == "⚙️ Settings":
    from pages import settings
    settings.show()

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🔒 Secure • 📊 Real-time • 🎯 Professional")
with col2:
    st.caption(f"⏰ Last updated: {datetime.now().strftime('%H:%M:%S')}")
with col3:
    st.caption("© 2024 F&O Trading Platform")
