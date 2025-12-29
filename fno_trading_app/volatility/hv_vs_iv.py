"""
Historical Volatility vs Implied Volatility Analysis
Trade the spread between realized and expected volatility
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class HVvsIVAnalyzer:
    """
    Compare Historical Volatility (realized) with Implied Volatility (expected)
    Professional volatility arbitrage analysis
    """

    def __init__(self):
        """Initialize HV vs IV analyzer"""
        logger.info("HV vs IV Analyzer initialized")

    def calculate_historical_volatility(
        self,
        prices: pd.Series,
        window: int = 30,
        annualization_factor: int = 252
    ) -> float:
        """
        Calculate Historical Volatility (HV) using log returns

        Args:
            prices: Series of prices
            window: Lookback window in days
            annualization_factor: Days per year for annualization (252 for trading days)

        Returns:
            Annualized historical volatility (as decimal)
        """
        if len(prices) < window:
            logger.warning(f"Insufficient data for HV calculation ({len(prices)} < {window})")
            return 0.0

        # Calculate log returns
        log_returns = np.log(prices / prices.shift(1))

        # Use last N days
        recent_returns = log_returns.iloc[-window:]

        # Calculate standard deviation and annualize
        std_dev = recent_returns.std()
        hv = std_dev * np.sqrt(annualization_factor)

        logger.debug(f"Calculated {window}-day HV: {hv:.2%}")
        return hv

    def calculate_parkinson_volatility(
        self,
        high: pd.Series,
        low: pd.Series,
        window: int = 30
    ) -> float:
        """
        Calculate Parkinson's Historical Volatility (uses high-low range)
        More efficient estimator than close-to-close volatility

        Args:
            high: Series of high prices
            low: Series of low prices
            window: Lookback window

        Returns:
            Parkinson volatility (annualized)
        """
        if len(high) < window or len(low) < window:
            return 0.0

        # Parkinson formula
        hl_ratio = np.log(high / low) ** 2
        recent_hl = hl_ratio.iloc[-window:]

        parkinson = np.sqrt(recent_hl.mean() / (4 * np.log(2))) * np.sqrt(252)

        logger.debug(f"Calculated {window}-day Parkinson HV: {parkinson:.2%}")
        return parkinson

    def calculate_garman_klass_volatility(
        self,
        open_prices: pd.Series,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        window: int = 30
    ) -> float:
        """
        Garman-Klass volatility estimator (most efficient)
        Uses OHLC data for better estimation

        Args:
            open_prices: Opening prices
            high: High prices
            low: Low prices
            close: Closing prices
            window: Lookback window

        Returns:
            Garman-Klass volatility (annualized)
        """
        if len(open_prices) < window:
            return 0.0

        hl = np.log(high / low) ** 2
        co = np.log(close / open_prices) ** 2

        gk = 0.5 * hl - (2 * np.log(2) - 1) * co

        recent_gk = gk.iloc[-window:]
        garman_klass = np.sqrt(recent_gk.mean()) * np.sqrt(252)

        logger.debug(f"Calculated {window}-day Garman-Klass HV: {garman_klass:.2%}")
        return garman_klass

    def compare_hv_iv(
        self,
        historical_vol: float,
        implied_vol: float,
        threshold: float = 0.05
    ) -> Dict:
        """
        Compare HV and IV to determine if options are over/underpriced

        Args:
            historical_vol: Historical volatility
            implied_vol: Implied volatility
            threshold: Threshold for significant difference (5% = 0.05)

        Returns:
            Dictionary with analysis
        """
        difference = implied_vol - historical_vol
        pct_difference = (difference / historical_vol) * 100 if historical_vol > 0 else 0

        analysis = {
            'historical_vol': historical_vol,
            'implied_vol': implied_vol,
            'difference': difference,
            'pct_difference': pct_difference,
            'iv_premium': difference > 0,
            'hv_premium': difference < 0
        }

        # Determine signal
        if difference > threshold:
            analysis['signal'] = 'SELL_OPTIONS'
            analysis['reason'] = (
                f"IV ({implied_vol:.1%}) is {abs(pct_difference):.1f}% higher than HV ({historical_vol:.1%}). "
                f"Options are OVERPRICED → Sell premium"
            )
            analysis['strength'] = min(abs(pct_difference) / 10, 5)  # Scale 0-5

        elif difference < -threshold:
            analysis['signal'] = 'BUY_OPTIONS'
            analysis['reason'] = (
                f"IV ({implied_vol:.1%}) is {abs(pct_difference):.1f}% lower than HV ({historical_vol:.1%}). "
                f"Options are UNDERPRICED → Buy options"
            )
            analysis['strength'] = min(abs(pct_difference) / 10, 5)

        else:
            analysis['signal'] = 'NEUTRAL'
            analysis['reason'] = (
                f"IV ({implied_vol:.1%}) and HV ({historical_vol:.1%}) are similar. "
                f"Options fairly priced"
            )
            analysis['strength'] = 0

        return analysis

    def volatility_cone(
        self,
        prices: pd.Series,
        windows: List[int] = [10, 20, 30, 60, 90]
    ) -> pd.DataFrame:
        """
        Create volatility cone (HV across multiple timeframes)

        Args:
            prices: Price series
            windows: List of lookback windows

        Returns:
            DataFrame with HV for each window
        """
        cone_data = []

        for window in windows:
            if len(prices) >= window:
                hv = self.calculate_historical_volatility(prices, window)
                cone_data.append({
                    'window': window,
                    'hv': hv
                })

        return pd.DataFrame(cone_data)

    def predict_volatility_reversal(
        self,
        hv_history: pd.Series,
        current_hv: float,
        std_threshold: float = 2.0
    ) -> Tuple[bool, str]:
        """
        Predict if volatility will mean-revert

        Args:
            hv_history: Historical HV values
            current_hv: Current HV
            std_threshold: Z-score threshold for reversal

        Returns:
            Tuple of (will_revert, message)
        """
        if len(hv_history) < 60:
            return False, "Insufficient history"

        mean_hv = hv_history.mean()
        std_hv = hv_history.std()

        z_score = (current_hv - mean_hv) / std_hv if std_hv > 0 else 0

        if z_score > std_threshold:
            return (
                True,
                f"HV {current_hv:.1%} is {z_score:.1f}σ above mean {mean_hv:.1%}. "
                f"Expect volatility to DECREASE"
            )
        elif z_score < -std_threshold:
            return (
                True,
                f"HV {current_hv:.1%} is {abs(z_score):.1f}σ below mean {mean_hv:.1%}. "
                f"Expect volatility to INCREASE"
            )

        return False, f"HV near mean ({current_hv:.1%} vs {mean_hv:.1%})"

    def volatility_risk_premium(
        self,
        historical_vol: float,
        implied_vol: float
    ) -> Dict:
        """
        Calculate Volatility Risk Premium (VRP)

        VRP = IV - HV (typically positive, as IV includes risk premium)

        Args:
            historical_vol: Realized volatility
            implied_vol: Expected volatility

        Returns:
            VRP analysis dictionary
        """
        vrp = implied_vol - historical_vol
        vrp_pct = (vrp / historical_vol) * 100 if historical_vol > 0 else 0

        analysis = {
            'vrp': vrp,
            'vrp_pct': vrp_pct,
            'interpretation': ''
        }

        if vrp > 0.05:  # 5% positive VRP
            analysis['interpretation'] = (
                f"✅ High VRP ({vrp:.1%}): Market paying premium for insurance. "
                f"Favorable for selling options."
            )
        elif vrp < -0.03:  # Negative VRP
            analysis['interpretation'] = (
                f"⚠️ Negative VRP ({vrp:.1%}): Options cheap relative to realized vol. "
                f"Consider buying options."
            )
        else:
            analysis['interpretation'] = (
                f"➖ Normal VRP ({vrp:.1%}): Standard risk premium."
            )

        return analysis

    def generate_hv_iv_report(
        self,
        historical_vol: float,
        implied_vol: float,
        instrument: str
    ) -> str:
        """
        Generate comprehensive HV vs IV report

        Args:
            historical_vol: Historical volatility
            implied_vol: Implied volatility
            instrument: Instrument name

        Returns:
            Formatted report
        """
        comparison = self.compare_hv_iv(historical_vol, implied_vol)
        vrp = self.volatility_risk_premium(historical_vol, implied_vol)

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║          HV vs IV ANALYSIS: {instrument:^30}         ║
╠══════════════════════════════════════════════════════════════╣

📊 VOLATILITY COMPARISON
   Historical Vol (HV): {historical_vol:>15.2%}
   Implied Vol (IV):    {implied_vol:>15.2%}

   Difference:          {comparison['difference']:>15.2%}
   % Difference:        {comparison['pct_difference']:>15.1f}%

💰 VOLATILITY RISK PREMIUM
   VRP:                 {vrp['vrp']:>15.2%}
   VRP %:               {vrp['vrp_pct']:>15.1f}%
   {vrp['interpretation']}

🎯 TRADING SIGNAL
   Signal:              {comparison['signal']:>20}
   Strength:            {'⭐' * int(comparison['strength']):>20}

   Reasoning:           {comparison['reason']}

╚══════════════════════════════════════════════════════════════╝

💡 INTERPRETATION:
   {'📉 IV > HV: Options are OVERPRICED - Sell premium' if comparison['iv_premium'] else
    '📈 HV > IV: Options are UNDERPRICED - Buy options' if comparison['hv_premium'] else
    '➖ IV ≈ HV: Options fairly priced'}
"""
        return report
