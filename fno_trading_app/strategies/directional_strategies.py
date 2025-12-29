"""
Directional Trading Strategies for F&O
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class TrendType(Enum):
    """Trend types"""
    STRONG_UPTREND = "strong_uptrend"
    WEAK_UPTREND = "weak_uptrend"
    STRONG_DOWNTREND = "strong_downtrend"
    WEAK_DOWNTREND = "weak_downtrend"
    RANGING = "ranging"


class DirectionalStrategies:
    """
    Directional trading strategies for trending markets

    Strategies:
    - Trend following with Supertrend
    - Breakout trading with volume
    - Mean reversion with Bollinger Bands
    - Opening range breakout
    - Support/Resistance bounces
    """

    def __init__(self):
        """Initialize directional strategies"""
        pass

    def supertrend_strategy(
        self,
        df: pd.DataFrame,
        multiplier: float = 3.0,
        period: int = 10
    ) -> Dict:
        """
        Trend following strategy using Supertrend indicator

        Args:
            df: DataFrame with OHLC data
            multiplier: ATR multiplier
            period: Lookback period

        Returns:
            Strategy signals
        """
        if df.empty or len(df) < period:
            return {'signal': 'HOLD', 'reason': 'Insufficient data'}

        # Get latest values
        latest = df.iloc[-1]

        if 'supertrend' not in df.columns:
            return {'signal': 'HOLD', 'reason': 'Supertrend not calculated'}

        close = latest['close']
        supertrend = latest['supertrend']
        trend = latest.get('supertrend_trend', 0)

        # Generate signal
        if trend == 1:  # Uptrend
            signal = 'BUY'
            entry = close
            stop_loss = supertrend
            # Target: 2x risk
            target = entry + 2 * (entry - stop_loss)
            reason = f"Supertrend Uptrend confirmed. Price {close:.2f} above ST {supertrend:.2f}"

        elif trend == -1:  # Downtrend
            signal = 'SELL'
            entry = close
            stop_loss = supertrend
            # Target: 2x risk
            target = entry - 2 * (stop_loss - entry)
            reason = f"Supertrend Downtrend confirmed. Price {close:.2f} below ST {supertrend:.2f}"

        else:
            signal = 'HOLD'
            entry = None
            stop_loss = None
            target = None
            reason = "No clear trend"

        return {
            'strategy': 'Supertrend Trend Following',
            'signal': signal,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'target': target,
            'risk_reward': 2.0,
            'reason': reason
        }

    def breakout_strategy(
        self,
        df: pd.DataFrame,
        lookback: int = 20,
        volume_threshold: float = 1.5
    ) -> Dict:
        """
        Breakout strategy with volume confirmation

        Args:
            df: DataFrame with OHLC and volume data
            lookback: Lookback period for high/low
            volume_threshold: Volume surge multiplier

        Returns:
            Strategy signals
        """
        if df.empty or len(df) < lookback + 1:
            return {'signal': 'HOLD', 'reason': 'Insufficient data'}

        latest = df.iloc[-1]
        previous_data = df.iloc[-(lookback+1):-1]

        # Calculate resistance and support
        resistance = previous_data['high'].max()
        support = previous_data['low'].min()

        close = latest['close']
        volume = latest.get('volume', 0)
        avg_volume = previous_data.get('volume', pd.Series([0])).mean()

        # Volume confirmation
        volume_surge = volume / avg_volume if avg_volume > 0 else 0

        # Breakout signals
        if close > resistance and volume_surge >= volume_threshold:
            signal = 'BUY'
            entry = close
            stop_loss = resistance - (resistance - support) * 0.1  # 10% below resistance
            target = entry + (entry - stop_loss) * 2
            reason = f"Breakout above {resistance:.2f} with {volume_surge:.1f}x volume"

        elif close < support and volume_surge >= volume_threshold:
            signal = 'SELL'
            entry = close
            stop_loss = support + (resistance - support) * 0.1  # 10% above support
            target = entry - (stop_loss - entry) * 2
            reason = f"Breakdown below {support:.2f} with {volume_surge:.1f}x volume"

        else:
            signal = 'HOLD'
            entry = None
            stop_loss = None
            target = None
            reason = f"Price in range [{support:.2f}, {resistance:.2f}]. Wait for breakout."

        return {
            'strategy': 'Breakout with Volume',
            'signal': signal,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'target': target,
            'support': support,
            'resistance': resistance,
            'volume_surge': round(volume_surge, 2),
            'reason': reason
        }

    def mean_reversion_strategy(
        self,
        df: pd.DataFrame,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14
    ) -> Dict:
        """
        Mean reversion using Bollinger Bands and RSI

        Best for ranging markets

        Args:
            df: DataFrame with OHLC data
            bb_period: Bollinger Band period
            bb_std: Standard deviation
            rsi_period: RSI period

        Returns:
            Strategy signals
        """
        if df.empty or len(df) < max(bb_period, rsi_period):
            return {'signal': 'HOLD', 'reason': 'Insufficient data'}

        latest = df.iloc[-1]

        close = latest['close']
        bb_upper = latest.get('bb_upper')
        bb_lower = latest.get('bb_lower')
        bb_middle = latest.get('bb_middle')
        rsi = latest.get('rsi')

        if bb_upper is None or bb_lower is None or rsi is None:
            return {'signal': 'HOLD', 'reason': 'Indicators not calculated'}

        # Mean reversion signals
        if close <= bb_lower and rsi <= 30:
            signal = 'BUY'
            entry = close
            stop_loss = bb_lower - (bb_middle - bb_lower) * 0.5
            target = bb_middle
            reason = f"Oversold: Price at lower BB ({bb_lower:.2f}), RSI {rsi:.1f}"

        elif close >= bb_upper and rsi >= 70:
            signal = 'SELL'
            entry = close
            stop_loss = bb_upper + (bb_upper - bb_middle) * 0.5
            target = bb_middle
            reason = f"Overbought: Price at upper BB ({bb_upper:.2f}), RSI {rsi:.1f}"

        else:
            signal = 'HOLD'
            entry = None
            stop_loss = None
            target = None
            reason = f"Price in normal range. BB: [{bb_lower:.2f}, {bb_upper:.2f}], RSI: {rsi:.1f}"

        return {
            'strategy': 'Mean Reversion (BB + RSI)',
            'signal': signal,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'target': target,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'rsi': rsi,
            'reason': reason
        }

    def opening_range_breakout(
        self,
        df: pd.DataFrame,
        or_minutes: int = 15
    ) -> Dict:
        """
        Opening range breakout strategy

        Trade breakouts of first X minutes range

        Args:
            df: Intraday DataFrame with timestamp
            or_minutes: Opening range minutes (default: 15)

        Returns:
            Strategy signals
        """
        if df.empty:
            return {'signal': 'HOLD', 'reason': 'No data'}

        # Ensure timestamp column
        if 'timestamp' not in df.columns:
            return {'signal': 'HOLD', 'reason': 'Timestamp required for ORB'}

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Get today's data
        today = df['timestamp'].max().date()
        today_data = df[df['timestamp'].dt.date == today].copy()

        if today_data.empty:
            return {'signal': 'HOLD', 'reason': 'No data for today'}

        # Market open time (9:15 AM IST)
        market_open = pd.Timestamp(today).replace(hour=9, minute=15)
        or_end = market_open + pd.Timedelta(minutes=or_minutes)

        # Opening range
        or_data = today_data[
            (today_data['timestamp'] >= market_open) &
            (today_data['timestamp'] <= or_end)
        ]

        if or_data.empty:
            return {'signal': 'HOLD', 'reason': 'Opening range data not available'}

        or_high = or_data['high'].max()
        or_low = or_data['low'].min()
        or_range = or_high - or_low

        # Current price
        latest = today_data.iloc[-1]
        current_price = latest['close']
        current_time = latest['timestamp']

        # Only trade after opening range
        if current_time <= or_end:
            return {
                'signal': 'HOLD',
                'reason': f'Wait for opening range to complete. OR: [{or_low:.2f}, {or_high:.2f}]',
                'or_high': or_high,
                'or_low': or_low
            }

        # Breakout signals
        if current_price > or_high:
            signal = 'BUY'
            entry = current_price
            stop_loss = or_low
            target = entry + or_range  # Target = OR range
            reason = f"Breakout above OR high {or_high:.2f}"

        elif current_price < or_low:
            signal = 'SELL'
            entry = current_price
            stop_loss = or_high
            target = entry - or_range
            reason = f"Breakdown below OR low {or_low:.2f}"

        else:
            signal = 'HOLD'
            entry = None
            stop_loss = None
            target = None
            reason = f"Price in OR range [{or_low:.2f}, {or_high:.2f}]"

        return {
            'strategy': f'Opening Range Breakout ({or_minutes}min)',
            'signal': signal,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'target': target,
            'or_high': or_high,
            'or_low': or_low,
            'or_range': or_range,
            'reason': reason
        }

    def support_resistance_bounce(
        self,
        df: pd.DataFrame,
        lookback: int = 50
    ) -> Dict:
        """
        Trade bounces off support/resistance levels

        Args:
            df: DataFrame with OHLC data
            lookback: Lookback period for S/R

        Returns:
            Strategy signals
        """
        if df.empty or len(df) < lookback:
            return {'signal': 'HOLD', 'reason': 'Insufficient data'}

        # Identify support and resistance
        recent_data = df.iloc[-lookback:]

        # Simple S/R: recent highs and lows
        resistance_levels = self._find_resistance_levels(recent_data)
        support_levels = self._find_support_levels(recent_data)

        latest = df.iloc[-1]
        close = latest['close']

        # Check for bounce signals
        bounce_signal = None
        level = None

        # Support bounce
        for support in support_levels:
            if abs(close - support) / support < 0.005:  # Within 0.5%
                bounce_signal = 'BUY'
                level = support
                break

        # Resistance bounce
        if bounce_signal is None:
            for resistance in resistance_levels:
                if abs(close - resistance) / resistance < 0.005:  # Within 0.5%
                    bounce_signal = 'SELL'
                    level = resistance
                    break

        if bounce_signal == 'BUY':
            entry = close
            stop_loss = level - (level * 0.01)  # 1% below support
            # Target: nearest resistance or 2:1 R:R
            nearest_resistance = min([r for r in resistance_levels if r > close], default=None)
            if nearest_resistance:
                target = min(nearest_resistance, entry + 2 * (entry - stop_loss))
            else:
                target = entry + 2 * (entry - stop_loss)

            reason = f"Bounce off support at {level:.2f}"

        elif bounce_signal == 'SELL':
            entry = close
            stop_loss = level + (level * 0.01)  # 1% above resistance
            # Target: nearest support or 2:1 R:R
            nearest_support = max([s for s in support_levels if s < close], default=None)
            if nearest_support:
                target = max(nearest_support, entry - 2 * (stop_loss - entry))
            else:
                target = entry - 2 * (stop_loss - entry)

            reason = f"Rejection at resistance {level:.2f}"

        else:
            bounce_signal = 'HOLD'
            entry = None
            stop_loss = None
            target = None
            reason = f"No S/R level nearby. Price: {close:.2f}"

        return {
            'strategy': 'Support/Resistance Bounce',
            'signal': bounce_signal,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'target': target,
            'key_level': level,
            'support_levels': support_levels[:3] if support_levels else [],
            'resistance_levels': resistance_levels[:3] if resistance_levels else [],
            'reason': reason
        }

    def _find_support_levels(self, df: pd.DataFrame, threshold: int = 3) -> List[float]:
        """Find support levels from local lows"""
        lows = df['low'].values
        support_levels = []

        for i in range(2, len(lows) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_levels.append(lows[i])

        # Cluster nearby levels
        return sorted(set(support_levels))

    def _find_resistance_levels(self, df: pd.DataFrame, threshold: int = 3) -> List[float]:
        """Find resistance levels from local highs"""
        highs = df['high'].values
        resistance_levels = []

        for i in range(2, len(highs) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_levels.append(highs[i])

        # Cluster nearby levels
        return sorted(set(resistance_levels), reverse=True)

    def select_best_strategy(
        self,
        df: pd.DataFrame,
        market_regime: str
    ) -> Dict:
        """
        Select best strategy based on market regime

        Args:
            df: DataFrame with OHLC data
            market_regime: Current market regime

        Returns:
            Best strategy for current conditions
        """
        regime = market_regime.upper()

        if 'TREND' in regime:
            return self.supertrend_strategy(df)

        elif 'RANGING' in regime or 'CONSOLIDAT' in regime:
            return self.mean_reversion_strategy(df)

        elif 'VOLATILE' in regime or 'BREAKOUT' in regime:
            return self.breakout_strategy(df)

        else:
            # Default to trend following
            return self.supertrend_strategy(df)
