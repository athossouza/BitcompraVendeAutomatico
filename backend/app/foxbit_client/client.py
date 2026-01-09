import logging
import requests
import time
from typing import Dict, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class FoxbitClient:
    """
    Client for interacting with the Foxbit API.
    Implements retries, backoff, and error handling.
    """
    BASE_URL = "https://api.foxbit.com.br/rest/v3/"

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        if api_key and api_secret:
            self.session.headers.update({
                "X-FB-ACCESS-KEY": api_key,
                # Note: Real auth requires signature generation. 
                # For public data (paper trading price feed), auth might not be needed.
                # Use secrets for signature in real impl.
            })

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, max_retries: int = 3) -> Dict[str, Any]:
        url = urljoin(self.BASE_URL, endpoint)
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling {endpoint}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        return {}

    def get_ticker(self, market_symbol: str = "btcbrl") -> Dict[str, Any]:
        """
        Fetch current ticker information.
        PRIMARY: Binance (Stable, High Limit)
        SECONDARY: Mercado Bitcoin (Stable, Brazilian Reference)
        """
        # 1. Try Binance (Reference Global / BTCBRL)
        try:
            symbol_upper = market_symbol.upper() # btcbrl -> BTCBRL
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_upper}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "last": float(data['price']),
                    "market_symbol": market_symbol,
                    "simulated": False,
                    "source": "Binance"
                }
        except Exception as e:
            logger.warning(f"Binance API failed: {e}")

        # 2. Try Mercado Bitcoin (Fallback)
        return self._get_fallback_ticker(market_symbol)

    def _get_fallback_ticker(self, market_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fallback to Mercado Bitcoin public API for BTC/BRL price.
        High limit, no auth required for public data.
        """
        try:
            # Pair symbol mapping (btcbrl -> BTC)
            coin = market_symbol[:3].upper()
            url = f"https://www.mercadobitcoin.net/api/{coin}/ticker/"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'ticker' in data and 'last' in data['ticker']:
                return {
                    "last": float(data['ticker']['last']),
                    "market_symbol": market_symbol,
                    "simulated": False,
                    "source": "MercadoBitcoin"
                }
        except Exception as fe:
            logger.error(f"Fallback Source (Mercado Bitcoin) Failed: {fe}")
        
        return None

    def get_candles(self, market_symbol: str = "btcbrl", interval: str = "1h", limit: int = 100) -> list:
        """
        Fetch OHLCV candles.
        Foxbit V3 usually provides this via /market/candles or similar.
        Adjusting to common standard or specific V3 endpoint.
        """
        # Example endpoint mapping
        params = {
            "market_symbol": market_symbol,
            "interval": interval,
            "limit": limit
        }
        return self._request("GET", "markets/candles", params=params)

    def get_orderbook(self, market_symbol: str = "btcbrl", depth: int = 20) -> Dict[str, Any]:
        return self._request("GET", "markets/orderbook", params={"market_symbol": market_symbol, "depth": depth})
