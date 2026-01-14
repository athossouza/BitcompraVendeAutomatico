
import logging
import requests
import time
import hmac
import hashlib
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlencode

logger = logging.getLogger(__name__)

class BinanceClient:
    """
    Client for interacting with the Binance API (Spot).
    Handles authentication (HMAC SHA256) and order execution.
    """
    BASE_URL = "https://api.binance.com/api/v3/"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key
        })

    def _sign_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds 'timestamp' and 'signature' to the parameters.
        """
        if params is None:
            params = {}
        
        # 1. Add Timestamp
        params['timestamp'] = int(time.time() * 1000)
        
        # 2. Generate Signature
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        return params

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False, max_retries: int = 3) -> Dict[str, Any]:
        url = urljoin(self.BASE_URL, endpoint)
        retry_delay = 1
        
        if signed:
            params = self._sign_request(params or {})

        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, params=params, timeout=10)
                
                # Handle Binance Errors
                if response.status_code >= 400:
                    logger.error(f"Binance API Error ({response.status_code}): {response.text}")
                    response.raise_for_status()
                
                return response.json()
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling {endpoint}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2
        return {}

    def get_account_info(self) -> Dict[str, Any]:
        """
        Fetch account balances and status.
        Weight: 10
        """
        return self._request("GET", "account", signed=True)

    def get_asset_balance(self, asset: str) -> float:
        """
        Helper to get free balance of a specific asset.
        """
        info = self.get_account_info()
        balances = info.get("balances", [])
        for b in balances:
            if b["asset"] == asset.upper():
                return float(b["free"])
        return 0.0

    def get_symbol_price(self, symbol: str = "BTCBRL") -> float:
        """
        Get current price.
        """
        data = self._request("GET", "ticker/price", params={"symbol": symbol.upper()})
        return float(data.get("price", 0.0))

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get exchange info for a specific symbol (stepSize, minNotional, etc).
        """
        data = self._request("GET", "exchangeInfo", params={"symbol": symbol.upper()})
        symbols = data.get("symbols", [])
        if symbols:
            return symbols[0]
        return {}

    def get_my_trades(self, symbol: str, limit: int = 50) -> list:
        """
        Get trade history (myTrades).
        """
        params = {
            "symbol": symbol.upper(),
            "limit": limit
        }
        return self._request("GET", "myTrades", params=params, signed=True)

    def create_order(self, symbol: str, side: str, quantity: float, type: str = "MARKET") -> Dict[str, Any]:
        """
        Place a new order.
        side: BUY or SELL
        type: MARKET (default)
        """
        # Format quantity to avoid scientific notation (e.g. 5e-05)
        qty_str = "{:.8f}".format(quantity).rstrip('0').rstrip('.')
        
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": type.upper(),
            "quantity": qty_str
        }
        
        logger.info(f"🚀 BINANCE EXECUTION: Placing {side} {qty_str} {symbol} @ {type}")
        return self._request("POST", "order", params=params, signed=True)
