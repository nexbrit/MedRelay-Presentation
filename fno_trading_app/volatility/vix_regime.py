"""
VIX Regime Analysis
Market volatility classification and position sizing adjustments
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class VIXRegime(Enum):
    """VIX regime classifications"""
    VERY_LOW = "VERY_LOW"  # VIX < 12
    LOW = "LOW"  # VIX 12-15
    NORMAL = "NORMAL"  # VIX 15-25
    HIGH = "HIGH"  # VIX 25-35
    EXTREME = "EXTREME"  # VIX > 35


class VIXAnalyzer:
    """
    Analyze VIX (India VIX) for trading decisions
    Adjust strategy and position sizing based on volatility regime
    """

    # VIX thresholds for regime classification
    VIX_THRESHOLDS = {
        'very_low': 12,
        'low': 15,
        'normal': 25,
        'high': 35
    }

    def __init__(self):
        """Initialize VIX analyzer"""
        self.vix_history = []  # [(date, vix_value), ...]
        logger.info("VIX Analyzer initialized")

    def add_vix_data(self, date, vix_value: float):
        """Add VIX data point"""
        self.vix_history.append((date, vix_value))

    def classify_regime(self, vix: float) -> VIXRegime:
        """
        Classify current VIX regime

        Args:
            vix: Current VIX value

        Returns:
            VIX regime classification
        """
        if vix < self.VIX_THRESHOLDS['very_low']:
            return VIXRegime.VERY_LOW
        elif vix < self.VIX_THRESHOLDS['low']:
            return VIXRegime.LOW
        elif vix < self.VIX_THRESHOLDS['normal']:
            return VIXRegime.NORMAL
        elif vix < self.VIX_THRESHOLDS['high']:
            return VIXRegime.HIGH
        else:
            return VIXRegime.EXTREME

    def get_position_size_multiplier(self, vix: float) -> float:
        """
        Get position size adjustment based on VIX

        High VIX → Reduce position size
        Low VIX → Normal/increase position size

        Args:
            vix: Current VIX value

        Returns:
            Multiplier for position sizing (0.5 to 1.0)
        """
        regime = self.classify_regime(vix)

        multipliers = {
            VIXRegime.VERY_LOW: 1.0,  # Normal size
            VIXRegime.LOW: 1.0,
            VIXRegime.NORMAL: 0.8,  # Reduce 20%
            VIXRegime.HIGH: 0.5,  # Reduce 50%
            VIXRegime.EXTREME: 0.3  # Reduce 70%
        }

        return multipliers[regime]

    def get_strategy_recommendation(self, vix: float) -> Dict[str, str]:
        """
        Get trading strategy recommendations based on VIX

        Args:
            vix: Current VIX value

        Returns:
            Dictionary with strategy recommendations
        """
        regime = self.classify_regime(vix)

        recommendations = {
            VIXRegime.VERY_LOW: {
                'regime': 'VERY LOW VOLATILITY',
                'market_condition': 'Complacent market, range-bound likely',
                'primary_strategy': 'SELL PREMIUM (Iron Condors, Credit Spreads)',
                'secondary_strategy': 'Buy cheap long-dated options for protection',
                'avoid': 'Avoid buying short-dated options (expensive time decay)',
                'risk_level': 'LOW',
                'position_size': 'Normal to Increased',
                'warning': '⚠️ Very low VIX often precedes volatility spike - keep some hedges'
            },
            VIXRegime.LOW: {
                'regime': 'LOW VOLATILITY',
                'market_condition': 'Calm market, trending or range-bound',
                'primary_strategy': 'SELL PREMIUM (Theta strategies)',
                'secondary_strategy': 'Iron Condors, Credit Spreads',
                'avoid': 'Avoid buying options (premium relatively expensive)',
                'risk_level': 'LOW',
                'position_size': 'Normal',
                'warning': ''
            },
            VIXRegime.NORMAL: {
                'regime': 'NORMAL VOLATILITY',
                'market_condition': 'Typical market conditions',
                'primary_strategy': 'Balanced approach - Both buying and selling viable',
                'secondary_strategy': 'Directional spreads, Calendar spreads',
                'avoid': 'No specific restrictions',
                'risk_level': 'MODERATE',
                'position_size': 'Slightly Reduced (80%)',
                'warning': ''
            },
            VIXRegime.HIGH: {
                'regime': 'HIGH VOLATILITY',
                'market_condition': 'Elevated uncertainty, trending market',
                'primary_strategy': 'BUY OPTIONS (Straddles, Strangles for breakouts)',
                'secondary_strategy': 'Sell far OTM premium for income',
                'avoid': 'Avoid selling naked options (unlimited risk)',
                'risk_level': 'HIGH',
                'position_size': 'Reduced by 50%',
                'warning': '⚠️ Large intraday swings expected - widen stop losses'
            },
            VIXRegime.EXTREME: {
                'regime': 'EXTREME VOLATILITY',
                'market_condition': 'PANIC/CRISIS MODE - Market in turmoil',
                'primary_strategy': 'CAPITAL PRESERVATION - Reduce exposure significantly',
                'secondary_strategy': 'Only trade with strict risk management',
                'avoid': 'Avoid large positions, avoid selling options',
                'risk_level': 'VERY HIGH',
                'position_size': 'Reduced by 70%',
                'warning': '🚨 CRISIS MODE - Consider staying in cash or protective puts only'
            }
        }

        return recommendations[regime]

    def detect_vix_spike(
        self,
        current_vix: float,
        spike_threshold: float = 30
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect VIX spike (potential market stress)

        Args:
            current_vix: Current VIX value
            spike_threshold: Threshold for spike detection (% change)

        Returns:
            Tuple of (is_spike, message)
        """
        if len(self.vix_history) < 5:
            return False, None

        # Get average VIX from last 5 days
        recent_vix = [v for _, v in self.vix_history[-5:]]
        avg_vix = np.mean(recent_vix)

        # Calculate % change
        pct_change = ((current_vix - avg_vix) / avg_vix) * 100

        if pct_change > spike_threshold:
            message = (
                f"🚨 VIX SPIKE: {current_vix:.1f} (+{pct_change:.1f}% from 5-day avg {avg_vix:.1f}). "
                f"REDUCE POSITIONS and widen stops!"
            )
            logger.warning(message)
            return True, message

        return False, None

    def vix_mean_reversion_signal(self, current_vix: float) -> Tuple[str, str]:
        """
        VIX mean reversion signal

        VIX tends to mean-revert to 15-18 range

        Args:
            current_vix: Current VIX value

        Returns:
            Tuple of (signal, reason)
        """
        historical_mean = 17.5  # India VIX long-term mean

        if current_vix > historical_mean * 1.5:  # 50% above mean
            return (
                "SELL_VOLATILITY",
                f"VIX at {current_vix:.1f} is elevated (mean: {historical_mean}). "
                f"Consider selling premium or volatility products."
            )
        elif current_vix < historical_mean * 0.7:  # 30% below mean
            return (
                "BUY_VOLATILITY",
                f"VIX at {current_vix:.1f} is depressed (mean: {historical_mean}). "
                f"Consider buying options or long volatility positions."
            )
        else:
            return (
                "NEUTRAL",
                f"VIX at {current_vix:.1f} near historical mean ({historical_mean})"
            )

    def get_max_portfolio_heat_for_vix(self, vix: float, base_heat: float = 6.0) -> float:
        """
        Adjust maximum portfolio heat based on VIX

        Args:
            vix: Current VIX value
            base_heat: Base portfolio heat limit (default 6%)

        Returns:
            Adjusted maximum portfolio heat
        """
        regime = self.classify_regime(vix)

        adjustments = {
            VIXRegime.VERY_LOW: 1.0,
            VIXRegime.LOW: 1.0,
            VIXRegime.NORMAL: 0.8,
            VIXRegime.HIGH: 0.5,
            VIXRegime.EXTREME: 0.3
        }

        adjusted_heat = base_heat * adjustments[regime]

        logger.info(
            f"Portfolio heat adjusted for VIX {vix:.1f}: "
            f"{base_heat}% → {adjusted_heat}%"
        )

        return adjusted_heat

    def should_trade(self, vix: float, max_vix_for_trading: float = 40) -> Tuple[bool, str]:
        """
        Determine if should trade based on VIX

        Args:
            vix: Current VIX value
            max_vix_for_trading: Maximum VIX to allow trading

        Returns:
            Tuple of (should_trade, reason)
        """
        if vix > max_vix_for_trading:
            return (
                False,
                f"🛑 VIX too high ({vix:.1f} > {max_vix_for_trading}). "
                f"Market in crisis mode - STOP TRADING"
            )

        regime = self.classify_regime(vix)

        if regime == VIXRegime.EXTREME:
            return (
                False,
                "🛑 EXTREME volatility regime - Only defensive trades allowed"
            )

        return True, f"✅ OK to trade (VIX: {vix:.1f}, Regime: {regime.value})"

    def generate_vix_report(self, current_vix: float) -> str:
        """
        Generate comprehensive VIX analysis report

        Args:
            current_vix: Current VIX value

        Returns:
            Formatted report
        """
        regime = self.classify_regime(current_vix)
        recommendations = self.get_strategy_recommendation(current_vix)
        size_multiplier = self.get_position_size_multiplier(current_vix)
        is_spike, spike_msg = self.detect_vix_spike(current_vix)
        mean_rev_signal, mean_rev_reason = self.vix_mean_reversion_signal(current_vix)
        should_trade, trade_msg = self.should_trade(current_vix)

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                 VIX REGIME ANALYSIS                          ║
╠══════════════════════════════════════════════════════════════╣

📊 CURRENT VIX METRICS
   India VIX:           {current_vix:>15.2f}
   Regime:              {regime.value:>15}
   Risk Level:          {recommendations['risk_level']:>15}

🎯 TRADING IMPLICATIONS
   Should Trade?        {should_trade:>15}
   {trade_msg}

   Position Size:       {recommendations['position_size']:>15}
   Size Multiplier:     {size_multiplier:>15.0%}

📈 STRATEGY RECOMMENDATIONS
   Market Condition:    {recommendations['market_condition']}

   PRIMARY:             {recommendations['primary_strategy']}
   SECONDARY:           {recommendations['secondary_strategy']}
   AVOID:               {recommendations['avoid']}

💡 VOLATILITY SIGNAL
   Mean Reversion:      {mean_rev_signal:>15}
   Reasoning:           {mean_rev_reason}

{'🚨 ' + spike_msg if is_spike else ''}
{recommendations['warning']}

╚══════════════════════════════════════════════════════════════╝

🎯 ACTION ITEMS:
   • Adjust position sizes by {size_multiplier:.0%}
   • Focus on: {recommendations['primary_strategy']}
   • Risk management: {recommendations['risk_level']}
"""
        return report
