"""
Position Management Page - Manage active positions and orders
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add parent to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from web_dashboard.data_provider import get_data_provider


def show():
    st.title("💼 Position Management")

    # Get data provider
    data_provider = get_data_provider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Active Positions", "📋 Orders", "📜 Trade History"])

    with tab1:
        show_active_positions(data_provider)

    with tab2:
        show_orders(data_provider)

    with tab3:
        show_trade_history(data_provider)


def show_active_positions(data_provider):
    st.subheader("Active Positions")

    # Fetch live positions
    positions = data_provider.get_positions()
    portfolio_summary = data_provider.get_portfolio_summary()

    # Position summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Positions", str(portfolio_summary.get('positions_count', 0)))
    with col2:
        long_pos = portfolio_summary.get('long_positions', 0)
        st.metric("Long Positions", str(long_pos),
                 delta=f"+{long_pos}" if long_pos > 0 else None)
    with col3:
        st.metric("Short Positions", str(portfolio_summary.get('short_positions', 0)))
    with col4:
        total_value = portfolio_summary.get('total_position_value', 0)
        st.metric("Total Exposure", f"₹{total_value:,.0f}")

    st.markdown("---")

    if not positions:
        st.info("No active positions. Start trading to see positions here.")
        return

    # Check if demo data
    is_demo = any(p.get('demo', False) for p in positions)
    if is_demo:
        st.caption("📊 Demo positions - Authenticate for live data")

    # Build positions DataFrame
    positions_data = {
        'Instrument': [p.get('symbol', p.get('instrument', '')) for p in positions],
        'Type': [p.get('direction', 'LONG') for p in positions],
        'Quantity': [abs(p.get('quantity', 0)) for p in positions],
        'Entry Price': [p.get('average_price', 0) for p in positions],
        'LTP': [p.get('last_price', 0) for p in positions],
        'P&L': [p.get('unrealized_pnl', p.get('pnl', 0)) for p in positions],
        'P&L %': [p.get('pnl_percent', 0) for p in positions],
        'Product': [p.get('product', 'I') for p in positions]
    }

    positions_df = pd.DataFrame(positions_data)

    # Add calculated columns
    if not positions_df.empty:
        positions_df['P&L %'] = positions_df.apply(
            lambda row: (row['P&L'] / (row['Quantity'] * row['Entry Price']) * 100)
            if row['Quantity'] * row['Entry Price'] > 0 else 0,
            axis=1
        )

    # Display with styling
    def style_positions(row):
        if row['P&L'] > 0:
            return ['background-color: #d4edda'] * len(row)
        elif row['P&L'] < 0:
            return ['background-color: #f8d7da'] * len(row)
        return [''] * len(row)

    st.dataframe(
        positions_df.style.apply(style_positions, axis=1).format({
            'Entry Price': '₹{:.2f}',
            'LTP': '₹{:.2f}',
            'P&L': '₹{:,.2f}',
            'P&L %': '{:.2f}%'
        }),
        hide_index=True,
        use_container_width=True
    )

    # Total P&L
    total_pnl = positions_df['P&L'].sum()
    avg_pnl_pct = positions_df['P&L %'].mean() if not positions_df.empty else 0

    if total_pnl > 0:
        st.success(f"**Total Unrealized P&L:** ₹{total_pnl:,.2f} (+{avg_pnl_pct:.2f}%)")
    elif total_pnl < 0:
        st.error(f"**Total Unrealized P&L:** ₹{total_pnl:,.2f} ({avg_pnl_pct:.2f}%)")
    else:
        st.info(f"**Total Unrealized P&L:** ₹{total_pnl:,.2f}")

    st.markdown("---")

    # Portfolio Greeks for options positions
    if portfolio_summary.get('options_positions', 0) > 0:
        st.subheader("📐 Portfolio Greeks")
        greeks = data_provider.get_portfolio_greeks()

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

    # Position details
    st.subheader("Position Details")

    if positions_df.empty:
        return

    selected_position = st.selectbox(
        "Select Position",
        positions_df['Instrument'].tolist()
    )

    if selected_position:
        pos_idx = positions_df[positions_df['Instrument'] == selected_position].index[0]
        pos = positions_df.iloc[pos_idx]
        pos_data = positions[pos_idx]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### Position Info")
            st.write(f"**Type:** {pos['Type']}")
            st.write(f"**Quantity:** {pos['Quantity']}")
            st.write(f"**Entry Price:** ₹{pos['Entry Price']:.2f}")
            st.write(f"**Product:** {pos['Product']}")
            if pos_data.get('option_type'):
                st.write(f"**Option Type:** {pos_data.get('option_type')}")

        with col2:
            st.markdown("#### Current Status")
            st.write(f"**LTP:** ₹{pos['LTP']:.2f}")
            pnl_color = "green" if pos['P&L'] > 0 else "red" if pos['P&L'] < 0 else "black"
            st.markdown(
                f"**P&L:** <span style='color:{pnl_color}'>₹{pos['P&L']:,.2f} ({pos['P&L %']:.2f}%)</span>",
                unsafe_allow_html=True
            )
            st.write(f"**Position Value:** ₹{pos['Quantity'] * pos['LTP']:,.2f}")

        with col3:
            st.markdown("#### Risk Metrics")
            # Calculate risk assuming 2% stop loss
            entry_value = pos['Quantity'] * pos['Entry Price']
            assumed_sl_pct = 2.0
            risk_amount = entry_value * (assumed_sl_pct / 100)
            assumed_target_pct = 4.0
            reward_amount = entry_value * (assumed_target_pct / 100)

            st.write(f"**At Risk (2% SL):** ₹{risk_amount:,.2f}")
            st.write(f"**Potential (4% Target):** ₹{reward_amount:,.2f}")
            rr = f"1:{reward_amount/risk_amount:.2f}" if risk_amount > 0 else "N/A"
            st.write(f"**R:R Ratio:** {rr}")

            capital_summary = data_provider.get_capital_summary()
            capital = capital_summary.get('current_capital', 100000)
            st.write(f"**% of Capital:** {(entry_value / capital * 100):.2f}%")

        # Action buttons
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("✏️ Modify Stop Loss", use_container_width=True):
                st.session_state.modify_sl = True

        with col2:
            if st.button("🎯 Modify Target", use_container_width=True):
                st.info("Target modification coming soon")

        with col3:
            if st.button("➕ Add to Position", use_container_width=True):
                st.info("Position scaling coming soon")

        with col4:
            if st.button("❌ Close Position", use_container_width=True, type="primary"):
                st.warning("⚠️ Position closure requires order confirmation")


def show_orders(data_provider):
    st.subheader("Order Management")

    # Order type tabs
    order_tab1, order_tab2, order_tab3 = st.tabs(["📝 Pending", "✅ Executed", "❌ Cancelled"])

    # Get order book
    order_book = data_provider.get_order_book()
    trade_book = data_provider.get_trade_book()

    with order_tab1:
        pending_orders = [
            o for o in order_book
            if o.get('status', '').lower() in ['open', 'pending', 'trigger_pending']
        ]

        if pending_orders:
            pending_df = pd.DataFrame([{
                'Time': o.get('order_timestamp', '')[:8] if o.get('order_timestamp') else '',
                'Instrument': o.get('symbol', o.get('instrument', '')),
                'Type': o.get('transaction_type', ''),
                'Order Type': o.get('order_type', ''),
                'Quantity': o.get('quantity', 0),
                'Price': o.get('price', 0),
                'Status': o.get('status', '').upper()
            } for o in pending_orders])

            st.dataframe(pending_df, hide_index=True, use_container_width=True)
        else:
            st.info("No pending orders")

        # Place new order form
        with st.expander("➕ Place New Order"):
            col1, col2 = st.columns(2)

            with col1:
                st.text_input("Instrument", "NIFTY 24000 CE")
                st.selectbox("Order Type", ["LIMIT", "MARKET", "SL", "SL-M"])
                st.number_input("Quantity (Lots)", value=1, min_value=1)

            with col2:
                st.selectbox("Direction", ["BUY", "SELL"])
                st.number_input("Price", value=250.0, step=0.5)
                st.selectbox("Validity", ["DAY", "IOC"])

            col1, col2 = st.columns(2)
            with col1:
                st.number_input("Stop Loss (Optional)", value=0.0)
            with col2:
                st.number_input("Target (Optional)", value=0.0)

            if st.button("📝 Place Order", use_container_width=True, type="primary"):
                st.warning("⚠️ Order placement requires confirmation. Coming in Phase 2.")

    with order_tab2:
        executed_orders = [
            o for o in order_book
            if o.get('status', '').lower() == 'complete'
        ]

        if executed_orders:
            executed_df = pd.DataFrame([{
                'Time': (
                    o.get('exchange_timestamp', o.get('order_timestamp', ''))[:8]
                    if o.get('exchange_timestamp') or o.get('order_timestamp') else ''
                ),
                'Instrument': o.get('symbol', o.get('instrument', '')),
                'Type': o.get('transaction_type', ''),
                'Quantity': o.get('filled_quantity', o.get('quantity', 0)),
                'Price': o.get('average_price', o.get('price', 0)),
                'Status': 'EXECUTED'
            } for o in executed_orders])

            st.dataframe(executed_df, hide_index=True, use_container_width=True)
        elif trade_book:
            trades_df = pd.DataFrame([{
                'Time': t.get('trade_timestamp', '')[:8] if t.get('trade_timestamp') else '',
                'Instrument': t.get('symbol', t.get('instrument', '')),
                'Type': t.get('transaction_type', ''),
                'Quantity': t.get('quantity', 0),
                'Price': t.get('price', 0),
                'Status': 'EXECUTED'
            } for t in trade_book])

            st.dataframe(trades_df, hide_index=True, use_container_width=True)
        else:
            st.info("No executed orders today")

    with order_tab3:
        cancelled_orders = [
            o for o in order_book
            if o.get('status', '').lower() in ['cancelled', 'rejected']
        ]

        if cancelled_orders:
            cancelled_df = pd.DataFrame([{
                'Time': o.get('order_timestamp', '')[:8] if o.get('order_timestamp') else '',
                'Instrument': o.get('symbol', o.get('instrument', '')),
                'Type': o.get('transaction_type', ''),
                'Quantity': o.get('quantity', 0),
                'Price': o.get('price', 0),
                'Status': o.get('status', '').upper(),
                'Reason': o.get('status_message', '')
            } for o in cancelled_orders])

            st.dataframe(cancelled_df, hide_index=True, use_container_width=True)
        else:
            st.info("No cancelled/rejected orders today")


def show_trade_history(data_provider):
    st.subheader("Trade History")

    # Get trade book
    trade_book = data_provider.get_trade_book()

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        st.selectbox("Period", ["Today", "Last 7 Days", "Last 30 Days", "All Time"])

    with col2:
        st.multiselect(
            "Instruments",
            ["NIFTY", "BANKNIFTY", "FINNIFTY"],
            default=[]
        )

    with col3:
        st.multiselect(
            "Status",
            ["Profit", "Loss", "Breakeven"],
            default=[]
        )

    st.markdown("---")

    if trade_book:
        trades_df = pd.DataFrame([{
            'Date': (
                t.get('trade_timestamp', '')[:10]
                if t.get('trade_timestamp') else datetime.now().strftime('%Y-%m-%d')
            ),
            'Instrument': t.get('symbol', t.get('instrument', '')),
            'Type': t.get('transaction_type', ''),
            'Quantity': t.get('quantity', 0),
            'Price': t.get('price', 0),
            'Value': t.get('quantity', 0) * t.get('price', 0)
        } for t in trade_book])

        st.dataframe(trades_df, hide_index=True, use_container_width=True)

        orders_summary = data_provider.get_orders_summary()

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Trades", orders_summary.get('total_trades', len(trades_df)))
        with col2:
            st.metric("Buy Orders", orders_summary.get('buy_orders', 0))
        with col3:
            st.metric("Sell Orders", orders_summary.get('sell_orders', 0))
        with col4:
            total_value = orders_summary.get('total_traded_value', trades_df['Value'].sum())
            st.metric("Traded Value", f"₹{total_value:,.0f}")
        with col5:
            success_rate = orders_summary.get('success_rate', 100)
            st.metric("Success Rate", f"{success_rate:.1f}%")
    else:
        st.info("No trades found for the selected period.")

        st.caption("📊 Demo trade history shown below:")

        demo_trades = {
            'Date': ['2024-12-29', '2024-12-28', '2024-12-27'],
            'Instrument': ['NIFTY CE', 'BANKNIFTY PE', 'NIFTY CE'],
            'Type': ['LONG', 'SHORT', 'LONG'],
            'Entry': [250.00, 180.00, 245.00],
            'Exit': [275.00, 160.00, 230.00],
            'Quantity': [50, 25, 50],
            'P&L': [1250, 500, -750],
            'P&L %': [10.0, 11.1, -6.1]
        }

        demo_df = pd.DataFrame(demo_trades)

        def style_trades(row):
            if row['P&L'] > 0:
                return ['background-color: #d4edda'] * len(row)
            elif row['P&L'] < 0:
                return ['background-color: #f8d7da'] * len(row)
            return [''] * len(row)

        st.dataframe(
            demo_df.style.apply(style_trades, axis=1),
            hide_index=True,
            use_container_width=True
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Trades", len(demo_df))
        with col2:
            winners = len(demo_df[demo_df['P&L'] > 0])
            st.metric("Winners", winners, delta=f"{winners/len(demo_df)*100:.1f}%")
        with col3:
            losers = len(demo_df[demo_df['P&L'] < 0])
            st.metric("Losers", losers)
        with col4:
            total_pnl = demo_df['P&L'].sum()
            st.metric("Total P&L", f"₹{total_pnl:,.0f}")
        with col5:
            avg_pnl = demo_df['P&L'].mean()
            st.metric("Avg P&L", f"₹{avg_pnl:,.0f}")
