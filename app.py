import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基本設定
st.set_page_config(page_title="全方位四大面股市分析與 50/50 戰略儀表板", layout="wide")

st.title("📈 全方位四大面股市分析與 50/50 戰略儀表板")
st.caption("結合：①基本面健診 ｜ ②籌碼量價卡位 ｜ ③技術面進出場與停損計算 ｜ ④總體經濟雷達")

# 2. 預設監控標的群組
PORTFOLIO_CONFIG = {
    "ETF_Core": {
        "title": "🛡️ 核心大盤型 ETF (30%)",
        "tickers": ["006208.TW", "VOO"],
        "desc": "追蹤整體市場經濟成長"
    },
    "ETF_Satellite": {
        "title": "🚀 趨勢主題型 ETF (20%)",
        "tickers": ["QQQ", "00830.TW"],
        "desc": "聚焦科技與半導體高成長趨勢"
    },
    "Stock_Core": {
        "title": "🏰 護城河龍頭個股 (30%)",
        "tickers": ["2330.TW", "MSFT", "2059.TW", "3293.TW"],
        "desc": "高技術壁壘與高 ROE 龍頭"
    },
    "Stock_Growth": {
        "title": "⚡ 高動能黑馬個股 (20%)",
        "tickers": ["NVDA", "2317.TW", "3661.TW", "2357.TW"],
        "desc": "站在 AI 與算力風口之高成長企業"
    }
}

MACRO_TICKERS = {
    "^SOX": "費城半導體指數 (半導體風向球)",
    "TWD=X": "美元/台幣 (外資動向)",
    "^TNX": "美國10年期公債殖利率 (估值錨)"
}

# 3. 數據抓取與指標計算 (結合籌碼量價與箱型)
@st.cache_data(ttl=600)
def fetch_stock_history(tickers, period="1y"):
    data_dict = {}
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period=period)
            if not df.empty and len(df) >= 60:
                # 均線
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['MA60'] = df['Close'].rolling(window=60).mean()
                df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
                
                # RSI (14)
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # 箱型頂底 (過去 20 日最高/最低)
                df['Box_High_20'] = df['High'].shift(1).rolling(20).max()
                df['Box_Low_20'] = df['Low'].shift(1).rolling(20).min()
                
                data_dict[ticker] = df
        except Exception:
            pass
    return data_dict

@st.cache_data(ttl=3600)
def fetch_fundamental_info(tickers):
    fundamental_list = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            name = info.get("shortName", info.get("longName", ticker))
            gross_margin = info.get("grossMargins", None)
            roe = info.get("returnOnEquity", None)
            rev_growth = info.get("revenueGrowth", None)
            pe = info.get("trailingPE", None)
            
            gm_pct = gross_margin * 100 if gross_margin is not None else np.nan
            roe_pct = roe * 100 if roe is not None else np.nan
            rev_pct = rev_growth * 100 if rev_growth is not None else np.nan
            
            fundamental_list.append({
                "代碼": ticker, "名稱": name,
                "毛利率 (%)": round(gm_pct, 2) if not np.isnan(gm_pct) else "N/A",
                "ROE (%)": round(roe_pct, 2) if not np.isnan(roe_pct) else "N/A",
                "營收成長率 (%)": round(rev_pct, 2) if not np.isnan(rev_pct) else "N/A",
                "本益比 (PE)": round(pe, 2) if pe is not None else "N/A"
            })
        except Exception:
            pass
    return pd.DataFrame(fundamental_list)

# 收集所有股票
all_tickers = []
for group in PORTFOLIO_CONFIG.values():
    all_tickers.extend(group["tickers"])
all_tickers = list(dict.fromkeys(all_tickers))

with st.spinner("更新即時行情、籌碼量價與技術面數據中..."):
    stock_data = fetch_stock_history(all_tickers)
    macro_data = fetch_stock_history(list(MACRO_TICKERS.keys()))

# 4. 頁籤規劃 (包含四大面分析)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 50/50 總覽", 
    "🏢 ① 基本面健診", 
    "💰 ② 籌碼與主力卡位", 
    "🎯 ③ 技術面進出場/停損計算", 
    "🌐 ④ 總體經濟雷達"
])

# ==========================================
# TAB 1: 50/50 配置與即時總覽
# ==========================================
with tab1:
    st.subheader("📌 50/50 雙軌策略標的監視看板")
    for group_key, group_info in PORTFOLIO_CONFIG.items():
        st.markdown(f"#### {group_info['title']}")
        cols = st.columns(len(group_info["tickers"]))
        for idx, ticker in enumerate(group_info["tickers"]):
            with cols[idx]:
                if ticker in stock_data and not stock_data[ticker].empty:
                    df = stock_data[ticker]
                    latest = df.iloc[-1]
                    prev = df.iloc[-2]
                    price = latest['Close']
                    change = price - prev['Close']
                    pct = (change / prev['Close']) * 100
                    
                    st.metric(label=f"{ticker}", value=f"{price:.2f}", delta=f"{change:+.2f} ({pct:+.2f}%)")
                    st.write(f"• **20MA**: {latest['MA20']:.2f}")
        st.markdown("---")

# ==========================================
# TAB 2: ① 基本面健診
# ==========================================
with tab2:
    st.subheader("🏢 ① 基本面護城河健診")
    individual_stocks = [t for t in all_tickers if not (t.startswith("00") or t in ["VOO", "QQQ"])]
    df_fundamental = fetch_fundamental_info(individual_stocks)
    if not df_fundamental.empty:
        st.dataframe(df_fundamental, use_container_width=True, hide_index=True)

# ==========================================
# TAB 3: ② 籌碼與主力卡位雷達
# ==========================================
with tab3:
    st.subheader("💰 ② 籌碼面量價與主力卡位分析")
    st.markdown("""
    **籌碼卡位判定法則**：
    1. **攻擊型（爆量衝刺）**：當日成交量 > 20日均量 1.5 倍，代表法人/主力真金白銀進場推升。
    2. **洗盤型（縮量整理）**：成交量 < 20日均量 0.7 倍，代表籌碼鎖定、主力未離場。
    """)
    
    chip_analysis_list = []
    for ticker in all_tickers:
        if ticker in stock_data and not stock_data[ticker].empty:
            df = stock_data[ticker]
            latest = df.iloc[-1]
            vol_ratio = latest['Volume'] / latest['Vol_MA20'] if latest['Vol_MA20'] > 0 else 1.0
            
            # 籌碼動能標籤
            if vol_ratio >= 1.5 and latest['Close'] > latest['Open']:
                chip_status = "🔥 主力強勢攻堅 (爆量大買)"
            elif vol_ratio >= 1.2:
                chip_status = "🟩 資金持續進駐"
            elif vol_ratio <= 0.7:
                chip_status = "💤 籌碼沉澱洗盤 (縮量)"
            else:
                chip_status = "⚪ 量能平穩"
                
            chip_analysis_list.append({
                "標的代碼": ticker,
                "最新價": round(latest['Close'], 2),
                "當日成交量": int(latest['Volume']),
                "20日均量": int(latest['Vol_MA20']),
                "量能放大倍數": f"{vol_ratio:.2f} 倍",
                "籌碼與主力動態": chip_status
            })
            
    st.dataframe(pd.DataFrame(chip_analysis_list), use_container_width=True, hide_index=True)

# ==========================================
# TAB 4: ③ 技術面進出場與停損價計算機
# ==========================================
with tab4:
    st.subheader("🎯 ③ 技術面：箱型突破/20MA回測與進出場點計算機")
    st.markdown("結合技術面位階，自動計算**建議進場點、停損點（破20MA -3%）與停利目標（風報比 2:1）**。")
    
    selected_ticker = st.selectbox("選擇要評估策略的股票/ETF", all_tickers, index=2)
    
    if selected_ticker in stock_data and not stock_data[selected_ticker].empty:
        df = stock_data[selected_ticker]
        latest = df.iloc[-1]
        
        price = latest['Close']
        ma20 = latest['MA20']
        box_high = latest['Box_High_20']
        box_low = latest['Box_Low_20']
        
        # 1. 型態訊號判斷
        is_breakout = price > box_high
        is_pullback_ma20 = abs(price - ma20) / ma20 <= 0.02 # 距離 20MA 2% 以內
        
        if is_breakout:
            pattern_label = "🚀 突破型態：帶量突破近20日箱型高點！(適合追價/需籌碼配合)"
            entry_price = price
        elif is_pullback_ma20:
            pattern_label = "🎯 回測型態：回測 20MA (月線) 尋求支撐！(適合低吸)"
            entry_price = ma20
        else:
            pattern_label = "📍 箱型內整理位階"
            entry_price = price
            
        # 2. 自動計算停損與停利 (風報比 2:1)
        stop_loss_price = ma20 * 0.97 # 跌破 20MA 往下 3% 硬停損
        risk = entry_price - stop_loss_price
        target_profit_price = entry_price + (risk * 2.0) if risk > 0 else entry_price * 1.1
        
        # 顯示策略資訊卡
        st.info(f"**目前型態診斷**：{pattern_label}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("建議參考進場價", f"{entry_price:.2f} 元")
        c2.metric("嚴格停損價 (破20MA-3%)", f"{stop_loss_price:.2f} 元", f"-{((entry_price-stop_loss_price)/entry_price)*100:.1f}%")
        c3.metric("建議停利價 (風報比2:1)", f"{target_profit_price:.2f} 元", f"+{((target_profit_price-entry_price)/entry_price)*100:.1f}%")
        c4.metric("近20日箱型區間", f"{box_low:.2f} ~ {box_high:.2f}")
        
        # 繪製 K 線與箱型/停損線
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.8])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name="20MA (月線)"), row=1, col=1)
        
        # 畫出停損線與箱頂線
        fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="red", annotation_text="停損點", row=1, col=1)
        fig.add_hline(y=box_high, line_dash="dot", line_color="green", annotation_text="20日箱頂", row=1, col=1)
        
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color='blue'), row=2, col=1)
        fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 5: ④ 總體經濟雷達
# ==========================================
with tab5:
    st.subheader("🌐 ④ 總體經濟與產業風口雷達")
    col_m1, col_m2 = st.columns(2)
    for idx, (m_ticker, m_name) in enumerate(MACRO_TICKERS.items()):
        with (col_m1 if idx % 2 == 0 else col_m2):
            if m_ticker in macro_data and not macro_data[m_ticker].empty:
                m_df = macro_data[m_ticker]
                m_latest = m_df.iloc[-1]['Close']
                st.metric(label=f"{m_name} (`{m_ticker}`)", value=f"{m_latest:.2f}")
