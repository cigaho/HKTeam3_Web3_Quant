class SimpleStrategy:
    def __init__(self):
        self.name = "简单移动平均策略"
        self.last_price = None
    
    def generate_signal(self, market_data):
        """
        生成交易信号
        返回: 'BUY', 'SELL', 或 'HOLD'
        """
        if not market_data.get('Success'):
            return 'HOLD'
            
        # 提取行情数据
        ticker = market_data['Data']['BTC/USD']
        current_price = ticker['LastPrice']
        price_change = ticker['Change']  # 24小时价格变化百分比
        
        print(f"价格: ${current_price}, 24小时变化: {price_change*100:.2f}%")
        
        # 简单的策略逻辑（你需要在这里实现你的真实策略）
        if price_change < -0.02:  # 如果24小时下跌超过2%
            return 'BUY'
        elif price_change > 0.03:  # 如果24小时上涨超过3%
            return 'SELL'
        else:
            return 'HOLD'
