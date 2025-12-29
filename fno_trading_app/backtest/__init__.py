"""
Backtesting Module
Test strategies against historical data with realistic costs and Monte Carlo analysis
"""

from .engine import BacktestEngine, TradingCosts, OrderType, TradeDirection
from .performance import PerformanceMetrics
from .monte_carlo import MonteCarloSimulator

__all__ = [
    'BacktestEngine',
    'TradingCosts',
    'OrderType',
    'TradeDirection',
    'PerformanceMetrics',
    'MonteCarloSimulator'
]
