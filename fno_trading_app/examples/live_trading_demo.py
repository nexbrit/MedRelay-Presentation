"""
Live Trading Demo (Sandbox Mode)
Demonstrates real-time signal generation and monitoring
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import FNOTradingApp
from signals import SignalType
import time


def demo_live_monitoring():
    """
    Demo: Live monitoring of instruments
    Note: Requires Upstox API credentials
    """
    print("\n" + "=" * 70)
    print("Live Trading Demo - Sandbox Mode")
    print("=" * 70)

    # Initialize app
    app = FNOTradingApp()

    print("\n📋 Setup Instructions:")
    print("1. Ensure you have set up your Upstox API credentials in .env")
    print("2. Get authorization URL and complete OAuth flow")
    print("3. Set access token using app.setup_authentication(access_token)")
    print("\nFor this demo, we'll show the structure without live connection")

    # Show what would happen in live mode
    print("\n" + "-" * 70)
    print("DEMO MODE - Example Output")
    print("-" * 70)

    demo_instruments = [
        'NSE_INDEX|Nifty 50',
        'NSE_INDEX|Nifty Bank',
        'NSE_INDEX|FINNIFTY'
    ]

    print(f"\n📊 Would monitor {len(demo_instruments)} instruments:")
    for instrument in demo_instruments:
        print(f"   - {instrument}")

    print("\n🔄 Monitoring cycle (example):")
    print("   Timestamp: 2025-01-15 09:30:00")
    print("   " + "=" * 60)

    # Simulate monitoring output
    example_signals = [
        {
            'instrument': 'NSE_INDEX|Nifty 50',
            'price': 21547.30,
            'signal': SignalType.BUY.value,
            'strength': 3,
            'rsi': 42.5,
            'macd': 'BUY'
        },
        {
            'instrument': 'NSE_INDEX|Nifty Bank',
            'price': 45123.80,
            'signal': SignalType.HOLD.value,
            'strength': 1,
            'rsi': 55.2,
            'macd': 'HOLD'
        },
        {
            'instrument': 'NSE_INDEX|FINNIFTY',
            'price': 19876.50,
            'signal': SignalType.STRONG_SELL.value,
            'strength': 4,
            'rsi': 78.3,
            'macd': 'SELL'
        }
    ]

    for sig in example_signals:
        print(f"\n   {sig['instrument']}")
        print(f"   Price: ₹{sig['price']}")
        print(f"   Signal: {sig['signal']} (Strength: {sig['strength']})")
        print(f"   RSI: {sig['rsi']}, MACD: {sig['macd']}")

        if sig['signal'] in [SignalType.STRONG_BUY.value, SignalType.STRONG_SELL.value]:
            print(f"   🚨 ALERT: Strong {sig['signal']} signal detected!")

    print("\n" + "=" * 70)
    print("Live monitoring demo completed")
    print("\nTo run actual live monitoring:")
    print("   app.live_monitoring(instruments, interval_seconds=300)")
    print("=" * 70 + "\n")


def demo_quick_analysis():
    """Demo: Quick analysis without live connection"""
    print("\n" + "=" * 70)
    print("Quick Analysis Demo")
    print("=" * 70)

    print("\n💡 This demonstrates what happens when you analyze an instrument:")
    print("\nSteps:")
    print("1. Fetch historical data (90 days by default)")
    print("2. Calculate technical indicators (RSI, MACD, EMA, etc.)")
    print("3. Generate individual signals from each indicator")
    print("4. Combine signals with weighted scoring")
    print("5. Output final signal with strength and details")

    print("\n📊 Example Analysis Output:")
    print("-" * 70)
    print("Instrument: NSE_INDEX|Nifty 50")
    print("Timestamp: 2025-01-15 15:30:00")
    print("Current Price: ₹21,547.30")
    print("\nSIGNAL: BUY")
    print("Strength: 3 (Buy: 3, Sell: 0)")
    print("\nIndicator Details:")
    print("  RSI: 42.50 - BUY (oversold)")
    print("  MACD: 15.23 - BUY (bullish crossover)")
    print("  EMA Crossover: BUY (golden cross)")
    print("  Bollinger Bands: HOLD")
    print("  Supertrend: HOLD")
    print("-" * 70)

    print("\n✓ Analysis provides comprehensive view of market conditions")
    print("=" * 70 + "\n")


def demo_option_chain():
    """Demo: Option chain analysis"""
    print("\n" + "=" * 70)
    print("Option Chain Analysis Demo")
    print("=" * 70)

    print("\n📈 Option Chain Features:")
    print("- Fetch complete option chain for any underlying")
    print("- Calculate Put-Call Ratio (PCR)")
    print("- Identify high Open Interest strikes")
    print("- Filter ATM, ITM, OTM options")
    print("- Detect unusual activity")

    print("\n📊 Example Option Chain Analysis:")
    print("-" * 70)
    print("Underlying: NIFTY")
    print("Spot Price: ₹21,547.30")
    print("Expiry: 2025-01-30")
    print("\nPut-Call Ratio: 1.15 (Slightly bullish)")
    print("\nHigh OI Strikes:")
    print("  21500 CE: OI = 2,45,678 | Volume = 45,234")
    print("  21500 PE: OI = 3,12,456 | Volume = 52,123")
    print("  21600 CE: OI = 1,87,234 | Volume = 34,567")
    print("\nATM Options:")
    print("  21550 CE: Premium = ₹125.50 | IV = 18.5%")
    print("  21550 PE: Premium = ₹132.75 | IV = 19.2%")
    print("-" * 70)

    print("\n✓ Option chain analysis helps identify key levels and sentiment")
    print("=" * 70 + "\n")


def demo_risk_management():
    """Demo: Risk management features"""
    print("\n" + "=" * 70)
    print("Risk Management Demo")
    print("=" * 70)

    print("\n⚠️ Risk Management Features:")
    print("- Position sizing based on capital")
    print("- Stop-loss calculations")
    print("- Take-profit targets")
    print("- Maximum position limits")
    print("- Portfolio-level risk tracking")

    print("\n📊 Example Risk Calculation:")
    print("-" * 70)
    print("Account Balance: ₹5,00,000")
    print("Risk per Trade: 2%")
    print("Maximum Risk: ₹10,000")
    print("\nProposed Trade:")
    print("  Instrument: NIFTY 21500 CE")
    print("  Entry Price: ₹125.50")
    print("  Stop Loss: ₹115.00 (-8.36%)")
    print("  Take Profit: ₹145.00 (+15.54%)")
    print("  Quantity: 95 lots (Risk ≈ ₹9,975)")
    print("  Risk-Reward Ratio: 1:1.86")
    print("-" * 70)

    print("\n✓ Proper risk management is crucial for long-term success")
    print("=" * 70 + "\n")


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("F&O Trading App - Live Trading Demonstrations")
    print("=" * 80)

    demos = [
        demo_quick_analysis,
        demo_option_chain,
        demo_risk_management,
        demo_live_monitoring
    ]

    for demo in demos:
        try:
            demo()
            time.sleep(1)  # Brief pause between demos
        except Exception as e:
            print(f"\n❌ Error in {demo.__name__}: {e}")

    print("\n" + "=" * 80)
    print("All demonstrations completed!")
    print("\n📚 Next Steps:")
    print("1. Set up your Upstox API credentials")
    print("2. Test in sandbox mode")
    print("3. Backtest your strategies")
    print("4. Start with small positions")
    print("5. Monitor and adjust")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
