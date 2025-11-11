import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class BacktestStrategy(ABC):
    
    def __init__(self, name):
        self.name = name
    
    @abstractmethod
    def generate_signals(self, data):
        pass

class MovingAverageStrategy(BacktestStrategy):
    
    def __init__(self, short_window=5, long_window=20):
        super().__init__(f"MA strategy ({short_window}/{long_window})")
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signals(self, data):
        df = data.copy()
        df['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_window).mean()
        
        df['signal'] = 0
        df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1    # long
        df.loc[df['short_ma'] < df['long_ma'], 'signal'] = -1   # short
        
        return df

class RSIStrategy(BacktestStrategy):
    
    def __init__(self, window=14, oversold=30, overbought=70):
        super().__init__(f"RSI strategy({window})")
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
        df.loc[df['rsi'] < self.oversold, 'signal'] = 1      # buy signal
        df.loc[df['rsi'] > self.overbought, 'signal'] = -1   # sell signal
        
        return df

class MeanReversionStrategy(BacktestStrategy):
    
    def __init__(self, window=20, z_score_threshold=2.0):
        super().__init__(f"Mean Reversion Strategy ({window})")
        self.window = window
        self.z_score_threshold = z_score_threshold
    
    def generate_signals(self, data):
        df = data.copy()
        df['mean'] = df['close'].rolling(window=self.window).mean()
        df['std'] = df['close'].rolling(window=self.window).std()
        df['z_score'] = (df['close'] - df['mean']) / df['std']
        
        df['signal'] = 0
        df.loc[df['z_score'] < -self.z_score_threshold, 'signal'] = 1    # buy when undervalued
        df.loc[df['z_score'] > self.z_score_threshold, 'signal'] = -1     # sell when overvalued

class MultiFactorStrategy(BacktestStrategy):

    def __init__(self):
        super().__init__("Multi factor")
        # weights for different models
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

        # ===== trend system =====
        df['MA_5'] = df['close'].rolling(5).mean()
        df['MA_10'] = df['close'].rolling(10).mean()
        df['MA_20'] = df['close'].rolling(20).mean()

        # ===== momentum system (speed up MACD & RSI) =====
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

        # ===== fluctuation system (10 days boll) =====
        df['mid'] = df['close'].rolling(10).mean()
        df['std'] = df['close'].rolling(10).std()
        df['upper'] = df['mid'] + 2 * df['std']
        df['lower'] = df['mid'] - 2 * df['std']
        df['Boll_pos'] = (df['close'] - df['lower']) / (df['upper'] - df['lower'])

        # ===== ATR (average true fluctuation) =====
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()

        # ===== trading volume system =====
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma20']

        # ===== market structure =====
        df['resistance'] = df['high'].rolling(20).max()
        df['support'] = df['low'].rolling(20).min()

        # ===== K-line pattern =====
        df['body_ratio'] = (df['close'] - df['open']).abs() / (df['high'] - df['low'])
        return df

    def generate_signals(self, data):
        df = self.calculate_indicators(data)

        # initialized score
        df['trend_score'] = 0
        df['momentum_score'] = 0
        df['volatility_score'] = 0
        df['volume_score'] = 0
        df['structure_score'] = 0
        df['candlestick_score'] = 0

        # === trend analysis ===
        df.loc[(df['MA_5'] > df['MA_10']) & (df['MA_10'] > df['MA_20']), 'trend_score'] = 2
        df.loc[(df['MA_5'] < df['MA_10']) & (df['MA_10'] < df['MA_20']), 'trend_score'] = -2

        # === momentum analysys ===
        df.loc[df['MACD'] > df['Signal'], 'momentum_score'] += 1
        df.loc[df['RSI'] < 30, 'momentum_score'] += 1
        df.loc[df['RSI'] > 70, 'momentum_score'] -= 1

        # === volatility analysis ===
        df.loc[df['Boll_pos'] < 0.3, 'volatility_score'] += 1
        df.loc[df['Boll_pos'] > 0.7, 'volatility_score'] -= 1

        # === trading volume analysis ===
        df.loc[df['vol_ratio'] > 1.1, 'volume_score'] = 1
        df.loc[df['vol_ratio'] < 0.9, 'volume_score'] = -1

        # === market structure analysis ===
        df.loc[df['close'] > df['resistance'], 'structure_score'] = 1
        df.loc[df['close'] < df['support'], 'structure_score'] = -1

        # === K-line pattern analysis ===
        df.loc[df['body_ratio'] > 0.6, 'candlestick_score'] = np.sign(df['close'] - df['open'])

        # === overall score ===
        df['total_score'] = (
            df['trend_score'] * self.weights['trend'] +
            df['momentum_score'] * self.weights['momentum'] +
            df['volatility_score'] * self.weights['volatility'] +
            df['volume_score'] * self.weights['volume'] +
            df['structure_score'] * self.weights['structure'] +
            df['candlestick_score'] * self.weights['candlestick']
        )

        # fill missing data
        df = df.fillna(0)

        # === generate trading signal ===
        df['signal'] = 0
        df.loc[df['total_score'] > 0.3, 'signal'] = 1
        df.loc[df['total_score'] < -0.3, 'signal'] = -1

        return df


class OpeningRangeBreakoutStrategy(BacktestStrategy):

    def __init__(self, lookback_minutes=90, atr_period=10, atr_multiplier=0.03, cooldown_hours=2):
        super().__init__("Opening range breakout strategy")
        self.lookback_minutes = lookback_minutes
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.cooldown_hours = cooldown_hours

    def generate_signals(self, data):
        df = data.copy()
        df['date'] = df.index.date
        df['hour'] = df.index.hour

        df['upper'] = np.nan
        df['lower'] = np.nan

        for date in df['date'].unique():
            open_period = df[(df['date'] == date) & (df['hour'] == 0)].head(int(self.lookback_minutes / 15))
            if not open_period.empty:
                df.loc[df['date'] == date, 'upper'] = open_period['high'].max()
                df.loc[df['date'] == date, 'lower'] = open_period['low'].min()

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(self.atr_period).mean()

        df['signal'] = 0
        df.loc[df['close'] > (df['upper'] + self.atr_multiplier * df['ATR']), 'signal'] = 1
        df.loc[df['close'] < (df['lower'] - self.atr_multiplier * df['ATR']), 'signal'] = -1

        df = df.fillna(0)
        return df
