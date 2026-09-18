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

# Top 60 High-Conviction Liquid Stocks
WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS",
    "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "TITAN.NS", "M&M.NS", "TATASTEEL.NS", "ASIANPAINT.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS", "BAJAJFINSV.NS", "NTPC.NS",
    "POWERGRID.NS", "ONGC.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "JSWSTEEL.NS",
    "GRASIM.NS", "HINDUNILVR.NS", "HINDALCO.NS", "WIPRO.NS", "TECHM.NS",
    "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS", "EICHERMOT.NS", "DIVISLAB.NS",
    "BPCL.NS", "BRITANNIA.NS", "HEROMOTOCO.NS", "TATACONSUM.NS", "INDUSINDBK.NS",
    "BEL.NS", "HAL.NS", "TRENT.NS", "ZOMATO.NS", "JIOFIN.NS",
    "CHOLAFIN.NS", "VEDL.NS", "DLF.NS", "VBL.NS", "SIEMENS.NS",
    "PFC.NS", "RECLTD.NS", "BHEL.NS", "IRFC.NS", "RVNL.NS"
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
    
    # Basic Safety Rules
    if curr['close'] < curr['ema_50'] or curr['rsi'] > 80 or curr['rsi'] < 45:
        return None

    score = 0
    reasons = []

    # 1. Trend Structure (EMA Stack)
    if curr['close'] > curr['ema_20'] > curr['ema_50']:
        score += 35
        reasons.append("Super Bullish Trend")
    elif curr['close'] > curr['ema_20']:
        score += 20
        reasons.append("Above 20 EMA")

    # 2. Volume Activity
    if curr['vol_surge'] >= 1.5:
        score += 30
        reasons.append(f"High Vol ({curr['vol_surge']:.1f}x)")
    elif curr['vol_surge'] >= 1.0:
        score += 15
        reasons.append("Above Avg Vol")

    # 3. Momentum (RSI)
    if 55 <= curr['rsi'] <= 72:
        score += 20
        reasons.append(f"RSI Strong ({int(curr['rsi'])})")
    elif curr['rsi'] > 50:
        score += 10

    # 4. Breakout Bonus
    if curr['close'] >= curr['high_20d'] * 0.98:  # Breakout ya breakout ke bilkul paas
        score += 15
        reasons.append("Near/At 20D High")

    # Cutoff Score >= 60 for High Conviction
    if score >= 60:
        entry = round(curr['close'], 2)
        atr_val = curr['atr'] if pd.notna(curr['atr']) else (entry * 0.02)
        return {
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Stock": symbol.replace(".NS", ""),
            "Score": score,
            "Price": entry,
            "Target 1": round(entry + (1.5 * atr_val), 2),
            "Target 2": round(entry + (2.5 * atr_val), 2),
            "Stop Loss": round(entry - (1.0 * atr_val), 2),
            "Signal": " + ".join(reasons)
        }
    return None

def scan_all_stocks():
    global signals_history
    new_signals = []
    for sym in WATCHLIST:
        df = fetch_data(sym)
        if df is not None:
            sig = evaluate(df, sym)
            if sig:
                new_signals.append(sig)
        time.sleep(0.3)
    
    # Sort by highest score
    new_signals.sort(key=lambda x: x['Score'], reverse=True)
    signals_history = new_signals

def background_scanner():
    while True:
        scan_all_stocks()
        # Top signals Telegram alert
        for sig in signals_history[:3]:
            msg = (
                f"🚨 *ALPHA HUNTER RADAR* 🚨\n\n"
                f"🟢 *Stock:* `{sig['Stock']}` (Score: {sig['Score']}/100)\n"
                f"🔹 *Entry:* ₹{sig['Price']}\n"
                f"🎯 *Target 1:* ₹{sig['Target 1']}\n"
                f"🎯 *Target 2:* ₹{sig['Target 2']}\n"
                f"🛑 *Stop Loss:* ₹{sig['Stop Loss']}\n"
                f"📌 *Signal:* {sig['Signal']}"
            )
            send_telegram(msg)
        time.sleep(300)

if "started" not in st.session_state:
    st.session_state.started = True
    t = threading.Thread(target=background_scanner, daemon=True)
    t.start()

# --- STREAMLIT UI DASHBOARD ---
st.set_page_config(page_title="Alpha Hunter", page_icon="📈", layout="wide")
st.title("🎯 Owl Alpha Hunter - Live Market Radar")
st.caption("Auto Cloud Bot & Momentum Scanner")

col1, col2, col3 = st.columns(3)
col1.metric("Status", "ONLINE 🟢")
col2.metric("Watchlist Count", len(WATCHLIST))
col3.metric("Filtered Stocks", len(signals_history))

st.subheader("⚡ Top Filtered Stocks (Ranked by Score)")

if signals_history:
    df_signals = pd.DataFrame(signals_history)
    st.dataframe(df_signals, use_container_width=True)
else:
    st.info("डेटा स्कैन हो रहा है... कृपया 30-40 सेकंड प्रतीक्षा करें या नीचे दिए गए बटन पर क्लिक करें।")

if st.button("🔄 Manual Scan Run"):
    with st.spinner("स्कैनिंग जारी है..."):
        scan_all_stocks()
    st.rerun()
