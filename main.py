import time
import json
import threading
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st

BOT_TOKEN = "8942257131:AAGSFvdiXFq5_y_kwKNYfnCSNb28l1JgIiA"
CHAT_ID = "8574214847"

# 30 प्रमुख लिक्विड स्टॉक्स (बिना एरर तेज़ी से लोड होने के लिए)
WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "TITAN.NS", "M&M.NS", "TATASTEEL.NS", "NTPC.NS", "POWERGRID.NS",
    "ONGC.NS", "COALINDIA.NS", "BEL.NS", "HAL.NS", "TRENT.NS",
    "ZOMATO.NS", "VEDL.NS", "PFC.NS", "RECLTD.NS", "BHEL.NS"
]

if "signals_history" not in st.session_state:
    st.session_state.signals_history = []

def send_telegram(text: str):
    import urllib.request
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass

def fetch_and_evaluate(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d")
        if df.empty or len(df) < 30:
            return None

        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['vol_sma20'] = df['Volume'].rolling(window=20).mean()
        df['vol_surge'] = df['Volume'] / (df['vol_sma20'] + 1e-6)

        tr = pd.concat([
            df['High'] - df['Low'],
            (df['High'] - df['Close'].shift(1)).abs(),
            (df['Low'] - df['Close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()

        change = df['Close'].diff()
        gain = (change.where(change > 0, 0)).rolling(window=14).mean()
        loss = (-change.where(change < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))

        curr = df.iloc[-1]
        score = 50
        reasons = []

        if curr['Close'] >= curr['ema_20']:
            score += 20
            reasons.append("Above 20 EMA")
        if curr['Close'] >= curr['ema_50']:
            score += 15
            reasons.append("Above 50 EMA")
        if curr['rsi'] >= 50:
            score += 15
            reasons.append(f"RSI Bullish ({int(curr['rsi'])})")

        entry = round(curr['Close'], 2)
        atr_val = curr['atr'] if pd.notna(curr['atr']) else (entry * 0.02)

        return {
            "Time": datetime.now().strftime("%H:%M"),
            "Stock": symbol.replace(".NS", ""),
            "Score": score,
            "Price": entry,
            "Target 1": round(entry + (1.5 * atr_val), 2),
            "Target 2": round(entry + (2.5 * atr_val), 2),
            "Stop Loss": round(entry - (1.0 * atr_val), 2),
            "Setup": " + ".join(reasons) if reasons else "Trend Base"
        }
    except Exception:
        return None

def run_scan():
    results = []
    for sym in WATCHLIST:
        res = fetch_and_evaluate(sym)
        if res:
            results.append(res)
    results.sort(key=lambda x: x['Score'], reverse=True)
    st.session_state.signals_history = results
    return results

# Streamlit UI
st.set_page_config(page_title="Alpha Hunter", page_icon="📈", layout="wide")
st.title("🎯 Owl Alpha Hunter - Radar")

col1, col2 = st.columns(2)
col1.metric("Status", "ONLINE 🟢")
col2.metric("Filtered Stocks", len(st.session_state.signals_history))

if st.button("🚀 Scan Market Now"):
    with st.spinner("लाइव डेटा लोड हो रहा है..."):
        run_scan()
    st.rerun()

st.subheader("⚡ Stock Radar Results")
if st.session_state.signals_history:
    st.dataframe(pd.DataFrame(st.session_state.signals_history), use_container_width=True)
else:
    st.warning("कोई डेटा नहीं मिला। कृपया ऊपर दिए गए '🚀 Scan Market Now' बटन पर क्लिक करें।")
