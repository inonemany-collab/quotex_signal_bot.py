import asyncio
import time
import requests
import os
from pyquotex.stable_api import Quotex

# Environment Variables থেকে নেবে
EMAIL = os.getenv("EMAIL", "shahinalampsu@gmail.com")
PASSWORD = os.getenv("PASSWORD", "M*y725626")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8911990505:AAGjJnyAMyaUu4Ufl95Y1zPUm7-UUGvWee4")
CHAT_ID = os.getenv("CHAT_ID", "7128688603")

SYMBOLS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc"]
PERIOD = 60
last_signals = {}

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
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        print("Telegram sent")
    except Exception as e:
        print("Telegram error:", e)

async def check_pair(client, symbol):
    try:
        candles = await client.get_candles(symbol, time.time(), 3600, PERIOD)
        if not candles or len(candles) < 20:
            print(f"{symbol}: Not enough candles")
            return

        closes = [float(c["close"]) for c in candles]
        rsi = calc_rsi(closes)
        if rsi is None:
            return

        current_time = time.strftime("%H:%M:%S")
        signal = None

        if rsi < 30:
            signal = "CALL 🔼 (RSI Oversold)"
        elif rsi > 70:
            signal = "PUT 🔽 (RSI Overbought)"

        if signal and last_signals.get(symbol) != signal:
            msg = (
                f"<b>Quotex Signal</b>\n"
                f"Pair: {symbol}\n"
                f"Time: {current_time}\n"
                f"Signal: <b>{signal}</b>\n"
                f"RSI: {rsi:.1f}\n"
                f"Expiry: 1 Minute"
            )
            print(msg)
            send_telegram(msg)
            last_signals[symbol] = signal
        else:
            print(f"[{current_time}] {symbol} RSI: {rsi:.1f}")

    except Exception as e:
        print(f"Error {symbol}: {e}")

async def main():
    print("Starting bot...")
    print(f"Email: {EMAIL}")

    hosts = ["qxbroker.com", "quotex.com"]
    client = None

    for host in hosts:
        try:
            print(f"Trying host: {host}")
            client = Quotex(email=EMAIL, password=PASSWORD, host=host)
            ok, reason = await client.connect()
            if ok:
                print(f"Connected successfully with {host}")
                break
            else:
                print(f"Connection failed on {host}: {reason}")
                client = None
        except Exception as e:
            print(f"Error connecting to {host}: {e}")
            client = None

    if client is None:
        print("Could not connect to Quotex. Exiting.")
        return

    print("Bot is running...")
    while True:
        for symbol in SYMBOLS:
            await check_pair(client, symbol)
            await asyncio.sleep(2)
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
