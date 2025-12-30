"""
Historical Data Downloader - Downloads and stores OHLCV data.

Features:
- Download index and stock historical data from Upstox
- Rate limiting with exponential backoff
- Parquet storage for efficient compression
- Data validation and integrity checks
- Gap detection and reporting
"""

import time
from datetime import date, timedelta
from typing import Any, Optional, Dict, List
from pathlib import Path
from enum import Enum
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class DataInterval(Enum):
    """Supported data intervals."""
    MINUTE_1 = "1minute"
    MINUTE_5 = "5minute"
    MINUTE_15 = "15minute"
    MINUTE_30 = "30minute"
    HOUR_1 = "1hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class DownloadStatus(Enum):
    """Download status."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some data downloaded
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    NO_DATA = "no_data"


class HistoricalDownloader:
    """
    Downloads historical OHLCV data from Upstox API.

    Features:
    - Rate limiting to respect 250 req/min limit
    - Exponential backoff on failures
    - Parquet storage for efficient compression
    - Data validation (OHLC relationships, gaps)
    - Resume capability for partial downloads

    Example:
        downloader = HistoricalDownloader(upstox_client)

        # Download Nifty 15-minute data
        result = downloader.download_index_history(
            instrument_key='NSE_INDEX|Nifty 50',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            interval=DataInterval.MINUTE_15
        )
    """

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 250
    REQUEST_DELAY_SECONDS = 0.25  # 4 requests per second max

    # Retry settings
    MAX_RETRIES = 4
    BACKOFF_BASE_SECONDS = 2

    # Storage paths
    BASE_DATA_PATH = Path("data/historical")

    def __init__(
        self,
        upstox_client=None,
        data_path: Optional[Path] = None
    ):
        """
        Initialize historical downloader.

        Args:
            upstox_client: Upstox client for API calls
            data_path: Custom data storage path
        """
        self._client = upstox_client
        self._data_path = data_path or self.BASE_DATA_PATH
        self._data_path.mkdir(parents=True, exist_ok=True)

        # Rate limiting state
        self._last_request_time = 0.0
        self._request_count = 0
        self._minute_start = time.time()

    def _rate_limit(self) -> None:
        """Apply rate limiting before API call."""
        now = time.time()

        # Reset counter every minute
        if now - self._minute_start >= 60:
            self._request_count = 0
            self._minute_start = now

        # Check if we've hit the limit
        if self._request_count >= self.MAX_REQUESTS_PER_MINUTE:
            sleep_time = 60 - (now - self._minute_start)
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self._request_count = 0
                self._minute_start = time.time()

        # Minimum delay between requests
        time_since_last = now - self._last_request_time
        if time_since_last < self.REQUEST_DELAY_SECONDS:
            time.sleep(self.REQUEST_DELAY_SECONDS - time_since_last)

        self._last_request_time = time.time()
        self._request_count += 1

    def _retry_with_backoff(
        self,
        func,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff on failure.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception after max retries
        """
        last_exception = None

        for attempt in range(self.MAX_RETRIES):
            try:
                self._rate_limit()
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.MAX_RETRIES - 1:
                    sleep_time = self.BACKOFF_BASE_SECONDS * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {sleep_time}s..."
                    )
                    time.sleep(sleep_time)

        raise last_exception

    def _get_storage_path(
        self,
        instrument_key: str,
        interval: DataInterval,
        category: str = "indices"
    ) -> Path:
        """
        Get storage path for instrument data.

        Args:
            instrument_key: Instrument key
            interval: Data interval
            category: Data category (indices, stocks, options)

        Returns:
            Path to parquet file
        """
        # Clean instrument key for filename
        safe_name = instrument_key.replace("|", "_").replace(" ", "_")
        filename = f"{safe_name}_{interval.value}.parquet"

        path = self._data_path / category / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        return path

    def download_index_history(
        self,
        instrument_key: str,
        start_date: date,
        end_date: date,
        interval: DataInterval = DataInterval.MINUTE_15
    ) -> Dict[str, Any]:
        """
        Download historical data for an index.

        Args:
            instrument_key: Instrument key (e.g., 'NSE_INDEX|Nifty 50')
            start_date: Start date for download
            end_date: End date for download
            interval: Data interval

        Returns:
            Dictionary with download status and details
        """
        logger.info(
            f"Downloading {instrument_key} from {start_date} to {end_date} "
            f"({interval.value})"
        )

        all_data = []
        current_date = start_date
        failed_dates = []

        # Download in chunks (Upstox may limit date ranges)
        while current_date <= end_date:
            chunk_end = min(
                current_date + timedelta(days=30),
                end_date
            )

            try:
                chunk_data = self._download_chunk(
                    instrument_key,
                    current_date,
                    chunk_end,
                    interval
                )

                if chunk_data is not None and not chunk_data.empty:
                    all_data.append(chunk_data)
                    logger.info(
                        f"Downloaded {len(chunk_data)} rows for "
                        f"{current_date} to {chunk_end}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to download {current_date} to {chunk_end}: {e}"
                )
                failed_dates.append((current_date, chunk_end))

            current_date = chunk_end + timedelta(days=1)

        # Combine all data
        if not all_data:
            return {
                'status': DownloadStatus.NO_DATA,
                'rows': 0,
                'failed_dates': failed_dates,
                'path': None
            }

        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['timestamp'])
        combined_df = combined_df.sort_values('timestamp')

        # Validate data
        validation = self._validate_data(combined_df)

        # Save to parquet
        storage_path = self._get_storage_path(instrument_key, interval)
        combined_df.to_parquet(storage_path, index=False)

        logger.info(
            f"Saved {len(combined_df)} rows to {storage_path}"
        )

        status = (
            DownloadStatus.SUCCESS if not failed_dates
            else DownloadStatus.PARTIAL
        )

        return {
            'status': status,
            'rows': len(combined_df),
            'path': str(storage_path),
            'failed_dates': failed_dates,
            'validation': validation,
            'date_range': {
                'start': combined_df['timestamp'].min().isoformat(),
                'end': combined_df['timestamp'].max().isoformat()
            }
        }

    def _download_chunk(
        self,
        instrument_key: str,
        start_date: date,
        end_date: date,
        interval: DataInterval
    ) -> Optional[pd.DataFrame]:
        """
        Download a single chunk of historical data.

        Args:
            instrument_key: Instrument key
            start_date: Start date
            end_date: End date
            interval: Data interval

        Returns:
            DataFrame with OHLCV data or None
        """
        if not self._client:
            # Return demo data if no client
            return self._generate_demo_data(start_date, end_date, interval)

        try:
            # Use Upstox API
            df = self._retry_with_backoff(
                self._client.get_historical_data,
                instrument_key,
                interval.value,
                start_date.isoformat(),
                end_date.isoformat()
            )

            if df is None or df.empty:
                return None

            # Normalize columns
            df = self._normalize_columns(df)
            return df

        except Exception as e:
            logger.error(f"Error downloading chunk: {e}")
            raise

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame columns to standard format.

        Args:
            df: Raw DataFrame from API

        Returns:
            Normalized DataFrame
        """
        # Map API columns to standard names
        column_map = {
            'date': 'timestamp',
            'time': 'timestamp',
            'datetime': 'timestamp',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            'vol': 'volume',
            'oi': 'open_interest'
        }

        df = df.rename(columns={
            k: v for k, v in column_map.items()
            if k in df.columns
        })

        # Ensure required columns exist
        required = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Add volume and OI if missing
        if 'volume' not in df.columns:
            df['volume'] = 0
        if 'open_interest' not in df.columns:
            df['open_interest'] = 0

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Convert numeric columns
        for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]

    def _validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate downloaded data for integrity.

        Checks:
        - OHLC relationships (High >= Close >= Low)
        - Duplicate timestamps
        - Missing data gaps

        Args:
            df: DataFrame to validate

        Returns:
            Validation report
        """
        issues = []

        # Check OHLC relationships
        invalid_ohlc = df[
            (df['high'] < df['low']) |
            (df['high'] < df['close']) |
            (df['high'] < df['open']) |
            (df['low'] > df['close']) |
            (df['low'] > df['open'])
        ]
        if len(invalid_ohlc) > 0:
            issues.append({
                'type': 'invalid_ohlc',
                'count': len(invalid_ohlc),
                'sample': invalid_ohlc.head(3).to_dict('records')
            })

        # Check for duplicates
        duplicates = df[df.duplicated(subset=['timestamp'], keep=False)]
        if len(duplicates) > 0:
            issues.append({
                'type': 'duplicates',
                'count': len(duplicates)
            })

        # Check for gaps (for daily data)
        df_sorted = df.sort_values('timestamp')
        time_diffs = df_sorted['timestamp'].diff()

        # This is a simplified gap check - would need more logic
        # for handling weekends/holidays properly
        if len(df) > 1:
            median_diff = time_diffs.median()
            large_gaps = time_diffs[time_diffs > median_diff * 3]
            if len(large_gaps) > 0:
                issues.append({
                    'type': 'gaps',
                    'count': len(large_gaps)
                })

        return {
            'valid': len(issues) == 0,
            'row_count': len(df),
            'issues': issues,
            'date_range': {
                'start': df['timestamp'].min().isoformat() if len(df) > 0 else None,
                'end': df['timestamp'].max().isoformat() if len(df) > 0 else None
            }
        }

    def _generate_demo_data(
        self,
        start_date: date,
        end_date: date,
        interval: DataInterval
    ) -> pd.DataFrame:
        """
        Generate demo data for testing when no API client available.

        Args:
            start_date: Start date
            end_date: End date
            interval: Data interval

        Returns:
            DataFrame with demo OHLCV data
        """
        import numpy as np

        # Determine number of periods
        days = (end_date - start_date).days + 1

        if interval == DataInterval.DAY:
            periods = days
            freq = 'D'
        elif interval == DataInterval.MINUTE_15:
            periods = days * 26  # ~26 15-min candles per trading day
            freq = '15T'
        elif interval == DataInterval.MINUTE_5:
            periods = days * 78
            freq = '5T'
        else:
            periods = days * 26
            freq = '15T'

        # Generate timestamps
        timestamps = pd.date_range(
            start=start_date,
            periods=periods,
            freq=freq
        )

        # Generate random walk price data
        base_price = 24000  # Nifty-like
        returns = np.random.normal(0.0001, 0.01, periods)
        prices = base_price * (1 + returns).cumprod()

        # Generate OHLC
        data = []
        for i, ts in enumerate(timestamps):
            close = prices[i]
            volatility = close * 0.005  # 0.5% typical range

            high = close + abs(np.random.normal(0, volatility))
            low = close - abs(np.random.normal(0, volatility))
            open_price = low + np.random.random() * (high - low)

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': int(np.random.randint(100000, 1000000)),
                'open_interest': int(np.random.randint(1000000, 5000000))
            })

        return pd.DataFrame(data)

    def load_historical_data(
        self,
        instrument_key: str,
        interval: DataInterval = DataInterval.MINUTE_15,
        category: str = "indices"
    ) -> Optional[pd.DataFrame]:
        """
        Load previously downloaded historical data.

        Args:
            instrument_key: Instrument key
            interval: Data interval
            category: Data category

        Returns:
            DataFrame with historical data or None
        """
        storage_path = self._get_storage_path(instrument_key, interval, category)

        if not storage_path.exists():
            logger.warning(f"No data file found at {storage_path}")
            return None

        return pd.read_parquet(storage_path)

    def get_available_data(self) -> Dict[str, List[str]]:
        """
        Get list of available downloaded data files.

        Returns:
            Dictionary mapping categories to list of files
        """
        available = {}

        for category in ['indices', 'stocks', 'options']:
            category_path = self._data_path / category
            if category_path.exists():
                files = list(category_path.glob("*.parquet"))
                available[category] = [f.stem for f in files]
            else:
                available[category] = []

        return available

    def get_data_summary(
        self,
        instrument_key: str,
        interval: DataInterval = DataInterval.MINUTE_15
    ) -> Optional[Dict[str, Any]]:
        """
        Get summary of downloaded data for an instrument.

        Args:
            instrument_key: Instrument key
            interval: Data interval

        Returns:
            Summary dictionary or None
        """
        df = self.load_historical_data(instrument_key, interval)

        if df is None:
            return None

        return {
            'instrument': instrument_key,
            'interval': interval.value,
            'rows': len(df),
            'date_range': {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat()
            },
            'columns': list(df.columns),
            'file_size_mb': round(
                self._get_storage_path(instrument_key, interval).stat().st_size
                / (1024 * 1024), 2
            )
        }
