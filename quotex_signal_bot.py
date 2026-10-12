"""
Simple Quotex Telegram Signal Bot (Multiple Pairs)
Educational - Always use DEMO first!
"""

import asyncio
import time
import requests
from pyquotex.stable_api import Quotex

# ============ SETTINGS ============
EMAIL = "shahinalampsu@gmail.com"
PASSWORD = "M*y725626"                  # আপনার পাসওয়ার্ড বসান
TELEGRAM_TOKEN = "8911990505:AAGjJnyAMyaUu4Ufl95Y1zPUm7-UUGvWee4"
CHAT_ID = "7128688603"

# এখানে যেসব পেয়ার চাইবেন যোগ করুন
SYMBOLS = [
    "EURUSD_otc",
    "GBPUSD_otc",
    "USDJPY_otc",
    "AUDUSD_otc",
    "USDCAD_otc",
    "NZDUSD_otc",
    "EURJPY_otc",
    "GBPJPY_otc",
]

PERIOD = 60
# ==================================

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
        print("Signal sent")
    except Exception as e:
        print("Telegram error:", e)

async def check_pair(client, symbol):
    try:
        candles = await client.get_candles(symbol, time.time(), 3600, PERIOD)
        if not candles or len(candles) < 20:
            return None

        closes = [float(c["close"]) for c in candles]
        rsi = calc_rsi(closes)
        if rsi is None:
            return None

        signal = None
        if rsi < 30:
            signal = "CALL 🔼"
        elif rsi > 70:
            signal = "PUT 🔽"

        if signal:
            current_time = time.strftime("%H:%M:%S")
            msg = (
                f"<b>Quotex Signal</b>\n"
                f"Pair: <b>{symbol}</b>\n"
                f"Time: {current_time}\n"
                f"Signal: <b>{signal}</b>\n"
                f"RSI: {rsi:.1f}\n"
                f"Expiry: 1 Minute"
            )
            print(f"{symbol} -> {signal} (RSI: {rsi:.1f})")
            send_telegram(msg)
            return signal
        else:
            print(f"{symbol} RSI: {rsi:.1f} - No signal")
            return None
    except Exception as e:
        print(f"Error on {symbol}:", e)
        return None

async def main():
    client = Quotex(email=EMAIL, password=PASSWORD)
    client.account_is_demo = 1
    print("Connecting to Quotex...")
    ok, reason = await client.connect()
    if not ok:
        print("Connection failed:", reason)
        return

    print(f"Connected! Monitoring {len(SYMBOLS)} pairs...")

    while True:
        for symbol in SYMBOLS:
            await check_pair(client, symbol)
            await asyncio.sleep(2)  # পেয়ারগুলোর মধ্যে একটু গ্যাপ
        print("--- Checking again in 30 seconds ---")
        await asyncio.sleep(30)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
