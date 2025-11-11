import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

class Backtester:
    def __init__(self, initial_capital=50000, commission=0.001, slippage=0.0005):
        """
        initialize backtest engine
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.reset()
    
    def reset(self):
        """reset backtest state"""
        self.capital = self.initial_capital
        self.position = 0
        self.position_value = 0
        self.trades = []
        self.equity_curve = []
        self.signals = []
        self.current_step = 0
        
    def run_backtest(self, strategy, data, add_indicators=True):
        print(f"🎯 Backtest start: {strategy.name}")
        self.reset()
        
        #add indicators
        if add_indicators:
            data = self.add_technical_indicators(data)
        
        # generate order signal
        signals_df = strategy.generate_signals(data)
        
        if signals_df is None or len(signals_df) == 0:
            raise ValueError("No trading signal formed by strategy")
        
        # run backtest 
        for i, (timestamp, row) in enumerate(signals_df.iterrows()):
            if i >= len(data):
                break
                
            self.current_step = i
            current_data = data.iloc[i]
            current_price = current_data['close']
            signal = row['signal'] if 'signal' in row else 0
            execution_price = self._apply_slippage(current_price, signal)
            
            # execute order
            self._execute_trading_rules(signal, execution_price, timestamp, current_data)
            
            # update equity curve
            self._update_equity_curve(execution_price, timestamp)
            
            # track signal
            self.signals.append({
                'timestamp': timestamp,
                'signal': signal,
                'price': execution_price
            })
        
        
        results = self._calculate_performance_metrics()
        results['strategy_name'] = strategy.name
        results['data_points'] = len(signals_df)
        
        print("✅ backtest finish!")
        return results
    
    def add_technical_indicators(self, data):
        df = data.copy()
        
        # moving average line
        df['ma_7'] = df['close'].rolling(window=7).mean()
        df['ma_25'] = df['close'].rolling(window=25).mean()
        
        # RSI
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        
        return df
    
    def _calculate_rsi(self, prices, window=14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _apply_slippage(self, price, signal):
        slippage_factor = self.slippage
        if signal > 0:
            return price * (1 + slippage_factor)
        elif signal < 0:
            return price * (1 - slippage_factor)
        else:
            return price
    
    def _execute_trading_rules(self, signal, price, timestamp, data):
        max_trade_value = self.capital * 0.1  # limit single transaction amount to 10%
        
        if signal == 1 and self.position == 0:  # buy
            max_quantity = max_trade_value / (price * (1 + self.commission))
            quantity = min(max_quantity, max_trade_value / price)
            
            if quantity > 0 and quantity * price <= self.capital:
                cost = quantity * price * (1 + self.commission)
                self.position = quantity
                self.capital -= cost
                
                self.trades.append({
                    'timestamp': timestamp,
                    'action': 'BUY',
                    'price': price,
                    'quantity': quantity,
                    'value': cost,
                    'commission': cost - quantity * price,
                    'signal_strength': signal
                })
        
        elif signal == -1 and self.position > 0:  # sell
            revenue = self.position * price * (1 - self.commission)
            self.capital += revenue
            self.position = 0
            
            self.trades.append({
                'timestamp': timestamp,
                'action': 'SELL',
                'price': price,
                'quantity': self.position,
                'value': revenue,
                'commission': self.position * price * self.commission,
                'signal_strength': signal
            })
    
    def _update_equity_curve(self, price, timestamp):
        current_equity = self.capital + (self.position * price)
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': current_equity,
            'price': price,
            'position': self.position,
            'cash': self.capital
        })
    
    def _calculate_performance_metrics(self):
        if len(self.equity_curve) == 0:
            return {}
        
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('timestamp', inplace=True)
        
        # basic indicator
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # calculate return
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        # calculate maximum drawdown
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()
        
        # annulized return rate
        days = (equity_df.index[-1] - equity_df.index[0]).days
        annual_return = (1 + total_return) ** (365/days) - 1 if days > 0 else 0
        
        # Sharpe ratio
        excess_returns = equity_df['returns'].dropna()
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        # Sortino Ratio 
        sortino_ratio = self._calculate_sortino_ratio(equity_df)
        
        #  Calmar Ratio
        calmar_ratio = self._calculate_calmar_ratio(annual_return, max_drawdown)
        
        # trading statistics
        total_trades = len(self.trades)
        winning_trades = self._calculate_winning_trades()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,  
            'calmar_ratio': calmar_ratio,   
            'total_trades': total_trades,
            'win_rate': win_rate,
            'trades': self.trades,
            'equity_curve': equity_df,
            'signals': self.signals
        }
    
    def _calculate_sortino_ratio(self, equity_df):
        """
        calculate Sortino Ratio
        formula: Sortino Ratio = Rp̄ / σd
        Rp̄ = average portfolio return
        σd = standard deviation for negative return
        """
        returns = equity_df['returns'].dropna()
        
        if len(returns) == 0:
            return 0
        
        
        mean_return = returns.mean()
        
        
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')
        
        downside_risk = downside_returns.std()
        
        if downside_risk == 0:
            return float('inf')
        
        # annualize
        sortino_ratio = mean_return / downside_risk * np.sqrt(252)
        return sortino_ratio
    
    def _calculate_calmar_ratio(self, annual_return, max_drawdown):
        """
        Calculate Calmar Ratio
        Formula: Calmar Ratio = annualized return / |maximum drawback|
        """
        if max_drawdown == 0:
            return float('inf')
        
        # absolute value for maximum drawback
        max_drawdown_abs = abs(max_drawdown)
        
        if max_drawdown_abs == 0:
            return float('inf')
        
        calmar_ratio = annual_return / max_drawdown_abs
        return calmar_ratio
    
    def _calculate_winning_trades(self):
        if len(self.trades) < 2:
            return 0
        
        wins = 0
        for i in range(0, len(self.trades)-1, 2):
            if self.trades[i]['action'] == 'BUY' and i+1 < len(self.trades):
                buy_price = self.trades[i]['price']
                sell_price = self.trades[i+1]['price']
                if sell_price > buy_price:
                    wins += 1
        return wins
    
    def generate_report(self, results):
        print("\n" + "="*60)
        print("📊 strategies backtest reports")
        print("="*60)
        
        print(f"Strategy name: {results['strategy_name']}")
        print(f"Data points: {results['data_points']}")
        print(f"Initial capital: ${results['initial_capital']:,.2f}")
        print(f"Final equity: ${results['final_equity']:,.2f}")
        print(f"Total return: {results['total_return']:+.2%}")
        print(f"Annualized return: {results['annual_return']:+.2%}")
        print(f"Maximum drawback: {results['max_drawdown']:+.2%}")
        print(f"Sharpe ratio: {results['sharpe_ratio']:.2f}")
        print(f"Sortino ratio: {results['sortino_ratio']:.2f}")  
        print(f"Calmar ratio: {results['calmar_ratio']:.2f}")    
        print(f"Total trade counts: {results['total_trades']}")
        print(f"Win rate: {results['win_rate']:.1%}")
        
        return results
