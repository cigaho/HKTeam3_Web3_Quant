# HKTeam3 Web3 Quant Trading Bot

A quantitative trading system for cryptocurrency markets with backtesting and real-time trading capabilities.

## Features

- Real-time and historical data from Horus API
- Backtesting engine with performance metrics  
- Automated trading via Roostoo API
- Technical indicators (MA, RSI, MACD, etc.)
- Modular strategy development

## Quick Start

Install dependencies:
pip install -r requirements.txt

Run backtesting:
python test_backtest.py

## Backtest Strategy
Construct a new class describing your strategy in backtest_strategy.py
The format can follow the previous class strategy in the python file
Upon adding the strategy class, go to test_backtest.py to import it and add it in strategies list
Then run test_backtest.py file to check new strategy results
Crypto type, data interval and data period can also be modified in data inside test_backtest.py (May 1,2025 - Oct 31, 2025,  15m is recommended)

## Project Structure

data_loader.py - Horus API data integration

backtester.py - Backtesting engine  

backtest_strategy.py - Strategy implementations

bot.py - Real-time trading bot

api_client.py - Roostoo trading API

## Usage Example

from data_loader import DataLoader

from backtester import Backtester

from backtest_strategy import MovingAverageStrategy

loader = DataLoader()

data = loader.get_historical_data('BTC', '1d')

backtester = Backtester()

strategy = MovingAverageStrategy(10, 30)

result = backtester.run_backtest(strategy, data)

print(f"Returns: {result['total_return']:.2%}")

## Environment Setup

Create .env file with your API keys:

HORUS_API_KEY=your_key_here

ROOSTOO_API_KEY=your_key_here  

ROOSTOO_SECRET=your_secret_here

## Support

For issues and questions, please open an issue on GitHub.
