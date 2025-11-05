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
            raise ValueError("API密钥未配置，请检查.env文件")
    
    def _get_timestamp(self):
        """获取13位毫秒时间戳"""
        return str(int(time.time() * 1000))
    
    def _generate_signature(self, params):
        """生成HMAC SHA256签名"""
        # 对参数按键排序
        sorted_params = sorted(params.items())
        # 构建查询字符串
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # 生成签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _request(self, method, endpoint, params=None, signed=False):
        """发送API请求"""
        url = self.base_url + endpoint
        
        # 准备参数
        if params is None:
            params = {}
            
        if signed:
            # 添加时间戳
            params['timestamp'] = self._get_timestamp()
            # 生成签名
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
            
            # 检查响应
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'Success': False,
                    'ErrMsg': f"HTTP错误: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'Success': False,
                'ErrMsg': f"请求异常: {str(e)}"
            }
    
    # 公开API方法
    
    def get_server_time(self):
        """获取服务器时间"""
        return self._request('GET', ENDPOINTS['server_time'])
    
    def get_exchange_info(self):
        """获取交易所信息"""
        return self._request('GET', ENDPOINTS['exchange_info'])
    
    def get_ticker(self, pair=None):
        """获取行情数据"""
        params = {}
        if pair:
            params['pair'] = pair
        return self._request('GET', ENDPOINTS['ticker'], params, signed=True)
    
    def get_balance(self):
        """获取账户余额"""
        return self._request('GET', ENDPOINTS['balance'], signed=True)
    
    def get_pending_count(self):
        """获取挂单数量"""
        return self._request('GET', ENDPOINTS['pending_count'], signed=True)
    
    def place_order(self, pair, side, order_type, quantity, price=None):
        """下单"""
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
        """查询订单"""
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
        """取消订单"""
        params = {}
        
        if order_id:
            params['order_id'] = str(order_id)
        elif pair:
            params['pair'] = pair
            
        return self._request('POST', ENDPOINTS['cancel_order'], params, signed=True)

# 创建全局客户端实例
client = RoostooAPIClient()
