"""
Options Strategy Builder - Battle-tested option strategies
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum


class OptionType(Enum):
    """Option types"""
    CALL = "CE"
    PUT = "PE"


class OptionsStrategyBuilder:
    """
    Build and analyze common options strategies

    Strategies:
    - Iron Condor (Range-bound markets)
    - Bull Call Spread (Moderate bullish)
    - Bear Put Spread (Moderate bearish)
    - Long Straddle (High volatility expected)
    - Short Strangle (Low volatility expected)
    - Calendar Spread (Time decay)
    - Butterfly Spread (Narrow range)
    """

    def __init__(self, spot_price: float, lot_size: int = 50):
        """
        Initialize strategy builder

        Args:
            spot_price: Current spot price
            lot_size: Lot size for the instrument
        """
        self.spot_price = spot_price
        self.lot_size = lot_size

    def iron_condor(
        self,
        iv_rank: float,
        target_premium: float = 10000,
        wing_width: int = 100,
        expiry_days: int = 30
    ) -> Dict:
        """
        Iron Condor - Sell OTM call & put, buy further OTM for protection

        Best for: Range-bound markets with IV Rank > 50

        Args:
            iv_rank: Implied volatility rank (0-100)
            target_premium: Target premium to collect
            wing_width: Width between short and long strikes
            expiry_days: Days to expiry

        Returns:
            Strategy details
        """
        if iv_rank < 50:
            return {
                'warning': 'Iron Condor works best when IV Rank > 50',
                'recommended': False
            }

        # Calculate strikes (symmetric around spot)
        # Sell calls and puts at ~1 SD
        call_short_strike = self._round_strike(self.spot_price * 1.05)
        put_short_strike = self._round_strike(self.spot_price * 0.95)

        # Buy protection
        call_long_strike = call_short_strike + wing_width
        put_long_strike = put_short_strike - wing_width

        # Estimated premiums (simplified)
        call_premium_short = self.spot_price * 0.02  # 2%
        call_premium_long = self.spot_price * 0.01   # 1%
        put_premium_short = self.spot_price * 0.02
        put_premium_long = self.spot_price * 0.01

        net_premium = (call_premium_short - call_premium_long +
                      put_premium_short - put_premium_long) * self.lot_size

        max_loss = (wing_width - (call_premium_short - call_premium_long)) * self.lot_size

        return {
            'strategy': 'Iron Condor',
            'market_outlook': 'Range-bound',
            'legs': [
                {
                    'action': 'SELL',
                    'type': 'CALL',
                    'strike': call_short_strike,
                    'premium': call_premium_short
                },
                {
                    'action': 'BUY',
                    'type': 'CALL',
                    'strike': call_long_strike,
                    'premium': call_premium_long
                },
                {
                    'action': 'SELL',
                    'type': 'PUT',
                    'strike': put_short_strike,
                    'premium': put_premium_short
                },
                {
                    'action': 'BUY',
                    'type': 'PUT',
                    'strike': put_long_strike,
                    'premium': put_premium_long
                }
            ],
            'net_premium_collected': round(net_premium, 2),
            'max_profit': round(net_premium, 2),
            'max_loss': round(max_loss, 2),
            'risk_reward_ratio': round(max_loss / net_premium, 2) if net_premium > 0 else 0,
            'breakeven_upper': call_short_strike + (net_premium / self.lot_size),
            'breakeven_lower': put_short_strike - (net_premium / self.lot_size),
            'probability_of_profit': 70,  # Approximate
            'expiry_days': expiry_days,
            'recommended': True
        }

    def bull_call_spread(
        self,
        target_gain_pct: float = 5,
        expiry_days: int = 30
    ) -> Dict:
        """
        Bull Call Spread - Buy ATM call, sell OTM call

        Best for: Moderately bullish outlook

        Args:
            target_gain_pct: Expected gain percentage
            expiry_days: Days to expiry

        Returns:
            Strategy details
        """
        # Buy ATM call
        call_long_strike = self._round_strike(self.spot_price)

        # Sell OTM call at target
        call_short_strike = self._round_strike(
            self.spot_price * (1 + target_gain_pct / 100)
        )

        # Estimated premiums
        call_premium_long = self.spot_price * 0.03  # 3% ATM
        call_premium_short = self.spot_price * 0.015  # 1.5% OTM

        net_debit = (call_premium_long - call_premium_short) * self.lot_size
        max_profit = (call_short_strike - call_long_strike -
                     (call_premium_long - call_premium_short)) * self.lot_size

        return {
            'strategy': 'Bull Call Spread',
            'market_outlook': 'Moderately Bullish',
            'legs': [
                {
                    'action': 'BUY',
                    'type': 'CALL',
                    'strike': call_long_strike,
                    'premium': call_premium_long
                },
                {
                    'action': 'SELL',
                    'type': 'CALL',
                    'strike': call_short_strike,
                    'premium': call_premium_short
                }
            ],
            'net_debit': round(net_debit, 2),
            'max_profit': round(max_profit, 2),
            'max_loss': round(net_debit, 2),
            'risk_reward_ratio': round(max_profit / net_debit, 2) if net_debit > 0 else 0,
            'breakeven': call_long_strike + (net_debit / self.lot_size),
            'expiry_days': expiry_days,
            'recommended': True
        }

    def bear_put_spread(
        self,
        target_drop_pct: float = 5,
        expiry_days: int = 30
    ) -> Dict:
        """
        Bear Put Spread - Buy ATM put, sell OTM put

        Best for: Moderately bearish outlook

        Args:
            target_drop_pct: Expected drop percentage
            expiry_days: Days to expiry

        Returns:
            Strategy details
        """
        # Buy ATM put
        put_long_strike = self._round_strike(self.spot_price)

        # Sell OTM put at target
        put_short_strike = self._round_strike(
            self.spot_price * (1 - target_drop_pct / 100)
        )

        # Estimated premiums
        put_premium_long = self.spot_price * 0.03  # 3% ATM
        put_premium_short = self.spot_price * 0.015  # 1.5% OTM

        net_debit = (put_premium_long - put_premium_short) * self.lot_size
        max_profit = (put_long_strike - put_short_strike -
                     (put_premium_long - put_premium_short)) * self.lot_size

        return {
            'strategy': 'Bear Put Spread',
            'market_outlook': 'Moderately Bearish',
            'legs': [
                {
                    'action': 'BUY',
                    'type': 'PUT',
                    'strike': put_long_strike,
                    'premium': put_premium_long
                },
                {
                    'action': 'SELL',
                    'type': 'PUT',
                    'strike': put_short_strike,
                    'premium': put_premium_short
                }
            ],
            'net_debit': round(net_debit, 2),
            'max_profit': round(max_profit, 2),
            'max_loss': round(net_debit, 2),
            'risk_reward_ratio': round(max_profit / net_debit, 2) if net_debit > 0 else 0,
            'breakeven': put_long_strike - (net_debit / self.lot_size),
            'expiry_days': expiry_days,
            'recommended': True
        }

    def long_straddle(
        self,
        iv_rank: float,
        days_to_event: int = 7,
        expiry_days: int = 30
    ) -> Dict:
        """
        Long Straddle - Buy ATM call and put

        Best for: Expecting big move, low IV

        Args:
            iv_rank: Implied volatility rank
            days_to_event: Days until major event
            expiry_days: Days to expiry

        Returns:
            Strategy details
        """
        if iv_rank > 50:
            return {
                'warning': 'Long Straddle expensive when IV Rank > 50. Consider waiting.',
                'recommended': False
            }

        strike = self._round_strike(self.spot_price)

        # Premiums for ATM options
        call_premium = self.spot_price * 0.03
        put_premium = self.spot_price * 0.03

        total_debit = (call_premium + put_premium) * self.lot_size

        # Breakevens
        breakeven_upper = strike + (total_debit / self.lot_size)
        breakeven_lower = strike - (total_debit / self.lot_size)

        return {
            'strategy': 'Long Straddle',
            'market_outlook': 'Big move expected (direction unknown)',
            'legs': [
                {
                    'action': 'BUY',
                    'type': 'CALL',
                    'strike': strike,
                    'premium': call_premium
                },
                {
                    'action': 'BUY',
                    'type': 'PUT',
                    'strike': strike,
                    'premium': put_premium
                }
            ],
            'total_debit': round(total_debit, 2),
            'max_profit': 'Unlimited',
            'max_loss': round(total_debit, 2),
            'breakeven_upper': round(breakeven_upper, 2),
            'breakeven_lower': round(breakeven_lower, 2),
            'expiry_days': expiry_days,
            'recommended': True if iv_rank < 30 else False
        }

    def short_strangle(
        self,
        iv_rank: float,
        expiry_days: int = 30,
        delta_target: float = 0.20
    ) -> Dict:
        """
        Short Strangle - Sell OTM call and put

        Best for: Range-bound market, high IV

        Args:
            iv_rank: Implied volatility rank
            expiry_days: Days to expiry
            delta_target: Target delta for strikes (~0.20)

        Returns:
            Strategy details
        """
        if iv_rank < 50:
            return {
                'warning': 'Short Strangle works best when IV Rank > 50',
                'recommended': False
            }

        # Sell OTM options at ~20 delta
        call_strike = self._round_strike(self.spot_price * 1.10)
        put_strike = self._round_strike(self.spot_price * 0.90)

        # Premiums
        call_premium = self.spot_price * 0.015
        put_premium = self.spot_price * 0.015

        total_premium = (call_premium + put_premium) * self.lot_size

        return {
            'strategy': 'Short Strangle',
            'market_outlook': 'Range-bound, low volatility expected',
            'legs': [
                {
                    'action': 'SELL',
                    'type': 'CALL',
                    'strike': call_strike,
                    'premium': call_premium
                },
                {
                    'action': 'SELL',
                    'type': 'PUT',
                    'strike': put_strike,
                    'premium': put_premium
                }
            ],
            'premium_collected': round(total_premium, 2),
            'max_profit': round(total_premium, 2),
            'max_loss': 'Unlimited (use stops!)',
            'breakeven_upper': call_strike + (total_premium / self.lot_size),
            'breakeven_lower': put_strike - (total_premium / self.lot_size),
            'expiry_days': expiry_days,
            'recommended': True,
            'warning': 'Undefined risk - use strict stop losses'
        }

    def calendar_spread(
        self,
        strike: float = None,
        near_expiry_days: int = 7,
        far_expiry_days: int = 30
    ) -> Dict:
        """
        Calendar Spread - Sell near-term, buy far-term

        Best for: Profiting from time decay

        Args:
            strike: Strike price (default: ATM)
            near_expiry_days: Days to near expiry
            far_expiry_days: Days to far expiry

        Returns:
            Strategy details
        """
        if strike is None:
            strike = self._round_strike(self.spot_price)

        # Near-term option (higher theta)
        near_premium = self.spot_price * 0.015

        # Far-term option (lower theta but more premium)
        far_premium = self.spot_price * 0.025

        net_debit = (far_premium - near_premium) * self.lot_size

        return {
            'strategy': 'Calendar Spread',
            'market_outlook': 'Neutral - profit from time decay',
            'legs': [
                {
                    'action': 'SELL',
                    'type': 'CALL',
                    'strike': strike,
                    'expiry_days': near_expiry_days,
                    'premium': near_premium
                },
                {
                    'action': 'BUY',
                    'type': 'CALL',
                    'strike': strike,
                    'expiry_days': far_expiry_days,
                    'premium': far_premium
                }
            ],
            'net_debit': round(net_debit, 2),
            'max_profit': 'Variable (depends on vol)',
            'max_loss': round(net_debit, 2),
            'best_case': 'Price stays near strike at near expiry',
            'near_expiry': near_expiry_days,
            'far_expiry': far_expiry_days,
            'recommended': True
        }

    def butterfly_spread(
        self,
        wing_width: int = 100,
        expiry_days: int = 30
    ) -> Dict:
        """
        Butterfly Spread - Limited risk, limited profit

        Best for: Expecting price to stay in narrow range

        Args:
            wing_width: Width between strikes
            expiry_days: Days to expiry

        Returns:
            Strategy details
        """
        # ATM strike
        middle_strike = self._round_strike(self.spot_price)

        # Wings
        lower_strike = middle_strike - wing_width
        upper_strike = middle_strike + wing_width

        # Premiums
        lower_premium = self.spot_price * 0.04  # ITM
        middle_premium = self.spot_price * 0.02  # ATM
        upper_premium = self.spot_price * 0.01  # OTM

        net_debit = (lower_premium - 2 * middle_premium + upper_premium) * self.lot_size
        max_profit = (wing_width - net_debit / self.lot_size) * self.lot_size

        return {
            'strategy': 'Butterfly Spread',
            'market_outlook': 'Neutral - narrow range expected',
            'legs': [
                {
                    'action': 'BUY',
                    'type': 'CALL',
                    'strike': lower_strike,
                    'premium': lower_premium
                },
                {
                    'action': 'SELL',
                    'type': 'CALL',
                    'strike': middle_strike,
                    'quantity': 2,
                    'premium': middle_premium
                },
                {
                    'action': 'BUY',
                    'type': 'CALL',
                    'strike': upper_strike,
                    'premium': upper_premium
                }
            ],
            'net_debit': round(net_debit, 2),
            'max_profit': round(max_profit, 2),
            'max_loss': round(net_debit, 2),
            'breakeven_lower': lower_strike + (net_debit / self.lot_size),
            'breakeven_upper': upper_strike - (net_debit / self.lot_size),
            'expiry_days': expiry_days,
            'recommended': True
        }

    def _round_strike(self, price: float, base: int = 50) -> float:
        """Round price to nearest strike"""
        return round(price / base) * base

    def suggest_strategy(
        self,
        market_regime: str,
        iv_rank: float,
        outlook: str = 'neutral'
    ) -> Dict:
        """
        Suggest best strategy based on conditions

        Args:
            market_regime: Market regime (trending/ranging/volatile)
            iv_rank: Implied volatility rank (0-100)
            outlook: Bullish/Bearish/Neutral

        Returns:
            Recommended strategy
        """
        outlook = outlook.lower()

        # High IV strategies (sell premium)
        if iv_rank > 60:
            if outlook == 'neutral':
                return self.iron_condor(iv_rank)
            elif outlook == 'bullish':
                return {
                    'suggestion': 'Bull Put Spread',
                    'reason': 'High IV - sell puts below support'
                }
            elif outlook == 'bearish':
                return {
                    'suggestion': 'Bear Call Spread',
                    'reason': 'High IV - sell calls above resistance'
                }

        # Low IV strategies (buy premium)
        elif iv_rank < 30:
            if outlook == 'neutral':
                return self.long_straddle(iv_rank)
            elif outlook == 'bullish':
                return self.bull_call_spread()
            elif outlook == 'bearish':
                return self.bear_put_spread()

        # Medium IV
        else:
            if outlook == 'bullish':
                return self.bull_call_spread()
            elif outlook == 'bearish':
                return self.bear_put_spread()
            else:
                return self.iron_condor(iv_rank)

    def print_strategy_details(self, strategy: Dict):
        """Print formatted strategy details"""
        print("\n" + "=" * 70)
        print(f"STRATEGY: {strategy.get('strategy', 'Unknown')}")
        print("=" * 70)

        print(f"\nMarket Outlook: {strategy.get('market_outlook', 'N/A')}")

        if 'warning' in strategy:
            print(f"\n⚠️  WARNING: {strategy['warning']}")

        print("\nStrategy Legs:")
        for i, leg in enumerate(strategy.get('legs', []), 1):
            qty = leg.get('quantity', 1)
            print(f"  {i}. {leg['action']} {qty}x {leg['type']} @ Strike {leg['strike']}")
            if 'premium' in leg:
                print(f"     Premium: ₹{leg['premium']:.2f}")

        print("\nP&L Profile:")
        if 'net_debit' in strategy:
            print(f"  Net Debit:     ₹{strategy['net_debit']:,.2f}")
        if 'net_premium_collected' in strategy:
            print(f"  Premium:       ₹{strategy['net_premium_collected']:,.2f}")
        if 'max_profit' in strategy:
            max_profit_str = strategy['max_profit'] if isinstance(strategy['max_profit'], str) else f"₹{strategy['max_profit']:,.2f}"
            print(f"  Max Profit:    {max_profit_str}")
        if 'max_loss' in strategy:
            max_loss_str = strategy['max_loss'] if isinstance(strategy['max_loss'], str) else f"₹{strategy['max_loss']:,.2f}"
            print(f"  Max Loss:      {max_loss_str}")

        if 'breakeven' in strategy:
            print(f"\nBreakeven:       ₹{strategy['breakeven']:.2f}")
        if 'breakeven_upper' in strategy:
            print(f"\nBreakevens:")
            print(f"  Upper:         ₹{strategy['breakeven_upper']:.2f}")
            print(f"  Lower:         ₹{strategy['breakeven_lower']:.2f}")

        print("\n" + "=" * 70)
