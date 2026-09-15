import time
import schedule
import json
import urllib.request
import pandas as pd
import numpy as np
from datetime import datetime

BOT_TOKEN = "8942257131:AAGSFvdiXFq5_y_kwKNYfnCSNb28l1JgIiA"
CHAT_ID = "8574214847"

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        print(f"Error: {e}")

WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS",
    "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "TITAN.NS", "M&M.NS", "TATASTEEL.NS", "ASIANPAINT.NS"
]

triggered_today = set()

def fetch_data(symbol: str):
    end_t = int(time.time())
    start_t = end_t - (100 * 86400)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&period1={start_t}&period2={end_t}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        res = data['chart']['result'][0]
        quote = res['indicators']['quote'][0]
        timestamps = res['timestamp']
        return pd.DataFrame({
            'date': pd.to_datetime(timestamps, unit='s'),
            'open': quote['open'],
            'high': quote['high'],
            'low': quote['low'],
            'close': quote['close'],
            'volume': quote['volume']
        }).dropna()
    except Exception:
        return None

def evaluate(df: pd.DataFrame, symbol: str):
    if len(df) < 55:
        return None

    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['vol_sma20'] = df['volume'].rolling(window=20).mean()
    df['vol_surge'] = df['volume'] / (df['vol_sma20'] + 1e-6)
    
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift(1)).abs(),
        (df['low'] - df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    
    change = df['close'].diff()
    gain = (change.where(change > 0, 0)).rolling(window=14).mean()
    loss = (-change.where(change < 0, 0)).rolling(window=14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))
    df['high_20d'] = df['high'].shift(1).rolling(window=20).max()

    curr = df.iloc[-1]

    if curr['close'] < curr['ema_50'] or curr['rsi'] > 78:
        return None
    if (curr['close'] > curr['high_20d']) and (curr['vol_surge'] < 1.3):
        return None

    score = 0
    reasons = []

    if curr['vol_surge'] >= 1.8:
        score += 30
        reasons.append(f"Volume Surge ({curr['vol_surge']:.1f}x)")
    elif curr['vol_surge'] >= 1.3:
        score += 15

    if curr['close'] > curr['ema_20'] > curr['ema_50']:
        score += 30
        reasons.append("Bullish Trend Stack")

    if curr['close'] > curr['high_20d']:
        score += 25
        reasons.append("20-Day Breakout")

    if 55 <= curr['rsi'] <= 70:
        score += 15
        reasons.append("RSI in Bullish Zone")

    if score >= 80:
        entry = round(curr['close'], 2)
        atr_val = curr['atr']
        return {
            "symbol": symbol.replace(".NS", ""),
            "action": "STRONG BUY",
            "score": score,
            "entry": entry,
            "target_1": round(entry + (1.5 * atr_val), 2),
            "target_2": round(entry + (2.5 * atr_val), 2),
            "stop_loss": round(entry - (1.0 * atr_val), 2),
            "reasons": " + ".join(reasons)
        }
    return None

def run_scan():
    for sym in WATCHLIST:
        if sym in triggered_today:
            continue
        df = fetch_data(sym)
        if df is None:
            continue
        sig = evaluate(df, sym)
        if sig:
            msg = (
                f"🚨 *ALPHA CLOUD SIGNAL* 🚨\n\n"
                f"🟢 *Stock:* `{sig['symbol']}`\n"
                f"*Action:* {sig['action']} (Score: {sig['score']}/100)\n\n"
                f"🔹 *Entry:* ₹{sig['entry']}\n"
                f"🎯 *Target 1:* ₹{sig['target_1']}\n"
                f"🎯 *Target 2:* ₹{sig['target_2']}\n"
                f"🛑 *Stop Loss:* ₹{sig['stop_loss']}\n\n"
                f"📌 *Reasons:* {sig['reasons']}"
            )
            send_telegram(msg)
            triggered_today.add(sym)
            time.sleep(1)

if __name__ == "__main__":
    send_telegram("☁️ *Owl Alpha Hunter Live!* अब यह क्लाउड सर्वर पर 24 घंटे एक्टिव रहेगा।")
    schedule.every(15).minutes.do(run_scan)
    schedule.every().day.at("00:00").do(lambda: triggered_today.clear())
    run_scan()
    while True:
        schedule.run_pending()
        time.sleep(1)
