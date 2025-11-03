import time
import schedule
from api_client import client  # 导入我们创建的客户端
from strategy import SimpleStrategy
import config

class TradingBot:
    def __init__(self):
        self.client = client
        self.strategy = SimpleStrategy()
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
            print(f"市场数据: {market_data}")
            
            if market_data.get('Success'):
                ticker = market_data['Data']['BTC/USD']
                current_price = ticker['LastPrice']
                print(f"当前BTC价格: ${current_price}")
                
                # 2. 生成交易信号（这里需要你的策略逻辑）
                signal = self.strategy.generate_signal(ticker)
                print(f"交易信号: {signal}")
                
                # 3. 执行交易（示例：小额测试交易）
                if signal == 'BUY':
                    print("执行买入操作...")
                    # 买0.001个BTC（小额测试）
                    result = self.client.place_order(
                        pair='BTC/USD',
                        side='BUY',
                        order_type='MARKET',
                        quantity=0.001
                    )
                    print(f"买入结果: {result}")
                    
                elif signal == 'SELL':
                    print("执行卖出操作...")
                    # 卖0.001个BTC（小额测试）
                    result = self.client.place_order(
                        pair='BTC/USD',
                        side='SELL',
                        order_type='MARKET',
                        quantity=0.001
                    )
                    print(f"卖出结果: {result}")
            
            # 4. 检查账户状态
            account = self.client.get_balance()
            print(f"账户状态: {account}")
            
        except Exception as e:
            print(f"交易循环错误: {e}")
    
    def run_continuous(self):
        """持续运行"""
        print("交易机器人启动...")
        
        # 先测试连接
        self.test_connection()
        
        # 每1分钟运行一次（测试阶段可以频繁一些）
        schedule.every(1).minutes.do(self.run_once)
        
        # 立即运行一次
        self.run_once()
        
        print("机器人开始定时运行...")
        while self.running:
            schedule.run_pending()
            time.sleep(1)
