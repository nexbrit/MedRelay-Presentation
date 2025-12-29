"""
Basic Usage Examples for F&O Trading App
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import FNOTradingApp
from signals import SignalGenerator
from screeners import FNOScreener
import pandas as pd
import numpy as np


def example_1_initialization():
    """Example 1: Initialize the application"""
    print("\n" + "=" * 60)
    print("Example 1: Application Initialization")
    print("=" * 60)

    # Initialize app with default config
    app = FNOTradingApp()
    print("✓ Application initialized successfully")

    # Or initialize with custom config
    # app = FNOTradingApp(config_path='path/to/custom/config.yaml')


def example_2_signal_generation():
    """Example 2: Generate signals from sample data"""
    print("\n" + "=" * 60)
    print("Example 2: Signal Generation")
    print("=" * 60)

    # Create sample OHLCV data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    # Generate synthetic price data
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.randn(100) * 0.5,
        'high': close_prices + abs(np.random.randn(100) * 1.5),
        'low': close_prices - abs(np.random.randn(100) * 1.5),
        'close': close_prices,
        'volume': np.random.randint(100000, 1000000, 100),
        'oi': np.random.randint(10000, 100000, 100)
    })

    # Initialize signal generator
    signal_gen = SignalGenerator()

    # Generate combined signals
    df_with_signals = signal_gen.generate_combined_signal(df)

    # Get latest signal
    latest_signal = signal_gen.get_latest_signal(df_with_signals)

    print(f"\n📊 Latest Signal Analysis:")
    print(f"   Signal: {latest_signal['signal']}")
    print(f"   Strength: {latest_signal['strength']}")
    print(f"   Buy Score: {latest_signal['buy_score']}")
    print(f"   Sell Score: {latest_signal['sell_score']}")
    print(f"\n   Indicator Signals:")
    for indicator, signal in latest_signal['indicators'].items():
        if isinstance(signal, str):
            print(f"      {indicator}: {signal}")

    print("\n✓ Signals generated successfully")


def example_3_screener():
    """Example 3: Use screener to filter stocks"""
    print("\n" + "=" * 60)
    print("Example 3: Stock Screening")
    print("=" * 60)

    # Create sample market data
    instruments = [f"STOCK_{i}" for i in range(50)]
    np.random.seed(42)

    market_data = pd.DataFrame({
        'instrument': instruments,
        'close': np.random.uniform(100, 5000, 50),
        'volume': np.random.randint(50000, 2000000, 50),
        'avg_volume': np.random.randint(50000, 1000000, 50),
        'open': np.random.uniform(100, 5000, 50),
        'high': np.random.uniform(100, 5000, 50),
        'low': np.random.uniform(100, 5000, 50),
    })

    # Calculate returns for momentum screening
    market_data['return_1d'] = np.random.uniform(-5, 5, 50)
    market_data['return_5d'] = np.random.uniform(-10, 10, 50)
    market_data['return_10d'] = np.random.uniform(-15, 15, 50)

    # Initialize screener
    screener = FNOScreener({
        'min_volume': 100000,
        'volume_surge_factor': 1.5,
        'min_price': 200,
        'max_price': 4000
    })

    print(f"\n📈 Initial dataset: {len(market_data)} instruments")

    # Screen by volume
    volume_filtered = screener.screen_by_volume(market_data)
    print(f"   After volume filter: {len(volume_filtered)} instruments")

    # Screen by price
    price_filtered = screener.screen_by_price(volume_filtered)
    print(f"   After price filter: {len(price_filtered)} instruments")

    # Multi-criteria screening
    screened = screener.multi_criteria_screen(
        market_data,
        filters=['volume', 'price', 'momentum']
    )
    print(f"\n✓ Final screened results: {len(screened)} instruments")

    # Get top opportunities
    if not screened.empty and 'momentum_score' in screened.columns:
        top_picks = screener.get_top_opportunities(
            screened,
            sort_by='momentum_score',
            top_n=5
        )
        print(f"\n🎯 Top 5 Opportunities:")
        for idx, row in top_picks.iterrows():
            print(f"   {row['instrument']}: Momentum Score = {row.get('momentum_score', 'N/A')}")


def example_4_option_screening():
    """Example 4: Option chain screening"""
    print("\n" + "=" * 60)
    print("Example 4: Option Chain Screening")
    print("=" * 60)

    # Create sample option chain data
    spot_price = 21500  # Nifty spot price
    strikes = range(21000, 22000, 50)
    np.random.seed(42)

    option_data = []
    for strike in strikes:
        # Call option
        option_data.append({
            'strike': strike,
            'option_type': 'CE',
            'oi': np.random.randint(1000, 100000),
            'volume': np.random.randint(100, 50000),
            'last_price': max(spot_price - strike, 10) if strike < spot_price else np.random.uniform(10, 200)
        })
        # Put option
        option_data.append({
            'strike': strike,
            'option_type': 'PE',
            'oi': np.random.randint(1000, 100000),
            'volume': np.random.randint(100, 50000),
            'last_price': max(strike - spot_price, 10) if strike > spot_price else np.random.uniform(10, 200)
        })

    option_df = pd.DataFrame(option_data)

    # Initialize screener
    screener = FNOScreener()

    # Screen for option strategies
    screened_options = screener.screen_option_strategies(option_df, spot_price)

    print(f"\n📊 Option Chain Analysis:")
    print(f"   Spot Price: {spot_price}")
    print(f"   Total Options: {len(option_df)}")
    print(f"   Filtered Options: {len(screened_options)}")

    # Show ATM options
    if not screened_options.empty:
        atm_options = screened_options[screened_options['is_atm']]
        print(f"\n💰 ATM Options (within 2% of spot):")
        if not atm_options.empty:
            for idx, row in atm_options.head(5).iterrows():
                print(f"   Strike {row['strike']} {row['option_type']}: "
                      f"OI={row['oi']}, Volume={row['volume']}")

    print("\n✓ Option screening completed")


def example_5_combined_workflow():
    """Example 5: Complete workflow - Analyze, Screen, and Generate Signals"""
    print("\n" + "=" * 60)
    print("Example 5: Complete Trading Workflow")
    print("=" * 60)

    # Step 1: Generate sample market data
    print("\n📥 Step 1: Fetching market data...")
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    instruments_data = {}
    for instrument in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
        close_prices = 20000 + np.cumsum(np.random.randn(100) * 100)
        instruments_data[instrument] = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.randn(100) * 50,
            'high': close_prices + abs(np.random.randn(100) * 100),
            'low': close_prices - abs(np.random.randn(100) * 100),
            'close': close_prices,
            'volume': np.random.randint(100000, 1000000, 100),
            'oi': np.random.randint(10000, 100000, 100)
        })

    # Step 2: Generate signals for each instrument
    print("\n📊 Step 2: Generating trading signals...")
    signal_gen = SignalGenerator()

    signals_summary = []
    for instrument, df in instruments_data.items():
        df_with_signals = signal_gen.generate_combined_signal(df)
        latest_signal = signal_gen.get_latest_signal(df_with_signals)

        signals_summary.append({
            'instrument': instrument,
            'signal': latest_signal['signal'],
            'strength': latest_signal['strength'],
            'close': latest_signal['close']
        })

        print(f"   {instrument}: {latest_signal['signal']} (Strength: {latest_signal['strength']})")

    # Step 3: Create summary DataFrame for screening
    print("\n🔍 Step 3: Screening for best opportunities...")
    summary_df = pd.DataFrame(signals_summary)

    # Filter for strong buy/sell signals
    strong_signals = summary_df[summary_df['strength'] >= 2]

    print(f"\n🎯 Strong Signals Found: {len(strong_signals)}")
    if not strong_signals.empty:
        for idx, row in strong_signals.iterrows():
            print(f"   {row['instrument']}: {row['signal']} "
                  f"(Strength: {row['strength']}, Price: {row['close']:.2f})")
    else:
        print("   No strong signals at this time")

    print("\n✓ Complete workflow executed successfully")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("F&O Trading App - Usage Examples")
    print("=" * 70)

    examples = [
        example_1_initialization,
        example_2_signal_generation,
        example_3_screener,
        example_4_option_screening,
        example_5_combined_workflow
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ Error in {example.__name__}: {e}")

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
