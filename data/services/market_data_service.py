"""
Market Data Service with caching, rate limiting, and connection state tracking.

Provides a clean interface to fetch live market quotes and option chains
with automatic caching, rate limiting to respect Upstox API limits,
and connection state monitoring.
"""

import time
import threading
from datetime import datetime
from typing import Any, Optional, List, Dict
from enum import Enum
from collections import deque
import logging
import pandas as pd

from data.cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    UNKNOWN = "unknown"


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Respects Upstox limit of 250 requests/minute.
    """

    def __init__(self, max_requests: int = 250, time_window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            time_window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window_seconds
        self._requests: deque = deque()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire permission to make a request.

        Args:
            timeout: Maximum time to wait for permission

        Returns:
            True if acquired, False if timeout
        """
        start_time = time.time()

        while True:
            with self._lock:
                now = time.time()

                # Remove old requests outside window
                while self._requests and self._requests[0] < now - self.time_window:
                    self._requests.popleft()

                # Check if we can make request
                if len(self._requests) < self.max_requests:
                    self._requests.append(now)
                    return True

            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning("Rate limiter timeout - too many requests")
                return False

            # Wait before retrying
            time.sleep(0.1)

    def get_available_requests(self) -> int:
        """Get number of available requests."""
        with self._lock:
            now = time.time()
            while self._requests and self._requests[0] < now - self.time_window:
                self._requests.popleft()
            return self.max_requests - len(self._requests)


class MarketDataService:
    """
    Service for fetching market data with caching and rate limiting.

    Features:
    - Automatic caching with configurable TTL
    - Rate limiting to respect API limits (250 req/min)
    - Connection state tracking
    - Fallback to last known good data on API failures
    - Thread-safe operations

    Example:
        service = MarketDataService(upstox_client)
        quote = service.get_live_quote('NSE_INDEX|Nifty 50')
        option_chain = service.get_option_chain('NSE_INDEX|Nifty 50', '2025-01-02')
    """

    # Cache TTL defaults (in seconds)
    QUOTE_TTL = 5
    OPTION_CHAIN_TTL = 30
    EXPIRY_TTL = 3600  # 1 hour

    def __init__(
        self,
        upstox_client,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize market data service.

        Args:
            upstox_client: UpstoxClient instance for API calls
            cache_manager: Optional custom cache manager
            rate_limiter: Optional custom rate limiter
        """
        self._client = upstox_client
        self._cache = cache_manager or CacheManager()
        self._rate_limiter = rate_limiter or RateLimiter()
        self._connection_state = ConnectionState.UNKNOWN
        self._last_successful_call = None
        self._consecutive_failures = 0
        self._lock = threading.Lock()

        # Store last known good data for fallback
        self._last_known_quotes: Dict[str, Dict[str, Any]] = {}

    @property
    def connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        """Check if service is connected."""
        return self._connection_state == ConnectionState.CONNECTED

    def _update_connection_state(self, success: bool) -> None:
        """Update connection state based on API call result."""
        with self._lock:
            if success:
                self._connection_state = ConnectionState.CONNECTED
                self._last_successful_call = datetime.now()
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    self._connection_state = ConnectionState.DISCONNECTED
                elif self._consecutive_failures >= 1:
                    self._connection_state = ConnectionState.RECONNECTING

    def get_live_quote(
        self,
        instrument_key: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get live quote for an instrument.

        Args:
            instrument_key: Instrument key (e.g., 'NSE_INDEX|Nifty 50')
            use_cache: Whether to use cache (default: True)

        Returns:
            Dictionary with quote data or None on failure
        """
        cache_key = f"quote:{instrument_key}"

        # Check cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        # Rate limit check
        if not self._rate_limiter.acquire():
            logger.warning(f"Rate limit hit for {instrument_key}, using fallback")
            return self._last_known_quotes.get(instrument_key)

        try:
            # Fetch from API
            df = self._client.get_market_quote([instrument_key])

            if df.empty:
                self._update_connection_state(False)
                return self._last_known_quotes.get(instrument_key)

            # Convert to dict
            row = df.iloc[0]
            quote_data = {
                'instrument': instrument_key,
                'last_price': float(row.get('last_price', 0)) if pd.notna(row.get('last_price')) else None,
                'open': float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                'high': float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
                'low': float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                'close': float(row.get('last_price', 0)) if pd.notna(row.get('last_price')) else None,
                'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
                'timestamp': datetime.now().isoformat(),
                'cached': False
            }

            # Update cache
            self._cache.set(cache_key, quote_data, self.QUOTE_TTL)

            # Store as last known good
            self._last_known_quotes[instrument_key] = quote_data

            self._update_connection_state(True)
            return quote_data

        except Exception as e:
            logger.error(f"Error fetching quote for {instrument_key}: {e}")
            self._update_connection_state(False)

            # Return last known good data
            fallback = self._last_known_quotes.get(instrument_key)
            if fallback:
                fallback['cached'] = True
                fallback['fallback'] = True
            return fallback

    def get_live_quotes(
        self,
        instrument_keys: List[str],
        use_cache: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get live quotes for multiple instruments.

        Args:
            instrument_keys: List of instrument keys
            use_cache: Whether to use cache

        Returns:
            Dictionary mapping instrument keys to quote data
        """
        results = {}
        uncached_keys = []

        # Check cache for each instrument
        if use_cache:
            for key in instrument_keys:
                cached = self._cache.get(f"quote:{key}")
                if cached:
                    cached['cached'] = True
                    results[key] = cached
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = instrument_keys

        if not uncached_keys:
            return results

        # Rate limit check
        if not self._rate_limiter.acquire():
            logger.warning("Rate limit hit, returning cached/fallback data")
            for key in uncached_keys:
                if key in self._last_known_quotes:
                    data = self._last_known_quotes[key].copy()
                    data['fallback'] = True
                    results[key] = data
            return results

        try:
            # Fetch uncached instruments from API
            df = self._client.get_market_quote(uncached_keys)

            for _, row in df.iterrows():
                instrument = row.get('instrument', '')
                quote_data = {
                    'instrument': instrument,
                    'last_price': float(row.get('last_price', 0)) if pd.notna(row.get('last_price')) else None,
                    'open': float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                    'high': float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
                    'low': float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                    'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
                    'timestamp': datetime.now().isoformat(),
                    'cached': False
                }

                # Cache and store
                self._cache.set(f"quote:{instrument}", quote_data, self.QUOTE_TTL)
                self._last_known_quotes[instrument] = quote_data
                results[instrument] = quote_data

            self._update_connection_state(True)

        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            self._update_connection_state(False)

            # Return fallback data for uncached
            for key in uncached_keys:
                if key in self._last_known_quotes:
                    data = self._last_known_quotes[key].copy()
                    data['fallback'] = True
                    results[key] = data

        return results

    def get_option_chain(
        self,
        underlying: str,
        expiry_date: str = None,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get option chain for an underlying.

        Args:
            underlying: Underlying instrument key (e.g., 'NSE_INDEX|Nifty 50')
            expiry_date: Expiry date in YYYY-MM-DD format (defaults to nearest)
            use_cache: Whether to use cache (default: True)

        Returns:
            DataFrame with option chain data or None on failure
        """
        # If no expiry provided, get nearest
        if not expiry_date:
            expiries = self.get_option_expiries(underlying)
            if expiries:
                expiry_date = expiries[0]
            else:
                return None

        cache_key = f"option_chain:{underlying}:{expiry_date}"

        # Check cache
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return pd.DataFrame(cached)

        # Rate limit
        if not self._rate_limiter.acquire():
            logger.warning(f"Rate limit hit for option chain {underlying}")
            cached = self._cache.get(cache_key)
            return pd.DataFrame(cached) if cached else None

        try:
            df = self._client.get_option_chain(underlying, expiry_date)

            if df.empty:
                self._update_connection_state(False)
                return df

            # Cache the result
            self._cache.set(cache_key, df.to_dict('records'), self.OPTION_CHAIN_TTL)

            self._update_connection_state(True)
            return df

        except Exception as e:
            logger.error(f"Error fetching option chain for {underlying}: {e}")
            self._update_connection_state(False)

            # Try to return cached data even if expired
            cached = self._cache.get(cache_key)
            return pd.DataFrame(cached) if cached else None

    def get_option_expiries(
        self,
        underlying: str,
        use_cache: bool = True
    ) -> Optional[List[str]]:
        """
        Get available expiry dates for an underlying.

        Args:
            underlying: Underlying instrument key
            use_cache: Whether to use cache

        Returns:
            List of expiry dates in YYYY-MM-DD format
        """
        cache_key = f"expiries:{underlying}"

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        # Rate limit
        if not self._rate_limiter.acquire():
            logger.warning(f"Rate limit hit for expiries {underlying}")
            return self._cache.get(cache_key)

        try:
            # This would need to be added to the UpstoxClient
            # For now, simulate with option chain call
            import upstox_client as upstox_sdk

            api_instance = upstox_sdk.OptionsApi(self._client.api_client)
            response = api_instance.get_option_expiries(underlying)

            expiries = list(response.data) if response.data else []

            self._cache.set(cache_key, expiries, self.EXPIRY_TTL)
            self._update_connection_state(True)

            return expiries

        except Exception as e:
            logger.error(f"Error fetching expiries for {underlying}: {e}")
            self._update_connection_state(False)
            return self._cache.get(cache_key)

    def get_index_quotes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get quotes for major indices (Nifty 50, Bank Nifty, India VIX).

        Returns:
            Dictionary mapping index names to quote data
        """
        index_instruments = [
            'NSE_INDEX|Nifty 50',
            'NSE_INDEX|Nifty Bank',
            'NSE_INDEX|India VIX'
        ]

        quotes = self.get_live_quotes(index_instruments)

        # Map to friendly names
        result = {}
        name_mapping = {
            'NSE_INDEX|Nifty 50': 'NIFTY',
            'NSE_INDEX|Nifty Bank': 'BANKNIFTY',
            'NSE_INDEX|India VIX': 'VIX'
        }

        for key, data in quotes.items():
            friendly_name = name_mapping.get(key, key)
            result[friendly_name] = data

        return result

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection status information.

        Returns:
            Dictionary with connection state details
        """
        return {
            'state': self._connection_state.value,
            'is_connected': self.is_connected,
            'last_successful_call': (
                self._last_successful_call.isoformat()
                if self._last_successful_call else None
            ),
            'consecutive_failures': self._consecutive_failures,
            'available_requests': self._rate_limiter.get_available_requests(),
            'cache_stats': self._cache.get_stats()
        }

    def clear_cache(self) -> int:
        """Clear all cached market data."""
        return self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()
