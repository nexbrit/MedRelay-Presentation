# TradeFlow v2 - Development Roadmap

> **Expert Review Date**: December 30, 2025
> **Reviewed By**: Oz (F&O Trading Expert via oz-fno-wizard agent)
> **Status**: Active Development

---

## Executive Summary

TradeFlow v2 has a solid foundation with professional-grade risk management, options Greeks, volatility analysis, and backtesting. However, **critical gaps must be addressed before live trading**. This roadmap outlines the development path to transform the application from a prototype to a production-ready F&O trading platform.

### Current State Assessment

**Strengths:**
- ✅ Risk management architecture (Kelly Criterion, position sizing, 6% portfolio heat limit)
- ✅ Backtesting engine with realistic trading costs (STT, exchange charges, GST, SEBI, stamp duty)
- ✅ Volatility intelligence (IV Rank, IV Percentile, regime detection)
- ✅ Options strategies (Iron Condor, Spreads, Straddles, Strangles, Butterflies)
- ✅ Working Upstox API integration with valid credentials

**Critical Gaps:**
- ❌ Dummy data throughout dashboard (positions, signals, P&L)
- ❌ No capital persistence (resets on restart)
- ❌ Missing safety mechanisms (order confirmation, stop-loss enforcement, circuit breakers)
- ❌ No token expiry handling (fails silently after 24 hours)
- ❌ No historical data infrastructure for backtesting
- ❌ UI needs professional polish for trading readiness

---

## Phase 1: Foundation - CRITICAL PRIORITY

**Objective**: Establish live data flows and persistent state management

### 1.1 Data Service Layer Architecture

**Files to Create:**
```
data/
├── services/
│   ├── __init__.py
│   ├── market_data_service.py      # Live quotes, option chain
│   ├── portfolio_service.py        # Positions, holdings, P&L
│   ├── order_service.py            # Order placement, tracking
│   ├── historical_data_service.py  # Historical data retrieval
│   └── capital_service.py          # Capital tracking and adjustment
├── cache/
│   └── market_cache.db             # SQLite for caching with TTL
└── persistence/
    └── app_state.db                # Application state persistence
```

**Tasks:**

- [x] **1.1.1** Create `market_data_service.py` ✅ **COMPLETED**
  - [x] Implement `get_live_quote(instrument_key)` with 5-second cache
  - [x] Implement `get_option_chain(underlying, expiry)` with 30-second cache
  - [x] Add connection state tracking (Connected/Disconnected/Reconnecting)
  - [x] Implement fallback to last known good data if API fails
  - [x] Add rate limiting (respect Upstox limits: 250 req/min)

- [x] **1.1.2** Create `portfolio_service.py` ✅ **COMPLETED**
  - [x] Implement `get_positions()` - fetch from Upstox API
  - [x] Implement `get_holdings()` - fetch from Upstox API
  - [x] Implement `calculate_unrealized_pnl()` - real-time P&L calculation
  - [x] Implement `calculate_realized_pnl()` - closed positions P&L
  - [x] Add portfolio Greeks aggregation (sum Delta, Gamma, Theta, Vega)

- [x] **1.1.3** Create `order_service.py` ✅ **COMPLETED**
  - [x] Implement `get_order_book()` - fetch all orders
  - [x] Implement `get_trade_book()` - fetch executed trades
  - [x] Implement `track_order_status(order_id)` - poll for updates
  - [x] Add order history caching

- [x] **1.1.4** Create SQLite cache infrastructure ✅ **COMPLETED**
  - [x] Design cache schema with TTL support
  - [x] Implement cache invalidation logic
  - [x] Add cache statistics (hit rate, miss rate)

### 1.2 Replace Dummy Data with Live Data

**Files to Modify:**
- `web_dashboard/app.py` (lines 244-265: positions data)
- `web_dashboard/pages/positions.py` (lines 44-55: sample positions)
- `web_dashboard/pages/trading_signals.py` (signal generation)
- `web_dashboard/pages/performance.py` (equity curve, metrics)

**Tasks:**

- [x] **1.2.1** Update Main Dashboard (`app.py`) ✅ **COMPLETED**
  - [x] Replace hardcoded positions with `portfolio_service.get_positions()`
  - [x] Calculate live P&L using current LTP
  - [x] Display actual margin utilized vs available
  - [x] Show real-time portfolio heat percentage
  - [x] Add "Last Updated" timestamp to all data sections
  - [x] Add connection status indicator (green dot = connected)

- [x] **1.2.2** Update Positions Page ✅ **COMPLETED**
  - [x] Fetch live positions from Upstox
  - [x] Calculate real-time Greeks for each options position
  - [x] Show combined portfolio Greeks
  - [x] Display margin requirement per position
  - [x] Add actual LTP with last update time
  - [x] Remove all `positions_data = {...}` hardcoded dictionaries

- [ ] **1.2.3** Update Trading Signals Page (Partial - Uses live data provider)
  - [x] Fetch real-time price data for signal calculation
  - [ ] Generate signals from live market data
  - [ ] Add last signal calculation timestamp
  - [ ] Remove sample signal data

- [ ] **1.2.4** Update Performance Page (Partial)
  - [ ] Replace dummy equity curve with actual trade history
  - [ ] Calculate real returns from closed trades
  - [ ] Show actual win rate, Sharpe ratio from real data
  - [x] Add "No data available" state for new accounts

### 1.3 Capital Management System

**Files to Create/Modify:**
- `data/services/capital_service.py` (new)
- `web_dashboard/pages/settings.py` (modify)
- `data/persistence/app_state.db` (schema)

**Tasks:**

- [x] **1.3.1** Create `capital_service.py` ✅ **COMPLETED**
  - [x] Implement `get_current_capital()` - fetch from DB
  - [x] Implement `set_initial_capital(amount)` - first-time setup
  - [x] Implement `adjust_capital(amount, type, reason)` - deposit/withdrawal
  - [x] Implement `get_capital_history()` - audit trail
  - [x] Calculate Time-Weighted Return (TWR) accounting for deposits/withdrawals

- [x] **1.3.2** Design Capital Database Schema ✅ **COMPLETED**
  ```sql
  CREATE TABLE capital_state (
    id INTEGER PRIMARY KEY,
    current_capital REAL NOT NULL,
    initial_capital REAL NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE capital_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    adjustment_type TEXT CHECK(adjustment_type IN ('DEPOSIT', 'WITHDRAWAL', 'MANUAL_ADJUSTMENT')),
    amount REAL NOT NULL,
    previous_capital REAL NOT NULL,
    new_capital REAL NOT NULL,
    reason TEXT
  );
  ```

- [x] **1.3.3** Update Settings Page UI ✅ **COMPLETED**
  - [x] Add "Capital & Account" section
  - [x] Display current capital (large, prominent)
  - [x] Add "Adjust Capital" button → opens modal
  - [x] Modal fields: Amount, Type (Deposit/Withdrawal), Reason
  - [x] Show capital adjustment history table
  - [x] Add initial capital setup wizard (first launch)

- [x] **1.3.4** Integrate with Position Sizing ✅ **COMPLETED**
  - [x] Modify `PositionSizer` to use `capital_service.get_current_capital()`
  - [x] Recalculate max position sizes when capital changes
  - [x] Update portfolio heat calculations with new capital

- [ ] **1.3.5** Capital Allocation Feature (Optional - Advanced)
  - [ ] Add strategy-level capital allocation
  - [ ] Track allocated vs available capital
  - [ ] Show utilization percentage per strategy

### 1.4 Authentication & Token Management

**Files to Create/Modify:**
- `auth/token_manager.py` (new)
- `main.py` (modify setup_authentication method)
- `web_dashboard/app.py` (add token status indicator)

**Tasks:**

- [x] **1.4.1** Create `token_manager.py` ✅ **COMPLETED**
  - [x] Implement `store_token(access_token, expiry_time)`
  - [x] Implement `get_token()` - return token if valid, else None
  - [x] Implement `is_token_expired()` - check expiry
  - [x] Implement `get_time_until_expiry()` - for warnings
  - [x] Store tokens securely (obfuscated in secure location)

- [x] **1.4.2** Update OAuth Flow in `main.py` ✅ **COMPLETED**
  - [x] Automatically store token expiry (Upstox tokens expire in 24h)
  - [x] Add token refresh reminder

- [x] **1.4.3** Add Token Status to Dashboard ✅ **COMPLETED**
  - [x] Show token expiry countdown in sidebar
  - [x] Warning banner when < 2 hours remaining
  - [x] Red alert when expired with re-auth button
  - [x] Auto-redirect to auth page if token expired

- [ ] **1.4.4** Implement Auto Re-Authentication (Advanced)
  - [ ] Background job to check token expiry
  - [ ] Email/SMS notification when token about to expire
  - [x] One-click re-auth flow

---

## Phase 2: Safety Mechanisms - HIGH PRIORITY

**Objective**: Implement critical safety features to prevent trading disasters

### 2.1 Order Confirmation System

**Files to Modify:**
- `api/upstox_client.py` (add confirmation layer)
- `web_dashboard/pages/positions.py` (add order placement UI)
- `orders/order_manager.py` (new)

**Tasks:**

- [x] **2.1.1** Create Order Preview Modal ✅ **COMPLETED**
  - [x] Display order details: Symbol, Qty, Price, Order Type
  - [x] Calculate and show estimated margin requirement
  - [x] Show potential risk (max loss) for the position
  - [x] Display portfolio heat impact (before and after)
  - [x] Add confirmation checkbox: "I confirm this order"
  - [x] Require explicit "Execute" button click

- [x] **2.1.2** Implement Order Validation ✅ **COMPLETED**
  - [x] Check if sufficient margin available
  - [x] Verify portfolio heat limit won't be exceeded
  - [x] Check daily order count limits (prevent over-trading)
  - [x] Validate order against trading rules (from `rules/enforcer.py`)

- [x] **2.1.3** Add High-Value Order Warnings ✅ **COMPLETED**
  - [x] Flag orders > 5% of capital (warning), > 8% (very high warning)
  - [x] Require additional confirmation for large orders
  - [x] Suggest position size reduction if oversized

- [x] **2.1.4** Implement Order Execution Logging ✅ **COMPLETED**
  - [x] Log every order attempt (approved/rejected/failed)
  - [x] Track who approved (user or auto-trading system)
  - [x] Store in `order_audit_log` table

### 2.2 Stop-Loss Automation

**Files to Create/Modify:**
- `orders/stop_loss_manager.py` (new) ✅ **CREATED**
- `risk/stop_loss_enforcer.py` (new)
- Background service for monitoring

**Tasks:**

- [x] **2.2.1** Design Stop-Loss Strategy ✅ **COMPLETED**
  - [x] Option 1: Place SL-M orders on exchange (recommended)
  - [x] Option 2: Monitor prices and trigger market orders
  - [x] Decision: Choose Option 1 for reliability

- [x] **2.2.2** Implement SL-M Order Placement ✅ **COMPLETED**
  - [x] When position opened, immediately place SL-M order
  - [x] Calculate SL price based on:
    - Fixed percentage (25% for index options, 30% for stock options)
    - ATR-based (2x ATR from entry)
    - User-defined absolute value
  - [x] Link SL order to parent position (order tags)

- [x] **2.2.3** Stop-Loss Modification System ✅ **COMPLETED**
  - [x] Allow users to modify SL from UI
  - [x] Trailing stop-loss feature (move SL up as profit increases)
  - [x] Validate SL modifications (can only tighten SL)

- [x] **2.2.4** Stop-Loss Monitoring (Fallback) ✅ **COMPLETED**
  - [x] check_stop_loss_trigger() method for fallback monitoring
  - [x] If LTP crosses SL and no SL-M order exists, trigger market order
  - [x] Logging when SL is hit

- [x] **2.2.5** Emergency Square-Off Button ✅ **COMPLETED**
  - [x] emergency_square_off_all() method
  - [x] Square off ALL positions at market price
  - [ ] UI integration (pending)

### 2.3 Daily Loss Circuit Breaker

**Files to Create/Modify:**
- `risk/circuit_breaker.py` (new) ✅ **CREATED**
- `web_dashboard/app.py` (add visual indicator)

**Tasks:**

- [x] **2.3.1** Implement Loss Monitoring ✅ **COMPLETED**
  - [x] Track daily realized + unrealized P&L
  - [x] Define daily loss limit (e.g., 2% of capital, configurable)
  - [x] Calculate distance to limit in real-time

- [x] **2.3.2** Tiered Alert System ✅ **COMPLETED**
  - [x] 50% of limit: CAUTION status with callback
  - [x] 80% of limit: WARNING status with callback
  - [x] 100% of limit: TRIGGERED status + callback for action

- [x] **2.3.3** Automatic Square-Off at Limit ✅ **COMPLETED**
  - [x] When 100% of daily loss limit hit, trigger callbacks
  - [x] trigger_emergency_exit() method for immediate action
  - [x] Block new position entry for rest of the day
  - [ ] Send SMS + Email notification (pending integration)

- [x] **2.3.4** Manual Override (with Safeguards) ✅ **COMPLETED**
  - [x] Allow user to disable circuit breaker (requires password hash)
  - [x] Log override action with reason
  - [x] Override expires at end of day (doesn't persist)

- [x] **2.3.5** Visual Indicators ✅ **COMPLETED**
  - [x] get_progress_bar_data() for UI display
  - [x] Color-coded: green (safe) → yellow → orange → red
  - [ ] UI integration (pending)

### 2.4 Real-Time Risk Monitoring

**Tasks:**

- [ ] **2.4.1** Portfolio Risk Dashboard
  - [ ] Display current portfolio heat percentage (live)
  - [ ] Show risk per position (% of capital at risk)
  - [ ] Highlight positions exceeding individual risk limits
  - [ ] Calculate and show portfolio Beta (vs Nifty)

- [ ] **2.4.2** Greeks-Based Risk Monitoring (Options)
  - [ ] Display portfolio Delta (directional risk)
  - [ ] Display portfolio Theta (time decay per day)
  - [ ] Display portfolio Vega (volatility risk)
  - [ ] Alert when portfolio Greeks exceed safe thresholds
    - Example: Portfolio Delta > 100 (too much directional exposure)

- [ ] **2.4.3** Correlation Risk
  - [ ] Use existing `CorrelationMatrix` from `risk/correlation_matrix.py`
  - [ ] Alert when positions are highly correlated (> 0.7)
  - [ ] Suggest diversification when concentration risk detected

---

## Phase 3: Data Infrastructure for Backtesting

**Objective**: Build historical data storage for effective strategy backtesting

### 3.1 Historical Data Download System

**Files to Create:**
```
data/
├── downloaders/
│   ├── __init__.py
│   ├── historical_downloader.py
│   └── options_chain_downloader.py
├── historical/
│   ├── indices/
│   │   ├── NIFTY50/
│   │   └── BANKNIFTY/
│   └── options/
│       ├── NIFTY/
│       └── BANKNIFTY/
└── schemas/
    └── parquet_schemas.py
```

**Tasks:**

- [x] **3.1.1** Create `historical_downloader.py` ✅ **COMPLETED**
  - [x] Implement `download_index_history(instrument, start_date, end_date, interval)`
    - Supported intervals: 1minute, 5minute, 15minute, 30minute, 1hour, day, week, month
  - [x] Implement rate limiting (respect Upstox 250 req/min limit)
  - [x] Implement retry logic with exponential backoff
  - [x] Handle API errors gracefully (partial data is ok)
  - [x] Save data in Parquet format (efficient compression)

- [x] **3.1.2** Define Storage Schema ✅ **COMPLETED**
  - [x] OHLCV schema in `data/schemas/parquet_schemas.py`
  - [x] Schema validation functions

- [x] **3.1.3** Implement Download Scheduling ✅ **COMPLETED**
  - [x] Bootstrap script with --dry-run option
  - [x] Configurable date ranges and instruments
  - [x] Cron job documentation in `data/historical/README.md`

- [x] **3.1.4** Data Validation & Integrity Checks ✅ **COMPLETED**
  - [x] Verify no missing dates (check for gaps)
  - [x] Validate OHLC relationships (High >= Close >= Low)
  - [x] Check for duplicate timestamps
  - [x] Generate data quality report

### 3.2 Options Chain Historical Data

**Tasks:**

- [x] **3.2.1** Create `options_chain_downloader.py` ✅ **COMPLETED**
  - [x] Download EOD option chain snapshots
  - [x] Store strike prices, premiums, IV, Greeks, OI
  - [x] Organize by expiry date

- [x] **3.2.2** Options Data Schema ✅ **COMPLETED**
  - [x] OPTION_CHAIN_SCHEMA in `data/schemas/parquet_schemas.py`
  - [x] Full schema including all Greeks and bid/ask data

- [x] **3.2.3** Storage Strategy for Options ✅ **COMPLETED**
  - [x] Store by snapshot date and expiry
  - [x] Parquet format for efficient storage
  - [x] Archive strategy documented in README

- [x] **3.2.4** Historical IV Database ✅ **COMPLETED**
  - [x] Calculate and store daily IV Rank (current IV vs 1-year range)
  - [x] Calculate and store daily IV Percentile
  - [x] `get_iv_history()` and `calculate_iv_rank()` methods

### 3.3 Data Retrieval Service

**Tasks:**

- [x] **3.3.1** Create `data_retrieval_service.py` ✅ **COMPLETED**
  - [x] Implement `get_historical_data(instrument, start, end, interval)`
  - [x] Implement `get_option_chain_snapshot(underlying, expiry, date)`
  - [x] Implement caching for frequently accessed data
  - [x] Return data as pandas DataFrame

- [x] **3.3.2** Data Export Functions ✅ **COMPLETED**
  - [x] Export to CSV for Excel analysis
  - [x] Export to JSON for external tools
  - [x] Data analysis utilities (returns, volatility, resampling)

### 3.4 Initial Data Bootstrap

**Tasks:**

- [x] **3.4.1** Download Initial Dataset ✅ **COMPLETED**
  - [x] Bootstrap script: `scripts/bootstrap_data.py`
  - [x] Supports indices (Nifty, BankNifty, VIX, etc.)
  - [x] Supports F&O stocks
  - [x] Supports option chain snapshots
  - [x] Configurable date ranges and intervals
  - [x] Note: API limits documented in README

- [x] **3.4.2** Document Data Limitations ✅ **COMPLETED**
  - [x] Created `data/historical/README.md` explaining:
    - Data sources (Upstox API)
    - Available date ranges (API limitations)
    - Directory structure and schemas
    - Usage examples and maintenance tasks

---

## Phase 4: UI/UX Professional Polish

**Objective**: Transform dashboard into a professional trading interface

### 4.1 Professional Color Scheme

**Tasks:**

- [x] **4.1.1** Define Color Palette ✅ **COMPLETED**
  - [x] Created `web_dashboard/theme.py` with comprehensive COLORS dictionary
  - [x] Dark Navy, Slate, Profit/Loss/Warning colors defined

- [x] **4.1.2** Apply Theme to All Pages ✅ **COMPLETED**
  - [x] Created `web_dashboard/theme.py` with `get_custom_css()` function
  - [x] Updated `app.py` to use theme CSS
  - [x] Replaced hardcoded colors with theme variables

- [x] **4.1.3** Consistent Typography ✅ **COMPLETED**
  - [x] H1-H4 heading sizes defined in theme
  - [x] Body, small, tiny text sizes with proper hierarchy
  - [x] Monospace font for numbers (JetBrains Mono / Fira Code)

### 4.2 Enhanced Information Density

**Tasks:**

- [x] **4.2.1** Market Overview Strip (Top of Dashboard) ✅ **COMPLETED**
  - [x] Show Nifty Spot, Bank Nifty Spot, India VIX side-by-side
  - [x] Display day's change with %
  - [x] Color code: Green (up), Red (down)
  - [x] Add market status badge (Pre-open/Open/Closed)
  - [ ] Show time to current week expiry (future enhancement)

- [x] **4.2.2** Account Summary Card (Fixed Header) ✅ **COMPLETED**
  - [x] Total Capital (large, prominent)
  - [x] Day's P&L (Realized + Unrealized) with %
  - [x] Open Positions Count
  - [x] Margin Utilized / Available
  - [x] Portfolio Heat (gauge: 0-6% with color gradient)
  - [x] Last updated timestamp

- [x] **4.2.3** Enhanced Positions Table ✅ **COMPLETED**
  - [x] Added columns: Symbol, Type (CE/PE/FUT badges), Qty (Lots), Avg Price, LTP (colored), P&L (Rs and %), % Capital at Risk, Stop Loss (with distance %), Days to Expiry (highlighted < 3 days), Greeks (Delta, Theta)
  - [x] Professional HTML table with hover effects, sticky headers
  - [x] Color-coded option type badges (CE blue, PE red, FUT purple)
  - [x] Direction indicators (▲ LONG / ▼ SHORT)
  - [ ] Make table sortable by any column (future enhancement)
  - [ ] Add quick actions: Modify SL, Square Off (future enhancement)

- [x] **4.2.4** Real-Time Indicators ✅ **COMPLETED**
  - [x] Connection status indicator in dashboard header
    - Green dot: Connected/Live
    - Yellow dot: Reconnecting
    - Red dot: Disconnected
  - [x] Last data refresh timestamp
  - [x] Manual refresh button
  - [x] Auto-refresh toggle control
  - [x] Price change blink animations (CSS)

### 4.3 Page-Specific Improvements

**Trading Signals Page:**

- [x] **4.3.1** Signal Visualization ✅ **COMPLETED**
  - [x] Confidence score as progress bar (0-100%)
  - [x] Color-coded signals: Strong Buy (green), Buy (light green), Hold (gray), Sell (light red), Strong Sell (red)
  - [x] Timestamp for each signal
  - [x] Signals grouped by underlying in tabs (Nifty, Bank Nifty, Others)
  - [x] Professional signal cards with hover effects

- [x] **4.3.2** Signal Details ✅ **COMPLETED**
  - [x] Contributing indicators displayed (RSI, MACD, Supertrend, EMA, BB, VWAP)
  - [x] Timeframe selector (1min, 5min, 15min, 30min, 1hour, 1day)
  - [x] "Trade This Signal" button for each tradeable signal
  - [x] Entry/Target/Stop Loss with Risk:Reward calculation
  - [x] Technical chart with Bollinger Bands overlay

**Performance Page:**

- [ ] **4.3.3** Enhanced Analytics
  - [ ] Add date range selector (7D, 30D, 90D, YTD, All)
  - [ ] Show rolling returns (7-day, 30-day, 90-day)
  - [ ] Add benchmark comparison (vs Nifty returns)
  - [ ] Calendar heatmap of daily P&L
  - [ ] Win rate calculation with confidence interval

- [ ] **4.3.4** Interactive Charts
  - [ ] Make equity curve zoomable
  - [ ] Add drawdown overlay on equity curve
  - [ ] Hover tooltip with trade details
  - [ ] Export chart as PNG

**Strategy Builder Page:**

- [ ] **4.3.5** Strategy Visualization
  - [ ] Interactive payoff diagram (drag strikes to adjust)
  - [ ] Show break-even points clearly
  - [ ] Display max profit, max loss, risk:reward ratio
  - [ ] Add "Execute Strategy" button → places all legs simultaneously

**Settings Page:**

- [ ] **4.3.6** Organized Settings Sections
  - [ ] Account & Capital (capital adjustment, deposit/withdrawal log)
  - [ ] Risk Management (daily loss limit, portfolio heat limit, position size limits)
  - [ ] Notifications (email, SMS, Telegram alerts)
  - [ ] Trading Rules (enable/disable specific rules)
  - [ ] API Configuration (token status, re-authenticate button)

### 4.4 Mobile Responsiveness (Basic)

**Tasks:**

- [ ] **4.4.1** Test on Mobile Devices
  - [ ] Ensure critical info visible on small screens
  - [ ] Make tables horizontally scrollable
  - [ ] Ensure buttons are touch-friendly (min 44px height)

- [ ] **4.4.2** Simplify Mobile Layout
  - [ ] Stack columns vertically on mobile
  - [ ] Hide less critical info on small screens
  - [ ] Add hamburger menu for navigation

---

## Phase 5: Advanced Features (Future Enhancements)

**Objective**: Add sophisticated features for experienced traders

### 5.1 WebSocket Real-Time Data

**Tasks:**

- [ ] **5.1.1** Implement Upstox WebSocket Integration
  - [ ] Connect to Upstox WebSocket feed
  - [ ] Subscribe to instruments in watchlist
  - [ ] Handle tick-by-tick price updates
  - [ ] Update UI in real-time (without page refresh)

- [ ] **5.1.2** Optimize for Performance
  - [ ] Throttle UI updates (max 1 update per second)
  - [ ] Use Streamlit session state efficiently
  - [ ] Batch updates for multiple instruments

### 5.2 Automated Trading (Algorithmic Execution)

**Tasks:**

- [ ] **5.2.1** Strategy Automation Framework
  - [ ] Create strategy base class with entry/exit rules
  - [ ] Implement signal-to-order converter
  - [ ] Add backtesting validation before live execution

- [ ] **5.2.2** Paper Trading Mode
  - [ ] Simulated order execution (no real money)
  - [ ] Track performance of automated strategies
  - [ ] Validate before switching to live

- [ ] **5.2.3** Auto-Trading Controls
  - [ ] Master on/off switch
  - [ ] Per-strategy enable/disable
  - [ ] Daily loss limits for auto-trading
  - [ ] Emergency stop button

### 5.3 Advanced Analytics

**Tasks:**

- [ ] **5.3.1** Options-Specific Metrics
  - [ ] Implied Volatility smile visualization
  - [ ] Put-Call Ratio (PCR) analysis
  - [ ] Max Pain calculation
  - [ ] Open Interest analysis

- [ ] **5.3.2** Machine Learning Integration
  - [ ] Price prediction models (LSTM, Prophet)
  - [ ] Volatility forecasting
  - [ ] Signal strength scoring using ML
  - [ ] Risk prediction models

### 5.4 Multi-Broker Support

**Tasks:**

- [ ] **5.4.1** Abstraction Layer
  - [ ] Create broker interface (abstract base class)
  - [ ] Implement adapters for different brokers (Zerodha, Angel One, etc.)
  - [ ] Unified API for all broker operations

- [ ] **5.4.2** Broker Switching
  - [ ] Allow user to select broker in settings
  - [ ] Store broker-specific credentials separately
  - [ ] Handle broker-specific quirks (order types, margin calculations)

### 5.5 Social/Collaborative Features

**Tasks:**

- [ ] **5.5.1** Strategy Sharing
  - [ ] Export strategy as JSON
  - [ ] Import community strategies
  - [ ] Strategy marketplace (optional)

- [ ] **5.5.2** Performance Leaderboard
  - [ ] Anonymized performance comparison
  - [ ] Monthly/yearly rankings
  - [ ] Community insights

---

## Critical Issues Reference (Immediate Attention Required)

### RED FLAG 1: No Order Confirmation Flow
**Risk**: Accidental order execution
**Fix**: Implement Phase 2.1 (Order Confirmation System)
**Priority**: CRITICAL

### RED FLAG 2: No Circuit Breaker for Runaway Losses
**Risk**: Unlimited losses if positions move against you
**Fix**: Implement Phase 2.3 (Daily Loss Circuit Breaker)
**Priority**: CRITICAL

### RED FLAG 3: Stop Loss Not Enforced
**Risk**: Stop losses shown in UI are not actual exchange orders
**Fix**: Implement Phase 2.2 (Stop-Loss Automation)
**Priority**: CRITICAL

### RED FLAG 4: No Session/Token Expiry Handling
**Risk**: App fails silently after 24 hours
**Fix**: Implement Phase 1.4 (Authentication & Token Management)
**Priority**: HIGH

### RED FLAG 5: Backtesting Uses Generic Equity Logic
**Risk**: Options backtesting inaccurate (ignores time decay, IV changes)
**Fix**: Implement Phase 3.2 (Options Chain Historical Data) and enhance BacktestEngine
**Priority**: MEDIUM (only affects backtesting, not live trading)

---

## Development Workflow

### Branch Strategy
- `main` - Production-ready code
- `develop` - Integration branch for completed features
- `feature/phase-X-Y` - Individual feature branches

### Commit Guidelines
- Use descriptive commit messages
- Reference phase and task number (e.g., "Phase 1.2.1: Replace dummy positions with live data")
- Include co-author tag for Claude Code contributions

### Testing Requirements
- Unit tests for all service layer functions
- Integration tests for API calls
- Manual testing for UI changes
- Performance testing for real-time data updates

### Documentation
- Update README.md with new features
- Document API methods with docstrings
- Create user guide for new features
- Maintain CHANGELOG.md

---

## Current Development Status

### Completed ✅
- Initial application architecture
- Risk management modules
- Backtesting engine (basic)
- Options strategy templates
- Web dashboard skeleton
- Upstox API integration (basic)
- Credentials verified and working
- **Phase 1.1: Data Service Layer** (Dec 30, 2025)
  - market_data_service.py with caching, rate limiting, connection tracking
  - portfolio_service.py with positions, holdings, Greeks aggregation
  - order_service.py with order/trade book and audit logging
  - capital_service.py with TWR/CAGR calculations
  - historical_data_service.py with gap detection
  - SQLite cache infrastructure with TTL support
- **Phase 1.3: Capital Management** (Dec 30, 2025)
  - Full capital persistence system
  - Deposit/withdrawal tracking
  - Settings UI with capital dashboard
- **Phase 1.4: Token Management** (Dec 30, 2025)
  - Token storage with obfuscation
  - Expiry tracking and warnings
  - Dashboard status indicators

- **Phase 2.1: Order Confirmation System** (Dec 30, 2025)
  - OrderManager with preview, validation, execution logging
  - Position size limits by instrument type
  - High-value order warnings
  - Daily order count limits
- **Phase 2.2: Stop-Loss Automation** (Dec 30, 2025)
  - StopLossManager with trailing SL support
  - Default SL percentages by instrument type
  - Emergency square-off capability
- **Phase 2.3: Daily Loss Circuit Breaker** (Dec 30, 2025)
  - CircuitBreaker with tiered alerts (50%, 80%, 100%)
  - Automatic trading block at limit
  - Password-protected override

- **Phase 3: Data Infrastructure for Backtesting** (Dec 30, 2025)
  - historical_downloader.py with rate limiting, retry logic, Parquet storage
  - options_chain_downloader.py with IV history and IV Rank/Percentile
  - parquet_schemas.py with OHLCV, option chain, IV history schemas
  - data_retrieval_service.py unified data access interface
  - bootstrap_data.py script for initial data download
  - Comprehensive data documentation in data/historical/README.md

### In Progress 🔄
- Phase 2.4: Real-Time Risk Monitoring (some features complete in portfolio_service.py)
- UI Integration for safety mechanisms
- Phase 4: UI/UX Professional Polish

### Blocked/Waiting ⏸️
- None currently

---

## Notes & Decisions

**Last Updated**: December 30, 2025

### Key Decisions Made
1. **Data Storage Format**: Parquet chosen over CSV/SQLite for historical data (better compression, faster reads)
2. **Stop-Loss Strategy**: Will use SL-M orders on exchange (Option 1) for reliability
3. **Capital Management**: Implement both global and per-strategy allocation
4. **Token Management**: Store locally with encryption, implement 2-hour expiry warning

### Assumptions
- Upstox API rate limits: 250 requests/minute
- Access tokens expire in 24 hours
- Historical data available for past 1 year from Upstox
- User has basic trading knowledge (understands F&O concepts)

### Questions/Clarifications Needed
- None currently

---

## Resources & References

### Upstox API Documentation
- Historical Candles: https://upstox.com/developer/api-documentation/v3/get-historical-candle-data
- Intraday Candles: https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data
- WebSocket Feed: https://upstox.com/developer/api-documentation/websocket-streaming
- Order Placement: https://upstox.com/developer/api-documentation/v3/place-order

### F&O Trading Resources
- NSE Options Chain: https://www.nseindia.com/option-chain
- India VIX: https://www.nseindia.com/products-services/indices-india-vix

### Technical Resources
- Streamlit Documentation: https://docs.streamlit.io/
- Pandas User Guide: https://pandas.pydata.org/docs/
- Apache Parquet Format: https://parquet.apache.org/

---

**Next Action**: Begin Phase 4 - UI/UX Professional Polish
**Recommended Starting Point**: Phase 4.1 (Professional Color Scheme)
**Phases Completed**: Phase 1 (Foundation), Phase 2 (Safety Mechanisms), Phase 3 (Data Infrastructure)

---

*This document is a living roadmap and will be updated as development progresses.*
