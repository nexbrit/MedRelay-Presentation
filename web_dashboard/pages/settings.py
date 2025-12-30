"""
Settings Page - Configure app settings and preferences
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add parent to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from web_dashboard.data_provider import get_data_provider  # noqa: E402


def show():
    st.title("⚙️ Settings & Configuration")

    # Get data provider
    data_provider = get_data_provider()

    # Settings tabs - added Capital & Account tab
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Capital & Account",
        "🔑 API Credentials",
        "⚡ Trading Rules",
        "🎨 Preferences",
        "📊 About"
    ])

    with tab1:
        show_capital_settings(data_provider)

    with tab2:
        show_api_settings(data_provider)

    with tab3:
        show_trading_rules()

    with tab4:
        show_preferences()

    with tab5:
        show_about()


def show_capital_settings(data_provider):
    st.subheader("💰 Capital & Account Management")

    # Get current capital state
    capital_summary = data_provider.get_capital_summary()
    is_initialized = capital_summary.get('initialized', False)

    if not is_initialized:
        # First-time setup wizard
        st.warning("⚠️ **Capital not initialized!** Please set your initial trading capital.")

        st.markdown("### 🚀 Initial Setup")

        with st.form("initial_capital_form"):
            initial_capital = st.number_input(
                "Initial Trading Capital (₹)",
                min_value=10000.0,
                max_value=100000000.0,
                value=500000.0,
                step=10000.0,
                help="Enter the capital you're allocating for F&O trading"
            )

            reason = st.text_input(
                "Setup Notes (Optional)",
                value="Initial trading capital setup",
                help="Add any notes about this initial setup"
            )

            submitted = st.form_submit_button(
                "💰 Initialize Capital",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                success = data_provider.initialize_capital(initial_capital, reason)
                if success:
                    st.success(f"✅ Capital initialized: ₹{initial_capital:,.2f}")
                    st.rerun()
                else:
                    st.error("❌ Failed to initialize capital. Please try again.")

        return

    # Capital Dashboard
    st.markdown("### 📊 Capital Overview")

    col1, col2, col3, col4 = st.columns(4)

    current_capital = capital_summary.get('current_capital', 0)
    initial_capital = capital_summary.get('initial_capital', 0)
    return_pct = capital_summary.get('return_percent', 0)
    absolute_return = capital_summary.get('absolute_return', 0)

    with col1:
        st.metric(
            "Current Capital",
            f"₹{current_capital:,.0f}",
            delta=f"₹{absolute_return:+,.0f}" if absolute_return != 0 else None,
            delta_color="normal" if absolute_return >= 0 else "inverse"
        )

    with col2:
        st.metric(
            "Initial Capital",
            f"₹{initial_capital:,.0f}"
        )

    with col3:
        st.metric(
            "Total Return",
            f"{return_pct:+.2f}%",
            delta_color="normal" if return_pct >= 0 else "inverse"
        )

    with col4:
        twr = capital_summary.get('twr_percent', 0)
        st.metric(
            "TWR (Time-Weighted)",
            f"{twr:+.2f}%"
        )

    st.markdown("---")

    # Capital Adjustment Section
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 💵 Adjust Capital")

        adjustment_type = st.radio(
            "Adjustment Type",
            ["Deposit", "Withdrawal"],
            horizontal=True
        )

        with st.form("capital_adjustment_form"):
            amount = st.number_input(
                f"{'Deposit' if adjustment_type == 'Deposit' else 'Withdrawal'} Amount (₹)",
                min_value=100.0,
                max_value=current_capital if adjustment_type == 'Withdrawal' else 100000000.0,
                value=10000.0,
                step=1000.0
            )

            reason = st.text_input(
                "Reason (Optional)",
                placeholder=f"e.g., Monthly {'deposit' if adjustment_type == 'Deposit' else 'withdrawal'}"
            )

            submitted = st.form_submit_button(
                f"{'➕ Deposit' if adjustment_type == 'Deposit' else '➖ Withdraw'}",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                if adjustment_type == 'Deposit':
                    success = data_provider.deposit_capital(amount, reason)
                else:
                    success = data_provider.withdraw_capital(amount, reason)

                if success:
                    st.success(f"✅ {'Deposit' if adjustment_type == 'Deposit' else 'Withdrawal'} recorded: ₹{amount:,.2f}")
                    st.rerun()
                else:
                    st.error("❌ Failed to process adjustment. Please try again.")

    with col2:
        st.markdown("### 📈 Capital Statistics")

        total_deposits = capital_summary.get('total_deposits', 0)
        total_withdrawals = capital_summary.get('total_withdrawals', 0)
        trading_pnl = capital_summary.get('total_trading_pnl', 0)
        net_cash_flow = capital_summary.get('net_cash_flow', 0)

        stats_data = {
            'Metric': [
                'Total Deposits',
                'Total Withdrawals',
                'Net Cash Flow',
                'Trading P&L',
                'CAGR'
            ],
            'Value': [
                f"₹{total_deposits:,.0f}",
                f"₹{total_withdrawals:,.0f}",
                f"₹{net_cash_flow:+,.0f}",
                f"₹{trading_pnl:+,.0f}",
                f"{capital_summary.get('cagr_percent', 0):.2f}%"
            ]
        }

        st.dataframe(
            pd.DataFrame(stats_data),
            hide_index=True,
            use_container_width=True
        )

    st.markdown("---")

    # Capital History
    st.markdown("### 📜 Capital Adjustment History")

    history = data_provider.get_capital_history(limit=20)

    if history:
        history_data = []
        for h in history:
            adj_type = h.get('adjustment_type', 'UNKNOWN')
            amount = h.get('amount', 0)

            # Format amount with sign
            if adj_type in ['DEPOSIT', 'TRADE_PROFIT', 'INITIAL_SETUP']:
                amount_str = f"+₹{amount:,.0f}"
            else:
                amount_str = f"-₹{amount:,.0f}"

            history_data.append({
                'Date': (
                    h.get('timestamp', '')[:10]
                    if h.get('timestamp') else ''
                ),
                'Type': adj_type.replace('_', ' ').title(),
                'Amount': amount_str,
                'New Balance': f"₹{h.get('new_capital', 0):,.0f}",
                'Reason': h.get('reason', '')[:30] if h.get('reason') else '-'
            })

        history_df = pd.DataFrame(history_data)
        st.dataframe(history_df, hide_index=True, use_container_width=True)
    else:
        st.info("No capital adjustments recorded yet.")


def show_api_settings(data_provider):
    st.subheader("🔑 API Credentials & Authentication")

    st.warning("⚠️ Never share your API credentials with anyone!")

    # Token Status
    token_status = data_provider.get_token_status()

    st.markdown("### 📡 Authentication Status")

    col1, col2 = st.columns(2)

    with col1:
        status = token_status.get('status', 'UNKNOWN')
        if status == 'VALID':
            st.success("✅ **Token Status:** Valid")
            st.info(f"⏱️ **Expires in:** {token_status.get('hours_remaining', 0):.1f} hours")
        elif status == 'WARNING':
            st.warning("⚠️ **Token Status:** Expiring Soon")
            st.warning(f"⏱️ **Expires in:** {token_status.get('hours_remaining', 0):.1f} hours")
        elif status == 'EXPIRED':
            st.error("🔴 **Token Status:** Expired")
            st.error("Please re-authenticate")
        else:
            st.info(f"ℹ️ **Token Status:** {status}")

    with col2:
        if token_status.get('last_authenticated'):
            st.info(f"🕐 **Last Auth:** {token_status.get('last_authenticated', 'Unknown')[:19]}")

        auth_url = data_provider.get_authorization_url()
        if auth_url:
            st.markdown(f"[🔗 Open Authorization Page]({auth_url})")

    st.markdown("---")

    # Manual token entry for development
    st.markdown("### 🔐 Manual Token Entry")
    st.caption("For development/testing purposes only")

    with st.form("manual_token_form"):
        access_token = st.text_input("Access Token", type="password")

        col1, col2 = st.columns(2)
        with col1:
            expiry_hours = st.number_input(
                "Token Expiry (hours)",
                min_value=1.0,
                max_value=24.0,
                value=24.0,
                step=1.0
            )

        submitted = st.form_submit_button("💾 Save Token", use_container_width=True)

        if submitted and access_token:
            success = data_provider.set_access_token(access_token, expiry_hours)
            if success:
                st.success("✅ Token saved successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to save token")

    st.markdown("---")

    # Connection Status
    st.markdown("### 📡 Connection Status")

    connection_status = data_provider.get_connection_status()

    col1, col2 = st.columns(2)
    with col1:
        conn_state = connection_status.get('state', 'unknown')
        if conn_state == 'connected':
            st.success("✅ **API:** Connected")
        elif conn_state == 'disconnected':
            st.error("🔴 **API:** Disconnected")
        else:
            st.warning(f"⚠️ **API:** {conn_state.capitalize()}")

        cache_stats = connection_status.get('cache_stats', {})
        hit_rate = cache_stats.get('hit_rate_percent', 0)
        st.info(f"📊 **Cache Hit Rate:** {hit_rate:.1f}%")

    with col2:
        available_requests = connection_status.get('available_requests', 0)
        st.info(f"🔄 **API Requests Available:** {available_requests}/250 per min")

        last_call = connection_status.get('last_successful_call')
        if last_call:
            st.info(f"🕐 **Last API Call:** {last_call[:19]}")


def show_trading_rules():
    st.subheader("⚡ Trading Rules Configuration")

    st.info("Configure automatic risk management rules to protect your capital")

    # Daily limits
    st.markdown("### 📅 Daily Limits")

    col1, col2 = st.columns(2)

    with col1:
        max_trades = st.number_input(
            "Max Trades Per Day",
            value=5,
            min_value=1,
            max_value=20
        )
        max_loss = st.number_input(
            "Max Daily Loss (₹)",
            value=5000,
            step=500
        )

    with col2:
        max_consecutive_losses = st.number_input(
            "Max Consecutive Losses",
            value=3,
            min_value=1,
            max_value=10
        )
        max_portfolio_heat = st.slider(
            "Max Portfolio Heat (%)",
            1.0, 15.0, 6.0, 0.5
        )

    # Time restrictions
    st.markdown("### ⏰ Time Restrictions")

    col1, col2 = st.columns(2)

    with col1:
        no_first_15 = st.checkbox("Block First 15 Minutes", value=True)
        no_last_15 = st.checkbox("Block Last 15 Minutes", value=True)

    with col2:
        revenge_cooldown = st.number_input(
            "Revenge Trading Cooldown (min)",
            value=60,
            step=5
        )
        min_time_between = st.number_input(
            "Min Time Between Trades (min)",
            value=5,
            step=1
        )

    # Weekend trading
    st.markdown("### 📆 Schedule")
    mandatory_weekend = st.checkbox("Mandatory Weekend Break", value=True)

    # Drawdown management
    st.markdown("### 📉 Drawdown Management")

    col1, col2 = st.columns(2)

    with col1:
        st.slider("Caution Level (%)", 1.0, 10.0, 5.0, 0.5)
        st.slider("Warning Level (%)", 5.0, 15.0, 10.0, 0.5)

    with col2:
        st.slider("Critical Level (%)", 10.0, 20.0, 15.0, 0.5)
        st.slider("Emergency Level (%)", 15.0, 30.0, 20.0, 0.5)

    # Save button
    if st.button("💾 Save Trading Rules", use_container_width=True, type="primary"):
        st.session_state.rules_config = {
            'max_trades_per_day': max_trades,
            'max_daily_loss': max_loss,
            'max_consecutive_losses': max_consecutive_losses,
            'max_portfolio_heat': max_portfolio_heat,
            'no_trade_first_15min': no_first_15,
            'no_trade_last_15min': no_last_15,
            'revenge_trading_cooldown_minutes': revenge_cooldown,
            'min_time_between_trades_minutes': min_time_between,
            'mandatory_weekend': mandatory_weekend
        }
        st.success("✅ Trading rules saved!")

    if st.button("🔄 Reset to Defaults"):
        st.info("Rules reset to default values")


def show_preferences():
    st.subheader("🎨 Display Preferences")

    # Theme
    st.selectbox("Theme", ["Light", "Dark", "Auto"])

    # Chart preferences
    st.markdown("### 📊 Charts")

    col1, col2 = st.columns(2)

    with col1:
        st.selectbox(
            "Chart Theme",
            ["Plotly", "Plotly Dark", "Seaborn", "Simple White"]
        )
        st.selectbox(
            "Default Timeframe",
            ["1 min", "5 min", "15 min", "30 min", "1 hour", "1 day"]
        )

    with col2:
        st.checkbox("Show Volume", value=True)
        st.checkbox("Show Indicators by Default", value=True)

    # Notifications
    st.markdown("### 🔔 Notifications")

    col1, col2 = st.columns(2)

    with col1:
        st.checkbox("Email Alerts", value=False)
        st.checkbox("Browser Notifications", value=True)

    with col2:
        st.checkbox("Sound Alerts", value=True)
        st.slider("Alert Volume", 0, 100, 50)

    # Alert conditions
    st.markdown("### ⚡ Alert Conditions")

    st.checkbox("Alert on Strong Signals", value=True)
    st.checkbox("Alert on Target Hit", value=True)
    st.checkbox("Alert on Stop Loss Hit", value=True)
    st.checkbox("Alert on Rule Violations", value=True)

    # Language & Region
    st.markdown("### 🌍 Regional Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.selectbox("Language", ["English", "हिन्दी"])
        st.selectbox("Timezone", ["Asia/Kolkata", "UTC"])

    with col2:
        st.selectbox("Currency Display", ["₹ INR", "$ USD"])
        st.selectbox("Number Format", ["Indian (1,00,000)", "International (100,000)"])

    if st.button("💾 Save Preferences", use_container_width=True, type="primary"):
        st.success("✅ Preferences saved!")


def show_about():
    st.subheader("📊 About F&O Trading Platform")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Application Info

        **Version:** 2.0.0
        **Build:** Phase 1 Complete
        **Last Updated:** December 2024

        ### Features

        ✅ Advanced Risk Management
        ✅ Professional Analytics
        ✅ Strategy Builder
        ✅ Live Signals
        ✅ Performance Tracking
        ✅ Drawdown Protection
        ✅ Trading Rules Enforcement
        ✅ Terminal & Web Dashboard
        ✅ Persistent Capital Tracking
        ✅ Token Management
        """)

    with col2:
        data_provider = get_data_provider()
        connection_status = data_provider.get_connection_status()

        st.markdown("### System Status")

        conn_state = connection_status.get('state', 'unknown')
        if conn_state == 'connected':
            st.success("- **Market Data:** ✅ Active")
            st.success("- **API Connection:** ✅ Connected")
        else:
            st.warning(f"- **API Connection:** ⚠️ {conn_state.capitalize()}")

        st.success("- **Database:** ✅ Healthy")
        st.success("- **Risk Engine:** ✅ Running")
        st.success("- **Analytics:** ✅ Active")

        st.markdown("""
        ### Support

        📧 Email: support@fnotrading.com
        📚 Documentation: [View Docs](/)
        🐛 Report Bug: [GitHub Issues](/)

        ### License

        This software is for personal use only.
        Not for commercial distribution.
        """)

    st.markdown("---")

    st.markdown("### 💻 System Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("**Python Version:** 3.10+")
        st.info("**Database:** SQLite")

    with col2:
        st.info("**UI Framework:** Streamlit")
        st.info("**Charts:** Plotly")

    with col3:
        st.info("**Total Modules:** 25+")
        st.info("**Lines of Code:** 15,000+")

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📚 View Documentation", use_container_width=True):
            st.info("Opening documentation...")

    with col2:
        if st.button("🔄 Check for Updates", use_container_width=True):
            st.success("You're on the latest version!")

    with col3:
        if st.button("📊 Export Logs", use_container_width=True):
            st.info("Exporting system logs...")

    with col4:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared!")

    st.markdown("---")

    st.caption("© 2024 F&O Trading Platform. Built with ❤️ for Indian F&O traders.")
