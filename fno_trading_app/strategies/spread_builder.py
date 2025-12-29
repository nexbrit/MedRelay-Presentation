"""
Spread Builder for complex multi-leg strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


@dataclass
class Leg:
    """Single leg of a spread"""
    action: str  # BUY or SELL
    instrument_type: str  # CE, PE, FUT
    strike: Optional[float] = None
    expiry: Optional[str] = None
    quantity: int = 1
    premium: Optional[float] = None


class SpreadType(Enum):
    """Types of spreads"""
    VERTICAL = "vertical"  # Same expiry, different strikes
    HORIZONTAL = "horizontal"  # Same strike, different expiries
    DIAGONAL = "diagonal"  # Different strikes and expiries
    RATIO = "ratio"  # Unequal quantities


class SpreadBuilder:
    """
    Build and analyze complex option spreads

    Features:
    - Vertical spreads (Bull/Bear)
    - Horizontal spreads (Calendar)
    - Diagonal spreads
    - Ratio spreads
    - Custom multi-leg strategies
    """

    def __init__(self, spot_price: float, lot_size: int = 50):
        """
        Initialize spread builder

        Args:
            spot_price: Current spot price
            lot_size: Standard lot size
        """
        self.spot_price = spot_price
        self.lot_size = lot_size
        self.legs: List[Leg] = []

    def add_leg(
        self,
        action: str,
        instrument_type: str,
        strike: Optional[float] = None,
        expiry: Optional[str] = None,
        quantity: int = 1,
        premium: Optional[float] = None
    ):
        """
        Add a leg to the spread

        Args:
            action: BUY or SELL
            instrument_type: CE, PE, or FUT
            strike: Strike price
            expiry: Expiry date
            quantity: Number of lots
            premium: Option premium
        """
        leg = Leg(
            action=action.upper(),
            instrument_type=instrument_type.upper(),
            strike=strike,
            expiry=expiry,
            quantity=quantity,
            premium=premium
        )
        self.legs.append(leg)

    def clear_legs(self):
        """Clear all legs"""
        self.legs = []

    def build_bull_call_debit_spread(
        self,
        long_strike: float,
        short_strike: float,
        long_premium: float,
        short_premium: float,
        quantity: int = 1
    ) -> Dict:
        """
        Build bull call debit spread

        Args:
            long_strike: Long call strike (lower)
            short_strike: Short call strike (higher)
            long_premium: Premium for long call
            short_premium: Premium for short call
            quantity: Number of spreads

        Returns:
            Spread analysis
        """
        self.clear_legs()

        self.add_leg('BUY', 'CE', long_strike, premium=long_premium, quantity=quantity)
        self.add_leg('SELL', 'CE', short_strike, premium=short_premium, quantity=quantity)

        return self.analyze_spread()

    def build_bear_put_debit_spread(
        self,
        long_strike: float,
        short_strike: float,
        long_premium: float,
        short_premium: float,
        quantity: int = 1
    ) -> Dict:
        """
        Build bear put debit spread

        Args:
            long_strike: Long put strike (higher)
            short_strike: Short put strike (lower)
            long_premium: Premium for long put
            short_premium: Premium for short put
            quantity: Number of spreads

        Returns:
            Spread analysis
        """
        self.clear_legs()

        self.add_leg('BUY', 'PE', long_strike, premium=long_premium, quantity=quantity)
        self.add_leg('SELL', 'PE', short_strike, premium=short_premium, quantity=quantity)

        return self.analyze_spread()

    def build_ratio_spread(
        self,
        long_strike: float,
        short_strike: float,
        long_quantity: int,
        short_quantity: int,
        option_type: str = 'CE',
        long_premium: float = None,
        short_premium: float = None
    ) -> Dict:
        """
        Build ratio spread (unequal quantities)

        Example: Buy 1 ATM call, Sell 2 OTM calls

        Args:
            long_strike: Long option strike
            short_strike: Short option strike
            long_quantity: Number of long options
            short_quantity: Number of short options
            option_type: CE or PE
            long_premium: Long option premium
            short_premium: Short option premium

        Returns:
            Spread analysis
        """
        self.clear_legs()

        self.add_leg('BUY', option_type, long_strike,
                    premium=long_premium, quantity=long_quantity)
        self.add_leg('SELL', option_type, short_strike,
                    premium=short_premium, quantity=short_quantity)

        analysis = self.analyze_spread()
        analysis['ratio'] = f"{short_quantity}:{long_quantity}"
        analysis['warning'] = "Ratio spreads have unlimited risk on one side"

        return analysis

    def build_box_spread(
        self,
        lower_strike: float,
        upper_strike: float,
        call_long_premium: float,
        call_short_premium: float,
        put_long_premium: float,
        put_short_premium: float
    ) -> Dict:
        """
        Build box spread (arbitrage strategy)

        Combination of bull call spread and bear put spread

        Args:
            lower_strike: Lower strike price
            upper_strike: Upper strike price
            call_long_premium: Long call premium
            call_short_premium: Short call premium
            put_long_premium: Long put premium
            put_short_premium: Short put premium

        Returns:
            Spread analysis
        """
        self.clear_legs()

        # Bull call spread
        self.add_leg('BUY', 'CE', lower_strike, premium=call_long_premium)
        self.add_leg('SELL', 'CE', upper_strike, premium=call_short_premium)

        # Bear put spread
        self.add_leg('BUY', 'PE', upper_strike, premium=put_long_premium)
        self.add_leg('SELL', 'PE', lower_strike, premium=put_short_premium)

        analysis = self.analyze_spread()
        analysis['strategy_type'] = 'Box Spread (Arbitrage)'
        analysis['note'] = 'Risk-free arbitrage if net debit < strike width'

        return analysis

    def build_iron_butterfly(
        self,
        atm_strike: float,
        wing_width: float,
        atm_call_premium: float,
        atm_put_premium: float,
        otm_call_premium: float,
        otm_put_premium: float
    ) -> Dict:
        """
        Build iron butterfly

        Args:
            atm_strike: ATM strike
            wing_width: Distance to wings
            atm_call_premium: ATM call premium
            atm_put_premium: ATM put premium
            otm_call_premium: OTM call premium
            otm_put_premium: OTM put premium

        Returns:
            Spread analysis
        """
        self.clear_legs()

        otm_call_strike = atm_strike + wing_width
        otm_put_strike = atm_strike - wing_width

        # Sell ATM straddle
        self.add_leg('SELL', 'CE', atm_strike, premium=atm_call_premium)
        self.add_leg('SELL', 'PE', atm_strike, premium=atm_put_premium)

        # Buy OTM protection
        self.add_leg('BUY', 'CE', otm_call_strike, premium=otm_call_premium)
        self.add_leg('BUY', 'PE', otm_put_strike, premium=otm_put_premium)

        return self.analyze_spread()

    def analyze_spread(self) -> Dict:
        """
        Analyze current spread configuration

        Returns:
            Comprehensive spread analysis
        """
        if not self.legs:
            return {'error': 'No legs defined'}

        # Calculate net debit/credit
        net_cashflow = 0
        for leg in self.legs:
            if leg.premium is None:
                continue

            cashflow = leg.premium * leg.quantity * self.lot_size

            if leg.action == 'BUY':
                net_cashflow -= cashflow
            else:  # SELL
                net_cashflow += cashflow

        is_debit_spread = net_cashflow < 0
        is_credit_spread = net_cashflow > 0

        # Calculate max profit and loss (simplified)
        max_profit, max_loss = self._calculate_max_pl()

        # Determine spread type
        spread_type = self._determine_spread_type()

        # Get breakeven points
        breakevens = self._calculate_breakevens()

        return {
            'legs': [
                {
                    'action': leg.action,
                    'type': leg.instrument_type,
                    'strike': leg.strike,
                    'quantity': leg.quantity,
                    'premium': leg.premium
                }
                for leg in self.legs
            ],
            'spread_type': spread_type,
            'net_cashflow': round(net_cashflow, 2),
            'is_debit_spread': is_debit_spread,
            'is_credit_spread': is_credit_spread,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'risk_reward': round(abs(max_profit / max_loss), 2) if max_loss != 0 else None,
            'breakevens': breakevens,
            'total_legs': len(self.legs)
        }

    def _calculate_max_pl(self) -> Tuple[float, float]:
        """Calculate max profit and loss"""
        # Simplified calculation
        # For accurate P&L, need full payoff diagram calculation

        calls = [leg for leg in self.legs if leg.instrument_type == 'CE']
        puts = [leg for leg in self.legs if leg.instrument_type == 'PE']

        if len(calls) == 2 and len(puts) == 0:
            # Vertical call spread
            long_call = next((l for l in calls if l.action == 'BUY'), None)
            short_call = next((l for l in calls if l.action == 'SELL'), None)

            if long_call and short_call and long_call.strike and short_call.strike:
                strike_width = abs(short_call.strike - long_call.strike) * self.lot_size

                net_premium = 0
                if long_call.premium and short_call.premium:
                    net_premium = (short_call.premium - long_call.premium) * self.lot_size

                if long_call.strike < short_call.strike:  # Bull call spread
                    max_profit = strike_width - abs(net_premium)
                    max_loss = abs(net_premium)
                else:  # Bear call spread
                    max_profit = abs(net_premium)
                    max_loss = strike_width - abs(net_premium)

                return max_profit, max_loss

        elif len(puts) == 2 and len(calls) == 0:
            # Vertical put spread
            long_put = next((l for l in puts if l.action == 'BUY'), None)
            short_put = next((l for l in puts if l.action == 'SELL'), None)

            if long_put and short_put and long_put.strike and short_put.strike:
                strike_width = abs(long_put.strike - short_put.strike) * self.lot_size

                net_premium = 0
                if long_put.premium and short_put.premium:
                    net_premium = (short_put.premium - long_put.premium) * self.lot_size

                if long_put.strike > short_put.strike:  # Bear put spread
                    max_profit = strike_width - abs(net_premium)
                    max_loss = abs(net_premium)
                else:  # Bull put spread
                    max_profit = abs(net_premium)
                    max_loss = strike_width - abs(net_premium)

                return max_profit, max_loss

        # Generic calculation for complex spreads
        total_premium = sum(
            (leg.premium or 0) * leg.quantity * self.lot_size *
            (1 if leg.action == 'SELL' else -1)
            for leg in self.legs
        )

        return abs(total_premium), abs(total_premium)

    def _determine_spread_type(self) -> str:
        """Determine the type of spread"""
        if not self.legs:
            return 'unknown'

        # Check expiries
        expiries = set(leg.expiry for leg in self.legs if leg.expiry)

        # Check strikes
        strikes = set(leg.strike for leg in self.legs if leg.strike)

        if len(expiries) == 1 and len(strikes) > 1:
            return 'vertical'
        elif len(strikes) == 1 and len(expiries) > 1:
            return 'horizontal'
        elif len(strikes) > 1 and len(expiries) > 1:
            return 'diagonal'

        # Check for ratio
        quantities = [leg.quantity for leg in self.legs]
        if len(set(quantities)) > 1:
            return 'ratio'

        return 'custom'

    def _calculate_breakevens(self) -> List[float]:
        """Calculate breakeven points"""
        # Simplified - actual calculation requires payoff diagram
        breakevens = []

        # For simple 2-leg spreads
        if len(self.legs) == 2:
            strikes = [leg.strike for leg in self.legs if leg.strike]
            premiums = [leg.premium for leg in self.legs if leg.premium]

            if len(strikes) == 2 and len(premiums) == 2:
                net_premium = premiums[0] - premiums[1]

                # Approximate breakeven
                breakeven = strikes[0] + net_premium
                breakevens.append(round(breakeven, 2))

        return breakevens

    def visualize_payoff(self) -> Dict:
        """
        Generate payoff diagram data

        Returns:
            Dictionary with payoff data for plotting
        """
        if not self.legs:
            return {}

        # Get strike range
        strikes = [leg.strike for leg in self.legs if leg.strike]
        if not strikes:
            return {}

        min_strike = min(strikes)
        max_strike = max(strikes)

        # Expand range by 20%
        range_width = max_strike - min_strike
        price_range = np.linspace(
            min_strike - range_width * 0.2,
            max_strike + range_width * 0.2,
            100
        )

        # Calculate P&L at each price point
        pnl_values = []

        for price in price_range:
            total_pnl = 0

            for leg in self.legs:
                if leg.strike is None or leg.premium is None:
                    continue

                if leg.instrument_type == 'CE':
                    # Call payoff
                    intrinsic = max(0, price - leg.strike)
                elif leg.instrument_type == 'PE':
                    # Put payoff
                    intrinsic = max(0, leg.strike - price)
                else:
                    continue

                # Calculate P&L for this leg
                if leg.action == 'BUY':
                    leg_pnl = (intrinsic - leg.premium) * leg.quantity * self.lot_size
                else:  # SELL
                    leg_pnl = (leg.premium - intrinsic) * leg.quantity * self.lot_size

                total_pnl += leg_pnl

            pnl_values.append(total_pnl)

        return {
            'prices': price_range.tolist(),
            'pnl': pnl_values,
            'max_profit': max(pnl_values),
            'max_loss': min(pnl_values)
        }

    def print_spread_details(self):
        """Print formatted spread details"""
        analysis = self.analyze_spread()

        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            return

        print("\n" + "=" * 70)
        print("SPREAD ANALYSIS")
        print("=" * 70)

        print(f"\nSpread Type: {analysis['spread_type'].upper()}")
        print(f"Total Legs: {analysis['total_legs']}")

        print("\nSpread Legs:")
        for i, leg in enumerate(analysis['legs'], 1):
            print(f"  {i}. {leg['action']} {leg['quantity']}x {leg['type']} @ {leg['strike']}")
            if leg['premium']:
                print(f"     Premium: ₹{leg['premium']:.2f}")

        print(f"\nNet Cashflow: {'Debit' if analysis['is_debit_spread'] else 'Credit'} ₹{abs(analysis['net_cashflow']):,.2f}")

        if isinstance(analysis['max_profit'], (int, float)):
            print(f"Max Profit: ₹{analysis['max_profit']:,.2f}")
        if isinstance(analysis['max_loss'], (int, float)):
            print(f"Max Loss: ₹{analysis['max_loss']:,.2f}")

        if analysis.get('risk_reward'):
            print(f"Risk:Reward = 1:{analysis['risk_reward']:.2f}")

        if analysis.get('breakevens'):
            print(f"\nBreakeven(s): {', '.join([f'₹{be:,.2f}' for be in analysis['breakevens']])}")

        print("\n" + "=" * 70)
