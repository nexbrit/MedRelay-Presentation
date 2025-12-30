"""
Order Service for order management, tracking, and execution.

Provides order book access, trade history, and order status tracking
with audit logging for compliance.
"""

import time
from datetime import datetime, date
from typing import Any, Optional, List, Dict
from enum import Enum
import logging

from data.cache.cache_manager import CacheManager
from data.persistence.state_manager import StateManager

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TRIGGER_PENDING = "trigger_pending"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class TransactionType(Enum):
    """Transaction type enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class ProductType(Enum):
    """Product type enumeration."""
    DELIVERY = "D"
    INTRADAY = "I"
    MARGIN = "M"


class OrderService:
    """
    Service for order management and execution.

    Features:
    - Order book and trade book access
    - Order status tracking with polling
    - Order history caching
    - Audit logging for all order actions
    - Order validation before execution

    Example:
        orders = OrderService(upstox_client)
        order_book = orders.get_order_book()
        trade_book = orders.get_trade_book()
        status = orders.track_order_status(order_id)
    """

    # Cache TTL
    ORDER_BOOK_TTL = 10
    TRADE_BOOK_TTL = 30

    def __init__(
        self,
        upstox_client,
        cache_manager: Optional[CacheManager] = None,
        state_manager: Optional[StateManager] = None
    ):
        """
        Initialize order service.

        Args:
            upstox_client: UpstoxClient instance for API calls
            cache_manager: Optional custom cache manager
            state_manager: Optional state manager for audit logging
        """
        self._client = upstox_client
        self._cache = cache_manager or CacheManager()
        self._state = state_manager or StateManager()

        # Order tracking
        self._tracked_orders: Dict[str, Dict] = {}
        self._order_history: List[Dict] = []
        self._daily_order_count = 0
        self._daily_order_reset_date = date.today()

    def get_order_book(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get all orders for the day.

        Args:
            force_refresh: Force API call, bypass cache

        Returns:
            List of order dictionaries
        """
        cache_key = "order_book:today"

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        try:
            import upstox_client as upstox_sdk
            api_instance = upstox_sdk.OrderApi(self._client.api_client)
            api_response = api_instance.get_order_book()

            orders = []
            if api_response.data:
                for order in api_response.data:
                    order_dict = {
                        'order_id': order.order_id,
                        'instrument': order.instrument_token,
                        'symbol': self._extract_symbol(order.instrument_token or ''),
                        'transaction_type': order.transaction_type,
                        'order_type': order.order_type,
                        'quantity': order.quantity,
                        'price': order.price,
                        'trigger_price': order.trigger_price,
                        'status': order.status,
                        'filled_quantity': order.filled_quantity,
                        'pending_quantity': order.pending_quantity,
                        'average_price': order.average_price,
                        'order_timestamp': (
                            order.order_timestamp.isoformat()
                            if order.order_timestamp else None
                        ),
                        'exchange_timestamp': (
                            order.exchange_timestamp.isoformat()
                            if order.exchange_timestamp else None
                        ),
                        'product': order.product,
                        'validity': order.validity,
                        'tag': order.tag,
                        'status_message': order.status_message
                    }
                    orders.append(order_dict)

            self._cache.set(cache_key, orders, self.ORDER_BOOK_TTL)
            logger.info(f"Fetched {len(orders)} orders from order book")
            return orders

        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            cached = self._cache.get(cache_key)
            return cached if cached else []

    def get_trade_book(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get executed trades for the day.

        Args:
            force_refresh: Force API call, bypass cache

        Returns:
            List of trade dictionaries
        """
        cache_key = "trade_book:today"

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        try:
            import upstox_client as upstox_sdk
            api_instance = upstox_sdk.OrderApi(self._client.api_client)
            api_response = api_instance.get_trade_history()

            trades = []
            if api_response.data:
                for trade in api_response.data:
                    trade_dict = {
                        'trade_id': trade.trade_id,
                        'order_id': trade.order_id,
                        'instrument': trade.instrument_token,
                        'symbol': self._extract_symbol(trade.instrument_token or ''),
                        'transaction_type': trade.transaction_type,
                        'quantity': trade.quantity,
                        'price': trade.price,
                        'trade_timestamp': (
                            trade.trade_timestamp.isoformat()
                            if trade.trade_timestamp else None
                        ),
                        'product': trade.product
                    }
                    trades.append(trade_dict)

            self._cache.set(cache_key, trades, self.TRADE_BOOK_TTL)
            logger.info(f"Fetched {len(trades)} trades from trade book")
            return trades

        except Exception as e:
            logger.error(f"Error fetching trade book: {e}")
            cached = self._cache.get(cache_key)
            return cached if cached else []

    def track_order_status(
        self,
        order_id: str,
        poll_interval: float = 1.0,
        max_polls: int = 30
    ) -> Dict[str, Any]:
        """
        Track order status until completion or timeout.

        Args:
            order_id: Order ID to track
            poll_interval: Seconds between status checks
            max_polls: Maximum number of status checks

        Returns:
            Final order status dictionary
        """
        logger.info(f"Tracking order {order_id}")

        for i in range(max_polls):
            order_book = self.get_order_book(force_refresh=True)

            for order in order_book:
                if order.get('order_id') == order_id:
                    status = order.get('status', '').upper()

                    # Update tracked orders
                    self._tracked_orders[order_id] = order

                    # Check if terminal state
                    if status in ['COMPLETE', 'REJECTED', 'CANCELLED']:
                        logger.info(f"Order {order_id} reached terminal state: {status}")
                        return order

                    logger.debug(
                        f"Order {order_id} status: {status} "
                        f"(poll {i+1}/{max_polls})"
                    )
                    break

            time.sleep(poll_interval)

        # Return last known state
        return self._tracked_orders.get(order_id, {'order_id': order_id, 'status': 'UNKNOWN'})

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a specific order.

        Args:
            order_id: Order ID to check

        Returns:
            Order dictionary or None if not found
        """
        order_book = self.get_order_book()

        for order in order_book:
            if order.get('order_id') == order_id:
                return order

        return self._tracked_orders.get(order_id)

    def get_order_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get order history from audit log.

        Args:
            limit: Maximum records to return

        Returns:
            List of historical order records
        """
        return self._state.get_order_audit_log(limit=limit)

    def get_today_orders_summary(self) -> Dict[str, Any]:
        """
        Get summary of today's orders.

        Returns:
            Dictionary with order statistics
        """
        order_book = self.get_order_book()
        trade_book = self.get_trade_book()

        total_orders = len(order_book)
        completed_orders = len([o for o in order_book if o.get('status') == 'complete'])
        rejected_orders = len([o for o in order_book if o.get('status') == 'rejected'])
        pending_orders = len([o for o in order_book if o.get('status') in ['open', 'pending', 'trigger_pending']])

        buy_orders = len([o for o in order_book if o.get('transaction_type') == 'BUY'])
        sell_orders = len([o for o in order_book if o.get('transaction_type') == 'SELL'])

        total_trades = len(trade_book)
        total_traded_value = sum(
            (t.get('quantity', 0) or 0) * (t.get('price', 0) or 0)
            for t in trade_book
        )

        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'rejected_orders': rejected_orders,
            'pending_orders': pending_orders,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'total_trades': total_trades,
            'total_traded_value': total_traded_value,
            'success_rate': (
                completed_orders / total_orders * 100
                if total_orders > 0 else 0
            ),
            'timestamp': datetime.now().isoformat()
        }

    def get_daily_order_count(self) -> int:
        """
        Get count of orders placed today.

        Returns:
            Number of orders placed today
        """
        # Reset counter if new day
        if date.today() != self._daily_order_reset_date:
            self._daily_order_count = 0
            self._daily_order_reset_date = date.today()

        return self._daily_order_count

    def increment_order_count(self) -> None:
        """Increment daily order count."""
        if date.today() != self._daily_order_reset_date:
            self._daily_order_count = 0
            self._daily_order_reset_date = date.today()

        self._daily_order_count += 1

    def log_order_action(
        self,
        action: str,
        instrument: str,
        order_id: str = None,
        order_type: str = None,
        transaction_type: str = None,
        quantity: int = None,
        price: float = None,
        status: str = None,
        approved_by: str = 'USER',
        rejection_reason: str = None,
        details: Dict = None
    ) -> bool:
        """
        Log an order action for audit purposes.

        Args:
            action: Action type (PLACE, MODIFY, CANCEL, EXECUTE, REJECT)
            instrument: Instrument key
            order_id: Order ID if available
            order_type: Order type (MARKET, LIMIT, etc.)
            transaction_type: BUY or SELL
            quantity: Order quantity
            price: Order price
            status: Order status
            approved_by: Who approved (USER, SYSTEM, AUTO)
            rejection_reason: Reason if rejected
            details: Additional details

        Returns:
            True if logged successfully
        """
        return self._state.log_order_action(
            action=action,
            instrument=instrument,
            order_id=order_id,
            order_type=order_type,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            status=status,
            approved_by=approved_by,
            rejection_reason=rejection_reason,
            details=details
        )

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Get all pending/open orders.

        Returns:
            List of pending order dictionaries
        """
        order_book = self.get_order_book()
        pending_statuses = ['open', 'pending', 'trigger_pending']

        return [
            order for order in order_book
            if order.get('status', '').lower() in pending_statuses
        ]

    def get_orders_by_instrument(
        self,
        instrument: str
    ) -> List[Dict[str, Any]]:
        """
        Get all orders for a specific instrument.

        Args:
            instrument: Instrument key to filter by

        Returns:
            List of order dictionaries for the instrument
        """
        order_book = self.get_order_book()
        return [
            order for order in order_book
            if order.get('instrument') == instrument
        ]

    def get_trades_by_order(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get trades associated with a specific order.

        Args:
            order_id: Order ID to filter by

        Returns:
            List of trade dictionaries for the order
        """
        trade_book = self.get_trade_book()
        return [
            trade for trade in trade_book
            if trade.get('order_id') == order_id
        ]

    def _extract_symbol(self, instrument: str) -> str:
        """Extract symbol from instrument key."""
        if '|' in instrument:
            return instrument.split('|')[-1]
        return instrument

    def refresh_all(self) -> Dict[str, bool]:
        """
        Force refresh all order data.

        Returns:
            Dictionary with refresh status
        """
        results = {}

        try:
            self.get_order_book(force_refresh=True)
            results['order_book'] = True
        except Exception as e:
            logger.error(f"Failed to refresh order book: {e}")
            results['order_book'] = False

        try:
            self.get_trade_book(force_refresh=True)
            results['trade_book'] = True
        except Exception as e:
            logger.error(f"Failed to refresh trade book: {e}")
            results['trade_book'] = False

        return results
