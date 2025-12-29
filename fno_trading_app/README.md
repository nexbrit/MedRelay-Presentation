# F&O Trading Application

A comprehensive Python-based F&O (Futures & Options) trading platform featuring live signal generation, Upstox API integration, and data-driven screeners using pandas.

## Features

### 1. Live Trading Signal Generator
- **Multi-Indicator Analysis**: RSI, MACD, EMA, Bollinger Bands, Supertrend, ADX, Stochastic
- **Combined Signal System**: Aggregates multiple indicators for stronger signals
- **Signal Strength Scoring**: Weighted scoring system for signal reliability
- **Real-time Monitoring**: Continuous market monitoring with configurable intervals

### 2. Upstox API Integration
- **Market Data**: Real-time quotes, historical data, option chains
- **Order Management**: Place, modify, cancel orders
- **Portfolio Tracking**: Monitor positions and holdings
- **OAuth Authentication**: Secure API access
- **Sandbox Mode**: Test strategies without real money

### 3. Data-Driven Screeners (Pandas)
- **Volume Screeners**: Filter by volume and volume surges
- **Price Action**: Identify bullish/bearish patterns (engulfing, hammer, shooting star)
- **Momentum Screeners**: Find high momentum stocks
- **Breakout Detection**: Identify breakout candidates
- **Option Strategies**: PCR analysis, high OI strikes, ATM/ITM/OTM filtering
- **Volatility Filters**: Screen by ATR percentage
- **Custom Filters**: Extensible filter system

### 4. Platform Effectiveness Features

Based on research, the platform includes:
- **Real-time Data Processing**: Fast pandas-based data manipulation
- **Configurable Parameters**: YAML-based configuration for easy customization
- **Modular Architecture**: Separate modules for signals, screeners, and API
- **Comprehensive Logging**: Track all operations and signals
- **Risk Management**: Position sizing, stop-loss, take-profit configuration
- **Backtesting Ready**: Historical data support for strategy testing

## Installation

### Prerequisites
- Python 3.8 or higher
- Upstox Developer Account ([Register here](https://upstox.com/developer/))

### Setup

1. **Clone the repository**
```bash
cd fno_trading_app
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure credentials**
```bash
cp .env.example .env
# Edit .env and add your Upstox API credentials
```

4. **Configure settings**
Edit `config/config.yaml` to customize:
- Trading instruments
- Indicator parameters
- Risk management settings
- Screener criteria

## Quick Start

### Basic Usage

```python
from fno_trading_app import FNOTradingApp

# Initialize the application
app = FNOTradingApp()

# Setup authentication (first time)
app.setup_authentication()
# Follow the authorization URL, then set your access token
app.setup_authentication(access_token='your_access_token_here')

# Analyze an instrument
analysis = app.analyze_instrument('NSE_INDEX|Nifty 50')
print(f"Signal: {analysis['latest_signal']['signal']}")

# Run live monitoring
instruments = ['NSE_INDEX|Nifty 50', 'NSE_INDEX|Nifty Bank']
app.live_monitoring(instruments, interval_seconds=300)
```

### Signal Generation Example

```python
from fno_trading_app import SignalGenerator
import pandas as pd

# Create sample data or fetch from Upstox
df = pd.DataFrame({
    'timestamp': [...],
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})

# Generate signals
signal_gen = SignalGenerator()
df_with_signals = signal_gen.generate_combined_signal(df)

# Get latest signal
latest = signal_gen.get_latest_signal(df_with_signals)
print(f"Signal: {latest['signal']}, Strength: {latest['strength']}")
```

### Screener Example

```python
from fno_trading_app import FNOScreener
import pandas as pd

# Initialize screener
screener = FNOScreener(config={
    'min_volume': 100000,
    'volume_surge_factor': 2.0,
    'min_price': 100,
    'max_price': 5000
})

# Apply multiple filters
screened = screener.multi_criteria_screen(
    market_data,
    filters=['volume', 'price', 'momentum', 'breakout']
)

# Get top opportunities
top_picks = screener.get_top_opportunities(
    screened,
    sort_by='momentum_score',
    top_n=10
)
```

### Option Chain Analysis

```python
# Analyze option chain
option_analysis = app.get_option_chain_analysis(
    underlying='NSE_INDEX|Nifty 50',
    expiry_date='2025-01-30'
)
```

## Architecture

```
fno_trading_app/
├── api/                    # Upstox API integration
│   ├── __init__.py
│   └── upstox_client.py   # API wrapper with all endpoints
├── signals/               # Signal generation
│   ├── __init__.py
│   ├── indicators.py      # Technical indicators
│   └── signal_generator.py # Signal logic
├── screeners/             # Screening tools
│   ├── __init__.py
│   └── fno_screener.py    # Pandas-based screeners
├── utils/                 # Utilities
│   ├── __init__.py
│   ├── config_loader.py   # Configuration management
│   └── logger.py          # Logging setup
├── config/                # Configuration files
│   └── config.yaml        # Main configuration
├── data/                  # Data storage (created at runtime)
├── logs/                  # Log files (created at runtime)
├── tests/                 # Unit tests
├── main.py               # Main application
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Configuration

### config.yaml Structure

```yaml
upstox:
  sandbox_mode: true  # Set to false for live trading

trading:
  instruments:
    - "NIFTY"
    - "BANKNIFTY"

  signals:
    rsi:
      period: 14
      overbought: 70
      oversold: 30
    # ... more indicators

  risk:
    max_position_size: 100000
    stop_loss_percentage: 2.0
    take_profit_percentage: 4.0

screener:
  min_volume: 100000
  min_price: 10
  # ... more filters
```

## Technical Indicators

| Indicator | Description | Signal Generation |
|-----------|-------------|-------------------|
| **RSI** | Relative Strength Index | Overbought (>70), Oversold (<30) |
| **MACD** | Moving Average Convergence Divergence | Bullish/Bearish crossovers |
| **EMA** | Exponential Moving Average | Golden/Death cross |
| **Bollinger Bands** | Volatility bands | Price touching upper/lower bands |
| **Supertrend** | Trend following | Trend direction changes |
| **ADX** | Average Directional Index | Trend strength |
| **Stochastic** | Momentum oscillator | Overbought/Oversold |

## Screener Capabilities

### Available Filters
1. **Volume Screeners**
   - Minimum volume threshold
   - Volume surge detection

2. **Price Filters**
   - Price range filtering
   - Price action patterns

3. **Momentum Filters**
   - Multi-timeframe returns
   - Momentum scoring

4. **Breakout Detection**
   - Support/Resistance levels
   - Breakout and near-breakout identification

5. **Option Screeners**
   - ATM/ITM/OTM filtering
   - High OI strike identification
   - PCR (Put-Call Ratio) analysis

## API Reference

### FNOTradingApp

Main application class for trading operations.

**Methods:**
- `setup_authentication(access_token)` - Configure API authentication
- `analyze_instrument(instrument_key, interval, days_back)` - Analyze and generate signals
- `run_screener(market_data, filters)` - Run screening filters
- `live_monitoring(instruments, interval_seconds)` - Monitor instruments in real-time
- `get_option_chain_analysis(underlying, expiry_date)` - Analyze option chain

### SignalGenerator

Generate trading signals from technical indicators.

**Methods:**
- `generate_rsi_signal(df)` - RSI-based signals
- `generate_macd_signal(df)` - MACD-based signals
- `generate_ema_signal(df)` - EMA crossover signals
- `generate_combined_signal(df)` - Multi-indicator combined signals
- `get_latest_signal(df)` - Get latest signal with details

### FNOScreener

Data-driven screeners for finding trading opportunities.

**Methods:**
- `screen_by_volume(df)` - Filter by volume criteria
- `screen_by_price(df)` - Filter by price range
- `screen_by_volatility(df)` - Filter by volatility
- `screen_breakout_candidates(df)` - Find breakout opportunities
- `screen_momentum_stocks(df)` - Find high momentum stocks
- `screen_option_strategies(df, spot_price)` - Option strategy screening
- `multi_criteria_screen(df, filters)` - Apply multiple filters
- `get_top_opportunities(df, sort_by, top_n)` - Get top N opportunities

## Making the Platform More Effective

### Research-Based Recommendations

Based on industry research, here are ways to enhance the platform:

1. **Machine Learning Integration**
   - Implement LSTM/GRU models for signal prediction
   - Use ML for parameter optimization
   - Ensemble methods for combining signals

2. **Advanced Risk Management**
   - Position sizing based on volatility
   - Kelly Criterion for optimal bet sizing
   - Portfolio-level risk metrics

3. **Backtesting Framework**
   - Historical strategy testing
   - Walk-forward analysis
   - Monte Carlo simulation

4. **Real-time Features**
   - WebSocket integration for tick-by-tick data
   - Order book analysis
   - Market depth visualization

5. **Performance Analytics**
   - Sharpe ratio, Sortino ratio calculations
   - Maximum drawdown tracking
   - Win/loss ratio analysis

6. **Alert System**
   - SMS/Email notifications
   - Webhook integration
   - Telegram bot integration

7. **Database Integration**
   - Store historical signals
   - Performance tracking database
   - Trade journal

8. **UI/Dashboard**
   - Web-based dashboard (Flask/Django)
   - Interactive charts (Plotly/TradingView)
   - Mobile app integration

## Testing

Run unit tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=fno_trading_app tests/
```

## Roadmap

- [ ] WebSocket support for real-time data
- [ ] Machine learning signal optimization
- [ ] Backtesting engine
- [ ] Web dashboard
- [ ] Mobile app
- [ ] Advanced order types (trailing stop, bracket orders)
- [ ] Multi-broker support
- [ ] Social trading features

## Disclaimer

This software is for educational purposes only. Trading in F&O involves substantial risk of loss. Always:
- Test strategies in sandbox mode first
- Use proper risk management
- Never invest more than you can afford to lose
- Consult with financial advisors
- Understand all risks before trading

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation
- Review example code

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## References

- [Upstox API Documentation](https://upstox.com/developer/api-documentation/)
- [Upstox Python SDK](https://github.com/upstox/upstox-python)
- [Technical Analysis with Pandas](https://pandas.pydata.org/)

---

**Built with ❤️ for F&O traders**
