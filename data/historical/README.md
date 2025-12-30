# Historical Data Documentation

This directory contains downloaded historical market data used for backtesting and analysis.

## Data Sources

### Primary Source: Upstox API
- **Provider**: Upstox (broker API)
- **Data Types**: OHLCV candles, option chain snapshots
- **Rate Limit**: 250 requests/minute
- **Update Frequency**: On-demand via bootstrap script or scheduled jobs

### Data Limitations

| Data Type | Available Range | Limitations |
|-----------|----------------|-------------|
| Intraday (1min, 5min, 15min) | ~6 months | API limits historical intraday data |
| Daily candles | ~2 years | More history available |
| Weekly/Monthly candles | ~5 years | Longer history possible |
| Option chains | Current day only | Historical options must be built daily |
| IV history | Built from option chain snapshots | Requires daily collection |

## Directory Structure

```
data/historical/
├── indices/
│   ├── NSE_INDEX_Nifty_50/
│   │   ├── 1minute/
│   │   ├── 15minute/
│   │   └── day/
│   ├── NSE_INDEX_Nifty_Bank/
│   └── NSE_INDEX_India_VIX/
├── equities/
│   └── NSE_EQ_RELIANCE/
│       └── day/
├── options/
│   ├── snapshots/
│   │   └── YYYY-MM-DD/
│   │       └── underlying_expiry.parquet
│   └── iv_history/
│       └── underlying.parquet
└── README.md (this file)
```

## File Format

All data is stored in **Apache Parquet** format for:
- Efficient compression (typically 50-80% smaller than CSV)
- Fast read performance (columnar format)
- Schema validation
- Type preservation (timestamps, floats, integers)

### OHLCV Schema

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime64[ns] | Candle timestamp (IST) |
| open | float64 | Opening price |
| high | float64 | High price |
| low | float64 | Low price |
| close | float64 | Closing price |
| volume | int64 | Trading volume |
| open_interest | int64 | Open interest (futures/options) |

### Option Chain Schema

| Column | Type | Description |
|--------|------|-------------|
| snapshot_timestamp | datetime64[ns] | Time of snapshot |
| underlying_symbol | string | NIFTY50, BANKNIFTY, etc. |
| underlying_spot | float64 | Spot price at snapshot |
| expiry_date | date | Option expiry date |
| strike_price | float64 | Strike price |
| option_type | string | CE (Call) or PE (Put) |
| ltp | float64 | Last traded price |
| bid_price | float64 | Best bid price |
| bid_qty | int64 | Bid quantity |
| ask_price | float64 | Best ask price |
| ask_qty | int64 | Ask quantity |
| open_interest | int64 | Open interest |
| oi_change | int64 | OI change from previous day |
| volume | int64 | Trading volume |
| iv | float64 | Implied volatility |
| delta | float64 | Option delta |
| gamma | float64 | Option gamma |
| theta | float64 | Option theta |
| vega | float64 | Option vega |

## Usage

### Downloading Data

Use the bootstrap script to download initial data:

```bash
# Download index data (Nifty, BankNifty)
python scripts/bootstrap_data.py --indices --days 365

# Download F&O stocks
python scripts/bootstrap_data.py --stocks --days 365

# Download option chain snapshots (current day)
python scripts/bootstrap_data.py --options

# Download all data types
python scripts/bootstrap_data.py --all --days 365

# Dry run (show what would be downloaded)
python scripts/bootstrap_data.py --all --dry-run
```

### Accessing Data

Use the `DataRetrievalService` for programmatic access:

```python
from data.services import DataRetrievalService
from datetime import date

service = DataRetrievalService()

# Get historical OHLCV data
df = service.get_historical_data(
    instrument='NSE_INDEX|Nifty 50',
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
    interval='15minute'
)

# Get option chain snapshot
chain = service.get_option_chain_snapshot(
    underlying='NSE_INDEX|Nifty 50',
    expiry=date(2025, 1, 2),
    snapshot_date=date(2024, 12, 30)
)

# Get IV metrics
iv_metrics = service.get_iv_metrics('NSE_INDEX|Nifty 50')
print(f"IV Rank: {iv_metrics['iv_rank']:.1f}%")
print(f"IV Percentile: {iv_metrics['iv_percentile']:.1f}%")
```

### Data Validation

The service includes built-in validation:

```python
# Validate downloaded data
report = service.validate_data(df, data_type='ohlcv')
print(f"Valid: {report['is_valid']}")
print(f"Rows: {report['row_count']}")
print(f"Issues: {report['issues']}")
```

## Building Historical Option Chain Data

Option chain data is only available for the current day via API. To build historical data:

1. **Set up daily job** to run the bootstrap script:
   ```bash
   # Add to crontab (runs at 3:35 PM after market close)
   35 15 * * 1-5 cd /path/to/TradeFlow-v2 && python scripts/bootstrap_data.py --options
   ```

2. **Accumulated data** will be stored by date in `options/snapshots/`

3. **IV history** is automatically calculated from accumulated snapshots

## Known Issues and Gaps

### Data Gaps
- Market holidays will have no data
- API outages may cause missing days
- Use `detect_gaps()` method to identify missing data

### Data Quality
- Very early morning or late evening candles may have low volume
- Option Greeks from API may differ from calculated values
- IV for deep OTM options may be unreliable

### Storage Considerations
- Intraday data grows quickly (~50MB/month for Nifty 15min)
- Consider archiving old intraday data after 6 months
- Daily data is compact and can be retained longer

## Alternative Data Sources

For data beyond API limits, consider:

1. **NSE Bhav Copies** (free, official)
   - Daily EOD data: https://www.nseindia.com/all-reports
   - Historical data available for years

2. **Yahoo Finance** (free, unofficial)
   - Index data with long history
   - May have adjusted prices

3. **Commercial Providers**
   - NSE's official data feed (paid)
   - Third-party data vendors

## Maintenance

### Regular Tasks
- [ ] Run bootstrap script daily after market close
- [ ] Check for data gaps weekly
- [ ] Archive old intraday data monthly
- [ ] Validate data integrity quarterly

### Troubleshooting

**Missing Data**:
```python
# Check for gaps
gaps = service.detect_gaps(df, expected_interval_minutes=15)
for gap in gaps:
    print(f"Gap from {gap['from']} to {gap['to']}")
```

**Corrupt Files**:
```python
# Validate specific file
report = service.validate_data(df, data_type='ohlcv')
if not report['is_valid']:
    print(f"Issues: {report['issues']}")
```

---

*Last Updated: December 30, 2025*
