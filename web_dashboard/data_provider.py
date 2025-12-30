"""
Data Provider for Web Dashboard.

Provides a unified interface to access all data services from the dashboard.
Handles initialization, connection management, and data aggregation.
"""

import streamlit as st
from datetime import datetime
from typing import Any, Optional, Dict, List
import logging
import sys
from pathlib import Path

# Add parent to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

logger = logging.getLogger(__name__)


class DashboardDataProvider:
    """
    Centralized data provider for the dashboard.

    Manages service initialization and provides convenient access
    to market data, portfolio, orders, capital, and authentication.

    Usage:
        provider = DashboardDataProvider.get_instance()
        positions = provider.get_positions()
        capital = provider.get_capital_state()
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> 'DashboardDataProvider':
        """Get singleton instance of data provider."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize data provider and all services."""
        self._initialized = False
        self._upstox_client = None
        self._market_data_service = None
        self._portfolio_service = None
        self._order_service = None
        self._capital_service = None
        self._token_manager = None
        self._historical_service = None

        self._initialize_services()

    def _initialize_services(self) -> None:
        """Initialize all data services."""
        try:
            from api import UpstoxClient
            from data.services.market_data_service import MarketDataService
            from data.services.portfolio_service import PortfolioService
            from data.services.order_service import OrderService
            from data.services.capital_service import CapitalService
            from data.services.historical_data_service import HistoricalDataService
            from auth.token_manager import TokenManager
            from data.cache.cache_manager import CacheManager
            from data.persistence.state_manager import StateManager

            # Initialize cache and state managers
            cache_manager = CacheManager()
            state_manager = StateManager()

            # Initialize token manager
            self._token_manager = TokenManager(state_manager=state_manager)

            # Initialize Upstox client
            self._upstox_client = UpstoxClient()

            # Set access token if available
            token = self._token_manager.get_token()
            if token:
                self._upstox_client.set_access_token(token)

            # Initialize services
            self._market_data_service = MarketDataService(
                self._upstox_client,
                cache_manager=cache_manager
            )

            self._portfolio_service = PortfolioService(
                self._upstox_client,
                market_data_service=self._market_data_service,
                cache_manager=cache_manager
            )

            self._order_service = OrderService(
                self._upstox_client,
                cache_manager=cache_manager,
                state_manager=state_manager
            )

            self._capital_service = CapitalService(state_manager=state_manager)

            self._historical_service = HistoricalDataService(
                self._upstox_client,
                cache_manager=cache_manager
            )

            self._initialized = True
            logger.info("Dashboard data provider initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize data provider: {e}")
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if services are initialized."""
        return self._initialized

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        if not self._token_manager:
            return False
        return self._token_manager.is_token_valid()

    # Market Data Methods

    def get_index_quotes(self) -> Dict[str, Dict[str, Any]]:
        """Get quotes for major indices (Nifty, Bank Nifty, VIX)."""
        if not self._market_data_service:
            return self._get_demo_index_quotes()

        try:
            return self._market_data_service.get_index_quotes()
        except Exception as e:
            logger.error(f"Error fetching index quotes: {e}")
            return self._get_demo_index_quotes()

    def get_live_quote(self, instrument: str) -> Optional[Dict[str, Any]]:
        """Get live quote for an instrument."""
        if not self._market_data_service:
            return None

        try:
            return self._market_data_service.get_live_quote(instrument)
        except Exception as e:
            logger.error(f"Error fetching quote for {instrument}: {e}")
            return None

    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information."""
        if not self._market_data_service:
            return {
                'state': 'disconnected',
                'is_connected': False,
                'message': 'Services not initialized'
            }

        try:
            return self._market_data_service.get_connection_info()
        except Exception as e:
            return {
                'state': 'error',
                'is_connected': False,
                'message': str(e)
            }

    # Portfolio Methods

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self._portfolio_service or not self.is_authenticated:
            return self._get_demo_positions()

        try:
            positions = self._portfolio_service.get_positions()
            return positions if positions else self._get_demo_positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return self._get_demo_positions()

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get current holdings."""
        if not self._portfolio_service or not self.is_authenticated:
            return []

        try:
            return self._portfolio_service.get_holdings()
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with all metrics."""
        capital = self.get_capital_state()
        current_capital = capital.get('current_capital', 100000) if capital else 100000

        if not self._portfolio_service or not self.is_authenticated:
            return self._get_demo_portfolio_summary(current_capital)

        try:
            return self._portfolio_service.get_portfolio_summary(capital=current_capital)
        except Exception as e:
            logger.error(f"Error fetching portfolio summary: {e}")
            return self._get_demo_portfolio_summary(current_capital)

    def get_unrealized_pnl(self) -> Dict[str, float]:
        """Get unrealized P&L breakdown."""
        if not self._portfolio_service or not self.is_authenticated:
            return {'total': 0, 'long_positions': 0, 'short_positions': 0}

        try:
            return self._portfolio_service.calculate_unrealized_pnl()
        except Exception as e:
            logger.error(f"Error calculating unrealized P&L: {e}")
            return {'total': 0, 'long_positions': 0, 'short_positions': 0}

    def get_portfolio_greeks(self) -> Dict[str, float]:
        """Get portfolio Greeks."""
        if not self._portfolio_service or not self.is_authenticated:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

        try:
            return self._portfolio_service.get_portfolio_greeks()
        except Exception as e:
            logger.error(f"Error calculating portfolio Greeks: {e}")
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

    # Order Methods

    def get_order_book(self) -> List[Dict[str, Any]]:
        """Get order book."""
        if not self._order_service or not self.is_authenticated:
            return []

        try:
            return self._order_service.get_order_book()
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            return []

    def get_trade_book(self) -> List[Dict[str, Any]]:
        """Get trade book."""
        if not self._order_service or not self.is_authenticated:
            return []

        try:
            return self._order_service.get_trade_book()
        except Exception as e:
            logger.error(f"Error fetching trade book: {e}")
            return []

    def get_orders_summary(self) -> Dict[str, Any]:
        """Get orders summary for today."""
        if not self._order_service or not self.is_authenticated:
            return {
                'total_orders': 0,
                'completed_orders': 0,
                'pending_orders': 0,
                'rejected_orders': 0
            }

        try:
            return self._order_service.get_today_orders_summary()
        except Exception as e:
            logger.error(f"Error fetching orders summary: {e}")
            return {
                'total_orders': 0,
                'completed_orders': 0,
                'pending_orders': 0,
                'rejected_orders': 0
            }

    # Capital Methods

    def get_capital_state(self) -> Optional[Dict[str, Any]]:
        """Get current capital state."""
        if not self._capital_service:
            return None

        try:
            return self._capital_service.get_capital_state()
        except Exception as e:
            logger.error(f"Error fetching capital state: {e}")
            return None

    def get_capital_summary(self) -> Dict[str, Any]:
        """Get comprehensive capital summary."""
        if not self._capital_service:
            return {
                'initialized': False,
                'current_capital': 100000,
                'initial_capital': 100000,
                'return_percent': 0
            }

        try:
            return self._capital_service.get_summary()
        except Exception as e:
            logger.error(f"Error fetching capital summary: {e}")
            return {
                'initialized': False,
                'current_capital': 100000,
                'initial_capital': 100000,
                'return_percent': 0
            }

    def is_capital_initialized(self) -> bool:
        """Check if capital has been initialized."""
        if not self._capital_service:
            return False
        return self._capital_service.is_initialized()

    def initialize_capital(self, amount: float, reason: str = "Initial setup") -> bool:
        """Initialize capital for first-time setup."""
        if not self._capital_service:
            return False

        try:
            return self._capital_service.initialize(amount, reason)
        except Exception as e:
            logger.error(f"Error initializing capital: {e}")
            return False

    def deposit_capital(self, amount: float, reason: str = "") -> bool:
        """Record a capital deposit."""
        if not self._capital_service:
            return False

        try:
            return self._capital_service.deposit(amount, reason)
        except Exception as e:
            logger.error(f"Error depositing capital: {e}")
            return False

    def withdraw_capital(self, amount: float, reason: str = "") -> bool:
        """Record a capital withdrawal."""
        if not self._capital_service:
            return False

        try:
            return self._capital_service.withdraw(amount, reason)
        except Exception as e:
            logger.error(f"Error withdrawing capital: {e}")
            return False

    def get_capital_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get capital adjustment history."""
        if not self._capital_service:
            return []

        try:
            return self._capital_service.get_history(limit=limit)
        except Exception as e:
            logger.error(f"Error fetching capital history: {e}")
            return []

    # Authentication Methods

    def get_token_status(self) -> Dict[str, Any]:
        """Get authentication token status."""
        if not self._token_manager:
            return {
                'has_token': False,
                'is_expired': True,
                'status': 'NOT_INITIALIZED'
            }

        try:
            return self._token_manager.get_expiry_status()
        except Exception as e:
            logger.error(f"Error fetching token status: {e}")
            return {
                'has_token': False,
                'is_expired': True,
                'status': 'ERROR',
                'message': str(e)
            }

    def get_authorization_url(self) -> str:
        """Get Upstox authorization URL."""
        if not self._upstox_client:
            return ""

        try:
            return self._upstox_client.get_authorization_url()
        except Exception as e:
            logger.error(f"Error getting authorization URL: {e}")
            return ""

    def set_access_token(self, token: str, expiry_hours: float = 24) -> bool:
        """Store access token after OAuth."""
        if not self._token_manager or not self._upstox_client:
            return False

        try:
            from datetime import timedelta
            expiry_time = datetime.now() + timedelta(hours=expiry_hours)
            self._token_manager.store_token(token, expiry_time)
            self._upstox_client.set_access_token(token)
            return True
        except Exception as e:
            logger.error(f"Error storing access token: {e}")
            return False

    # Demo Data Methods (for when not authenticated)

    def _get_demo_index_quotes(self) -> Dict[str, Dict[str, Any]]:
        """Get demo index quotes."""
        return {
            'NIFTY': {
                'instrument': 'NSE_INDEX|Nifty 50',
                'last_price': 23950.50,
                'open': 23900.00,
                'high': 24050.00,
                'low': 23850.00,
                'change': 50.50,
                'change_percent': 0.21,
                'timestamp': datetime.now().isoformat(),
                'demo': True
            },
            'BANKNIFTY': {
                'instrument': 'NSE_INDEX|Nifty Bank',
                'last_price': 47250.00,
                'open': 47100.00,
                'high': 47400.00,
                'low': 47000.00,
                'change': 150.00,
                'change_percent': 0.32,
                'timestamp': datetime.now().isoformat(),
                'demo': True
            },
            'VIX': {
                'instrument': 'NSE_INDEX|India VIX',
                'last_price': 14.25,
                'open': 14.50,
                'high': 14.80,
                'low': 14.00,
                'change': -0.25,
                'change_percent': -1.72,
                'timestamp': datetime.now().isoformat(),
                'demo': True
            }
        }

    def _get_demo_positions(self) -> List[Dict[str, Any]]:
        """Get demo positions."""
        return [
            {
                'instrument': 'NSE_FO|NIFTY24JAN24000CE',
                'symbol': 'NIFTY 24000 CE',
                'quantity': 50,
                'average_price': 250.00,
                'last_price': 275.00,
                'pnl': 1250.00,
                'unrealized_pnl': 1250.00,
                'pnl_percent': 10.0,
                'direction': 'LONG',
                'product': 'I',
                'option_type': 'CE',
                'demo': True
            },
            {
                'instrument': 'NSE_FO|BANKNIFTY24JAN47000PE',
                'symbol': 'BANKNIFTY 47000 PE',
                'quantity': -25,
                'average_price': 180.00,
                'last_price': 160.00,
                'pnl': 500.00,
                'unrealized_pnl': 500.00,
                'pnl_percent': 11.1,
                'direction': 'SHORT',
                'product': 'I',
                'option_type': 'PE',
                'demo': True
            }
        ]

    def _get_demo_portfolio_summary(self, capital: float) -> Dict[str, Any]:
        """Get demo portfolio summary."""
        return {
            'positions_count': 2,
            'holdings_count': 0,
            'total_position_value': 17000,
            'total_holding_value': 0,
            'total_portfolio_value': 17000,
            'unrealized_pnl': {
                'total': 1750.00,
                'long_positions': 1250.00,
                'short_positions': 500.00
            },
            'portfolio_greeks': {
                'delta': 25.0,
                'gamma': 0.5,
                'theta': -50.0,
                'vega': 10.0
            },
            'long_positions': 1,
            'short_positions': 1,
            'options_positions': 2,
            'capital_utilized_percent': 17.0,
            'timestamp': datetime.now().isoformat(),
            'demo': True
        }


def get_data_provider() -> DashboardDataProvider:
    """
    Get or create the dashboard data provider.

    Uses Streamlit session state for persistence across reruns.
    """
    if 'data_provider' not in st.session_state:
        st.session_state.data_provider = DashboardDataProvider.get_instance()
    return st.session_state.data_provider
