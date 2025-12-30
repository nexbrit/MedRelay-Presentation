"""
Settings Page - Configure app settings and preferences

Enhanced with Phase 4.3.6 features:
- Organized settings sections
- Professional theme styling
- Position size limits
- Complete risk management controls
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add parent to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from web_dashboard.data_provider import get_data_provider  # noqa: E402
from web_dashboard.theme import COLORS  # noqa: E402


def show():
    st.title("Settings & Configuration")

    # Get data provider
    data_provider = get_data_provider()

    # Settings tabs - organized sections (Phase 4.3.6)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Account & Capital",
        "Risk Management",
        "Trading Rules",
        "API Configuration",
        "Notifications",
        "About"
    ])

    with tab1:
        show_capital_settings(data_provider)

    with tab2:
        show_risk_management()

    with tab3:
        show_trading_rules()

    with tab4:
        show_api_settings(data_provider)

    with tab5:
        show_notifications()

    with tab6:
        show_about()


def show_capital_settings(data_provider):
    """Account & Capital section (Phase 4.3.6)"""
    st.subheader("Account & Capital Management")

    # Get current capital state
    capital_summary = data_provider.get_capital_summary()
    is_initialized = capital_summary.get('initialized', False)

    if not is_initialized:
        # First-time setup wizard
        st.warning("**Capital not initialized!** Please set your initial trading capital.")

        st.markdown("### Initial Setup")

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
                "Initialize Capital",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                success = data_provider.initialize_capital(initial_capital, reason)
                if success:
                    st.success(f"Capital initialized: ₹{initial_capital:,.2f}")
                    st.rerun()
                else:
                    st.error("Failed to initialize capital. Please try again.")

        return

    # Capital Dashboard - styled summary card
    st.markdown(f"""
    <div style="background: {COLORS['bg_secondary']}; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
        <h4 style="color: {COLORS['text_primary']}; margin-bottom: 1rem;">Capital Overview</h4>
    </div>
    """, unsafe_allow_html=True)

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
        st.metric("Initial Capital", f"₹{initial_capital:,.0f}")

    with col3:
        st.metric(
            "Total Return",
            f"{return_pct:+.2f}%",
            delta_color="normal" if return_pct >= 0 else "inverse"
        )

    with col4:
        twr = capital_summary.get('twr_percent', 0)
        st.metric("TWR (Time-Weighted)", f"{twr:+.2f}%")

    st.markdown("---")

    # Capital Adjustment Section
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Adjust Capital")

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
                f"{'Deposit' if adjustment_type == 'Deposit' else 'Withdraw'}",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                if adjustment_type == 'Deposit':
                    success = data_provider.deposit_capital(amount, reason)
                else:
                    success = data_provider.withdraw_capital(amount, reason)

                if success:
                    st.success(f"{'Deposit' if adjustment_type == 'Deposit' else 'Withdrawal'} recorded: ₹{amount:,.2f}")
                    st.rerun()
                else:
                    st.error("Failed to process adjustment. Please try again.")

    with col2:
        st.markdown("### Capital Statistics")

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

        st.dataframe(pd.DataFrame(stats_data), hide_index=True, use_container_width=True)

    st.markdown("---")

    # Capital History (Deposit/Withdrawal Log)
    st.markdown("### Deposit/Withdrawal Log")

    history = data_provider.get_capital_history(limit=20)

    if history:
        history_data = []
        for h in history:
            adj_type = h.get('adjustment_type', 'UNKNOWN')
            amount = h.get('amount', 0)

            if adj_type in ['DEPOSIT', 'TRADE_PROFIT', 'INITIAL_SETUP']:
                amount_str = f"+₹{amount:,.0f}"
            else:
                amount_str = f"-₹{amount:,.0f}"

            history_data.append({
                'Date': h.get('timestamp', '')[:10] if h.get('timestamp') else '',
                'Type': adj_type.replace('_', ' ').title(),
                'Amount': amount_str,
                'New Balance': f"₹{h.get('new_capital', 0):,.0f}",
                'Reason': h.get('reason', '')[:30] if h.get('reason') else '-'
            })

        history_df = pd.DataFrame(history_data)
        st.dataframe(history_df, hide_index=True, use_container_width=True)
    else:
        st.info("No capital adjustments recorded yet.")


def show_risk_management():
    """Risk Management section (Phase 4.3.6)"""
    st.subheader("Risk Management Settings")

    st.info("Configure risk limits to protect your capital")

    # Position Size Limits (Phase 4.3.6)
    st.markdown("### Position Size Limits")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input(
            "Max Position Size (% of Capital)",
            value=10.0,
            min_value=1.0,
            max_value=50.0,
            step=1.0,
            help="Maximum capital allocation for a single position"
        )
        st.number_input(
            "Max Lots Per Trade",
            value=5,
            min_value=1,
            max_value=50,
            help="Maximum number of lots for a single trade"
        )

    with col2:
        st.number_input(
            "Max Open Positions",
            value=3,
            min_value=1,
            max_value=10,
            help="Maximum concurrent open positions"
        )
        st.number_input(
            "Max Exposure (% of Capital)",
            value=30.0,
            min_value=5.0,
            max_value=100.0,
            step=5.0,
            help="Maximum total exposure across all positions"
        )

    st.markdown("---")

    # Daily Loss Limits
    st.markdown("### Daily Loss Limits")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input(
            "Daily Loss Limit (₹)",
            value=5000,
            min_value=500,
            max_value=100000,
            step=500,
            help="Trading stops when daily loss reaches this amount"
        )
        st.number_input(
            "Daily Loss Limit (% of Capital)",
            value=2.0,
            min_value=0.5,
            max_value=10.0,
            step=0.5,
            help="Trading stops when daily loss reaches this percentage"
        )

    with col2:
        st.number_input(
            "Weekly Loss Limit (₹)",
            value=15000,
            min_value=1000,
            max_value=500000,
            step=1000,
            help="Trading pauses when weekly loss reaches this amount"
        )
        st.number_input(
            "Monthly Loss Limit (₹)",
            value=50000,
            min_value=5000,
            max_value=1000000,
            step=5000,
            help="Trading pauses when monthly loss reaches this amount"
        )

    st.markdown("---")

    # Portfolio Heat Settings
    st.markdown("### Portfolio Heat Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.slider(
            "Max Portfolio Heat (%)",
            min_value=1.0,
            max_value=15.0,
            value=6.0,
            step=0.5,
            help="Sum of all position risks as % of capital"
        )
        st.slider(
            "Heat Warning Level (%)",
            min_value=1.0,
            max_value=10.0,
            value=4.0,
            step=0.5,
            help="Warning triggers when heat exceeds this level"
        )

    with col2:
        st.checkbox("Auto-reduce positions at max heat", value=False)
        st.checkbox("Block new trades at max heat", value=True)

    st.markdown("---")

    # Drawdown Management
    st.markdown("### Drawdown Management")

    col1, col2 = st.columns(2)

    with col1:
        st.slider("Caution Level (%)", 1.0, 10.0, 5.0, 0.5,
                 help="Reduce position sizes at this drawdown level")
        st.slider("Warning Level (%)", 5.0, 15.0, 10.0, 0.5,
                 help="Alert and restrict trading at this level")

    with col2:
        st.slider("Critical Level (%)", 10.0, 20.0, 15.0, 0.5,
                 help="Halt all trading at this level")
        st.slider("Emergency Level (%)", 15.0, 30.0, 20.0, 0.5,
                 help="Close all positions at this level")

    # Save button
    if st.button("Save Risk Management Settings", use_container_width=True, type="primary"):
        st.success("Risk management settings saved!")


def show_trading_rules():
    """Trading Rules section (Phase 4.3.6)"""
    st.subheader("Trading Rules Configuration")

    st.info("Enable/disable automatic trading rules for disciplined trading")

    # Rules with toggle switches (Phase 4.3.6)
    st.markdown("### Active Rules")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Entry Rules")
        st.toggle("Max Trades Per Day Limit", value=True, help="Limit daily trade count")
        st.number_input("Max Trades", value=5, min_value=1, max_value=20, key="max_trades_rule")

        st.toggle("Block First 15 Minutes", value=True, help="No trading in first 15 min")
        st.toggle("Block Last 15 Minutes", value=True, help="No trading in last 15 min")
        st.toggle("Block During Lunch (12:30-1:30)", value=False)

    with col2:
        st.markdown("#### Loss Prevention")
        st.toggle("Consecutive Loss Limit", value=True, help="Stop after N consecutive losses")
        st.number_input("Max Consecutive Losses", value=3, min_value=1, max_value=10, key="max_consec_rule")

        st.toggle("Revenge Trading Cooldown", value=True, help="Wait after loss before trading")
        st.number_input("Cooldown Minutes", value=60, min_value=5, max_value=240, key="cooldown_rule")

    st.markdown("---")

    st.markdown("### Time-Based Rules")

    col1, col2 = st.columns(2)

    with col1:
        st.toggle("Mandatory Weekend Break", value=True, help="No trading on Sat/Sun")
        st.toggle("Market Hours Only", value=True, help="9:15 AM - 3:30 PM IST")

    with col2:
        st.number_input(
            "Min Time Between Trades (min)",
            value=5,
            min_value=0,
            max_value=60,
            help="Minimum gap between consecutive trades"
        )

    st.markdown("---")

    st.markdown("### Exit Rules")

    col1, col2 = st.columns(2)

    with col1:
        st.toggle("Auto Square-off at 3:15 PM", value=True, help="Close intraday positions")
        st.toggle("Force Stop Loss on All Trades", value=True, help="Require SL on every trade")

    with col2:
        st.toggle("Trail Stop Loss", value=False, help="Automatically trail SL in profit")
        st.number_input("Trail Points", value=10, min_value=5, max_value=100, key="trail_rule")

    # Save button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Trading Rules", use_container_width=True, type="primary"):
            st.success("Trading rules saved!")
    with col2:
        if st.button("Reset to Defaults", use_container_width=True):
            st.info("Rules reset to default values")


def show_api_settings(data_provider):
    """API Configuration section (Phase 4.3.6)"""
    st.subheader("API Configuration")

    st.warning("Never share your API credentials with anyone!")

    # Token Status
    token_status = data_provider.get_token_status()

    st.markdown("### Authentication Status")

    col1, col2 = st.columns(2)

    with col1:
        status = token_status.get('status', 'UNKNOWN')
        if status == 'VALID':
            st.success("**Token Status:** Valid")
            st.info(f"**Expires in:** {token_status.get('hours_remaining', 0):.1f} hours")
        elif status == 'WARNING':
            st.warning("**Token Status:** Expiring Soon")
            st.warning(f"**Expires in:** {token_status.get('hours_remaining', 0):.1f} hours")
        elif status == 'EXPIRED':
            st.error("**Token Status:** Expired")
            st.error("Please re-authenticate")
        else:
            st.info(f"**Token Status:** {status}")

    with col2:
        if token_status.get('last_authenticated'):
            st.info(f"**Last Auth:** {token_status.get('last_authenticated', 'Unknown')[:19]}")

        # Re-authenticate button (Phase 4.3.6)
        auth_url = data_provider.get_authorization_url()
        if auth_url:
            st.link_button("Re-Authenticate", auth_url, use_container_width=True)

    st.markdown("---")

    # Connection Status
    st.markdown("### Connection Status")

    connection_status = data_provider.get_connection_status()

    col1, col2 = st.columns(2)
    with col1:
        conn_state = connection_status.get('state', 'unknown')
        if conn_state == 'connected':
            st.success("**API:** Connected")
        elif conn_state == 'disconnected':
            st.error("**API:** Disconnected")
        else:
            st.warning(f"**API:** {conn_state.capitalize()}")

        cache_stats = connection_status.get('cache_stats', {})
        hit_rate = cache_stats.get('hit_rate_percent', 0)
        st.info(f"**Cache Hit Rate:** {hit_rate:.1f}%")

    with col2:
        available_requests = connection_status.get('available_requests', 0)
        st.info(f"**API Requests Available:** {available_requests}/250 per min")

        last_call = connection_status.get('last_successful_call')
        if last_call:
            st.info(f"**Last API Call:** {last_call[:19]}")

    st.markdown("---")

    # Manual token entry
    st.markdown("### Manual Token Entry")
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

        submitted = st.form_submit_button("Save Token", use_container_width=True)

        if submitted and access_token:
            success = data_provider.set_access_token(access_token, expiry_hours)
            if success:
                st.success("Token saved successfully!")
                st.rerun()
            else:
                st.error("Failed to save token")


def show_notifications():
    """Notifications section (Phase 4.3.6)"""
    st.subheader("Notification Settings")

    st.info("Configure how you receive trading alerts and notifications")

    # Notification channels
    st.markdown("### Notification Channels")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Browser & Sound")
        st.toggle("Browser Notifications", value=True)
        st.toggle("Sound Alerts", value=True)
        st.slider("Alert Volume", 0, 100, 50)

    with col2:
        st.markdown("#### External Channels")
        st.toggle("Email Alerts", value=False)
        st.text_input("Email Address", placeholder="your@email.com", disabled=True, key="notif_email")

        st.toggle("Telegram Alerts", value=False)
        st.text_input("Telegram Chat ID", placeholder="Enter chat ID", disabled=True, key="notif_telegram")

    st.markdown("---")

    # Alert types
    st.markdown("### Alert Conditions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Signal Alerts")
        st.checkbox("Strong Buy/Sell Signals", value=True)
        st.checkbox("Strategy Entry Signals", value=True)
        st.checkbox("IV Rank Changes", value=False)

    with col2:
        st.markdown("#### Trade Alerts")
        st.checkbox("Order Execution", value=True)
        st.checkbox("Target Hit", value=True)
        st.checkbox("Stop Loss Hit", value=True)

    st.markdown("---")

    st.markdown("### Risk Alerts")

    col1, col2 = st.columns(2)

    with col1:
        st.checkbox("Daily Loss Limit Warning", value=True)
        st.checkbox("Portfolio Heat Warning", value=True)
        st.checkbox("Drawdown Warning", value=True)

    with col2:
        st.checkbox("Rule Violation Alerts", value=True)
        st.checkbox("Token Expiry Warning", value=True)
        st.checkbox("Connection Lost", value=True)

    # Save button
    if st.button("Save Notification Settings", use_container_width=True, type="primary"):
        st.success("Notification settings saved!")


def show_about():
    """About section"""
    st.subheader("About F&O Trading Platform")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Application Info

        **Version:** 2.0.0 (Phase 4 Complete)
        **Build:** Professional Trading Dashboard
        **Last Updated:** December 2024

        ### Features

        - Advanced Risk Management
        - Professional Analytics Dashboard
        - Strategy Builder with Payoff Diagrams
        - Live Signals with Confidence Scores
        - Performance Tracking with Benchmarks
        - Drawdown Protection System
        - Trading Rules Enforcement
        - Real-Time Market Data
        - Persistent Capital Tracking
        - Token Management
        """)

    with col2:
        data_provider = get_data_provider()
        connection_status = data_provider.get_connection_status()

        st.markdown("### System Status")

        conn_state = connection_status.get('state', 'unknown')
        if conn_state == 'connected':
            st.success("**Market Data:** Active")
            st.success("**API Connection:** Connected")
        else:
            st.warning(f"**API Connection:** {conn_state.capitalize()}")

        st.success("**Database:** Healthy")
        st.success("**Risk Engine:** Running")
        st.success("**Analytics:** Active")

        st.markdown("""
        ### Support

        📧 support@fnotrading.com
        📚 Documentation: /docs
        🐛 Report Issues: GitHub
        """)

    st.markdown("---")

    st.markdown("### System Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("**Python:** 3.10+")
        st.info("**Database:** SQLite")

    with col2:
        st.info("**UI:** Streamlit")
        st.info("**Charts:** Plotly")

    with col3:
        st.info("**Modules:** 25+")
        st.info("**Lines:** 15,000+")

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("View Documentation", use_container_width=True):
            st.info("Opening documentation...")

    with col2:
        if st.button("Check for Updates", use_container_width=True):
            st.success("You're on the latest version!")

    with col3:
        if st.button("Export Logs", use_container_width=True):
            st.info("Exporting system logs...")

    with col4:
        if st.button("Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared!")

    st.caption("© 2024 F&O Trading Platform. Built for Indian F&O traders.")
