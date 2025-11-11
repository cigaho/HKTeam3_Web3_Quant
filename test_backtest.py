#!/usr/bin/env python3
"""
Quantitative Strategy Backtesting Test Script
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from backtest_strategy import (MultiFactorStrategy, OpeningRangeBreakoutStrategy)

# Load environment variables
load_dotenv()

print("🎯 Quantitative Strategy Backtesting System")
print("="*60)

# Check API Key
api_key = os.getenv('HORUS_API_KEY')
if not api_key:
    print("❌ Error: Please set HORUS_API_KEY in .env file")
    sys.exit(1)

print(f"✅ Using API Key: {api_key[:10]}...")

try:
    from data_loader import DataLoader
    from backtester import Backtester
    from backtest_strategy import MovingAverageStrategy, RSIStrategy
    
    # 1. Load data
    print("\n📥 Loading historical data...")
    loader = DataLoader(api_key=api_key)
    
    data = loader.get_historical_data(
        asset='BTC',
        interval='15m',
        start=int(datetime(2025, 10, 1).timestamp()),
        end=int(datetime(2025, 10, 15).timestamp())
    )
    
    # Add technical indicators
    data = loader.add_technical_indicators(data)
    print(f"✅ Data loading completed: {data.shape}")
    
    # 2. Initialize backtester
    backtester = Backtester(initial_capital=50000, commission=0.001)
    
    # 3. Test strategies
    strategies = [
        MovingAverageStrategy(short_window=10, long_window=30),
        RSIStrategy(window=14, oversold=30, overbought=70),
        MultiFactorStrategy(),
        OpeningRangeBreakoutStrategy()
    ]
    
    results = {}
    for strategy in strategies:
        print(f"\n📈 Testing strategy: {strategy.name}")
        
        try:
            result = backtester.run_backtest(strategy, data)
            results[strategy.name] = result
            
            # Display results
            print(f"   📊 Total return: {result['total_return']:+.2%}")
            print(f"   📉 Max drawdown: {result['max_drawdown']:+.2%}")
            print(f"   ⭐ Sharpe ratio: {result['sharpe_ratio']:.2f}")
            print(f"   📈 Sortino ratio: {result['sortino_ratio']:.2f}")
            print(f"   📊 Calmar ratio: {result['calmar_ratio']:.2f}")
            print(f"   🔢 Total trades: {result['total_trades']}")
            print(f"   🎯 Win rate: {result['win_rate']:.1%}")
            
        except Exception as e:
            print(f"   ❌ Strategy test failed: {e}")
            continue
    
    # 4. Compare strategy performance
    if results:
        print("\n🏆 Strategy Comparison Results")
        print("="*40)
        for name, result in results.items():
            print(f"{name}:")
            print(f"   Return: {result['total_return']:+.2%} | Sharpe: {result['sharpe_ratio']:.2f}")
            print(f"   Sortino: {result['sortino_ratio']:.2f} | Calmar: {result['calmar_ratio']:.2f}")
            print(f"   Drawdown: {result['max_drawdown']:+.2%} | Win rate: {result['win_rate']:.1%}")
        
        # Find best strategy (based on Sortino ratio)
        best_strategy = max(results.items(), key=lambda x: x[1]['sortino_ratio'])
        print(f"\n🏅 Best strategy (based on Sortino ratio): {best_strategy[0]}")
        print(f"📈 Sortino ratio: {best_strategy[1]['sortino_ratio']:.2f}")
    
    print("\n🎉 Backtesting completed!")
    
except Exception as e:
    print(f"❌ Backtesting failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
