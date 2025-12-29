"""
Orders Module
Advanced order types for professional F&O trading
"""

from .bracket_order import BracketOrder, OrderStatus, create_bracket_order_from_signal
from .trailing_stop import TrailingStop, TrailingStopType, create_trailing_stop_from_position
from .oco_order import OCOOrder, OCOStatus, create_oco_from_range, create_oco_from_current_price
from .iceberg_order import IcebergOrder, IcebergStatus, create_iceberg_from_position_size

__all__ = [
    # Bracket Orders
    'BracketOrder',
    'OrderStatus',
    'create_bracket_order_from_signal',

    # Trailing Stops
    'TrailingStop',
    'TrailingStopType',
    'create_trailing_stop_from_position',

    # OCO Orders
    'OCOOrder',
    'OCOStatus',
    'create_oco_from_range',
    'create_oco_from_current_price',

    # Iceberg Orders
    'IcebergOrder',
    'IcebergStatus',
    'create_iceberg_from_position_size'
]
