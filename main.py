# stock_ai.py
# Multi-Factor NSE Stock Scanner
# News + FII/DII + Volume + Results + OI + Options
# + Technical + Sector + Corporate Events + Risk

import numpy as np
import pandas as pd
from dataclasses import dataclass


# ============================================================
# 1. 200 STOCKS
# ============================================================

STOCKS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "TCS", "INFY",
    "BHARTIARTL", "SBIN", "ITC", "LT", "AXISBANK",
    "KOTAKBANK", "M&M", "HINDUNILVR", "SUNPHARMA", "MARUTI",
    "TITAN", "ADANIPORTS", "NTPC", "POWERGRID", "BAJFINANCE",
    "BAJAJFINSV", "HCLTECH", "WIPRO", "ULTRACEMCO", "ASIANPAINT",
    "NESTLEIND", "TATASTEEL", "JSWSTEEL", "ONGC", "COALINDIA",
    "ADANIENT", "TECHM", "TATAMOTORS", "HINDALCO", "GRASIM",
    "CIPLA", "DRREDDY", "EICHERMOT", "DIVISLAB", "BRITANNIA",
    "APOLLOHOSP", "SBILIFE", "HDFCLIFE", "INDUSINDBK",
    "BAJAJ-AUTO", "HEROMOTOCO", "TRENT", "BEL", "HAL",
    "DLF", "PIDILITIND", "SIEMENS"
]

# बाद में इस list को exact 200 stocks तक बढ़ाएँ


# ============================================================
# 2. FACTOR WEIGHTS
# ============================================================

WEIGHTS = {

    "news":       0.12,
    "fii_dii":    0.08,
    "volume":     0.12,
    "delivery":   0.06,

    "results":    0.12,
    "technical":  0.12,

    "oi":         0.10,
    "options":    0.07,

    "sector":     0.05,
    "corporate":  0.06,

    "momentum":   0.06,
    "risk":       0.04
}


# ============================================================
# 3. BASIC FUNCTIONS
# ============================================================

def limit_score(value):

    return max(-100, min(100, float(value)))


def weighted_score(factors):

    total = 0

    for factor, weight in WEIGHTS.items():

        value = factors.get(factor, 0)

        total += value * weight

    return limit_score(total)


# ============================================================
# 4. TECHNICAL ANALYSIS
# ============================================================

def technical_score(df):

    close = df["close"]

    ema20 = close.ewm(span=20).mean()
    ema50 = close.ewm(span=50).mean()
    ema200 = close.ewm(span=200).mean()

    score = 0

    # Trend

    if close.iloc[-1] > ema20.iloc[-1]:
        score += 25
    else:
        score -= 25

    if ema20.iloc[-1] > ema50.iloc[-1]:
        score += 25
    else:
        score -= 25

    if ema50.iloc[-1] > ema200.iloc[-1]:
        score += 25
    else:
        score -= 25


    # 20-day breakout

    previous_high = close.shift(1).rolling(20).max().iloc[-1]
    previous_low = close.shift(1).rolling(20).min().iloc[-1]

    if close.iloc[-1] > previous_high:

        score += 25

    elif close.iloc[-1] < previous_low:

        score -= 25


    return limit_score(score)


# ============================================================
# 5. RSI / MOMENTUM
# ============================================================

def momentum_score(df):

    close = df["close"]

    delta = close.diff()

    gain = delta.clip(lower=0).rolling(14).mean()

    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    rsi_value = rsi.iloc[-1]

    score = (rsi_value - 50) * 2.5

    # बहुत ज्यादा overbought होने पर penalty

    if rsi_value > 80:
        score -= 30

    # बहुत ज्यादा oversold होने पर bounce possibility

    if rsi_value < 20:
        score += 30

    return limit_score(score)


# ============================================================
# 6. ABNORMAL VOLUME
# ============================================================

def volume_score(df):

    volume = df["volume"]

    avg_volume = volume.rolling(20).mean().iloc[-1]

    current_volume = volume.iloc[-1]

    ratio = current_volume / avg_volume

    price_change = (
        df["close"].iloc[-1] /
        df["close"].iloc[-2] - 1
    )

    score = (ratio - 1) * 100

    # Volume + price confirmation

    if ratio > 1.5:

        if price_change > 0:
            score += 25
        else:
            score -= 25

    return limit_score(score)


# ============================================================
# 7. NEWS ENGINE
# ============================================================

POSITIVE_NEWS = [

    "order win",
    "large order",
    "new order",
    "contract",
    "profit rises",
    "profit growth",
    "revenue growth",
    "earnings beat",
    "rating upgrade",
    "upgrade",
    "acquisition",
    "merger",
    "buyback",
    "dividend",
    "capacity expansion",
    "new plant",
    "production increase",
    "partnership",
    "investment"

]

NEGATIVE_NEWS = [

    "fraud",
    "investigation",
    "default",
    "downgrade",
    "rating downgrade",
    "resignation",
    "promoter pledge",
    "penalty",
    "fine",
    "lawsuit",
    "regulatory action",
    "profit falls",
    "revenue falls",
    "earnings miss",
    "order cancelled",
    "shutdown",
    "insolvency"

]


def news_score(headlines):

    score = 0

    for headline in headlines:

        text = headline.lower()

        for word in POSITIVE_NEWS:

            if word in text:
                score += 20

        for word in NEGATIVE_NEWS:

            if word in text:
                score -= 20

    return limit_score(score)


# ============================================================
# 8. FII / DII
# ============================================================

def fii_dii_score(

    fii_buy,
    fii_sell,
    dii_buy,
    dii_sell

):

    fii_net = fii_buy - fii_sell

    dii_net = dii_buy - dii_sell

    total = fii_net + dii_net

    return limit_score(total)


# ============================================================
# 9. DELIVERY
# ============================================================

def delivery_score(

    current_delivery,
    average_delivery

):

    if average_delivery == 0:

        return 0

    ratio = current_delivery / average_delivery

    return limit_score((ratio - 1) * 150)


# ============================================================
# 10. QUARTERLY RESULTS
# ============================================================

def results_score(

    revenue_growth,
    profit_growth,
    margin_change,
    eps_growth

):

    score = 0

    score += revenue_growth * 1.5

    score += profit_growth * 2

    score += margin_change * 2

    score += eps_growth * 1.5

    return limit_score(score)


# ============================================================
# 11. FUTURES OI
# ============================================================

def oi_score(

    price_change,
    oi_change

):

    # Long buildup

    if price_change > 0 and oi_change > 0:

        return 80

    # Short buildup

    if price_change < 0 and oi_change > 0:

        return -80

    # Short covering

    if price_change > 0 and oi_change < 0:

        return 60

    # Long unwinding

    if price_change < 0 and oi_change < 0:

        return -60

    return 0


# ============================================================
# 12. OPTIONS PCR
# ============================================================

def options_score(pcr):

    if pcr >= 1.30:

        return 70

    if pcr >= 1.10:

        return 40

    if pcr >= 0.90:

        return 0

    if pcr >= 0.70:

        return -40

    return -70


# ============================================================
# 13. SECTOR STRENGTH
# ============================================================

def sector_score(

    stock_return,
    sector_return

):

    relative_strength = stock_return - sector_return

    return limit_score(relative_strength * 10)


# ============================================================
# 14. CORPORATE EVENTS
# ============================================================

def corporate_score(events):

    score = 0

    for event in events:

        event = event.lower()

        if "order" in event:
            score += 25

        if "acquisition" in event:
            score += 20

        if "buyback" in event:
            score += 20

        if "dividend" in event:
            score += 15

        if "promoter selling" in event:
            score -= 25

        if "pledge increase" in event:
            score -= 35

        if "resignation" in event:
            score -= 20

        if "regulatory action" in event:
            score -= 30

    return limit_score(score)


# ============================================================
# 15. RISK
# ============================================================

def risk_score(volatility):

    if volatility < 2:

        return 80

    if volatility < 3:

        return 60

    if volatility < 4:

        return 30

    if volatility < 5:

        return 0

    if volatility < 7:

        return -40

    return -80


# ============================================================
# 16. FALSE SIGNAL FILTER
# ============================================================

def false_signal_filter(factors, final_score):

    bullish = 0
    bearish = 0

    for name in WEIGHTS:

        value = factors.get(name, 0)

        if value > 15:
            bullish += 1

        if value < -15:
            bearish += 1


    # बहुत conflicting data

    if final_score > 38 and bearish >= 4:

        return False

    if final_score < -38 and bullish >= 4:

        return False


    return True


# ============================================================
# 17. SIGNAL ENGINE
# ============================================================

def generate_signal(symbol, factors, price, atr_percent):

    score = weighted_score(factors)

    # False signal filter

    if not false_signal_filter(factors, score):

        return {

            "symbol": symbol,
            "signal": "WAIT",
            "score": round(score, 2),
            "reason": "Conflicting factors"

        }


    if score >= 38:

        signal = "BUY"

    elif score <= -38:

        signal = "SELL"

    else:

        signal = "WAIT"


    # Model strength — probability नहीं

    confidence = min(

        99,

        50 + abs(score) * 0.45

    )


    # ATR based SL / targets

    atr = max(atr_percent, 0.5) / 100


    if signal == "BUY":

        stop_loss = price * (1 - atr * 1.2)

        target1 = price * (1 + atr * 1.5)

        target2 = price * (1 + atr * 2.5)


    elif signal == "SELL":

        stop_loss = price * (1 + atr * 1.2)

        target1 = price * (1 - atr * 1.5)

        target2 = price * (1 - atr * 2.5)


    else:

        stop_loss = None
        target1 = None
        target2 = None


    # Main reasons

    sorted_factors = sorted(

        factors.items(),

        key=lambda x: abs(x[1]),

        reverse=True

    )


    reasons = []

    for name, value in sorted_factors[:5]:

        if value >= 15:

            reasons.append(

                f"{name}: positive"

            )

        elif value <= -15:

            reasons.append(

                f"{name}: negative"

            )


    return {

        "symbol": symbol,

        "signal": signal,

        "score": round(score, 2),

        "confidence": round(confidence, 2),

        "price": round(price, 2),

        "stop_loss": round(stop_loss, 2)
            if stop_loss else None,

        "target1": round(target1, 2)
            if target1 else None,

        "target2": round(target2, 2)
            if target2 else None,

        "reasons": ", ".join(reasons)

    }


# ============================================================
# 18. SCAN ALL STOCKS
# ============================================================

def scan_market(stock_data):

    results = []

    for symbol in STOCKS:

        if symbol not in stock_data:

            continue

        data = stock_data[symbol]

        factors = {

            "news":
                data.get("news", 0),

            "fii_dii":
                data.get("fii_dii", 0),

            "volume":
                data.get("volume", 0),

            "delivery":
                data.get("delivery", 0),

            "results":
                data.get("results", 0),

            "technical":
                data.get("technical", 0),

            "oi":
                data.get("oi", 0),

            "options":
                data.get("options", 0),

            "sector":
                data.get("sector", 0),

            "corporate":
                data.get("corporate", 0),

            "momentum":
                data.get("momentum", 0),

            "risk":
                data.get("risk", 0)

        }


        result = generate_signal(

            symbol,

            factors,

            data["price"],

            data.get("atr_percent", 3)

        )

        results.append(result)


    df = pd.DataFrame(results)

    return df


# ============================================================
# 19. TOP 2-3 STOCKS
# ============================================================

def top_signals(df):

    buys = df[

        df["signal"] == "BUY"

    ].sort_values(

        "score",

        ascending=False

    ).head(3)


    sells = df[

        df["signal"] == "SELL"

    ].sort_values(

        "score",

        ascending=True

    ).head(3)


    return buys, sells


# ============================================================
# 20. EXAMPLE
# ============================================================

if __name__ == "__main__":

    # यह केवल structure test है।
    # यहाँ बाद में live API का data आएगा।

    stock_data = {

        "RELIANCE": {

            "price": 1400,

            "atr_percent": 2.5,

            "news": 70,

            "fii_dii": 40,

            "volume": 75,

            "delivery": 50,

            "results": 65,

            "technical": 80,

            "oi": 70,

            "options": 50,

            "sector": 60,

            "corporate": 40,

            "momentum": 65,

            "risk": 40

        },

        "TCS": {

            "price": 3000,

            "atr_percent": 2.2,

            "news": -20,

            "fii_dii": -10,

            "volume": 40,

            "delivery": 20,

            "results": -30,

            "technical": -45,

            "oi": -60,

            "options": -30,

            "sector": -20,

            "corporate": -10,

            "momentum": -40,

            "risk": 30

        }

    }


    results = scan_market(stock_data)


    buys, sells = top_signals(results)


    print("\n==============================")
    print("TOP BUY")
    print("==============================")

    print(

        buys.to_string(index=False)

    )


    print("\n==============================")
    print("TOP SELL")
    print("==============================")

    print(

        sells.to_string(index=False)

    )


    results.to_csv(

        "stock_signals.csv",

        index=False

    )

    print(

        "\nResults saved to stock_signals.csv"

    )
