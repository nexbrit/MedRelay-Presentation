"""
F&O Screener Module
Data-driven screeners using pandas for filtering trading opportunities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FNOScreener:
    """Advanced F&O screener with multiple filtering strategies"""

    def __init__(self, config: Dict = None):
        """
        Initialize screener

        Args:
            config: Configuration dictionary with screening parameters
        """
        self.config = config or {}

        # Volume filters
        self.min_volume = self.config.get('min_volume', 100000)
        self.volume_surge_factor = self.config.get('volume_surge_factor', 2.0)

        # Price filters
        self.min_price = self.config.get('min_price', 10)
        self.max_price = self.config.get('max_price', 50000)

        # Volatility filters
        self.min_atr_percentage = self.config.get('min_atr_percentage', 1.0)
        self.max_atr_percentage = self.config.get('max_atr_percentage', 10.0)

        # Option filters
        self.min_oi = self.config.get('min_oi', 100)
        self.min_oi_change_percentage = self.config.get('min_oi_change_percentage', 10)

        logger.info("FNO Screener initialized")

    def screen_by_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Screen instruments by volume criteria

        Args:
            df: DataFrame with market data including 'volume' column

        Returns:
            Filtered DataFrame
        """
        if 'volume' not in df.columns:
            logger.warning("Volume column not found in DataFrame")
            return df

        # Calculate average volume (if historical data available)
        if 'avg_volume' in df.columns:
            volume_surge = df['volume'] / df['avg_volume']
            filtered = df[
                (df['volume'] >= self.min_volume) &
                (volume_surge >= self.volume_surge_factor)
            ].copy()
        else:
            filtered = df[df['volume'] >= self.min_volume].copy()

        logger.info(f"Volume screen: {len(filtered)} of {len(df)} instruments passed")
        return filtered

    def screen_by_price(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Screen instruments by price range

        Args:
            df: DataFrame with 'close' or 'last_price' column

        Returns:
            Filtered DataFrame
        """
        price_col = 'close' if 'close' in df.columns else 'last_price'

        if price_col not in df.columns:
            logger.warning(f"Price column '{price_col}' not found in DataFrame")
            return df

        filtered = df[
            (df[price_col] >= self.min_price) &
            (df[price_col] <= self.max_price)
        ].copy()

        logger.info(f"Price screen: {len(filtered)} of {len(df)} instruments passed")
        return filtered

    def screen_by_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Screen by volatility (ATR as percentage of price)

        Args:
            df: DataFrame with 'atr' and price columns

        Returns:
            Filtered DataFrame
        """
        if 'atr' not in df.columns:
            logger.warning("ATR column not found in DataFrame")
            return df

        price_col = 'close' if 'close' in df.columns else 'last_price'
        df['atr_percentage'] = (df['atr'] / df[price_col]) * 100

        filtered = df[
            (df['atr_percentage'] >= self.min_atr_percentage) &
            (df['atr_percentage'] <= self.max_atr_percentage)
        ].copy()

        logger.info(f"Volatility screen: {len(filtered)} of {len(df)} instruments passed")
        return filtered

    def screen_by_open_interest(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Screen options by open interest

        Args:
            df: DataFrame with 'oi' (open interest) column

        Returns:
            Filtered DataFrame
        """
        if 'oi' not in df.columns:
            logger.warning("Open Interest column not found in DataFrame")
            return df

        # Calculate OI change if historical data available
        if 'oi_prev' in df.columns:
            df['oi_change_pct'] = ((df['oi'] - df['oi_prev']) / df['oi_prev']) * 100
            filtered = df[
                (df['oi'] >= self.min_oi) &
                (abs(df['oi_change_pct']) >= self.min_oi_change_percentage)
            ].copy()
        else:
            filtered = df[df['oi'] >= self.min_oi].copy()

        logger.info(f"OI screen: {len(filtered)} of {len(df)} instruments passed")
        return filtered

    def screen_by_price_action(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Screen by price action patterns

        Args:
            df: DataFrame with OHLC data

        Returns:
            Filtered DataFrame with pattern indicators
        """
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            logger.warning("Required OHLC columns not found")
            return df

        df = df.copy()

        # Bullish patterns
        df['bullish_engulfing'] = (
            (df['close'] > df['open']) &  # Current candle is bullish
            (df['close'].shift(1) < df['open'].shift(1)) &  # Previous candle is bearish
            (df['close'] > df['open'].shift(1)) &  # Current close > previous open
            (df['open'] < df['close'].shift(1))  # Current open < previous close
        )

        df['hammer'] = (
            (df['close'] > df['open']) &  # Bullish candle
            ((df['high'] - df['close']) < (df['close'] - df['open']) * 0.3) &  # Small upper wick
            ((df['open'] - df['low']) > (df['close'] - df['open']) * 2)  # Long lower wick
        )

        # Bearish patterns
        df['bearish_engulfing'] = (
            (df['close'] < df['open']) &  # Current candle is bearish
            (df['close'].shift(1) > df['open'].shift(1)) &  # Previous candle is bullish
            (df['close'] < df['open'].shift(1)) &  # Current close < previous open
            (df['open'] > df['close'].shift(1))  # Current open > previous close
        )

        df['shooting_star'] = (
            (df['close'] < df['open']) &  # Bearish candle
            ((df['high'] - df['open']) > (df['open'] - df['close']) * 2) &  # Long upper wick
            ((df['close'] - df['low']) < (df['open'] - df['close']) * 0.3)  # Small lower wick
        )

        # Filter instruments with recent patterns
        filtered = df[
            df['bullish_engulfing'] | df['hammer'] |
            df['bearish_engulfing'] | df['shooting_star']
        ].copy()

        logger.info(f"Price action screen: {len(filtered)} of {len(df)} instruments with patterns")
        return filtered

    def screen_breakout_candidates(self, df: pd.DataFrame, lookback_period: int = 20) -> pd.DataFrame:
        """
        Screen for breakout candidates

        Args:
            df: DataFrame with OHLC data
            lookback_period: Period for calculating breakout levels

        Returns:
            Filtered DataFrame with breakout indicators
        """
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            logger.warning("Required columns for breakout screening not found")
            return df

        df = df.copy()

        # Calculate resistance and support levels
        df['resistance'] = df['high'].rolling(window=lookback_period).max()
        df['support'] = df['low'].rolling(window=lookback_period).min()

        # Breakout conditions
        df['breakout_up'] = df['close'] > df['resistance'].shift(1)
        df['breakout_down'] = df['close'] < df['support'].shift(1)

        # Near breakout (within 2% of resistance/support)
        df['near_resistance'] = (
            (df['close'] >= df['resistance'] * 0.98) &
            (df['close'] <= df['resistance'])
        )
        df['near_support'] = (
            (df['close'] <= df['support'] * 1.02) &
            (df['close'] >= df['support'])
        )

        # Filter breakout candidates
        filtered = df[
            df['breakout_up'] | df['breakout_down'] |
            df['near_resistance'] | df['near_support']
        ].copy()

        logger.info(f"Breakout screen: {len(filtered)} of {len(df)} candidates found")
        return filtered

    def screen_momentum_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Screen for high momentum stocks

        Args:
            df: DataFrame with price data

        Returns:
            Filtered DataFrame with momentum indicators
        """
        if 'close' not in df.columns:
            logger.warning("Close price column not found")
            return df

        df = df.copy()

        # Calculate returns
        df['return_1d'] = df['close'].pct_change(1) * 100
        df['return_5d'] = df['close'].pct_change(5) * 100
        df['return_10d'] = df['close'].pct_change(10) * 100

        # Momentum score (simple average of returns)
        df['momentum_score'] = (
            df['return_1d'] * 0.5 +
            df['return_5d'] * 0.3 +
            df['return_10d'] * 0.2
        )

        # Filter high momentum (positive across all timeframes)
        filtered = df[
            (df['return_1d'] > 0) &
            (df['return_5d'] > 2) &
            (df['return_10d'] > 5) &
            (df['momentum_score'] > 3)
        ].copy()

        # Sort by momentum score
        filtered = filtered.sort_values('momentum_score', ascending=False)

        logger.info(f"Momentum screen: {len(filtered)} of {len(df)} high momentum stocks")
        return filtered

    def screen_option_strategies(self, df: pd.DataFrame, spot_price: float) -> pd.DataFrame:
        """
        Screen for option trading strategies

        Args:
            df: DataFrame with option chain data
            spot_price: Current spot price of underlying

        Returns:
            DataFrame with strategy recommendations
        """
        required_cols = ['strike', 'option_type', 'oi', 'volume']
        if not all(col in df.columns for col in required_cols):
            logger.warning("Required option columns not found")
            return df

        df = df.copy()

        # Calculate moneyness
        df['moneyness'] = (df['strike'] - spot_price) / spot_price * 100

        # ATM options (within 2% of spot)
        df['is_atm'] = abs(df['moneyness']) <= 2

        # ITM options
        df['is_itm'] = (
            ((df['option_type'] == 'CE') & (df['strike'] < spot_price)) |
            ((df['option_type'] == 'PE') & (df['strike'] > spot_price))
        )

        # OTM options
        df['is_otm'] = (
            ((df['option_type'] == 'CE') & (df['strike'] > spot_price)) |
            ((df['option_type'] == 'PE') & (df['strike'] < spot_price))
        )

        # High OI strikes (potential support/resistance)
        if 'oi' in df.columns:
            df['high_oi'] = df['oi'] > df['oi'].quantile(0.75)

        # PCR (Put-Call Ratio) analysis
        ce_df = df[df['option_type'] == 'CE']
        pe_df = df[df['option_type'] == 'PE']

        if not ce_df.empty and not pe_df.empty:
            total_ce_oi = ce_df['oi'].sum()
            total_pe_oi = pe_df['oi'].sum()
            pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

            logger.info(f"Put-Call Ratio: {pcr:.2f}")

        # Filter interesting options
        filtered = df[
            (df['is_atm'] | df['high_oi']) &
            (df['volume'] > df['volume'].quantile(0.5))
        ].copy()

        logger.info(f"Option strategy screen: {len(filtered)} contracts of interest")
        return filtered

    def apply_custom_filter(
        self,
        df: pd.DataFrame,
        filter_func: Callable[[pd.DataFrame], pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Apply a custom filter function

        Args:
            df: DataFrame to filter
            filter_func: Custom filter function

        Returns:
            Filtered DataFrame
        """
        try:
            filtered = filter_func(df)
            logger.info(f"Custom filter applied: {len(filtered)} of {len(df)} passed")
            return filtered
        except Exception as e:
            logger.error(f"Error applying custom filter: {e}")
            return df

    def multi_criteria_screen(
        self,
        df: pd.DataFrame,
        filters: List[str] = None
    ) -> pd.DataFrame:
        """
        Apply multiple screening criteria

        Args:
            df: DataFrame with market data
            filters: List of filter names to apply

        Returns:
            Filtered DataFrame
        """
        if filters is None:
            filters = ['volume', 'price', 'volatility']

        filtered_df = df.copy()

        filter_map = {
            'volume': self.screen_by_volume,
            'price': self.screen_by_price,
            'volatility': self.screen_by_volatility,
            'oi': self.screen_by_open_interest,
            'price_action': self.screen_by_price_action,
            'breakout': self.screen_breakout_candidates,
            'momentum': self.screen_momentum_stocks
        }

        for filter_name in filters:
            if filter_name in filter_map:
                filtered_df = filter_map[filter_name](filtered_df)
                logger.debug(f"Applied {filter_name} filter: {len(filtered_df)} remaining")

        logger.info(f"Multi-criteria screen complete: {len(filtered_df)} of {len(df)} passed all filters")
        return filtered_df

    def get_top_opportunities(
        self,
        df: pd.DataFrame,
        sort_by: str = 'momentum_score',
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get top trading opportunities

        Args:
            df: Screened DataFrame
            sort_by: Column to sort by
            top_n: Number of top opportunities to return

        Returns:
            DataFrame with top opportunities
        """
        if sort_by not in df.columns:
            logger.warning(f"Sort column '{sort_by}' not found, returning top {top_n} by index")
            return df.head(top_n)

        top_df = df.nlargest(top_n, sort_by)
        logger.info(f"Top {top_n} opportunities selected by {sort_by}")
        return top_df
