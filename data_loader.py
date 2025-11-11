import pandas as pd
import numpy as np
import requests
import os
import pandas as pd
from datetime import datetime, timedelta
import json

class DataLoader:
    def __init__(self, api_key=None):
        """
        Initialize data loader.
        Uses Horus API only; raise on failure.
        """
        self.base_url = "https://api-horus.com"
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv('HORUS_API_KEY')
        if not self.api_key:
            raise ValueError("HORUS_API_KEY is not set. Please set it in .env or pass it in.")

        print(f"🔑 Using API Key: {self.api_key[:10]}...")

    def get_historical_data(self, asset='BTC', interval='1d', start=None, end=None):
        """
        Get historical price data from Horus API.

        Args:
            asset: asset symbol, e.g. 'BTC', 'ETH'
            interval: '15m', '1h', '1d'
            start: start timestamp (seconds)
            end: end timestamp (seconds)

        Returns:
            DataFrame with timestamp index and OHLC data

        Raises on API failure.
        """
        print(f"📊 Fetching {asset} historical data from Horus API...")

        if start is None:
            start_date = datetime(2024, 8, 1)
            start = int(start_date.timestamp())

        if end is None:
            end_date = datetime(2024, 11, 1)
            end = int(end_date.timestamp())

        print(f"📅 Time range: {datetime.fromtimestamp(start)} to {datetime.fromtimestamp(end)}")
        print(f"⏰ Interval: {interval}")
        print(f"💰 Asset: {asset}")

        endpoint = f"{self.base_url}/market/price"

        params = {
            'asset': asset,
            'interval': interval,
            'start': start,
            'end': end
        }

        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'QuantTradingBot/1.0'
        }

        print(f"🌐 Request URL: {endpoint}")
        print(f"📋 Request params: {params}")

        try:
            print("🔄 Sending API request...")
            response = requests.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                error_msg = f"API request failed: HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise Exception(error_msg)

            print("✅ API request succeeded")

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise Exception(f"JSON decode failed: {e} - response: {response.text[:200]}")

            df = self._parse_api_response(data, asset)

            print(f"✅ Parsed {len(df)} {asset} rows")
            print(f"📈 Price range: ${df['close'].min():.0f} - ${df['close'].max():.0f}")
            print(f"📊 Data time range: {df.index[0]} to {df.index[-1]}")

            return df

        except requests.exceptions.Timeout:
            raise Exception("API request timed out (30s)")
        except requests.exceptions.ConnectionError:
            raise Exception("Network connection error, please check network")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request error: {e}")
        except Exception as e:
            raise Exception(f"Data fetch failed: {e}")

    def _parse_api_response(self, api_data, asset):
        """
        Parse Horus API response.
        Expects format: [{"timestamp": ..., "price": ...}, ...]
        """
        if not api_data:
            raise ValueError("API returned empty data")

        if not isinstance(api_data, list):
            raise ValueError(f"API returned invalid format, expected list, got: {type(api_data)}")

        if len(api_data) == 0:
            raise ValueError("API returned empty list")

        records = []
        for i, item in enumerate(api_data):
            if not isinstance(item, dict):
                raise ValueError(f"Item {i} has invalid type, expected dict, got: {type(item)}")

            if 'timestamp' not in item:
                raise ValueError(f"Item {i} is missing 'timestamp': {item}")

            if 'price' not in item:
                raise ValueError(f"Item {i} is missing 'price': {item}")

            try:
                timestamp = datetime.fromtimestamp(item['timestamp'])
                price = float(item['price'])
            except (ValueError, TypeError) as e:
                raise ValueError(f"Item {i} conversion error: {e} - item: {item}")

            if price <= 0:
                raise ValueError(f"Item {i} has invalid price: {price}")

            records.append({
                'timestamp': timestamp,
                'price': price
            })

        df = pd.DataFrame(records)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        df = self._generate_ohlc_from_price(df, asset)

        return df

    def _generate_ohlc_from_price(self, price_df, asset):
        """
        Generate OHLCV from price-only data.
        """
        df = price_df.copy()

        df.rename(columns={'price': 'close'}, inplace=True)

        df['open'] = df['close'].shift(1)
        df.loc[df.index[0], 'open'] = df.loc[df.index[0], 'close']

        volatility_map = {
            'BTC': 0.02, 'ETH': 0.03, 'SOL': 0.05, 'BNB': 0.025,
            'XRP': 0.04, 'ADA': 0.045, 'DOGE': 0.08, 'DOT': 0.035,
            'LINK': 0.04, 'LTC': 0.03, 'BCH': 0.04, 'AVAX': 0.05
        }
        volatility = volatility_map.get(asset, 0.03)

        np.random.seed(42)

        high_volatility = np.random.uniform(0, volatility, len(df))
        df['high'] = df['close'] * (1 + high_volatility)

        low_volatility = np.random.uniform(0, volatility, len(df))
        df['low'] = df['close'] * (1 - low_volatility)

        df['high'] = np.maximum(df['high'], df[['open', 'close']].max(axis=1))
        df['low'] = np.minimum(df['low'], df[['open', 'close']].min(axis=1))

        base_volume = {
            'BTC': 1e9, 'ETH': 5e8, 'SOL': 2e8, 'BNB': 1e8,
            'XRP': 3e8, 'ADA': 2e8, 'DOGE': 1e8, 'DOT': 5e7,
            'LINK': 5e7, 'LTC': 8e7, 'BCH': 6e7, 'AVAX': 4e7
        }
        base_vol = base_volume.get(asset, 1e8)

        price_change = df['close'].pct_change().abs().fillna(0)
        volume_multiplier = 1 + price_change * 10

        df['volume'] = base_vol * volume_multiplier * np.random.uniform(0.8, 1.2, len(df))

        df = df[['open', 'high', 'low', 'close', 'volume']]

        return df

    def add_technical_indicators(self, data):
        """
        Add technical indicators.
        """
        df = data.copy()

        print("📊 Calculating technical indicators...")

        df['ma_7'] = df['close'].rolling(window=7, min_periods=1).mean()
        df['ma_25'] = df['close'].rolling(window=25, min_periods=1).mean()
        df['ma_99'] = df['close'].rolling(window=99, min_periods=1).mean()

        df['rsi_14'] = self._calculate_rsi(df['close'], 14)

        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        df['bb_middle'] = df['close'].rolling(window=20, min_periods=1).mean()
        bb_std = df['close'].rolling(window=20, min_periods=1).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        df['price_change'] = df['close'].pct_change()
        df['volatility_20'] = df['price_change'].rolling(window=20, min_periods=1).std()

        print("✅ Technical indicators calculated")
        return df

    def _calculate_rsi(self, prices, window=14):
        """Calculate RSI."""
        delta = prices.diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=window, min_periods=1).mean()
        avg_loss = loss.rolling(window=window, min_periods=1).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def validate_data(self, df):
        """
        Validate data quality.
        """
        print("🔍 Validating data...")

        if len(df) == 0:
            raise ValueError("Empty data")

        missing_values = df.isnull().sum().sum()
        if missing_values > 0:
            print(f"⚠️ Found {missing_values} missing values")

        if (df['close'] <= 0).any():
            raise ValueError("Found invalid price data (<= 0)")

        time_diff = df.index.to_series().diff().dropna()
        if len(time_diff) > 0:
            avg_gap = time_diff.mean()
            print(f"⏱️ Avg time gap: {avg_gap}")

        print("✅ Data validation passed")
        return True

# simple test
def test_data_loader():
    """Test data loader."""
    try:
        loader = DataLoader()

        print("🧪 Start testing DataLoader...")

        data = loader.get_historical_data(
            asset='BTC',
            interval='1d'
        )

        loader.validate_data(data)

        data_with_indicators = loader.add_technical_indicators(data)

        print(f"🎉 Test succeeded!")
        print(f"📊 Final data shape: {data_with_indicators.shape}")
        print(f"📈 Columns: {list(data_with_indicators.columns)}")

        return data_with_indicators

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    test_data_loader()
