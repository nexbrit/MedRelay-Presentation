"""
Trade Journal Database for tracking all trades and analyzing performance
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd


class TradeJournal:
    """
    Trade journal database for storing and analyzing trading history

    Tracks every trade with detailed metrics including:
    - Entry/Exit prices and times
    - P&L and returns
    - Strategy and market regime
    - Trade quality metrics
    """

    def __init__(self, db_path: str = "data/trade_journal.db"):
        """
        Initialize trade journal database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()

        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                instrument TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity INTEGER NOT NULL,
                pnl REAL,
                pnl_percentage REAL,
                hold_time INTEGER,
                strategy TEXT,
                market_regime TEXT,
                entry_reason TEXT,
                exit_reason TEXT,
                stop_loss REAL,
                target REAL,
                max_favorable_excursion REAL,
                max_adverse_excursion REAL,
                slippage REAL,
                commission REAL,
                notes TEXT,
                status TEXT DEFAULT 'OPEN',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Performance snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                total_pnl REAL,
                win_rate REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                current_capital REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def record_trade_entry(
        self,
        instrument: str,
        direction: str,
        entry_price: float,
        quantity: int,
        strategy: str = None,
        market_regime: str = None,
        entry_reason: str = None,
        stop_loss: float = None,
        target: float = None,
        notes: str = None
    ) -> int:
        """
        Record a new trade entry

        Args:
            instrument: Trading instrument
            direction: LONG or SHORT
            entry_price: Entry price
            quantity: Number of units
            strategy: Strategy name
            market_regime: Current market regime
            entry_reason: Reason for entry
            stop_loss: Stop loss price
            target: Target price
            notes: Additional notes

        Returns:
            trade_id: ID of the recorded trade
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO trades (
                timestamp, instrument, direction, entry_price, quantity,
                strategy, market_regime, entry_reason, stop_loss, target, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(), instrument, direction, entry_price, quantity,
            strategy, market_regime, entry_reason, stop_loss, target, notes
        ))

        self.conn.commit()
        return cursor.lastrowid

    def record_trade_exit(
        self,
        trade_id: int,
        exit_price: float,
        exit_reason: str = None,
        commission: float = 0,
        slippage: float = 0
    ):
        """
        Record trade exit and calculate metrics

        Args:
            trade_id: ID of the trade to close
            exit_price: Exit price
            exit_reason: Reason for exit
            commission: Total commission paid
            slippage: Slippage in points
        """
        cursor = self.conn.cursor()

        # Get trade details
        cursor.execute('SELECT * FROM trades WHERE trade_id = ?', (trade_id,))
        trade = cursor.fetchone()

        if not trade:
            raise ValueError(f"Trade ID {trade_id} not found")

        # Extract trade info (based on column order)
        entry_time = datetime.fromisoformat(trade[1])
        instrument = trade[2]
        direction = trade[3]
        entry_price = trade[4]
        quantity = trade[6]

        # Calculate metrics
        exit_time = datetime.now()
        hold_time = int((exit_time - entry_time).total_seconds() / 60)  # minutes

        # Calculate P&L
        if direction == 'LONG':
            pnl = (exit_price - entry_price) * quantity
            pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl = (entry_price - exit_price) * quantity
            pnl_percentage = ((entry_price - exit_price) / entry_price) * 100

        # Adjust for commission and slippage
        pnl -= commission

        # Update trade record
        cursor.execute('''
            UPDATE trades
            SET exit_price = ?,
                pnl = ?,
                pnl_percentage = ?,
                hold_time = ?,
                exit_reason = ?,
                slippage = ?,
                commission = ?,
                status = 'CLOSED'
            WHERE trade_id = ?
        ''', (
            exit_price, pnl, pnl_percentage, hold_time,
            exit_reason, slippage, commission, trade_id
        ))

        self.conn.commit()

    def get_all_trades(self, status: str = None) -> pd.DataFrame:
        """
        Get all trades as DataFrame

        Args:
            status: Filter by status (OPEN/CLOSED), None for all

        Returns:
            DataFrame with all trades
        """
        query = 'SELECT * FROM trades'
        if status:
            query += f" WHERE status = '{status}'"
        query += ' ORDER BY timestamp DESC'

        return pd.read_sql_query(query, self.conn)

    def get_trade_by_id(self, trade_id: int) -> Dict:
        """
        Get specific trade details

        Args:
            trade_id: Trade ID

        Returns:
            Dictionary with trade details
        """
        df = pd.read_sql_query(
            'SELECT * FROM trades WHERE trade_id = ?',
            self.conn,
            params=(trade_id,)
        )

        if df.empty:
            return {}

        return df.iloc[0].to_dict()

    def get_trades_by_instrument(self, instrument: str) -> pd.DataFrame:
        """Get all trades for a specific instrument"""
        return pd.read_sql_query(
            'SELECT * FROM trades WHERE instrument = ? ORDER BY timestamp DESC',
            self.conn,
            params=(instrument,)
        )

    def get_trades_by_strategy(self, strategy: str) -> pd.DataFrame:
        """Get all trades for a specific strategy"""
        return pd.read_sql_query(
            'SELECT * FROM trades WHERE strategy = ? ORDER BY timestamp DESC',
            self.conn,
            params=(strategy,)
        )

    def get_trades_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Get trades within a date range"""
        return pd.read_sql_query(
            'SELECT * FROM trades WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp',
            self.conn,
            params=(start_date, end_date)
        )

    def get_open_positions(self) -> pd.DataFrame:
        """Get all currently open positions"""
        return pd.read_sql_query(
            "SELECT * FROM trades WHERE status = 'OPEN' ORDER BY timestamp DESC",
            self.conn
        )

    def detect_revenge_trading(self, hours: int = 1) -> List[Dict]:
        """
        Detect potential revenge trading (trading within X hours after a loss)

        Args:
            hours: Time window in hours

        Returns:
            List of potential revenge trades
        """
        query = '''
            SELECT t1.trade_id, t1.timestamp, t1.instrument, t1.pnl,
                   t2.trade_id as prev_trade_id, t2.pnl as prev_pnl,
                   (julianday(t1.timestamp) - julianday(t2.timestamp)) * 24 as hours_gap
            FROM trades t1
            JOIN trades t2 ON t1.trade_id > t2.trade_id
            WHERE t2.pnl < 0
              AND (julianday(t1.timestamp) - julianday(t2.timestamp)) * 24 < ?
              AND t1.status = 'CLOSED'
            ORDER BY t1.timestamp DESC
        '''

        df = pd.read_sql_query(query, self.conn, params=(hours,))
        return df.to_dict('records')

    def get_best_trading_hours(self) -> pd.DataFrame:
        """
        Analyze performance by hour of day

        Returns:
            DataFrame with average P&L by hour
        """
        query = '''
            SELECT
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                COUNT(*) as trade_count,
                AVG(pnl) as avg_pnl,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
            FROM trades
            WHERE status = 'CLOSED' AND pnl IS NOT NULL
            GROUP BY hour
            ORDER BY hour
        '''

        return pd.read_sql_query(query, self.conn)

    def get_weekend_effect(self) -> Dict:
        """
        Analyze Monday performance (potential weekend effect)

        Returns:
            Dictionary with Monday vs other days stats
        """
        query = '''
            SELECT
                CASE
                    WHEN CAST(strftime('%w', timestamp) AS INTEGER) = 1 THEN 'Monday'
                    ELSE 'Other Days'
                END as day_type,
                COUNT(*) as trade_count,
                AVG(pnl) as avg_pnl,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
            FROM trades
            WHERE status = 'CLOSED' AND pnl IS NOT NULL
            GROUP BY day_type
        '''

        df = pd.read_sql_query(query, self.conn)
        return df.set_index('day_type').to_dict('index')

    def save_performance_snapshot(
        self,
        metrics: Dict
    ):
        """
        Save performance snapshot for tracking over time

        Args:
            metrics: Dictionary with performance metrics
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO performance_snapshots (
                timestamp, total_trades, winning_trades, losing_trades,
                total_pnl, win_rate, profit_factor, sharpe_ratio,
                max_drawdown, current_capital
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            metrics.get('total_trades', 0),
            metrics.get('winning_trades', 0),
            metrics.get('losing_trades', 0),
            metrics.get('total_pnl', 0),
            metrics.get('win_rate', 0),
            metrics.get('profit_factor', 0),
            metrics.get('sharpe_ratio', 0),
            metrics.get('max_drawdown', 0),
            metrics.get('current_capital', 0)
        ))

        self.conn.commit()

    def get_performance_history(self, days: int = 30) -> pd.DataFrame:
        """
        Get historical performance snapshots

        Args:
            days: Number of days to look back

        Returns:
            DataFrame with performance history
        """
        query = '''
            SELECT * FROM performance_snapshots
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp
        '''

        return pd.read_sql_query(query, self.conn, params=(days,))

    def close(self):
        """Close database connection"""
        self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
