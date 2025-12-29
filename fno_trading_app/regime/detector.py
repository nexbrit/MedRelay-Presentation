"""
Market Regime Detection
Classify market as trending, ranging, or volatile
Adapt trading strategy to current regime
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classifications"""
    STRONG_UPTREND = "STRONG_UPTREND"
    WEAK_UPTREND = "WEAK_UPTREND"
    RANGING_MARKET = "RANGING_MARKET"
    WEAK_DOWNTREND = "WEAK_DOWNTREND"
    STRONG_DOWNTREND = "STRONG_DOWNTREND"
    HIGH_VOLATILITY_CHAOS = "HIGH_VOLATILITY_CHAOS"


class RegimeDetector:
    """
    Detect current market regime using multiple indicators
    Professional regime classification for strategy selection
    """

    def __init__(self):
        """Initialize regime detector"""
        logger.info("Regime Detector initialized")

    def calculate_adx(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average Directional Index (ADX)
        Measures trend strength (not direction)

        ADX > 25: Strong trend
        ADX < 20: Weak trend / ranging

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ADX period

        Returns:
            ADX series
        """
        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smooth +DM, -DM, and TR
        plus_dm_smooth = plus_dm.rolling(window=period).mean()
        minus_dm_smooth = minus_dm.rolling(window=period).mean()
        tr_smooth = tr.rolling(window=period).mean()

        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx

    def calculate_atr_percentile(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        percentile_period: int = 100
    ) -> float:
        """
        Calculate ATR percentile (volatility level)

        Args:
            high, low, close: OHLC data
            period: ATR period
            percentile_period: Period for percentile calculation

        Returns:
            ATR percentile (0-100)
        """
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate ATR
        atr = tr.rolling(window=period).mean()

        # Calculate percentile of current ATR
        if len(atr) < percentile_period:
            return 50.0

        recent_atr = atr.iloc[-percentile_period:]
        current_atr = atr.iloc[-1]

        percentile = (recent_atr < current_atr).sum() / len(recent_atr) * 100

        return percentile

    def detect_regime(
        self,
        df: pd.DataFrame,
        adx_period: int = 14,
        ema_period: int = 50
    ) -> Tuple[MarketRegime, Dict]:
        """
        Detect current market regime

        Args:
            df: DataFrame with OHLC data
            adx_period: ADX period
            ema_period: EMA period for trend direction

        Returns:
            Tuple of (regime, details)
        """
        if len(df) < max(adx_period, ema_period) + 20:
            return MarketRegime.RANGING_MARKET, {'error': 'Insufficient data'}

        # Calculate ADX (trend strength)
        adx = self.calculate_adx(df['high'], df['low'], df['close'], adx_period)
        current_adx = adx.iloc[-1]

        # Calculate EMA (trend direction)
        ema = df['close'].ewm(span=ema_period, adjust=False).mean()
        current_price = df['close'].iloc[-1]
        current_ema = ema.iloc[-1]
        price_vs_ema = ((current_price - current_ema) / current_ema) * 100

        # Calculate ATR percentile (volatility)
        atr_percentile = self.calculate_atr_percentile(
            df['high'], df['low'], df['close']
        )

        # Determine regime
        details = {
            'adx': current_adx,
            'price_vs_ema': price_vs_ema,
            'atr_percentile': atr_percentile,
            'current_price': current_price,
            'ema': current_ema
        }

        # High volatility chaos (overrides other regimes)
        if atr_percentile > 90:
            return MarketRegime.HIGH_VOLATILITY_CHAOS, details

        # Strong trend (ADX > 30)
        if current_adx > 30:
            if price_vs_ema > 2:  # 2% above EMA
                return MarketRegime.STRONG_UPTREND, details
            elif price_vs_ema < -2:
                return MarketRegime.STRONG_DOWNTREND, details

        # Moderate trend (ADX 20-30)
        elif current_adx > 20:
            if price_vs_ema > 1:
                return MarketRegime.WEAK_UPTREND, details
            elif price_vs_ema < -1:
                return MarketRegime.WEAK_DOWNTREND, details

        # Ranging market (ADX < 20)
        return MarketRegime.RANGING_MARKET, details

    def get_strategy_for_regime(self, regime: MarketRegime) -> Dict:
        """
        Get recommended strategies for each regime

        Args:
            regime: Current market regime

        Returns:
            Dictionary with strategy recommendations
        """
        strategies = {
            MarketRegime.STRONG_UPTREND: {
                'primary': 'MOMENTUM_LONG',
                'description': 'Strong upward trend - Follow the trend',
                'recommended_strategies': [
                    'Buy breakouts above resistance',
                    'Long call options',
                    'Bull call spreads',
                    'Trend-following with trailing stops'
                ],
                'indicators': ['EMA crossovers', 'Supertrend', 'MACD'],
                'avoid': [
                    'Mean reversion (RSI oversold)',
                    'Selling naked calls',
                    'Counter-trend shorts'
                ],
                'stop_loss': 'ATR-based trailing stop (2x ATR)',
                'position_sizing': 'Normal to aggressive'
            },

            MarketRegime.WEAK_UPTREND: {
                'primary': 'SWING_LONG',
                'description': 'Moderate uptrend - Pullback buying',
                'recommended_strategies': [
                    'Buy dips to support/EMA',
                    'Moderate call spreads',
                    'Credit put spreads',
                    'Swing trading longs'
                ],
                'indicators': ['RSI pullbacks', 'EMA support', 'Bollinger Bands'],
                'avoid': [
                    'Aggressive breakout buying',
                    'Heavy short positions'
                ],
                'stop_loss': 'Below recent support or EMA',
                'position_sizing': 'Normal'
            },

            MarketRegime.RANGING_MARKET: {
                'primary': 'MEAN_REVERSION',
                'description': 'Range-bound - Buy support, sell resistance',
                'recommended_strategies': [
                    'Iron Condors',
                    'Credit spreads (both sides)',
                    'Range trading (buy low, sell high)',
                    'Straddle/Strangle selling (theta strategies)'
                ],
                'indicators': ['RSI', 'Bollinger Bands', 'Support/Resistance'],
                'avoid': [
                    'Breakout trading',
                    'Trend-following indicators',
                    'Directional bets'
                ],
                'stop_loss': 'Outside range boundaries',
                'position_sizing': 'Normal to increased (favorable for premium selling)'
            },

            MarketRegime.WEAK_DOWNTREND: {
                'primary': 'SWING_SHORT',
                'description': 'Moderate downtrend - Rally selling',
                'recommended_strategies': [
                    'Sell rallies to resistance/EMA',
                    'Put spreads',
                    'Credit call spreads',
                    'Swing trading shorts'
                ],
                'indicators': ['RSI overbought', 'EMA resistance', 'Bearish patterns'],
                'avoid': [
                    'Aggressive long positions',
                    'Bottom fishing'
                ],
                'stop_loss': 'Above recent resistance or EMA',
                'position_sizing': 'Normal'
            },

            MarketRegime.STRONG_DOWNTREND: {
                'primary': 'MOMENTUM_SHORT',
                'description': 'Strong downtrend - Ride the decline',
                'recommended_strategies': [
                    'Short breakdowns below support',
                    'Long put options',
                    'Bear put spreads',
                    'Protective puts on longs'
                ],
                'indicators': ['Moving averages', 'Momentum indicators', 'Support breaks'],
                'avoid': [
                    'Buying dips (catching falling knife)',
                    'Selling naked puts',
                    'Counter-trend longs'
                ],
                'stop_loss': 'ATR-based trailing stop (2x ATR)',
                'position_sizing': 'Reduced (risk management in declining market)'
            },

            MarketRegime.HIGH_VOLATILITY_CHAOS: {
                'primary': 'CAPITAL_PRESERVATION',
                'description': 'High volatility chaos - Reduce exposure',
                'recommended_strategies': [
                    'Cash / sidelines',
                    'Protective puts only',
                    'Very tight stop losses',
                    'Wait for clarity'
                ],
                'indicators': ['VIX', 'ATR', 'Market breadth'],
                'avoid': [
                    'Large positions',
                    'Selling options (unlimited risk)',
                    'Fighting the volatility'
                ],
                'stop_loss': 'Very tight (1x ATR or less)',
                'position_sizing': 'Minimal (20-30% of normal)'
            }
        }

        return strategies.get(regime, strategies[MarketRegime.RANGING_MARKET])

    def regime_transition_alert(
        self,
        previous_regime: MarketRegime,
        current_regime: MarketRegime
    ) -> Optional[str]:
        """
        Alert on regime changes

        Args:
            previous_regime: Previous regime
            current_regime: Current regime

        Returns:
            Alert message if regime changed
        """
        if previous_regime == current_regime:
            return None

        alert = (
            f"🚨 REGIME CHANGE: {previous_regime.value} → {current_regime.value}\n"
            f"   Update strategy accordingly!"
        )

        logger.warning(alert)
        return alert

    def calculate_regime_confidence(self, details: Dict) -> float:
        """
        Calculate confidence in regime detection

        Args:
            details: Regime details dictionary

        Returns:
            Confidence score (0-100)
        """
        adx = details['adx']
        atr_percentile = details['atr_percentile']

        # High ADX = high confidence in trend
        # Moderate ATR = high confidence
        adx_confidence = min(adx / 40 * 100, 100) if adx > 20 else 50

        # ATR too high or too low reduces confidence
        if 20 < atr_percentile < 80:
            atr_confidence = 100
        else:
            atr_confidence = 100 - abs(atr_percentile - 50)

        # Average confidence
        confidence = (adx_confidence + atr_confidence) / 2

        return confidence

    def generate_regime_report(
        self,
        regime: MarketRegime,
        details: Dict
    ) -> str:
        """
        Generate comprehensive regime report

        Args:
            regime: Current regime
            details: Regime details

        Returns:
            Formatted report
        """
        strategy = self.get_strategy_for_regime(regime)
        confidence = self.calculate_regime_confidence(details)

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║              MARKET REGIME ANALYSIS                           ║
╠══════════════════════════════════════════════════════════════╣

📊 CURRENT REGIME
   Regime:              {regime.value:>30}
   Confidence:          {confidence:>15.1f}%  {'✅ HIGH' if confidence > 75 else '⚠️ MODERATE' if confidence > 50 else '❌ LOW'}

📈 MARKET METRICS
   ADX (Trend Strength): {details['adx']:>14.2f}  {'🔥 STRONG' if details['adx'] > 25 else '➖ WEAK'}
   Price vs EMA50:       {details['price_vs_ema']:>14.2f}%
   ATR Percentile:       {details['atr_percentile']:>14.1f}%  {'📊 HIGH VOL' if details['atr_percentile'] > 80 else '📉 LOW VOL' if details['atr_percentile'] < 20 else '➖ NORMAL'}

🎯 RECOMMENDED STRATEGY
   Primary Approach:     {strategy['primary']:>30}
   Description:          {strategy['description']}

📋 SPECIFIC STRATEGIES
"""
        for strat in strategy['recommended_strategies']:
            report += f"   ✓ {strat}\n"

        report += f"""
📊 INDICATORS TO USE
"""
        for indicator in strategy['indicators']:
            report += f"   • {indicator}\n"

        report += f"""
⚠️  STRATEGIES TO AVOID
"""
        for avoid in strategy['avoid']:
            report += f"   ✗ {avoid}\n"

        report += f"""
🛡️  RISK MANAGEMENT
   Stop Loss:           {strategy['stop_loss']}
   Position Sizing:     {strategy['position_sizing']}

╚══════════════════════════════════════════════════════════════╝

💡 KEY INSIGHT: {strategy['description']}
"""
        return report
