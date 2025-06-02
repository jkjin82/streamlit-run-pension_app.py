import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

# --- 함수 정의 ---
def calculate_early_pension_reduction_rate(years_early):
    """
    조기 노령연금 감액률 계산
    출처: 국민연금공단 (매년 6% 감액)
    """
    return 1 - (years_early * 0.06)

def calculate_annual_pension_with_increase_rate(base_monthly_pension, pension_start_age, current_age, pension_increase_rate):
    """
    연금 상승률을 반영한 연간 연금 수령액 계산
    pension_start_age는 해당 연금을 받기 시작하는 실제 연령 (정규 or 조기)
    """
    if current_age < pension_start_age:
        return 0  # 연금 수령 시작 연령 이전에는 연금 없음
    
    years_since_start = current_age - pension_start_age
    adjusted_monthly_pension = base_monthly_pension * ((1 + pension_increase_rate)**years_since_start)
    return adjusted_monthly_pension * 12

def simulate_investment(initial_capital, early_monthly_pension_at_start, base_regular_monthly_pension, annual_return_rate, investment_start_age, investment_end_age, pension_increase_rate, pension_type, regular_pension_start_age, early_pension_start_age):
    """
    투자를 시뮬레이션하고 연도별 자산 변화를 반환합니다.
    early_monthly_pension_at_start: 조기 수령 시작 시점의 월 고정 연금액 (감액된 금액)
    base_regular_monthly_pension: 정규 수령 시작 시점의 월 고정 연금액
    """
    data = []
    current_capital = initial_capital
    
    # 연간 수익률을 분기 수익률로 변환
    quarterly_return_rate = (1 + annual_return_rate)**(1/4) - 1
    
    for age in range(investment_start_age, investment_end_age + 1):
        annual_pension_income_for_current_year = 0
        
        if pension_type == "early":
            # 조기 수령 시작 시점의 월 고정액(감액된)을 기준으로 매년 연금 상승률 반영
            annual_pension_income_for_current_year = calculate_annual_pension_with_increase_rate(
                early_monthly_pension_at_start, early_pension_start_age, age, pension_increase_rate
            )
        else: # regular
            # 정규 수령 시작 시점의 월 고정액을 기준으로 매년 연금 상승률 반영
            annual_pension_income_for_current_year = calculate_annual_pension_with_increase_rate(
                base_regular_monthly_pension, regular_pension_start_age, age, pension_increase_rate
            )
        
        # 연간 연금 수령액을 월별로 나눈 값 (실제 받는 단위)
        monthly_pension_amount_received = annual_pension_income_for_current_year / 12

        # 분기별 복리 시뮬레이션 (총 4분기)
        for quarter in range(4):
            # 3개월치 연금 수입을 합산하여 자산에 추가
            current_capital += (monthly_pension_amount_received * 3)
            # 분기 수익률 적용하여 복리 계산
            current_capital *= (1 + quarterly_return_rate)

        data.append({"연령": age, "자산": round(current_capital)})
    
    return pd.DataFrame(data)

# --- Streamlit 앱 시작 ---

st.set_page_config(layout="wide", page_title="국민연금 조기 vs. 정규 수령 자산 비교")

st.title("💰 국민연금 조기 vs. 정규 수령 자산 비교 시뮬레이터")
st.markdown("---")

st.sidebar.header("설정 입력")

# --- 사용자 입력 ---
# 정규 수령 시작 연령 고정 (65세)
regular_pension_start_age = 65
st.sidebar.write(f"**정규 수령 시작 연령:** {regular_pension_start_age}세 (고정)")

col1_sidebar, col2_sidebar = st.sidebar.columns(2)
with col1_sidebar:
    base_regular_monthly_pension = st.number_input(
        "정규 수령 시 예상 월 수령금 (원)",
        min_value=100_000,
        max_value=5_000_000,
        value=1_000_000,
        step=100_000,
        help="연금 상승률이 적용되기 전, 정규 수령 시작 시점에 받게 될 월 연금액을 입력하세요."
    )
    early_pension_years = st.number_input(
        "조기 수령 연수 (최대 5년)",
        min_value=0, # 0년은 정규 수령과 동일한 시작 나이에 받는 것
        max_value=5,
        value=0,
        step=1,
        help="정규 수령 시점보다 몇 년 일찍 연금을 받을지 선택하세요. 최대 5년입니다."
    )
with col2_sidebar:
    investment_end_age = st.number_input(
        "투자 종료 연령 (세)",
        min_value=regular_pension_start_age + 1,
        max_value=100,
        value=80,
        step=1,
        help="투자를 종료하고 최종 자산을 비교할 연령을 입력하세요."
    )
    annual_return_rate = st.slider(
        "연간 투자 수익률 (%)",
        min_value=0.0,
        max_value=20.0,
        value=5.0,
        step=0.1,
        format="%.1f",
        help="연간 예상 투자 수익률을 입력하세요. 이 수익률에 따라 분기 복리 계산이 적용됩니다."
    ) / 100

st.sidebar.markdown("#### 연간 연금 상승률")
st.sidebar.info("국민연금은 전년도 물가상승률을 반영하여 연금액을 인상합니다. 최근 5년(2021~2025년 적용분)의 연평균 인상률은 약 **3.42%**입니다.")
pension_increase_rate = st.sidebar.slider(
    "연간 연금 상승률 (%)",
    min_value=0.0,
    max_value=10.0,
    value=3.4, # Calculated average of 3.42%, rounded to 3.4 for slider
    step=0.1,
    format="%.1f",
    help="매년 연금액이 상승하는 비율을 입력하세요. 정규 연금과 조기 연금 모두에 반영됩니다."
) / 100

st.markdown("---")

# --- 계산 로직 ---
# 조기 수령 관련 계산
early_pension_start_age = regular_pension_start_age - early_pension_years
early_pension_reduction_rate = calculate_early_pension_reduction_rate(early_pension_years)
# 조기 수령 시작 시점의 월 연금액 (이 금액을 기준으로 이후 연금 상승률이 적용됨)
early_monthly_pension_at_start = base_regular_monthly_pension * early_pension_reduction_rate

st.subheader("💡 연금 수령 정보")
st.write(f"**정규 수령 시작 연령:** {regular_pension_start_age}세")
st.write(f"**조기 수령 시작 연령:** {early_pension_start_age}세")
st.write(f"**정규 수령 시 월 예상액:** {base_regular_monthly_pension:,.0f}원")
if early_pension_years > 0:
    st.write(f"**조기 수령 시작 시점의 월 예상액 (감액률 {early_pension_reduction_rate:.1%} 적용):** {early_monthly_pension_at_start:,.0f}원")
else:
    st.write("**조기 수령을 선택하지 않았습니다.**")

st.markdown("---")

# 시뮬레이션 실행
st.subheader("📊 자산 시뮬레이션 결과")
st.write(f"**연간 투자 수익률:** {annual_return_rate*100:.1f}%")
st.write(f"**연간 연금 상승률:** {pension_increase_rate*100:.1f}%")

early_pension_df = simulate_investment(
    initial_capital=0, # 초기 자산은 0으로 시작 (연금만으로 투자)
    early_monthly_pension_at_start=early_monthly_pension_at_start, # 조기 수령 시작 시점 금액 전달
    base_regular_monthly_pension=base_regular_monthly_pension, # 정규 수령 기준 금액 전달
    annual_return_rate=annual_return_rate,
    investment_start_age=early_pension_start_age,
    investment_end_age=investment_end_age,
    pension_increase_rate=pension_increase_rate,
    pension_type="early",
    regular_pension_start_age=regular_pension_start_age,
    early_pension_start_age=early_pension_start_age
)

regular_pension_df = simulate_investment(
    initial_capital=0,
    early_monthly_pension_at_start=early_monthly_pension_at_start, # 이 시뮬에서는 사용 안함 (조기 연금액 기준이 아님)
    base_regular_monthly_pension=base_regular_monthly_pension,
    annual_return_rate=annual_return_rate,
    investment_start_age=regular_pension_start_age,
    investment_end_age=investment_end_age,
    pension_increase_rate=pension_increase_rate,
    pension_type="regular",
    regular_pension_start_age=regular_pension_start_age,
    early_pension_start_age=early_pension_start_age # 이 시뮬에서는 사용 안함 (정규 연금액 기준이 아님)
)

# 결과 데이터프레임 병합
merged_df = pd.DataFrame({'연령': range(early_pension_start_age, investment_end_age + 1)})

# 조기 수령 데이터 병합
merged_df = pd.merge(merged_df, early_pension_df, on='연령', how='left').rename(columns={'자산': '조기 수령 시 자산'})

# 정규 수령 데이터 병합 (조기 수령 시작 연령부터 투자 종료 연령까지)
# 정규 수령 시작 연령 이전은 NaN 처리 후 0으로 채우기
merged_df = pd.merge(merged_df, regular_pension_df, on='연령', how='left').rename(columns={'자산': '정규 수령 시 자산'})
merged_df['정규 수령 시 자산'] = merged_df['정규 수령 시 자산'].fillna(0) # 정규 수령 시작 전까지 0으로 채움

# 자산 차이 계산
merged_df['자산 차이 (조기 - 정규)'] = merged_df['조기 수령 시 자산'] - merged_df['정규 수령 시 자산']

# --- 표에서 역전 시점 강조 ---
def highlight_crossover(row):
    # '자산 차이 (조기 - 정규)' 컬럼에서 0 이하로 떨어지는 시점 강조
    if row['자산 차이 (조기 - 정규)'] <= 0:
        return ['color: red'] * len(row)
    return [''] * len(row)

st.subheader("표: 연도별 자산 변화")
st.dataframe(
    merged_df.style.apply(highlight_crossover, axis=1).format({
        '조기 수령 시 자산': "{:,.0f}원".format,
        '정규 수령 시 자산': "{:,.0f}원".format,
        '자산 차이 (조기 - 정규)': "{:,.0f}원".format
    }),
    hide_index=True,
    use_container_width=True
)

st.subheader("그래프: 자산 변화 추이")
fig, ax = plt.subplots(figsize=(12, 6))
# 그래프 텍스트만 영어로 변경
ax.plot(merged_df['연령'], merged_df['조기 수령 시 자산'], label='Early Receipt Asset', marker='o', markersize=4)
ax.plot(merged_df['연령'], merged_df['정규 수령 시 자산'], label='Regular Receipt Asset', marker='x', markersize=4)
ax.set_xlabel("Age")
ax.set_ylabel("Asset (KRW)")
ax.set_title("National Pension Early vs. Regular Receipt Asset Comparison")
ax.ticklabel_format(style='plain', axis='y') # y축 지수표기법 방지
ax.grid(True, linestyle='--', alpha=0.7)
ax.legend()

# 역전 시점 찾기 (있는 경우)
crossover_age = None
for i in range(1, len(merged_df)):
    if (merged_df['자산 차이 (조기 - 정규)'].iloc[i-1] > 0) and \
       (merged_df['자산 차이 (조기 - 정규)'].iloc[i] <= 0):
        crossover_age = merged_df['연령'].iloc[i]
        break
    elif (merged_df['자산 차이 (조기 - 정규)'].iloc[i-1] < 0) and \
         (merged_df['자산 차이 (조기 - 정규)'].iloc[i] >= 0):
        crossover_age = merged_df['연령'].iloc[i]
        break

if crossover_age:
    # 그래프 내 텍스트만 영어로 변경
    ax.axvline(x=crossover_age, color='red', linestyle='--', linewidth=2, label=f'Crossover Age: {crossover_age}')
    ax.legend(loc='upper left') # 범례 위치 조정
    st.info(f"정규 수령 자산이 조기 수령 자산을 **추월**하기 시작하는 시점은 약 **{crossover_age}세**입니다.")
else:
    st.info("시뮬레이션 기간 내에 정규 수령 자산이 조기 수령 자산을 명확하게 추월하는 시점을 찾을 수 없습니다.")

plt.tight_layout()
st.pyplot(fig, dpi=150) # dpi를 높여 해상도 개선

st.markdown("---")
st.subheader("🔍 계산 과정 상세 보기 (연령 선택)")
st.info("위 표에서 특정 연령을 선택하여 상세 계산 과정을 확인하세요.")

selected_age_from_table = st.selectbox(
    "상세 계산을 보고 싶은 연령을 선택하세요:",
    options=merged_df['연령'].tolist(),
    key="age_selector_for_details"
)

if selected_age_from_table:
    selected_data_row = merged_df[merged_df['연령'] == selected_age_from_table].iloc[0]
    
    st.markdown(f"#### 선택된 연령: {selected_age_from_table}세")
    st.write(f"**조기 수령 시 자산:** {selected_data_row['조기 수령 시 자산']:,.0f}원")
    st.write(f"**정규 수령 시 자산:** {selected_data_row['정규 수령 시 자산']:,.0f}원")

    st.markdown("---")
    
    # 조기 수령 계산 과정 설명
    st.markdown("##### 조기 수령 자산 계산 풀이 과정:")
    current_annual_return_rate_display = annual_return_rate * 100
    current_quarterly_return_rate_display = ((1 + annual_return_rate)**(1/4) - 1) * 100
    
    current_early_monthly_pension_at_selected_age = early_monthly_pension_at_start * ((1 + pension_increase_rate)**(selected_age_from_table - early_pension_start_age)) if selected_age_from_table >= early_pension_start_age else 0

    st.write(f"이 계산은 **{early_pension_start_age}세**부터 **{selected_age_from_table}세**까지 조기 수령 시작 시점의 월 **{early_monthly_pension_at_start:,.0f}원** (감액 적용된 금액)이 연간 **{pension_increase_rate*100:.1f}%**의 연금 상승률에 따라 매년 증가하며, 이 연금액을 연간 **{current_annual_return_rate_display:.1f}%**의 투자 수익률(분기 수익률: **{current_quarterly_return_rate_display:.2f}%**)로 투자한 결과입니다. 매 분기마다 3개월치 연금 수입이 합산되어 복리 계산됩니다.")
    
    if selected_age_from_table >= early_pension_start_age:
        # LaTeX 수식에서 "원"을 \text{} 안에 넣고, f-string과 r-string을 분리하여 사용
        st.latex(
            r"$$\text{조정된 월 연금액} = \text{시작 월 연금액} \times (1 + \text{연금 상승률})^{(\text{현재 연령} - \text{조기 시작 연령})}$$"
            + f"$$= {early_monthly_pension_at_start:,.0f} \\text{{ 원}} \\times (1 + {pension_increase_rate:.4f})^{{{selected_age_from_table} - {early_pension_start_age}}} = {current_early_monthly_pension_at_selected_age:,.0f} \\text{{ 원}}$$"
        )
    st.markdown("분기 복리 계산 공식은 다음과 같습니다:")
    st.latex(r"$$\text{현재 자산} = (\text{이전 분기 말 자산} + \text{분기 연금 수입}) \times (1 + \text{분기 수익률})$$")
    st.markdown(f"이 과정이 매 분기 반복되어 총 자산이 누적됩니다.")

    st.markdown("##### 정규 수령 자산 계산 풀이 과정:")
    if selected_age_from_table < regular_pension_start_age:
        st.write(f"{selected_age_from_table}세는 정규 수령 시작 연령({regular_pension_start_age}세) 이전이므로, 현재까지의 정규 수령 자산은 **0원**입니다.")
    else:
        st.write(f"이 계산은 **{regular_pension_start_age}세**부터 **{selected_age_from_table}세**까지 연금액이 연간 연금 상승률 **{pension_increase_rate*100:.1f}%**에 따라 매년 조정된 연금을 받고, 이를 연간 **{current_annual_return_rate_display:.1f}%**의 투자 수익률(분기 수익률: **{current_quarterly_return_rate_display:.2f}%**)로 투자한 결과입니다. 매 분기마다 3개월치 연금 수입이 합산되어 복리 계산됩니다.")
        
        current_adjusted_monthly_pension_regular = base_regular_monthly_pension * ((1 + pension_increase_rate)**(selected_age_from_table - regular_pension_start_age))
        # LaTeX 수식에서 "원"을 \text{} 안에 넣고, f-string과 r-string을 분리하여 사용
        st.latex(
            r"$$\text{조정된 월 연금액} = \text{기본 월 연금액} \times (1 + \text{연금 상승률})^{(\text{현재 연령} - \text{정규 시작 연령})}$$"
            + f"$$= {base_regular_monthly_pension:,.0f} \\text{{ 원}} \\times (1 + {pension_increase_rate:.4f})^{{{selected_age_from_table} - {regular_pension_start_age}}} = {current_adjusted_monthly_pension_regular:,.0f} \\text{{ 원}}$$"
        )
        st.markdown("총 자산은 이 조정된 연금액과 매 분기 연금 수입 및 분기 복리 계산을 통해 누적됩니다.")

st.markdown("---")
st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")