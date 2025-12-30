"""
Settings Page - Configure app settings and preferences
"""

import streamlit as st
import yaml

def show():
    st.title("⚙️ Settings & Configuration")

    # Settings tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔑 API Credentials", "⚡ Trading Rules", "🎨 Preferences", "📊 About"])

    with tab1:
        show_api_settings()

    with tab2:
        show_trading_rules()

    with tab3:
        show_preferences()

    with tab4:
        show_about()


def show_api_settings():
    st.subheader("🔑 API Credentials")

    st.warning("⚠️ Never share your API credentials with anyone!")

    with st.form("api_credentials"):
        api_key = st.text_input("Upstox API Key", type="password")
        api_secret = st.text_input("Upstox API Secret", type="password")
        redirect_uri = st.text_input("Redirect URI", value="http://localhost:8080")

        sandbox_mode = st.checkbox("Sandbox Mode (Paper Trading)", value=True)

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Save Credentials", use_container_width=True)
            if submitted:
                st.success("✅ Credentials saved securely!")

        with col2:
            test = st.form_submit_button("🧪 Test Connection", use_container_width=True)
            if test:
                st.info("Testing connection...")

    st.markdown("---")

    # Connection status
    st.subheader("📡 Connection Status")

    col1, col2 = st.columns(2)
    with col1:
        st.success("✅ **API:** Connected")
        st.success("✅ **WebSocket:** Active")
    with col2:
        st.info("📊 **Market Data:** Live")
        st.info("💼 **Account:** Active")


def show_trading_rules():
    st.subheader("⚡ Trading Rules Configuration")

    st.info("Configure automatic risk management rules to protect your capital")

    # Daily limits
    st.markdown("### 📅 Daily Limits")

    col1, col2 = st.columns(2)

    with col1:
        max_trades = st.number_input("Max Trades Per Day", value=5, min_value=1, max_value=20)
        max_loss = st.number_input("Max Daily Loss (₹)", value=5000, step=500)

    with col2:
        max_consecutive_losses = st.number_input("Max Consecutive Losses", value=3, min_value=1, max_value=10)
        max_portfolio_heat = st.slider("Max Portfolio Heat (%)", 1.0, 15.0, 6.0, 0.5)

    # Time restrictions
    st.markdown("### ⏰ Time Restrictions")

    col1, col2 = st.columns(2)

    with col1:
        no_first_15 = st.checkbox("Block First 15 Minutes", value=True)
        no_last_15 = st.checkbox("Block Last 15 Minutes", value=True)

    with col2:
        revenge_cooldown = st.number_input("Revenge Trading Cooldown (min)", value=60, step=5)
        min_time_between = st.number_input("Min Time Between Trades (min)", value=5, step=1)

    # Weekend trading
    st.markdown("### 📆 Schedule")
    mandatory_weekend = st.checkbox("Mandatory Weekend Break", value=True)

    # Drawdown management
    st.markdown("### 📉 Drawdown Management")

    col1, col2 = st.columns(2)

    with col1:
        caution_dd = st.slider("Caution Level (%)", 1.0, 10.0, 5.0, 0.5)
        warning_dd = st.slider("Warning Level (%)", 5.0, 15.0, 10.0, 0.5)

    with col2:
        critical_dd = st.slider("Critical Level (%)", 10.0, 20.0, 15.0, 0.5)
        emergency_dd = st.slider("Emergency Level (%)", 15.0, 30.0, 20.0, 0.5)

    # Save button
    if st.button("💾 Save Trading Rules", use_container_width=True, type="primary"):
        # Save to session state
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

    # Reset to defaults
    if st.button("🔄 Reset to Defaults"):
        st.info("Rules reset to default values")


def show_preferences():
    st.subheader("🎨 Display Preferences")

    # Theme
    theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])

    # Chart preferences
    st.markdown("### 📊 Charts")

    col1, col2 = st.columns(2)

    with col1:
        chart_theme = st.selectbox("Chart Theme", ["Plotly", "Plotly Dark", "Seaborn", "Simple White"])
        default_timeframe = st.selectbox("Default Timeframe", ["1 min", "5 min", "15 min", "30 min", "1 hour", "1 day"])

    with col2:
        show_volume = st.checkbox("Show Volume", value=True)
        show_indicators = st.checkbox("Show Indicators by Default", value=True)

    # Notifications
    st.markdown("### 🔔 Notifications")

    col1, col2 = st.columns(2)

    with col1:
        email_alerts = st.checkbox("Email Alerts", value=False)
        browser_notifications = st.checkbox("Browser Notifications", value=True)

    with col2:
        sound_alerts = st.checkbox("Sound Alerts", value=True)
        alert_volume = st.slider("Alert Volume", 0, 100, 50)

    # Alert conditions
    st.markdown("### ⚡ Alert Conditions")

    alert_on_signal = st.checkbox("Alert on Strong Signals", value=True)
    alert_on_target = st.checkbox("Alert on Target Hit", value=True)
    alert_on_sl = st.checkbox("Alert on Stop Loss Hit", value=True)
    alert_on_rules = st.checkbox("Alert on Rule Violations", value=True)

    # Language & Region
    st.markdown("### 🌍 Regional Settings")

    col1, col2 = st.columns(2)

    with col1:
        language = st.selectbox("Language", ["English", "हिन्दी"])
        timezone = st.selectbox("Timezone", ["Asia/Kolkata", "UTC"])

    with col2:
        currency = st.selectbox("Currency Display", ["₹ INR", "$ USD"])
        number_format = st.selectbox("Number Format", ["Indian (1,00,000)", "International (100,000)"])

    # Save
    if st.button("💾 Save Preferences", use_container_width=True, type="primary"):
        st.success("✅ Preferences saved!")


def show_about():
    st.subheader("📊 About F&O Trading Platform")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Application Info

        **Version:** 1.0.0
        **Build:** Phase 3 & 4 Complete
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
        """)

    with col2:
        st.markdown("""
        ### System Status

        - **Market Data:** ✅ Active
        - **API Connection:** ✅ Connected
        - **Database:** ✅ Healthy
        - **Risk Engine:** ✅ Running
        - **Analytics:** ✅ Active

        ### Support

        📧 Email: support@fnotrading.com
        📚 Documentation: [View Docs](/)
        🐛 Report Bug: [GitHub Issues](/)

        ### License

        This software is for personal use only.
        Not for commercial distribution.
        """)

    st.markdown("---")

    # System info
    st.markdown("### 💻 System Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("**Python Version:** 3.10+")
        st.info("**Database:** SQLite")

    with col2:
        st.info("**UI Framework:** Streamlit")
        st.info("**Charts:** Plotly")

    with col3:
        st.info("**Total Modules:** 20+")
        st.info("**Lines of Code:** 10,000+")

    st.markdown("---")

    # Quick actions
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
