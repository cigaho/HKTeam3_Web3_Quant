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
        
        return df