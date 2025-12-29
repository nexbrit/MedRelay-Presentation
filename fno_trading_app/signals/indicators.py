"""
Technical Indicators Module
Implements various technical indicators for signal generation
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Collection of technical indicators for trading signals"""

    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)

        Args:
            data: Price series (typically close prices)
            period: RSI period (default 14)

        Returns:
            Series with RSI values
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        logger.debug(f"RSI calculated with period {period}")
        return rsi

    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            data: Price series (typically close prices)
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        fast_ema = data.ewm(span=fast_period, adjust=False).mean()
        slow_ema = data.ewm(span=slow_period, adjust=False).mean()

        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        logger.debug(f"MACD calculated with periods {fast_period}/{slow_period}/{signal_period}")
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA)

        Args:
            data: Price series
            period: EMA period

        Returns:
            Series with EMA values
        """
        ema = data.ewm(span=period, adjust=False).mean()
        logger.debug(f"EMA calculated with period {period}")
        return ema

    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA)

        Args:
            data: Price series
            period: SMA period

        Returns:
            Series with SMA values
        """
        sma = data.rolling(window=period).mean()
        logger.debug(f"SMA calculated with period {period}")
        return sma

    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands

        Args:
            data: Price series (typically close prices)
            period: Period for moving average (default 20)
            std_dev: Number of standard deviations (default 2.0)

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        middle_band = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()

        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)

        logger.debug(f"Bollinger Bands calculated with period {period}, std_dev {std_dev}")
        return upper_band, middle_band, lower_band

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range (ATR)

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period (default 14)

        Returns:
            Series with ATR values
        """
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        logger.debug(f"ATR calculated with period {period}")
        return atr

    @staticmethod
    def calculate_stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic Oscillator

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            k_period: %K period (default 14)
            d_period: %D period (default 3)

        Returns:
            Tuple of (%K, %D)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()

        logger.debug(f"Stochastic calculated with periods K={k_period}, D={d_period}")
        return k_percent, d_percent

    @staticmethod
    def calculate_adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average Directional Index (ADX)

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ADX period (default 14)

        Returns:
            Series with ADX values
        """
        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # Calculate ATR
        atr = TechnicalIndicators.calculate_atr(high, low, close, period)

        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        logger.debug(f"ADX calculated with period {period}")
        return adx

    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV)

        Args:
            close: Close prices
            volume: Volume

        Returns:
            Series with OBV values
        """
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        logger.debug("OBV calculated")
        return obv

    @staticmethod
    def calculate_vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume

        Returns:
            Series with VWAP values
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()

        logger.debug("VWAP calculated")
        return vwap

    @staticmethod
    def calculate_supertrend(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 10,
        multiplier: float = 3.0
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Supertrend Indicator

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period (default 10)
            multiplier: ATR multiplier (default 3.0)

        Returns:
            Tuple of (supertrend, trend_direction)
            trend_direction: 1 for uptrend, -1 for downtrend
        """
        atr = TechnicalIndicators.calculate_atr(high, low, close, period)
        hl_avg = (high + low) / 2

        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)

        supertrend = pd.Series(index=close.index, dtype=float)
        direction = pd.Series(index=close.index, dtype=float)

        supertrend.iloc[0] = lower_band.iloc[0]
        direction.iloc[0] = 1

        for i in range(1, len(close)):
            if close.iloc[i] > supertrend.iloc[i - 1]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            elif close.iloc[i] < supertrend.iloc[i - 1]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = supertrend.iloc[i - 1]
                direction.iloc[i] = direction.iloc[i - 1]

        logger.debug(f"Supertrend calculated with period {period}, multiplier {multiplier}")
        return supertrend, direction
