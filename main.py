import time
import json
import threading
import urllib.request
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st

BOT_TOKEN = "8942257131:AAGSFvdiXFq5_y_kwKNYfnCSNb28l1JgIiA"
CHAT_ID = "8574214847"

WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS",
    "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "TITAN.NS", "M&M.NS", "TATASTEEL.NS", "ASIANPAINT.NS"
]

signals_history = []

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        print(f"Telegram error: {e}")

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
        reasons.append("RSI Bullish")

    if score >= 70:
        entry = round(curr['close'], 2)
        atr_val = curr['atr']
        return {
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Stock": symbol.replace(".NS", ""),
            "Score": score,
            "Price": entry,
            "Target 1": round(entry + (1.5 * atr_val), 2),
            "Target 2": round(entry + (2.5 * atr_val), 2),
            "Stop Loss": round(entry - (1.0 * atr_val), 2),
            "Reasons": " + ".join(reasons)
        }
    return None

def background_scanner():
    while True:
        for sym in WATCHLIST:
            df = fetch_data(sym)
            if df is not None:
                sig = evaluate(df, sym)
                if sig and not any(s['Stock'] == sig['Stock'] for s in signals_history[-20:]):
                    signals_history.insert(0, sig)
                    msg = (
                        f"🚨 *ALPHA APP SIGNAL* 🚨\n\n"
                        f"🟢 *Stock:* `{sig['Stock']}` (Score: {sig['Score']}/100)\n"
                        f"🔹 *Entry:* ₹{sig['Price']}\n"
                        f"🎯 *Target 1:* ₹{sig['Target 1']}\n"
                        f"🎯 *Target 2:* ₹{sig['Target 2']}\n"
                        f"🛑 *Stop Loss:* ₹{sig['Stop Loss']}\n"
                        f"📌 *Signal:* {sig['Reasons']}"
                    )
                    send_telegram(msg)
            time.sleep(1)
        time.sleep(300)

if "started" not in st.session_state:
    st.session_state.started = True
    t = threading.Thread(target=background_scanner, daemon=True)
    t.start()

# --- STREAMLIT UI DASHBOARD ---
st.set_page_config(page_title="Alpha Hunter", page_icon="📈", layout="wide")
st.title("🎯 Owl Alpha Hunter - Live Market Scanner")
st.caption("24/7 Cloud Bot & Technical Radar Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Status", "ONLINE 🟢")
col2.metric("Watchlist Count", len(WATCHLIST))
col3.metric("Signals Today", len(signals_history))

st.subheader("⚡ Live Breakout Signals")
if signals_history:
    df_signals = pd.DataFrame(signals_history)
    st.dataframe(df_signals, use_container_width=True)
else:
    st.info("स्कैनर चालू है... जैसे ही किसी शेयर में 70+ स्कोर बनेगा, यहाँ लाइव लिस्ट आ जाएगी और टेलीग्राम पर भी मैसेज जाएगा।")

if st.button("🔄 Manual Scan Run"):
    st.rerun()
