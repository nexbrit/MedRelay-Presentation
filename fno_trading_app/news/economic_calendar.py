"""
Economic Calendar Integration for NSE/India markets
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from enum import Enum


class EventImportance(Enum):
    """Event importance levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class EconomicCalendar:
    """
    Economic Calendar for tracking important market events

    Tracks:
    - RBI Policy meetings
    - Earnings announcements
    - F&O expiry dates
    - Market holidays
    - Major economic indicators
    """

    def __init__(self):
        """Initialize economic calendar"""
        self.events = []
        self.holidays = []
        self._load_default_events()

    def _load_default_events(self):
        """Load default recurring events"""
        # F&O Expiry - Last Thursday of every month
        self._add_monthly_expiry_events()

        # Common holidays (2024-2025)
        self.holidays = [
            {'date': '2024-01-26', 'event': 'Republic Day'},
            {'date': '2024-03-08', 'event': 'Maha Shivaratri'},
            {'date': '2024-03-25', 'event': 'Holi'},
            {'date': '2024-03-29', 'event': 'Good Friday'},
            {'date': '2024-04-11', 'event': 'Id-Ul-Fitr'},
            {'date': '2024-04-17', 'event': 'Ram Navami'},
            {'date': '2024-04-21', 'event': 'Mahavir Jayanti'},
            {'date': '2024-05-01', 'event': 'Maharashtra Day'},
            {'date': '2024-06-17', 'event': 'Bakri Id'},
            {'date': '2024-07-17', 'event': 'Muharram'},
            {'date': '2024-08-15', 'event': 'Independence Day'},
            {'date': '2024-10-02', 'event': 'Gandhi Jayanti'},
            {'date': '2024-11-01', 'event': 'Diwali Laxmi Pujan'},
            {'date': '2024-11-15', 'event': 'Guru Nanak Jayanti'},
            {'date': '2024-12-25', 'event': 'Christmas'},
            {'date': '2025-01-26', 'event': 'Republic Day'},
        ]

    def _add_monthly_expiry_events(self):
        """Add F&O monthly expiry events (last Thursday of each month)"""
        today = datetime.now()

        for month_offset in range(-1, 13):  # Past month to next 12 months
            # Get first day of target month
            target_date = today.replace(day=1) + timedelta(days=32 * month_offset)
            target_date = target_date.replace(day=1)

            # Find last Thursday
            last_day = (target_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

            # Find last Thursday
            days_until_thursday = (3 - last_day.weekday()) % 7
            if days_until_thursday > 0:
                expiry_date = last_day - timedelta(days=7 - days_until_thursday)
            else:
                expiry_date = last_day

            self.events.append({
                'date': expiry_date.strftime('%Y-%m-%d'),
                'event': 'F&O Monthly Expiry',
                'importance': EventImportance.CRITICAL,
                'category': 'expiry'
            })

    def add_event(
        self,
        date: str,
        event: str,
        importance: EventImportance = EventImportance.MEDIUM,
        category: str = 'custom',
        notes: str = None
    ):
        """
        Add custom event to calendar

        Args:
            date: Event date (YYYY-MM-DD)
            event: Event description
            importance: Event importance level
            category: Event category
            notes: Additional notes
        """
        self.events.append({
            'date': date,
            'event': event,
            'importance': importance,
            'category': category,
            'notes': notes
        })

    def add_rbi_policy_meeting(self, date: str):
        """Add RBI Monetary Policy meeting"""
        self.add_event(
            date=date,
            event='RBI Monetary Policy Meeting',
            importance=EventImportance.CRITICAL,
            category='central_bank'
        )

    def add_earnings_announcement(
        self,
        date: str,
        company: str,
        importance: EventImportance = EventImportance.HIGH
    ):
        """Add earnings announcement"""
        self.add_event(
            date=date,
            event=f'{company} Earnings',
            importance=importance,
            category='earnings'
        )

    def get_upcoming_events(self, days: int = 7) -> pd.DataFrame:
        """
        Get upcoming events for next N days

        Args:
            days: Number of days to look ahead

        Returns:
            DataFrame with upcoming events
        """
        today = datetime.now().date()
        future_date = today + timedelta(days=days)

        upcoming = []

        for event in self.events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            if today <= event_date <= future_date:
                upcoming.append(event)

        if not upcoming:
            return pd.DataFrame()

        df = pd.DataFrame(upcoming)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        return df

    def get_todays_events(self) -> List[Dict]:
        """Get events happening today"""
        today = datetime.now().strftime('%Y-%m-%d')

        todays_events = [
            event for event in self.events
            if event['date'] == today
        ]

        return todays_events

    def is_market_holiday(self, date: str = None) -> bool:
        """
        Check if given date is a market holiday

        Args:
            date: Date to check (YYYY-MM-DD), defaults to today

        Returns:
            True if holiday, False otherwise
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        for holiday in self.holidays:
            if holiday['date'] == date:
                return True

        # Check if weekend
        check_date = datetime.strptime(date, '%Y-%m-%d')
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return True

        return False

    def is_expiry_week(self, date: str = None) -> bool:
        """
        Check if given date is in F&O expiry week

        Args:
            date: Date to check (YYYY-MM-DD), defaults to today

        Returns:
            True if expiry week, False otherwise
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        check_date = datetime.strptime(date, '%Y-%m-%d')

        # Find this month's expiry
        for event in self.events:
            if event.get('category') == 'expiry':
                expiry_date = datetime.strptime(event['date'], '%Y-%m-%d')

                # Check if same month and year
                if (expiry_date.year == check_date.year and
                    expiry_date.month == check_date.month):

                    # Check if within 5 days of expiry
                    days_to_expiry = (expiry_date - check_date).days
                    if 0 <= days_to_expiry <= 5:
                        return True

        return False

    def check_pre_event_warning(
        self,
        hours_before: int = 24
    ) -> List[Dict]:
        """
        Check for important events coming up soon

        Args:
            hours_before: Hours before event to warn

        Returns:
            List of upcoming important events
        """
        now = datetime.now()
        warning_time = now + timedelta(hours=hours_before)

        warnings = []

        for event in self.events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')

            # Check if event is within warning window
            if now <= event_date <= warning_time:
                # Only warn for medium importance or higher
                if event.get('importance', EventImportance.LOW).value >= EventImportance.MEDIUM.value:
                    warnings.append(event)

        return warnings

    def get_position_size_adjustment(self, date: str = None) -> float:
        """
        Get recommended position size adjustment based on upcoming events

        Args:
            date: Date to check (YYYY-MM-DD), defaults to today

        Returns:
            Position size multiplier (0.5 to 1.0)
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # Check for critical events today or tomorrow
        today = datetime.strptime(date, '%Y-%m-%d')
        tomorrow = today + timedelta(days=1)

        critical_soon = False
        high_soon = False

        for event in self.events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')

            if event_date in [today, tomorrow]:
                if event.get('importance') == EventImportance.CRITICAL:
                    critical_soon = True
                elif event.get('importance') == EventImportance.HIGH:
                    high_soon = True

        # Position size adjustments
        if critical_soon:
            return 0.5  # Reduce by 50%
        elif high_soon or self.is_expiry_week(date):
            return 0.75  # Reduce by 25%
        else:
            return 1.0  # No adjustment

    def print_upcoming_events(self, days: int = 7):
        """Print upcoming events in formatted table"""
        df = self.get_upcoming_events(days)

        if df.empty:
            print(f"\nNo events scheduled for next {days} days")
            return

        print(f"\n📅 UPCOMING EVENTS (Next {days} days)")
        print("=" * 70)

        for _, event in df.iterrows():
            importance = event.get('importance', EventImportance.MEDIUM)
            if isinstance(importance, str):
                importance_str = importance
            else:
                importance_str = importance.name

            # Emoji for importance
            emoji = "🔴" if importance_str == "CRITICAL" else \
                    "🟠" if importance_str == "HIGH" else \
                    "🟡" if importance_str == "MEDIUM" else "🟢"

            print(f"{emoji} {event['date'].strftime('%Y-%m-%d')} - {event['event']}")
            if event.get('notes'):
                print(f"   Notes: {event['notes']}")

        print("=" * 70)

    def get_next_expiry_date(self) -> Optional[str]:
        """Get next F&O expiry date"""
        today = datetime.now().date()

        expiry_events = [
            e for e in self.events
            if e.get('category') == 'expiry'
        ]

        future_expiries = [
            e for e in expiry_events
            if datetime.strptime(e['date'], '%Y-%m-%d').date() >= today
        ]

        if not future_expiries:
            return None

        next_expiry = min(
            future_expiries,
            key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d')
        )

        return next_expiry['date']

    def get_days_to_expiry(self) -> Optional[int]:
        """Get number of days until next expiry"""
        next_expiry = self.get_next_expiry_date()

        if not next_expiry:
            return None

        today = datetime.now().date()
        expiry_date = datetime.strptime(next_expiry, '%Y-%m-%d').date()

        return (expiry_date - today).days
