"""
Upstox API Integration Module
Handles authentication, market data retrieval, and order execution
"""

import upstox_client
from upstox_client.rest import ApiException
import logging
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class UpstoxClient:
    """Wrapper class for Upstox API operations"""

    def __init__(self, api_key: str = None, api_secret: str = None, redirect_uri: str = None, sandbox: bool = True):
        """
        Initialize Upstox client

        Args:
            api_key: Upstox API key
            api_secret: Upstox API secret
            redirect_uri: OAuth redirect URI
            sandbox: Use sandbox environment for testing
        """
        self.api_key = api_key or os.getenv('UPSTOX_API_KEY')
        self.api_secret = api_secret or os.getenv('UPSTOX_API_SECRET')
        self.redirect_uri = redirect_uri or os.getenv('UPSTOX_REDIRECT_URI', 'http://localhost:8080')
        self.sandbox = sandbox

        self.configuration = upstox_client.Configuration()
        if sandbox:
            self.configuration.host = "https://api-v2.upstox.com"

        self.access_token = None
        self.api_client = None

        logger.info(f"Upstox client initialized in {'sandbox' if sandbox else 'production'} mode")

    def get_authorization_url(self) -> str:
        """
        Get OAuth authorization URL for user login

        Returns:
            Authorization URL string
        """
        auth_url = (
            f"https://api-v2.upstox.com/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={self.api_key}"
            f"&redirect_uri={self.redirect_uri}"
        )
        logger.info(f"Authorization URL generated: {auth_url}")
        return auth_url

    def set_access_token(self, access_token: str):
        """
        Set access token for API authentication

        Args:
            access_token: OAuth access token
        """
        self.access_token = access_token
        self.configuration.access_token = access_token
        self.api_client = upstox_client.ApiClient(self.configuration)
        logger.info("Access token set successfully")

    def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information

        Returns:
            Dictionary containing user profile data
        """
        try:
            api_instance = upstox_client.UserApi(self.api_client)
            api_response = api_instance.get_profile()
            logger.info("Profile retrieved successfully")
            return api_response.to_dict()
        except ApiException as e:
            logger.error(f"Exception when calling UserApi->get_profile: {e}")
            raise

    def get_market_quote(self, instruments: List[str]) -> pd.DataFrame:
        """
        Get market quotes for given instruments

        Args:
            instruments: List of instrument keys (e.g., 'NSE_INDEX|Nifty 50')

        Returns:
            DataFrame with market quote data
        """
        try:
            api_instance = upstox_client.MarketQuoteApi(self.api_client)
            api_response = api_instance.get_full_market_quote(','.join(instruments), 'v2')

            quotes_data = []
            for instrument, data in api_response.data.items():
                quote = {
                    'instrument': instrument,
                    'last_price': data.ohlc.close if data.ohlc else None,
                    'open': data.ohlc.open if data.ohlc else None,
                    'high': data.ohlc.high if data.ohlc else None,
                    'low': data.ohlc.low if data.ohlc else None,
                    'volume': data.volume if hasattr(data, 'volume') else None,
                    'timestamp': datetime.now()
                }
                quotes_data.append(quote)

            df = pd.DataFrame(quotes_data)
            logger.info(f"Market quotes retrieved for {len(instruments)} instruments")
            return df

        except ApiException as e:
            logger.error(f"Exception when calling MarketQuoteApi: {e}")
            raise

    def get_historical_data(
        self,
        instrument_key: str,
        interval: str = '1day',
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Get historical candle data for an instrument

        Args:
            instrument_key: Instrument key (e.g., 'NSE_INDEX|Nifty 50')
            interval: Candle interval (1minute, 30minute, 1day, etc.)
            days_back: Number of days of historical data

        Returns:
            DataFrame with OHLCV data
        """
        try:
            api_instance = upstox_client.HistoryApi(self.api_client)

            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)

            api_response = api_instance.get_historical_candle_data(
                instrument_key=instrument_key,
                interval=interval,
                to_date=to_date.strftime('%Y-%m-%d'),
                from_date=from_date.strftime('%Y-%m-%d')
            )

            if api_response.data and api_response.data.candles:
                df = pd.DataFrame(
                    api_response.data.candles,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                logger.info(f"Historical data retrieved: {len(df)} candles for {instrument_key}")
                return df
            else:
                logger.warning(f"No historical data available for {instrument_key}")
                return pd.DataFrame()

        except ApiException as e:
            logger.error(f"Exception when calling HistoryApi: {e}")
            raise

    def get_option_chain(self, instrument_key: str, expiry_date: str = None) -> pd.DataFrame:
        """
        Get option chain data for an underlying instrument

        Args:
            instrument_key: Underlying instrument key
            expiry_date: Expiry date (YYYY-MM-DD format), defaults to nearest expiry

        Returns:
            DataFrame with option chain data
        """
        try:
            api_instance = upstox_client.OptionsApi(self.api_client)

            if not expiry_date:
                # Get nearest expiry
                expiry_response = api_instance.get_option_expiries(instrument_key)
                expiry_date = expiry_response.data[0] if expiry_response.data else None

            if not expiry_date:
                raise ValueError("No expiry date available")

            api_response = api_instance.get_option_contracts(
                instrument_key=instrument_key,
                expiry_date=expiry_date
            )

            options_data = []
            if api_response.data:
                for option in api_response.data:
                    options_data.append({
                        'strike': option.strike_price,
                        'option_type': option.option_type,
                        'instrument_key': option.instrument_key,
                        'trading_symbol': option.trading_symbol,
                        'expiry': expiry_date
                    })

            df = pd.DataFrame(options_data)
            logger.info(f"Option chain retrieved: {len(df)} contracts")
            return df

        except ApiException as e:
            logger.error(f"Exception when calling OptionsApi: {e}")
            raise

    def place_order(
        self,
        instrument_key: str,
        quantity: int,
        transaction_type: str,  # 'BUY' or 'SELL'
        order_type: str = 'MARKET',  # 'MARKET' or 'LIMIT'
        price: float = 0.0,
        product: str = 'D',  # 'D' for delivery, 'I' for intraday
        validity: str = 'DAY'
    ) -> Dict[str, Any]:
        """
        Place an order

        Args:
            instrument_key: Instrument key
            quantity: Order quantity
            transaction_type: 'BUY' or 'SELL'
            order_type: 'MARKET' or 'LIMIT'
            price: Price (for limit orders)
            product: Product type ('D' for delivery, 'I' for intraday)
            validity: Order validity ('DAY' or 'IOC')

        Returns:
            Dictionary with order details
        """
        try:
            api_instance = upstox_client.OrderApi(self.api_client)

            order_data = upstox_client.PlaceOrderRequest(
                quantity=quantity,
                product=product,
                validity=validity,
                price=price,
                tag='fno_trading_app',
                instrument_token=instrument_key,
                order_type=order_type,
                transaction_type=transaction_type,
                disclosed_quantity=0,
                trigger_price=0,
                is_amo=False
            )

            api_response = api_instance.place_order(order_data)
            logger.info(f"Order placed: {transaction_type} {quantity} of {instrument_key}")
            return api_response.to_dict()

        except ApiException as e:
            logger.error(f"Exception when placing order: {e}")
            raise

    def get_positions(self) -> pd.DataFrame:
        """
        Get current positions

        Returns:
            DataFrame with position data
        """
        try:
            api_instance = upstox_client.PortfolioApi(self.api_client)
            api_response = api_instance.get_positions()

            positions_data = []
            if api_response.data:
                for pos in api_response.data:
                    positions_data.append({
                        'instrument': pos.instrument_token,
                        'quantity': pos.quantity,
                        'average_price': pos.average_price,
                        'last_price': pos.last_price,
                        'pnl': pos.pnl,
                        'product': pos.product
                    })

            df = pd.DataFrame(positions_data)
            logger.info(f"Retrieved {len(df)} positions")
            return df

        except ApiException as e:
            logger.error(f"Exception when getting positions: {e}")
            raise

    def get_holdings(self) -> pd.DataFrame:
        """
        Get holdings

        Returns:
            DataFrame with holdings data
        """
        try:
            api_instance = upstox_client.PortfolioApi(self.api_client)
            api_response = api_instance.get_holdings()

            holdings_data = []
            if api_response.data:
                for holding in api_response.data:
                    holdings_data.append({
                        'instrument': holding.instrument_token,
                        'quantity': holding.quantity,
                        'average_price': holding.average_price,
                        'last_price': holding.last_price,
                        'pnl': holding.pnl
                    })

            df = pd.DataFrame(holdings_data)
            logger.info(f"Retrieved {len(df)} holdings")
            return df

        except ApiException as e:
            logger.error(f"Exception when getting holdings: {e}")
            raise
