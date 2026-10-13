import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基本設定
st.set_page_config(page_title="全方位股票分析與 50/50 雙軌戰略儀表板", layout="wide")

st.title("📈 全方位股票分析與 50/50 雙軌戰略儀表板")
st.caption("整合①基本面健診、④總體經濟雷達、技術面K線與 50/50 雙軌資產追蹤")

# 2. 預設監控標的群組
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
        "tickers": ["2330.TW", "MSFT", "2059.TW", "3293.TW"],
        "desc": "具備高技術壁壘、壟斷定價權與高 ROE"
    },
    "Stock_Growth": {
        "title": "⚡ 高動能黑馬個股 (20%)",
        "tickers": ["NVDA", "2317.TW", "3661.TW", "2357.TW"],
        "desc": "站在 AI/算力/伺服器強勁風口的高成長企業"
    }
}

# 總體經濟觀察指標代碼
MACRO_TICKERS = {
    "^SOX": "費城半導體指數 (半導體景氣風向球)",
    "TWD=X": "美元 / 新台幣 (外資資金動向)",
    "^TNX": "美國10年期公債殖利率 (科技股估值錨)",
    "^GSPC": "標普 500 指數 (美股總體氛圍)"
}

# 3. 數據抓取與快取處理
@st.cache_data(ttl=600)
def fetch_stock_history(tickers, period="1y"):
    """批次抓取歷史價格並計算技術指標"""
    data_dict = {}
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period=period)
            if not df.empty:
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['MA60'] = df['Close'].rolling(window=60).mean()
                
                # 計算 RSI (14)
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                data_dict[ticker] = df
        except Exception:
            pass
    return data_dict

@st.cache_data(ttl=3600)
def fetch_fundamental_info(tickers):
    """抓取基本面財務數據 (方法①)"""
    fundamental_list = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            
            # 安全提取數據
            name = info.get("shortName", info.get("longName", ticker))
            gross_margin = info.get("grossMargins", None)
            op_margin = info.get("operatingMargins", None)
            roe = info.get("returnOnEquity", None)
            pe = info.get("trailingPE", None)
            forward_pe = info.get("forwardPE", None)
            rev_growth = info.get("revenueGrowth", None)
            debt_equity = info.get("debtToEquity", None)
            
            # 百分比轉換
            gross_margin_pct = gross_margin * 100 if gross_margin is not None else np.nan
            op_margin_pct = op_margin * 100 if op_margin is not None else np.nan
            roe_pct = roe * 100 if roe is not None else np.nan
            rev_growth_pct = rev_growth * 100 if rev_growth is not None else np.nan
            
            # 基本面護城河綜合評分 (硬指標)
            pass_flags = 0
            if gross_margin_pct >= 40: pass_flags += 1
            if roe_pct >= 15: pass_flags += 1
            if rev_growth_pct >= 10: pass_flags += 1
            
            score_badge = "🟢 強力護城河" if pass_flags >= 2 else ("🟡 營運穩健" if pass_flags == 1 else "⚪ 觀察/轉型中")
            
            fundamental_list.append({
                "代碼": ticker,
                "名稱": name,
                "評級": score_badge,
                "毛利率 (%)": round(gross_margin_pct, 2) if not np.isnan(gross_margin_pct) else "N/A",
                "營業利益率 (%)": round(op_margin_pct, 2) if not np.isnan(op_margin_pct) else "N/A",
                "ROE (%)": round(roe_pct, 2) if not np.isnan(roe_pct) else "N/A",
                "營收成長率 (%)": round(rev_growth_pct, 2) if not np.isnan(rev_growth_pct) else "N/A",
                "本益比 (PE)": round(pe, 2) if pe is not None else "N/A",
                "前瞻本益比": round(forward_pe, 2) if forward_pe is not None else "N/A",
                "負債比率 (%)": round(debt_equity, 2) if debt_equity is not None else "N/A"
            })
        except Exception:
            pass
    return pd.DataFrame(fundamental_list)

# 收集所有股票清單
all_tickers = []
for group in PORTFOLIO_CONFIG.values():
    all_tickers.extend(group["tickers"])
# 確保唯一性
all_tickers = list(dict.fromkeys(all_tickers))

with st.spinner("載入行情與基本面財務數據中..."):
    stock_data = fetch_stock_history(all_tickers)
    macro_data = fetch_stock_history(list(MACRO_TICKERS.keys()))

# 4. 頁籤規劃 (新增基本面與總經頁籤)
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 50/50 配置與即時總覽", 
    "🏢 ① 基本面財務健診與估值", 
    "🌐 ④ 總體經濟與產業風口雷達", 
    "🔍 單一標的深度 K 線技術分析"
])

# ==========================================
# TAB 1: 50/50 配置與即時總覽
# ==========================================
with tab1:
    st.subheader("📌 50/50 雙軌策略標的監視看板")
    
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
                    
                    trend_status = "🟩 站上20MA" if price >= ma20 else "🟥 跌破20MA"
                    
                    st.metric(
                        label=f"{ticker}",
                        value=f"{price:.2f}",
                        delta=f"{change:+.2f} ({pct:+.2f}%)"
                    )
                    st.write(f"• **趨勢**: {trend_status}")
                    st.write(f"• **20MA**: {ma20:.2f}")
                else:
                    st.error(f"無 {ticker} 數據")
        st.markdown("---")

# ==========================================
# TAB 2: ① 基本面財務健診與估值篩選
# ==========================================
with tab2:
    st.subheader("🏢 方法①：基本面護城河與估值篩選器")
    st.markdown("""
    **核心篩選硬指標**：
    * **毛利率 > 40%**：具備高附加價值與定價權（抗通膨能力）。
    * **ROE > 15%**：公司運用股東資金創造利潤的能力極強。
    * **營收成長率 > 10%**：處於高成長趨勢軌道上。
    """)
    
    # 過濾出純個股 (排除 ETF 以利計算真實基本面)
    individual_stocks = [t for t in all_tickers if not (t.startswith("00") or t in ["VOO", "QQQ"])]
    
    with st.spinner("讀取財報數據與計算 ROE/毛利率..."):
        df_fundamental = fetch_fundamental_info(individual_stocks)
    
    if not df_fundamental.empty:
        # 基本面數據表格展示
        st.dataframe(df_fundamental, use_container_width=True, hide_index=True)
        
        # 篩選器互動區
        st.markdown("---")
        st.subheader("🔍 條件自訂篩選")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            min_margin = st.slider("最低毛利率要求 (%)", 0, 70, 30)
        with col_f2:
            min_roe = st.slider("最低 ROE 要求 (%)", 0, 40, 15)
            
        # 套用篩選條件
        filtered_df = df_fundamental[
            (pd.to_numeric(df_fundamental["毛利率 (%)"], errors='coerce') >= min_margin) &
            (pd.to_numeric(df_fundamental["ROE (%)"], errors='coerce') >= min_roe)
        ]
        
        st.markdown(f"**符合篩選條件的標的數量：{len(filtered_df)} 檔**")
        st.dataframe(filtered_df[["代碼", "名稱", "評級", "毛利率 (%)", "ROE (%)", "本益比 (PE)"]], use_container_width=True, hide_index=True)
    else:
        st.warning("無法載入基本面財報數據。")

# ==========================================
# TAB 3: ④ 總體經濟與產業風口雷達
# ==========================================
with tab3:
    st.subheader("🌐 方法④：總體經濟與產業風口趨勢雷達")
    st.markdown("掌握市場資金大潮（降息/通膨/美債殖利率）與全球半導體景氣動向。")
    
    col_m1, col_m2 = st.columns(2)
    
    # 觀察 4 大總經指標
    for idx, (m_ticker, m_name) in enumerate(MACRO_TICKERS.items()):
        with (col_m1 if idx % 2 == 0 else col_m2):
            st.markdown(f"##### {m_name} (`{m_ticker}`)")
            if m_ticker in macro_data and not macro_data[m_ticker].empty:
                m_df = macro_data[m_ticker]
                m_latest = m_df.iloc[-1]['Close']
                m_prev = m_df.iloc[-2]['Close']
                m_change = m_latest - m_prev
                m_pct = (m_change / m_prev) * 100
                m_ma20 = m_df.iloc[-1]['MA20']
                
                # 判斷趨勢方向
                m_status = "📈 多頭升勢" if m_latest >= m_ma20 else "📉 空頭拉回"
                
                st.metric(
                    label=f"最新數值",
                    value=f"{m_latest:.2f}",
                    delta=f"{m_change:+.2f} ({m_pct:+.2f}%)"
                )
                st.write(f"• **中期趨勢 (20MA)**: {m_status}")
                
                # 微型走勢圖
                fig_macro = go.Figure()
                fig_macro.add_trace(go.Scatter(x=m_df.index[-60:], y=m_df['Close'][-60:], mode='lines', name=m_ticker, line=dict(color='deepskyblue')))
                fig_macro.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white")
                st.plotly_chart(fig_macro, use_container_width=True)
            else:
                st.write("數據載入中或無法取得。")
            st.markdown("---")

# ==========================================
# TAB 4: 單一標的深度 K 線技術分析
# ==========================================
with tab4:
    st.subheader("🔍 單一標的技術分析與 K 線圖")
    
    selected_ticker = st.selectbox("選擇要分析的股票/ETF", all_tickers, index=0)
    selected_period = st.selectbox("時間範圍", ["3mo", "6mo", "1y", "2y"], index=2)
    
    single_data = fetch_stock_history([selected_ticker], period=selected_period)
    
    if selected_ticker in single_data and not single_data[selected_ticker].empty:
        df_single = single_data[selected_ticker]
        
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            subplot_titles=(f'{selected_ticker} K線圖與均線 (20MA / 60MA)', '成交量', 'RSI (14) 指標'),
            row_width=[0.2, 0.2, 0.6]
        )
        
        fig.add_trace(go.Candlestick(
            x=df_single.index,
            open=df_single['Open'], high=df_single['High'],
            low=df_single['Low'], close=df_single['Close'],
            name="K線"
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df_single.index, y=df_single['MA20'], line=dict(color='orange', width=1.5), name="20MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_single.index, y=df_single['MA60'], line=dict(color='green', width=1.5), name="60MA"), row=1, col=1)
        fig.add_trace(go.Bar(x=df_single.index, y=df_single['Volume'], name="成交量", marker_color='rgba(0,128,255,0.6)'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_single.index, y=df_single['RSI'], line=dict(color='purple', width=1.5), name="RSI (14)"), row=3, col=1)
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        
        fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
