# F&O Trading Web Dashboard - User Guide

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Make sure you're in the project root directory
pip install -r requirements.txt
```

### 2. Launch Dashboard

```bash
python launch_dashboard.py
```

Or directly with Streamlit:

```bash
streamlit run web_dashboard/app.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`

---

## 📊 Dashboard Features

### 1. 🏠 Main Dashboard

**Overview Screen with:**
- Real-time account summary (Capital, P&L, Portfolio Heat)
- Active positions table
- Live trading signals
- Economic calendar events
- Trading rules status
- Equity curve chart

**Key Metrics:**
- 💰 Account Balance
- 📊 Today's P&L
- 🔥 Portfolio Heat
- 📈 Trades Count

**Color Coding:**
- 🟢 Green: Positive/Healthy
- 🔴 Red: Negative/Critical
- 🟡 Yellow: Warning/Caution

---

### 2. 📊 Trading Signals

**Features:**
- Multi-instrument signal monitoring
- Timeframe selection (1min to 1day)
- Signal strength filtering
- Detailed signal breakdown
- Technical indicator analysis
- Interactive price charts
- Signal history tracking

**Signal Types:**
- 🚀 STRONG_BUY
- 📈 BUY
- ⏸️ HOLD
- 📉 SELL
- ⬇️ STRONG_SELL

**Each Signal Shows:**
- Entry price
- Target price
- Stop loss
- Risk:Reward ratio
- Contributing indicators

---

### 3. 🎯 Strategy Builder

**Three Strategy Types:**

#### A. Options Strategies
Pre-built professional strategies:
- Iron Condor (range-bound)
- Bull Call Spread (bullish)
- Bear Put Spread (bearish)
- Long Straddle (high volatility)
- Short Strangle (low volatility)
- Calendar Spread (time decay)
- Butterfly Spread (narrow range)

**For Each Strategy:**
- Input parameters (spot, IV rank, expiry)
- Strategy legs breakdown
- P&L profile
- Interactive payoff diagram
- Breakeven points
- Risk:Reward analysis

#### B. Directional Strategies
Trend and momentum strategies:
- Supertrend trend following
- Breakout with volume
- Mean reversion (BB + RSI)
- Opening range breakout (ORB)
- Support/Resistance bounce

**Shows:**
- Entry/exit rules
- Current signal status
- Risk metrics
- Live recommendations

#### C. Custom Spread Builder
Build your own multi-leg strategies:
- Add 1-6 legs
- Configure each leg (BUY/SELL, CALL/PUT, strike, premium)
- Automatic P&L calculation
- Interactive payoff diagram
- Risk analysis

---

### 4. 📈 Performance Analytics

**Comprehensive Performance Tracking:**

#### Key Metrics Dashboard
- Total P&L and Return %
- Win Rate
- Profit Factor
- Sharpe Ratio
- Maximum Drawdown
- Average Win/Loss

#### Interactive Charts
1. **Equity Curve**
   - Daily equity progression
   - Drawdown overlay
   - Initial capital baseline

2. **Monthly Returns Heatmap**
   - Color-coded monthly performance
   - Year-over-year comparison

3. **P&L Distribution**
   - Winner vs loser histogram
   - Distribution analysis

4. **Hourly Performance**
   - Average P&L by hour
   - Win rate by time of day
   - Identify best trading hours

5. **Strategy Comparison**
   - Performance by strategy
   - Return % comparison
   - Trade count analysis

#### Recent Trades Table
- Last 10+ trades
- Color-coded P&L
- Strategy attribution
- Hold time analysis

---

### 5. 💼 Position Management

**Three Main Tabs:**

#### Active Positions
- Real-time position tracking
- Unrealized P&L
- Entry/LTP comparison
- Stop loss & target levels
- Position modification controls

**For Each Position:**
- Detailed metrics
- Risk analysis
- Distance to SL/Target
- R:R ratio
- Action buttons (modify, close, add)

#### Orders
- Pending orders
- Executed orders
- Cancelled orders
- Place new order form

**Order Types Supported:**
- LIMIT
- MARKET
- STOP LOSS (SL)
- STOP LOSS MARKET (SL-M)

#### Trade History
- Complete trade log
- Filterable by period, instrument, status
- Color-coded wins/losses
- Summary statistics
- Export functionality

---

### 6. ⚙️ Settings

**Four Configuration Sections:**

#### A. API Credentials
- Upstox API key & secret
- Redirect URI
- Sandbox mode toggle
- Connection testing
- Status monitoring

#### B. Trading Rules
Configure automatic risk controls:

**Daily Limits:**
- Max trades per day (1-20)
- Max daily loss (₹)
- Max consecutive losses
- Max portfolio heat (%)

**Time Restrictions:**
- Block first 15 minutes
- Block last 15 minutes
- Revenge trading cooldown
- Min time between trades

**Drawdown Management:**
- Caution level (%)
- Warning level (%)
- Critical level (%)
- Emergency level (%)

#### C. Preferences
- Theme selection (Light/Dark)
- Chart preferences
- Notification settings
- Alert conditions
- Language & region
- Currency display

#### D. About
- Version information
- System status
- Support links
- Documentation access
- Update checker

---

## 🎨 UI/UX Features

### Navigation
- **Sidebar:** Always visible navigation menu
- **Tabs:** Organize related content
- **Expandable Sections:** Collapse/expand details
- **Modal Dialogs:** Focused actions

### Visual Design
- **Color Coding:** Consistent throughout
  - Green: Positive/Profit/Healthy
  - Red: Negative/Loss/Critical
  - Yellow: Warning/Caution
  - Blue: Info/Normal

- **Cards:** Gradient cards for key metrics
- **Tables:** Sortable, color-coded data tables
- **Charts:** Interactive Plotly visualizations

### Responsive Layout
- **Wide Layout:** Maximizes screen space
- **Columns:** Organized multi-column layouts
- **Auto-scaling:** Adapts to screen size

---

## 💡 Tips & Tricks

### Performance
1. **Use filters** to reduce data load
2. **Collapse sections** not in use
3. **Select specific timeframes** for faster loading

### Workflow
1. Start at **Dashboard** for overview
2. Check **Signals** for opportunities
3. Build strategy in **Strategy Builder**
4. Monitor in **Positions**
5. Review in **Performance**

### Customization
1. Set your preferred timeframe
2. Configure alert preferences
3. Customize trading rules
4. Choose chart theme

---

## 🔧 Troubleshooting

### Dashboard Won't Start
```bash
# Check if Streamlit is installed
pip install streamlit

# Try running directly
streamlit run web_dashboard/app.py
```

### Import Errors
```bash
# Ensure parent modules are importable
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install package
pip install -e .
```

### Charts Not Displaying
```bash
# Install/update Plotly
pip install --upgrade plotly
```

### Slow Performance
1. Reduce data range in filters
2. Close unused browser tabs
3. Clear Streamlit cache (Settings → Clear Cache)

---

## 📱 Browser Compatibility

**Recommended:**
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Not Recommended:**
- ❌ Internet Explorer (any version)
- ⚠️ Very old browser versions

---

## 🔐 Security Notes

1. **API Credentials:** Stored in session (not persistent)
2. **Local Only:** Dashboard runs on localhost
3. **No External Access:** Not exposed to internet
4. **Sandbox Mode:** Test safely without real trading

**For Production:**
- Use environment variables for credentials
- Enable HTTPS
- Add authentication
- Regular security updates

---

## 🚀 Advanced Usage

### Running on Different Port
```bash
streamlit run web_dashboard/app.py --server.port=8502
```

### Running on Network
```bash
# ⚠️ Only on trusted networks!
streamlit run web_dashboard/app.py --server.address=0.0.0.0
```

### Headless Mode (Server)
```bash
streamlit run web_dashboard/app.py --server.headless=true
```

---

## 📊 Dashboard vs Terminal UI

| Feature | Web Dashboard | Terminal UI |
|---------|--------------|-------------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ Beginner-friendly | ⭐⭐⭐ Power users |
| **Visuals** | ⭐⭐⭐⭐⭐ Rich charts | ⭐⭐⭐ Basic tables |
| **Interactivity** | ⭐⭐⭐⭐⭐ Click & edit | ⭐⭐ Command-based |
| **Speed** | ⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐⭐ Instant |
| **Resources** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Minimal |
| **Remote Access** | ⭐⭐⭐⭐⭐ Browser-based | ⭐⭐⭐⭐ SSH |

**Use Web Dashboard For:**
- Daily trading operations
- Strategy building
- Performance analysis
- Beginner learning

**Use Terminal UI For:**
- Quick status checks
- SSH sessions
- Minimal resource usage
- Automation/scripts

---

## 🎓 Learning Path

### Day 1: Basics
1. Launch dashboard
2. Explore main overview
3. Check trading signals
4. Review settings

### Day 2: Strategy
1. Build first option strategy
2. Analyze payoff diagram
3. Compare strategies
4. Save favorites

### Day 3: Trading
1. Monitor positions
2. Place test orders (sandbox)
3. Review performance
4. Adjust rules

### Week 2: Advanced
1. Custom spread building
2. Performance optimization
3. Alert configuration
4. Strategy backtesting

---

## 📞 Support

**Issues?**
1. Check this guide
2. Review error messages
3. Check logs in `logs/`
4. Restart dashboard

**Feature Requests:**
- Submit via GitHub Issues
- Include use case description
- Provide screenshots if applicable

---

## 🔄 Updates

**Checking for Updates:**
1. Go to Settings → About
2. Click "Check for Updates"

**Manual Update:**
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

**Enjoy trading with the F&O Web Dashboard! 📈🚀**
