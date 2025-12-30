"""
Options Chain Downloader - Downloads and stores options chain snapshots.

Features:
- Download EOD option chain snapshots
- Store strikes, premiums, IV, Greeks, OI
- Organize by expiry date
- Historical IV database for IV Rank/Percentile
"""

import time
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List
from pathlib import Path
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class OptionsChainDownloader:
    """
    Downloads and stores options chain historical data.

    Features:
    - EOD option chain snapshots
    - Strike prices, premiums, IV, Greeks, OI
    - Organized by underlying and expiry
    - Historical IV tracking for IV Rank/Percentile

    Example:
        downloader = OptionsChainDownloader(upstox_client)

        # Download current option chain
        result = downloader.download_option_chain_snapshot(
            underlying='NSE_INDEX|Nifty 50',
            expiry_date=date(2025, 1, 2)
        )

        # Get IV history
        iv_data = downloader.get_iv_history('NSE_INDEX|Nifty 50')
    """

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 250
    REQUEST_DELAY_SECONDS = 0.3

    # Storage paths
    BASE_DATA_PATH = Path("data/historical/options")

    # IV history tracking
    IV_HISTORY_FILE = "iv_history.parquet"

    def __init__(
        self,
        upstox_client=None,
        data_path: Optional[Path] = None
    ):
        """
        Initialize options chain downloader.

        Args:
            upstox_client: Upstox client for API calls
            data_path: Custom data storage path
        """
        self._client = upstox_client
        self._data_path = data_path or self.BASE_DATA_PATH
        self._data_path.mkdir(parents=True, exist_ok=True)

        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0
        self._minute_start = time.time()

    def _rate_limit(self) -> None:
        """Apply rate limiting before API call."""
        now = time.time()

        if now - self._minute_start >= 60:
            self._request_count = 0
            self._minute_start = now

        if self._request_count >= self.MAX_REQUESTS_PER_MINUTE:
            sleep_time = 60 - (now - self._minute_start)
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self._request_count = 0
                self._minute_start = time.time()

        time_since_last = now - self._last_request_time
        if time_since_last < self.REQUEST_DELAY_SECONDS:
            time.sleep(self.REQUEST_DELAY_SECONDS - time_since_last)

        self._last_request_time = time.time()
        self._request_count += 1

    def _get_storage_path(
        self,
        underlying: str,
        expiry_date: date,
        snapshot_date: date
    ) -> Path:
        """
        Get storage path for option chain snapshot.

        Args:
            underlying: Underlying instrument
            expiry_date: Option expiry date
            snapshot_date: Date of snapshot

        Returns:
            Path to parquet file
        """
        # Clean names
        safe_underlying = underlying.replace("|", "_").replace(" ", "_")
        expiry_str = expiry_date.strftime("%Y%m%d")
        snapshot_str = snapshot_date.strftime("%Y%m%d")

        # Path: options/NIFTY/2025-01/NIFTY_20250102_snapshot_20241230.parquet
        expiry_month = expiry_date.strftime("%Y-%m")
        path = (
            self._data_path / safe_underlying / expiry_month /
            f"{safe_underlying}_{expiry_str}_snapshot_{snapshot_str}.parquet"
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        return path

    def download_option_chain_snapshot(
        self,
        underlying: str,
        expiry_date: date,
        snapshot_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Download and save option chain snapshot.

        Args:
            underlying: Underlying instrument (e.g., 'NSE_INDEX|Nifty 50')
            expiry_date: Option expiry date
            snapshot_date: Date of snapshot (defaults to today)

        Returns:
            Dictionary with download status and details
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        logger.info(
            f"Downloading option chain for {underlying}, "
            f"expiry {expiry_date}, snapshot {snapshot_date}"
        )

        try:
            self._rate_limit()

            if self._client:
                # Fetch from API
                df = self._client.get_option_chain(underlying, expiry_date.isoformat())
            else:
                # Generate demo data
                df = self._generate_demo_option_chain(underlying, expiry_date)

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return {
                    'status': 'no_data',
                    'rows': 0,
                    'path': None
                }

            # Normalize and enrich data
            df = self._normalize_option_chain(df, underlying, expiry_date, snapshot_date)

            # Calculate IV Rank and Percentile if we have history
            df = self._add_iv_metrics(df, underlying)

            # Save snapshot
            storage_path = self._get_storage_path(underlying, expiry_date, snapshot_date)
            df.to_parquet(storage_path, index=False)

            # Update IV history
            self._update_iv_history(underlying, snapshot_date, df)

            logger.info(f"Saved {len(df)} option rows to {storage_path}")

            return {
                'status': 'success',
                'rows': len(df),
                'path': str(storage_path),
                'underlying': underlying,
                'expiry': expiry_date.isoformat(),
                'snapshot_date': snapshot_date.isoformat(),
                'strikes': df['strike_price'].nunique(),
                'atm_iv': self._get_atm_iv(df)
            }

        except Exception as e:
            logger.error(f"Error downloading option chain: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'rows': 0,
                'path': None
            }

    def _normalize_option_chain(
        self,
        df: pd.DataFrame,
        underlying: str,
        expiry_date: date,
        snapshot_date: date
    ) -> pd.DataFrame:
        """
        Normalize option chain data to standard format.

        Standard schema:
        - timestamp: Snapshot datetime
        - underlying_symbol: Underlying instrument
        - underlying_spot: Spot price
        - expiry_date: Option expiry
        - strike_price: Strike price
        - option_type: CE or PE
        - ltp: Last traded price
        - bid_price, bid_qty, ask_price, ask_qty
        - oi: Open interest
        - oi_change: Change in OI
        - volume: Trading volume
        - iv: Implied volatility
        - delta, gamma, theta, vega: Greeks
        """
        # Add metadata columns
        df['timestamp'] = datetime.combine(snapshot_date, datetime.min.time())
        df['underlying_symbol'] = underlying
        df['expiry_date'] = expiry_date

        # Ensure required columns exist with defaults
        defaults = {
            'underlying_spot': 0.0,
            'strike_price': 0.0,
            'option_type': 'CE',
            'ltp': 0.0,
            'bid_price': 0.0,
            'bid_qty': 0,
            'ask_price': 0.0,
            'ask_qty': 0,
            'oi': 0,
            'oi_change': 0,
            'volume': 0,
            'iv': 0.0,
            'delta': 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0
        }

        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = default

        # Select and order columns
        columns = [
            'timestamp', 'underlying_symbol', 'underlying_spot', 'expiry_date',
            'strike_price', 'option_type', 'ltp', 'bid_price', 'bid_qty',
            'ask_price', 'ask_qty', 'oi', 'oi_change', 'volume',
            'iv', 'delta', 'gamma', 'theta', 'vega'
        ]

        return df[[c for c in columns if c in df.columns]]

    def _get_atm_iv(self, df: pd.DataFrame) -> Optional[float]:
        """
        Get ATM implied volatility from option chain.

        Args:
            df: Option chain DataFrame

        Returns:
            ATM IV or None
        """
        if 'underlying_spot' not in df.columns or 'strike_price' not in df.columns:
            return None

        spot = df['underlying_spot'].iloc[0] if len(df) > 0 else 0
        if spot == 0:
            return None

        # Find ATM strike
        df['strike_distance'] = abs(df['strike_price'] - spot)
        atm_row = df.loc[df['strike_distance'].idxmin()]

        return atm_row.get('iv', None)

    def _add_iv_metrics(
        self,
        df: pd.DataFrame,
        underlying: str
    ) -> pd.DataFrame:
        """
        Add IV Rank and IV Percentile based on historical data.

        Args:
            df: Option chain DataFrame
            underlying: Underlying symbol

        Returns:
            DataFrame with IV metrics added
        """
        # Load IV history
        iv_history = self._load_iv_history(underlying)

        if iv_history is None or len(iv_history) < 20:
            df['iv_rank'] = None
            df['iv_percentile'] = None
            return df

        # Calculate ATM IV for current snapshot
        current_atm_iv = self._get_atm_iv(df)
        if current_atm_iv is None:
            df['iv_rank'] = None
            df['iv_percentile'] = None
            return df

        # Calculate IV Rank (current IV relative to 1-year range)
        # IV Rank = (Current IV - 52-week Low) / (52-week High - 52-week Low)
        iv_values = iv_history['atm_iv'].dropna()
        iv_min = iv_values.min()
        iv_max = iv_values.max()

        if iv_max > iv_min:
            iv_rank = (current_atm_iv - iv_min) / (iv_max - iv_min) * 100
        else:
            iv_rank = 50.0

        # Calculate IV Percentile (% of days with lower IV)
        iv_percentile = (iv_values < current_atm_iv).sum() / len(iv_values) * 100

        df['iv_rank'] = round(iv_rank, 2)
        df['iv_percentile'] = round(iv_percentile, 2)

        return df

    def _load_iv_history(self, underlying: str) -> Optional[pd.DataFrame]:
        """
        Load IV history for an underlying.

        Args:
            underlying: Underlying symbol

        Returns:
            DataFrame with IV history or None
        """
        safe_name = underlying.replace("|", "_").replace(" ", "_")
        history_path = self._data_path / safe_name / self.IV_HISTORY_FILE

        if not history_path.exists():
            return None

        return pd.read_parquet(history_path)

    def _update_iv_history(
        self,
        underlying: str,
        snapshot_date: date,
        df: pd.DataFrame
    ) -> None:
        """
        Update IV history with new snapshot data.

        Args:
            underlying: Underlying symbol
            snapshot_date: Date of snapshot
            df: Option chain DataFrame
        """
        safe_name = underlying.replace("|", "_").replace(" ", "_")
        history_path = self._data_path / safe_name / self.IV_HISTORY_FILE
        history_path.parent.mkdir(parents=True, exist_ok=True)

        atm_iv = self._get_atm_iv(df)
        if atm_iv is None:
            return

        # Get underlying spot
        spot = df['underlying_spot'].iloc[0] if len(df) > 0 else 0

        new_row = pd.DataFrame([{
            'date': snapshot_date,
            'underlying': underlying,
            'atm_iv': atm_iv,
            'spot_price': spot
        }])

        # Load existing history
        if history_path.exists():
            existing = pd.read_parquet(history_path)

            # Check if date already exists
            if snapshot_date in existing['date'].values:
                # Update existing row
                existing.loc[existing['date'] == snapshot_date, 'atm_iv'] = atm_iv
                existing.loc[existing['date'] == snapshot_date, 'spot_price'] = spot
                history = existing
            else:
                history = pd.concat([existing, new_row], ignore_index=True)
        else:
            history = new_row

        # Keep last 365 days
        history = history.sort_values('date').tail(365)

        history.to_parquet(history_path, index=False)

    def _generate_demo_option_chain(
        self,
        underlying: str,
        expiry_date: date
    ) -> pd.DataFrame:
        """
        Generate demo option chain data for testing.

        Args:
            underlying: Underlying symbol
            expiry_date: Expiry date

        Returns:
            DataFrame with demo option chain
        """
        # Base price for underlying
        if 'BANKNIFTY' in underlying.upper():
            spot = 51000
            lot_size = 15
        elif 'NIFTY' in underlying.upper():
            spot = 24000
            lot_size = 25
        else:
            spot = 1000
            lot_size = 100

        # Generate strikes around ATM
        strike_step = 50 if 'NIFTY' in underlying.upper() else 100
        atm_strike = round(spot / strike_step) * strike_step

        strikes = list(range(
            atm_strike - strike_step * 20,
            atm_strike + strike_step * 21,
            strike_step
        ))

        # Days to expiry
        dte = max((expiry_date - date.today()).days, 1)

        data = []
        for strike in strikes:
            for option_type in ['CE', 'PE']:
                # Simple Black-Scholes approximation
                moneyness = (spot - strike) / spot
                if option_type == 'PE':
                    moneyness = -moneyness

                # Base IV varies with moneyness (smile)
                base_iv = 15 + abs(moneyness) * 50  # Higher IV for OTM
                iv = base_iv + np.random.normal(0, 2)

                # Approximate premium
                if option_type == 'CE':
                    intrinsic = max(spot - strike, 0)
                else:
                    intrinsic = max(strike - spot, 0)

                time_value = spot * (iv / 100) * np.sqrt(dte / 365) * 0.4
                premium = intrinsic + time_value

                # Greeks (simplified)
                if option_type == 'CE':
                    delta = 0.5 + moneyness * 2
                    delta = max(-1, min(1, delta))
                else:
                    delta = -0.5 + moneyness * 2
                    delta = max(-1, min(0, delta))

                gamma = 0.01 * np.exp(-moneyness ** 2 * 10)
                theta = -premium * 0.05 / dte if dte > 0 else 0
                vega = spot * np.sqrt(dte / 365) * 0.01

                # OI and volume (higher near ATM)
                atm_factor = np.exp(-abs(moneyness) * 20)
                oi = int(100000 * atm_factor * np.random.uniform(0.5, 1.5))
                volume = int(oi * 0.1 * np.random.uniform(0.5, 2))

                data.append({
                    'underlying_spot': spot,
                    'strike_price': strike,
                    'option_type': option_type,
                    'ltp': round(max(premium, 0.05), 2),
                    'bid_price': round(max(premium * 0.98, 0.05), 2),
                    'bid_qty': int(lot_size * np.random.randint(10, 100)),
                    'ask_price': round(max(premium * 1.02, 0.10), 2),
                    'ask_qty': int(lot_size * np.random.randint(10, 100)),
                    'oi': oi,
                    'oi_change': int(oi * np.random.uniform(-0.1, 0.1)),
                    'volume': volume,
                    'iv': round(iv, 2),
                    'delta': round(delta, 4),
                    'gamma': round(gamma, 6),
                    'theta': round(theta, 2),
                    'vega': round(vega, 2)
                })

        return pd.DataFrame(data)

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
        history = self._load_iv_history(underlying)

        if history is None:
            return None

        # Filter to requested days
        cutoff_date = date.today() - timedelta(days=days)
        history = history[history['date'] >= cutoff_date]

        return history.sort_values('date')

    def calculate_iv_rank(
        self,
        underlying: str,
        current_iv: Optional[float] = None
    ) -> Optional[Dict[str, float]]:
        """
        Calculate IV Rank and Percentile for an underlying.

        Args:
            underlying: Underlying symbol
            current_iv: Current IV (if None, uses latest from history)

        Returns:
            Dictionary with IV metrics
        """
        history = self._load_iv_history(underlying)

        if history is None or len(history) < 20:
            return None

        iv_values = history['atm_iv'].dropna()

        if current_iv is None:
            current_iv = iv_values.iloc[-1]

        iv_min = iv_values.min()
        iv_max = iv_values.max()

        if iv_max > iv_min:
            iv_rank = (current_iv - iv_min) / (iv_max - iv_min) * 100
        else:
            iv_rank = 50.0

        iv_percentile = (iv_values < current_iv).sum() / len(iv_values) * 100

        return {
            'current_iv': round(current_iv, 2),
            'iv_rank': round(iv_rank, 2),
            'iv_percentile': round(iv_percentile, 2),
            'iv_min_52w': round(iv_min, 2),
            'iv_max_52w': round(iv_max, 2),
            'iv_mean': round(iv_values.mean(), 2),
            'data_points': len(iv_values)
        }

    def load_option_chain_snapshot(
        self,
        underlying: str,
        expiry_date: date,
        snapshot_date: date
    ) -> Optional[pd.DataFrame]:
        """
        Load a previously saved option chain snapshot.

        Args:
            underlying: Underlying symbol
            expiry_date: Option expiry date
            snapshot_date: Date of snapshot

        Returns:
            DataFrame with option chain or None
        """
        storage_path = self._get_storage_path(underlying, expiry_date, snapshot_date)

        if not storage_path.exists():
            return None

        return pd.read_parquet(storage_path)

    def get_available_snapshots(
        self,
        underlying: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Get list of available option chain snapshots.

        Args:
            underlying: Filter by underlying (optional)

        Returns:
            Dictionary mapping underlyings to snapshot files
        """
        available = {}

        search_path = self._data_path
        if underlying:
            safe_name = underlying.replace("|", "_").replace(" ", "_")
            search_path = search_path / safe_name

        for parquet_file in search_path.rglob("*.parquet"):
            if parquet_file.name == self.IV_HISTORY_FILE:
                continue

            # Extract underlying from path
            parts = parquet_file.parts
            underlying_name = parts[-3] if len(parts) >= 3 else "unknown"

            if underlying_name not in available:
                available[underlying_name] = []

            available[underlying_name].append(parquet_file.stem)

        return available
