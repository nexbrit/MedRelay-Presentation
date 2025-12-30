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

- [ ] **1.1.1** Create `market_data_service.py`
  - [ ] Implement `get_live_quote(instrument_key)` with 5-second cache
  - [ ] Implement `get_option_chain(underlying, expiry)` with 30-second cache
  - [ ] Add connection state tracking (Connected/Disconnected/Reconnecting)
  - [ ] Implement fallback to last known good data if API fails
  - [ ] Add rate limiting (respect Upstox limits: 250 req/min)

- [ ] **1.1.2** Create `portfolio_service.py`
  - [ ] Implement `get_positions()` - fetch from Upstox API
  - [ ] Implement `get_holdings()` - fetch from Upstox API
  - [ ] Implement `calculate_unrealized_pnl()` - real-time P&L calculation
  - [ ] Implement `calculate_realized_pnl()` - closed positions P&L
  - [ ] Add portfolio Greeks aggregation (sum Delta, Gamma, Theta, Vega)

- [ ] **1.1.3** Create `order_service.py`
  - [ ] Implement `get_order_book()` - fetch all orders
  - [ ] Implement `get_trade_book()` - fetch executed trades
  - [ ] Implement `track_order_status(order_id)` - poll for updates
  - [ ] Add order history caching

- [ ] **1.1.4** Create SQLite cache infrastructure
  - [ ] Design cache schema with TTL support
  - [ ] Implement cache invalidation logic
  - [ ] Add cache statistics (hit rate, miss rate)

### 1.2 Replace Dummy Data with Live Data

**Files to Modify:**
- `web_dashboard/app.py` (lines 244-265: positions data)
- `web_dashboard/pages/positions.py` (lines 44-55: sample positions)
- `web_dashboard/pages/trading_signals.py` (signal generation)
- `web_dashboard/pages/performance.py` (equity curve, metrics)

**Tasks:**

- [ ] **1.2.1** Update Main Dashboard (`app.py`)
  - [ ] Replace hardcoded positions with `portfolio_service.get_positions()`
  - [ ] Calculate live P&L using current LTP
  - [ ] Display actual margin utilized vs available
  - [ ] Show real-time portfolio heat percentage
  - [ ] Add "Last Updated" timestamp to all data sections
  - [ ] Add connection status indicator (green dot = connected)

- [ ] **1.2.2** Update Positions Page
  - [ ] Fetch live positions from Upstox
  - [ ] Calculate real-time Greeks for each options position
  - [ ] Show combined portfolio Greeks
  - [ ] Display margin requirement per position
  - [ ] Add actual LTP with last update time
  - [ ] Remove all `positions_data = {...}` hardcoded dictionaries

- [ ] **1.2.3** Update Trading Signals Page
  - [ ] Fetch real-time price data for signal calculation
  - [ ] Generate signals from live market data
  - [ ] Add last signal calculation timestamp
  - [ ] Remove sample signal data

- [ ] **1.2.4** Update Performance Page
  - [ ] Replace dummy equity curve with actual trade history
  - [ ] Calculate real returns from closed trades
  - [ ] Show actual win rate, Sharpe ratio from real data
  - [ ] Add "No data available" state for new accounts

### 1.3 Capital Management System

**Files to Create/Modify:**
- `data/services/capital_service.py` (new)
- `web_dashboard/pages/settings.py` (modify)
- `data/persistence/app_state.db` (schema)

**Tasks:**

- [ ] **1.3.1** Create `capital_service.py`
  - [ ] Implement `get_current_capital()` - fetch from DB
  - [ ] Implement `set_initial_capital(amount)` - first-time setup
  - [ ] Implement `adjust_capital(amount, type, reason)` - deposit/withdrawal
  - [ ] Implement `get_capital_history()` - audit trail
  - [ ] Calculate Time-Weighted Return (TWR) accounting for deposits/withdrawals

- [ ] **1.3.2** Design Capital Database Schema
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

- [ ] **1.3.3** Update Settings Page UI
  - [ ] Add "Capital & Account" section
  - [ ] Display current capital (large, prominent)
  - [ ] Add "Adjust Capital" button → opens modal
  - [ ] Modal fields: Amount, Type (Deposit/Withdrawal), Reason
  - [ ] Show capital adjustment history table
  - [ ] Add initial capital setup wizard (first launch)

- [ ] **1.3.4** Integrate with Position Sizing
  - [ ] Modify `PositionSizer` to use `capital_service.get_current_capital()`
  - [ ] Recalculate max position sizes when capital changes
  - [ ] Update portfolio heat calculations with new capital

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

- [ ] **1.4.1** Create `token_manager.py`
  - [ ] Implement `store_token(access_token, expiry_time)`
  - [ ] Implement `get_token()` - return token if valid, else None
  - [ ] Implement `is_token_expired()` - check expiry
  - [ ] Implement `get_time_until_expiry()` - for warnings
  - [ ] Store tokens securely (encrypted or in secure location)

- [ ] **1.4.2** Update OAuth Flow in `main.py`
  - [ ] Automatically store token expiry (Upstox tokens expire in 24h)
  - [ ] Add token refresh reminder

- [ ] **1.4.3** Add Token Status to Dashboard
  - [ ] Show token expiry countdown in sidebar
  - [ ] Warning banner when < 2 hours remaining
  - [ ] Red alert when expired with re-auth button
  - [ ] Auto-redirect to auth page if token expired

- [ ] **1.4.4** Implement Auto Re-Authentication (Advanced)
  - [ ] Background job to check token expiry
  - [ ] Email/SMS notification when token about to expire
  - [ ] One-click re-auth flow

---

## Phase 2: Safety Mechanisms - HIGH PRIORITY

**Objective**: Implement critical safety features to prevent trading disasters

### 2.1 Order Confirmation System

**Files to Modify:**
- `api/upstox_client.py` (add confirmation layer)
- `web_dashboard/pages/positions.py` (add order placement UI)
- `orders/order_manager.py` (new)

**Tasks:**

- [ ] **2.1.1** Create Order Preview Modal
  - [ ] Display order details: Symbol, Qty, Price, Order Type
  - [ ] Calculate and show estimated margin requirement
  - [ ] Show potential risk (max loss) for the position
  - [ ] Display portfolio heat impact (before and after)
  - [ ] Add confirmation checkbox: "I confirm this order"
  - [ ] Require explicit "Execute" button click

- [ ] **2.1.2** Implement Order Validation
  - [ ] Check if sufficient margin available
  - [ ] Verify portfolio heat limit won't be exceeded
  - [ ] Check daily order count limits (prevent over-trading)
  - [ ] Validate order against trading rules (from `rules/enforcer.py`)

- [ ] **2.1.3** Add High-Value Order Warnings
  - [ ] Flag orders > 10% of capital
  - [ ] Require additional confirmation for large orders
  - [ ] Suggest position size reduction if oversized

- [ ] **2.1.4** Implement Order Execution Logging
  - [ ] Log every order attempt (approved/rejected/failed)
  - [ ] Track who approved (user or auto-trading system)
  - [ ] Store in `order_audit_log` table

### 2.2 Stop-Loss Automation

**Files to Create/Modify:**
- `orders/stop_loss_manager.py` (new)
- `risk/stop_loss_enforcer.py` (new)
- Background service for monitoring

**Tasks:**

- [ ] **2.2.1** Design Stop-Loss Strategy
  - [ ] Option 1: Place SL-M orders on exchange (recommended)
  - [ ] Option 2: Monitor prices and trigger market orders
  - [ ] Decision: Choose Option 1 for reliability

- [ ] **2.2.2** Implement SL-M Order Placement
  - [ ] When position opened, immediately place SL-M order
  - [ ] Calculate SL price based on:
    - Fixed percentage (e.g., 2% for stocks, 20% for options)
    - ATR-based (2x ATR from entry)
    - User-defined absolute value
  - [ ] Link SL order to parent position (order tags)

- [ ] **2.2.3** Stop-Loss Modification System
  - [ ] Allow users to modify SL from UI
  - [ ] Trailing stop-loss feature (move SL up as profit increases)
  - [ ] Validate SL modifications (can't move SL further from current price)

- [ ] **2.2.4** Stop-Loss Monitoring (Fallback)
  - [ ] Background service to monitor positions every 30 seconds
  - [ ] If LTP crosses SL and no SL-M order exists, trigger market order
  - [ ] Send alert when SL is hit

- [ ] **2.2.5** Emergency Square-Off Button
  - [ ] Prominent "PANIC EXIT" button in UI
  - [ ] Square off ALL positions at market price
  - [ ] Confirmation dialog with countdown (5 seconds)

### 2.3 Daily Loss Circuit Breaker

**Files to Create/Modify:**
- `risk/circuit_breaker.py` (new)
- `web_dashboard/app.py` (add visual indicator)

**Tasks:**

- [ ] **2.3.1** Implement Loss Monitoring
  - [ ] Track daily realized + unrealized P&L
  - [ ] Define daily loss limit (e.g., 2% of capital)
  - [ ] Calculate distance to limit in real-time

- [ ] **2.3.2** Tiered Alert System
  - [ ] 50% of limit: Yellow warning banner
  - [ ] 80% of limit: Orange alert + email notification
  - [ ] 100% of limit: Red alert + automatic action

- [ ] **2.3.3** Automatic Square-Off at Limit
  - [ ] When 100% of daily loss limit hit, square off all positions
  - [ ] Use market orders for immediate execution
  - [ ] Block new position entry for rest of the day
  - [ ] Send SMS + Email notification

- [ ] **2.3.4** Manual Override (with Safeguards)
  - [ ] Allow user to disable circuit breaker (requires password)
  - [ ] Log override action with reason
  - [ ] Require re-enable next day (doesn't persist)

- [ ] **2.3.5** Visual Indicators
  - [ ] Progress bar showing daily loss vs limit
  - [ ] Color-coded: Green (safe) → Yellow → Orange → Red
  - [ ] Display "Circuit Breaker Active" banner when limit hit

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

- [ ] **3.1.1** Create `historical_downloader.py`
  - [ ] Implement `download_index_history(instrument, start_date, end_date, interval)`
    - Supported intervals: 1minute, 15minute, 30minute, day
  - [ ] Implement rate limiting (respect Upstox 250 req/min limit)
  - [ ] Implement retry logic with exponential backoff
  - [ ] Handle API errors gracefully (partial data is ok)
  - [ ] Save data in Parquet format (efficient compression)

- [ ] **3.1.2** Define Storage Schema
  ```python
  # Index OHLCV Schema
  {
      'timestamp': datetime,
      'open': float,
      'high': float,
      'low': float,
      'close': float,
      'volume': int,
      'oi': int  # open interest
  }
  ```

- [ ] **3.1.3** Implement Download Scheduling
  - [ ] Daily job to download previous day's data
  - [ ] Weekly job to download weekly candles
  - [ ] Monthly job to download monthly candles
  - [ ] Use `schedule` library or cron job

- [ ] **3.1.4** Data Validation & Integrity Checks
  - [ ] Verify no missing dates (check for gaps)
  - [ ] Validate OHLC relationships (High >= Close >= Low)
  - [ ] Check for duplicate timestamps
  - [ ] Generate data quality report

### 3.2 Options Chain Historical Data

**Tasks:**

- [ ] **3.2.1** Create `options_chain_downloader.py`
  - [ ] Download EOD option chain snapshots
  - [ ] Store strike prices, premiums, IV, Greeks, OI
  - [ ] Organize by expiry date

- [ ] **3.2.2** Options Data Schema
  ```python
  {
      'timestamp': datetime,
      'underlying_symbol': str,  # NIFTY/BANKNIFTY
      'underlying_spot': float,
      'expiry_date': date,
      'strike_price': float,
      'option_type': str,  # CE/PE
      'ltp': float,
      'bid_price': float,
      'bid_qty': int,
      'ask_price': float,
      'ask_qty': int,
      'oi': int,
      'oi_change': int,
      'volume': int,
      'iv': float,  # implied volatility
      'delta': float,
      'gamma': float,
      'theta': float,
      'vega': float
  }
  ```

- [ ] **3.2.3** Storage Strategy for Options
  - [ ] Store by expiry cycle (weekly/monthly)
  - [ ] Keep current cycle + 2-3 past cycles
  - [ ] Archive old data (compress further or delete)
  - [ ] Typical storage: ~50-100 MB per expiry cycle

- [ ] **3.2.4** Historical IV Database
  - [ ] Calculate and store daily IV Rank (current IV vs 1-year range)
  - [ ] Calculate and store daily IV Percentile
  - [ ] This enables IV-based strategy backtesting

### 3.3 Data Retrieval Service

**Tasks:**

- [ ] **3.3.1** Create `data_retrieval_service.py`
  - [ ] Implement `get_historical_data(instrument, start, end, interval)`
  - [ ] Implement `get_option_chain_snapshot(underlying, expiry, date)`
  - [ ] Implement caching for frequently accessed data
  - [ ] Return data as pandas DataFrame

- [ ] **3.3.2** Data Export Functions
  - [ ] Export to CSV for Excel analysis
  - [ ] Export to JSON for external tools
  - [ ] Provide data via REST API (optional, advanced)

### 3.4 Initial Data Bootstrap

**Tasks:**

- [ ] **3.4.1** Download Initial Dataset
  - [ ] Nifty 50: 15-minute data for past 2 years
  - [ ] Bank Nifty: 15-minute data for past 2 years
  - [ ] Nifty 50: Daily data for past 10 years
  - [ ] Bank Nifty: Daily data for past 10 years
  - [ ] Note: Upstox API may limit historical data to 1 year; use NSE Bhav copies for older data

- [ ] **3.4.2** Document Data Limitations
  - [ ] Create `data/README.md` explaining:
    - Data sources
    - Available date ranges
    - Known gaps or issues
    - Update frequency

---

## Phase 4: UI/UX Professional Polish

**Objective**: Transform dashboard into a professional trading interface

### 4.1 Professional Color Scheme

**Tasks:**

- [ ] **4.1.1** Define Color Palette
  ```css
  --bg-primary: #0f172a (Dark Navy)
  --bg-secondary: #1e293b (Slate)
  --bg-accent: #334155 (Lighter Slate)
  --text-primary: #f1f5f9 (Light)
  --text-secondary: #94a3b8 (Muted)
  --profit: #22c55e (Green)
  --loss: #ef4444 (Red)
  --warning: #f59e0b (Amber)
  --info: #3b82f6 (Blue)
  ```

- [ ] **4.1.2** Apply Theme to All Pages
  - [ ] Create `web_dashboard/theme.py` with Streamlit theme config
  - [ ] Update all `st.markdown()` with custom CSS
  - [ ] Replace generic colors with theme colors

- [ ] **4.1.3** Consistent Typography
  - [ ] Heading sizes: H1 (2.5rem), H2 (2rem), H3 (1.5rem)
  - [ ] Body text: 1rem (16px)
  - [ ] Small text (timestamps, labels): 0.875rem (14px)
  - [ ] Monospace for numbers: Use tabular figures

### 4.2 Enhanced Information Density

**Tasks:**

- [ ] **4.2.1** Market Overview Strip (Top of Dashboard)
  - [ ] Show Nifty Spot, Bank Nifty Spot, India VIX side-by-side
  - [ ] Display day's change with % and absolute value
  - [ ] Color code: Green (up), Red (down)
  - [ ] Add market status badge (Pre-open/Open/Closed)
  - [ ] Show time to current week expiry (e.g., "2d 4h to expiry")

- [ ] **4.2.2** Account Summary Card (Fixed Header)
  - [ ] Total Capital (large, prominent)
  - [ ] Day's P&L (Realized + Unrealized) with %
  - [ ] Open Positions Count
  - [ ] Margin Utilized / Available (progress bar)
  - [ ] Portfolio Heat (gauge: 0-6% with color gradient)
  - [ ] Last updated timestamp

- [ ] **4.2.3** Enhanced Positions Table
  - [ ] Add columns:
    - Symbol
    - Type (CE/PE/FUT)
    - Qty (Lots)
    - Avg Price
    - LTP (with color: green if profitable)
    - P&L (Rs and %)
    - % of Capital at Risk
    - Stop Loss (with distance in %)
    - Days to Expiry (highlight if < 3 days)
    - Greeks (Delta, Theta for options)
  - [ ] Make table sortable by any column
  - [ ] Add quick actions: Modify SL, Square Off

- [ ] **4.2.4** Real-Time Indicators
  - [ ] Add connection status indicator (top-right corner)
    - Green dot: Connected to Upstox
    - Yellow dot: Reconnecting
    - Red dot: Disconnected
  - [ ] Show last data refresh timestamp
  - [ ] Add manual refresh button

### 4.3 Page-Specific Improvements

**Trading Signals Page:**

- [ ] **4.3.1** Signal Visualization
  - [ ] Show confidence score as progress bar (0-100%)
  - [ ] Color code signals: Strong Buy (green), Buy (light green), Hold (gray), Sell (light red), Strong Sell (red)
  - [ ] Add timestamp for each signal
  - [ ] Group signals by underlying (tabs: Nifty, Bank Nifty, Others)

- [ ] **4.3.2** Signal Details
  - [ ] Show contributing indicators (RSI value, MACD crossover, etc.)
  - [ ] Display timeframe selector (1min, 5min, 15min, 1day)
  - [ ] Add "Trade This Signal" button → opens order form

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

### In Progress 🔄
- Phase 1: Foundation (Not Started)

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

**Next Action**: Begin Phase 1 - Foundation
**Recommended Starting Point**: Phase 1.2 (Replace Dummy Data with Live Data)
**Estimated Effort**: Phase 1 = ~40-60 hours of development

---

*This document is a living roadmap and will be updated as development progresses.*
