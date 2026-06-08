import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="AI 종목 분석 도우미", page_icon="🤖", layout="wide")

st.title("🤖 AI 종목 분석 도우미")
st.markdown("""
AI 관련 종목을 **데이터 기반으로 자동 분석**해 점수로 보여줍니다.
> ⚠️ 이것은 **투자 추천이 아닙니다.** 데이터 해석을 돕는 학습용 도구이며,
> 최종 판단과 책임은 본인에게 있습니다.
""")

# ===== AI 관련 종목 =====
AI_STOCKS = {
    "NVDA": "NVIDIA (AI 반도체)",
    "MSFT": "Microsoft (OpenAI)",
    "GOOGL": "Alphabet (Gemini)",
    "META": "Meta (Llama)",
    "AMD": "AMD (AI 반도체)",
    "AVGO": "Broadcom (AI 칩)",
    "PLTR": "Palantir (AI 분석)",
    "TSM": "TSMC (파운드리)",
    "005930.KS": "삼성전자 (HBM)",
    "000660.KS": "SK하이닉스 (HBM)",
    "042700.KS": "한미반도체 (HBM 장비)",
    "035420.KS": "NAVER (하이퍼클로바)",
}

st.sidebar.header("⚙️ 분석 설정")
period_map = {"3개월": "3mo", "6개월": "6mo", "1년": "1y", "2년": "2y"}
period_option = st.sidebar.selectbox("분석 기간", list(period_map.keys()), index=2)
period = period_map[period_option]


@st.cache_data(ttl=3600)
def load_data(ticker, period):
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return None


def analyze_stock(df):
    """종목을 분석해 지표와 점수를 계산합니다."""
    close = df["Close"]

    # 1. 기간 수익률 (%)
    total_return = (close.iloc[-1] / close.iloc[0] - 1) * 100

    # 2. 변동성 (일일 수익률의 표준편차, 연율화 %)
    daily_return = close.pct_change().dropna()
    volatility = daily_return.std() * np.sqrt(252) * 100

    # 3. 추세 신호 (현재가 vs 20일 이동평균)
    ma20 = close.rolling(20).mean().iloc[-1]
    trend = "상승추세" if close.iloc[-1] > ma20 else "하락추세"

    # 4. 위험 대비 수익 (간단 샤프 비율 개념)
    risk_return = total_return / volatility if volatility != 0 else 0

    return {
        "수익률": total_return,
        "변동성": volatility,
        "추세": trend,
        "위험대비수익": risk_return
    }


# ===== 전체 종목 분석 =====
with st.spinner("AI 종목들을 분석하는 중..."):
    results = []
    for ticker, name in AI_STOCKS.items():
        df = load_data(ticker, period)
        if df is not None and len(df) > 20:
            a = analyze_stock(df)
            results.append({
                "종목": name,
                "티커": ticker,
                "수익률(%)": round(a["수익률"], 2),
                "변동성(%)": round(a["변동성"], 2),
                "추세": a["추세"],
                "위험대비수익": round(a["위험대비수익"], 3),
            })

result_df = pd.DataFrame(results)

# ===== 1. 종합 분석 표 =====
st.subheader("📊 AI 종목 종합 분석")
st.caption("위험대비수익이 높을수록 '위험 대비 효율이 좋았던' 종목입니다.")

# 위험대비수익 기준 정렬
result_df = result_df.sort_values("위험대비수익", ascending=False).reset_index(drop=True)

# 표에 색상 강조
st.dataframe(
    result_df.style.background_gradient(
        subset=["위험대비수익"], cmap="RdYlGn"
    ).format({
        "수익률(%)": "{:.2f}",
        "변동성(%)": "{:.2f}",
        "위험대비수익": "{:.3f}"
    }),
    use_container_width=True,
    hide_index=True
)

st.divider()

# ===== 2. 수익률 vs 위험 산점도 =====
st.subheader("🎯 수익률 vs 위험(변동성) 지도")
st.caption("오른쪽 아래(고수익·저위험)일수록 효율이 좋았던 영역입니다.")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=result_df["변동성(%)"],
    y=result_df["수익률(%)"],
    mode="markers+text",
    text=result_df["종목"],
    textposition="top center",
    marker=dict(
        size=14,
        color=result_df["위험대비수익"],
        colorscale="RdYlGn",
        showscale=True,
        colorbar=dict(title="위험대비<br>수익")
    )
))
fig.update_layout(
    xaxis_title="위험 (변동성 %)",
    yaxis_title="수익률 (%)",
    height=550,
    template="plotly_white"
)
fig.add_hline(y=0, line_dash="dash", line_color="gray")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===== 3. 데이터 기반 참고 의견 =====
st.subheader("💡 데이터 기반 참고 정보")

best = result_df.iloc[0]
worst = result_df.iloc[-1]
up_trend = result_df[result_df["추세"] == "상승추세"]["종목"].tolist()

col1, col2 = st.columns(2)
with col1:
    st.success(f"""
    **📈 위험 대비 효율이 가장 좋았던 종목**
    → **{best['종목']}**
    (수익률 {best['수익률(%)']}%, 변동성 {best['변동성(%)']}%)
    """)
with col2:
    st.warning(f"""
    **📉 위험 대비 효율이 낮았던 종목**
    → **{worst['종목']}**
    (수익률 {worst['수익률(%)']}%, 변동성 {worst['변동성(%)']}%)
    """)

if up_trend:
    st.info(f"**현재 상승추세(20일선 위)인 종목:** {', '.join(up_trend)}")

st.error("""
⚠️ **꼭 기억하세요!**
위 정보는 **과거 데이터**일 뿐, 미래 수익을 보장하지 않습니다.
과거에 좋았던 종목이 앞으로도 좋다는 보장은 없습니다.
이 자료는 **학습용**이며, 실제 투자 판단과 책임은 본인에게 있습니다.
""")

st.caption("데이터 출처: Yahoo Finance")
