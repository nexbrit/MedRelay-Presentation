# Phase 3 & 4 Features - Usage Guide

## Quick Start Guide for New Features

This guide covers the new features added in Phase 3 (Analytics & Intelligence) and Phase 4 (Professional Controls).

---

## Table of Contents

1. [Performance Analytics](#1-performance-analytics)
2. [News & Economic Calendar](#2-news--economic-calendar)
3. [Strategy Templates](#3-strategy-templates)
4. [Trading Rules Enforcement](#4-trading-rules-enforcement)
5. [Drawdown Management](#5-drawdown-management)
6. [Terminal Dashboard](#6-terminal-dashboard)

---

## 1. Performance Analytics

### Trade Journal

Record and analyze all your trades:

```python
from analytics import TradeJournal

# Initialize journal
journal = TradeJournal("data/trade_journal.db")

# Record trade entry
trade_id = journal.record_trade_entry(
    instrument="NIFTY 24000 CE",
    direction="LONG",
    entry_price=250,
    quantity=50,
    strategy="Trend Following",
    market_regime="UPTREND",
    entry_reason="Supertrend buy signal",
    stop_loss=240,
    target=270,
    notes="High momentum breakout"
)

# Record trade exit
journal.record_trade_exit(
    trade_id=trade_id,
    exit_price=265,
    exit_reason="Target reached",
    commission=40,
    slippage=2
)

# Get all trades
all_trades = journal.get_all_trades()
print(all_trades)

# Analyze revenge trading
revenge_trades = journal.detect_revenge_trading(hours=1)

# Best trading hours
best_hours = journal.get_best_trading_hours()
print(best_hours)
```

### Performance Metrics

Calculate comprehensive metrics:

```python
from analytics import PerformanceMetrics

# Initialize with trades
metrics = PerformanceMetrics(trades_df)

# Calculate all metrics
results = metrics.calculate_all_metrics(initial_capital=100000)

# Print formatted report
metrics.print_report()

# Get daily summary
daily = metrics.get_daily_summary()
print(f"Today: {daily['total_trades']} trades, P&L: ₹{daily['pnl']}")
```

### Visualizations

Create interactive charts:

```python
from analytics import PerformanceVisualizer

viz = PerformanceVisualizer(trades_df)

# Equity curve with drawdown
fig = viz.plot_equity_curve(initial_capital=100000, show_drawdown=True)
fig.show()

# Monthly returns heatmap
heatmap = viz.plot_monthly_returns_heatmap()
heatmap.show()

# P&L distribution
dist = viz.plot_pnl_distribution()
dist.show()

# Hourly performance
hourly = viz.plot_hourly_performance()
hourly.show()

# Complete dashboard
viz.create_performance_dashboard(
    initial_capital=100000,
    save_html="dashboard.html"
)
```

---

## 2. News & Economic Calendar

### Economic Calendar

Track important events:

```python
from news import EconomicCalendar

calendar = EconomicCalendar()

# Add RBI meeting
calendar.add_rbi_policy_meeting("2024-12-08")

# Add earnings
calendar.add_earnings_announcement(
    date="2024-12-15",
    company="RELIANCE",
    importance=EventImportance.HIGH
)

# Get upcoming events
upcoming = calendar.get_upcoming_events(days=7)
calendar.print_upcoming_events(days=7)

# Check if today is expiry week
if calendar.is_expiry_week():
    print("⚠️ Expiry week - reduce position size")

# Get position size adjustment
multiplier = calendar.get_position_size_adjustment()
print(f"Position size: {multiplier*100}% of normal")

# Days to next expiry
days = calendar.get_days_to_expiry()
print(f"Days to expiry: {days}")
```

### Sentiment Analysis

Analyze market sentiment:

```python
from news import SentimentAnalyzer

analyzer = SentimentAnalyzer()

# Sample headlines
headlines = [
    "Nifty surges 200 points on strong buying",
    "Market rallies to new all-time high",
    "Banking stocks lead the gains",
]

# Analyze sentiment
sentiment = analyzer.get_market_sentiment_indicator(headlines)

# Print report
analyzer.print_sentiment_report(headlines)

# Contrarian signal
if sentiment['contrarian_signal'] == 'EXTREME_BULLISH_SELL_SIGNAL':
    print("⚠️ Extreme bullishness - consider taking profits")
```

---

## 3. Strategy Templates

### Options Strategies

```python
from strategies import OptionsStrategyBuilder

# Initialize with current spot
builder = OptionsStrategyBuilder(spot_price=23950, lot_size=50)

# Iron Condor (range-bound)
iron_condor = builder.iron_condor(
    iv_rank=60,
    target_premium=10000,
    wing_width=100,
    expiry_days=30
)
builder.print_strategy_details(iron_condor)

# Bull Call Spread
bull_call = builder.bull_call_spread(
    target_gain_pct=5,
    expiry_days=30
)
builder.print_strategy_details(bull_call)

# Get strategy recommendation
recommended = builder.suggest_strategy(
    market_regime="RANGING",
    iv_rank=65,
    outlook="neutral"
)
builder.print_strategy_details(recommended)
```

### Directional Strategies

```python
from strategies import DirectionalStrategies

strategies = DirectionalStrategies()

# Trend following
trend_signal = strategies.supertrend_strategy(df)
print(f"Signal: {trend_signal['signal']}")
print(f"Entry: {trend_signal['entry_price']}")
print(f"Stop Loss: {trend_signal['stop_loss']}")
print(f"Target: {trend_signal['target']}")

# Breakout strategy
breakout = strategies.breakout_strategy(df, lookback=20)

# Mean reversion
mean_rev = strategies.mean_reversion_strategy(df)

# Opening range breakout
orb = strategies.opening_range_breakout(df, or_minutes=15)
```

### Spread Builder

```python
from strategies import SpreadBuilder

builder = SpreadBuilder(spot_price=23950, lot_size=50)

# Bull call debit spread
spread = builder.build_bull_call_debit_spread(
    long_strike=23900,
    short_strike=24000,
    long_premium=150,
    short_premium=75,
    quantity=1
)

# Print analysis
builder.print_spread_details()

# Visualize payoff
payoff_data = builder.visualize_payoff()
```

---

## 4. Trading Rules Enforcement

Prevent emotional trading:

```python
from rules import TradingRulesEnforcer

# Initialize with rules
enforcer = TradingRulesEnforcer({
    'max_trades_per_day': 5,
    'max_consecutive_losses': 3,
    'max_daily_loss': 5000,
    'revenge_trading_cooldown_minutes': 60
})

# Check if trading is allowed
can_trade, reason = enforcer.can_trade(
    portfolio_heat=3.5
)

if can_trade:
    print("✅ OK to trade")
else:
    print(f"⛔ Cannot trade: {reason}")

# Record a trade
enforcer.record_trade(pnl=1250)

# Get daily summary
summary = enforcer.get_daily_summary()
print(f"Trades today: {summary['trades_taken']}/{summary['trades_remaining']}")
print(f"Consecutive wins: {summary['consecutive_wins']}")
print(f"Daily P&L: ₹{summary['daily_pnl']}")

# Print all rules
enforcer.print_rules_summary()

# Get trading status
status = enforcer.get_trading_status()
print(status)
```

---

## 5. Drawdown Management

Protect capital during losing periods:

```python
from risk import DrawdownManager

# Initialize
dd_manager = DrawdownManager(
    initial_capital=100000,
    max_dd_threshold=15.0
)

# Update with current capital
status = dd_manager.update(current_capital=95000)

print(f"Drawdown: {status['drawdown_pct']:.2f}%")
print(f"Severity: {status['severity']}")
print(f"Action: {status['recommended_action']}")

# Check if trading allowed
can_trade, reason = dd_manager.can_trade()

# Get position size multiplier
multiplier = dd_manager.get_position_size_multiplier()
print(f"Position size: {multiplier*100}%")

# Get recovery plan
recovery = dd_manager.get_recovery_plan()
print("Recovery Plan:")
for rec in recovery['recommendations']:
    print(f"  - {rec}")

# Print status
dd_manager.print_status()
```

---

## 6. Terminal Dashboard

Professional trading UI:

```python
from ui import TerminalDashboard

# Initialize dashboard
dashboard = TerminalDashboard()

# Print banner
dashboard.print_banner()

# Set account data
dashboard.set_account_data(
    capital=100000,
    daily_pnl=2500,
    portfolio_heat=3.5,
    trades_today=3,
    max_trades=5
)

# Set positions
dashboard.set_positions([
    {
        'instrument': 'NIFTY 24000 CE',
        'type': 'LONG',
        'quantity': 50,
        'entry_price': 250,
        'ltp': 275,
        'pnl': 1250
    }
])

# Set signals
dashboard.set_signals([
    {
        'instrument': 'NIFTY',
        'signal': 'STRONG_BUY',
        'strength': 8,
        'price': 23950
    }
])

# Set performance
dashboard.set_performance({
    'win_rate': 65.5,
    'profit_factor': 1.85,
    'sharpe_ratio': 1.42,
    'max_drawdown': 4.2
})

# Set market regime
dashboard.set_market_regime("STRONG_UPTREND")

# Add alerts
dashboard.add_alert("NIFTY showing strong momentum", "INFO")
dashboard.add_alert("Portfolio heat approaching 4%", "WARNING")

# Render dashboard
dashboard.render()

# Or render with live updates
def update_data():
    # Fetch latest data and update dashboard
    pass

dashboard.render_live(update_data, interval=1)
```

---

## Complete Example: Full Trading Session

```python
from analytics import TradeJournal, PerformanceMetrics
from news import EconomicCalendar
from strategies import DirectionalStrategies
from rules import TradingRulesEnforcer
from risk import DrawdownManager
from ui import TerminalDashboard

# Initialize components
journal = TradeJournal()
calendar = EconomicCalendar()
strategies = DirectionalStrategies()
rules = TradingRulesEnforcer()
dd_manager = DrawdownManager(initial_capital=100000)
dashboard = TerminalDashboard()

# Setup dashboard
dashboard.print_banner()

# Check economic calendar
upcoming_events = calendar.get_upcoming_events(days=1)
if not upcoming_events.empty:
    dashboard.add_alert(f"⚠️ {len(upcoming_events)} events today", "WARNING")

# Check if trading allowed
can_trade, reason = rules.can_trade()

if not can_trade:
    dashboard.add_alert(f"Trading blocked: {reason}", "ERROR")
    exit()

# Check drawdown
dd_status = dd_manager.update(100000)
multiplier = dd_manager.get_position_size_multiplier()

if multiplier < 1.0:
    dashboard.add_alert(
        f"Reduce position size to {multiplier*100}% (DD: {dd_status['drawdown_pct']:.1f}%)",
        "WARNING"
    )

# Get signals
signal = strategies.supertrend_strategy(market_data)

if signal['signal'] == 'BUY':
    dashboard.add_alert(f"Buy signal: {signal['reason']}", "INFO")

    # Record trade (if executed)
    trade_id = journal.record_trade_entry(
        instrument="NIFTY 24000 CE",
        direction="LONG",
        entry_price=250,
        quantity=int(50 * multiplier),  # Adjusted for DD
        strategy="Supertrend",
        entry_reason=signal['reason']
    )

# Update dashboard
dashboard.set_account_data(
    capital=100000,
    daily_pnl=rules.daily_stats['daily_pnl'],
    portfolio_heat=3.5,
    trades_today=rules.daily_stats['trades_count'],
    max_trades=5
)

dashboard.render()
```

---

## Configuration

All features are configurable via `config.yaml`:

```yaml
# Trading Rules
trading_rules:
  max_trades_per_day: 5
  max_consecutive_losses: 3
  max_daily_loss: 5000

# Drawdown Management
drawdown:
  max_acceptable_dd: 15.0
  caution_level: 5.0

# Analytics
analytics:
  trade_journal_db: "data/trade_journal.db"
  enable_visualizations: true

# News
news:
  enable_economic_calendar: true
  pre_event_warning_hours: 24

# Dashboard
dashboard:
  enable_terminal_ui: true
  refresh_interval_seconds: 1
```

---

## Best Practices

1. **Always check rules before trading**
   ```python
   can_trade, reason = rules.can_trade()
   if not can_trade:
       return  # Don't trade
   ```

2. **Record every trade**
   ```python
   trade_id = journal.record_trade_entry(...)
   # ... execute trade ...
   journal.record_trade_exit(trade_id, ...)
   ```

3. **Monitor drawdown continuously**
   ```python
   dd_status = dd_manager.update(current_capital)
   multiplier = dd_manager.get_position_size_multiplier()
   # Adjust position size
   ```

4. **Use dashboard for overview**
   ```python
   dashboard.render()  # Before trading session
   ```

5. **Review performance regularly**
   ```python
   metrics = PerformanceMetrics(journal.get_all_trades())
   metrics.print_report()
   ```

---

## Troubleshooting

### Issue: "Database locked" error
**Solution:** Close all connections
```python
journal.close()
```

### Issue: Charts not displaying
**Solution:** Install plotly and open HTML files
```bash
pip install plotly
```

### Issue: Terminal dashboard looks broken
**Solution:** Install Rich library and use proper terminal
```bash
pip install rich
```

---

## Next Steps

1. ✅ Paper trade for 2-4 weeks
2. ✅ Analyze performance metrics weekly
3. ✅ Refine strategies based on data
4. ✅ Test all edge cases
5. ✅ Start live trading with small capital

---

*For more details, see PHASE34_CRITICAL_REVIEW.md*
