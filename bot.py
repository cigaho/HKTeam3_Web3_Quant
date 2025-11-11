import time
import os
import logging
from datetime import datetime
import schedule
import pandas as pd

from api_client import client
from strategy import OpeningRangeBreakoutStrategy
import config

# global logging init
os.makedirs("logs", exist_ok=True)
today = datetime.now().strftime('%Y-%m-%d')
log_file = f"logs/{today}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger("trading-bot")


class TradingBot:
    def __init__(self):
        self.client = client
        self.strategy = OpeningRangeBreakoutStrategy()
        self.running = True
        # minimum notional in USD to avoid dust trades
        self.min_notional_usd = 10.0

    # connection test
    def test_connection(self):
        print("Testing API connection...")

        result = self.client.get_server_time()
        print(f"Server time: {result}")

        result = self.client.get_exchange_info()
        print(f"Exchange info: {result}")

        result = self.client.get_balance()
        print(f"Account balance: {result}")

        result = self.client.get_ticker('ETH/USD')
        print(f"ETH ticker: {result}")

    # normalize quantity according to exchange rules
    def _normalize_qty(self, raw_qty: float, pair_rule: dict) -> float:
        """
        Normalize quantity to exchange rule:
        - round by AmountPrecision
        - must be >= MiniOrder
        """
        if raw_qty <= 0:
            return 0.0

        amount_prec = int(pair_rule.get("AmountPrecision", 4))
        mini_order = float(pair_rule.get("MiniOrder", 0))

        qty = round(raw_qty, amount_prec)

        if qty <= 0:
            return 0.0

        if mini_order > 0 and qty < mini_order:
            return 0.0

        return qty

    # single trading loop
    def run_once(self):
        logger.info("==== start trading round ====")

        # 1) get balance
        account = self.client.get_balance()
        if not account.get("Success"):
            logger.error(f"failed to get balance: {account}")
            return

        spot = account.get("SpotWallet", {})
        usd_free = float(spot.get("USD", {}).get("Free", 0.0))
        logger.info(f"current USD balance: {usd_free}")

        usd_available = usd_free

        assets = getattr(config, "TRADE_ASSETS", ["ETH/USD"])

        exch_info = self.client.get_exchange_info()
        trade_pairs = exch_info.get("TradePairs", {}) if isinstance(exch_info, dict) else {}

        asset_info = {}
        signaled_assets = []

        # 2) generate signals for all assets
        for pair in assets:
            base = pair.split("/")[0]
            logger.info(f"processing asset: {pair}")

            try:
                df = self.client.get_ohlcv(base, interval='15m', limit=100)
            except Exception as e:
                logger.error(f"{pair} failed to fetch OHLCV: {e}")
                continue

            if df is None or df.empty:
                logger.warning(f"{pair} OHLCV is empty, skip")
                continue

            signal_df = self.strategy.generate_signals(df)
            latest_signal = int(signal_df["signal"].iloc[-1])
            last_price = float(df["close"].iloc[-1])

            logger.info(f"{pair} last price: {last_price}, signal: {latest_signal}")

            asset_info[pair] = {
                "signal": latest_signal,
                "price": last_price,
            }

            if latest_signal != 0:
                signaled_assets.append(pair)

        # 3) allocation
        allocations = {}
        allocation_mode = getattr(config, "ALLOCATION_MODE", "fixed")
        fixed_pct = float(getattr(config, "FIXED_ALLOCATION", 0.15))

        if allocation_mode == "fixed":
            for pair in assets:
                allocations[pair] = usd_free * fixed_pct
        else:
            if len(signaled_assets) > 0:
                per_usd = usd_free / len(signaled_assets)
                for pair in signaled_assets:
                    allocations[pair] = per_usd

        # 4) place orders
        for pair in assets:
            info = asset_info.get(pair)
            if not info:
                continue

            signal = info["signal"]
            price = info["price"]
            base = pair.split("/")[0]

            base_free = float(spot.get(base, {}).get("Free", 0.0))

            pair_rule = trade_pairs.get(pair, {})

            target_usd_for_this_asset = float(allocations.get(pair, 0.0))

            if signal == 1:
                usd_to_use = min(target_usd_for_this_asset, usd_available)

                if usd_to_use < self.min_notional_usd:
                    logger.info(f"{pair} buy signal but notional too small ({usd_to_use:.2f} USD), skip")
                    continue

                raw_qty = usd_to_use / price

                qty = self._normalize_qty(raw_qty, pair_rule)

                if qty <= 0:
                    logger.info(
                        f"{pair} buy signal but normalized qty is 0 "
                        f"(raw {raw_qty}, rule {pair_rule}), skip"
                    )
                    continue

                notional = qty * price
                if notional < self.min_notional_usd:
                    logger.info(
                        f"{pair} buy signal but final notional is only {notional:.2f} USD, skip"
                    )
                    continue

                logger.info(
                    f"{pair} buy signal, will buy {qty} {base}, about {notional:.2f} USD"
                )
                resp = self.client.place_order(
                    pair=pair,
                    side="BUY",
                    order_type="MARKET",
                    quantity=qty
                )
                logger.info(f"{pair} buy result: {resp}")

                usd_available = max(usd_available - notional, 0)

            elif signal == -1:
                if base_free <= 0:
                    logger.info(f"{pair} sell signal but no position, skip")
                    continue

                sell_qty = self._normalize_qty(base_free, pair_rule)
                if sell_qty <= 0:
                    logger.info(
                        f"{pair} sell signal but position {base_free} cannot be normalized, skip"
                    )
                    continue

                if sell_qty * price < self.min_notional_usd:
                    logger.info(
                        f"{pair} sell signal but notional too small {sell_qty*price:.2f} USD, skip"
                    )
                    continue

                logger.info(f"{pair} sell signal, will sell {sell_qty} {base}")
                resp = self.client.place_order(
                    pair=pair,
                    side="SELL",
                    order_type="MARKET",
                    quantity=sell_qty
                )
                logger.info(f"{pair} sell result: {resp}")
            else:
                logger.info(f"{pair} no signal this round")

        logger.info("==== end trading round ====")

    # continuous run
    def run_continuous(self):
        print("🚀 start quick test mode...")

        self.test_connection()

        schedule.every(2).minutes.do(self.run_once)

        self.run_once()

        print("⏰ bot is running (every 2 minutes)...")
        while self.running:
            schedule.run_pending()
            time.sleep(1)
