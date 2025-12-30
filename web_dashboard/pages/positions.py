"""
Position Management Page - Manage active positions and orders
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

def show():
    st.title("💼 Position Management")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Active Positions", "📋 Orders", "📜 Trade History"])

    with tab1:
        show_active_positions()

    with tab2:
        show_orders()

    with tab3:
        show_trade_history()


def show_active_positions():
    st.subheader("Active Positions")

    # Position summary
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Positions", "2")
    with col2:
        st.metric("Long Positions", "1", delta="+1")
    with col3:
        st.metric("Short Positions", "1")
    with col4:
        st.metric("Total Exposure", "₹62,500")

    st.markdown("---")

    # Positions table
    positions_data = {
        'Instrument': ['NIFTY 24000 CE', 'BANKNIFTY 47000 PE'],
        'Type': ['LONG', 'SHORT'],
        'Quantity': [50, 25],
        'Entry Price': [250.00, 180.00],
        'LTP': [275.00, 160.00],
        'P&L': [1250.00, 500.00],
        'P&L %': [10.0, 11.1],
        'Entry Time': ['2024-12-29 10:15', '2024-12-29 11:30'],
        'Stop Loss': [240.00, 190.00],
        'Target': [285.00, 155.00]
    }

    positions_df = pd.DataFrame(positions_data)

    # Display with styling
    def style_positions(row):
        if row['P&L'] > 0:
            return ['background-color: #d4edda'] * len(row)
        elif row['P&L'] < 0:
            return ['background-color: #f8d7da'] * len(row)
        return [''] * len(row)

    st.dataframe(
        positions_df.style.apply(style_positions, axis=1),
        hide_index=True,
        use_container_width=True
    )

    # Total P&L
    total_pnl = positions_df['P&L'].sum()
    if total_pnl > 0:
        st.success(f"**Total Unrealized P&L:** ₹{total_pnl:,.2f} (+{positions_df['P&L %'].mean():.2f}%)")
    else:
        st.error(f"**Total Unrealized P&L:** ₹{total_pnl:,.2f} ({positions_df['P&L %'].mean():.2f}%)")

    st.markdown("---")

    # Position details
    st.subheader("Position Details")

    selected_position = st.selectbox(
        "Select Position",
        positions_df['Instrument'].tolist()
    )

    if selected_position:
        pos = positions_df[positions_df['Instrument'] == selected_position].iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### Position Info")
            st.write(f"**Type:** {pos['Type']}")
            st.write(f"**Quantity:** {pos['Quantity']}")
            st.write(f"**Entry Price:** ₹{pos['Entry Price']:.2f}")
            st.write(f"**Entry Time:** {pos['Entry Time']}")

        with col2:
            st.markdown("#### Current Status")
            st.write(f"**LTP:** ₹{pos['LTP']:.2f}")
            st.write(f"**P&L:** ₹{pos['P&L']:.2f} ({pos['P&L %']:.2f}%)")
            st.write(f"**Stop Loss:** ₹{pos['Stop Loss']:.2f}")
            st.write(f"**Target:** ₹{pos['Target']:.2f}")

        with col3:
            st.markdown("#### Risk Metrics")
            risk = abs(pos['Entry Price'] - pos['Stop Loss']) * pos['Quantity']
            reward = abs(pos['Target'] - pos['Entry Price']) * pos['Quantity']
            st.write(f"**Risk:** ₹{risk:,.2f}")
            st.write(f"**Reward:** ₹{reward:,.2f}")
            st.write(f"**R:R Ratio:** 1:{reward/risk:.2f}")

            distance_to_sl = abs(pos['LTP'] - pos['Stop Loss'])
            distance_to_target = abs(pos['Target'] - pos['LTP'])
            st.write(f"**To SL:** ₹{distance_to_sl:.2f}")
            st.write(f"**To Target:** ₹{distance_to_target:.2f}")

        # Action buttons
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("✏️ Modify Stop Loss", use_container_width=True):
                new_sl = st.number_input("New Stop Loss", value=pos['Stop Loss'])
                if st.button("Update SL"):
                    st.success("Stop loss updated!")

        with col2:
            if st.button("🎯 Modify Target", use_container_width=True):
                st.info("Target modification interface")

        with col3:
            if st.button("➕ Add to Position", use_container_width=True):
                st.info("Adding to position...")

        with col4:
            if st.button("❌ Close Position", use_container_width=True, type="primary"):
                st.warning("Confirm position closure?")


def show_orders():
    st.subheader("Order Management")

    # Order type tabs
    order_tab1, order_tab2, order_tab3 = st.tabs(["📝 Pending", "✅ Executed", "❌ Cancelled"])

    with order_tab1:
        st.info("No pending orders")

        # Place new order form
        with st.expander("➕ Place New Order"):
            col1, col2 = st.columns(2)

            with col1:
                instrument = st.text_input("Instrument", "NIFTY 24000 CE")
                order_type = st.selectbox("Order Type", ["LIMIT", "MARKET", "SL", "SL-M"])
                quantity = st.number_input("Quantity (Lots)", value=1, min_value=1)

            with col2:
                direction = st.selectbox("Direction", ["BUY", "SELL"])
                price = st.number_input("Price", value=250.0, step=0.5)
                validity = st.selectbox("Validity", ["DAY", "IOC"])

            col1, col2 = st.columns(2)
            with col1:
                stop_loss = st.number_input("Stop Loss (Optional)", value=0.0)
            with col2:
                target = st.number_input("Target (Optional)", value=0.0)

            if st.button("📝 Place Order", use_container_width=True, type="primary"):
                st.success("Order placed successfully!")

    with order_tab2:
        executed_orders = {
            'Time': ['10:15:30', '11:30:45', '14:00:12'],
            'Instrument': ['NIFTY 24000 CE', 'BANKNIFTY 47000 PE', 'FINNIFTY 21500 CE'],
            'Type': ['BUY', 'SELL', 'BUY'],
            'Quantity': [50, 25, 40],
            'Price': [250.00, 180.00, 125.00],
            'Status': ['EXECUTED', 'EXECUTED', 'EXECUTED']
        }

        st.dataframe(pd.DataFrame(executed_orders), hide_index=True, use_container_width=True)

    with order_tab3:
        st.info("No cancelled orders today")


def show_trade_history():
    st.subheader("Trade History")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        period = st.selectbox("Period", ["Today", "Last 7 Days", "Last 30 Days", "All Time"])

    with col2:
        instrument_filter = st.multiselect(
            "Instruments",
            ["NIFTY", "BANKNIFTY", "FINNIFTY"],
            default=[]
        )

    with col3:
        status_filter = st.multiselect(
            "Status",
            ["Profit", "Loss", "Breakeven"],
            default=[]
        )

    st.markdown("---")

    # Trade history table
    trades_data = {
        'Date': ['2024-12-29', '2024-12-28', '2024-12-27', '2024-12-26', '2024-12-25'],
        'Instrument': ['NIFTY CE', 'BANKNIFTY PE', 'NIFTY CE', 'FINNIFTY CE', 'NIFTY PE'],
        'Type': ['LONG', 'SHORT', 'LONG', 'LONG', 'SHORT'],
        'Entry': [250.00, 180.00, 245.00, 120.00, 190.00],
        'Exit': [275.00, 160.00, 230.00, 135.00, 185.00],
        'Quantity': [50, 25, 50, 40, 50],
        'P&L': [1250, 500, -750, 600, 250],
        'P&L %': [10.0, 11.1, -6.1, 12.5, 2.6],
        'Duration': ['2h 30m', '1h 45m', '3h 15m', '4h 00m', '2h 00m'],
        'Strategy': ['Supertrend', 'Iron Condor', 'Breakout', 'ORB', 'Mean Rev']
    }

    trades_df = pd.DataFrame(trades_data)

    def style_trades(row):
        if row['P&L'] > 0:
            return ['background-color: #d4edda'] * len(row)
        elif row['P&L'] < 0:
            return ['background-color: #f8d7da'] * len(row)
        return [''] * len(row)

    st.dataframe(
        trades_df.style.apply(style_trades, axis=1),
        hide_index=True,
        use_container_width=True
    )

    # Summary
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Trades", len(trades_df))
    with col2:
        winners = len(trades_df[trades_df['P&L'] > 0])
        st.metric("Winners", winners, delta=f"{winners/len(trades_df)*100:.1f}%")
    with col3:
        losers = len(trades_df[trades_df['P&L'] < 0])
        st.metric("Losers", losers)
    with col4:
        total_pnl = trades_df['P&L'].sum()
        st.metric("Total P&L", f"₹{total_pnl:,.0f}")
    with col5:
        avg_pnl = trades_df['P&L'].mean()
        st.metric("Avg P&L", f"₹{avg_pnl:,.0f}")
