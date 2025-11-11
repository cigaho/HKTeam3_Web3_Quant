import time
import schedule
from api_client import client
from strategy import QuickTestStrategy, SimpleStrategy
import config

class TradingBot:
    def __init__(self):
        self.client = client
        self.strategy = QuickTestStrategy()  # 默认策略
        self.running = True
        self.watchlist = ['BTC/USD', 'ETH/USD', 'SOL/USD']  # 监控的资产列表
        self.asset_strategies = {}  # 每个资产的策略实例
        
    def initialize_strategies(self):
        """为每个资产初始化策略"""
        print("🎯 初始化资产策略...")
        for asset in self.watchlist:
            # 为每个资产创建独立的策略实例
            self.asset_strategies[asset] = QuickTestStrategy()
            print(f"   {asset}: {self.asset_strategies[asset].name}")
    
    def test_connection(self):
        """测试API连接"""
        print("🔌 测试API连接...")
        
        # 测试服务器时间
        result = self.client.get_server_time()
        print(f"服务器时间: {result}")
        
        # 测试交易所信息
        result = self.client.get_exchange_info()
        print(f"交易所信息: {result}")
        
        # 测试余额查询
        result = self.client.get_balance()
        print(f"账户余额: {result}")
        
        # 测试所有监控资产的行情
        for asset in self.watchlist:
            result = self.client.get_ticker(asset)
            print(f"{asset}行情: {result.get('Success', False)}")
    
    def run_once(self):
        """执行一次完整的交易循环"""
        try:
            print("\n" + "="*60)
            print("🔄 开始多资产交易循环...")
            
            # 为每个资产执行交易逻辑
            for asset in self.watchlist:
                self._trade_asset(asset)
            
            # 检查总体账户状态
            self._check_account_status()
            
        except Exception as e:
            print(f"❌ 交易循环错误: {e}")
    
    def _trade_asset(self, asset):
        """处理单个资产的交易"""
        print(f"\n📊 处理资产: {asset}")
        
        # 1. 获取市场数据
        market_data = self.client.get_ticker(asset)
        
        if not market_data.get('Success'):
            print(f"   ❌ 获取{asset}数据失败")
            return
        
        ticker = market_data['Data'][asset]
        current_price = ticker['LastPrice']
        price_change = ticker.get('Change', 0) * 100  # 转换为百分比
        
        print(f"   💰 当前价格: ${current_price}")
        print(f"   📈 24小时变化: {price_change:+.2f}%")
        
        # 2. 获取该资产的策略信号
        strategy = self.asset_strategies.get(asset, self.strategy)
        signal = strategy.generate_signal(market_data)
        print(f"   🎯 交易信号: {signal}")
        
        # 3. 执行交易
        if signal == 'BUY':
            self._execute_buy(asset, current_price)
        elif signal == 'SELL':
            self._execute_sell(asset, current_price)
        else:
            print("   ⏸️  持有不动")
    
    def _execute_buy(self, asset, current_price):
        """执行买入操作"""
        print("   🟢 执行买入操作...")
        
        # 计算交易量（根据资产类型调整最小交易量）
        if 'BTC' in asset:
            quantity = 0.0001  # BTC最小交易量
        elif 'ETH' in asset:
            quantity = 0.001   # ETH最小交易量
        else:
            quantity = 0.01    # 其他资产最小交易量
        
        # 检查账户余额
        account = self.client.get_balance()
        if account.get('Success'):
            usd_balance = account['SpotWallet']['USD']['Free']
            required_cash = quantity * current_price * 1.001  # 包含手续费
            
            if required_cash > usd_balance:
                print(f"   ❌ 余额不足: 需要${required_cash:.2f}, 可用${usd_balance:.2f}")
                return
        
        try:
            result = self.client.place_order(
                pair=asset,
                side='BUY',
                order_type='MARKET',
                quantity=quantity
            )
            print(f"   ✅ 买入结果: {result.get('Success', False)}")
        except Exception as e:
            print(f"   ❌ 买入失败: {e}")
    
    def _execute_sell(self, asset, current_price):
        """执行卖出操作"""
        print("   🔴 执行卖出操作...")
        
        # 检查持仓
        account = self.client.get_balance()
        if not account.get('Success'):
            return
        
        # 获取该资产的持仓数量
        asset_name = asset.split('/')[0]  # 提取BTC、ETH等
        holdings = account['SpotWallet'].get(asset_name, {})
        quantity = holdings.get('Free', 0)
        
        if quantity <= 0:
            print(f"   ❌ 无{asset_name}持仓可卖")
            return
        
        # 使用最小交易量或全部持仓
        trade_quantity = min(quantity, 0.0001 if 'BTC' in asset else 0.001)
        
        try:
            result = self.client.place_order(
                pair=asset,
                side='SELL',
                order_type='MARKET',
                quantity=trade_quantity
            )
            print(f"   ✅ 卖出结果: {result.get('Success', False)}")
        except Exception as e:
            print(f"   ❌ 卖出失败: {e}")
    
    def _check_account_status(self):
        """检查账户状态"""
        print("\n📊 账户状态检查:")
        account = self.client.get_balance()
        
        if account.get('Success'):
            spot_wallet = account['SpotWallet']
            
            # 显示有余额的资产
            for asset, balance in spot_wallet.items():
                free = balance['Free']
                locked = balance['Lock']
                if free > 0 or locked > 0:
                    print(f"   {asset}: 可用={free}, 冻结={locked}")
    
    def run_continuous(self):
        """持续运行"""
        print("🚀 启动多资产交易机器人")
        print("="*50)
        
        # 初始化策略
        self.initialize_strategies()
        
        # 先测试连接
        self.test_connection()
        
        # 设置定时任务（每2分钟运行一次）
        schedule.every(2).minutes.do(self.run_once)
        
        # 立即运行一次
        self.run_once()
        
        print("\n⏰ 多资产交易机器人开始运行...")
        print("监控资产:", self.watchlist)
        print("运行频率: 每2分钟检查一次")
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """停止机器人"""
        self.running = False
        print("🛑 交易机器人已停止")

# 使用示例
if __name__ == "__main__":
    bot = TradingBot()
    
    try:
        bot.run_continuous()
    except KeyboardInterrupt:
        print("\n👋 用户中断程序")
        bot.stop()
