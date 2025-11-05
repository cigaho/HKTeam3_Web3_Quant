import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

class Backtester:
    def __init__(self, initial_capital=50000, commission=0.001, slippage=0.0005):
        """
        初始化回测引擎
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.reset()
    
    def reset(self):
        """重置回测状态"""
        self.capital = self.initial_capital
        self.position = 0
        self.position_value = 0
        self.trades = []
        self.equity_curve = []
        self.signals = []
        self.current_step = 0
        
    def run_backtest(self, strategy, data, add_indicators=True):
        """
        运行回测
        """
        print(f"🎯 开始回测: {strategy.name}")
        self.reset()
        
        # 添加技术指标
        if add_indicators:
            data = self.add_technical_indicators(data)
        
        # 生成交易信号
        signals_df = strategy.generate_signals(data)
        
        if signals_df is None or len(signals_df) == 0:
            raise ValueError("策略未生成有效信号")
        
        # 运行回测循环
        for i, (timestamp, row) in enumerate(signals_df.iterrows()):
            if i >= len(data):
                break
                
            self.current_step = i
            current_data = data.iloc[i]
            current_price = current_data['close']
            signal = row['signal'] if 'signal' in row else 0
            
            # 应用滑点
            execution_price = self._apply_slippage(current_price, signal)
            
            # 执行交易逻辑
            self._execute_trading_rules(signal, execution_price, timestamp, current_data)
            
            # 更新权益曲线
            self._update_equity_curve(execution_price, timestamp)
            
            # 记录信号
            self.signals.append({
                'timestamp': timestamp,
                'signal': signal,
                'price': execution_price
            })
        
        # 计算绩效指标
        results = self._calculate_performance_metrics()
        results['strategy_name'] = strategy.name
        results['data_points'] = len(signals_df)
        
        print("✅ 回测完成!")
        return results
    
    def add_technical_indicators(self, data):
        """添加技术指标（与data_loader中的相同逻辑）"""
        df = data.copy()
        
        # 移动平均线
        df['ma_7'] = df['close'].rolling(window=7).mean()
        df['ma_25'] = df['close'].rolling(window=25).mean()
        
        # RSI
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        
        return df
    
    def _calculate_rsi(self, prices, window=14):
        """计算RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _apply_slippage(self, price, signal):
        """应用滑点"""
        slippage_factor = self.slippage
        if signal > 0:
            return price * (1 + slippage_factor)
        elif signal < 0:
            return price * (1 - slippage_factor)
        else:
            return price
    
    def _execute_trading_rules(self, signal, price, timestamp, data):
        """执行交易规则"""
        max_trade_value = self.capital * 0.1  # 单次交易最多10%资金
        
        if signal == 1 and self.position == 0:  # 买入
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
        
        elif signal == -1 and self.position > 0:  # 卖出
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
        """更新权益曲线"""
        current_equity = self.capital + (self.position * price)
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': current_equity,
            'price': price,
            'position': self.position,
            'cash': self.capital
        })
    
    def _calculate_performance_metrics(self):
        """计算绩效指标"""
        if len(self.equity_curve) == 0:
            return {}
        
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('timestamp', inplace=True)
        
        # 基础指标
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 计算收益率
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        # 最大回撤
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()
        
        # 年化收益率
        days = (equity_df.index[-1] - equity_df.index[0]).days
        annual_return = (1 + total_return) ** (365/days) - 1 if days > 0 else 0
        
        # 夏普比率
        excess_returns = equity_df['returns'].dropna()
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        # 交易统计
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
            'total_trades': total_trades,
            'win_rate': win_rate,
            'trades': self.trades,
            'equity_curve': equity_df,
            'signals': self.signals
        }
    
    def _calculate_winning_trades(self):
        """计算盈利交易数量"""
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
        """生成回测报告"""
        print("\n" + "="*60)
        print("📊 量化策略回测报告")
        print("="*60)
        
        print(f"策略名称: {results['strategy_name']}")
        print(f"数据点数: {results['data_points']}")
        print(f"初始资金: ${results['initial_capital']:,.2f}")
        print(f"最终权益: ${results['final_equity']:,.2f}")
        print(f"总收益率: {results['total_return']:+.2%}")
        print(f"年化收益率: {results['annual_return']:+.2%}")
        print(f"最大回撤: {results['max_drawdown']:+.2%}")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"总交易次数: {results['total_trades']}")
        print(f"胜率: {results['win_rate']:.1%}")
        
        return results