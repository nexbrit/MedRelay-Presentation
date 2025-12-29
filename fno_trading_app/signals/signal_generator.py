"""
Trading Signal Generator
Generates buy/sell signals based on technical indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
from .indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


class SignalGenerator:
    """Generates trading signals from technical indicators"""

    def __init__(self, config: Dict = None):
        """
        Initialize signal generator

        Args:
            config: Configuration dictionary with indicator parameters
        """
        self.config = config or {}
        self.indicators = TechnicalIndicators()

        # Default parameters
        self.rsi_period = self.config.get('rsi_period', 14)
        self.rsi_overbought = self.config.get('rsi_overbought', 70)
        self.rsi_oversold = self.config.get('rsi_oversold', 30)

        self.macd_fast = self.config.get('macd_fast', 12)
        self.macd_slow = self.config.get('macd_slow', 26)
        self.macd_signal = self.config.get('macd_signal', 9)

        self.ema_short = self.config.get('ema_short', 9)
        self.ema_medium = self.config.get('ema_medium', 21)
        self.ema_long = self.config.get('ema_long', 50)

        self.bb_period = self.config.get('bb_period', 20)
        self.bb_std = self.config.get('bb_std', 2.0)

        logger.info("Signal generator initialized with custom config")

    def generate_rsi_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on RSI

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with RSI and signal column
        """
        df = df.copy()
        df['rsi'] = self.indicators.calculate_rsi(df['close'], self.rsi_period)

        # Generate signals
        df['rsi_signal'] = SignalType.HOLD.value

        # Oversold - potential buy
        df.loc[df['rsi'] < self.rsi_oversold, 'rsi_signal'] = SignalType.BUY.value
        # Very oversold - strong buy
        df.loc[df['rsi'] < (self.rsi_oversold - 10), 'rsi_signal'] = SignalType.STRONG_BUY.value

        # Overbought - potential sell
        df.loc[df['rsi'] > self.rsi_overbought, 'rsi_signal'] = SignalType.SELL.value
        # Very overbought - strong sell
        df.loc[df['rsi'] > (self.rsi_overbought + 10), 'rsi_signal'] = SignalType.STRONG_SELL.value

        logger.debug("RSI signals generated")
        return df

    def generate_macd_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on MACD

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with MACD and signal column
        """
        df = df.copy()
        df['macd'], df['macd_signal'], df['macd_hist'] = self.indicators.calculate_macd(
            df['close'], self.macd_fast, self.macd_slow, self.macd_signal
        )

        # Generate signals
        df['macd_crossover'] = SignalType.HOLD.value

        # Bullish crossover - buy signal
        macd_cross_up = (
            (df['macd'] > df['macd_signal']) &
            (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        )
        df.loc[macd_cross_up, 'macd_crossover'] = SignalType.BUY.value

        # Bearish crossover - sell signal
        macd_cross_down = (
            (df['macd'] < df['macd_signal']) &
            (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        )
        df.loc[macd_cross_down, 'macd_crossover'] = SignalType.SELL.value

        logger.debug("MACD signals generated")
        return df

    def generate_ema_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on EMA crossovers

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with EMA and signal column
        """
        df = df.copy()
        df['ema_short'] = self.indicators.calculate_ema(df['close'], self.ema_short)
        df['ema_medium'] = self.indicators.calculate_ema(df['close'], self.ema_medium)
        df['ema_long'] = self.indicators.calculate_ema(df['close'], self.ema_long)

        # Generate signals
        df['ema_signal'] = SignalType.HOLD.value

        # Golden cross - buy signal (short crosses above medium)
        golden_cross = (
            (df['ema_short'] > df['ema_medium']) &
            (df['ema_short'].shift(1) <= df['ema_medium'].shift(1))
        )
        df.loc[golden_cross, 'ema_signal'] = SignalType.BUY.value

        # Death cross - sell signal (short crosses below medium)
        death_cross = (
            (df['ema_short'] < df['ema_medium']) &
            (df['ema_short'].shift(1) >= df['ema_medium'].shift(1))
        )
        df.loc[death_cross, 'ema_signal'] = SignalType.SELL.value

        # Strong trend confirmation
        strong_uptrend = (
            (df['ema_short'] > df['ema_medium']) &
            (df['ema_medium'] > df['ema_long'])
        )
        df.loc[strong_uptrend & golden_cross, 'ema_signal'] = SignalType.STRONG_BUY.value

        strong_downtrend = (
            (df['ema_short'] < df['ema_medium']) &
            (df['ema_medium'] < df['ema_long'])
        )
        df.loc[strong_downtrend & death_cross, 'ema_signal'] = SignalType.STRONG_SELL.value

        logger.debug("EMA signals generated")
        return df

    def generate_bollinger_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on Bollinger Bands

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with Bollinger Bands and signal column
        """
        df = df.copy()
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.indicators.calculate_bollinger_bands(
            df['close'], self.bb_period, self.bb_std
        )

        # Generate signals
        df['bb_signal'] = SignalType.HOLD.value

        # Price touches or breaks lower band - buy signal
        df.loc[df['close'] <= df['bb_lower'], 'bb_signal'] = SignalType.BUY.value

        # Price touches or breaks upper band - sell signal
        df.loc[df['close'] >= df['bb_upper'], 'bb_signal'] = SignalType.SELL.value

        # Price crosses middle band
        price_above_middle = df['close'] > df['bb_middle']
        price_below_middle = df['close'] < df['bb_middle']

        logger.debug("Bollinger Bands signals generated")
        return df

    def generate_supertrend_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on Supertrend indicator

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with Supertrend and signal column
        """
        df = df.copy()
        df['supertrend'], df['supertrend_direction'] = self.indicators.calculate_supertrend(
            df['high'], df['low'], df['close']
        )

        # Generate signals
        df['supertrend_signal'] = SignalType.HOLD.value

        # Trend change from down to up - buy signal
        trend_up = (
            (df['supertrend_direction'] == 1) &
            (df['supertrend_direction'].shift(1) == -1)
        )
        df.loc[trend_up, 'supertrend_signal'] = SignalType.BUY.value

        # Trend change from up to down - sell signal
        trend_down = (
            (df['supertrend_direction'] == -1) &
            (df['supertrend_direction'].shift(1) == 1)
        )
        df.loc[trend_down, 'supertrend_signal'] = SignalType.SELL.value

        logger.debug("Supertrend signals generated")
        return df

    def generate_combined_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate combined signal from multiple indicators

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with all indicators and combined signal
        """
        df = df.copy()

        # Generate individual signals
        df = self.generate_rsi_signal(df)
        df = self.generate_macd_signal(df)
        df = self.generate_ema_signal(df)
        df = self.generate_bollinger_signal(df)
        df = self.generate_supertrend_signal(df)

        # Calculate signal scores
        signal_columns = ['rsi_signal', 'macd_crossover', 'ema_signal', 'bb_signal', 'supertrend_signal']

        def calculate_score(row):
            buy_score = 0
            sell_score = 0

            for col in signal_columns:
                if row[col] == SignalType.BUY.value:
                    buy_score += 1
                elif row[col] == SignalType.STRONG_BUY.value:
                    buy_score += 2
                elif row[col] == SignalType.SELL.value:
                    sell_score += 1
                elif row[col] == SignalType.STRONG_SELL.value:
                    sell_score += 2

            return pd.Series({'buy_score': buy_score, 'sell_score': sell_score})

        df[['buy_score', 'sell_score']] = df.apply(calculate_score, axis=1)

        # Generate combined signal
        df['combined_signal'] = SignalType.HOLD.value

        # Strong buy: 3+ buy signals and no sell signals
        df.loc[(df['buy_score'] >= 3) & (df['sell_score'] == 0), 'combined_signal'] = SignalType.STRONG_BUY.value

        # Buy: 2+ buy signals and minimal sell signals
        df.loc[(df['buy_score'] >= 2) & (df['sell_score'] <= 1), 'combined_signal'] = SignalType.BUY.value

        # Strong sell: 3+ sell signals and no buy signals
        df.loc[(df['sell_score'] >= 3) & (df['buy_score'] == 0), 'combined_signal'] = SignalType.STRONG_SELL.value

        # Sell: 2+ sell signals and minimal buy signals
        df.loc[(df['sell_score'] >= 2) & (df['buy_score'] <= 1), 'combined_signal'] = SignalType.SELL.value

        # Calculate signal strength
        df['signal_strength'] = df.apply(
            lambda row: max(row['buy_score'], row['sell_score']),
            axis=1
        )

        logger.info("Combined signals generated")
        return df

    def get_latest_signal(self, df: pd.DataFrame) -> Dict:
        """
        Get the latest signal with details

        Args:
            df: DataFrame with signals

        Returns:
            Dictionary with signal details
        """
        if df.empty:
            return {'signal': SignalType.HOLD.value, 'strength': 0}

        latest = df.iloc[-1]

        signal_dict = {
            'timestamp': latest.get('timestamp', pd.Timestamp.now()),
            'close': latest.get('close', 0),
            'signal': latest.get('combined_signal', SignalType.HOLD.value),
            'strength': latest.get('signal_strength', 0),
            'buy_score': latest.get('buy_score', 0),
            'sell_score': latest.get('sell_score', 0),
            'indicators': {
                'rsi': latest.get('rsi', 0),
                'rsi_signal': latest.get('rsi_signal', SignalType.HOLD.value),
                'macd': latest.get('macd', 0),
                'macd_signal': latest.get('macd_signal', 0),
                'macd_crossover': latest.get('macd_crossover', SignalType.HOLD.value),
                'ema_signal': latest.get('ema_signal', SignalType.HOLD.value),
                'bb_signal': latest.get('bb_signal', SignalType.HOLD.value),
                'supertrend_signal': latest.get('supertrend_signal', SignalType.HOLD.value)
            }
        }

        logger.info(f"Latest signal: {signal_dict['signal']} (strength: {signal_dict['strength']})")
        return signal_dict
