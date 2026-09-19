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

# NIFTY TOP 50 LIQUID STOCKS
STOCKS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "TCS.NS", "INFY.NS",
    "BHARTIARTL.NS", "SBIN.NS", "ITC.NS", "LT.NS", "AXISBANK.NS",
    "KOTAKBANK.NS", "M&M.NS", "HINDUNILVR.NS", "SUNPHARMA.NS", "MARUTI.NS",
    "TITAN.NS", "ADANIPORTS.NS", "NTPC.NS", "POWERGRID.NS", "BAJFINANCE.NS",
    "BAJAJFINSV.NS", "HCLTECH.NS", "WIPRO.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS",
    "NESTLEIND.NS", "TATASTEEL.NS", "JSWSTEEL.NS", "ONGC.NS", "COALINDIA.NS",
    "ADANIENT.NS", "TECHM.NS", "TATAMOTORS.NS", "HINDALCO.NS", "GRASIM.NS",
    "CIPLA.NS", "DRREDDY.NS", "EICHERMOT.NS", "DIVISLAB.NS", "BRITANNIA.NS",
    "APOLLOHOSP.NS", "SBILIFE.NS", "HDFCLIFE.NS", "INDUSINDBK.NS",
    "HEROMOTOCO.NS", "TRENT.NS", "BEL.NS", "HAL.NS", "DLF.NS", "SIEMENS.NS"
]

WEIGHTS = {
    "technical":  0.30,
    "volume":     0.25,
    "momentum":   0.25,
    "risk":       0.20
}

def limit_score(value):
    return max(-100, min(100, float(value)))

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

def calculate_factors(df):
    close = df["Close"]
    vol = df["Volume"]

    # 1. Technical Trend (EMA Stack + 20D High)
    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]
    prev_high = close.shift(1).rolling(20).max().iloc[-1]
    curr_close = close.iloc[-1]

    tech_score = 0
    if curr_close > ema20: tech_score += 35
    else: tech_score -= 35
    if ema20 > ema50: tech_score += 35
    else: tech_score -= 35
    if curr_close >= prev_high * 0.985: tech_score += 30

    # 2. Volume Surge
    avg_vol = vol.rolling(20).mean().iloc[-1]
    vol_ratio = vol.iloc[-1] / (avg_vol + 1e-6)
    v_score = (vol_ratio - 1.0) * 80

    # 3. RSI Momentum
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - (100 / (1 + rs))).iloc[-1]
    
    m_score = (rsi - 50) * 2.5
    if rsi > 78: m_score -= 40
    if rsi < 30: m_score -= 30

    # 4. Risk / Volatility
    daily_returns = close.pct_change()
    volatility = daily_returns.rolling(20).std().iloc[-1] * 100
    r_score = 70 if volatility < 2.5 else (30 if volatility < 4.0 else -50)

    # 5. ATR for Targets
    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift(1)).abs(),
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]

    return {
        "technical": limit_score(tech_score),
        "volume": limit_score(v_score),
        "momentum": limit_score(m_score),
        "risk": limit_score(r_score)
    }, curr_close, atr, vol_ratio

def analyze_stock(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d")
        if df.empty or len(df) < 35:
            return None

        factors, price, atr, vol_ratio = calculate_factors(df)

        final_score = 0
        for k, w in WEIGHTS.items():
            final_score += factors[k] * w
        final_score = limit_score(final_score)

        if final_score >= 45 and factors["volume"] > 0:
            signal = "BUY"
            sl = round(price - (1.2 * atr), 2)
            t1 = round(price + (1.5 * atr), 2)
            t2 = round(price + (2.5 * atr), 2)
            
            return {
                "Symbol": symbol.replace(".NS", ""),
                "Signal": signal,
                "Score": round(final_score, 1),
                "Price": round(price, 2),
                "Target 1": t1,
                "Target 2": t2,
                "Stop Loss": sl,
                "Volume": f"{vol_ratio:.1f}x"
            }
        return None
    except Exception:
        return None

def scan_full_market():
    picks = []
    for s in STOCKS:
        res = analyze_stock(s)
        if res:
            picks.append(res)
    picks.sort(key=lambda x: x["Score"], reverse=True)
    return picks[:5]

# UI DASHBOARD
st.set_page_config(page_title="AI Multi-Factor Radar", page_icon="⚡", layout="wide")
st.title("🎯 Multi-Factor NSE Alpha Radar")
st.caption("Auto Weighted Technical, Momentum, Volume & Volatility Engine")

if "picks" not in st.session_state:
    st.session_state.picks = []

col1, col2 = st.columns(2)
col1.metric("System Status", "ACTIVE 🟢")
col2.metric("Top Candidates Found", len(st.session_state.picks))

if st.button("🚀 Run Multi-Factor AI Scan"):
    with st.spinner("50 शेयरों का मल्टी-फैक्टर एनालिसिस चल रहा है..."):
        st.session_state.picks = scan_full_market()
    st.rerun()

st.subheader("⚡ Top 3-5 Filtered High-Probability Setups")
if st.session_state.picks:
    st.dataframe(pd.DataFrame(st.session_state.picks), use_container_width=True)
else:
    st.info("सिस्टम तैयार है। ऊपर दिए गए बटन पर क्लिक करके 50 शेयरों का ताज़ा विश्लेषण निकालें।")
