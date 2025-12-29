"""
Correlation Matrix for Risk Management
Prevents over-concentration in correlated instruments
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CorrelationMatrix:
    """
    Track and manage correlation between instruments
    Prevents taking multiple positions in highly correlated instruments
    """

    # Known correlations for Indian F&O instruments
    KNOWN_CORRELATIONS = {
        ('NIFTY', 'BANKNIFTY'): 0.70,
        ('NIFTY', 'FINNIFTY'): 0.65,
        ('BANKNIFTY', 'FINNIFTY'): 0.60,
        ('NIFTY', 'RELIANCE'): 0.75,
        ('NIFTY', 'HDFC'): 0.72,
        ('BANKNIFTY', 'HDFC'): 0.80,
        ('BANKNIFTY', 'ICICI'): 0.78,
    }

    def __init__(
        self,
        max_correlated_exposure: float = 10.0,
        correlation_threshold: float = 0.60,
        lookback_period: int = 30
    ):
        """
        Initialize correlation matrix

        Args:
            max_correlated_exposure: Max % of account in correlated instruments
            correlation_threshold: Threshold to consider instruments correlated (0.60 = 60%)
            lookback_period: Days to calculate rolling correlation
        """
        self.max_correlated_exposure = max_correlated_exposure
        self.correlation_threshold = correlation_threshold
        self.lookback_period = lookback_period
        self.correlation_data = {}  # Historical price data for correlation calc
        self.correlation_matrix = pd.DataFrame()

        logger.info(
            f"Correlation Matrix initialized: "
            f"Max Correlated Exposure={max_correlated_exposure}%, "
            f"Threshold={correlation_threshold}, "
            f"Lookback={lookback_period} days"
        )

    def add_price_data(self, instrument: str, prices: pd.Series):
        """
        Add historical price data for an instrument

        Args:
            instrument: Instrument name
            prices: Series of historical prices (DatetimeIndex)
        """
        self.correlation_data[instrument] = prices
        logger.debug(f"Added price data for {instrument}: {len(prices)} points")

    def calculate_correlation(
        self,
        instrument1: str,
        instrument2: str,
        use_returns: bool = True
    ) -> float:
        """
        Calculate correlation between two instruments

        Args:
            instrument1: First instrument
            instrument2: Second instrument
            use_returns: Use returns instead of prices (more accurate)

        Returns:
            Correlation coefficient (-1 to 1)
        """
        # Check known correlations first
        pair = tuple(sorted([instrument1, instrument2]))
        if pair in self.KNOWN_CORRELATIONS:
            logger.debug(f"Using known correlation for {pair}: {self.KNOWN_CORRELATIONS[pair]}")
            return self.KNOWN_CORRELATIONS[pair]

        # Calculate from data
        if instrument1 not in self.correlation_data or instrument2 not in self.correlation_data:
            logger.warning(f"Missing data for correlation calculation: {instrument1}, {instrument2}")
            return 0.0

        prices1 = self.correlation_data[instrument1]
        prices2 = self.correlation_data[instrument2]

        # Align data by date
        df = pd.DataFrame({
            instrument1: prices1,
            instrument2: prices2
        }).dropna()

        if len(df) < 10:
            logger.warning(f"Insufficient data for correlation: {len(df)} points")
            return 0.0

        if use_returns:
            # Calculate returns
            returns = df.pct_change().dropna()
            if len(returns) == 0:
                return 0.0
            correlation = returns[instrument1].corr(returns[instrument2])
        else:
            correlation = df[instrument1].corr(df[instrument2])

        logger.debug(f"Calculated correlation {instrument1}-{instrument2}: {correlation:.3f}")
        return correlation

    def build_correlation_matrix(self, instruments: List[str]) -> pd.DataFrame:
        """
        Build full correlation matrix for multiple instruments

        Args:
            instruments: List of instrument names

        Returns:
            DataFrame with correlation matrix
        """
        n = len(instruments)
        matrix = np.zeros((n, n))

        for i, inst1 in enumerate(instruments):
            for j, inst2 in enumerate(instruments):
                if i == j:
                    matrix[i, j] = 1.0  # Perfect correlation with itself
                else:
                    matrix[i, j] = self.calculate_correlation(inst1, inst2)

        self.correlation_matrix = pd.DataFrame(
            matrix,
            index=instruments,
            columns=instruments
        )

        logger.info(f"Built correlation matrix for {n} instruments")
        return self.correlation_matrix

    def get_correlated_instruments(
        self,
        instrument: str,
        threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        Get list of instruments correlated with given instrument

        Args:
            instrument: Instrument to check
            threshold: Correlation threshold (uses default if None)

        Returns:
            List of tuples (instrument, correlation)
        """
        if threshold is None:
            threshold = self.correlation_threshold

        correlated = []

        # Check from correlation matrix if available
        if not self.correlation_matrix.empty and instrument in self.correlation_matrix.index:
            row = self.correlation_matrix.loc[instrument]
            for other_inst, corr in row.items():
                if other_inst != instrument and abs(corr) >= threshold:
                    correlated.append((other_inst, corr))

        # Check known correlations
        for (inst1, inst2), corr in self.KNOWN_CORRELATIONS.items():
            if instrument in (inst1, inst2) and abs(corr) >= threshold:
                other = inst2 if instrument == inst1 else inst1
                if not any(c[0] == other for c in correlated):
                    correlated.append((other, corr))

        correlated.sort(key=lambda x: abs(x[1]), reverse=True)
        return correlated

    def check_correlation_risk(
        self,
        new_instrument: str,
        existing_positions: List[Dict],
        account_balance: float
    ) -> Tuple[bool, str, List[str]]:
        """
        Check if adding a position creates excessive correlation risk

        Args:
            new_instrument: Instrument to add
            existing_positions: List of existing positions (each with instrument, risk_amount)
            account_balance: Total account balance

        Returns:
            Tuple of (allowed: bool, message: str, correlated_instruments: List[str])
        """
        correlated_instruments = self.get_correlated_instruments(new_instrument)

        if not correlated_instruments:
            return True, "No significant correlations detected", []

        # Calculate total exposure in correlated instruments
        total_correlated_exposure = 0.0
        instruments_at_risk = []

        for position in existing_positions:
            pos_instrument = position.get('instrument', '')

            # Check if this position is correlated with new instrument
            for corr_inst, corr_value in correlated_instruments:
                if pos_instrument == corr_inst:
                    risk_amount = position.get('risk_amount', 0)
                    risk_pct = (risk_amount / account_balance) * 100
                    total_correlated_exposure += risk_pct
                    instruments_at_risk.append(
                        f"{pos_instrument} (corr: {corr_value:.2f}, risk: {risk_pct:.2f}%)"
                    )

        if total_correlated_exposure > self.max_correlated_exposure:
            msg = (
                f"⚠️  WARNING: Correlated exposure {total_correlated_exposure:.2f}% "
                f"exceeds limit {self.max_correlated_exposure}%. "
                f"Correlated positions: {', '.join(instruments_at_risk)}"
            )
            logger.warning(msg)
            return False, msg, [inst.split(' ')[0] for inst in instruments_at_risk]

        if total_correlated_exposure > self.max_correlated_exposure * 0.7:
            # Warning but not rejection
            msg = (
                f"⚠️  CAUTION: Approaching correlation limit. "
                f"Current: {total_correlated_exposure:.2f}%, "
                f"Limit: {self.max_correlated_exposure}%"
            )
            logger.info(msg)
            return True, msg, [inst.split(' ')[0] for inst in instruments_at_risk]

        msg = f"✅ OK: Correlated exposure {total_correlated_exposure:.2f}% within limits"
        logger.debug(msg)
        return True, msg, []

    def suggest_diversification(
        self,
        existing_positions: List[Dict],
        available_instruments: List[str]
    ) -> List[str]:
        """
        Suggest uncorrelated instruments for diversification

        Args:
            existing_positions: Current positions
            available_instruments: List of tradeable instruments

        Returns:
            List of suggested instruments (low correlation)
        """
        if not existing_positions:
            return available_instruments[:5]  # Return first 5 if no positions

        # Get instruments from existing positions
        existing_instruments = [pos['instrument'] for pos in existing_positions]

        # Find uncorrelated instruments
        suggestions = []
        for instrument in available_instruments:
            if instrument in existing_instruments:
                continue

            # Check correlation with all existing positions
            max_correlation = 0.0
            for existing_inst in existing_instruments:
                corr = abs(self.calculate_correlation(instrument, existing_inst))
                max_correlation = max(max_correlation, corr)

            # Suggest if correlation is low
            if max_correlation < self.correlation_threshold:
                suggestions.append((instrument, max_correlation))

        # Sort by lowest correlation
        suggestions.sort(key=lambda x: x[1])

        # Return top 5
        return [inst for inst, _ in suggestions[:5]]

    def get_correlation_heatmap_data(self) -> Dict:
        """
        Get data for correlation heatmap visualization

        Returns:
            Dictionary with heatmap data
        """
        if self.correlation_matrix.empty:
            return {}

        return {
            'instruments': self.correlation_matrix.index.tolist(),
            'correlations': self.correlation_matrix.values.tolist(),
            'heatmap': self.correlation_matrix.to_dict()
        }

    def rolling_correlation(
        self,
        instrument1: str,
        instrument2: str,
        window: int = 30
    ) -> pd.Series:
        """
        Calculate rolling correlation over time

        Args:
            instrument1: First instrument
            instrument2: Second instrument
            window: Rolling window in days

        Returns:
            Series of rolling correlations
        """
        if instrument1 not in self.correlation_data or instrument2 not in self.correlation_data:
            return pd.Series()

        prices1 = self.correlation_data[instrument1]
        prices2 = self.correlation_data[instrument2]

        df = pd.DataFrame({
            instrument1: prices1,
            instrument2: prices2
        }).dropna()

        returns = df.pct_change().dropna()
        rolling_corr = returns[instrument1].rolling(window).corr(returns[instrument2])

        return rolling_corr

    def detect_correlation_breakdown(
        self,
        instrument1: str,
        instrument2: str,
        threshold_change: float = 0.30
    ) -> Tuple[bool, str]:
        """
        Detect if correlation between instruments has broken down

        Args:
            instrument1: First instrument
            instrument2: Second instrument
            threshold_change: Minimum change to consider breakdown (e.g., 0.30 = 30% drop)

        Returns:
            Tuple of (breakdown_detected: bool, message: str)
        """
        rolling_corr = self.rolling_correlation(instrument1, instrument2, window=30)

        if len(rolling_corr) < 60:
            return False, "Insufficient data for breakdown detection"

        recent_corr = rolling_corr.iloc[-30:].mean()
        historical_corr = rolling_corr.iloc[-60:-30].mean()

        change = abs(recent_corr - historical_corr)

        if change > threshold_change:
            msg = (
                f"⚠️  CORRELATION BREAKDOWN DETECTED: "
                f"{instrument1}-{instrument2} correlation changed from "
                f"{historical_corr:.2f} to {recent_corr:.2f} (Δ{change:.2f})"
            )
            logger.warning(msg)
            return True, msg

        return False, f"Correlation stable: {recent_corr:.2f}"


class RiskLimitEnforcer:
    """
    Enforce hard risk limits across the platform
    Acts as final gatekeeper before any trade
    """

    def __init__(
        self,
        account_balance: float,
        max_portfolio_heat: float = 6.0,
        max_single_position: float = 2.0,
        max_correlated_exposure: float = 10.0,
        max_daily_loss: float = 3.0
    ):
        """
        Initialize risk limit enforcer

        Args:
            account_balance: Account balance
            max_portfolio_heat: Maximum total risk %
            max_single_position: Maximum single position risk %
            max_correlated_exposure: Maximum correlated exposure %
            max_daily_loss: Maximum daily loss % (circuit breaker)
        """
        self.account_balance = account_balance
        self.max_portfolio_heat = max_portfolio_heat
        self.max_single_position = max_single_position
        self.max_correlated_exposure = max_correlated_exposure
        self.max_daily_loss = max_daily_loss

        self.daily_start_balance = account_balance
        self.positions = []

        logger.info("Risk Limit Enforcer initialized with strict limits")

    def pre_trade_check(
        self,
        instrument: str,
        risk_amount: float,
        risk_percent: float,
        correlated_instruments: List[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Perform all pre-trade risk checks

        Args:
            instrument: Instrument to trade
            risk_amount: Risk amount in INR
            risk_percent: Risk as % of account
            correlated_instruments: List of correlated instruments

        Returns:
            Tuple of (approved: bool, reasons: List[str])
        """
        reasons = []
        approved = True

        # Check 1: Single position limit
        if risk_percent > self.max_single_position:
            reasons.append(
                f"❌ Single position risk {risk_percent:.2f}% exceeds "
                f"limit {self.max_single_position}%"
            )
            approved = False

        # Check 2: Portfolio heat
        current_heat = sum(p.get('risk_percent', 0) for p in self.positions)
        new_heat = current_heat + risk_percent
        if new_heat > self.max_portfolio_heat:
            reasons.append(
                f"❌ Portfolio heat {new_heat:.2f}% exceeds "
                f"limit {self.max_portfolio_heat}%"
            )
            approved = False

        # Check 3: Daily loss limit (circuit breaker)
        current_balance = self.account_balance
        daily_loss_pct = ((self.daily_start_balance - current_balance) /
                          self.daily_start_balance) * 100

        if daily_loss_pct > self.max_daily_loss:
            reasons.append(
                f"🛑 CIRCUIT BREAKER: Daily loss {daily_loss_pct:.2f}% exceeds "
                f"limit {self.max_daily_loss}%. STOP TRADING FOR TODAY."
            )
            approved = False

        # Check 4: Correlation exposure (if provided)
        if correlated_instruments:
            correlated_risk = sum(
                p.get('risk_percent', 0)
                for p in self.positions
                if p.get('instrument') in correlated_instruments
            )
            if correlated_risk > self.max_correlated_exposure:
                reasons.append(
                    f"⚠️  Correlated exposure {correlated_risk:.2f}% exceeds "
                    f"limit {self.max_correlated_exposure}%"
                )
                approved = False

        if approved:
            reasons.append("✅ All risk checks passed - TRADE APPROVED")

        return approved, reasons

    def reset_daily_limits(self):
        """Reset daily limits (call at start of each trading day)"""
        self.daily_start_balance = self.account_balance
        logger.info(f"Daily limits reset. Starting balance: ₹{self.account_balance:,.2f}")
