import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class BacktestStrategy(ABC):
    """回测策略基类"""
    
    def __init__(self, name):
        self.name = name
    
    @abstractmethod
    def generate_signals(self, data):
        """生成交易信号"""
        pass

class MovingAverageStrategy(BacktestStrategy):
    """移动平均线策略"""
    
    def __init__(self, short_window=5, long_window=20):
        super().__init__(f"MA策略({short_window}/{long_window})")
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signals(self, data):
        df = data.copy()
        df['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_window).mean()
        
        df['signal'] = 0
        df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1    # 金叉买入
        df.loc[df['short_ma'] < df['long_ma'], 'signal'] = -1   # 死叉卖出
        
        return df

class RSIStrategy(BacktestStrategy):
    """RSI策略"""
    
    def __init__(self, window=14, oversold=30, overbought=70):
        super().__init__(f"RSI策略({window})")
        self.window = window
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_rsi(self, prices):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.window).mean()
        avg_loss = loss.rolling(window=self.window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, data):
        df = data.copy()
        df['rsi'] = self.calculate_rsi(df['close'])
        
        df['signal'] = 0
        df.loc[df['rsi'] < self.oversold, 'signal'] = 1      # 超卖买入
        df.loc[df['rsi'] > self.overbought, 'signal'] = -1   # 超买卖出
        
        return df

class MeanReversionStrategy(BacktestStrategy):
    """均值回归策略"""
    
    def __init__(self, window=20, z_score_threshold=2.0):
        super().__init__(f"均值回归策略({window})")
        self.window = window
        self.z_score_threshold = z_score_threshold
    
    def generate_signals(self, data):
        df = data.copy()
        df['mean'] = df['close'].rolling(window=self.window).mean()
        df['std'] = df['close'].rolling(window=self.window).std()
        df['z_score'] = (df['close'] - df['mean']) / df['std']
        
        df['signal'] = 0
        df.loc[df['z_score'] < -self.z_score_threshold, 'signal'] = 1    # 低估买入
        df.loc[df['z_score'] > self.z_score_threshold, 'signal'] = -1     # 高估卖出

class MultiFactorStrategy(BacktestStrategy):
    """多因子评分策略（增强版：短期高频响应）"""

    def __init__(self):
        super().__init__("多因子策略")
        # 各因子权重（强化动量与波动）
        self.weights = {
            "trend": 0.20,
            "momentum": 0.35,
            "volatility": 0.20,
            "volume": 0.15,
            "structure": 0.05,
            "candlestick": 0.05
        }

    def calculate_indicators(self, df):
        df = df.copy()

        # ===== 趋势系统 (短期均线) =====
        df['MA_5'] = df['close'].rolling(5).mean()
        df['MA_10'] = df['close'].rolling(10).mean()
        df['MA_20'] = df['close'].rolling(20).mean()

        # ===== 动量系统 (加快MACD & RSI) =====
        df['EMA6'] = df['close'].ewm(span=6).mean()
        df['EMA13'] = df['close'].ewm(span=13).mean()
        df['MACD'] = df['EMA6'] - df['EMA13']
        df['Signal'] = df['MACD'].ewm(span=4).mean()
        df['Hist'] = (df['MACD'] - df['Signal']) * 2

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(7).mean()
        avg_loss = loss.rolling(7).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # ===== 波动率系统 (10日布林带) =====
        df['mid'] = df['close'].rolling(10).mean()
        df['std'] = df['close'].rolling(10).std()
        df['upper'] = df['mid'] + 2 * df['std']
        df['lower'] = df['mid'] - 2 * df['std']
        df['Boll_pos'] = (df['close'] - df['lower']) / (df['upper'] - df['lower'])

        # ===== ATR (平均真实波幅) =====
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()

        # ===== 成交量系统 =====
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma20']

        # ===== 市场结构 =====
        df['resistance'] = df['high'].rolling(20).max()
        df['support'] = df['low'].rolling(20).min()

        # ===== K线形态系统 =====
        df['body_ratio'] = (df['close'] - df['open']).abs() / (df['high'] - df['low'])
        return df

    def generate_signals(self, data):
        df = self.calculate_indicators(data)

        # 初始化得分
        df['trend_score'] = 0
        df['momentum_score'] = 0
        df['volatility_score'] = 0
        df['volume_score'] = 0
        df['structure_score'] = 0
        df['candlestick_score'] = 0

        # === 趋势判断 ===
        df.loc[(df['MA_5'] > df['MA_10']) & (df['MA_10'] > df['MA_20']), 'trend_score'] = 2
        df.loc[(df['MA_5'] < df['MA_10']) & (df['MA_10'] < df['MA_20']), 'trend_score'] = -2

        # === 动量判断 ===
        df.loc[df['MACD'] > df['Signal'], 'momentum_score'] += 1
        df.loc[df['RSI'] < 30, 'momentum_score'] += 1
        df.loc[df['RSI'] > 70, 'momentum_score'] -= 1

        # === 波动率判断 ===
        df.loc[df['Boll_pos'] < 0.3, 'volatility_score'] += 1
        df.loc[df['Boll_pos'] > 0.7, 'volatility_score'] -= 1

        # === 成交量判断 ===
        df.loc[df['vol_ratio'] > 1.1, 'volume_score'] = 1
        df.loc[df['vol_ratio'] < 0.9, 'volume_score'] = -1

        # === 市场结构判断 ===
        df.loc[df['close'] > df['resistance'], 'structure_score'] = 1
        df.loc[df['close'] < df['support'], 'structure_score'] = -1

        # === K线形态判断 ===
        df.loc[df['body_ratio'] > 0.6, 'candlestick_score'] = np.sign(df['close'] - df['open'])

        # === 综合总分 ===
        df['total_score'] = (
            df['trend_score'] * self.weights['trend'] +
            df['momentum_score'] * self.weights['momentum'] +
            df['volatility_score'] * self.weights['volatility'] +
            df['volume_score'] * self.weights['volume'] +
            df['structure_score'] * self.weights['structure'] +
            df['candlestick_score'] * self.weights['candlestick']
        )

        # 填补缺失值，避免初期NaN
        df = df.fillna(0)

        # === 生成交易信号（阈值调低以增加频率） ===
        df['signal'] = 0
        df.loc[df['total_score'] > 0.3, 'signal'] = 1
        df.loc[df['total_score'] < -0.3, 'signal'] = -1

        return df
