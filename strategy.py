import time
import numpy as np
import pandas as pd


class OpeningRangeBreakoutStrategy:
    """Opening Range Breakout, works with arbitrary minute bars (e.g. 2m, 15m)."""
    def __init__(self, lookback_minutes=90, atr_period=10, atr_multiplier=0.03, cooldown_hours=2):
        self.name = "Opening Range Breakout Strategy (adaptive)"
        self.lookback_minutes = lookback_minutes
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.cooldown_hours = cooldown_hours

    def _infer_bar_minutes(self, index) -> int:
        # use median gap to infer bar size in minutes
        diffs = pd.Series(index).diff().dropna()
        seconds = diffs.dt.total_seconds().median() if hasattr(diffs, 'dt') else diffs.median().total_seconds()
        return max(int(round(seconds / 60.0)), 1)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        df = df.sort_index()

        bar_min = self._infer_bar_minutes(df.index)
        bars_in_lookback = max(int(self.lookback_minutes // bar_min), 1)

        df['date'] = df.index.date
        df['upper'] = np.nan
        df['lower'] = np.nan

        for d, day_data in df.groupby('date'):
            if len(day_data) >= bars_in_lookback:
                open_period = day_data.head(bars_in_lookback)
                df.loc[df['date'] == d, 'upper'] = open_period['high'].max()
                df.loc[df['date'] == d, 'lower'] = open_period['low'].min()
            else:
                df.loc[df['date'] == d, 'upper'] = np.nan
                df.loc[df['date'] == d, 'lower'] = np.nan

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close  = (df['low']  - df['close'].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = true_range.rolling(self.atr_period, min_periods=1).mean()

        df['signal'] = 0
        can_trade_mask = df['upper'].notna() & df['lower'].notna()
        df.loc[can_trade_mask & (df['close'] > df['upper'] + self.atr_multiplier * df['ATR']), 'signal'] = 1
        df.loc[can_trade_mask & (df['close'] < df['lower'] - self.atr_multiplier * df['ATR']), 'signal'] = -1

        cooldown_bars = int((self.cooldown_hours * 60) // bar_min)
        if cooldown_bars > 0:
            sig = df['signal'].to_numpy()
            last_i = -10**9
            for i in range(len(sig)):
                if i <= last_i + cooldown_bars:
                    sig[i] = 0
                elif sig[i] != 0:
                    last_i = i
            df['signal'] = sig

        df.drop(columns=['date'], inplace=True)
        df.fillna(0, inplace=True)
        return df


class QuickTestStrategy:
    def __init__(self):
        self.name = "Quick Test Strategy"
        self.trade_count = 0
        self.last_trade_time = 0

    def generate_signal(self, market_data):
        """
        Simple fast test strategy: alternate buy/sell every minute.
        """
        current_time = time.time()

        if current_time - self.last_trade_time < 60:
            return 'HOLD'

        self.trade_count += 1
        self.last_trade_time = current_time

        print(f"🎯 Test trade #{self.trade_count}")

        if self.trade_count % 2 == 1:
            print("➡️ generate BUY signal")
            return 'BUY'
        else:
            print("⬅️ generate SELL signal")
            return 'SELL'


class SimpleStrategy:
    def __init__(self):
        self.name = "Simple Moving Average Strategy"
        self.last_price = None

    def generate_signal(self, market_data):
        """
        Generate trading signal.
        Return: 'BUY', 'SELL', or 'HOLD'
        """
        if not market_data.get('Success'):
            return 'HOLD'

        ticker = market_data['Data']['BTC/USD']
        current_price = ticker['LastPrice']
        price_change = ticker['Change']

        print(f"Price: ${current_price}, 24h change: {price_change*100:.2f}%")

        if price_change < -0.02:
            return 'BUY'
        elif price_change > 0.03:
            return 'SELL'
        else:
            return 'HOLD'
