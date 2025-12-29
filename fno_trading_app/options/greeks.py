"""
Options Greeks Calculator
Black-Scholes model for calculating option Greeks
Professional-grade options analysis
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OptionType(Enum):
    """Option types"""
    CALL = "CALL"
    PUT = "PUT"


class GreeksCalculator:
    """
    Calculate options Greeks using Black-Scholes model

    Greeks are the risk measures for options:
    - Delta: Rate of change of option price with respect to underlying
    - Gamma: Rate of change of delta
    - Theta: Time decay
    - Vega: Sensitivity to volatility changes
    - Rho: Sensitivity to interest rate changes
    """

    def __init__(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,  # In years
        volatility: float,  # Implied volatility as decimal (e.g., 0.20 for 20%)
        interest_rate: float = 0.06,  # Risk-free rate (6% for India)
        option_type: OptionType = OptionType.CALL
    ):
        """
        Initialize Greeks calculator

        Args:
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years (e.g., 30 days = 30/365)
            volatility: Implied volatility (as decimal)
            interest_rate: Risk-free interest rate (as decimal)
            option_type: CALL or PUT
        """
        self.S = spot_price
        self.K = strike_price
        self.T = time_to_expiry
        self.sigma = volatility
        self.r = interest_rate
        self.option_type = option_type

        # Validation
        if self.T <= 0:
            raise ValueError("Time to expiry must be positive")
        if self.sigma <= 0:
            raise ValueError("Volatility must be positive")
        if self.S <= 0 or self.K <= 0:
            raise ValueError("Prices must be positive")

        logger.debug(
            f"Greeks calculator initialized: S={spot_price}, K={strike_price}, "
            f"T={time_to_expiry:.4f}y, σ={volatility:.2%}, Type={option_type.value}"
        )

    def _d1(self) -> float:
        """Calculate d1 from Black-Scholes formula"""
        return (np.log(self.S / self.K) + (self.r + 0.5 * self.sigma ** 2) * self.T) / \
               (self.sigma * np.sqrt(self.T))

    def _d2(self) -> float:
        """Calculate d2 from Black-Scholes formula"""
        return self._d1() - self.sigma * np.sqrt(self.T)

    def option_price(self) -> float:
        """
        Calculate theoretical option price using Black-Scholes

        Returns:
            Option price
        """
        d1 = self._d1()
        d2 = self._d2()

        if self.option_type == OptionType.CALL:
            price = (self.S * stats.norm.cdf(d1) -
                     self.K * np.exp(-self.r * self.T) * stats.norm.cdf(d2))
        else:  # PUT
            price = (self.K * np.exp(-self.r * self.T) * stats.norm.cdf(-d2) -
                     self.S * stats.norm.cdf(-d1))

        return price

    def delta(self) -> float:
        """
        Calculate Delta (∂V/∂S)

        Delta measures the rate of change of option price with respect to underlying price

        Call Delta: 0 to 1 (typically 0.30 to 0.70 for ATM)
        Put Delta: -1 to 0

        Interpretation:
        - Delta 0.50 means option moves ₹0.50 for every ₹1 move in underlying
        - Also represents hedge ratio (delta-neutral hedging)

        Returns:
            Delta value
        """
        d1 = self._d1()

        if self.option_type == OptionType.CALL:
            delta = stats.norm.cdf(d1)
        else:  # PUT
            delta = stats.norm.cdf(d1) - 1

        return delta

    def gamma(self) -> float:
        """
        Calculate Gamma (∂²V/∂S²)

        Gamma measures the rate of change of delta
        Same for calls and puts

        Interpretation:
        - High gamma means delta changes quickly
        - ATM options have highest gamma
        - Gamma is highest near expiration

        Returns:
            Gamma value
        """
        d1 = self._d1()
        gamma = stats.norm.pdf(d1) / (self.S * self.sigma * np.sqrt(self.T))

        return gamma

    def theta(self) -> float:
        """
        Calculate Theta (∂V/∂t)

        Theta measures time decay (per day)
        Negative for long options (you lose money each day)

        Interpretation:
        - Theta of -45 means option loses ₹45 per day
        - Time decay accelerates near expiration
        - ATM options have highest theta

        Returns:
            Theta per day (negative for long options)
        """
        d1 = self._d1()
        d2 = self._d2()

        if self.option_type == OptionType.CALL:
            theta = (-self.S * stats.norm.pdf(d1) * self.sigma / (2 * np.sqrt(self.T)) -
                     self.r * self.K * np.exp(-self.r * self.T) * stats.norm.cdf(d2))
        else:  # PUT
            theta = (-self.S * stats.norm.pdf(d1) * self.sigma / (2 * np.sqrt(self.T)) +
                     self.r * self.K * np.exp(-self.r * self.T) * stats.norm.cdf(-d2))

        # Convert to per-day theta
        theta_per_day = theta / 365

        return theta_per_day

    def vega(self) -> float:
        """
        Calculate Vega (∂V/∂σ)

        Vega measures sensitivity to 1% change in implied volatility
        Same for calls and puts

        Interpretation:
        - Vega of 12 means option gains ₹12 if IV increases by 1%
        - Long options have positive vega (benefit from vol increase)
        - Short options have negative vega

        Returns:
            Vega (per 1% IV change)
        """
        d1 = self._d1()
        vega = self.S * stats.norm.pdf(d1) * np.sqrt(self.T) / 100

        return vega

    def rho(self) -> float:
        """
        Calculate Rho (∂V/∂r)

        Rho measures sensitivity to 1% change in interest rates
        Least important Greek in practice

        Returns:
            Rho (per 1% interest rate change)
        """
        d2 = self._d2()

        if self.option_type == OptionType.CALL:
            rho = self.K * self.T * np.exp(-self.r * self.T) * stats.norm.cdf(d2) / 100
        else:  # PUT
            rho = -self.K * self.T * np.exp(-self.r * self.T) * stats.norm.cdf(-d2) / 100

        return rho

    def all_greeks(self) -> Dict[str, float]:
        """
        Calculate all Greeks at once

        Returns:
            Dictionary with all Greeks
        """
        greeks = {
            'price': self.option_price(),
            'delta': self.delta(),
            'gamma': self.gamma(),
            'theta': self.theta(),
            'vega': self.vega(),
            'rho': self.rho(),
            'spot': self.S,
            'strike': self.K,
            'time_to_expiry_years': self.T,
            'time_to_expiry_days': self.T * 365,
            'volatility': self.sigma,
            'option_type': self.option_type.value
        }

        return greeks

    def moneyness(self) -> str:
        """
        Determine if option is ITM, ATM, or OTM

        Returns:
            Moneyness classification
        """
        ratio = self.S / self.K

        if self.option_type == OptionType.CALL:
            if ratio > 1.02:
                return "ITM"  # In the money
            elif ratio < 0.98:
                return "OTM"  # Out of the money
            else:
                return "ATM"  # At the money
        else:  # PUT
            if ratio < 0.98:
                return "ITM"
            elif ratio > 1.02:
                return "OTM"
            else:
                return "ATM"

    @staticmethod
    def implied_volatility(
        option_price: float,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        option_type: OptionType,
        interest_rate: float = 0.06,
        initial_guess: float = 0.20,
        max_iterations: int = 100,
        tolerance: float = 0.0001
    ) -> Optional[float]:
        """
        Calculate implied volatility using Newton-Raphson method

        Given an option price, find the volatility that produces that price

        Args:
            option_price: Market price of option
            spot_price: Current price of underlying
            strike_price: Strike price
            time_to_expiry: Time to expiry in years
            option_type: CALL or PUT
            interest_rate: Risk-free rate
            initial_guess: Starting volatility guess
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance

        Returns:
            Implied volatility (or None if didn't converge)
        """
        sigma = initial_guess

        for i in range(max_iterations):
            # Calculate price with current sigma
            calc = GreeksCalculator(
                spot_price, strike_price, time_to_expiry,
                sigma, interest_rate, option_type
            )

            calc_price = calc.option_price()
            vega = calc.vega() * 100  # Convert back from per-1%

            # Newton-Raphson update
            price_diff = calc_price - option_price

            if abs(price_diff) < tolerance:
                return sigma

            if vega == 0:
                return None  # Cannot converge

            sigma = sigma - price_diff / vega

            # Keep sigma positive
            sigma = max(0.01, min(sigma, 3.0))  # Cap between 1% and 300%

        logger.warning(f"IV calculation did not converge after {max_iterations} iterations")
        return None

    def delta_equivalent_futures(self, lot_size: int = 50) -> float:
        """
        Calculate equivalent futures position for this option

        Useful for delta-neutral hedging

        Args:
            lot_size: Futures lot size

        Returns:
            Number of futures lots needed
        """
        return self.delta() * lot_size

    def gamma_risk(self) -> str:
        """
        Assess gamma risk level

        Returns:
            Risk assessment string
        """
        gamma = self.gamma()

        if gamma > 0.02:
            return "HIGH - Delta will change rapidly"
        elif gamma > 0.01:
            return "MODERATE - Monitor delta closely"
        else:
            return "LOW - Delta relatively stable"

    def theta_per_week(self) -> float:
        """Calculate theta decay per week"""
        return self.theta() * 7

    def intrinsic_value(self) -> float:
        """Calculate intrinsic value"""
        if self.option_type == OptionType.CALL:
            return max(0, self.S - self.K)
        else:  # PUT
            return max(0, self.K - self.S)

    def time_value(self) -> float:
        """Calculate time value (extrinsic value)"""
        return self.option_price() - self.intrinsic_value()

    def break_even_price(self, premium_paid: float) -> float:
        """
        Calculate break-even price at expiration

        Args:
            premium_paid: Premium paid for the option

        Returns:
            Break-even underlying price
        """
        if self.option_type == OptionType.CALL:
            return self.K + premium_paid
        else:  # PUT
            return self.K - premium_paid

    def profit_loss_at_expiry(self, spot_at_expiry: float, premium_paid: float) -> float:
        """
        Calculate P&L at expiration for given spot price

        Args:
            spot_at_expiry: Underlying price at expiration
            premium_paid: Premium paid for option

        Returns:
            Profit/Loss
        """
        if self.option_type == OptionType.CALL:
            intrinsic = max(0, spot_at_expiry - self.K)
        else:  # PUT
            intrinsic = max(0, self.K - spot_at_expiry)

        pnl = intrinsic - premium_paid
        return pnl


def calculate_time_to_expiry(expiry_date: datetime, current_date: Optional[datetime] = None) -> float:
    """
    Calculate time to expiry in years

    Args:
        expiry_date: Option expiry date
        current_date: Current date (uses now if None)

    Returns:
        Time to expiry in years
    """
    if current_date is None:
        current_date = datetime.now()

    days_to_expiry = (expiry_date - current_date).days
    years_to_expiry = days_to_expiry / 365

    return max(years_to_expiry, 1/365)  # Minimum 1 day


def create_greeks_from_days(
    spot_price: float,
    strike_price: float,
    days_to_expiry: int,
    volatility: float,
    option_type: OptionType,
    interest_rate: float = 0.06
) -> GreeksCalculator:
    """
    Convenience function to create Greeks calculator from days to expiry

    Args:
        spot_price: Current price of underlying
        strike_price: Strike price
        days_to_expiry: Days until expiration
        volatility: Implied volatility (as decimal)
        option_type: CALL or PUT
        interest_rate: Risk-free rate

    Returns:
        GreeksCalculator instance
    """
    time_to_expiry = days_to_expiry / 365

    return GreeksCalculator(
        spot_price=spot_price,
        strike_price=strike_price,
        time_to_expiry=time_to_expiry,
        volatility=volatility,
        interest_rate=interest_rate,
        option_type=option_type
    )
