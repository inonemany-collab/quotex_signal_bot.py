"""
Simple Quotex Telegram Signal Bot (Educational)
Uses pyquotex for real candle data + RSI strategy
Always use DEMO account first!
"""

import asyncio
import time
import requests
from pyquotex.stable_api import Quotex

# ============ SETTINGS ============
EMAIL = "your_quotex_email@gmail.com"      # Quotex ডেমো অ্যাকাউন্ট ইমেইল
PASSWORD = "your_password"                  # পাসওয়ার্ড
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"           # @BotFather থেকে পাওয়া টোকেন
CHAT_ID = "YOUR_CHAT_ID"                    # আপনার Telegram Chat ID (অথবা চ্যানেল ID)
SYMBOL = "EURUSD_otc"                       # পেয়ার (যেমন GBPUSD_otc, USDJPY_otc)
PERIOD = 60                                 # ১ মিনিট ক্যান্ডল
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
        print("Signal sent to Telegram")
    except Exception as e:
        print("Telegram error:", e)

async def main():
    client = Quotex(email=EMAIL, password=PASSWORD)
    client.account_is_demo = 1  # ডেমো মোড
    print("Connecting to Quotex...")
    ok, reason = await client.connect()
    if not ok:
        print("Connection failed:", reason)
        return

    print(f"Connected! Monitoring {SYMBOL}...")
    last_signal = None

    while True:
        try:
            candles = await client.get_candles(SYMBOL, time.time(), 3600, PERIOD)
            if not candles or len(candles) < 20:
                await asyncio.sleep(10)
                continue

            closes = [float(c["close"]) for c in candles]
            rsi = calc_rsi(closes)

            if rsi is None:
                await asyncio.sleep(5)
                continue

            current_time = time.strftime("%H:%M:%S")
            signal = None

            if rsi < 30:
                signal = "CALL 🔼 (RSI Oversold)"
            elif rsi > 70:
                signal = "PUT 🔽 (RSI Overbought)"

            if signal and signal != last_signal:
                msg = (
                    f"<b>Quotex Signal</b>\n"
                    f"Pair: {SYMBOL}\n"
                    f"Time: {current_time}\n"
                    f"Signal: <b>{signal}</b>\n"
                    f"RSI: {rsi:.1f}\n"
                    f"Expiry: 1 Minute"
                )
                print(msg.replace("<b>", "").replace("</b>", ""))
                send_telegram(msg)
                last_signal = signal
            else:
                print(f"[{current_time}] RSI: {rsi:.1f} - No signal")

            await asyncio.sleep(30)  # প্রতি ৩০ সেকেন্ডে চেক

        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(10)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
