"""
F&O Trading Dashboard - Main App
Web-based interface using Streamlit for user-friendly trading
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from analytics import TradeJournal, PerformanceMetrics, PerformanceVisualizer
from news import EconomicCalendar, SentimentAnalyzer
from rules import TradingRulesEnforcer
from risk import DrawdownManager
from strategies import OptionsStrategyBuilder

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
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.capital = 100000.0
    st.session_state.daily_pnl = 0.0
    st.session_state.trades_today = 0
    st.session_state.portfolio_heat = 0.0

    # Initialize components
    st.session_state.journal = TradeJournal("data/trade_journal.db")
    st.session_state.calendar = EconomicCalendar()
    st.session_state.rules = TradingRulesEnforcer()
    st.session_state.dd_manager = DrawdownManager(initial_capital=100000)
    st.session_state.sentiment = SentimentAnalyzer()

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/1f77b4/ffffff?text=F%26O+Trading", use_container_width=True)

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📊 Trading Signals", "🎯 Strategy Builder",
         "📈 Performance", "💼 Positions", "⚙️ Settings"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Quick Stats
    st.markdown("### Quick Stats")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Capital", f"₹{st.session_state.capital:,.0f}")
    with col2:
        pnl_delta = st.session_state.daily_pnl
        st.metric("Today's P&L", f"₹{abs(pnl_delta):,.0f}",
                 delta=f"{pnl_delta:+,.0f}", delta_color="normal")

    st.metric("Portfolio Heat", f"{st.session_state.portfolio_heat:.1f}%",
             delta=f"{st.session_state.portfolio_heat - 6.0:.1f}%",
             delta_color="inverse")

    st.metric("Trades Today", f"{st.session_state.trades_today}/5")

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

# Main content based on selected page
if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">📊 Trading Dashboard</p>', unsafe_allow_html=True)

    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
            <div class="metric-card">
                <h4>💰 Account Balance</h4>
                <h2>₹{:,.2f}</h2>
                <p>Initial: ₹100,000</p>
            </div>
        """.format(st.session_state.capital), unsafe_allow_html=True)

    with col2:
        pnl = st.session_state.daily_pnl
        card_class = "success-card" if pnl >= 0 else "danger-card"
        st.markdown("""
            <div class="{}">
                <h4>📊 Today's P&L</h4>
                <h2>{:+,.2f}</h2>
                <p>Return: {:.2f}%</p>
            </div>
        """.format(card_class, pnl, (pnl/st.session_state.capital)*100), unsafe_allow_html=True)

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
        trades = st.session_state.trades_today
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

        # Demo positions
        positions_data = {
            'Instrument': ['NIFTY 24000 CE', 'BANKNIFTY 47000 PE'],
            'Type': ['LONG', 'SHORT'],
            'Qty': [50, 25],
            'Entry': [250.00, 180.00],
            'LTP': [275.00, 160.00],
            'P&L': [1250.00, 500.00]
        }

        positions_df = pd.DataFrame(positions_data)

        # Style the dataframe
        def color_pnl(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'black'
            return f'color: {color}'

        st.dataframe(
            positions_df.style.applymap(color_pnl, subset=['P&L']),
            use_container_width=True,
            hide_index=True
        )

        total_pnl = positions_df['P&L'].sum()
        if total_pnl > 0:
            st.success(f"Total Unrealized P&L: ₹{total_pnl:,.2f}")
        else:
            st.error(f"Total Unrealized P&L: ₹{total_pnl:,.2f}")

    with col2:
        st.subheader("🎯 Live Signals")

        # Demo signals
        signals_data = {
            'Instrument': ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'],
            'Signal': ['STRONG_BUY', 'BUY', 'HOLD', 'SELL'],
            'Strength': [8, 6, 5, 7],
            'Price': [23950.00, 47200.00, 21500.00, 12300.00]
        }

        signals_df = pd.DataFrame(signals_data)

        for _, signal in signals_df.iterrows():
            sig_type = signal['Signal']

            if sig_type == 'STRONG_BUY':
                st.success(f"🚀 **{signal['Instrument']}** - {sig_type} @ ₹{signal['Price']:,.2f}")
            elif sig_type == 'BUY':
                st.info(f"📈 **{signal['Instrument']}** - {sig_type} @ ₹{signal['Price']:,.2f}")
            elif sig_type == 'SELL':
                st.warning(f"📉 **{signal['Instrument']}** - {sig_type} @ ₹{signal['Price']:,.2f}")
            else:
                st.write(f"⏸️ **{signal['Instrument']}** - {sig_type} @ ₹{signal['Price']:,.2f}")

    st.markdown("---")

    # Performance Chart
    st.subheader("📈 Equity Curve (Last 30 Days)")

    # Demo equity curve
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    equity = [100000]
    for i in range(29):
        change = pd.np.random.normal(200, 500)
        equity.append(equity[-1] + change)

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

    fig.add_hline(y=100000, line_dash="dash", line_color="gray",
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
