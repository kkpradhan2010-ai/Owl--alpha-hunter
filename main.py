import time
import json
import urllib.request
import xml.etree.ElementTree as ET
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st

BOT_TOKEN = "8942257131:AAGSFvdiXFq5_y_kwKNYfnCSNb28l1JgIiA"
CHAT_ID = "8574214847"

# स्टॉक और उनके संबंधित सेक्टोरल इंडेक्स मैपिंग
STOCK_METADATA = {
    "RELIANCE.NS": "^CNXENERGY", "HDFCBANK.NS": "^NSEBANK", "ICICIBANK.NS": "^NSEBANK",
    "TCS.NS": "^CNXIT", "INFY.NS": "^CNXIT", "BHARTIARTL.NS": "^NSEI",
    "SBIN.NS": "^NSEBANK", "ITC.NS": "^CNXFMCG", "LT.NS": "^CNXINFRA",
    "AXISBANK.NS": "^NSEBANK", "KOTAKBANK.NS": "^NSEBANK", "M&M.NS": "^CNXAUTO",
    "HINDUNILVR.NS": "^CNXFMCG", "SUNPHARMA.NS": "^CNXPHARMA", "MARUTI.NS": "^CNXAUTO",
    "TITAN.NS": "^CNXCONSUM", "ADANIPORTS.NS": "^CNXINFRA", "NTPC.NS": "^CNXENERGY",
    "POWERGRID.NS": "^CNXENERGY", "BAJFINANCE.NS": "^CNXFINANCE", "BAJAJFINSV.NS": "^CNXFINANCE",
    "HCLTECH.NS": "^CNXIT", "WIPRO.NS": "^CNXIT", "ULTRACEMCO.NS": "^CNXINFRA",
    "ASIANPAINT.NS": "^CNXCONSUM", "TATASTEEL.NS": "^CNXMETAL", "JSWSTEEL.NS": "^CNXMETAL",
    "ONGC.NS": "^CNXENERGY", "COALINDIA.NS": "^CNXENERGY", "ADANIENT.NS": "^NSEI",
    "TATAMOTORS.NS": "^CNXAUTO", "HINDALCO.NS": "^CNXMETAL", "CIPLA.NS": "^CNXPHARMA",
    "DRREDDY.NS": "^CNXPHARMA", "EICHERMOT.NS": "^CNXAUTO", "DIVISLAB.NS": "^CNXPHARMA",
    "HEROMOTOCO.NS": "^CNXAUTO", "TRENT.NS": "^CNXCONSUM", "BEL.NS": "^NSEI",
    "HAL.NS": "^NSEI", "DLF.NS": "^CNXREALTY", "SIEMENS.NS": "^CNXINFRA"
}

WEIGHTS = {
    "technical": 0.28,
    "volume":    0.22,
    "momentum":  0.20,
    "news":      0.15,
    "sector":    0.15
}

POSITIVE_NEWS = [
    "order win", "large order", "new order", "contract", "profit rises",
    "profit growth", "revenue growth", "earnings beat", "upgrade",
    "acquisition", "buyback", "dividend", "expansion", "partnership"
]

NEGATIVE_NEWS = [
    "fraud", "investigation", "default", "downgrade", "resignation",
    "pledge", "penalty", "fine", "lawsuit", "regulatory action",
    "profit falls", "revenue falls", "earnings miss", "cancelled"
]

def limit_score(val):
    return max(-100, min(100, float(val)))

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception:
        pass

def get_live_news_score(symbol_clean: str):
    try:
        query = urllib.parse.quote(f"{symbol_clean} share news")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        
        headlines = []
        for item in root.findall('.//item')[:6]:
            title = item.find('title')
            if title is not None and title.text:
                headlines.append(title.text.lower())
        
        score = 0
        matched = []
        for text in headlines:
            for w in POSITIVE_NEWS:
                if w in text:
                    score += 25
                    matched.append(w)
            for w in NEGATIVE_NEWS:
                if w in text:
                    score -= 25
                    matched.append(f"risk:{w}")
        return limit_score(score), matched[:3]
    except Exception:
        return 0, []

def analyze_stock_multi_factor(symbol: str, sector_sym: str):
    try:
        # Stock Data
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d")
        if df.empty or len(df) < 35:
            return None

        close = df["Close"]
        vol = df["Volume"]
        curr_price = round(close.iloc[-1], 2)

        # 1. Technical
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        prev_high = close.shift(1).rolling(20).max().iloc[-1]

        t_score = 0
        if curr_price > ema20: t_score += 35
        else: t_score -= 35
        if ema20 > ema50: t_score += 35
        else: t_score -= 35
        if curr_price >= prev_high * 0.985: t_score += 30

        # 2. Volume Surge
        avg_vol = vol.rolling(20).mean().iloc[-1]
        vol_ratio = vol.iloc[-1] / (avg_vol + 1e-6)
        v_score = (vol_ratio - 1.0) * 80

        # 3. Momentum (RSI)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        m_score = (rsi - 50) * 2.5
        if rsi > 78: m_score -= 40

        # 4. Sector Relative Strength (5-day return comparison)
        sec_score = 0
        try:
            sec_df = yf.Ticker(sector_sym).history(period="10d")
            if not sec_df.empty and len(sec_df) >= 5:
                stock_ret = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                sec_ret = (sec_df["Close"].iloc[-1] / sec_df["Close"].iloc[-5] - 1) * 100
                rel_strength = stock_ret - sec_ret
                sec_score = limit_score(rel_strength * 12)
        except Exception:
            sec_score = 0

        # 5. Live News Score
        sym_clean = symbol.replace(".NS", "")
        n_score, news_tags = get_live_news_score(sym_clean)

        # Multi-Factor Weighted Calculation
        factors = {
            "technical": limit_score(t_score),
            "volume": limit_score(v_score),
            "momentum": limit_score(m_score),
            "news": limit_score(n_score),
            "sector": limit_score(sec_score)
        }

        final_score = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS)
        final_score = round(limit_score(final_score), 1)

        # False Signal Filter
        bearish_factors = sum(1 for v in factors.values() if v < -15)
        if final_score >= 38 and bearish_factors >= 2:
            return None  # Conflicting signals trap filter

        # ATR calculation for targets
        tr = pd.concat([
            df['High'] - df['Low'],
            (df['High'] - df['Close'].shift(1)).abs(),
            (df['Low'] - df['Close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        if pd.isna(atr): atr = curr_price * 0.02

        if final_score >= 40 and factors["technical"] > 0:
            return {
                "Rank": "",
                "Stock": sym_clean,
                "Score": final_score,
                "Price (₹)": curr_price,
                "Target 1 (₹)": round(curr_price + (1.5 * atr), 2),
                "Target 2 (₹)": round(curr_price + (2.5 * atr), 2),
                "Stop Loss (₹)": round(curr_price - (1.2 * atr), 2),
                "Vol Surge": f"{vol_ratio:.1f}x",
                "Sector RS": f"{sec_score:+.1f}",
                "News Factor": f"{n_score:+.0f}"
            }
        return None
    except Exception:
        return None

# Streamlit UI
st.set_page_config(page_title="AI Multi-Factor Alpha Hunter", page_icon="🎯", layout="wide")
st.title("🎯 Multi-Factor Stock Scanner (Live Technical + Sector + News)")
st.caption("24/7 Multi-Engine Stock Screening System")

if "picks" not in st.session_state:
    st.session_state.picks = []

col1, col2 = st.columns(2)
col1.metric("Status", "ONLINE 🟢")
col2.metric("High-Probability Setups", len(st.session_state.picks))

if st.button("🚀 Run Multi-Factor AI Scan"):
    results = []
    with st.spinner("तकनीकी डेटा, सेक्टोरल मजबूती और लाइव न्यूज़ स्कैन हो रही है..."):
        for sym, sec in STOCK_METADATA.items():
            res = analyze_stock_multi_factor(sym, sec)
            if res:
                results.append(res)
            time.sleep(0.15)
        
        results.sort(key=lambda x: x["Score"], reverse=True)
        top_picks = results[:5]
        for idx, item in enumerate(top_picks, 1):
            item["Rank"] = f"#{idx}"
        
        st.session_state.picks = top_picks
    st.rerun()

st.subheader("⚡ Top 3-5 High-Conviction Setups")
if st.session_state.picks:
    st.dataframe(pd.DataFrame(st.session_state.picks), use_container_width=True)
else:
    st.info("सिस्टम तैयार है। '🚀 Run Multi-Factor AI Scan' बटन दबाएँ।")
