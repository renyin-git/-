import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 網頁頁面設定
st.set_page_config(page_title="個人股票監控儀表板", layout="wide")

st.title("📈 個人股票即時追蹤與技術分析")
st.caption("數據來源：Yahoo Finance (台股請加 .TW 或 .TWO，例如：2330.TW 或 0050.TW)")

# 側邊欄輸入參數
st.sidebar.header("股票選擇與設定")
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330.TW")
time_period = st.sidebar.selectbox("選擇時間範圍", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

# 載入股票資料
@st.cache_data(ttl=300) # 快取 5 分鐘，避免頻繁請求
def load_data(ticker, period):
    data = yf.Ticker(ticker)
    df = data.history(period=period)
    info = data.info
    return df, info

try:
    df, info = load_data(stock_id, time_period)

    if df.empty:
        st.error("找不到該股票資料，請確認代碼是否正確！")
    else:
        # 計算簡單移動平均線 (MA)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 最新價格與漲跌幅指標
        latest_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = latest_price - prev_price
        pct_change = (change / prev_price) * 100

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("公司名稱", info.get("shortName", stock_id))
        col2.metric("最新收盤價", f"{latest_price:.2f} 元", f"{change:+.2f} ({pct_change:+.2f}%)")
        col3.metric("最高價 (期間)", f"{df['High'].max():.2f} 元")
        col4.metric("最低價 (期間)", f"{df['Low'].min():.2f} 元")

        st.markdown("---")

        # 繪製 K 線圖與均線 (Plotly 互動式圖表)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, subplot_titles=('K線圖與均線', '成交量'),
                            row_width=[0.2, 0.7])

        # K線
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name="K線"
        ), row=1, col=1)

        # 均線
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name="20MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='green', width=1.5), name="60MA"), row=1, col=1)

        # 成交量
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color='blue'), row=2, col=1)

        fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        # 顯示歷史數據表格
        with st.expander("查看近 10 日歷史數據"):
            st.dataframe(df.tail(10)[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index(ascending=False))

except Exception as e:
    st.error(f"發生錯誤: {e}")
