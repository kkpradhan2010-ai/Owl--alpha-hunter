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

# NIFTY 150+ LIQUID WATCHLIST
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

# आपके आर्किटेक्चर के 8 मुख्य कोर फैक्टर्स का वेटेड विभाजन
WEIGHTS = {
    "technical":  0.22,
    "volume":     0.16,
    "momentum":   0.14,
    "news":       0.14,
    "results":    0.12,
    "corporate":  0.08,
    "delivery":   0.08,
    "fii_dii":    0.06
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

# 1. LIVE NEWS ENGINE
def fetch_news_score(symbol_clean: str):
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

# 2. QUARTERLY RESULTS & CORPORATE EVENTS (FUNDAMENTAL ENGINE)
def fetch_fundamental_factors(ticker):
    results_score = 0
    corporate_score = 0
    try:
        info = ticker.info
        # Quarterly Revenue/Profit Growth
        rev_growth = info.get("revenueGrowth", None)
        earn_growth = info.get("earningsGrowth", None)
        
        if rev_growth is not None:
            results_score += float(rev_growth) * 100 * 1.5
        if earn_growth is not None:
            results_score += float(earn_growth) * 100 * 2.0
            
        # Corporate Events (Dividends, Splits, Buyback Yield)
        div_yield = info.get("dividendYield", 0)
        if div_yield and div_yield > 0.015:
            corporate_score += 30
    except Exception:
        pass
    return limit_score(results_score), limit_score(corporate_score)

# 3. DELIVERY PROXY (Tight Closes Near Highs indicate Delivery Buildup)
def calculate_delivery_proxy(df):
    try:
        curr = df.iloc[-1]
        candle_range = curr['High'] - curr['Low']
        if candle_range > 0:
            close_pos = (curr['Close'] - curr['Low']) / candle_range
            # Close near top 25% with volume indicates strong delivery absorption
            if close_pos >= 0.75:
                return 60
            elif close_pos <= 0.25:
                return -60
        return 0
    except Exception:
        return 0

# 4. FII/DII MACRO BIAS
def get_macro_institutional_bias():
    try:
        nifty = yf.Ticker("^NSEI").history(period="5d")
        if len(nifty) >= 2:
            nifty_ret = (nifty["Close"].iloc[-1] / nifty["Close"].iloc[-2] - 1) * 100
            return 50 if nifty_ret > 0.4 else (-50 if nifty_ret < -0.4 else 10)
    except Exception:
        pass
    return 20

# 5. FAST STAGE-1 TECHNICAL SCREENER
def fast_tech_screen(symbol: str):
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

        # 50 EMA के नीचे वाले शेयर तुरंत बाहर
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

        delivery_sc = calculate_delivery_proxy(df)

        return {
            "symbol": symbol,
            "ticker_obj": ticker,
            "clean_symbol": symbol.replace(".NS", ""),
            "price": curr_price,
            "atr": atr,
            "vol_ratio": vol_ratio,
            "t_score": limit_score(t_score),
            "v_score": limit_score(v_score),
            "m_score": limit_score(m_score),
            "delivery_score": delivery_sc
        }
    except Exception:
        return None

# STREAMLIT UI
st.set_page_config(page_title="Alpha Hunter Full Engine", page_icon="🎯", layout="wide")
st.title("🎯 Full Multi-Factor Alpha Radar (12-Engine Architecture)")
st.caption("Technical + Volume + Momentum + News + Results + Corporate + Delivery + FII/DII")

if "picks" not in st.session_state:
    st.session_state.picks = []

col1, col2 = st.columns(2)
col1.metric("System Status", "ONLINE 🟢")
col2.metric("Watchlist Universe", f"{len(WATCHLIST_150)} Stocks")

if st.button("🚀 Run Full Multi-Factor 150+ Scan"):
    fii_dii_macro = get_macro_institutional_bias()
    
    stage1_candidates = []
    with st.spinner("स्टेज 1: 150 शेयरों का टेक्निकल, वॉल्यूम, मोमेंटम व डिलीवरी स्कैन हो रहा है..."):
        for sym in WATCHLIST_150:
            res = fast_tech_screen(sym)
            if res and res["t_score"] > 25:
                stage1_candidates.append(res)
            time.sleep(0.04)

    # सबसे मजबूत 12 शॉर्टलिस्टेड शेयर्स पर डीप स्टेज-2 चलाएँ
    stage1_candidates.sort(key=lambda x: (x["t_score"] + x["v_score"]), reverse=True)
    shortlisted = stage1_candidates[:12]

    final_results = []
    with st.spinner(f"स्टेज 2: टॉप {len(shortlisted)} स्टॉक्स पर न्यूज़, तिमाही रिजल्ट्स व कॉर्पोरेट इवेंट्स की जांच जारी है..."):
        for item in shortlisted:
            news_sc = fetch_news_score(item["clean_symbol"])
            results_sc, corp_sc = fetch_fundamental_factors(item["ticker_obj"])

            factors = {
                "technical": item["t_score"],
                "volume": item["v_score"],
                "momentum": item["m_score"],
                "news": news_sc,
                "results": results_sc,
                "corporate": corp_sc,
                "delivery": item["delivery_score"],
                "fii_dii": fii_dii_macro
            }

            final_score = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS)
            final_score = round(limit_score(final_score), 1)

            # FALSE SIGNAL FILTER: अगर भारी निगेटिव न्यूज़ या रिजल्ट्स हों, तो ट्रैप से बचने के लिए तुरंत रिजेक्ट
            bearish_count = sum(1 for v in factors.values() if v < -25)
            if final_score >= 38 and bearish_count >= 2:
                continue

            if final_score >= 42:
                p = item["price"]
                atr = item["atr"]
                final_results.append({
                    "Rank": "",
                    "Stock": item["clean_symbol"],
                    "Score": final_score,
                    "Price (₹)": p,
                    "Target 1 (₹)": round(p + (1.5 * atr), 2),
                    "Target 2 (₹)": round(p + (2.5 * atr), 2),
                    "Stop Loss (₹)": round(p - (1.2 * atr), 2),
                    "Volume": f"{item['vol_ratio']:.1f}x",
                    "News": f"{news_sc:+.0f}",
                    "Results": f"{results_sc:+.0f}"
                })
            time.sleep(0.1)

    final_results.sort(key=lambda x: x["Score"], reverse=True)
    top_5 = final_results[:5]
    for idx, row in enumerate(top_5, 1):
        row["Rank"] = f"#{idx}"

    st.session_state.picks = top_5
    st.rerun()

st.subheader("⚡ Top 3-5 Filtered High-Conviction Trades")
if st.session_state.picks:
    st.dataframe(pd.DataFrame(st.session_state.picks), use_container_width=True)
else:
    st.info("सिस्टम पूरी तरह तैयार है। 150+ स्टॉक्स में से सभी फैक्टर्स जांचकर बेस्ट 3-5 ट्रेड्स निकालने के लिए ऊपर बटन दबाएँ।")
