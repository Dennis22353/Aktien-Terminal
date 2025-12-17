import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import urllib.parse
import requests
import json
import os
import numpy as np
import math

# --- KONFIGURATION ---
st.set_page_config(
    page_title="Investment Terminal Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: PROFESSIONAL REPORT STYLE ---
st.markdown("""
<style>
    /* Global Clean Look */
    .stApp { background-color: #f8f9fa; color: #212529; font-family: 'Inter', 'Helvetica Neue', sans-serif; }
    
    /* Header Card */
    .header-card {
        background: white; padding: 25px; border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px;
        border-left: 6px solid #2563eb;
    }
    
    /* Scorecard Container - Die 4 Säulen */
    .score-box {
        background: white; padding: 20px; border-radius: 10px;
        border: 1px solid #e9ecef; text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        height: 100%;
    }
    .score-title { font-size: 0.85rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .score-val { font-size: 2.2rem; font-weight: 800; color: #0f172a; }
    .score-bar-bg { height: 8px; background: #f1f5f9; border-radius: 4px; margin-top: 12px; overflow: hidden; }
    .score-bar-fill { height: 100%; border-radius: 4px; transition: width 0.8s ease-in-out; }
    
    /* Verdict Badge */
    .verdict-box {
        text-align: center; padding: 25px; background: #1e293b; color: white;
        border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .verdict-label { font-size: 0.9rem; opacity: 0.8; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px; }
    .verdict-text { font-size: 2.8rem; font-weight: 900; letter-spacing: 1px; margin: 0; }
    
    /* KI Erklärung Box */
    .ai-summary-box {
        background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 25px; margin-bottom: 25px; color: #1e293b; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #6366f1;
    }
    .ai-summary-box h4 { color: #4338ca; margin-top: 0; font-size: 1.2rem; margin-bottom: 15px; }
    
    /* Farben */
    .bg-green { background-color: #10b981; }
    .bg-red { background-color: #ef4444; }
    .bg-orange { background-color: #f59e0b; }
    .bg-blue { background-color: #3b82f6; }
    
    /* Tabs */
    div[data-baseweb="tab-list"] { gap: 10px; background: white; padding: 10px; border-radius: 8px; border: 1px solid #e9ecef; }
    div[data-baseweb="tab"] { height: 50px; border-radius: 6px; font-weight: 600; border: none; background: transparent; }
    div[data-baseweb="tab"][aria-selected="true"] { background: #2563eb; color: white; }
    
    /* Calc Box */
    .calc-box {
        background: #f8fafc; padding: 20px; border-radius: 10px;
        border: 1px solid #e2e8f0; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- UTILS & HELPERS ---

def get_eur_rate(from_currency):
    """Holt den aktuellen Wechselkurs zu Euro."""
    if from_currency == "EUR" or not from_currency: return 1.0
    pairs = {"USD": "EUR=X", "GBP": "GBPEUR=X", "CHF": "CHFEUR=X", "JPY": "JPYEUR=X", "AUD": "AUDEUR=X"}
    ticker = pairs.get(from_currency)
    if not ticker: return 1.0
    try:
        fx = yf.Ticker(ticker)
        rate = fx.fast_info.last_price
        if not rate:
            h = fx.history(period="1d")
            rate = h['Close'].iloc[-1]
        return float(rate)
    except: return 1.0

def get_ticker_symbol(query):
    query = query.strip().upper()
    manual = {
        "BAYER": "BAYN.DE", "BASF": "BAS.DE", "ALLIANZ": "ALV.DE", "SAP": "SAP.DE", "SIEMENS": "SIE.DE",
        "VW": "VOW3.DE", "MERCEDES": "MBG.DE", "BMW": "BMW.DE", "DT TELEKOM": "DTE.DE", "INFINEON": "IFX.DE",
        "RHEINMETALL": "RHM.DE", "VONOVIA": "VNA.DE", "ADIDAS": "ADS.DE", "DHL": "DHL.DE", "EON": "EOAN.DE",
        "APPLE": "AAPL", "MICROSOFT": "MSFT", "NVIDIA": "NVDA", "TESLA": "TSLA", "AMAZON": "AMZN",
        "GOOGLE": "GOOGL", "META": "META", "AMD": "AMD", "INTEL": "INTC", "PALANTIR": "PLTR",
        "NOVO NORDISK": "NOVO-B.CO", "BYD": "BYDDF", "ORACLE": "ORCL", "QUANTUM": "QBTS", "DRONESHIELD": "DRO.AX"
    }
    if query in manual: return manual[query]
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=2)
        d = r.json()
        if 'quotes' in d and d['quotes']: return d['quotes'][0]['symbol']
    except: pass
    return query

def get_data(ticker):
    try:
        s = yf.Ticker(ticker)
        price = None
        try: price = float(s.fast_info.last_price); cur = s.fast_info.currency
        except: 
            h = s.history(period="1d")
            if not h.empty: price = float(h['Close'].iloc[-1]); cur = s.info.get('currency', '?')
        if price: return s, s.info, price, cur
    except: pass
    return None

def manage_watchlist(symbol, action):
    WATCHLIST_FILE = "watchlist.json"
    if not os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "w") as f: json.dump([], f)
    with open(WATCHLIST_FILE, "r") as f: wl = json.load(f)
    if action == "add" and symbol not in wl: wl.append(symbol)
    elif action == "del" and symbol in wl: wl.remove(symbol)
    with open(WATCHLIST_FILE, "w") as f: json.dump(wl, f)
    return wl

# --- CORE ANALYTICS: GEWICHTETE PROFI-ANALYSE ---

def audit_stock(info, price, history):
    # Initialisierung der deutschen Säulen
    scores = {"Qualität": 50, "Prognose": 50, "Trend": 50, "Bewertung": 50}
    reasons = {"Qualität": [], "Prognose": [], "Trend": [], "Bewertung": []}
    
    pe = info.get('trailingPE')
    f_pe = info.get('forwardPE')
    used_pe = pe if pe else f_pe
    peg = info.get('pegRatio')
    debt = info.get('debtToEquity', 0)
    margin = info.get('profitMargins', 0)
    target = info.get('targetMeanPrice')
    rec_mean = info.get('recommendationMean') # 1.0 = Strong Buy, 5.0 = Sell
    
    # 1. QUALITÄT (35%) - DIE BASIS
    q_points = 50
    if margin > 0.20: 
        q_points += 40; reasons["Qualität"].append("✅ Exzellente Gewinnmarge (>20%)")
    elif margin < 0.05: 
        q_points -= 40; reasons["Qualität"].append("❌ Schwache Profitabilität / Verlust")
    
    if debt > 150: 
        q_points -= 30; reasons["Qualität"].append("❌ Hohe Verschuldung (>150%)")
    elif debt < 60: 
        q_points += 20; reasons["Qualität"].append("✅ Solide Kapitalstruktur")
    scores["Qualität"] = q_points

    # 2. PROGNOSE & WACHSTUM (30%) - DER ZUKUNFTS-BLICK
    f_points = 50
    # Wachstumsteil
    if peg and peg > 0:
        if peg < 1.0: f_points += 20; reasons["Prognose"].append("✅ Zukunftswachstum extrem günstig (PEG)")
        elif peg > 2.5: f_points -= 20; reasons["Prognose"].append("⚠️ Wachstum sehr teuer eingepreist")
        
    # Analysten & Markt-Expertise
    if rec_mean:
        if rec_mean <= 2.2: 
            f_points += 25; reasons["Prognose"].append("🚀 Experten-Konsens: KAUFEN")
        elif rec_mean >= 3.8:
            f_points -= 45; reasons["Prognose"].append("🛑 Experten raten zur Vorsicht (Verkauf/Hold)")
            
    if target and price:
        upside = ((target - price) / price) * 100
        if upside > 20: 
            f_points += 25; reasons["Prognose"].append(f"🎯 Starkes Kursziel-Potenzial (+{upside:.0f}%)")
        elif upside < 0:
            f_points -= 50; reasons["Prognose"].append("❌ Kursziel liegt UNTER aktuellem Preis")
    scores["Prognose"] = f_points

    # 3. TREND (20%) - DAS MOMENTUM
    m_points = 50
    if history is not None and len(history) > 200:
        sma200 = history['Close'].rolling(200).mean().iloc[-1]
        if price > sma200: 
            m_points = 90; reasons["Trend"].append("✅ Stabiler Langzeittrend (Bullish)")
        else:
            m_points = 10; reasons["Trend"].append("❌ Aktie im Abwärtstrend (Bearish)")
    scores["Trend"] = m_points

    # 4. BEWERTUNG (15%) - DER PREIS-CHECK
    v_points = 50
    if used_pe:
        if used_pe < 15: v_points = 90; reasons["Bewertung"].append(f"✅ Günstige fundamentale Bewertung (KGV {used_pe:.1f})")
        elif used_pe > 80: v_points = 5; reasons["Bewertung"].append(f"❌ Extrem überhitzt (KGV {used_pe:.1f})")
        elif used_pe > 40: v_points = 20; reasons["Bewertung"].append(f"⚠️ Aktuell teuer bewertet (KGV {used_pe:.1f})")
    scores["Bewertung"] = v_points

    # Normalisierung aller Säulen auf 0-100
    for k in scores: scores[k] = max(0, min(100, scores[k]))
    
    # FINALE GEWICHTUNG (Optimiertes Modell für Realismus)
    total_score = (scores["Qualität"] * 0.35) + \
                  (scores["Prognose"] * 0.30) + \
                  (scores["Trend"] * 0.20) + \
                  (scores["Bewertung"] * 0.15)
    
    total_score = int(total_score)
    
    # ANTI-MITTELMÄSSIGKEIT FILTER (Strafpunkt für gravierende Mängel in Kernsäulen)
    if scores["Qualität"] < 25 or scores["Prognose"] < 25:
        if total_score > 40: total_score -= 15 
        
    # ENTSCHEIDUNG
    verdict = "HOLD"
    color = "#f59e0b"
    
    if total_score >= 80: verdict = "STRONG BUY"; color = "#064e3b"
    elif total_score >= 65: verdict = "KAUFEN"; color = "#10b981"
    elif total_score >= 50: verdict = "AUFSTOCKEN"; color = "#34d399"
    elif total_score <= 35: verdict = "VERKAUFEN"; color = "#ef4444"
    
    # Sonderprüfung: Value Trap
    if scores["Bewertung"] > 75 and scores["Trend"] < 30:
        verdict = "VALUE TRAP"; color = "#ef4444"; reasons["Bewertung"].append("⚠️ Achtung: Billig, aber Markt bricht weg!")

    return total_score, verdict, color, scores, reasons

# --- UI RENDERERS ---

def render_scorecard(scores, reasons):
    cols = st.columns(4)
    cats = ["Qualität", "Prognose", "Trend", "Bewertung"]
    weights = {"Qualität": "35%", "Prognose": "30%", "Trend": "20%", "Bewertung": "15%"}
    for i, cat in enumerate(cats):
        val = scores[cat]
        c_class = "bg-green" if val >= 70 else "bg-red" if val <= 35 else "bg-orange"
        with cols[i]:
            st.markdown(f"""
            <div class="score-box">
                <div class="score-title">{cat} <br><small>({weights[cat]})</small></div>
                <div class="score-val">{val}/100</div>
                <div class="score-bar-bg"><div class="score-bar-fill {c_class}" style="width: {val}%;"></div></div>
            </div>
            """, unsafe_allow_html=True)

def render_ai_fazit(verdict, score, scores, reasons):
    fazit = ""
    if "BUY" in verdict:
        fazit = f"Dieses Asset ist ein **Top-Performer ({score} Punkte)**. Die Kombination aus Zukunftsprognose und fundamentaler Substanz ist exzellent. "
    elif "VERKAUFEN" in verdict:
        fazit = f"Hier ist Vorsicht geboten. Die Aktie erreicht nur **{score} Punkte**. Die Warnsignale überwiegen die Chancen. "
    else:
        fazit = f"Das Ergebnis von **{score} Punkten** deutet auf eine neutrale Bewertung hin. Keine Eile beim Einstieg erforderlich. "

    if scores["Bewertung"] < 20: fazit += "Die Bewertung ist aktuell extrem heiß gelaufen, was das Risiko für Rücksetzer erhöht. "
    if scores["Prognose"] > 80: fazit += "Die Marktanalysten blicken sehr optimistisch in die Zukunft der kommenden 12 Monate. "

    st.markdown(f"""
    <div class="ai-summary-box">
        <h4>🤖 Strategische KI-Analyse</h4>
        <p style="line-height: 1.6;">{fazit}</p>
        <div style="font-size: 0.85rem; color: #64748b; margin-top: 15px; border-top: 1px solid #f1f5f9; padding-top: 10px;">
            <b>Wichtigste Einflussfaktoren:</b> {', '.join(reasons['Qualität'] + reasons['Prognose'] + reasons['Trend'] + reasons['Bewertung'])}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_chart(ticker, hist):
    if hist.empty: return st.error("Chart-Daten fehlen.")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], fill='tozeroy', mode='lines', line=dict(color='#2563eb', width=2.5), name='Kurs'), row=1, col=1)
    if len(hist) > 200:
        sma = hist['Close'].rolling(200).mean()
        fig.add_trace(go.Scatter(x=hist.index, y=sma, line=dict(color='#f59e0b', width=2, dash='dash'), name='200-Tage'), row=1, col=1)
    
    # Farbschema für Volumen (Grün wenn Preis gestiegen, sonst Rot)
    colors = ['#10b981' if r['Open'] <= r['Close'] else '#ef4444' for i, r in hist.iterrows()]
    fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], marker_color=colors, name='Volumen'), row=2, col=1)
    
    fig.update_layout(height=500, template="plotly_white", margin=dict(l=10,r=10,t=10,b=10), showlegend=False, xaxis_rangeslider_visible=False, hovermode="x unified")
    fig.update_yaxes(side='right', row=1, col=1)
    st.plotly_chart(fig, use_container_width=True)

# --- MAIN APP ---

c_title, c_search = st.columns([2, 1])
with c_title: st.markdown("### 🏛️ Professional Investment Audit")
with c_search: q = st.text_input("Asset Suche:", placeholder="z.B. Nvidia, Apple, DroneShield", label_visibility="collapsed")

if q:
    with st.spinner("Analysiere Markt-Daten..."):
        ticker = get_ticker_symbol(q)
        data = get_data(ticker)
        if not data and "." not in ticker: data = get_data(ticker + ".DE")
        
    if data:
        stock, info, price_raw, cur_raw = data
        rate = get_eur_rate(cur_raw)
        price_eur = price_raw * rate
        hist = stock.history(period="2y")
        
        # ANALYSE DURCHFÜHREN
        total, verdict, color, scores, reasons = audit_stock(info, price_raw, hist)
        
        # HEADER CARD
        st.markdown(f"""
        <div class="header-card">
            <div style="color:#64748b; font-weight:600; font-size:0.9rem;">{info.get('sector', 'Asset')} • {ticker} • {info.get('exchange', 'Unknown')}</div>
            <div style="display:flex; justify-content:space-between; align-items:end;">
                <div style="font-size:3rem; font-weight:800; color:#1e293b; line-height:1;">{info.get('longName')}</div>
                <div style="text-align:right;">
                    <div style="font-size:2.8rem; font-weight:700; color:#2563eb;">{price_eur:,.2f} €</div>
                    <div style="font-size:0.75rem; color:#94a3b8;">Status: {datetime.now().strftime('%H:%M:%S')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # VERDICT & SCORECARD
        c_verdict, c_chart_area = st.columns([1, 2])
        
        with c_verdict:
            st.markdown(f"""<div class="verdict-box" style="background:{color};"><div class="verdict-label">PROFI-BEWERTUNG</div><div class="verdict-text">{verdict}</div><div>Gesamt-Score: <b>{total}/100</b></div></div>""", unsafe_allow_html=True)
            
            # KI Fazit
            render_ai_fazit(verdict, total, scores, reasons)
            
            if st.button("⭐ Auf Watchlist"):
                manage_watchlist(ticker, "add")
                st.toast("Gespeichert!")

        with c_chart_area:
            render_scorecard(scores, reasons)
            
            st.markdown("##### Performance-Analyse")
            b_cols = st.columns(7)
            # Standardmäßig 1 Jahr
            if 'timeframe' not in st.session_state: st.session_state.timeframe = "1y"
            
            if b_cols[0].button("1T"): st.session_state.timeframe = "1d"
            if b_cols[1].button("1W"): st.session_state.timeframe = "5d"
            if b_cols[2].button("1M"): st.session_state.timeframe = "1mo"
            if b_cols[3].button("6M"): st.session_state.timeframe = "6mo"
            if b_cols[4].button("1J"): st.session_state.timeframe = "1y"
            if b_cols[5].button("5J"): st.session_state.timeframe = "5y"
            if b_cols[6].button("MAX"): st.session_state.timeframe = "max"
            
            # Intervall-Logik
            tf = st.session_state.timeframe
            interval = "1d"
            if tf == "1d": interval = "5m"
            elif tf == "5d": interval = "15m"
            
            hist_chart = stock.history(period=tf, interval=interval)
            render_chart(ticker, hist_chart)

        # Tabs
        t1, t2, t3 = st.tabs(["📊 DETAILS & RECHNER", "📰 NACHRICHTEN", "🏢 UNTERNEHMEN"])
        
        with t1:
            col1, col2, col3 = st.columns(3)
            col1.metric("KGV (Ist)", f"{info.get('trailingPE', 0):.1f}" if info.get('trailingPE') else "-")
            col2.metric("PEG Ratio", f"{info.get('pegRatio', 0):.2f}" if info.get('pegRatio') else "-")
            rec_val = info.get('recommendationMean')
            rec_text = "BUY" if (rec_val or 5) < 2.5 else ("HOLD" if (rec_val or 5) < 3.5 else "SELL")
            col3.metric("Experten-Votum", rec_text)
            
            st.markdown("<div class='calc-box'>", unsafe_allow_html=True)
            st.subheader("💰 Zukunfts-Rechner")
            c_inv1, c_inv2 = st.columns(2)
            with c_inv1: invest = st.number_input("Investitionssumme (€):", value=1000, step=100)
            with c_inv2: months = st.slider("Haltedauer (Monate):", 1, 60, 12)
            
            target = info.get('targetMeanPrice')
            if target:
                target_eur = target * rate
                pot = ((target_eur - price_eur) / price_eur) * (months / 12)
                end_val = invest * (1 + pot)
                diff = end_val - invest
                color_res = "green" if diff > 0 else "red"
                st.markdown(f"Zielwert nach Prognose: <b style='color:{color_res}; font-size:1.6rem;'>{end_val:,.2f} €</b> ({diff:+.2f} €)", unsafe_allow_html=True)
                st.caption(f"Grundlage: Durchschnittliches Experten-Ziel von {target_eur:.2f} €")
            else: st.info("Keine Prognose-Daten verfügbar.")
            st.markdown("</div>", unsafe_allow_html=True)

        with t2:
            news = stock.news
            if news:
                for n in news[:5]:
                    title = n.get('title')
                    link = n.get('link')
                    if title and link:
                        date_str = datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%d.%m. %H:%M')
                        st.markdown(f"**[{title}]({link})**")
                        st.caption(f"{n.get('publisher', 'News')} • {date_str}")
                        st.markdown("---")
            else: st.write("Keine aktuellen Nachrichten gefunden.")

        with t3:
            st.write(info.get('longBusinessSummary', 'Keine Beschreibung verfügbar.'))
    else:
        st.error(f"Asset '{q}' nicht gefunden. Bitte Symbol prüfen.")

else:
    st.info("Willkommen im Terminal. Gib oben ein Symbol ein, um die gewichtete Profi-Analyse inklusive Zukunfts-Check zu starten.")