"""
Backtesting Engine
Test strategies against historical data with realistic cost modeling
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional, Tuple
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class TradeDirection(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"


class TradingCosts:
    """
    Calculate realistic trading costs for Indian F&O markets
    """

    def __init__(
        self,
        brokerage_per_order: float = 20.0,  # Flat ₹20 per order
        brokerage_percent: float = 0.05,  # Or 0.05% whichever is lower
        stt_percent: float = 0.05,  # 0.05% on sell side for options
        exchange_charges: float = 0.0035,  # 0.0035%
        gst_percent: float = 18.0,  # 18% GST on brokerage + exchange
        sebi_charges: float = 10.0,  # ₹10 per crore
        stamp_duty: float = 0.003  # 0.003% on buy side
    ):
        """
        Initialize trading costs calculator

        Args:
            brokerage_per_order: Flat brokerage per order
            brokerage_percent: Percentage brokerage (whichever is lower)
            stt_percent: STT percentage (on sell side for options)
            exchange_charges: Exchange charges percentage
            gst_percent: GST on brokerage and exchange charges
            sebi_charges: SEBI charges (₹10 per crore)
            stamp_duty: Stamp duty on buy side
        """
        self.brokerage_per_order = brokerage_per_order
        self.brokerage_percent = brokerage_percent
        self.stt_percent = stt_percent
        self.exchange_charges = exchange_charges
        self.gst_percent = gst_percent
        self.sebi_charges = sebi_charges
        self.stamp_duty = stamp_duty

    def calculate_brokerage(self, turnover: float) -> float:
        """Calculate brokerage (whichever is lower: flat or percentage)"""
        percent_brokerage = turnover * (self.brokerage_percent / 100)
        return min(self.brokerage_per_order, percent_brokerage)

    def calculate_total_costs(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int,
        lot_size: int,
        is_option: bool = True
    ) -> Dict[str, float]:
        """
        Calculate all trading costs for a round trip (entry + exit)

        Args:
            entry_price: Entry price per unit
            exit_price: Exit price per unit
            quantity: Number of lots
            lot_size: Lot size per contract
            is_option: Whether trading options (affects STT)

        Returns:
            Dictionary with cost breakdown
        """
        total_quantity = quantity * lot_size

        # Turnover
        entry_turnover = entry_price * total_quantity
        exit_turnover = exit_price * total_quantity
        total_turnover = entry_turnover + exit_turnover

        # Brokerage (both sides)
        entry_brokerage = self.calculate_brokerage(entry_turnover)
        exit_brokerage = self.calculate_brokerage(exit_turnover)
        total_brokerage = entry_brokerage + exit_brokerage

        # STT (only on sell side for options, both sides for futures)
        if is_option:
            stt = exit_turnover * (self.stt_percent / 100)
        else:
            stt = total_turnover * (self.stt_percent / 100)

        # Exchange charges
        exchange_charges = total_turnover * (self.exchange_charges / 100)

        # GST (on brokerage + exchange charges)
        gst_base = total_brokerage + exchange_charges
        gst = gst_base * (self.gst_percent / 100)

        # SEBI charges (₹10 per crore)
        sebi = (total_turnover / 10000000) * self.sebi_charges

        # Stamp duty (on buy side only)
        stamp_duty = entry_turnover * (self.stamp_duty / 100)

        # Total costs
        total_costs = total_brokerage + stt + exchange_charges + gst + sebi + stamp_duty

        return {
            'entry_turnover': entry_turnover,
            'exit_turnover': exit_turnover,
            'total_turnover': total_turnover,
            'brokerage': total_brokerage,
            'stt': stt,
            'exchange_charges': exchange_charges,
            'gst': gst,
            'sebi': sebi,
            'stamp_duty': stamp_duty,
            'total_costs': total_costs,
            'cost_percent': (total_costs / total_turnover) * 100
        }

    def calculate_slippage(
        self,
        price: float,
        order_type: OrderType,
        volatility_factor: float = 1.0
    ) -> float:
        """
        Estimate slippage based on order type and market volatility

        Args:
            price: Price per unit
            order_type: Order type (MARKET has more slippage)
            volatility_factor: Multiplier for volatile periods

        Returns:
            Slippage amount per unit
        """
        base_slippage_bps = {
            OrderType.MARKET: 5,  # 0.05% = 5 basis points
            OrderType.LIMIT: 0,    # No slippage for limit orders (might not fill though)
            OrderType.STOP: 10     # Higher slippage for stop orders
        }

        slippage_bps = base_slippage_bps.get(order_type, 5)
        slippage = price * (slippage_bps / 10000) * volatility_factor

        return slippage


class BacktestEngine:
    """
    Core backtesting engine with realistic execution and costs
    """

    def __init__(
        self,
        initial_capital: float,
        lot_size: int = 50,
        trading_costs: Optional[TradingCosts] = None,
        enable_slippage: bool = True
    ):
        """
        Initialize backtesting engine

        Args:
            initial_capital: Starting capital
            lot_size: Contract lot size
            trading_costs: TradingCosts instance (uses default if None)
            enable_slippage: Whether to simulate slippage
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.lot_size = lot_size
        self.trading_costs = trading_costs or TradingCosts()
        self.enable_slippage = enable_slippage

        # Trading state
        self.positions = []
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        logger.info(
            f"Backtest engine initialized: Capital=₹{initial_capital:,.2f}, "
            f"Lot Size={lot_size}"
        )

    def enter_position(
        self,
        timestamp: datetime,
        instrument: str,
        direction: TradeDirection,
        entry_price: float,
        quantity: int,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET,
        strategy: str = "unknown"
    ) -> Dict:
        """
        Enter a new position

        Args:
            timestamp: Entry timestamp
            instrument: Instrument name
            direction: LONG or SHORT
            entry_price: Entry price
            quantity: Number of lots
            stop_loss: Stop loss price (optional)
            target: Target price (optional)
            order_type: Order type
            strategy: Strategy name

        Returns:
            Position dictionary
        """
        # Apply slippage if enabled
        if self.enable_slippage:
            slippage = self.trading_costs.calculate_slippage(entry_price, order_type)
            if direction == TradeDirection.LONG:
                entry_price += slippage  # Pay higher when buying
            else:
                entry_price -= slippage  # Get lower when shorting

        position = {
            'entry_timestamp': timestamp,
            'instrument': instrument,
            'direction': direction,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'target': target,
            'strategy': strategy,
            'status': 'OPEN'
        }

        self.positions.append(position)

        logger.debug(
            f"Entered {direction.value} position: {instrument} @ ₹{entry_price:.2f}, "
            f"Qty: {quantity} lots"
        )

        return position

    def exit_position(
        self,
        position: Dict,
        timestamp: datetime,
        exit_price: float,
        exit_reason: str = "SIGNAL",
        order_type: OrderType = OrderType.MARKET
    ) -> Dict:
        """
        Exit an existing position

        Args:
            position: Position dictionary
            timestamp: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit (SIGNAL, STOP_LOSS, TARGET, etc.)
            order_type: Order type

        Returns:
            Completed trade dictionary
        """
        # Apply slippage
        if self.enable_slippage:
            slippage = self.trading_costs.calculate_slippage(exit_price, order_type)
            if position['direction'] == TradeDirection.LONG:
                exit_price -= slippage  # Get lower when selling
            else:
                exit_price += slippage  # Pay higher when covering short

        # Calculate gross P&L
        entry_price = position['entry_price']
        quantity = position['quantity']
        total_quantity = quantity * self.lot_size

        if position['direction'] == TradeDirection.LONG:
            gross_pnl = (exit_price - entry_price) * total_quantity
        else:
            gross_pnl = (entry_price - exit_price) * total_quantity

        # Calculate costs
        costs_breakdown = self.trading_costs.calculate_total_costs(
            entry_price, exit_price, quantity, self.lot_size
        )

        # Net P&L
        net_pnl = gross_pnl - costs_breakdown['total_costs']

        # Update capital
        self.capital += net_pnl

        # Hold time
        hold_time = (timestamp - position['entry_timestamp']).total_seconds() / 3600  # hours

        # Create trade record
        trade = {
            **position,
            'exit_timestamp': timestamp,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'hold_time_hours': hold_time,
            'gross_pnl': gross_pnl,
            'costs': costs_breakdown['total_costs'],
            'net_pnl': net_pnl,
            'pnl_percent': (net_pnl / self.capital) * 100,
            'return_on_risk': (net_pnl / (abs(entry_price - position.get('stop_loss', entry_price)) *
                                          total_quantity)) if position.get('stop_loss') else 0,
            'status': 'CLOSED'
        }

        self.trades.append(trade)
        self.total_trades += 1

        if net_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Remove from open positions
        position['status'] = 'CLOSED'

        logger.debug(
            f"Exited {position['direction'].value} position: {position['instrument']} "
            f"@ ₹{exit_price:.2f}, Net P&L: ₹{net_pnl:,.2f} ({exit_reason})"
        )

        return trade

    def update_equity_curve(self, timestamp: datetime):
        """Update equity curve with current capital"""
        self.equity_curve.append({
            'timestamp': timestamp,
            'capital': self.capital,
            'drawdown': self.calculate_current_drawdown()
        })

    def calculate_current_drawdown(self) -> float:
        """Calculate current drawdown from peak"""
        if not self.equity_curve:
            return 0.0

        peak = max(ec['capital'] for ec in self.equity_curve)
        current = self.capital
        drawdown = ((peak - current) / peak) * 100 if peak > 0 else 0.0

        return drawdown

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_function: Callable,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Run backtest on historical data

        Args:
            data: Historical OHLCV data (DataFrame with timestamp index)
            strategy_function: Function that generates signals
                               signature: f(data_row, current_positions) -> signal
            start_date: Start date for backtest (uses all data if None)
            end_date: End date for backtest (uses all data if None)

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")

        # Filter data by date range
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]

        if len(data) == 0:
            logger.error("No data available for backtest")
            return {}

        # Run through historical data
        for timestamp, row in data.iterrows():
            # Get current open positions
            open_positions = [p for p in self.positions if p['status'] == 'OPEN']

            # Check stop loss and target for open positions
            for position in open_positions:
                # Stop loss check
                if position.get('stop_loss'):
                    if position['direction'] == TradeDirection.LONG:
                        if row['low'] <= position['stop_loss']:
                            self.exit_position(
                                position, timestamp,
                                position['stop_loss'],
                                exit_reason='STOP_LOSS'
                            )
                            continue
                    else:  # SHORT
                        if row['high'] >= position['stop_loss']:
                            self.exit_position(
                                position, timestamp,
                                position['stop_loss'],
                                exit_reason='STOP_LOSS'
                            )
                            continue

                # Target check
                if position.get('target'):
                    if position['direction'] == TradeDirection.LONG:
                        if row['high'] >= position['target']:
                            self.exit_position(
                                position, timestamp,
                                position['target'],
                                exit_reason='TARGET'
                            )
                            continue
                    else:  # SHORT
                        if row['low'] <= position['target']:
                            self.exit_position(
                                position, timestamp,
                                position['target'],
                                exit_reason='TARGET'
                            )
                            continue

            # Get signal from strategy
            signal = strategy_function(row, open_positions)

            # Execute signal
            if signal and signal.get('action'):
                action = signal['action']

                if action == 'BUY' and len(open_positions) == 0:
                    self.enter_position(
                        timestamp=timestamp,
                        instrument=signal.get('instrument', 'UNKNOWN'),
                        direction=TradeDirection.LONG,
                        entry_price=row['close'],
                        quantity=signal.get('quantity', 1),
                        stop_loss=signal.get('stop_loss'),
                        target=signal.get('target'),
                        strategy=signal.get('strategy', 'unknown')
                    )

                elif action == 'SELL' and len(open_positions) > 0:
                    for position in open_positions:
                        if position['direction'] == TradeDirection.LONG:
                            self.exit_position(
                                position, timestamp,
                                row['close'],
                                exit_reason='SIGNAL'
                            )

                elif action == 'SHORT' and len(open_positions) == 0:
                    self.enter_position(
                        timestamp=timestamp,
                        instrument=signal.get('instrument', 'UNKNOWN'),
                        direction=TradeDirection.SHORT,
                        entry_price=row['close'],
                        quantity=signal.get('quantity', 1),
                        stop_loss=signal.get('stop_loss'),
                        target=signal.get('target'),
                        strategy=signal.get('strategy', 'unknown')
                    )

                elif action == 'COVER' and len(open_positions) > 0:
                    for position in open_positions:
                        if position['direction'] == TradeDirection.SHORT:
                            self.exit_position(
                                position, timestamp,
                                row['close'],
                                exit_reason='SIGNAL'
                            )

            # Update equity curve
            self.update_equity_curve(timestamp)

        # Close any remaining open positions at last price
        for position in [p for p in self.positions if p['status'] == 'OPEN']:
            last_price = data.iloc[-1]['close']
            self.exit_position(
                position,
                data.index[-1],
                last_price,
                exit_reason='BACKTEST_END'
            )

        logger.info(f"Backtest completed: {self.total_trades} trades executed")

        return self.get_results()

    def get_results(self) -> Dict:
        """
        Get backtest results and statistics

        Returns:
            Dictionary with comprehensive results
        """
        if not self.trades:
            return {'error': 'No trades executed'}

        trades_df = pd.DataFrame(self.trades)

        # Basic statistics
        total_pnl = trades_df['net_pnl'].sum()
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        winning_trades = trades_df[trades_df['net_pnl'] > 0]
        losing_trades = trades_df[trades_df['net_pnl'] < 0]

        win_rate = (len(winning_trades) / len(trades_df)) * 100 if len(trades_df) > 0 else 0

        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0

        # Profit factor
        gross_profit = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Expectancy
        expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)

        # Max drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        max_drawdown = equity_df['drawdown'].max()

        # Largest win/loss
        largest_win = winning_trades['net_pnl'].max() if len(winning_trades) > 0 else 0
        largest_loss = losing_trades['net_pnl'].min() if len(losing_trades) > 0 else 0

        # Average hold time
        avg_hold_time = trades_df['hold_time_hours'].mean()

        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_pnl': total_pnl,
            'total_return_percent': total_return,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'max_drawdown': max_drawdown,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_hold_time_hours': avg_hold_time,
            'total_costs': trades_df['costs'].sum(),
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }

        return results

    def get_trades_dataframe(self) -> pd.DataFrame:
        """Get all trades as a DataFrame"""
        return pd.DataFrame(self.trades)

    def get_equity_curve_dataframe(self) -> pd.DataFrame:
        """Get equity curve as a DataFrame"""
        return pd.DataFrame(self.equity_curve)
