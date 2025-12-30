"""
Portfolio Service for position and holdings management.

Provides real-time portfolio data including positions, holdings,
P&L calculations, and portfolio Greeks aggregation.
"""

from datetime import datetime
from typing import Any, Optional, List, Dict
import logging

from data.cache.cache_manager import CacheManager
from data.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Service for portfolio management including positions, holdings,
    and P&L calculations.

    Features:
    - Real-time position fetching from Upstox
    - Unrealized and realized P&L calculations
    - Portfolio Greeks aggregation for options
    - Margin utilization tracking
    - Position risk metrics

    Example:
        portfolio = PortfolioService(upstox_client, market_data_service)
        positions = portfolio.get_positions()
        pnl = portfolio.calculate_unrealized_pnl()
        greeks = portfolio.get_portfolio_greeks()
    """

    # Cache TTL (in seconds)
    POSITIONS_TTL = 10
    HOLDINGS_TTL = 60

    def __init__(
        self,
        upstox_client,
        market_data_service: Optional[MarketDataService] = None,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Initialize portfolio service.

        Args:
            upstox_client: UpstoxClient instance for API calls
            market_data_service: Optional MarketDataService for live quotes
            cache_manager: Optional custom cache manager
        """
        self._client = upstox_client
        self._market_data = market_data_service
        self._cache = cache_manager or CacheManager()

        # Store positions locally for quick access
        self._positions_cache: List[Dict] = []
        self._holdings_cache: List[Dict] = []
        self._last_positions_update: Optional[datetime] = None
        self._last_holdings_update: Optional[datetime] = None

    def get_positions(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get current positions from Upstox.

        Args:
            force_refresh: Force API call, bypass cache

        Returns:
            List of position dictionaries
        """
        cache_key = "positions:all"

        # Check cache
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        try:
            df = self._client.get_positions()

            if df.empty:
                self._positions_cache = []
                return []

            positions = []
            for _, row in df.iterrows():
                position = {
                    'instrument': row.get('instrument', ''),
                    'symbol': self._extract_symbol(row.get('instrument', '')),
                    'quantity': int(row.get('quantity', 0)),
                    'average_price': float(row.get('average_price', 0)),
                    'last_price': float(row.get('last_price', 0)),
                    'pnl': float(row.get('pnl', 0)),
                    'product': row.get('product', ''),
                    'direction': 'LONG' if row.get('quantity', 0) > 0 else 'SHORT',
                    'unrealized_pnl': self._calculate_position_pnl(
                        row.get('quantity', 0),
                        row.get('average_price', 0),
                        row.get('last_price', 0)
                    ),
                    'pnl_percent': self._calculate_pnl_percent(
                        row.get('quantity', 0),
                        row.get('average_price', 0),
                        row.get('pnl', 0)
                    ),
                    'updated_at': datetime.now().isoformat()
                }

                # Add options-specific fields
                option_info = self._parse_option_info(row.get('instrument', ''))
                if option_info:
                    position.update(option_info)

                positions.append(position)

            # Cache and store
            self._cache.set(cache_key, positions, self.POSITIONS_TTL)
            self._positions_cache = positions
            self._last_positions_update = datetime.now()

            logger.info(f"Fetched {len(positions)} positions")
            return positions

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            # Return cached data on error
            return self._positions_cache

    def get_holdings(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get holdings from Upstox.

        Args:
            force_refresh: Force API call, bypass cache

        Returns:
            List of holding dictionaries
        """
        cache_key = "holdings:all"

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        try:
            df = self._client.get_holdings()

            if df.empty:
                self._holdings_cache = []
                return []

            holdings = []
            for _, row in df.iterrows():
                holding = {
                    'instrument': row.get('instrument', ''),
                    'symbol': self._extract_symbol(row.get('instrument', '')),
                    'quantity': int(row.get('quantity', 0)),
                    'average_price': float(row.get('average_price', 0)),
                    'last_price': float(row.get('last_price', 0)),
                    'pnl': float(row.get('pnl', 0)),
                    'pnl_percent': self._calculate_pnl_percent(
                        row.get('quantity', 0),
                        row.get('average_price', 0),
                        row.get('pnl', 0)
                    ),
                    'investment_value': (
                        row.get('quantity', 0) * row.get('average_price', 0)
                    ),
                    'current_value': (
                        row.get('quantity', 0) * row.get('last_price', 0)
                    ),
                    'updated_at': datetime.now().isoformat()
                }
                holdings.append(holding)

            self._cache.set(cache_key, holdings, self.HOLDINGS_TTL)
            self._holdings_cache = holdings
            self._last_holdings_update = datetime.now()

            logger.info(f"Fetched {len(holdings)} holdings")
            return holdings

        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return self._holdings_cache

    def calculate_unrealized_pnl(self) -> Dict[str, float]:
        """
        Calculate real-time unrealized P&L.

        Returns:
            Dictionary with unrealized P&L breakdown
        """
        positions = self.get_positions()

        total_pnl = 0.0
        long_pnl = 0.0
        short_pnl = 0.0
        options_pnl = 0.0
        futures_pnl = 0.0

        for pos in positions:
            pnl = pos.get('unrealized_pnl', 0)
            total_pnl += pnl

            if pos.get('direction') == 'LONG':
                long_pnl += pnl
            else:
                short_pnl += pnl

            if pos.get('option_type'):
                options_pnl += pnl
            elif 'FUT' in pos.get('instrument', '').upper():
                futures_pnl += pnl

        return {
            'total': total_pnl,
            'long_positions': long_pnl,
            'short_positions': short_pnl,
            'options': options_pnl,
            'futures': futures_pnl,
            'timestamp': datetime.now().isoformat()
        }

    def calculate_realized_pnl(self, start_date: datetime = None) -> Dict[str, float]:
        """
        Calculate realized P&L from closed positions.

        Note: This requires trade history which may need to be
        fetched from order/trade book.

        Args:
            start_date: Start date for calculation (default: today)

        Returns:
            Dictionary with realized P&L breakdown
        """
        # TODO: Implement trade book integration
        # For now, return placeholder
        return {
            'total': 0.0,
            'winning_trades': 0.0,
            'losing_trades': 0.0,
            'trades_count': 0,
            'timestamp': datetime.now().isoformat(),
            'note': 'Trade book integration pending'
        }

    def get_portfolio_greeks(self) -> Dict[str, float]:
        """
        Calculate aggregated portfolio Greeks for options positions.

        Returns:
            Dictionary with total Delta, Gamma, Theta, Vega
        """
        positions = self.get_positions()

        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0

        options_positions = [p for p in positions if p.get('option_type')]

        for pos in options_positions:
            qty = pos.get('quantity', 0)

            # Greeks should be fetched from option chain or calculated
            # For now, we'll use placeholder values
            # In production, integrate with options/greeks.py
            delta = pos.get('delta', 0.5) * qty
            gamma = pos.get('gamma', 0.01) * qty
            theta = pos.get('theta', -0.05) * qty
            vega = pos.get('vega', 0.1) * qty

            total_delta += delta
            total_gamma += gamma
            total_theta += theta
            total_vega += vega

        return {
            'delta': round(total_delta, 2),
            'gamma': round(total_gamma, 4),
            'theta': round(total_theta, 2),
            'vega': round(total_vega, 2),
            'options_count': len(options_positions),
            'timestamp': datetime.now().isoformat()
        }

    def get_margin_utilization(self) -> Dict[str, Any]:
        """
        Get margin utilization information.

        Returns:
            Dictionary with margin details
        """
        try:
            # Fetch profile for margin info
            profile = self._client.get_profile()

            if profile and 'data' in profile:
                data = profile['data']
                return {
                    'total_margin': data.get('funds', {}).get('commodity', 0) +
                                    data.get('funds', {}).get('equity', 0),
                    'used_margin': data.get('margin_used', 0),
                    'available_margin': data.get('funds', {}).get('available_margin', 0),
                    'utilization_percent': 0,  # Calculate if data available
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error fetching margin info: {e}")

        return {
            'total_margin': 0,
            'used_margin': 0,
            'available_margin': 0,
            'utilization_percent': 0,
            'timestamp': datetime.now().isoformat(),
            'error': 'Failed to fetch margin info'
        }

    def get_position_risks(self, capital: float) -> List[Dict[str, Any]]:
        """
        Calculate risk metrics for each position.

        Args:
            capital: Total trading capital

        Returns:
            List of positions with risk metrics
        """
        positions = self.get_positions()
        results = []

        for pos in positions:
            qty = abs(pos.get('quantity', 0))
            avg_price = pos.get('average_price', 0)
            position_value = qty * avg_price

            # Calculate risk assuming 2% stop loss
            stop_loss_percent = 0.02
            max_loss = position_value * stop_loss_percent

            risk_metrics = {
                **pos,
                'position_value': position_value,
                'capital_allocated_percent': (position_value / capital * 100)
                    if capital > 0 else 0,
                'max_loss_at_2pct_sl': max_loss,
                'risk_percent_of_capital': (max_loss / capital * 100)
                    if capital > 0 else 0
            }

            results.append(risk_metrics)

        return results

    def get_portfolio_summary(self, capital: float = None) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary.

        Args:
            capital: Trading capital (for percentage calculations)

        Returns:
            Dictionary with portfolio summary
        """
        positions = self.get_positions()
        holdings = self.get_holdings()
        unrealized_pnl = self.calculate_unrealized_pnl()
        greeks = self.get_portfolio_greeks()

        total_position_value = sum(
            abs(p.get('quantity', 0)) * p.get('average_price', 0)
            for p in positions
        )

        total_holding_value = sum(
            h.get('current_value', 0) for h in holdings
        )

        return {
            'positions_count': len(positions),
            'holdings_count': len(holdings),
            'total_position_value': total_position_value,
            'total_holding_value': total_holding_value,
            'total_portfolio_value': total_position_value + total_holding_value,
            'unrealized_pnl': unrealized_pnl,
            'portfolio_greeks': greeks,
            'long_positions': len([p for p in positions if p.get('direction') == 'LONG']),
            'short_positions': len([p for p in positions if p.get('direction') == 'SHORT']),
            'options_positions': len([p for p in positions if p.get('option_type')]),
            'capital_utilized_percent': (
                (total_position_value / capital * 100) if capital else 0
            ),
            'last_positions_update': (
                self._last_positions_update.isoformat()
                if self._last_positions_update else None
            ),
            'last_holdings_update': (
                self._last_holdings_update.isoformat()
                if self._last_holdings_update else None
            ),
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_position_pnl(
        self,
        quantity: int,
        avg_price: float,
        current_price: float
    ) -> float:
        """Calculate P&L for a position."""
        if quantity == 0 or avg_price == 0:
            return 0.0

        if quantity > 0:  # Long position
            return (current_price - avg_price) * quantity
        else:  # Short position
            return (avg_price - current_price) * abs(quantity)

    def _calculate_pnl_percent(
        self,
        quantity: int,
        avg_price: float,
        pnl: float
    ) -> float:
        """Calculate P&L percentage."""
        investment = abs(quantity) * avg_price
        if investment == 0:
            return 0.0
        return (pnl / investment) * 100

    def _extract_symbol(self, instrument: str) -> str:
        """Extract symbol from instrument key."""
        if '|' in instrument:
            return instrument.split('|')[-1]
        return instrument

    def _parse_option_info(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Parse option information from instrument key.

        Returns strike, option type, expiry if it's an option.
        """
        instrument_upper = instrument.upper()

        if 'CE' in instrument_upper or 'PE' in instrument_upper:
            # Try to parse option details
            try:
                # Pattern: NIFTY25DEC22000CE
                option_type = 'CE' if 'CE' in instrument_upper else 'PE'

                return {
                    'option_type': option_type,
                    'is_option': True
                }
            except Exception:
                pass

        return None

    def refresh_all(self) -> Dict[str, bool]:
        """
        Force refresh all portfolio data.

        Returns:
            Dictionary with refresh status for each data type
        """
        results = {}

        try:
            self.get_positions(force_refresh=True)
            results['positions'] = True
        except Exception as e:
            logger.error(f"Failed to refresh positions: {e}")
            results['positions'] = False

        try:
            self.get_holdings(force_refresh=True)
            results['holdings'] = True
        except Exception as e:
            logger.error(f"Failed to refresh holdings: {e}")
            results['holdings'] = False

        return results
