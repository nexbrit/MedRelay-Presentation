"""
F&O Trading Application - Main Entry Point
Live trading signal generator with Upstox API integration
"""

import sys
import time
from pathlib import Path
from typing import Dict, List
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api import UpstoxClient
from signals import SignalGenerator, SignalType
from screeners import FNOScreener
from utils import ConfigLoader, setup_logger


class FNOTradingApp:
    """Main F&O Trading Application"""

    def __init__(self, config_path: str = None):
        """
        Initialize trading application

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.config

        # Setup logging
        log_config = self.config.get('logging', {})
        self.logger = setup_logger(
            level=log_config.get('level', 'INFO'),
            log_file=log_config.get('file'),
            console=log_config.get('console', True)
        )

        self.logger.info("=" * 60)
        self.logger.info("F&O Trading Application Starting")
        self.logger.info("=" * 60)

        # Initialize components
        self.upstox_client = None
        self.signal_generator = None
        self.screener = None

        self._initialize_components()

    def _initialize_components(self):
        """Initialize application components"""
        try:
            # Initialize Upstox client
            upstox_config = self.config.get('upstox', {})
            self.upstox_client = UpstoxClient(
                sandbox=upstox_config.get('sandbox_mode', True)
            )
            self.logger.info("Upstox client initialized")

            # Initialize signal generator
            signal_config = self.config.get('trading', {}).get('signals', {})
            combined_signal_config = {
                'rsi_period': signal_config.get('rsi', {}).get('period', 14),
                'rsi_overbought': signal_config.get('rsi', {}).get('overbought', 70),
                'rsi_oversold': signal_config.get('rsi', {}).get('oversold', 30),
                'macd_fast': signal_config.get('macd', {}).get('fast_period', 12),
                'macd_slow': signal_config.get('macd', {}).get('slow_period', 26),
                'macd_signal': signal_config.get('macd', {}).get('signal_period', 9),
                'ema_short': signal_config.get('ema', {}).get('short_period', 9),
                'ema_medium': signal_config.get('ema', {}).get('medium_period', 21),
                'ema_long': signal_config.get('ema', {}).get('long_period', 50),
                'bb_period': signal_config.get('bollinger', {}).get('period', 20),
                'bb_std': signal_config.get('bollinger', {}).get('std_dev', 2.0),
            }
            self.signal_generator = SignalGenerator(combined_signal_config)
            self.logger.info("Signal generator initialized")

            # Initialize screener
            screener_config = self.config.get('screener', {})
            self.screener = FNOScreener(screener_config)
            self.logger.info("Screener initialized")

        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise

    def setup_authentication(self, access_token: str = None):
        """
        Setup Upstox authentication

        Args:
            access_token: OAuth access token (if available)
        """
        if access_token:
            self.upstox_client.set_access_token(access_token)
            self.logger.info("Access token configured")
        else:
            auth_url = self.upstox_client.get_authorization_url()
            self.logger.info(f"\nPlease authorize the application:")
            self.logger.info(f"Authorization URL: {auth_url}")
            self.logger.info("\nAfter authorization, use set_access_token() method")

    def analyze_instrument(self, instrument_key: str, interval: str = '1day', days_back: int = 90) -> Dict:
        """
        Analyze an instrument and generate signals

        Args:
            instrument_key: Instrument key (e.g., 'NSE_INDEX|Nifty 50')
            interval: Candle interval
            days_back: Historical days to analyze

        Returns:
            Dictionary with analysis results
        """
        try:
            self.logger.info(f"\n{'=' * 60}")
            self.logger.info(f"Analyzing: {instrument_key}")
            self.logger.info(f"{'=' * 60}")

            # Get historical data
            df = self.upstox_client.get_historical_data(
                instrument_key=instrument_key,
                interval=interval,
                days_back=days_back
            )

            if df.empty:
                self.logger.warning(f"No data available for {instrument_key}")
                return {}

            # Generate signals
            df_with_signals = self.signal_generator.generate_combined_signal(df)

            # Get latest signal
            latest_signal = self.signal_generator.get_latest_signal(df_with_signals)

            # Print analysis results
            self._print_analysis_results(instrument_key, latest_signal)

            return {
                'instrument': instrument_key,
                'data': df_with_signals,
                'latest_signal': latest_signal,
                'timestamp': datetime.now()
            }

        except Exception as e:
            self.logger.error(f"Error analyzing {instrument_key}: {e}")
            return {}

    def _print_analysis_results(self, instrument: str, signal: Dict):
        """Print formatted analysis results"""
        self.logger.info(f"\nInstrument: {instrument}")
        self.logger.info(f"Timestamp: {signal.get('timestamp', 'N/A')}")
        self.logger.info(f"Current Price: {signal.get('close', 0):.2f}")
        self.logger.info(f"\nSIGNAL: {signal.get('signal', 'HOLD')}")
        self.logger.info(f"Strength: {signal.get('strength', 0)} (Buy: {signal.get('buy_score', 0)}, Sell: {signal.get('sell_score', 0)})")

        indicators = signal.get('indicators', {})
        self.logger.info("\nIndicator Details:")
        self.logger.info(f"  RSI: {indicators.get('rsi', 0):.2f} - {indicators.get('rsi_signal', 'HOLD')}")
        self.logger.info(f"  MACD: {indicators.get('macd', 0):.4f} - {indicators.get('macd_crossover', 'HOLD')}")
        self.logger.info(f"  EMA Crossover: {indicators.get('ema_signal', 'HOLD')}")
        self.logger.info(f"  Bollinger Bands: {indicators.get('bb_signal', 'HOLD')}")
        self.logger.info(f"  Supertrend: {indicators.get('supertrend_signal', 'HOLD')}")

    def run_screener(self, market_data: pd.DataFrame, filters: List[str] = None) -> pd.DataFrame:
        """
        Run screener on market data

        Args:
            market_data: DataFrame with market data
            filters: List of filters to apply

        Returns:
            Screened DataFrame
        """
        try:
            self.logger.info("\n" + "=" * 60)
            self.logger.info("Running Screener")
            self.logger.info("=" * 60)

            screened_df = self.screener.multi_criteria_screen(market_data, filters)

            self.logger.info(f"\nScreening Results:")
            self.logger.info(f"Total instruments scanned: {len(market_data)}")
            self.logger.info(f"Instruments passed screening: {len(screened_df)}")

            if not screened_df.empty:
                self.logger.info("\nTop Opportunities:")
                top_opportunities = self.screener.get_top_opportunities(screened_df, top_n=5)
                self.logger.info(f"\n{top_opportunities.to_string()}")

            return screened_df

        except Exception as e:
            self.logger.error(f"Error running screener: {e}")
            return pd.DataFrame()

    def live_monitoring(self, instruments: List[str], interval_seconds: int = 60):
        """
        Monitor instruments in real-time and generate live signals

        Args:
            instruments: List of instrument keys to monitor
            interval_seconds: Update interval in seconds
        """
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Starting Live Monitoring")
        self.logger.info("=" * 60)
        self.logger.info(f"Monitoring {len(instruments)} instruments")
        self.logger.info(f"Update interval: {interval_seconds} seconds")
        self.logger.info("Press Ctrl+C to stop\n")

        try:
            while True:
                for instrument in instruments:
                    try:
                        # Analyze instrument
                        analysis = self.analyze_instrument(instrument, interval='30minute', days_back=30)

                        # Check for actionable signals
                        if analysis:
                            signal = analysis['latest_signal']['signal']
                            if signal in [SignalType.STRONG_BUY.value, SignalType.STRONG_SELL.value]:
                                self.logger.warning(f"\n🚨 ALERT: {instrument} - {signal}")

                    except Exception as e:
                        self.logger.error(f"Error monitoring {instrument}: {e}")

                # Wait for next update
                self.logger.info(f"\nWaiting {interval_seconds} seconds for next update...")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            self.logger.info("\n\nStopping live monitoring...")
        except Exception as e:
            self.logger.error(f"Error in live monitoring: {e}")

    def get_option_chain_analysis(self, underlying: str, expiry_date: str = None) -> pd.DataFrame:
        """
        Get and analyze option chain

        Args:
            underlying: Underlying instrument key
            expiry_date: Expiry date (optional)

        Returns:
            Analyzed option chain DataFrame
        """
        try:
            # Get spot price
            spot_data = self.upstox_client.get_market_quote([underlying])
            spot_price = spot_data['last_price'].iloc[0] if not spot_data.empty else 0

            # Get option chain
            option_chain = self.upstox_client.get_option_chain(underlying, expiry_date)

            if option_chain.empty:
                self.logger.warning("No option chain data available")
                return pd.DataFrame()

            # Screen for strategies
            screened_options = self.screener.screen_option_strategies(option_chain, spot_price)

            self.logger.info(f"\nOption Chain Analysis for {underlying}")
            self.logger.info(f"Spot Price: {spot_price}")
            self.logger.info(f"\nInteresting Strikes:\n{screened_options.to_string()}")

            return screened_options

        except Exception as e:
            self.logger.error(f"Error in option chain analysis: {e}")
            return pd.DataFrame()


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("F&O Trading Application")
    print("=" * 60)

    # Initialize app
    app = FNOTradingApp()

    # Demo mode - show features without live connection
    print("\n📊 Application Features:")
    print("1. Live Trading Signal Generator (RSI, MACD, EMA, Bollinger, Supertrend)")
    print("2. Upstox API Integration (Market data, Orders, Portfolio)")
    print("3. Data-Driven Screeners (Volume, Price, Momentum, Breakouts)")
    print("4. Option Chain Analysis (PCR, High OI strikes)")
    print("5. Real-time Monitoring")

    print("\n🔧 Setup Instructions:")
    print("1. Get Upstox API credentials from: https://upstox.com/developer/")
    print("2. Copy .env.example to .env and add your credentials")
    print("3. Run: pip install -r requirements.txt")
    print("4. Authorize the app: app.setup_authentication()")
    print("5. Start monitoring: app.live_monitoring(['NSE_INDEX|Nifty 50'])")

    print("\n📖 Quick Start Example:")
    print("""
    from main import FNOTradingApp

    # Initialize app
    app = FNOTradingApp()

    # Setup authentication (one-time)
    app.setup_authentication()  # Follow the URL to authorize

    # After getting access token
    app.setup_authentication(access_token='your_token_here')

    # Analyze an instrument
    analysis = app.analyze_instrument('NSE_INDEX|Nifty 50')

    # Start live monitoring
    instruments = ['NSE_INDEX|Nifty 50', 'NSE_INDEX|Nifty Bank']
    app.live_monitoring(instruments, interval_seconds=300)
    """)

    print("\n" + "=" * 60)
    print("Application initialized successfully!")
    print("Import and use the FNOTradingApp class to get started.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
