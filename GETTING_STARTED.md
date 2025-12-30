# TradeFlow v2 - Getting Started Guide

## Project Successfully Restructured! ✓

The project has been moved from `fno_trading_app/` to the root directory and rebranded as **TradeFlow v2**.

## Quick Start

### 1. Run the Main Application

```bash
python main.py
```

This will display:
- Application features
- Setup instructions
- Quick start examples

### 2. Run Example Scripts

Try the basic usage examples:

```bash
python examples/basic_usage.py
```

Or the live trading demo:

```bash
python examples/live_trading_demo.py
```

### 3. Use as a Library

```python
from main import FNOTradingApp

# Initialize the app
app = FNOTradingApp()

# Use the features
# - Signal generation
# - Market screening
# - Option chain analysis
```

## What's Working

✓ All dependencies installed (Python 3.14 compatible)
✓ Main application runs successfully
✓ All modules import correctly
✓ Example scripts available

## Configuration

The application uses `config/config.yaml` for configuration. You can customize:
- Trading instruments
- Technical indicator parameters
- Risk management settings
- Screener criteria

## Next Steps

### For Live Trading

1. **Get Upstox API Credentials**
   - Visit: https://upstox.com/developer/
   - Create an app and get API Key & Secret

2. **Setup Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your Upstox credentials
   ```

3. **Authenticate**
   ```python
   from main import FNOTradingApp
   app = FNOTradingApp()
   app.setup_authentication()
   # Follow the authorization URL
   ```

### For Testing/Development

The application works in demo mode without API credentials. You can:
- Test signal generation with sample data
- Use the screening functions
- Explore the codebase
- **Launch the Web Dashboard**: `python launch_dashboard.py`

## Project Structure

```
TradeFlow v2/
├── main.py                    # Main entry point
├── config/                    # Configuration files
├── api/                       # Upstox API integration
├── signals/                   # Signal generation (RSI, MACD, etc.)
├── screeners/                 # Market screeners
├── options/                   # Options analysis & Greeks
├── strategies/                # Trading strategies
├── risk/                      # Risk management
├── backtest/                  # Backtesting engine
├── analytics/                 # Performance analytics
├── examples/                  # Example scripts
└── tests/                     # Unit tests

```

## Features

1. **Signal Generation**: RSI, MACD, EMA, Bollinger Bands, Supertrend, ADX, Stochastic
2. **Market Screeners**: Volume, Price Action, Momentum, Breakouts
3. **Options Analysis**: Greeks calculation, Portfolio Greeks, Option Chain analysis
4. **Trading Strategies**: Directional strategies, Options strategies, Spread building
5. **Risk Management**: Position sizing, Drawdown management, Correlation analysis
6. **Backtesting**: Historical testing, Monte Carlo simulation
7. **Analytics**: Performance metrics, Trade journal, Visualizations
8. **Web Dashboard**: Streamlit-based interactive web interface with real-time monitoring

## Troubleshooting

### Issue: Module not found
**Solution**: Make sure you're running from the project root directory

### Issue: Import errors
**Solution**: All dependencies are installed. Try: `python -m pip install -r requirements.txt`

### Issue: Encoding errors (Windows)
**Solution**: Fixed! UTF-8 encoding is now properly configured

## Notes

- **ta-lib** and **pandas-ta** are commented out in requirements.txt (Python 3.14 compatibility issues)
- The application works without these libraries, but some advanced indicators may be unavailable
- All core functionality (signals, screening, API integration) is fully operational

## Need Help?

Check these files:
- `README.md` - Full documentation
- `SETUP_GUIDE.md` - Detailed setup instructions
- `QUICK_REFERENCE.md` - Quick reference guide
- `examples/` - Working code examples

---

**TradeFlow v2** - Professional F&O Trading Platform
