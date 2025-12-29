"""
Portfolio Greeks Management
Aggregate Greeks across multiple option positions
Delta-neutral hedging and risk management
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from .greeks import GreeksCalculator, OptionType

logger = logging.getLogger(__name__)


class PortfolioGreeks:
    """
    Manage Greeks for an entire options portfolio
    Professional options portfolio management
    """

    def __init__(self):
        """Initialize portfolio Greeks manager"""
        self.positions = []
        logger.info("Portfolio Greeks manager initialized")

    def add_position(
        self,
        position_id: str,
        greeks_calc: GreeksCalculator,
        quantity: int,  # Positive for long, negative for short
        lot_size: int = 50
    ) -> Dict:
        """
        Add an option position to the portfolio

        Args:
            position_id: Unique position identifier
            greeks_calc: GreeksCalculator instance for this option
            quantity: Number of lots (positive = long, negative = short)
            lot_size: Contract lot size

        Returns:
            Position dictionary
        """
        greeks = greeks_calc.all_greeks()

        # Calculate position Greeks (multiplied by quantity and lot size)
        total_quantity = quantity * lot_size

        position = {
            'position_id': position_id,
            'quantity': quantity,
            'lot_size': lot_size,
            'total_quantity': total_quantity,

            # Option details
            'option_type': greeks_calc.option_type.value,
            'spot': greeks_calc.S,
            'strike': greeks_calc.K,
            'volatility': greeks_calc.sigma,
            'time_to_expiry': greeks_calc.T,

            # Individual Greeks
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'theta': greeks['theta'],
            'vega': greeks['vega'],
            'rho': greeks['rho'],
            'price': greeks['price'],

            # Position Greeks (scaled by quantity)
            'position_delta': greeks['delta'] * total_quantity,
            'position_gamma': greeks['gamma'] * total_quantity,
            'position_theta': greeks['theta'] * total_quantity,
            'position_vega': greeks['vega'] * total_quantity,
            'position_rho': greeks['rho'] * total_quantity,
            'position_value': greeks['price'] * total_quantity
        }

        self.positions.append(position)

        logger.info(
            f"Added position {position_id}: {quantity} lots of {greeks_calc.option_type.value} "
            f"{greeks_calc.K} strike, Delta={position['position_delta']:.2f}"
        )

        return position

    def remove_position(self, position_id: str):
        """Remove a position from portfolio"""
        self.positions = [p for p in self.positions if p['position_id'] != position_id]
        logger.info(f"Removed position {position_id}")

    def get_portfolio_greeks(self) -> Dict:
        """
        Calculate aggregate portfolio Greeks

        Returns:
            Dictionary with total Greeks
        """
        if not self.positions:
            return {
                'total_delta': 0,
                'total_gamma': 0,
                'total_theta': 0,
                'total_vega': 0,
                'total_rho': 0,
                'total_value': 0,
                'num_positions': 0
            }

        df = pd.DataFrame(self.positions)

        portfolio_greeks = {
            'total_delta': df['position_delta'].sum(),
            'total_gamma': df['position_gamma'].sum(),
            'total_theta': df['position_theta'].sum(),
            'total_vega': df['position_vega'].sum(),
            'total_rho': df['position_rho'].sum(),
            'total_value': df['position_value'].sum(),
            'num_positions': len(self.positions),

            # Additional metrics
            'largest_delta_position': df.loc[df['position_delta'].abs().idxmax()] if len(df) > 0 else None,
            'largest_gamma_position': df.loc[df['position_gamma'].abs().idxmax()] if len(df) > 0 else None,
            'net_long_delta': df[df['position_delta'] > 0]['position_delta'].sum(),
            'net_short_delta': df[df['position_delta'] < 0]['position_delta'].sum(),
        }

        return portfolio_greeks

    def is_delta_neutral(self, tolerance: float = 10.0) -> Tuple[bool, float]:
        """
        Check if portfolio is delta-neutral

        Args:
            tolerance: Tolerance for delta neutrality (absolute delta)

        Returns:
            Tuple of (is_neutral, total_delta)
        """
        greeks = self.get_portfolio_greeks()
        total_delta = greeks['total_delta']

        is_neutral = abs(total_delta) <= tolerance

        return is_neutral, total_delta

    def calculate_hedge(self, futures_lot_size: int = 50) -> Dict:
        """
        Calculate futures hedge needed for delta-neutral portfolio

        Args:
            futures_lot_size: Futures contract lot size

        Returns:
            Dictionary with hedging recommendation
        """
        greeks = self.get_portfolio_greeks()
        total_delta = greeks['total_delta']

        # Calculate futures needed
        # If delta is positive (net long), need to short futures
        # If delta is negative (net short), need to long futures

        futures_contracts = -total_delta / futures_lot_size

        hedge = {
            'current_delta': total_delta,
            'futures_needed': futures_contracts,
            'futures_lots': int(np.round(futures_contracts)),
            'direction': 'SHORT' if futures_contracts < 0 else 'LONG',
            'residual_delta': total_delta + (int(np.round(futures_contracts)) * futures_lot_size),
            'is_hedged': abs(total_delta + (int(np.round(futures_contracts)) * futures_lot_size)) < 10
        }

        # Recommendation
        if abs(hedge['futures_lots']) == 0:
            hedge['recommendation'] = "✅ Portfolio is delta-neutral, no hedge needed"
        elif abs(hedge['residual_delta']) < 10:
            hedge['recommendation'] = f"🔒 {hedge['direction']} {abs(hedge['futures_lots'])} futures lots for delta neutrality"
        else:
            hedge['recommendation'] = f"⚠️ {hedge['direction']} {abs(hedge['futures_lots'])} futures lots (residual delta: {hedge['residual_delta']:.1f})"

        return hedge

    def gamma_scalping_opportunity(self, spot_move: float) -> Dict:
        """
        Calculate gamma scalping opportunity from a spot price move

        Args:
            spot_move: Expected move in spot price

        Returns:
            Dictionary with scalping details
        """
        greeks = self.get_portfolio_greeks()

        # Gamma scalping profit = 0.5 × Gamma × (Spot Move)²
        gamma_pnl = 0.5 * greeks['total_gamma'] * (spot_move ** 2)

        # Delta change from spot move
        delta_change = greeks['total_gamma'] * spot_move

        scalping = {
            'current_gamma': greeks['total_gamma'],
            'current_delta': greeks['total_delta'],
            'spot_move': spot_move,
            'new_delta': greeks['total_delta'] + delta_change,
            'delta_change': delta_change,
            'gamma_pnl': gamma_pnl,
            'recommendation': self._gamma_scalp_recommendation(gamma_pnl, delta_change)
        }

        return scalping

    def _gamma_scalp_recommendation(self, gamma_pnl: float, delta_change: float) -> str:
        """Generate gamma scalping recommendation"""
        if abs(gamma_pnl) < 100:
            return "💤 Gamma P&L too small for scalping"
        elif abs(delta_change) > 50:
            return f"🎯 Significant gamma scalping opportunity: ₹{abs(gamma_pnl):.2f} P&L, rehedge delta"
        else:
            return f"✅ Moderate opportunity: ₹{abs(gamma_pnl):.2f} P&L"

    def theta_decay_daily(self) -> Dict:
        """
        Calculate expected daily theta decay

        Returns:
            Dictionary with theta analysis
        """
        greeks = self.get_portfolio_greeks()

        theta_analysis = {
            'total_theta_per_day': greeks['total_theta'],
            'theta_per_week': greeks['total_theta'] * 7,
            'theta_per_month': greeks['total_theta'] * 30,
            'direction': 'POSITIVE' if greeks['total_theta'] > 0 else 'NEGATIVE',
            'recommendation': self._theta_recommendation(greeks['total_theta'])
        }

        return theta_analysis

    def _theta_recommendation(self, total_theta: float) -> str:
        """Generate theta recommendation"""
        if total_theta < -500:
            return f"⚠️  Heavy time decay: losing ₹{abs(total_theta):.2f}/day - consider closing or rolling"
        elif total_theta < 0:
            return f"⏰ Losing ₹{abs(total_theta):.2f}/day to theta - monitor closely"
        elif total_theta > 500:
            return f"💰 Earning ₹{total_theta:.2f}/day from theta decay - positive carry"
        elif total_theta > 0:
            return f"✅ Earning ₹{total_theta:.2f}/day from theta"
        else:
            return "➖ Theta-neutral portfolio"

    def vega_exposure(self) -> Dict:
        """
        Analyze portfolio's volatility exposure

        Returns:
            Dictionary with vega analysis
        """
        greeks = self.get_portfolio_greeks()

        vega_analysis = {
            'total_vega': greeks['total_vega'],
            'vega_exposure_1pct': greeks['total_vega'],  # For 1% IV change
            'vega_exposure_5pct': greeks['total_vega'] * 5,  # For 5% IV change
            'direction': 'LONG_VOL' if greeks['total_vega'] > 0 else 'SHORT_VOL',
            'recommendation': self._vega_recommendation(greeks['total_vega'])
        }

        return vega_analysis

    def _vega_recommendation(self, total_vega: float) -> str:
        """Generate vega recommendation"""
        if total_vega > 1000:
            return f"⚠️  High vega exposure: +₹{total_vega:.2f} per 1% IV - volatility spike will help"
        elif total_vega > 0:
            return f"📈 Long vega: benefit from vol increase (+₹{total_vega:.2f} per 1%)"
        elif total_vega < -1000:
            return f"⚠️  Heavy short vega: -₹{abs(total_vega):.2f} per 1% IV - vol spike will hurt"
        elif total_vega < 0:
            return f"📉 Short vega: benefit from vol decrease (₹{abs(total_vega):.2f} per 1%)"
        else:
            return "➖ Vega-neutral portfolio"

    def stress_test_spot_move(self, spot_moves: List[float]) -> pd.DataFrame:
        """
        Stress test portfolio across different spot price movements

        Args:
            spot_moves: List of spot price changes to test (e.g., [-100, -50, 0, 50, 100])

        Returns:
            DataFrame with P&L for each scenario
        """
        greeks = self.get_portfolio_greeks()
        current_delta = greeks['total_delta']
        current_gamma = greeks['total_gamma']

        scenarios = []

        for move in spot_moves:
            # Linear P&L from delta
            delta_pnl = current_delta * move

            # Gamma P&L (convexity)
            gamma_pnl = 0.5 * current_gamma * (move ** 2)

            # Total P&L (approximate)
            total_pnl = delta_pnl + gamma_pnl

            scenarios.append({
                'spot_move': move,
                'delta_pnl': delta_pnl,
                'gamma_pnl': gamma_pnl,
                'total_pnl': total_pnl,
                'pnl_percent': (total_pnl / greeks['total_value']) * 100 if greeks['total_value'] != 0 else 0
            })

        return pd.DataFrame(scenarios)

    def generate_portfolio_report(self) -> str:
        """
        Generate comprehensive portfolio Greeks report

        Returns:
            Formatted report string
        """
        if not self.positions:
            return "No positions in portfolio"

        greeks = self.get_portfolio_greeks()
        hedge = self.calculate_hedge()
        theta_info = self.theta_decay_daily()
        vega_info = self.vega_exposure()

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║              OPTIONS PORTFOLIO GREEKS REPORT                  ║
╠══════════════════════════════════════════════════════════════╣

📊 PORTFOLIO OVERVIEW
   Positions:           {greeks['num_positions']:>15}
   Total Value:         ₹{greeks['total_value']:>15,.2f}

📈 AGGREGATE GREEKS
   Total Delta:         {greeks['total_delta']:>15.2f}  {'✅ Delta-neutral' if abs(greeks['total_delta']) < 10 else '⚠️ Directional exposure'}
   Total Gamma:         {greeks['total_gamma']:>15.4f}
   Total Theta:         ₹{greeks['total_theta']:>15.2f} /day
   Total Vega:          ₹{greeks['total_vega']:>15.2f} /1% IV
   Total Rho:           ₹{greeks['total_rho']:>15.2f}

🔒 DELTA HEDGING
   Current Delta:       {hedge['current_delta']:>15.2f}
   Hedge Needed:        {hedge['direction']:>15} {abs(hedge['futures_lots'])} futures lots
   Residual Delta:      {hedge['residual_delta']:>15.2f}
   Status:              {hedge['recommendation']}

⏰ THETA DECAY
   Daily Theta:         ₹{theta_info['total_theta_per_day']:>15,.2f}
   Weekly Theta:        ₹{theta_info['theta_per_week']:>15,.2f}
   Monthly Theta:       ₹{theta_info['theta_per_month']:>15,.2f}
   Direction:           {theta_info['direction']:>15}
   Analysis:            {theta_info['recommendation']}

📊 VOLATILITY EXPOSURE
   Total Vega:          ₹{vega_info['total_vega']:>15,.2f}
   1% IV Move Impact:   ₹{vega_info['vega_exposure_1pct']:>15,.2f}
   5% IV Move Impact:   ₹{vega_info['vega_exposure_5pct']:>15,.2f}
   Direction:           {vega_info['direction']:>15}
   Analysis:            {vega_info['recommendation']}

╚══════════════════════════════════════════════════════════════╝

💡 RISK MANAGEMENT ACTIONS:
{self._generate_action_items(greeks, hedge, theta_info, vega_info)}
"""
        return report

    def _generate_action_items(
        self,
        greeks: Dict,
        hedge: Dict,
        theta_info: Dict,
        vega_info: Dict
    ) -> str:
        """Generate action items based on portfolio state"""
        actions = []

        # Delta management
        if abs(greeks['total_delta']) > 50:
            actions.append(f"   • URGENT: Hedge delta exposure ({hedge['recommendation']})")
        elif abs(greeks['total_delta']) > 20:
            actions.append(f"   • Consider hedging delta (current: {greeks['total_delta']:.1f})")

        # Gamma management
        if abs(greeks['total_gamma']) > 0.05:
            actions.append("   • Monitor gamma - delta can change rapidly")

        # Theta management
        if theta_info['total_theta_per_day'] < -500:
            actions.append(f"   • Heavy theta decay - losing ₹{abs(theta_info['total_theta_per_day']):.0f}/day")

        # Vega management
        if abs(vega_info['total_vega']) > 1000:
            actions.append(f"   • High vega exposure - monitor IV carefully")

        if not actions:
            actions.append("   ✅ Portfolio well-managed - no immediate actions needed")

        return '\n'.join(actions)

    def get_positions_dataframe(self) -> pd.DataFrame:
        """Get all positions as a DataFrame"""
        return pd.DataFrame(self.positions)
