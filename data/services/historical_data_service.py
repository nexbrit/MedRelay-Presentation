"""
Historical Data Service for retrieving and managing historical market data.

Provides efficient access to historical OHLCV data with caching
and rate limiting.
"""

from datetime import datetime, timedelta, date
from typing import Any, Optional, List, Dict, Union
import logging
import pandas as pd

from data.cache.cache_manager import CacheManager
from data.services.market_data_service import RateLimiter

logger = logging.getLogger(__name__)


class HistoricalDataService:
    """
    Service for historical market data retrieval.

    Features:
    - Historical OHLCV data for indices and stocks
    - Automatic caching with configurable TTL
    - Rate limiting to respect API limits
    - Multiple timeframe support (1min, 15min, 30min, day)
    - Data validation and gap detection

    Example:
        service = HistoricalDataService(upstox_client)
        df = service.get_historical_data(
            'NSE_INDEX|Nifty 50',
            start_date='2025-01-01',
            end_date='2025-01-30',
            interval='15minute'
        )
    """

    # Supported intervals
    VALID_INTERVALS = ['1minute', '15minute', '30minute', 'day', 'week', 'month']

    # Cache TTL (in seconds)
    INTRADAY_TTL = 60  # 1 minute for intraday data
    DAILY_TTL = 3600  # 1 hour for daily data
    HISTORICAL_TTL = 86400  # 24 hours for historical data

    def __init__(
        self,
        upstox_client,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize historical data service.

        Args:
            upstox_client: UpstoxClient instance for API calls
            cache_manager: Optional custom cache manager
            rate_limiter: Optional custom rate limiter
        """
        self._client = upstox_client
        self._cache = cache_manager or CacheManager()
        self._rate_limiter = rate_limiter or RateLimiter()

    def get_historical_data(
        self,
        instrument_key: str,
        start_date: Union[str, date, datetime] = None,
        end_date: Union[str, date, datetime] = None,
        interval: str = 'day',
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for an instrument.

        Args:
            instrument_key: Instrument key (e.g., 'NSE_INDEX|Nifty 50')
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            interval: Candle interval (1minute, 15minute, 30minute, day)
            use_cache: Whether to use cache

        Returns:
            DataFrame with OHLCV data (timestamp, open, high, low, close, volume, oi)
        """
        # Validate interval
        if interval not in self.VALID_INTERVALS:
            raise ValueError(
                f"Invalid interval '{interval}'. "
                f"Valid intervals: {self.VALID_INTERVALS}"
            )

        # Parse dates
        end_date = self._parse_date(end_date) or datetime.now().date()
        start_date = self._parse_date(start_date) or (
            end_date - timedelta(days=30)
        )

        # Convert to date objects if datetime
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        # Generate cache key
        cache_key = (
            f"historical:{instrument_key}:{start_date}:{end_date}:{interval}"
        )

        # Check cache
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return pd.DataFrame(cached)

        # Rate limit check
        if not self._rate_limiter.acquire():
            logger.warning(f"Rate limit hit for historical data {instrument_key}")
            cached = self._cache.get(cache_key)
            return pd.DataFrame(cached) if cached else pd.DataFrame()

        try:
            # Calculate days for API call
            days_back = (end_date - start_date).days + 1

            # Fetch from API
            df = self._client.get_historical_data(
                instrument_key=instrument_key,
                interval=interval,
                days_back=days_back
            )

            if df.empty:
                logger.warning(f"No data returned for {instrument_key}")
                return df

            # Ensure proper columns
            df = self._standardize_dataframe(df)

            # Filter to requested date range
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            df = df.drop(columns=['date'])

            # Cache the result
            ttl = self._get_cache_ttl(interval)
            self._cache.set(cache_key, df.to_dict('records'), ttl)

            logger.info(
                f"Fetched {len(df)} candles for {instrument_key} "
                f"({start_date} to {end_date}, {interval})"
            )

            return df

        except Exception as e:
            logger.error(f"Error fetching historical data for {instrument_key}: {e}")
            # Try to return cached data even if expired
            cached = self._cache.get(cache_key)
            return pd.DataFrame(cached) if cached else pd.DataFrame()

    def get_intraday_data(
        self,
        instrument_key: str,
        interval: str = '15minute',
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get intraday data for today's session.

        Args:
            instrument_key: Instrument key
            interval: Candle interval (1minute, 15minute, 30minute)
            use_cache: Whether to use cache

        Returns:
            DataFrame with today's OHLCV data
        """
        today = datetime.now().date()

        return self.get_historical_data(
            instrument_key=instrument_key,
            start_date=today,
            end_date=today,
            interval=interval,
            use_cache=use_cache
        )

    def get_daily_data(
        self,
        instrument_key: str,
        days: int = 365,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get daily OHLCV data for the specified number of days.

        Args:
            instrument_key: Instrument key
            days: Number of days of data
            use_cache: Whether to use cache

        Returns:
            DataFrame with daily OHLCV data
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        return self.get_historical_data(
            instrument_key=instrument_key,
            start_date=start_date,
            end_date=end_date,
            interval='day',
            use_cache=use_cache
        )

    def get_ohlc_for_dates(
        self,
        instrument_key: str,
        dates: List[Union[str, date, datetime]]
    ) -> pd.DataFrame:
        """
        Get OHLC data for specific dates.

        Args:
            instrument_key: Instrument key
            dates: List of dates to retrieve

        Returns:
            DataFrame with OHLCV data for specified dates
        """
        if not dates:
            return pd.DataFrame()

        parsed_dates = [self._parse_date(d) for d in dates]
        min_date = min(parsed_dates)
        max_date = max(parsed_dates)

        # Get data for date range
        df = self.get_historical_data(
            instrument_key=instrument_key,
            start_date=min_date,
            end_date=max_date,
            interval='day'
        )

        if df.empty:
            return df

        # Filter to requested dates
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        df = df[df['date'].isin(parsed_dates)]
        df = df.drop(columns=['date'])

        return df

    def get_latest_candle(
        self,
        instrument_key: str,
        interval: str = 'day'
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent candle for an instrument.

        Args:
            instrument_key: Instrument key
            interval: Candle interval

        Returns:
            Dictionary with latest candle data or None
        """
        df = self.get_historical_data(
            instrument_key=instrument_key,
            start_date=datetime.now().date() - timedelta(days=5),
            end_date=datetime.now().date(),
            interval=interval
        )

        if df.empty:
            return None

        return df.iloc[-1].to_dict()

    def calculate_returns(
        self,
        instrument_key: str,
        period_days: int = 252
    ) -> Dict[str, float]:
        """
        Calculate various return metrics for an instrument.

        Args:
            instrument_key: Instrument key
            period_days: Number of trading days

        Returns:
            Dictionary with return metrics
        """
        df = self.get_daily_data(instrument_key, days=period_days + 30)

        if df.empty or len(df) < 2:
            return {
                'daily_return': 0,
                'weekly_return': 0,
                'monthly_return': 0,
                'yearly_return': 0,
                'total_return': 0
            }

        df = df.sort_values('timestamp')

        # Get closing prices
        latest_close = df.iloc[-1]['close']
        prev_close = df.iloc[-2]['close'] if len(df) > 1 else latest_close

        # Calculate returns
        daily_return = ((latest_close - prev_close) / prev_close * 100) if prev_close else 0

        weekly_close = df.iloc[-5]['close'] if len(df) >= 5 else df.iloc[0]['close']
        weekly_return = ((latest_close - weekly_close) / weekly_close * 100) if weekly_close else 0

        monthly_close = df.iloc[-22]['close'] if len(df) >= 22 else df.iloc[0]['close']
        monthly_return = ((latest_close - monthly_close) / monthly_close * 100) if monthly_close else 0

        first_close = df.iloc[0]['close']
        yearly_return = ((latest_close - first_close) / first_close * 100) if first_close else 0

        return {
            'daily_return': round(daily_return, 2),
            'weekly_return': round(weekly_return, 2),
            'monthly_return': round(monthly_return, 2),
            'yearly_return': round(yearly_return, 2),
            'total_return': round(yearly_return, 2),
            'period_days': len(df)
        }

    def calculate_volatility(
        self,
        instrument_key: str,
        period_days: int = 30,
        annualize: bool = True
    ) -> Dict[str, float]:
        """
        Calculate historical volatility.

        Args:
            instrument_key: Instrument key
            period_days: Number of days for calculation
            annualize: Whether to annualize the volatility

        Returns:
            Dictionary with volatility metrics
        """
        import numpy as np

        df = self.get_daily_data(instrument_key, days=period_days + 10)

        if df.empty or len(df) < 5:
            return {
                'volatility': 0,
                'annualized_volatility': 0,
                'avg_daily_range': 0
            }

        df = df.sort_values('timestamp')

        # Calculate daily returns
        df['return'] = df['close'].pct_change()

        # Calculate volatility (standard deviation of returns)
        daily_vol = df['return'].std()

        # Annualize (252 trading days)
        annualized_vol = daily_vol * np.sqrt(252) if annualize else daily_vol

        # Calculate average daily range
        df['daily_range'] = (df['high'] - df['low']) / df['close'] * 100
        avg_range = df['daily_range'].mean()

        return {
            'volatility': round(daily_vol * 100, 2),
            'annualized_volatility': round(annualized_vol * 100, 2),
            'avg_daily_range': round(avg_range, 2),
            'period_days': len(df) - 1
        }

    def detect_gaps(
        self,
        instrument_key: str,
        start_date: Union[str, date, datetime] = None,
        end_date: Union[str, date, datetime] = None,
        interval: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Detect gaps in historical data.

        Args:
            instrument_key: Instrument key
            start_date: Start date
            end_date: End date
            interval: Candle interval

        Returns:
            List of detected gaps
        """
        df = self.get_historical_data(
            instrument_key=instrument_key,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        if df.empty or len(df) < 2:
            return []

        df = df.sort_values('timestamp')
        gaps = []

        # Determine max gap between candles (accounting for market hours/weekends)
        if interval == 'day':
            max_gap = timedelta(days=3)  # Account for weekends
        elif interval == '15minute':
            max_gap = timedelta(hours=18)  # Account for market close
        else:
            max_gap = timedelta(hours=18)

        for i in range(1, len(df)):
            prev_time = pd.to_datetime(df.iloc[i-1]['timestamp'])
            curr_time = pd.to_datetime(df.iloc[i]['timestamp'])
            gap = curr_time - prev_time

            if gap > max_gap:
                gaps.append({
                    'from': prev_time.isoformat(),
                    'to': curr_time.isoformat(),
                    'gap_duration': str(gap),
                    'gap_days': gap.days
                })

        return gaps

    def validate_data(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Validate OHLCV data for common issues.

        Args:
            df: DataFrame to validate

        Returns:
            Dictionary with validation results
        """
        if df.empty:
            return {
                'valid': False,
                'issues': ['Empty DataFrame'],
                'rows': 0
            }

        issues = []

        # Check required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")

        # Check for null values
        null_counts = df[required_cols].isnull().sum()
        null_cols = null_counts[null_counts > 0]
        if not null_cols.empty:
            issues.append(f"Null values: {null_cols.to_dict()}")

        # Check OHLC relationships
        if all(c in df.columns for c in ['open', 'high', 'low', 'close']):
            # High should be >= Open, Close, Low
            invalid_high = len(df[
                (df['high'] < df['open']) |
                (df['high'] < df['close']) |
                (df['high'] < df['low'])
            ])
            if invalid_high > 0:
                issues.append(f"Invalid high values: {invalid_high} rows")

            # Low should be <= Open, Close, High
            invalid_low = len(df[
                (df['low'] > df['open']) |
                (df['low'] > df['close']) |
                (df['low'] > df['high'])
            ])
            if invalid_low > 0:
                issues.append(f"Invalid low values: {invalid_low} rows")

        # Check for duplicates
        if 'timestamp' in df.columns:
            duplicates = df['timestamp'].duplicated().sum()
            if duplicates > 0:
                issues.append(f"Duplicate timestamps: {duplicates}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'rows': len(df),
            'date_range': {
                'start': str(df['timestamp'].min()) if 'timestamp' in df.columns else None,
                'end': str(df['timestamp'].max()) if 'timestamp' in df.columns else None
            }
        }

    def _parse_date(
        self,
        date_input: Union[str, date, datetime, None]
    ) -> Optional[date]:
        """Parse various date formats to date object."""
        if date_input is None:
            return None

        if isinstance(date_input, datetime):
            return date_input.date()

        if isinstance(date_input, date):
            return date_input

        if isinstance(date_input, str):
            try:
                return datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.fromisoformat(date_input).date()
                except ValueError:
                    logger.error(f"Invalid date format: {date_input}")
                    return None

        return None

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize DataFrame column names and types."""
        # Ensure standard column names
        column_mapping = {
            'time': 'timestamp',
            'date': 'timestamp',
            'datetime': 'timestamp',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            'vol': 'volume'
        }

        df = df.rename(columns={
            k: v for k, v in column_mapping.items()
            if k in df.columns
        })

        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Sort by timestamp
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp').reset_index(drop=True)

        return df

    def _get_cache_ttl(self, interval: str) -> int:
        """Get appropriate cache TTL based on interval."""
        if interval in ['1minute', '15minute', '30minute']:
            return self.INTRADAY_TTL
        elif interval == 'day':
            return self.DAILY_TTL
        else:
            return self.HISTORICAL_TTL
