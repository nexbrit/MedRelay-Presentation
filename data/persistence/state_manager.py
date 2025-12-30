"""
State Manager for persistent application state.

Handles storage of application settings, capital state,
and other data that needs to survive application restarts.
"""

import sqlite3
import json
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """
    SQLite-based state manager for persistent application state.

    Stores:
    - Capital state (current, initial, history)
    - User settings
    - Application configuration
    - Token state

    Example:
        state = StateManager()
        state.set('last_login', datetime.now().isoformat())
        last_login = state.get('last_login')
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize state manager.

        Args:
            db_path: Path to SQLite database. Defaults to data/persistence/app_state.db
        """
        if db_path is None:
            persistence_dir = Path(__file__).parent
            db_path = str(persistence_dir / 'app_state.db')

        self.db_path = db_path
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=10.0
        )
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Generic key-value state storage
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    type TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            ''')

            # Capital state table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS capital_state (
                    id INTEGER PRIMARY KEY,
                    current_capital REAL NOT NULL,
                    initial_capital REAL NOT NULL,
                    allocated_capital REAL DEFAULT 0,
                    available_capital REAL NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Capital adjustments history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS capital_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    adjustment_type TEXT CHECK(
                        adjustment_type IN (
                            'DEPOSIT', 'WITHDRAWAL', 'MANUAL_ADJUSTMENT',
                            'TRADE_PROFIT', 'TRADE_LOSS', 'INITIAL_SETUP'
                        )
                    ),
                    amount REAL NOT NULL,
                    previous_capital REAL NOT NULL,
                    new_capital REAL NOT NULL,
                    reason TEXT,
                    reference_id TEXT
                )
            ''')

            # Token state table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_state (
                    id INTEGER PRIMARY KEY,
                    access_token TEXT,
                    token_expiry TIMESTAMP,
                    refresh_token TEXT,
                    broker TEXT DEFAULT 'upstox',
                    last_authenticated TIMESTAMP,
                    last_validated TIMESTAMP
                )
            ''')

            # User settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT,
                    updated_at TIMESTAMP NOT NULL
                )
            ''')

            # Trading session state
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_state (
                    id INTEGER PRIMARY KEY,
                    session_date DATE NOT NULL UNIQUE,
                    starting_capital REAL NOT NULL,
                    realized_pnl REAL DEFAULT 0,
                    unrealized_pnl REAL DEFAULT 0,
                    trades_count INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    circuit_breaker_triggered INTEGER DEFAULT 0,
                    session_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Order audit log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_id TEXT,
                    action TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    order_type TEXT,
                    transaction_type TEXT,
                    quantity INTEGER,
                    price REAL,
                    status TEXT,
                    approved_by TEXT,
                    rejection_reason TEXT,
                    details TEXT
                )
            ''')

            # Indices
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_capital_adj_timestamp
                ON capital_adjustments (timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_order_audit_timestamp
                ON order_audit_log (timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_date
                ON session_state (session_date)
            ''')

            conn.commit()
            logger.info(f"State database initialized at {self.db_path}")
        finally:
            conn.close()

    def set(self, key: str, value: Any) -> bool:
        """
        Store a value in app state.

        Args:
            key: State key
            value: Value to store (will be JSON serialized)

        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()

            # Determine type
            value_type = type(value).__name__
            value_json = json.dumps(value, default=str)

            cursor.execute('''
                INSERT OR REPLACE INTO app_state
                (key, value, type, created_at, updated_at)
                VALUES (
                    ?,
                    ?,
                    ?,
                    COALESCE(
                        (SELECT created_at FROM app_state WHERE key = ?),
                        ?
                    ),
                    ?
                )
            ''', (key, value_json, value_type, key, now, now))

            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"State SET error for {key}: {e}")
            return False
        finally:
            conn.close()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from app state.

        Args:
            key: State key
            default: Default value if not found

        Returns:
            Stored value or default
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT value FROM app_state WHERE key = ?',
                (key,)
            )
            row = cursor.fetchone()

            if row:
                return json.loads(row['value'])
            return default
        except sqlite3.Error as e:
            logger.error(f"State GET error for {key}: {e}")
            return default
        finally:
            conn.close()

    def delete(self, key: str) -> bool:
        """Delete a state key."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM app_state WHERE key = ?', (key,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"State DELETE error for {key}: {e}")
            return False
        finally:
            conn.close()

    # Capital Management Methods

    def get_capital_state(self) -> Optional[dict]:
        """Get current capital state."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM capital_state WHERE id = 1')
            row = cursor.fetchone()

            if row:
                return {
                    'current_capital': row['current_capital'],
                    'initial_capital': row['initial_capital'],
                    'allocated_capital': row['allocated_capital'],
                    'available_capital': row['available_capital'],
                    'last_updated': row['last_updated']
                }
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting capital state: {e}")
            return None
        finally:
            conn.close()

    def initialize_capital(
        self,
        initial_capital: float,
        reason: str = "Initial setup"
    ) -> bool:
        """
        Initialize capital for first-time setup.

        Args:
            initial_capital: Starting capital amount
            reason: Reason for initialization

        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()

            # Check if already initialized
            cursor.execute('SELECT id FROM capital_state WHERE id = 1')
            if cursor.fetchone():
                logger.warning("Capital already initialized. Use adjust_capital instead.")
                return False

            # Insert initial capital state
            cursor.execute('''
                INSERT INTO capital_state
                (id, current_capital, initial_capital, allocated_capital,
                 available_capital, last_updated)
                VALUES (1, ?, ?, 0, ?, ?)
            ''', (initial_capital, initial_capital, initial_capital, now))

            # Record in history
            cursor.execute('''
                INSERT INTO capital_adjustments
                (timestamp, adjustment_type, amount, previous_capital,
                 new_capital, reason)
                VALUES (?, 'INITIAL_SETUP', ?, 0, ?, ?)
            ''', (now, initial_capital, initial_capital, reason))

            conn.commit()
            logger.info(f"Capital initialized: {initial_capital}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error initializing capital: {e}")
            return False
        finally:
            conn.close()

    def adjust_capital(
        self,
        amount: float,
        adjustment_type: str,
        reason: str = "",
        reference_id: str = None
    ) -> bool:
        """
        Adjust capital (deposit, withdrawal, or trade P&L).

        Args:
            amount: Adjustment amount (positive or negative)
            adjustment_type: DEPOSIT, WITHDRAWAL, MANUAL_ADJUSTMENT,
                           TRADE_PROFIT, TRADE_LOSS
            reason: Reason for adjustment
            reference_id: Optional reference (e.g., order ID)

        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()

            # Get current capital
            cursor.execute(
                'SELECT current_capital FROM capital_state WHERE id = 1'
            )
            row = cursor.fetchone()

            if not row:
                logger.error("Capital not initialized")
                return False

            previous_capital = row['current_capital']

            # Calculate new capital based on type
            if adjustment_type in ['DEPOSIT', 'TRADE_PROFIT']:
                new_capital = previous_capital + abs(amount)
            elif adjustment_type in ['WITHDRAWAL', 'TRADE_LOSS']:
                new_capital = previous_capital - abs(amount)
            else:  # MANUAL_ADJUSTMENT
                new_capital = previous_capital + amount

            if new_capital < 0:
                logger.error(f"Adjustment would result in negative capital: {new_capital}")
                return False

            # Update capital state
            cursor.execute('''
                UPDATE capital_state
                SET current_capital = ?,
                    available_capital = current_capital - allocated_capital,
                    last_updated = ?
                WHERE id = 1
            ''', (new_capital, now))

            # Record adjustment
            cursor.execute('''
                INSERT INTO capital_adjustments
                (timestamp, adjustment_type, amount, previous_capital,
                 new_capital, reason, reference_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (now, adjustment_type, amount, previous_capital,
                  new_capital, reason, reference_id))

            conn.commit()
            logger.info(
                f"Capital adjusted: {previous_capital} -> {new_capital} "
                f"({adjustment_type}: {amount})"
            )
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adjusting capital: {e}")
            return False
        finally:
            conn.close()

    def get_capital_history(
        self,
        limit: int = 50,
        adjustment_type: str = None
    ) -> list:
        """
        Get capital adjustment history.

        Args:
            limit: Maximum records to return
            adjustment_type: Filter by type (optional)

        Returns:
            List of adjustment records
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if adjustment_type:
                cursor.execute('''
                    SELECT * FROM capital_adjustments
                    WHERE adjustment_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (adjustment_type, limit))
            else:
                cursor.execute('''
                    SELECT * FROM capital_adjustments
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error getting capital history: {e}")
            return []
        finally:
            conn.close()

    # Token Management Methods

    def store_token(
        self,
        access_token: str,
        token_expiry: datetime,
        broker: str = 'upstox'
    ) -> bool:
        """Store authentication token."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()

            cursor.execute('''
                INSERT OR REPLACE INTO token_state
                (id, access_token, token_expiry, broker,
                 last_authenticated, last_validated)
                VALUES (1, ?, ?, ?, ?, ?)
            ''', (access_token, token_expiry, broker, now, now))

            conn.commit()
            logger.info(f"Token stored for {broker}, expires: {token_expiry}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error storing token: {e}")
            return False
        finally:
            conn.close()

    def get_token_state(self) -> Optional[dict]:
        """Get current token state."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM token_state WHERE id = 1')
            row = cursor.fetchone()

            if row:
                return {
                    'access_token': row['access_token'],
                    'token_expiry': row['token_expiry'],
                    'broker': row['broker'],
                    'last_authenticated': row['last_authenticated'],
                    'last_validated': row['last_validated']
                }
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting token state: {e}")
            return None
        finally:
            conn.close()

    # Session State Methods

    def get_or_create_session(self, session_date: datetime = None) -> dict:
        """Get or create trading session for a date."""
        if session_date is None:
            session_date = datetime.now().date()
        elif isinstance(session_date, datetime):
            session_date = session_date.date()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'SELECT * FROM session_state WHERE session_date = ?',
                (session_date,)
            )
            row = cursor.fetchone()

            if row:
                return dict(row)

            # Create new session
            capital_state = self.get_capital_state()
            starting_capital = (
                capital_state['current_capital']
                if capital_state else 0
            )

            cursor.execute('''
                INSERT INTO session_state
                (session_date, starting_capital)
                VALUES (?, ?)
            ''', (session_date, starting_capital))

            conn.commit()

            cursor.execute(
                'SELECT * FROM session_state WHERE session_date = ?',
                (session_date,)
            )
            return dict(cursor.fetchone())
        except sqlite3.Error as e:
            logger.error(f"Error with session state: {e}")
            return {}
        finally:
            conn.close()

    def update_session_pnl(
        self,
        realized_pnl: float,
        unrealized_pnl: float,
        session_date: datetime = None
    ) -> bool:
        """Update session P&L."""
        if session_date is None:
            session_date = datetime.now().date()
        elif isinstance(session_date, datetime):
            session_date = session_date.date()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE session_state
                SET realized_pnl = ?,
                    unrealized_pnl = ?,
                    updated_at = ?
                WHERE session_date = ?
            ''', (realized_pnl, unrealized_pnl, datetime.now(), session_date))

            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating session P&L: {e}")
            return False
        finally:
            conn.close()

    # Order Audit Methods

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
        approved_by: str = None,
        rejection_reason: str = None,
        details: dict = None
    ) -> bool:
        """Log an order action for audit purposes."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO order_audit_log
                (order_id, action, instrument, order_type, transaction_type,
                 quantity, price, status, approved_by, rejection_reason, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_id, action, instrument, order_type, transaction_type,
                quantity, price, status, approved_by, rejection_reason,
                json.dumps(details) if details else None
            ))

            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error logging order action: {e}")
            return False
        finally:
            conn.close()

    def get_order_audit_log(
        self,
        limit: int = 100,
        instrument: str = None
    ) -> list:
        """Get order audit log."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if instrument:
                cursor.execute('''
                    SELECT * FROM order_audit_log
                    WHERE instrument = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (instrument, limit))
            else:
                cursor.execute('''
                    SELECT * FROM order_audit_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error getting audit log: {e}")
            return []
        finally:
            conn.close()

    # User Settings Methods

    def set_setting(
        self,
        key: str,
        value: Any,
        category: str = 'general'
    ) -> bool:
        """Store a user setting."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO user_settings
                (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, json.dumps(value, default=str), category, datetime.now()))

            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error setting {key}: {e}")
            return False
        finally:
            conn.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a user setting."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT value FROM user_settings WHERE key = ?',
                (key,)
            )
            row = cursor.fetchone()

            if row:
                return json.loads(row['value'])
            return default
        except sqlite3.Error as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
        finally:
            conn.close()

    def get_settings_by_category(self, category: str) -> dict:
        """Get all settings in a category."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT key, value FROM user_settings WHERE category = ?',
                (category,)
            )
            rows = cursor.fetchall()
            return {row['key']: json.loads(row['value']) for row in rows}
        except sqlite3.Error as e:
            logger.error(f"Error getting settings for {category}: {e}")
            return {}
        finally:
            conn.close()
