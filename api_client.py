import hmac
import hashlib
from datetime import datetime, timedelta
from data_loader import DataLoader
import time
import requests
from urllib.parse import urlencode
import json
import pandas as pd
from config import ROOSTOO_API_KEY, ROOSTOO_SECRET, ROOSTOO_BASE_URL, ENDPOINTS

class RoostooAPIClient:
    def __init__(self):
        self.api_key = ROOSTOO_API_KEY
        self.secret_key = ROOSTOO_SECRET
        self.base_url = ROOSTOO_BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": ROOSTOO_API_KEY,
            "X-API-SECRET": ROOSTOO_SECRET
        }
        
        # validate config
        if not self.api_key or not self.secret_key:
            raise ValueError("API key not configured, please check .env file")

    def _interval_to_minutes(self, interval: str) -> int:
        interval = interval.strip().lower()
        if interval.endswith('m'):
            return int(interval[:-1])
        if interval.endswith('h'):
            return int(interval[:-1]) * 60
        raise ValueError(f"Unsupported interval: {interval}")

    def get_ohlcv(self, symbol='BTC/USD', interval='15m', limit=100):
        import pandas as pd
        """
        Try Roostoo first (/v3/ohlcv or /ohlcv). If not available, fall back to Horus (DataLoader) to always return an OHLCV DataFrame.
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }

        roostoo_paths = ["/v3/ohlcv", "/ohlcv"]
        for path in roostoo_paths:
            try:
                url = f"{self.base_url}{path}"
                r = requests.get(url, params=params, headers=self.headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    rows = data.get('data', data)
                    if rows and isinstance(rows, list):
                        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        ts = int(df['timestamp'].iloc[-1])
                        if ts > 10**12:  # ms
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                        else:            # s
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                        df.set_index('timestamp', inplace=True)
                        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                        return df
            except Exception:
                pass

        asset = symbol.split('/')[0] if '/' in symbol else symbol
        bar_min = self._interval_to_minutes(interval)
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(minutes=bar_min * (limit + 5))
        loader = DataLoader()
        df = loader.get_historical_data(
            asset=asset,
            interval=interval,
            start=int(start_dt.timestamp()),
            end=int(end_dt.timestamp())
        )
        return df
    
    def _get_timestamp(self):
        """Get 13-digit millisecond timestamp"""
        return str(int(time.time() * 1000))
    
    def _generate_signature(self, params):
        """Generate HMAC SHA256 signature"""
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _request(self, method, endpoint, params=None, signed=False):
        """Send API request"""
        url = self.base_url + endpoint
        
        if params is None:
            params = {}
            
        if signed:
            params['timestamp'] = self._get_timestamp()
            signature = self._generate_signature(params)
            
            headers = {
                'RST-API-KEY': self.api_key,
                'MSG-SIGNATURE': signature,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        else:
            headers = {}
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers)
            else:
                response = requests.post(url, data=params, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'Success': False,
                    'ErrMsg': f"HTTP error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'Success': False,
                'ErrMsg': f"Request exception: {str(e)}"
            }
    
    # public API methods
    
    def get_server_time(self):
        """Get server time"""
        return self._request('GET', ENDPOINTS['server_time'])
    
    def get_exchange_info(self):
        """Get exchange info"""
        return self._request('GET', ENDPOINTS['exchange_info'])
    
    def get_ticker(self, pair=None):
        """Get ticker data"""
        params = {}
        if pair:
            params['pair'] = pair
        return self._request('GET', ENDPOINTS['ticker'], params, signed=True)
    
    def get_balance(self):
        """Get account balance"""
        return self._request('GET', ENDPOINTS['balance'], signed=True)
    
    def get_pending_count(self):
        """Get pending order count"""
        return self._request('GET', ENDPOINTS['pending_count'], signed=True)
    
    def place_order(self, pair, side, order_type, quantity, price=None):
        """Place order"""
        params = {
            'pair': pair,
            'side': side,            # 'BUY' or 'SELL'
            'type': order_type,      # 'LIMIT' or 'MARKET'
            'quantity': str(quantity)
        }
        
        if order_type == 'LIMIT' and price is not None:
            params['price'] = str(price)
        
        return self._request('POST', ENDPOINTS['place_order'], params, signed=True)
    
    def query_order(self, order_id=None, pair=None, pending_only=False, limit=100, offset=0):
        """Query order"""
        params = {}
        
        if order_id:
            params['order_id'] = str(order_id)
        elif pair:
            params['pair'] = pair
            
        if pending_only:
            params['pending_only'] = 'TRUE'
            
        params['limit'] = str(limit)
        params['offset'] = str(offset)
        
        return self._request('POST', ENDPOINTS['query_order'], params, signed=True)
    
    def cancel_order(self, order_id=None, pair=None):
        """Cancel order"""
        params = {}
        
        if order_id:
            params['order_id'] = str(order_id)
        elif pair:
            params['pair'] = pair
            
        return self._request('POST', ENDPOINTS['cancel_order'], params, signed=True)

# global client instance
client = RoostooAPIClient()
