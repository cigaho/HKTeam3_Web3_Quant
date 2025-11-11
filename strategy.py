import time

class QuickTestStrategy:
    def __init__(self):
        self.name = "快速测试策略"
        self.trade_count = 0
        self.last_trade_time = 0

    def get_ohlcv(self, pair='BTC/USD', interval='15m', limit=100):
        """获取历史K线数据"""
        url = f"{self.base_url}/ohlcv"
        params = {
            "symbol": pair,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(url, params=params, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取K线数据失败: {response.text}")
            return None

    def convert_to_dataframe(self, ohlcv_json):
        """将返回的OHLCV数据转成DataFrame"""
        candles = ohlcv_json.get("Data", {}).get("BTC/USD", [])
        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)
        return df
        
    def generate_signal(self, market_data):
        """
        快速测试策略：每分钟交替买卖
        """
        current_time = time.time()
        
        # 每分钟执行一次交易（避免频率限制）
        if current_time - self.last_trade_time < 60:  # 60秒间隔
            return 'HOLD'
        
        self.trade_count += 1
        self.last_trade_time = current_time
        
        print(f"🎯 测试交易 #{self.trade_count}")
        
        # 交替执行买卖：奇数次数买，偶数次数卖
        if self.trade_count % 2 == 1:
            print("➡️ 生成买入信号")
            return 'BUY'
        else:
            print("⬅️ 生成卖出信号")
            return 'SELL'

# 保留原来的SimpleStrategy类作为备用
class SimpleStrategy:
    def __init__(self):
        self.name = "简单移动平均策略"
        self.last_price = None
    
    def generate_signal(self, market_data):
        """
        生成交易信号
        返回: 'BUY', 'SELL', 或 'HOLD'
        """
        if not market_data.get('Success'):
            return 'HOLD'
            
        # 提取行情数据
        ticker = market_data['Data']['BTC/USD']
        current_price = ticker['LastPrice']
        price_change = ticker['Change']  # 24小时价格变化百分比
        
        print(f"价格: ${current_price}, 24小时变化: {price_change*100:.2f}%")
        
        # 简单的策略逻辑
        if price_change < -0.02:  # 如果24小时下跌超过2%
            return 'BUY'
        elif price_change > 0.03:  # 如果24小时上涨超过3%
            return 'SELL'
        else:
            return 'HOLD'

class MultiAssetStrategy:
    """同时监控多个资产的策略"""
    
    def __init__(self, assets=None):
        self.name = "多资产监控策略"
        self.assets = assets or ['BTC/USD', 'ETH/USD', 'SOL/USD']
        self.asset_strategies = {}
        
        # 为每个资产创建独立的策略
        for asset in self.assets:
            self.asset_strategies[asset] = SimpleStrategy(asset)
    
    def generate_signal(self, market_data):
        """
        为每个资产生成独立的信号
        返回: 字典 {asset: signal}
        """
        signals = {}
        
        for asset, strategy in self.asset_strategies.items():
            signals[asset] = strategy.generate_signal(market_data)
        
        return signals
