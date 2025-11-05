import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta
import json

class DataLoader:
    def __init__(self, api_key=None):
        """
        初始化数据加载器
        只使用Horus API，失败直接报错
        """
        self.base_url = "https://api-horus.com"  # Horus API基础URL
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv('HORUS_API_KEY')
        if not self.api_key:
            raise ValueError("HORUS_API_KEY未设置，请在.env文件中配置或作为参数传入")
        
        print(f"🔑 使用API Key: {self.api_key[:10]}...")
    
    def get_historical_data(self, asset='BTC', interval='1d', start=None, end=None):
        """
        从Horus API获取历史价格数据
        
        参数:
        asset: 资产代码，如 'BTC', 'ETH' 等
        interval: 时间间隔 '15m', '1h', '1d'
        start: 开始时间戳（秒）
        end: 结束时间戳（秒）
        
        返回: DataFrame with timestamp index and OHLC data
        
        API失败直接抛出异常，不尝试任何回退方案
        """
        print(f"📊 从Horus API获取 {asset} 历史数据...")
        
        # 设置默认时间范围：8月1日到11月1日（过去3个月）
        if start is None:
            start_date = datetime(2024, 8, 1)  # 8月1日
            start = int(start_date.timestamp())
        
        if end is None:
            end_date = datetime(2024, 11, 1)  # 11月1日
            end = int(end_date.timestamp())
        
        print(f"📅 时间范围: {datetime.fromtimestamp(start)} 到 {datetime.fromtimestamp(end)}")
        print(f"⏰ 时间间隔: {interval}")
        print(f"💰 资产: {asset}")
        
        # 构建API请求 - 根据图片中的API格式
        endpoint = f"{self.base_url}/market/price"
        
        params = {
            'asset': asset,
            'interval': interval,
            'start': start,
            'end': end
        }
        
        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'QuantTradingBot/1.0'
        }
        
        print(f"🌐 请求URL: {endpoint}")
        print(f"📋 请求参数: {params}")
        
        try:
            # 发送API请求
            print("🔄 发送API请求...")
            response = requests.get(
                endpoint, 
                params=params, 
                headers=headers, 
                timeout=30
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败: HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise Exception(error_msg)
            
            print("✅ API请求成功")
            
            # 解析JSON响应
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise Exception(f"JSON解析失败: {e} - 响应内容: {response.text[:200]}")
            
            # 解析API响应数据
            df = self._parse_api_response(data, asset)
            
            print(f"✅ 成功解析 {len(df)} 条{asset}历史数据")
            print(f"📈 价格范围: ${df['close'].min():.0f} - ${df['close'].max():.0f}")
            print(f"📊 数据时间范围: {df.index[0]} 到 {df.index[-1]}")
            
            return df
            
        except requests.exceptions.Timeout:
            raise Exception("API请求超时（30秒）")
        except requests.exceptions.ConnectionError:
            raise Exception("网络连接错误，请检查网络连接")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求异常: {e}")
        except Exception as e:
            raise Exception(f"数据获取失败: {e}")
    
    def _parse_api_response(self, api_data, asset):
        """
        解析Horus API返回的数据
        严格按照图片中的格式: [{"timestamp": ..., "price": ...}]
        """
        if not api_data:
            raise ValueError("API返回空数据")
        
        if not isinstance(api_data, list):
            raise ValueError(f"API返回格式错误，期望列表，得到: {type(api_data)}")
        
        if len(api_data) == 0:
            raise ValueError("API返回空数据列表")
        
        records = []
        for i, item in enumerate(api_data):
            # 验证数据格式
            if not isinstance(item, dict):
                raise ValueError(f"第{i}个数据项格式错误，期望字典，得到: {type(item)}")
            
            # 检查必要字段
            if 'timestamp' not in item:
                raise ValueError(f"第{i}个数据项缺少'timestamp'字段: {item}")
            
            if 'price' not in item:
                raise ValueError(f"第{i}个数据项缺少'price'字段: {item}")
            
            # 转换数据
            try:
                timestamp = datetime.fromtimestamp(item['timestamp'])
                price = float(item['price'])
            except (ValueError, TypeError) as e:
                raise ValueError(f"第{i}个数据项格式转换错误: {e} - 数据项: {item}")
            
            # 验证价格合理性
            if price <= 0:
                raise ValueError(f"第{i}个数据项价格无效: {price}")
            
            records.append({
                'timestamp': timestamp,
                'price': price
            })
        
        # 创建DataFrame
        df = pd.DataFrame(records)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)  # 按时间排序
        
        # 从价格数据生成OHLC数据
        df = self._generate_ohlc_from_price(df, asset)
        
        return df
    
    def _generate_ohlc_from_price(self, price_df, asset):
        """
        从价格数据生成OHLC数据
        由于API只返回价格，我们需要基于价格生成OHLC
        """
        df = price_df.copy()
        
        # 重命名price列为close
        df.rename(columns={'price': 'close'}, inplace=True)
        
        # 基于收盘价生成合理的OHLC数据
        # 开盘价 = 前一个时间点的收盘价
        df['open'] = df['close'].shift(1)
        df['open'].iloc[0] = df['close'].iloc[0]  # 第一个数据点
        
        # 根据资产类型设置合理的波动率
        volatility_map = {
            'BTC': 0.02, 'ETH': 0.03, 'SOL': 0.05, 'BNB': 0.025,
            'XRP': 0.04, 'ADA': 0.045, 'DOGE': 0.08, 'DOT': 0.035,
            'LINK': 0.04, 'LTC': 0.03, 'BCH': 0.04, 'AVAX': 0.05
        }
        volatility = volatility_map.get(asset, 0.03)
        
        # 生成高低价（基于收盘价的合理波动）
        np.random.seed(42)  # 固定随机种子以便结果可复现
        
        # 高价 = 收盘价 + 随机波动
        high_volatility = np.random.uniform(0, volatility, len(df))
        df['high'] = df['close'] * (1 + high_volatility)
        
        # 低价 = 收盘价 - 随机波动
        low_volatility = np.random.uniform(0, volatility, len(df))
        df['low'] = df['close'] * (1 - low_volatility)
        
        # 确保高低价的合理性
        df['high'] = np.maximum(df['high'], df[['open', 'close']].max(axis=1))
        df['low'] = np.minimum(df['low'], df[['open', 'close']].min(axis=1))
        
        # 添加成交量（基于价格和波动率生成）
        base_volume = {
            'BTC': 1e9, 'ETH': 5e8, 'SOL': 2e8, 'BNB': 1e8,
            'XRP': 3e8, 'ADA': 2e8, 'DOGE': 1e8, 'DOT': 5e7,
            'LINK': 5e7, 'LTC': 8e7, 'BCH': 6e7, 'AVAX': 4e7
        }
        base_vol = base_volume.get(asset, 1e8)
        
        # 成交量与价格波动相关
        price_change = df['close'].pct_change().abs().fillna(0)
        volume_multiplier = 1 + price_change * 10  # 波动大时成交量大
        
        df['volume'] = base_vol * volume_multiplier * np.random.uniform(0.8, 1.2, len(df))
        
        # 重新排列列顺序（标准的OHLCV顺序）
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        return df
    
    def add_technical_indicators(self, data):
        """
        添加技术指标到数据中
        """
        df = data.copy()
        
        print("📊 计算技术指标...")
        
        # 移动平均线
        df['ma_7'] = df['close'].rolling(window=7, min_periods=1).mean()
        df['ma_25'] = df['close'].rolling(window=25, min_periods=1).mean()
        df['ma_99'] = df['close'].rolling(window=99, min_periods=1).mean()
        
        # RSI (14周期)
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20, min_periods=1).mean()
        bb_std = df['close'].rolling(window=20, min_periods=1).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # 价格变化率和波动率
        df['price_change'] = df['close'].pct_change()
        df['volatility_20'] = df['price_change'].rolling(window=20, min_periods=1).std()
        
        print("✅ 技术指标计算完成")
        return df
    
    def _calculate_rsi(self, prices, window=14):
        """计算RSI指标"""
        delta = prices.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window, min_periods=1).mean()
        avg_loss = loss.rolling(window=window, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def validate_data(self, df):
        """
        验证数据质量
        """
        print("🔍 验证数据质量...")
        
        if len(df) == 0:
            raise ValueError("数据为空")
        
        # 检查缺失值
        missing_values = df.isnull().sum().sum()
        if missing_values > 0:
            print(f"⚠️  发现 {missing_values} 个缺失值")
        
        # 检查价格合理性
        if (df['close'] <= 0).any():
            raise ValueError("发现无效的价格数据（<=0）")
        
        # 检查时间连续性
        time_diff = df.index.to_series().diff().dropna()
        if len(time_diff) > 0:
            avg_gap = time_diff.mean()
            print(f"⏱️  平均时间间隔: {avg_gap}")
        
        print("✅ 数据验证通过")
        return True

# 简单的测试函数
def test_data_loader():
    """测试数据加载器"""
    try:
        loader = DataLoader()
        
        print("🧪 开始测试数据加载器...")
        
        # 获取比特币数据
        data = loader.get_historical_data(
            asset='BTC',
            interval='1d'
        )
        
        # 验证数据
        loader.validate_data(data)
        
        # 添加技术指标
        data_with_indicators = loader.add_technical_indicators(data)
        
        print(f"🎉 测试成功!")
        print(f"📊 最终数据形状: {data_with_indicators.shape}")
        print(f"📈 列名: {list(data_with_indicators.columns)}")
        
        return data_with_indicators
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise

if __name__ == "__main__":
    test_data_loader()