"""
Strategy Selector Based on Market Regime
Automatically select appropriate trading strategies for current market conditions
"""

import pandas as pd
from typing import Dict, List, Optional
import logging
from .detector import MarketRegime, RegimeDetector

logger = logging.getLogger(__name__)


class StrategySelector:
    """
    Select trading strategies based on market regime
    Professional adaptive trading system
    """

    def __init__(self):
        """Initialize strategy selector"""
        self.regime_detector = RegimeDetector()
        logger.info("Strategy Selector initialized")

    def select_signal_generators(self, regime: MarketRegime) -> List[str]:
        """
        Select which signal generators to use for current regime

        Args:
            regime: Current market regime

        Returns:
            List of recommended signal generators
        """
        signal_map = {
            MarketRegime.STRONG_UPTREND: [
                'ema_crossover',  # Trend following
                'supertrend',
                'macd'  # Momentum
            ],
            MarketRegime.WEAK_UPTREND: [
                'ema_crossover',
                'rsi',  # For pullback entries
                'macd'
            ],
            MarketRegime.RANGING_MARKET: [
                'rsi',  # Mean reversion
                'bollinger_bands',
                'stochastic'
            ],
            MarketRegime.WEAK_DOWNTREND: [
                'ema_crossover',
                'rsi',  # For rally exits
                'macd'
            ],
            MarketRegime.STRONG_DOWNTREND: [
                'ema_crossover',
                'supertrend',
                'macd'
            ],
            MarketRegime.HIGH_VOLATILITY_CHAOS: [
                'none'  # Stay out
            ]
        }

        return signal_map.get(regime, ['rsi', 'macd'])

    def adjust_signal_thresholds(
        self,
        regime: MarketRegime,
        default_thresholds: Dict
    ) -> Dict:
        """
        Adjust signal thresholds based on regime

        Args:
            regime: Current regime
            default_thresholds: Default indicator thresholds

        Returns:
            Adjusted thresholds
        """
        adjusted = default_thresholds.copy()

        if regime == MarketRegime.STRONG_UPTREND:
            # More lenient buy signals, stricter sell signals
            adjusted['rsi_oversold'] = 40  # Buy earlier (normally 30)
            adjusted['rsi_overbought'] = 75  # Hold longer (normally 70)

        elif regime == MarketRegime.STRONG_DOWNTREND:
            # More lenient sell signals, stricter buy signals
            adjusted['rsi_oversold'] = 25  # Buy later (normally 30)
            adjusted['rsi_overbought'] = 65  # Sell earlier (normally 70)

        elif regime == MarketRegime.RANGING_MARKET:
            # Tighter buy/sell zones for mean reversion
            adjusted['rsi_oversold'] = 30
            adjusted['rsi_overbought'] = 70
            # Use normal Bollinger Band touches

        return adjusted

    def get_position_sizing_recommendation(
        self,
        regime: MarketRegime,
        vix: float,
        base_size: int
    ) -> int:
        """
        Recommend position size based on regime and VIX

        Args:
            regime: Current regime
            vix: Current VIX level
            base_size: Base position size

        Returns:
            Recommended position size
        """
        regime_multipliers = {
            MarketRegime.STRONG_UPTREND: 1.0,
            MarketRegime.WEAK_UPTREND: 0.9,
            MarketRegime.RANGING_MARKET: 1.0,  # Good for premium selling
            MarketRegime.WEAK_DOWNTREND: 0.8,
            MarketRegime.STRONG_DOWNTREND: 0.6,
            MarketRegime.HIGH_VOLATILITY_CHAOS: 0.3
        }

        regime_mult = regime_multipliers.get(regime, 0.8)

        # VIX adjustment
        if vix > 30:
            vix_mult = 0.5
        elif vix > 20:
            vix_mult = 0.8
        else:
            vix_mult = 1.0

        # Combined adjustment
        final_mult = regime_mult * vix_mult
        adjusted_size = int(base_size * final_mult)

        logger.info(
            f"Position sizing: {base_size} → {adjusted_size} "
            f"(Regime: {final_mult:.0%}, VIX adj: {vix_mult:.0%})"
        )

        return max(1, adjusted_size)  # At least 1 lot

    def should_take_signal(
        self,
        signal_type: str,  # 'BUY' or 'SELL'
        regime: MarketRegime,
        signal_strength: int
    ) -> Tuple[bool, str]:
        """
        Determine if should take a signal given the regime

        Args:
            signal_type: 'BUY' or 'SELL'
            regime: Current regime
            signal_strength: Signal strength (1-5)

        Returns:
            Tuple of (should_take, reason)
        """
        # Require stronger signals in certain regimes
        min_strength = {
            MarketRegime.HIGH_VOLATILITY_CHAOS: 5,  # Very selective
            MarketRegime.STRONG_DOWNTREND: 3 if signal_type == 'BUY' else 2,
            MarketRegime.STRONG_UPTREND: 2 if signal_type == 'BUY' else 3,
            MarketRegime.RANGING_MARKET: 2
        }

        required_strength = min_strength.get(regime, 2)

        if signal_strength < required_strength:
            return (
                False,
                f"Signal strength {signal_strength} below required {required_strength} "
                f"for regime {regime.value}"
            )

        # Regime-specific signal filtering
        if regime == MarketRegime.STRONG_UPTREND and signal_type == 'SELL':
            if signal_strength < 4:
                return False, "Don't fight strong uptrends unless very strong sell signal"

        elif regime == MarketRegime.STRONG_DOWNTREND and signal_type == 'BUY':
            if signal_strength < 4:
                return False, "Don't catch falling knives unless very strong buy signal"

        elif regime == MarketRegime.HIGH_VOLATILITY_CHAOS:
            return False, "Avoid trading in high volatility chaos - wait for clarity"

        return True, f"Signal approved for regime {regime.value}"

    def get_stop_loss_strategy(self, regime: MarketRegime) -> Dict:
        """
        Get stop loss strategy for current regime

        Args:
            regime: Current regime

        Returns:
            Stop loss strategy dictionary
        """
        strategies = {
            MarketRegime.STRONG_UPTREND: {
                'type': 'TRAILING_STOP',
                'distance': '2x ATR',
                'reasoning': 'Let winners run with trailing stop'
            },
            MarketRegime.WEAK_UPTREND: {
                'type': 'FIXED_PERCENTAGE',
                'distance': '2%',
                'reasoning': 'Standard stop for moderate trends'
            },
            MarketRegime.RANGING_MARKET: {
                'type': 'RANGE_BASED',
                'distance': 'Outside range boundaries',
                'reasoning': 'Stop if breaks out of range'
            },
            MarketRegime.WEAK_DOWNTREND: {
                'type': 'FIXED_PERCENTAGE',
                'distance': '2%',
                'reasoning': 'Standard stop for moderate trends'
            },
            MarketRegime.STRONG_DOWNTREND: {
                'type': 'TIGHT_STOP',
                'distance': '1x ATR',
                'reasoning': 'Tight stops in strong downtrends'
            },
            MarketRegime.HIGH_VOLATILITY_CHAOS: {
                'type': 'VERY_TIGHT',
                'distance': '1% or less',
                'reasoning': 'Very tight stops or stay out'
            }
        }

        return strategies.get(regime, strategies[MarketRegime.RANGING_MARKET])

    def combine_regime_and_volatility(
        self,
        regime: MarketRegime,
        vix: float,
        iv_rank: float
    ) -> Dict:
        """
        Combine regime detection with volatility analysis for comprehensive view

        Args:
            regime: Current market regime
            vix: Current VIX
            iv_rank: Current IV Rank

        Returns:
            Comprehensive trading recommendation
        """
        recommendation = {
            'regime': regime.value,
            'vix': vix,
            'iv_rank': iv_rank,
            'overall_strategy': '',
            'specific_actions': [],
            'risk_level': 'MODERATE'
        }

        # Uptrend + Low Volatility = Best for directional long
        if regime in [MarketRegime.STRONG_UPTREND, MarketRegime.WEAK_UPTREND] and vix < 15:
            recommendation['overall_strategy'] = 'DIRECTIONAL_LONG'
            recommendation['specific_actions'] = [
                'Buy call options or long futures',
                'Bull call spreads',
                'Sell OTM put spreads for income'
            ]
            recommendation['risk_level'] = 'LOW'

        # Uptrend + High Volatility = Caution
        elif regime in [MarketRegime.STRONG_UPTREND, MarketRegime.WEAK_UPTREND] and vix > 25:
            recommendation['overall_strategy'] = 'CAUTIOUS_LONG'
            recommendation['specific_actions'] = [
                'Reduce position sizes',
                'Use wider stops',
                'Consider protective puts'
            ]
            recommendation['risk_level'] = 'HIGH'

        # Ranging + High IV = Premium selling paradise
        elif regime == MarketRegime.RANGING_MARKET and iv_rank > 60:
            recommendation['overall_strategy'] = 'PREMIUM_SELLING'
            recommendation['specific_actions'] = [
                'Iron Condors (ideal setup)',
                'Credit spreads both sides',
                'Straddle/Strangle selling'
            ]
            recommendation['risk_level'] = 'LOW'

        # Ranging + Low IV = Wait or buy cheap options
        elif regime == MarketRegime.RANGING_MARKET and iv_rank < 30:
            recommendation['overall_strategy'] = 'WAIT_OR_BUY_OPTIONS'
            recommendation['specific_actions'] = [
                'Wait for better setups',
                'Buy cheap long-dated options',
                'Small range-trading positions only'
            ]
            recommendation['risk_level'] = 'LOW'

        # Downtrend + High Volatility = Danger zone
        elif regime in [MarketRegime.STRONG_DOWNTREND, MarketRegime.WEAK_DOWNTREND] and vix > 25:
            recommendation['overall_strategy'] = 'DEFENSIVE'
            recommendation['specific_actions'] = [
                'Move to cash',
                'Buy protective puts',
                'Very small positions only'
            ]
            recommendation['risk_level'] = 'VERY_HIGH'

        # High volatility chaos
        elif regime == MarketRegime.HIGH_VOLATILITY_CHAOS:
            recommendation['overall_strategy'] = 'CAPITAL_PRESERVATION'
            recommendation['specific_actions'] = [
                'Stay in cash',
                'Close most positions',
                'Wait for regime to stabilize'
            ]
            recommendation['risk_level'] = 'EXTREME'

        # Default
        else:
            recommendation['overall_strategy'] = 'BALANCED'
            recommendation['specific_actions'] = [
                'Use regime-appropriate strategies',
                'Normal position sizing',
                'Follow trend/range accordingly'
            ]
            recommendation['risk_level'] = 'MODERATE'

        return recommendation

    def generate_strategy_report(
        self,
        regime: MarketRegime,
        details: Dict,
        vix: float,
        iv_rank: float
    ) -> str:
        """
        Generate comprehensive strategy selection report

        Args:
            regime: Current regime
            details: Regime details
            vix: Current VIX
            iv_rank: Current IV Rank

        Returns:
            Formatted report
        """
        combined = self.combine_regime_and_volatility(regime, vix, iv_rank)
        signal_generators = self.select_signal_generators(regime)
        stop_loss = self.get_stop_loss_strategy(regime)

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║           STRATEGY SELECTION RECOMMENDATION                   ║
╠══════════════════════════════════════════════════════════════╣

📊 MARKET ANALYSIS
   Regime:              {regime.value:>30}
   VIX:                 {vix:>15.1f}
   IV Rank:             {iv_rank:>15.1f}%

   Risk Level:          {combined['risk_level']:>30}

🎯 RECOMMENDED STRATEGY
   Overall Approach:    {combined['overall_strategy']:>30}

📋 SPECIFIC ACTIONS
"""
        for action in combined['specific_actions']:
            report += f"   ✓ {action}\n"

        report += f"""
📊 SIGNAL GENERATORS TO USE
"""
        for gen in signal_generators:
            report += f"   • {gen}\n"

        report += f"""
🛡️  STOP LOSS STRATEGY
   Type:                {stop_loss['type']:>30}
   Distance:            {stop_loss['distance']:>30}
   Reasoning:           {stop_loss['reasoning']}

╚══════════════════════════════════════════════════════════════╝

💡 KEY INSIGHT:
   {combined['overall_strategy']} is optimal for current market conditions
   (Regime: {regime.value}, VIX: {vix:.1f}, IV Rank: {iv_rank:.0f}%)
"""
        return report
