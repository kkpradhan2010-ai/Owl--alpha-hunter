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

# 40 प्रमुख लिक्विड स्टॉक्स
WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "TITAN.NS", "M&M.NS", "TATASTEEL.NS", "NTPC.NS", "POWERGRID.NS",
    "ONGC.NS", "COALINDIA.NS", "BEL.NS", "HAL.NS", "TRENT.NS",
    "ZOMATO.NS", "VEDL.NS", "PFC.NS", "RECLTD.NS", "BHEL.NS",
    "DIXON.NS", "POLYCAB.NS", "CHOLAFIN.NS", "DLF.NS", "VBL.NS",
    "PERSISTENT.NS", "IRFC.NS", "RVNL.NS", "MAZDOCK.NS", "CUMMINSIND.NS"
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
        if df.empty or len(df) < 35:
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
        df['high_20d'] = df['High'].shift(1).rolling(window=20).max()

        curr = df.iloc[-1]
        
        # 1. सख्त रिजेक्शन नियम (Strict Rejections)
        if curr['Close'] < curr['ema_50']:  # अगर 50 EMA के नीचे है तो तुरंत बाहर
            return None
        if curr['rsi'] > 76 or curr['rsi'] < 52:  # ओवरबॉट या कमज़ोर मोमेंटम बाहर
            return None

        score = 0
        reasons = []

        # 2. ट्रेंड अलाइनमेंट (30 अंक)
        if curr['Close'] > curr['ema_20'] > curr['ema_50']:
            score += 30
            reasons.append("Super Trend")

        # 3. भारी वॉल्यूम सर्ज (35 अंक)
        if curr['vol_surge'] >= 1.6:
            score += 35
            reasons.append(f"Big Vol ({curr['vol_surge']:.1f}x)")
        elif curr['vol_surge'] >= 1.25:
            score += 20
            reasons.append(f"Vol Surge ({curr['vol_surge']:.1f}x)")
        else:
            return None  # बिना वॉल्यूम वाला शेयर बिल्कुल नहीं चाहिए

        # 4. RSI बुलिश मोमेंटम (20 अंक)
        if 58 <= curr['rsi'] <= 72:
            score += 20
            reasons.append("RSI Momentum")

        # 5. ब्रेकआउट के करीब या नया हाई (15 अंक)
        if curr['Close'] >= curr['high_20d'] * 0.985:
            score += 15
            reasons.append("Breakout Zone")

        # सिर्फ 75+ स्कोर वाले हाई-कनविक्शन शेयर्स ही पास होंगे
        if score >= 75:
            entry = round(curr['Close'], 2)
            atr_val = curr['atr'] if pd.notna(curr['atr']) else (entry * 0.02)
            return {
                "Rank": 0,
                "Stock": symbol.replace(".NS", ""),
                "Score": f"{score}/100",
                "Price (₹)": entry,
                "Target 1 (₹)": round(entry + (1.5 * atr_val), 2),
                "Target 2 (₹)": round(entry + (2.5 * atr_val), 2),
                "Stop Loss (₹)": round(entry - (1.0 * atr_val), 2),
                "Setup Reason": " + ".join(reasons)
            }
        return None
    except Exception:
        return None

def run_scan():
    results = []
    for sym in WATCHLIST:
        res = fetch_and_evaluate(sym)
        if res:
            results.append(res)
    
    # सबसे ज़्यादा स्कोर के आधार पर सॉर्ट
    results.sort(key=lambda x: int(x['Score'].split('/')[0]), reverse=True)
    
    # केवल टॉप 3 से 5 बेस्ट स्टॉक्स ही रखें
    top_picks = results[:5]
    for idx, item in enumerate(top_picks, 1):
        item["Rank"] = f"#{idx}"
        
    st.session_state.signals_history = top_picks
    return top_picks

# UI Dashboard
st.set_page_config(page_title="Alpha Hunter", page_icon="🎯", layout="wide")
st.title("🎯 Owl Alpha Hunter - Top High-Conviction Picks")
st.caption("A+ Grade Breakout & Momentum Radar (Max 3-5 Stocks)")

col1, col2 = st.columns(2)
col1.metric("Status", "ONLINE 🟢")
col2.metric("Filtered High Conviction", len(st.session_state.signals_history))

if st.button("🚀 Scan Top High-Conviction Picks"):
    with st.spinner("कड़े नियमों के साथ बेस्ट 3-5 स्टॉक्स फ़िल्टर हो रहे हैं..."):
        run_scan()
    st.rerun()

st.subheader("⚡ Today's Top A+ Trades")
if st.session_state.signals_history:
    st.dataframe(pd.DataFrame(st.session_state.signals_history), use_container_width=True)
else:
    st.info("अभी कोई कचरा या अधूरा सेटअप नहीं मिला। सिर्फ A+ सेटअप मिलने पर यहाँ टॉप 3-5 शेयर दिखेंगे। '🚀 Scan Top High-Conviction Picks' दबाएँ।")
