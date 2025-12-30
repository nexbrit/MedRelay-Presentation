"""
Data Retrieval Service - Unified interface for historical data access.

Provides a clean API to retrieve historical OHLCV and options data
for backtesting and analysis.

Features:
- Unified interface for all historical data
- Automatic caching for frequently accessed data
- Export to CSV/JSON
- Date range filtering
- Data quality reporting
"""

from datetime import date, timedelta
from typing import Any, Optional, Dict, List, Union
from pathlib import Path
import logging

import pandas as pd

from data.downloaders.historical_downloader import (
    HistoricalDownloader,
    DataInterval,
)
from data.downloaders.options_chain_downloader import OptionsChainDownloader
from data.schemas.parquet_schemas import (
    validate_ohlcv_data,
    validate_option_chain_data,
)

logger = logging.getLogger(__name__)


class DataRetrievalService:
    """
    Unified service for retrieving historical market data.

    Provides a simple interface to:
    - Fetch historical OHLCV data for indices and stocks
    - Fetch historical options chain snapshots
    - Get IV history and metrics
    - Export data in various formats
    - Validate data quality

    Example:
        service = DataRetrievalService()

        # Get Nifty 15-minute data
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
    """

    def __init__(
        self,
        upstox_client=None,
        data_path: Optional[Path] = None
    ):
        """
        Initialize data retrieval service.

        Args:
            upstox_client: Upstox client for downloading new data
            data_path: Base path for data storage
        """
        self._client = upstox_client
        self._data_path = data_path or Path("data/historical")

        # Initialize downloaders
        self._historical_downloader = HistoricalDownloader(
            upstox_client,
            data_path
        )
        self._options_downloader = OptionsChainDownloader(
            upstox_client,
            data_path / "options" if data_path else None
        )

        # In-memory cache for frequently accessed data
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_max_size = 10  # Max cached DataFrames

    def get_historical_data(
        self,
        instrument: str,
        start_date: date,
        end_date: date,
        interval: Union[str, DataInterval] = "15minute",
        download_if_missing: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data for an instrument.

        Args:
            instrument: Instrument key (e.g., 'NSE_INDEX|Nifty 50')
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval ('1minute', '5minute', '15minute', 'day', etc.)
            download_if_missing: Download data if not available locally

        Returns:
            DataFrame with OHLCV data or None
        """
        # Convert string interval to enum
        if isinstance(interval, str):
            interval = DataInterval(interval)

        cache_key = f"{instrument}_{interval.value}_{start_date}_{end_date}"

        # Check cache
        if cache_key in self._cache:
            logger.debug(f"Returning cached data for {cache_key}")
            return self._cache[cache_key].copy()

        # Try to load from file
        df = self._historical_downloader.load_historical_data(
            instrument, interval
        )

        if df is not None:
            # Filter to date range
            df = df[
                (df['timestamp'].dt.date >= start_date) &
                (df['timestamp'].dt.date <= end_date)
            ]

            if len(df) > 0:
                self._add_to_cache(cache_key, df)
                return df.copy()

        # Download if missing
        if download_if_missing:
            logger.info(f"Downloading {instrument} data...")
            result = self._historical_downloader.download_index_history(
                instrument, start_date, end_date, interval
            )

            if result['status'].value in ['success', 'partial']:
                df = self._historical_downloader.load_historical_data(
                    instrument, interval
                )
                if df is not None:
                    df = df[
                        (df['timestamp'].dt.date >= start_date) &
                        (df['timestamp'].dt.date <= end_date)
                    ]
                    self._add_to_cache(cache_key, df)
                    return df.copy()

        return None

    def get_option_chain_snapshot(
        self,
        underlying: str,
        expiry: date,
        snapshot_date: Optional[date] = None,
        download_if_missing: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get option chain snapshot for a specific date.

        Args:
            underlying: Underlying instrument
            expiry: Option expiry date
            snapshot_date: Date of snapshot (defaults to today)
            download_if_missing: Download if not available

        Returns:
            DataFrame with option chain data or None
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        # Try to load from file
        df = self._options_downloader.load_option_chain_snapshot(
            underlying, expiry, snapshot_date
        )

        if df is not None:
            return df

        # Download if missing
        if download_if_missing:
            logger.info(f"Downloading option chain for {underlying}...")
            result = self._options_downloader.download_option_chain_snapshot(
                underlying, expiry, snapshot_date
            )

            if result['status'] == 'success':
                return self._options_downloader.load_option_chain_snapshot(
                    underlying, expiry, snapshot_date
                )

        return None

    def get_iv_history(
        self,
        underlying: str,
        days: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        Get IV history for an underlying.

        Args:
            underlying: Underlying symbol
            days: Number of days of history

        Returns:
            DataFrame with IV history
        """
        return self._options_downloader.get_iv_history(underlying, days)

    def get_iv_metrics(
        self,
        underlying: str,
        current_iv: Optional[float] = None
    ) -> Optional[Dict[str, float]]:
        """
        Calculate IV Rank and Percentile for an underlying.

        Args:
            underlying: Underlying symbol
            current_iv: Current IV (if None, uses latest)

        Returns:
            Dictionary with IV metrics
        """
        return self._options_downloader.calculate_iv_rank(
            underlying, current_iv
        )

    def export_to_csv(
        self,
        df: pd.DataFrame,
        filepath: Union[str, Path]
    ) -> bool:
        """
        Export DataFrame to CSV file.

        Args:
            df: DataFrame to export
            filepath: Output file path

        Returns:
            True if successful
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(filepath, index=False)
            logger.info(f"Exported {len(df)} rows to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False

    def export_to_json(
        self,
        df: pd.DataFrame,
        filepath: Union[str, Path]
    ) -> bool:
        """
        Export DataFrame to JSON file.

        Args:
            df: DataFrame to export
            filepath: Output file path

        Returns:
            True if successful
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            df.to_json(filepath, orient='records', date_format='iso')
            logger.info(f"Exported {len(df)} rows to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return False

    def validate_data(
        self,
        df: pd.DataFrame,
        data_type: str = 'ohlcv'
    ) -> Dict[str, Any]:
        """
        Validate DataFrame against schema.

        Args:
            df: DataFrame to validate
            data_type: 'ohlcv' or 'option_chain'

        Returns:
            Validation report
        """
        if data_type == 'ohlcv':
            return validate_ohlcv_data(df)
        elif data_type == 'option_chain':
            return validate_option_chain_data(df)
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def get_available_data(self) -> Dict[str, Any]:
        """
        Get summary of all available downloaded data.

        Returns:
            Dictionary with available data by category
        """
        historical = self._historical_downloader.get_available_data()
        options = self._options_downloader.get_available_snapshots()

        return {
            'historical': historical,
            'options': options
        }

    def get_data_summary(
        self,
        instrument: str,
        interval: Union[str, DataInterval] = "15minute"
    ) -> Optional[Dict[str, Any]]:
        """
        Get summary of downloaded data for an instrument.

        Args:
            instrument: Instrument key
            interval: Data interval

        Returns:
            Summary dictionary
        """
        if isinstance(interval, str):
            interval = DataInterval(interval)

        return self._historical_downloader.get_data_summary(instrument, interval)

    def _add_to_cache(
        self,
        key: str,
        df: pd.DataFrame
    ) -> None:
        """
        Add DataFrame to cache with LRU eviction.

        Args:
            key: Cache key
            df: DataFrame to cache
        """
        # Evict oldest if cache is full
        if len(self._cache) >= self._cache_max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = df.copy()

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.info("Data cache cleared")

    def get_returns(
        self,
        df: pd.DataFrame,
        period: int = 1
    ) -> pd.Series:
        """
        Calculate returns from OHLCV data.

        Args:
            df: OHLCV DataFrame
            period: Return period (1 = daily/per-candle)

        Returns:
            Series with returns
        """
        if 'close' not in df.columns:
            raise ValueError("DataFrame must have 'close' column")

        return df['close'].pct_change(period)

    def get_volatility(
        self,
        df: pd.DataFrame,
        window: int = 20,
        annualize: bool = True
    ) -> pd.Series:
        """
        Calculate rolling volatility from OHLCV data.

        Args:
            df: OHLCV DataFrame
            window: Rolling window size
            annualize: Whether to annualize (assumes 252 trading days)

        Returns:
            Series with volatility
        """
        returns = self.get_returns(df)
        vol = returns.rolling(window).std()

        if annualize:
            vol = vol * (252 ** 0.5)

        return vol

    def resample_data(
        self,
        df: pd.DataFrame,
        target_interval: str
    ) -> pd.DataFrame:
        """
        Resample OHLCV data to a different interval.

        Args:
            df: OHLCV DataFrame with 'timestamp' column
            target_interval: Target interval ('5T', '15T', '1H', '1D', etc.)

        Returns:
            Resampled DataFrame
        """
        if 'timestamp' not in df.columns:
            raise ValueError("DataFrame must have 'timestamp' column")

        df = df.set_index('timestamp')

        resampled = df.resample(target_interval).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        if 'open_interest' in df.columns:
            resampled['open_interest'] = df['open_interest'].resample(
                target_interval
            ).last()

        return resampled.reset_index()

    def get_trading_days(
        self,
        df: pd.DataFrame
    ) -> List[date]:
        """
        Get list of trading days from data.

        Args:
            df: OHLCV DataFrame

        Returns:
            List of unique trading days
        """
        if 'timestamp' not in df.columns:
            return []

        dates = df['timestamp'].dt.date.unique()
        return sorted(dates.tolist())

    def detect_gaps(
        self,
        df: pd.DataFrame,
        expected_interval_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Detect gaps in time series data.

        Args:
            df: OHLCV DataFrame
            expected_interval_minutes: Expected interval between candles

        Returns:
            List of detected gaps
        """
        if 'timestamp' not in df.columns or len(df) < 2:
            return []

        df_sorted = df.sort_values('timestamp')
        time_diffs = df_sorted['timestamp'].diff()

        expected_delta = timedelta(minutes=expected_interval_minutes)
        threshold = expected_delta * 2  # Gap if > 2x expected

        gaps = []
        for idx, diff in time_diffs.items():
            if pd.notna(diff) and diff > threshold:
                prev_idx = df_sorted.index.get_loc(idx) - 1
                if prev_idx >= 0:
                    prev_ts = df_sorted.iloc[prev_idx]['timestamp']
                    curr_ts = df_sorted.loc[idx, 'timestamp']
                    gaps.append({
                        'from': prev_ts.isoformat(),
                        'to': curr_ts.isoformat(),
                        'gap_minutes': diff.total_seconds() / 60
                    })

        return gaps
