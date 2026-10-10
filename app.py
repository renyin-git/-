import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基本設定
st.set_page_config(page_title="50/50 雙軌資產追蹤與股票篩選儀表板", layout="wide")

st.title("📈 50/50 雙軌資產追蹤與股票篩選儀表板")
st.caption("結合 50% ETF 穩健底盤 + 50% 護城河個股超額報酬策略")

# 2. 策略預設標的清單（可隨時修改擴充）
PORTFOLIO_CONFIG = {
    "ETF_Core": {
        "title": "🛡️ 核心大盤型 ETF (30%)",
        "tickers": ["006208.TW", "VOO"],
        "desc": "追蹤整體市場經濟成長，自動淘汰衰退企業"
    },
    "ETF_Satellite": {
        "title": "🚀 趨勢主題型 ETF (20%)",
        "tickers": ["QQQ", "00830.TW"],
        "desc": "聚焦科技與半導體高成長趨勢"
    },
    "Stock_Core": {
        "title": "🏰 護城河龍頭個股 (30%)",
        "tickers": ["2330.TW", "MSFT"],
        "desc": "具備高技術壁壘、定價權與穩定高獲利能力"
    },
    "Stock_Growth": {
        "title": "⚡ 高動能黑馬個股 (20%)",
        "tickers": ["NVDA", "2317.TW"],
        "desc": "站在 AI/算力/伺服器強勁風口的高成長企業"
    }
}

# 3. 數據載入與指標計算函式
@st.cache_data(ttl=300)
def fetch_stock_data(tickers, period="1y"):
    """批次抓取股票資料並計算 MA 與 RSI"""
    data_dict = {}
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period=period)
            if not df.empty:
                # 計算 20MA, 60MA
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['MA60'] = df['Close'].rolling(window=60).mean()
                
                # 計算 RSI (14)
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                data_dict[ticker] = df
        except Exception as e:
            st.warning(f"無法載入 {ticker} 資料: {e}")
    return data_dict

# 收集所有需要監控的標的
all_tickers = []
for group in PORTFOLIO_CONFIG.values():
    all_tickers.extend(group["tickers"])

with st.spinner("正從 Yahoo Finance 抓取最新行情與技術數據..."):
    stock_data = fetch_stock_data(all_tickers)

# 4. 頁籤規劃
tab1, tab2, tab3 = st.tabs(["📊 50/50 配置與行情總覽", "🔍 單一標的深度技術分析", "💡 選股策略與篩選標準說明"])

# ==========================================
# TAB 1: 50/50 配置與行情總覽
# ==========================================
with tab1:
    st.subheader("📌 雙軌策略標的即時監視看板")
    
    # 建立多欄位卡片展示
    for group_key, group_info in PORTFOLIO_CONFIG.items():
        st.markdown(f"#### {group_info['title']}")
        st.caption(group_info['desc'])
        
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
                    ma20 = latest['MA20']
                    ma60 = latest['MA60']
                    rsi = latest['RSI']
                    
                    # 均線位階判斷
                    trend_status = "🟩 站上20MA" if price >= ma20 else "🟥 跌破20MA"
                    
                    st.metric(
                        label=f"{ticker}",
                        value=f"{price:.2f}",
                        delta=f"{change:+.2f} ({pct:+.2f}%)"
                    )
                    st.write(f"• **趨勢狀態**: {trend_status}")
                    st.write(f"• **RSI (14)**: {rsi:.1f}" if not np.isnan(rsi) else "• **RSI**: 計算中")
                    st.write(f"• **20MA**: {ma20:.2f} | **60MA**: {ma60:.2f}")
                else:
                    st.error(f"無 {ticker} 數據")
        st.markdown("---")

# ==========================================
# TAB 2: 單一標的深度技術分析
# ==========================================
with tab2:
    st.subheader("🔍 單一標的技術分析與 K 線圖")
    
    col_select, col_period = st.columns([2, 1])
    with col_select:
        selected_ticker = st.selectbox("選擇要分析的股票/ETF", all_tickers, index=2) # 預設 2330.TW
    with col_period:
        selected_period = st.selectbox("時間範圍", ["3mo", "6mo", "1y", "2y"], index=2)
    
    # 重新抓取選擇時間範圍的詳細數據
    single_data = fetch_stock_data([selected_ticker], period=selected_period)
    
    if selected_ticker in single_data and not single_data[selected_ticker].empty:
        df_single = single_data[selected_ticker]
        
        # 繪製 Plotly 互動式 K線圖 + 成交量 + RSI
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            subplot_titles=(f'{selected_ticker} K線圖與均線 (20MA / 60MA)', '成交量', 'RSI (14) 指標'),
            row_width=[0.2, 0.2, 0.6]
        )
        
        # 1. K 線圖
        fig.add_trace(go.Candlestick(
            x=df_single.index,
            open=df_single['Open'], high=df_single['High'],
            low=df_single['Low'], close=df_single['Close'],
            name="K線"
        ), row=1, col=1)
        
        # 均線
        fig.add_trace(go.Scatter(x=df_single.index, y=df_single['MA20'], line=dict(color='orange', width=1.5), name="20MA (月線)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_single.index, y=df_single['MA60'], line=dict(color='green', width=1.5), name="60MA (季線)"), row=1, col=1)
        
        # 2. 成交量
        fig.add_trace(go.Bar(x=df_single.index, y=df_single['Volume'], name="成交量", marker_color='rgba(0,128,255,0.6)'), row=2, col=1)
        
        # 3. RSI
        fig.add_trace(go.Scatter(x=df_single.index, y=df_single['RSI'], line=dict(color='purple', width=1.5), name="RSI (14)"), row=3, col=1)
        # 超買超賣參考線
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        
        fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("無法取得該標的詳細數據。")

# ==========================================
# TAB 3: 選股策略與篩選標準說明
# ==========================================
with tab3:
    st.subheader("💡 50/50 雙軌策略之篩選邏輯與紀律")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 🛡️ 50% ETF 部位篩選標準")
        st.markdown("""
        1. **核心大盤型 (30%)**：
           - **標準**：總市值全市場前 50 大、內建自動剔除劣質公司機制、費用率低。
           - **代表標的**：`006208.TW` (富邦台50)、`VOO` (S&P 500 ETF)。
        2. **趨勢主題型 (20%)**：
           - **標準**：聚焦長線 Mega-Trend（AI 算力、半導體），成分股為全球產業霸主。
           - **代表標的**：`QQQ` (納斯達克100)、`00830.TW` (國泰費城半導體)。
        """)
        
    with col_b:
        st.markdown("### 🚀 50% 個股部位 4 大硬指標")
        st.markdown("""
        1. **獨家護城河 (Moat)**：具備產業壟斷性或技術獨霸地位（如台積電先進製程、輝達 CUDA 生態）。
        2. **高毛利率 (>40%)**：展現強大定價能力與抵抗通膨能力。
        3. **高 ROE (>20%)**：股東權益報酬率高，代表公司運用資本效率極佳。
        4. **高獲利成長率 (CAGR >15%)**：未來 3~5 年 EPS 具備高複合成長動能。
        """)
        
    st.markdown("---")
    st.info("💡 **再平衡紀律**：當個股因大漲導致佔總資產比例大於 60% 時，建議獲利了結 10% 轉入 ETF；當遇到系統性回檔導致個股低於 40% 時，可用 ETF 股息進行逢低加碼。")
