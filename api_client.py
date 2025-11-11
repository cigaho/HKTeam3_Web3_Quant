import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode
import json
from config import ROOSTOO_API_KEY, ROOSTOO_SECRET, ROOSTOO_BASE_URL, ENDPOINTS

class RoostooAPIClient:
    def __init__(self):
        self.api_key = ROOSTOO_API_KEY
        self.secret_key = ROOSTOO_SECRET
        self.base_url = ROOSTOO_BASE_URL
        
        # 验证配置
        if not self.api_key or not self.secret_key:
            raise ValueError("API key is not set，please check .env file")
    
    def _get_timestamp(self):
        return str(int(time.time() * 1000))
    
    def _generate_signature(self, params):
        """generate HMAC SHA256 signature"""
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
            # add timestamp
            params['timestamp'] = self._get_timestamp()
            # generate signature
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
            else:  # POST
                response = requests.post(url, data=params, headers=headers)
            
            # check response
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
                'ErrMsg': f"Request error: {str(e)}"
            }
    
   
    
    def get_server_time(self):
        return self._request('GET', ENDPOINTS['server_time'])
    
    def get_exchange_info(self):
        return self._request('GET', ENDPOINTS['exchange_info'])
    
    def get_ticker(self, pair=None):
        params = {}
        if pair:
            params['pair'] = pair
        return self._request('GET', ENDPOINTS['ticker'], params, signed=True)
    
    def get_balance(self):
        return self._request('GET', ENDPOINTS['balance'], signed=True)
    
    def get_pending_count(self):
        return self._request('GET', ENDPOINTS['pending_count'], signed=True)
    
    def place_order(self, pair, side, order_type, quantity, price=None):
        params = {
            'pair': pair,
            'side': side,  # 'BUY' or 'SELL'
            'type': order_type,  # 'LIMIT' or 'MARKET'
            'quantity': str(quantity)
        }
        
        if order_type == 'LIMIT' and price is not None:
            params['price'] = str(price)
        
        return self._request('POST', ENDPOINTS['place_order'], params, signed=True)
    
    def query_order(self, order_id=None, pair=None, pending_only=False, limit=100, offset=0):
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
        params = {}
        
        if order_id:
            params['order_id'] = str(order_id)
        elif pair:
            params['pair'] = pair
            
        return self._request('POST', ENDPOINTS['cancel_order'], params, signed=True)

# create client instance
client = RoostooAPIClient()
