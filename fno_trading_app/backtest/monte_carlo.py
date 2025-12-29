"""
Monte Carlo Simulation for Backtest Analysis
Randomize trade sequence to assess strategy robustness
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Monte Carlo simulation for trading strategies
    Randomizes trade sequence to understand distribution of possible outcomes
    """

    def __init__(self, num_simulations: int = 10000, random_seed: Optional[int] = None):
        """
        Initialize Monte Carlo simulator

        Args:
            num_simulations: Number of simulations to run
            random_seed: Random seed for reproducibility
        """
        self.num_simulations = num_simulations
        self.random_seed = random_seed

        if random_seed:
            np.random.seed(random_seed)

        logger.info(f"Monte Carlo Simulator initialized: {num_simulations} simulations")

    def run_simulation(
        self,
        trades: List[Dict],
        initial_capital: float
    ) -> Dict:
        """
        Run Monte Carlo simulation by randomizing trade sequence

        Args:
            trades: List of completed trades
            initial_capital: Starting capital

        Returns:
            Dictionary with simulation results
        """
        if len(trades) < 10:
            logger.warning("Less than 10 trades - Monte Carlo results may not be reliable")

        logger.info(f"Running {self.num_simulations} Monte Carlo simulations...")

        # Extract P&L from each trade
        pnl_sequence = [t['net_pnl'] for t in trades]

        # Run simulations
        results = []
        for i in range(self.num_simulations):
            # Randomly shuffle the trade sequence
            randomized_pnl = np.random.choice(pnl_sequence, size=len(pnl_sequence), replace=True)

            # Calculate equity curve
            equity = np.cumsum(randomized_pnl) + initial_capital

            # Calculate metrics for this simulation
            final_capital = equity[-1]
            max_equity = np.maximum.accumulate(equity)
            drawdowns = (equity - max_equity) / max_equity
            max_drawdown = abs(drawdowns.min()) * 100

            total_return = ((final_capital - initial_capital) / initial_capital) * 100

            results.append({
                'final_capital': final_capital,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'equity_curve': equity
            })

        # Analyze results
        analysis = self._analyze_results(results, initial_capital)

        logger.info("Monte Carlo simulation completed")
        return analysis

    def _analyze_results(
        self,
        results: List[Dict],
        initial_capital: float
    ) -> Dict:
        """
        Analyze Monte Carlo simulation results

        Args:
            results: List of simulation results
            initial_capital: Starting capital

        Returns:
            Statistical analysis of results
        """
        final_capitals = [r['final_capital'] for r in results]
        total_returns = [r['total_return'] for r in results]
        max_drawdowns = [r['max_drawdown'] for r in results]

        analysis = {
            # Final capital statistics
            'final_capital': {
                'mean': np.mean(final_capitals),
                'median': np.median(final_capitals),
                'std': np.std(final_capitals),
                'min': np.min(final_capitals),
                'max': np.max(final_capitals),
                'percentile_5': np.percentile(final_capitals, 5),
                'percentile_25': np.percentile(final_capitals, 25),
                'percentile_75': np.percentile(final_capitals, 75),
                'percentile_95': np.percentile(final_capitals, 95)
            },

            # Return statistics
            'returns': {
                'mean': np.mean(total_returns),
                'median': np.median(total_returns),
                'std': np.std(total_returns),
                'min': np.min(total_returns),
                'max': np.max(total_returns),
                'percentile_5': np.percentile(total_returns, 5),
                'percentile_25': np.percentile(total_returns, 25),
                'percentile_75': np.percentile(total_returns, 75),
                'percentile_95': np.percentile(total_returns, 95)
            },

            # Drawdown statistics
            'max_drawdown': {
                'mean': np.mean(max_drawdowns),
                'median': np.median(max_drawdowns),
                'std': np.std(max_drawdowns),
                'min': np.min(max_drawdowns),
                'max': np.max(max_drawdowns),
                'percentile_5': np.percentile(max_drawdowns, 5),
                'percentile_25': np.percentile(max_drawdowns, 25),
                'percentile_75': np.percentile(max_drawdowns, 75),
                'percentile_95': np.percentile(max_drawdowns, 95)
            },

            # Risk metrics
            'probability_of_profit': (sum(1 for r in total_returns if r > 0) / len(total_returns)) * 100,
            'probability_of_loss': (sum(1 for r in total_returns if r < 0) / len(total_returns)) * 100,
            'probability_of_ruin': (sum(1 for fc in final_capitals if fc < initial_capital * 0.5) /
                                     len(final_capitals)) * 100,

            # Extreme scenarios
            'worst_case_scenario': min(total_returns),
            'best_case_scenario': max(total_returns),
            'expected_return': np.mean(total_returns),

            # Confidence intervals
            'confidence_interval_95': (
                np.percentile(total_returns, 2.5),
                np.percentile(total_returns, 97.5)
            ),

            # All simulations (for plotting)
            'all_simulations': results
        }

        return analysis

    def calculate_risk_of_ruin(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        num_trades: int,
        capital: float,
        simulations: int = 10000
    ) -> Dict:
        """
        Calculate probability of losing a significant portion of capital

        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive)
            num_trades: Number of trades to simulate
            capital: Starting capital
            simulations: Number of Monte Carlo runs

        Returns:
            Risk of ruin statistics
        """
        ruin_threshold = capital * 0.3  # Consider "ruin" if lose 70% of capital

        ruins = 0
        severe_drawdowns = 0  # > 30% drawdown

        for _ in range(simulations):
            current_capital = capital
            max_capital = capital

            for _ in range(num_trades):
                # Simulate trade outcome
                if np.random.random() < win_rate:
                    current_capital += avg_win
                else:
                    current_capital -= avg_loss

                max_capital = max(max_capital, current_capital)

                # Check for ruin
                if current_capital <= ruin_threshold:
                    ruins += 1
                    break

            # Check for severe drawdown
            drawdown = (max_capital - current_capital) / max_capital
            if drawdown > 0.30:
                severe_drawdowns += 1

        risk_of_ruin = (ruins / simulations) * 100
        risk_of_severe_dd = (severe_drawdowns / simulations) * 100

        return {
            'risk_of_ruin_percent': risk_of_ruin,
            'risk_of_severe_drawdown_percent': risk_of_severe_dd,
            'ruin_threshold': ruin_threshold,
            'simulations': simulations,
            'recommendation': self._get_risk_recommendation(risk_of_ruin, risk_of_severe_dd)
        }

    def _get_risk_recommendation(self, risk_of_ruin: float, risk_of_severe_dd: float) -> str:
        """Get recommendation based on risk metrics"""
        if risk_of_ruin > 10:
            return "🛑 VERY HIGH RISK - Do NOT trade this strategy"
        elif risk_of_ruin > 5:
            return "⚠️  HIGH RISK - Reduce position sizes significantly"
        elif risk_of_ruin > 2:
            return "⚠️  MODERATE RISK - Reduce position sizes or improve strategy"
        elif risk_of_severe_dd > 20:
            return "⚠️  High drawdown risk - consider tighter stop losses"
        else:
            return "✅ Acceptable risk level"

    def stress_test(
        self,
        trades: List[Dict],
        initial_capital: float,
        scenarios: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Stress test strategy under adverse market conditions

        Args:
            trades: List of completed trades
            initial_capital: Starting capital
            scenarios: List of stress scenarios (uses defaults if None)

        Returns:
            Stress test results
        """
        if scenarios is None:
            scenarios = self._get_default_stress_scenarios()

        results = {}

        for scenario in scenarios:
            name = scenario['name']
            multiplier = scenario['loss_multiplier']
            probability = scenario['loss_probability']

            logger.info(f"Running stress test: {name}")

            # Modify trade outcomes based on scenario
            stressed_pnl = []
            for trade in trades:
                pnl = trade['net_pnl']

                # Apply stress conditions
                if pnl < 0:
                    # Losses are worse in stress scenario
                    stressed_pnl.append(pnl * multiplier)
                else:
                    # Random chance of turning win into loss
                    if np.random.random() < probability:
                        stressed_pnl.append(-abs(pnl) * 0.5)  # Half the win becomes a loss
                    else:
                        stressed_pnl.append(pnl)

            # Calculate stressed equity curve
            stressed_equity = np.cumsum(stressed_pnl) + initial_capital
            final_capital = stressed_equity[-1]

            # Calculate max drawdown
            max_equity = np.maximum.accumulate(stressed_equity)
            drawdowns = (stressed_equity - max_equity) / max_equity
            max_dd = abs(drawdowns.min()) * 100

            # Total return
            total_return = ((final_capital - initial_capital) / initial_capital) * 100

            results[name] = {
                'final_capital': final_capital,
                'total_return': total_return,
                'max_drawdown': max_dd,
                'survived': final_capital > initial_capital * 0.5,
                'recommendation': self._get_stress_recommendation(final_capital, initial_capital, max_dd)
            }

        return results

    def _get_default_stress_scenarios(self) -> List[Dict]:
        """Get default stress test scenarios"""
        return [
            {
                'name': '2020_march_crash',
                'description': 'March 2020 COVID crash',
                'loss_multiplier': 2.5,  # Losses 2.5x worse
                'loss_probability': 0.30  # 30% of wins turn to losses
            },
            {
                'name': 'flash_crash',
                'description': 'Flash crash scenario',
                'loss_multiplier': 3.0,
                'loss_probability': 0.40
            },
            {
                'name': 'sustained_bear',
                'description': 'Sustained bear market',
                'loss_multiplier': 1.5,
                'loss_probability': 0.20
            },
            {
                'name': 'high_volatility',
                'description': 'High volatility period (VIX > 35)',
                'loss_multiplier': 2.0,
                'loss_probability': 0.25
            }
        ]

    def _get_stress_recommendation(
        self,
        final_capital: float,
        initial_capital: float,
        max_dd: float
    ) -> str:
        """Get recommendation from stress test"""
        survival_rate = (final_capital / initial_capital)

        if survival_rate < 0.50:
            return "🛑 FAILS stress test - strategy not robust"
        elif survival_rate < 0.75:
            return "⚠️  Marginal - would suffer significant losses in crisis"
        elif survival_rate < 0.90:
            return "⚠️  Acceptable but not ideal for crisis periods"
        elif max_dd > 40:
            return "⚠️  High drawdown - difficult to psychologically endure"
        else:
            return "✅ Passes stress test - robust strategy"

    def generate_monte_carlo_report(self, analysis: Dict) -> str:
        """
        Generate Monte Carlo analysis report

        Args:
            analysis: Monte Carlo analysis dictionary

        Returns:
            Formatted report
        """
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║              MONTE CARLO SIMULATION ANALYSIS                  ║
╠══════════════════════════════════════════════════════════════╣

📊 RETURN DISTRIBUTION
   Expected Return:     {analysis['returns']['mean']:>15.2f}%
   Median Return:       {analysis['returns']['median']:>15.2f}%
   Std Deviation:       {analysis['returns']['std']:>15.2f}%

   Best Case (95%):     {analysis['returns']['percentile_95']:>15.2f}%
   Worst Case (5%):     {analysis['returns']['percentile_5']:>15.2f}%

   95% Confidence:      {analysis['confidence_interval_95'][0]:.2f}% to {analysis['confidence_interval_95'][1]:.2f}%

📈 FINAL CAPITAL DISTRIBUTION
   Expected:            ₹{analysis['final_capital']['mean']:>15,.2f}
   Median:              ₹{analysis['final_capital']['median']:>15,.2f}

   Best Case (95%):     ₹{analysis['final_capital']['percentile_95']:>15,.2f}
   Worst Case (5%):     ₹{analysis['final_capital']['percentile_5']:>15,.2f}

📉 MAXIMUM DRAWDOWN DISTRIBUTION
   Expected:            {analysis['max_drawdown']['mean']:>15.2f}%
   Median:              {analysis['max_drawdown']['median']:>15.2f}%

   Best Case (5%):      {analysis['max_drawdown']['percentile_5']:>15.2f}%
   Worst Case (95%):    {analysis['max_drawdown']['percentile_95']:>15.2f}%

⚠️  RISK METRICS
   Probability of Profit:           {analysis['probability_of_profit']:>10.1f}%
   Probability of Loss:             {analysis['probability_of_loss']:>10.1f}%
   Probability of Ruin (>50% loss): {analysis['probability_of_ruin']:>10.1f}%

💡 INTERPRETATION:
   {self._interpret_monte_carlo(analysis)}

╚══════════════════════════════════════════════════════════════╝
"""
        return report

    def _interpret_monte_carlo(self, analysis: Dict) -> str:
        """Interpret Monte Carlo results"""
        interpretations = []

        # Check expected return
        if analysis['returns']['mean'] > 20:
            interpretations.append("✅ High expected return - profitable strategy")
        elif analysis['returns']['mean'] > 10:
            interpretations.append("✅ Decent expected return")
        elif analysis['returns']['mean'] > 0:
            interpretations.append("⚠️  Low expected return - consider improvements")
        else:
            interpretations.append("❌ Negative expected return - do NOT trade")

        # Check consistency (std dev)
        if analysis['returns']['std'] < 10:
            interpretations.append("✅ Low variance - consistent returns")
        elif analysis['returns']['std'] > 30:
            interpretations.append("⚠️  High variance - inconsistent results")

        # Check downside risk
        if analysis['returns']['percentile_5'] < -15:
            interpretations.append("⚠️  Significant downside risk (5th percentile < -15%)")
        elif analysis['returns']['percentile_5'] > -10:
            interpretations.append("✅ Limited downside risk")

        # Check probability of ruin
        if analysis['probability_of_ruin'] > 5:
            interpretations.append("🛑 HIGH risk of ruin - reduce position sizes")
        elif analysis['probability_of_ruin'] > 2:
            interpretations.append("⚠️  Moderate risk of ruin - be cautious")
        else:
            interpretations.append("✅ Low risk of ruin")

        return '\n   '.join(interpretations)
