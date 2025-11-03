import os
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件中的环境变量

# Roostoo API配置
ROOSTOO_API_KEY = os.getenv('ROOSTOO_API_KEY', 'your_competition_api_key')
ROOSTOO_SECRET = os.getenv('ROOSTOO_SECRET', 'your_competition_secret')
ROOSTOO_BASE_URL = "https://api.roostoo.com"  # 根据实际API文档修改

# 交易配置
INITIAL_BALANCE = 50000  # 初始资金
COMMISSION_RATE = 0.001  # 手续费率
