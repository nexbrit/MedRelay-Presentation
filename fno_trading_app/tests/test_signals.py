"""
Unit tests for signal generation
"""

import pytest
import pandas as pd
import numpy as np
from signals import SignalGenerator, TechnicalIndicators, SignalType


class TestTechnicalIndicators:
    """Test technical indicators calculations"""

    @pytest.fixture
    def sample_data(self):
        """Create sample price data"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        close_prices = 100 + np.cumsum(np.random.randn(100) * 2)

        return pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.randn(100) * 0.5,
            'high': close_prices + abs(np.random.randn(100) * 1.5),
            'low': close_prices - abs(np.random.randn(100) * 1.5),
            'close': close_prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })

    def test_rsi_calculation(self, sample_data):
        """Test RSI calculation"""
        indicators = TechnicalIndicators()
        rsi = indicators.calculate_rsi(sample_data['close'], period=14)

        assert len(rsi) == len(sample_data)
        assert rsi.min() >= 0
        assert rsi.max() <= 100
        assert not rsi.isna().all()  # Should have some valid values

    def test_macd_calculation(self, sample_data):
        """Test MACD calculation"""
        indicators = TechnicalIndicators()
        macd, signal, hist = indicators.calculate_macd(sample_data['close'])

        assert len(macd) == len(sample_data)
        assert len(signal) == len(sample_data)
        assert len(hist) == len(sample_data)

    def test_ema_calculation(self, sample_data):
        """Test EMA calculation"""
        indicators = TechnicalIndicators()
        ema = indicators.calculate_ema(sample_data['close'], period=20)

        assert len(ema) == len(sample_data)
        assert not ema.isna().all()

    def test_bollinger_bands(self, sample_data):
        """Test Bollinger Bands calculation"""
        indicators = TechnicalIndicators()
        upper, middle, lower = indicators.calculate_bollinger_bands(
            sample_data['close'], period=20
        )

        assert len(upper) == len(sample_data)
        # Upper band should be above lower band (where data is valid)
        valid_data = ~upper.isna() & ~lower.isna()
        assert (upper[valid_data] >= lower[valid_data]).all()


class TestSignalGenerator:
    """Test signal generation"""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        close_prices = 100 + np.cumsum(np.random.randn(100) * 2)

        return pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.randn(100) * 0.5,
            'high': close_prices + abs(np.random.randn(100) * 1.5),
            'low': close_prices - abs(np.random.randn(100) * 1.5),
            'close': close_prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })

    def test_rsi_signal_generation(self, sample_data):
        """Test RSI signal generation"""
        signal_gen = SignalGenerator()
        df_with_signals = signal_gen.generate_rsi_signal(sample_data)

        assert 'rsi' in df_with_signals.columns
        assert 'rsi_signal' in df_with_signals.columns

        # Signals should be valid types
        valid_signals = {
            SignalType.BUY.value,
            SignalType.SELL.value,
            SignalType.HOLD.value,
            SignalType.STRONG_BUY.value,
            SignalType.STRONG_SELL.value
        }
        assert df_with_signals['rsi_signal'].isin(valid_signals).all()

    def test_macd_signal_generation(self, sample_data):
        """Test MACD signal generation"""
        signal_gen = SignalGenerator()
        df_with_signals = signal_gen.generate_macd_signal(sample_data)

        assert 'macd' in df_with_signals.columns
        assert 'macd_signal' in df_with_signals.columns
        assert 'macd_crossover' in df_with_signals.columns

    def test_combined_signal_generation(self, sample_data):
        """Test combined signal generation"""
        signal_gen = SignalGenerator()
        df_with_signals = signal_gen.generate_combined_signal(sample_data)

        # Check all signal columns exist
        required_columns = [
            'rsi_signal', 'macd_crossover', 'ema_signal',
            'bb_signal', 'supertrend_signal', 'combined_signal',
            'buy_score', 'sell_score', 'signal_strength'
        ]

        for col in required_columns:
            assert col in df_with_signals.columns

        # Scores should be non-negative
        assert (df_with_signals['buy_score'] >= 0).all()
        assert (df_with_signals['sell_score'] >= 0).all()

    def test_get_latest_signal(self, sample_data):
        """Test getting latest signal"""
        signal_gen = SignalGenerator()
        df_with_signals = signal_gen.generate_combined_signal(sample_data)
        latest = signal_gen.get_latest_signal(df_with_signals)

        assert isinstance(latest, dict)
        assert 'signal' in latest
        assert 'strength' in latest
        assert 'buy_score' in latest
        assert 'sell_score' in latest
        assert 'indicators' in latest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
