import os
from dotenv import load_dotenv

load_dotenv()  # load .env file environment data

# Roostoo API
ROOSTOO_API_KEY = os.getenv('ROOSTOO_API_KEY')
ROOSTOO_SECRET = os.getenv('ROOSTOO_SECRET')
ROOSTOO_BASE_URL = "https://mock-api.roostoo.com"

# Trade settings
INITIAL_BALANCE = 50000  # initial balance
COMMISSION_RATE = 0.001  # transaction fee

# API endpoints
ENDPOINTS = {
    'server_time': '/v3/serverTime',
    'exchange_info': '/v3/exchangeInfo',
    'ticker': '/v3/ticker',
    'balance': '/v3/balance',
    'pending_count': '/v3/pending_count',
    'place_order': '/v3/place_order',
    'query_order': '/v3/query_order',
    'cancel_order': '/v3/cancel_order'
}
