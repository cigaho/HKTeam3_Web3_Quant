#!/usr/bin/env python3
"""
量化策略回测测试脚本
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from backtest_strategy import MultiFactorStrategy

# 加载环境变量
load_dotenv()

print("🎯 量化策略回测系统")
print("="*60)

# 检查API Key
api_key = os.getenv('HORUS_API_KEY')
if not api_key:
    print("❌ 错误: 请在.env文件中设置HORUS_API_KEY")
    sys.exit(1)

print(f"✅ 使用API Key: {api_key[:10]}...")

try:
    from data_loader import DataLoader
    from backtester import Backtester
    from backtest_strategy import MovingAverageStrategy, RSIStrategy
    
    # 1. 加载数据
    print("\n📥 加载历史数据...")
    loader = DataLoader(api_key=api_key)
    
    data = loader.get_historical_data(
        asset='BTC',
        interval='1d',
        start=int(datetime(2024, 8, 1).timestamp()),
        end=int(datetime(2025, 11, 1).timestamp())
    )
    
    # 添加技术指标
    data = loader.add_technical_indicators(data)
    print(f"✅ 数据加载完成: {data.shape}")
    
    # 2. 初始化回测器
    backtester = Backtester(initial_capital=50000, commission=0.001)
    
    # 3. 测试策略
    strategies = [
        MovingAverageStrategy(short_window=10, long_window=30),
        RSIStrategy(window=14, oversold=30, overbought=70),
        MultiFactorStrategy()
    ]
    
    results = {}
    for strategy in strategies:
        print(f"\n📈 测试策略: {strategy.name}")
        
        try:
            result = backtester.run_backtest(strategy, data)
            results[strategy.name] = result
            
            # 显示结果
            print(f"   📊 总收益: {result['total_return']:+.2%}")
            print(f"   📉 最大回撤: {result['max_drawdown']:+.2%}")
            print(f"   ⭐ 夏普比率: {result['sharpe_ratio']:.2f}")
            print(f"   📈 索提诺比率: {result['sortino_ratio']:.2f}")
            print(f"   📊 卡尔玛比率: {result['calmar_ratio']:.2f}")
            print(f"   🔢 交易次数: {result['total_trades']}")
            print(f"   🎯 胜率: {result['win_rate']:.1%}")
            
        except Exception as e:
            print(f"   ❌ 策略测试失败: {e}")
            continue
    
    # 4. 比较策略表现
    if results:
        print("\n🏆 策略比较结果")
        print("="*40)
        for name, result in results.items():
            print(f"{name}:")
            print(f"   收益: {result['total_return']:+.2%} | 夏普: {result['sharpe_ratio']:.2f}")
            print(f"   索提诺: {result['sortino_ratio']:.2f} | 卡尔玛: {result['calmar_ratio']:.2f}")
            print(f"   回撤: {result['max_drawdown']:+.2%} | 胜率: {result['win_rate']:.1%}")
        
        # 找出最佳策略（基于索提诺比率）
        best_strategy = max(results.items(), key=lambda x: x[1]['sortino_ratio'])
        print(f"\n🏅 最佳策略（基于索提诺比率）: {best_strategy[0]}")
        print(f"📈 索提诺比率: {best_strategy[1]['sortino_ratio']:.2f}")
    
    print("\n🎉 回测完成!")
    
except Exception as e:
    print(f"❌ 回测失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
