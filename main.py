import time
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st

BOT_TOKEN = "8942257131:AAGSFvdiXFq5_y_kwKNYfnCSNb28l1JgIiA"
CHAT_ID = "8574214847"

# NIFTY TOP 150+ HIGH LIQUIDITY WATCHLIST
WATCHLIST_150 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS",
    "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "TITAN.NS", "M&M.NS", "TATASTEEL.NS", "ASIANPAINT.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS", "BAJAJFINSV.NS", "NTPC.NS",
    "POWERGRID.NS", "ONGC.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "JSWSTEEL.NS",
    "GRASIM.NS", "HINDUNILVR.NS", "HINDALCO.NS", "WIPRO.NS", "TECHM.NS",
    "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS", "EICHERMOT.NS", "DIVISLAB.NS",
    "BPCL.NS", "BRITANNIA.NS", "HEROMOTOCO.NS", "TATACONSUM.NS", "INDUSINDBK.NS",
    "SHRIRAMFIN.NS", "BEL.NS", "HAL.NS", "TRENT.NS", "ZOMATO.NS",
    "JIOFIN.NS", "CHOLAFIN.NS", "VEDL.NS", "DLF.NS", "VBL.NS",
    "SIEMENS.NS", "ABB.NS", "PFC.NS", "RECLTD.NS", "IOC.NS",
    "GAIL.NS", "TVSMOTOR.NS", "HAVELLS.NS", "POLYCAB.NS", "PIDILITIND.NS",
    "GODREJCP.NS", "DABUR.NS", "AMBUJACEM.NS", "BANKBARODA.NS", "PNB.NS",
    "CANBK.NS", "UNIONBANK.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS", "AUBANK.NS",
    "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS", "LTTS.NS", "LTIM.NS",
    "NAUKRI.NS", "KPITTECH.NS", "TATAELXSI.NS", "DIXON.NS", "KALYANKJIL.NS",
    "MOTHERSON.NS", "BOSCHLTD.NS", "BHARATFORG.NS", "ASHOKLEY.NS", "BALKRISIND.NS",
    "MRF.NS", "EXIDEIND.NS", "APOLLOTYRE.NS", "LUPIN.NS", "AUROPHARMA.NS",
    "ALKEM.NS", "TORNTPHARM.NS", "MANAPPURAM.NS", "MUTHOOTFIN.NS", "LICHSGFIN.NS",
    "POONAWALLA.NS", "ABCAPITAL.NS", "LICI.NS", "SBILIFE.NS", "HDFCLIFE.NS",
    "ICICIPRULI.NS", "MAXHEALTH.NS", "FORTIS.NS", "BIOCON.NS", "GLENMARK.NS",
    "VOLTAS.NS", "BLUESTARCO.NS", "CROMPTON.NS", "WHIRLPOOL.NS", "PAGEIND.NS",
    "BATAINDIA.NS", "DEVYANI.NS", "JUBLFOOD.NS", "COLPAL.NS", "MARICO.NS",
    "BERGEPAINT.NS", "KANSAINER.NS", "OBEROIRLTY.NS", "GODREJPROP.NS", "PRESTIGE.NS",
    "PHOENIXLTD.NS", "BRIGADE.NS", "CUMMINSIND.NS", "ASTRAL.NS", "SUPREMEIND.NS",
    "PIIND.NS", "UPL.NS", "COROMANDEL.NS", "DEEPAKNTR.NS", "TATACHEM.NS",
    "SRF.NS", "ATGL.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "SUZLON.NS",
    "NHPC.NS", "SJVN.NS", "IREDA.NS", "IRFC.NS", "RVNL.NS",
    "IRCON.NS", "MAZDOCK.NS", "COCHINSHIP.NS", "BDL.NS", "BHEL.NS",
    "SAIL.NS", "NMDC.NS", "NATIONALUM.NS", "JINDALSTEL.NS"
]

WEIGHTS = {
    "technical": 0.35,
    "volume":    0.25,
    "momentum":  0.20,
    "news":      0.20
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
        with urllib.request.urlopen(req, timeout=4) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        
        headlines = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title')
            if title is not None and title.text:
                headlines.append(title.text.lower())
        
        score = 0
        for text in headlines:
            for w in POSITIVE_NEWS:
                if w in text: score += 25
            for w in NEGATIVE_NEWS:
                if w in text: score -= 25
        return limit_score(score)
    except Exception:
        return 0

def quick_technical_scan(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d")
        if df.empty or len(df) < 35:
            return None

        close = df["Close"]
        vol = df["Volume"]
        curr_price = round(close.iloc[-1], 2)

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        prev_high = close.shift(1).rolling(20).max().iloc[-1]

        # सख्त फ़िल्टर: 50 EMA के नीचे वाले शेयर तुरंत बाहर
        if curr_price < ema50:
            return None

        t_score = 0
        if curr_price > ema20: t_score += 35
        else: t_score -= 20
        if ema20 > ema50: t_score += 35
        else: t_score -= 20
        if curr_price >= prev_high * 0.985: t_score += 30

        avg_vol = vol.rolling(20).mean().iloc[-1]
        vol_ratio = vol.iloc[-1] / (avg_vol + 1e-6)
        v_score = (vol_ratio - 1.0) * 80

        # वॉल्यूम कम से कम औसत के बराबर या उससे ज्यादा होना चाहिए
        if vol_ratio < 1.0:
            return None

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        if rsi > 78 or rsi < 48:
            return None

        m_score = (rsi - 50) * 2.5

        tr = pd.concat([
            df['High'] - df['Low'],
            (df['High'] - df['Close'].shift(1)).abs(),
            (df['Low'] - df['Close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        if pd.isna(atr): atr = curr_price * 0.02

        return {
            "symbol": symbol,
            "clean_symbol": symbol.replace(".NS", ""),
            "price": curr_price,
            "atr": atr,
            "vol_ratio": vol_ratio,
            "t_score": limit_score(t_score),
            "v_score": limit_score(v_score),
            "m_score": limit_score(m_score)
        }
    except Exception:
        return None

# Streamlit UI
st.set_page_config(page_title="Alpha Hunter 150", page_icon="🎯", layout="wide")
st.title("🎯 NIFTY 150+ Multi-Factor Alpha Radar")
st.caption("Auto Technical + Momentum + Volume Surge + Live News Engine")

if "picks" not in st.session_state:
    st.session_state.picks = []

col1, col2 = st.columns(2)
col1.metric("Status", "ONLINE 🟢")
col2.metric("Watchlist Monitored", f"{len(WATCHLIST_150)} Stocks")

if st.button("🚀 Run 150+ Market AI Scan"):
    stage1_candidates = []
    with st.spinner("स्टेज 1: 150 शेयरों का टेक्निकल व वॉल्यूम स्कैन हो रहा है..."):
        for sym in WATCHLIST_150:
            res = quick_technical_scan(sym)
            if res and res["t_score"] > 20:
                stage1_candidates.append(res)
            time.sleep(0.05)
    
    final_picks = []
    with st.spinner(f"स्टेज 2: टॉप {len(stage1_candidates)} शॉर्टलिस्टेड शेयरों की लाइव न्यूज़ जांच जारी है..."):
        for item in stage1_candidates:
            n_score = get_live_news_score(item["clean_symbol"])
            
            final_score = (
                item["t_score"] * WEIGHTS["technical"] +
                item["v_score"] * WEIGHTS["volume"] +
                item["m_score"] * WEIGHTS["momentum"] +
                n_score * WEIGHTS["news"]
            )
            final_score = round(limit_score(final_score), 1)

            # False Signal Trap Filter
            if n_score < -30:
                continue

            if final_score >= 40:
                p = item["price"]
                atr = item["atr"]
                final_picks.append({
                    "Rank": "",
                    "Stock": item["clean_symbol"],
                    "Score": final_score,
                    "Price (₹)": p,
                    "Target 1 (₹)": round(p + (1.5 * atr), 2),
                    "Target 2 (₹)": round(p + (2.5 * atr), 2),
                    "Stop Loss (₹)": round(p - (1.2 * atr), 2),
                    "Vol Surge": f"{item['vol_ratio']:.1f}x",
                    "News Sentiment": f"{n_score:+.0f}"
                })
            time.sleep(0.1)

    final_picks.sort(key=lambda x: x["Score"], reverse=True)
    top_5 = final_picks[:5]
    for idx, row in enumerate(top_5, 1):
        row["Rank"] = f"#{idx}"

    st.session_state.picks = top_5
    st.rerun()

st.subheader("⚡ Top 3-5 Filtered High-Conviction Trades")
if st.session_state.picks:
    st.dataframe(pd.DataFrame(st.session_state.picks), use_container_width=True)
else:
    st.info("सिस्टम तैयार है। 150+ स्टॉक्स में से बेस्ट 3-5 सेटअप्स निकालने के लिए ऊपर बटन दबाएँ।")
