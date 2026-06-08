import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ===== 페이지 기본 설정 =====
st.set_page_config(
    page_title="주식 분석 대시보드",
    page_icon="📈",
    layout="wide"
)

st.title("📈 한국 & 미국 주식 분석 대시보드")
st.markdown("yfinance와 Plotly를 활용한 주식 수익률 비교 웹앱")

# ===== 주요 종목 딕셔너리 (티커: 이름) =====
# 한국 주식은 .KS(코스피), .KQ(코스닥)를 붙여야 합니다.
KOREA_STOCKS = {
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "035420.KS": "NAVER",
    "035720.KS": "카카오",
    "005380.KS": "현대차",
    "051910.KS": "LG화학",
    "006400.KS": "삼성SDI",
    "207940.KS": "삼성바이오로직스",
}

USA_STOCKS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet(Google)",
    "AMZN": "Amazon",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "META": "Meta",
    "NFLX": "Netflix",
}

# ===== 사이드바: 사용자 입력 =====
st.sidebar.header("⚙️ 설정")

# 시장 선택
market = st.sidebar.radio("시장 선택", ["한국", "미국", "한국+미국"])

# 시장에 따라 종목 목록 구성
if market == "한국":
    stock_dict = KOREA_STOCKS
elif market == "미국":
    stock_dict = USA_STOCKS
else:
    stock_dict = {**KOREA_STOCKS, **USA_STOCKS}

# 종목 다중 선택 (이름으로 보여주고 티커로 변환)
selected_names = st.sidebar.multiselect(
    "비교할 종목을 선택하세요 (여러 개 가능)",
    options=list(stock_dict.values()),
    default=list(stock_dict.values())[:3]  # 기본 3개 선택
)

# 이름 -> 티커 변환
name_to_ticker = {v: k for k, v in stock_dict.items()}
selected_tickers = [name_to_ticker[name] for name in selected_names]

# 기간 선택
period_option = st.sidebar.selectbox(
    "조회 기간",
    ["1개월", "3개월", "6개월", "1년", "2년", "5년"],
    index=3
)

period_map = {
    "1개월": "1mo", "3개월": "3mo", "6개월": "6mo",
    "1년": "1y", "2년": "2y", "5년": "5y"
}
period = period_map[period_option]


# ===== 데이터 불러오기 함수 =====
@st.cache_data(ttl=3600)  # 1시간 동안 캐시 (속도 향상)
def load_data(ticker, period):
    """yfinance로 주가 데이터를 불러옵니다."""
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            return None
        # 멀티인덱스 컬럼 처리 (yfinance 최신 버전 대응)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        return None


# ===== 메인 화면 =====
if not selected_tickers:
    st.warning("⬅️ 사이드바에서 종목을 하나 이상 선택해주세요.")
else:
    # 데이터 수집
    data_dict = {}
    return_data = {}  # 수익률 비교용

    with st.spinner("데이터를 불러오는 중..."):
        for ticker in selected_tickers:
            df = load_data(ticker, period)
            if df is not None and not df.empty:
                data_dict[ticker] = df
                # 누적 수익률 계산 (시작일 기준 %)
                first_price = df["Close"].iloc[0]
                return_data[ticker] = (df["Close"] / first_price - 1) * 100

    if not data_dict:
        st.error("데이터를 불러오지 못했습니다. 다시 시도해주세요.")
    else:
        # ===== 1. 수익률 요약 카드 =====
        st.subheader("📊 수익률 요약")
        cols = st.columns(len(data_dict))

        for idx, (ticker, df) in enumerate(data_dict.items()):
            name = stock_dict.get(ticker, ticker)
            start_price = df["Close"].iloc[0]
            end_price = df["Close"].iloc[-1]
            total_return = (end_price / start_price - 1) * 100

            with cols[idx]:
                st.metric(
                    label=f"{name}",
                    value=f"{end_price:,.0f}",
                    delta=f"{total_return:.2f}%"
                )

        st.divider()

        # ===== 2. 누적 수익률 비교 차트 =====
        st.subheader("📈 누적 수익률 비교 (%)")
        st.caption("선택 기간 시작일을 0%로 기준한 상대 수익률입니다.")

        fig_return = go.Figure()
        for ticker, ret in return_data.items():
            name = stock_dict.get(ticker, ticker)
            fig_return.add_trace(go.Scatter(
                x=ret.index,
                y=ret.values,
                mode="lines",
                name=name,
                line=dict(width=2)
            ))

        fig_return.update_layout(
            xaxis_title="날짜",
            yaxis_title="누적 수익률 (%)",
            hovermode="x unified",
            height=500,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        # 0% 기준선
        fig_return.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_return, use_container_width=True)

        st.divider()

        # ===== 3. 개별 종목 캔들차트 =====
        st.subheader("🕯️ 개별 종목 캔들차트")

        # 차트로 볼 종목 선택
        chart_name = st.selectbox(
            "캔들차트로 볼 종목 선택",
            options=[stock_dict.get(t, t) for t in data_dict.keys()]
        )
        chart_ticker = name_to_ticker.get(chart_name, chart_name)
        df = data_dict[chart_ticker]

        # 캔들차트 + 거래량 (2행 구조)
        fig_candle = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{chart_name} 주가", "거래량")
        )

        # 캔들차트
        fig_candle.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="주가",
                increasing_line_color="red",   # 한국식: 상승=빨강
                decreasing_line_color="blue"   # 하락=파랑
            ),
            row=1, col=1
        )

        # 이동평균선 (20일)
        df["MA20"] = df["Close"].rolling(window=20).mean()
        fig_candle.add_trace(
            go.Scatter(
                x=df.index, y=df["MA20"],
                mode="lines", name="20일 이동평균",
                line=dict(color="orange", width=1.5)
            ),
            row=1, col=1
        )

        # 거래량
        fig_candle.add_trace(
            go.Bar(
                x=df.index, y=df["Volume"],
                name="거래량",
                marker_color="lightgray"
            ),
            row=2, col=1
        )

        fig_candle.update_layout(
            height=600,
            template="plotly_white",
            xaxis_rangeslider_visible=False,
            showlegend=True
        )
        st.plotly_chart(fig_candle, use_container_width=True)

        st.divider()

        # ===== 4. 원본 데이터 표 =====
        with st.expander("📋 원본 데이터 보기"):
            st.dataframe(df.tail(20))

# ===== 푸터 =====
st.markdown("---")
st.caption("데이터 출처: Yahoo Finance (yfinance) | 본 자료는 투자 참고용이며 투자 책임은 본인에게 있습니다.")
