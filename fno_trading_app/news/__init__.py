"""
News and Economic Calendar module for trading awareness
"""

from .economic_calendar import EconomicCalendar
from .sentiment import SentimentAnalyzer

__all__ = [
    'EconomicCalendar',
    'SentimentAnalyzer',
]
