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

# 표에
