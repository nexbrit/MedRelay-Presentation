"""
Implied Volatility Analysis
IV Rank, IV Percentile, and volatility trading signals
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class IVAnalyzer:
    """
    Analyze Implied Volatility for options trading
    Professional volatility trading tools
    """

    def __init__(self, historical_iv_window: int = 252):
        """
        Initialize IV analyzer

        Args:
            historical_iv_window: Days of IV history to track (default 252 = 1 year)
        """
        self.historical_iv_window = historical_iv_window
        self.iv_history = {}  # {instrument: [(date, iv), ...]}

        logger.info(f"IV Analyzer initialized with {historical_iv_window}-day window")

    def add_iv_data(self, instrument: str, date: datetime, implied_vol: float):
        """
        Add historical IV data point

        Args:
            instrument: Instrument name
            date: Date of observation
            implied_vol: Implied volatility (as decimal, e.g., 0.18 for 18%)
        """
        if instrument not in self.iv_history:
            self.iv_history[instrument] = []

        self.iv_history[instrument].append((date, implied_vol))

        # Keep only last N days
        if len(self.iv_history[instrument]) > self.historical_iv_window:
            self.iv_history[instrument] = self.iv_history[instrument][-self.historical_iv_window:]

    def calculate_iv_rank(self, instrument: str, current_iv: float) -> Optional[float]:
        """
        Calculate IV Rank

        IV Rank = (Current IV - Min IV) / (Max IV - Min IV) × 100

        Interpretation:
        - IV Rank < 30: Low volatility → Consider buying options
        - IV Rank > 70: High volatility → Consider selling options
        - IV Rank 30-70: Normal range

        Args:
            instrument: Instrument name
            current_iv: Current implied volatility

        Returns:
            IV Rank (0-100), or None if insufficient data
        """
        if instrument not in self.iv_history or len(self.iv_history[instrument]) < 20:
            logger.warning(f"Insufficient IV history for {instrument}")
            return None

        ivs = [iv for _, iv in self.iv_history[instrument]]

        min_iv = min(ivs)
        max_iv = max(ivs)

        if max_iv == min_iv:
            return 50.0  # No range, return neutral

        iv_rank = ((current_iv - min_iv) / (max_iv - min_iv)) * 100

        logger.debug(f"IV Rank for {instrument}: {iv_rank:.1f}% (IV: {current_iv:.1%})")
        return iv_rank

    def calculate_iv_percentile(self, instrument: str, current_iv: float) -> Optional[float]:
        """
        Calculate IV Percentile

        IV Percentile = What percentage of days had lower IV?

        More stable than IV Rank (less affected by one-day spikes)

        Args:
            instrument: Instrument name
            current_iv: Current implied volatility

        Returns:
            IV Percentile (0-100), or None if insufficient data
        """
        if instrument not in self.iv_history or len(self.iv_history[instrument]) < 20:
            return None

        ivs = [iv for _, iv in self.iv_history[instrument]]

        # Count how many days had lower IV
        lower_count = sum(1 for iv in ivs if iv < current_iv)
        percentile = (lower_count / len(ivs)) * 100

        logger.debug(f"IV Percentile for {instrument}: {percentile:.1f}%")
        return percentile

    def get_iv_statistics(self, instrument: str) -> Optional[Dict]:
        """
        Get comprehensive IV statistics

        Args:
            instrument: Instrument name

        Returns:
            Dictionary with IV statistics
        """
        if instrument not in self.iv_history or not self.iv_history[instrument]:
            return None

        ivs = [iv for _, iv in self.iv_history[instrument]]

        stats = {
            'current_iv': ivs[-1],
            'mean_iv': np.mean(ivs),
            'median_iv': np.median(ivs),
            'std_iv': np.std(ivs),
            'min_iv': np.min(ivs),
            'max_iv': np.max(ivs),
            'percentile_25': np.percentile(ivs, 25),
            'percentile_75': np.percentile(ivs, 75),
            'iv_range': np.max(ivs) - np.min(ivs),
            'days_of_data': len(ivs)
        }

        return stats

    def get_volatility_regime(self, instrument: str, current_iv: float) -> Tuple[str, str]:
        """
        Determine volatility regime

        Args:
            instrument: Instrument name
            current_iv: Current implied volatility

        Returns:
            Tuple of (regime, recommendation)
        """
        iv_rank = self.calculate_iv_rank(instrument, current_iv)
        iv_percentile = self.calculate_iv_percentile(instrument, current_iv)

        if iv_rank is None or iv_percentile is None:
            return "UNKNOWN", "Insufficient data"

        # Determine regime
        if iv_rank > 70 or iv_percentile > 70:
            regime = "HIGH_VOLATILITY"
            recommendation = (
                "📉 SELL premium (options overpriced) - "
                "Consider iron condors, credit spreads, or covered calls"
            )
        elif iv_rank < 30 or iv_percentile < 30:
            regime = "LOW_VOLATILITY"
            recommendation = (
                "📈 BUY options (options cheap) - "
                "Consider long straddles, long strangles, or debit spreads"
            )
        else:
            regime = "NORMAL_VOLATILITY"
            recommendation = (
                "➖ Neutral volatility - "
                "Both buying and selling strategies viable"
            )

        return regime, recommendation

    def detect_iv_spike(
        self,
        instrument: str,
        current_iv: float,
        spike_threshold: float = 2.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect sudden IV spike (potential trading opportunity)

        Args:
            instrument: Instrument name
            current_iv: Current implied volatility
            spike_threshold: Standard deviations for spike detection

        Returns:
            Tuple of (is_spike, message)
        """
        stats = self.get_iv_statistics(instrument)

        if not stats:
            return False, None

        # Calculate z-score
        z_score = (current_iv - stats['mean_iv']) / stats['std_iv'] if stats['std_iv'] > 0 else 0

        if z_score > spike_threshold:
            message = (
                f"🚨 IV SPIKE DETECTED: {instrument} IV at {current_iv:.1%} "
                f"({z_score:.1f}σ above mean). "
                f"Consider SELLING premium before IV crush."
            )
            logger.warning(message)
            return True, message

        elif z_score < -spike_threshold:
            message = (
                f"📊 IV CRUSH DETECTED: {instrument} IV at {current_iv:.1%} "
                f"({abs(z_score):.1f}σ below mean). "
                f"Consider BUYING options (cheap premium)."
            )
            logger.info(message)
            return True, message

        return False, None

    def calculate_iv_skew(self, option_chain: pd.DataFrame, atm_strike: float) -> Dict:
        """
        Calculate volatility skew (smile)

        Skew shows if OTM puts or calls are more expensive

        Args:
            option_chain: DataFrame with columns ['strike', 'option_type', 'iv']
            atm_strike: At-the-money strike price

        Returns:
            Dictionary with skew metrics
        """
        if option_chain.empty:
            return {}

        # Separate calls and puts
        calls = option_chain[option_chain['option_type'] == 'CE'].copy()
        puts = option_chain[option_chain['option_type'] == 'PE'].copy()

        # Calculate moneyness
        calls['moneyness'] = (calls['strike'] - atm_strike) / atm_strike * 100
        puts['moneyness'] = (puts['strike'] - atm_strike) / atm_strike * 100

        # Get ATM IV
        atm_calls = calls[abs(calls['moneyness']) < 2]
        atm_puts = puts[abs(puts['moneyness']) < 2]

        atm_iv = pd.concat([atm_calls, atm_puts])['iv'].mean() if len(atm_calls) > 0 or len(puts) > 0 else None

        # Get OTM put IV (10% below spot)
        otm_puts = puts[(puts['moneyness'] >= -12) & (puts['moneyness'] <= -8)]
        otm_put_iv = otm_puts['iv'].mean() if len(otm_puts) > 0 else None

        # Get OTM call IV (10% above spot)
        otm_calls = calls[(calls['moneyness'] >= 8) & (calls['moneyness'] <= 12)]
        otm_call_iv = otm_calls['iv'].mean() if len(otm_calls) > 0 else None

        # Calculate skew
        put_skew = (otm_put_iv - atm_iv) if (otm_put_iv and atm_iv) else 0
        call_skew = (otm_call_iv - atm_iv) if (otm_call_iv and atm_iv) else 0

        skew = {
            'atm_iv': atm_iv,
            'otm_put_iv': otm_put_iv,
            'otm_call_iv': otm_call_iv,
            'put_skew': put_skew,
            'call_skew': call_skew,
            'total_skew': put_skew - call_skew,
            'interpretation': self._interpret_skew(put_skew, call_skew)
        }

        return skew

    def _interpret_skew(self, put_skew: float, call_skew: float) -> str:
        """Interpret volatility skew"""
        total_skew = put_skew - call_skew

        if total_skew > 0.05:  # 5% higher put IV
            return "⬇️  BEARISH SKEW - Market fears downside (normal in equity indices)"
        elif total_skew < -0.05:  # 5% higher call IV
            return "⬆️  BULLISH SKEW - Market expects upside (unusual)"
        else:
            return "➖ NEUTRAL SKEW - Balanced"

    def mean_reversion_signal(self, instrument: str, current_iv: float) -> Tuple[str, str]:
        """
        IV mean reversion trading signal

        High IV tends to revert to mean (sell premium)
        Low IV tends to revert to mean (buy premium)

        Args:
            instrument: Instrument name
            current_iv: Current IV

        Returns:
            Tuple of (signal, reason)
        """
        stats = self.get_iv_statistics(instrument)

        if not stats:
            return "HOLD", "Insufficient data"

        mean_iv = stats['mean_iv']
        std_iv = stats['std_iv']

        # Calculate deviation from mean
        deviation = (current_iv - mean_iv) / std_iv if std_iv > 0 else 0

        if deviation > 1.5:  # 1.5 std above mean
            return "SELL", f"IV {current_iv:.1%} is {deviation:.1f}σ above mean {mean_iv:.1%} - likely to revert down"
        elif deviation > 1.0:
            return "SELL", f"IV elevated ({current_iv:.1%} vs mean {mean_iv:.1%}) - consider selling premium"
        elif deviation < -1.5:
            return "BUY", f"IV {current_iv:.1%} is {abs(deviation):.1f}σ below mean {mean_iv:.1%} - likely to revert up"
        elif deviation < -1.0:
            return "BUY", f"IV depressed ({current_iv:.1%} vs mean {mean_iv:.1%}) - consider buying options"
        else:
            return "HOLD", f"IV near mean ({current_iv:.1%} vs {mean_iv:.1%}) - no strong edge"

    def vega_exposure_recommendation(
        self,
        current_iv: float,
        portfolio_vega: float,
        instrument: str
    ) -> str:
        """
        Recommend vega exposure based on IV level

        Args:
            current_iv: Current IV
            portfolio_vega: Current portfolio vega
            instrument: Instrument name

        Returns:
            Recommendation string
        """
        iv_rank = self.calculate_iv_rank(instrument, current_iv)

        if iv_rank is None:
            return "Insufficient data for recommendation"

        if iv_rank > 70:
            # High IV - want negative vega (short options)
            if portfolio_vega > 0:
                return "⚠️  High IV + Positive Vega = RISKY. Consider reducing vega exposure (sell options)"
            else:
                return "✅ High IV + Negative Vega = GOOD. Positioned for IV crush"

        elif iv_rank < 30:
            # Low IV - want positive vega (long options)
            if portfolio_vega < 0:
                return "⚠️  Low IV + Negative Vega = RISKY. Consider increasing vega exposure (buy options)"
            else:
                return "✅ Low IV + Positive Vega = GOOD. Positioned for IV expansion"

        else:
            return "➖ Normal IV - vega exposure acceptable either way"

    def generate_iv_report(self, instrument: str, current_iv: float) -> str:
        """
        Generate comprehensive IV analysis report

        Args:
            instrument: Instrument name
            current_iv: Current IV

        Returns:
            Formatted report
        """
        stats = self.get_iv_statistics(instrument)
        if not stats:
            return f"Insufficient IV data for {instrument}"

        iv_rank = self.calculate_iv_rank(instrument, current_iv)
        iv_percentile = self.calculate_iv_percentile(instrument, current_iv)
        regime, regime_rec = self.get_volatility_regime(instrument, current_iv)
        is_spike, spike_msg = self.detect_iv_spike(instrument, current_iv)
        mean_rev_signal, mean_rev_reason = self.mean_reversion_signal(instrument, current_iv)

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║           IMPLIED VOLATILITY ANALYSIS: {instrument:^20}    ║
╠══════════════════════════════════════════════════════════════╣

📊 CURRENT IV METRICS
   Current IV:          {current_iv:>15.2%}
   IV Rank:             {iv_rank:>15.1f}%  {'🔴 HIGH' if iv_rank > 70 else '🟢 LOW' if iv_rank < 30 else '🟡 NORMAL'}
   IV Percentile:       {iv_percentile:>15.1f}%

📈 HISTORICAL IV STATISTICS ({stats['days_of_data']} days)
   Mean IV:             {stats['mean_iv']:>15.2%}
   Median IV:           {stats['median_iv']:>15.2%}
   Std Deviation:       {stats['std_iv']:>15.2%}

   Min IV (52w):        {stats['min_iv']:>15.2%}
   Max IV (52w):        {stats['max_iv']:>15.2%}
   IV Range:            {stats['iv_range']:>15.2%}

🎯 VOLATILITY REGIME
   Regime:              {regime:>25}
   Recommendation:      {regime_rec}

💡 MEAN REVERSION SIGNAL
   Signal:              {mean_rev_signal:>25}
   Reason:              {mean_rev_reason}

{'🚨 ' + spike_msg if is_spike else ''}

╚══════════════════════════════════════════════════════════════╝
"""
        return report
