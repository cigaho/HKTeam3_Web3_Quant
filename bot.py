import time
import schedule
from api_client import client  # 导入我们创建的客户端
from strategy import SimpleStrategy, QuickTestStrategy
import config

class TradingBot:
    def __init__(self):
        self.client = client
        self.strategy = QuickTestStrategy()
        self.running = True
        
    def test_connection(self):
        """测试API连接"""
        print("测试API连接...")
        
        # 测试服务器时间
        result = self.client.get_server_time()
        print(f"服务器时间: {result}")
        
        # 测试交易所信息
        result = self.client.get_exchange_info()
        print(f"交易所信息: {result}")
        
        # 测试余额查询
        result = self.client.get_balance()
        print(f"账户余额: {result}")
        
        # 测试行情数据
        result = self.client.get_ticker('BTC/USD')
        print(f"BTC行情: {result}")
    
    def run_once(self):
        """执行一次完整的交易循环"""
        try:
            print("\n" + "="*50)
            print("开始交易循环...")
            
            # 1. 获取市场数据
            market_data = self.client.get_ticker('BTC/USD')
            print(f"市场数据获取: {'成功' if market_data.get('Success') else '失败'}")
            
            if market_data.get('Success'):
                ticker = market_data['Data']['BTC/USD']
                current_price = ticker['LastPrice']
                print(f"当前BTC价格: ${current_price}")
                
                # 2. 生成交易信号
                signal = self.strategy.generate_signal(market_data)
                print(f"交易信号: {signal}")
                
                # 3. 执行交易（使用最小交易量）
                if signal == 'BUY':
                    print("🟢 执行买入操作...")
                    # 最小交易量：0.0001 BTC（约$10）
                    result = self.client.place_order(
                        pair='BTC/USD',
                        side='BUY',
                        order_type='MARKET',
                        quantity=0.0001  # 最小交易量
                    )
                    print(f"买入结果: {result}")
                    
                elif signal == 'SELL':
                    print("🔴 执行卖出操作...")
                    # 最小交易量：0.0001 BTC
                    result = self.client.place_order(
                        pair='BTC/USD',
                        side='SELL',
                        order_type='MARKET', 
                        quantity=0.0001  # 最小交易量
                    )
                    print(f"卖出结果: {result}")
            
            # 4. 检查账户状态
            account = self.client.get_balance()
            if account.get('Success'):
                usd_balance = account['SpotWallet']['USD']['Free']
                print(f"💰 账户USD余额: ${usd_balance}")
            
        except Exception as e:
            print(f"交易循环错误: {e}")

    def run_continuous(self):
        """持续运行"""
        print("🚀 启动快速测试模式...")
        
        # 先测试连接
        self.test_connection()
        
        # 修改这行：改为每2分钟运行一次（原先是5分钟）
        schedule.every(2).minutes.do(self.run_once)
        
        # 立即运行一次
        self.run_once()
        
        print("⏰ 机器人开始运行（每2分钟检查一次）...")
        while self.running:
            schedule.run_pending()
            time.sleep(1)