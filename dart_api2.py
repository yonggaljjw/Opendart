import requests
import pandas as pd
import os
from openai import OpenAI
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
import streamlit as st
import pymysql

load_dotenv()  # env파일을 읽어서 환경변수 설정

key = os.getenv('key')
openai_key = os.getenv('openai_key')
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWD = os.getenv("PASSWD")
PORT = os.getenv("PORT")

## 기업 고유번호 DB에서 불러오기
pymysql.install_as_MySQLdb()  # 파이썬 전용 데이터베이스 커넥터

## 기업 고유번호 DB에서 불러오기
pd.options.display.float_format = '{:.2f}'.format
connection = pymysql.connect(host=HOST,
                             user=USER,
                             password=PASSWD,
                             db='notouch')
SQL = 'SELECT * from notouch'
corp_code = pd.read_sql(SQL, connection)
connection.close()


def balance_sheet(corp_name, bsns_year, report_code) :
    url = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'
    response = requests.get(url, params = {'crtfc_key' : key,
                                           'corp_code' : corp_code[corp_code.corp_name == corp_name]['corp_code'].values[0],
                                           'bsns_year' : bsns_year,
                                           'reprt_code' : report_code})
    df_balance = pd.DataFrame(response.json()['list'])
    df_balance = df_balance[['account_nm', 'thstrm_amount', 'frmtrm_amount', 'thstrm_dt', 'frmtrm_dt']]
    df_balance = df_balance.rename(columns = {'account_nm' : '계정명', 'thstrm_amount' : '당기금액',
                                              'frmtrm_amount' : '전기금액', 'thstrm_dt' : '당기일자',
                                              'frmtrm_dt' : '전기일자'})
    return df_balance


# Background image and sidebar styles
page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
background-image: url("https://i.postimg.cc/4xgNnkfX/Untitled-design.png");
background-size: cover;
background-position: center center;
background-repeat: no-repeat;
background-attachment: local;
}}
[data-testid="stHeader"] {{
background: rgba(0,0,0,0);
}}
[data-testid="stSidebar"] {{
background-image: url("https://i.postimg.cc/4xgNnkfX/Untitled-design.png");
background-size: cover;
}}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)


# Sidebar with input fields
with st.sidebar:
    st.subheader('회사 이름과 기간을 입력하세요')
    stock_name = st.text_input("회사이름", "삼성전자")
    bsns_year = st.text_input("시작년도", "2022")
    button_result = st.button('재무제표 분석하기')

if button_result:
    df = balance_sheet(stock_name, bsns_year, '11012')

    ## GPT 출력
    os.environ['OPENAI_API_KEY'] = openai_key

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are a highly assistant that analyzes financial data based on the given DataFrame \n
            The answer should provide a summarized analysis and insights"""},
            {"role": "user", "content": f"financial dataframe: {df}"},
            {"role": "assistant", "content" : 
            """Analyze the following financial data for a company and provide insights. Focus on:
            1. Balance Sheet Analysis:
            - Changes in equity: common stock, retained earnings, total equity.
            2. Income Statement Analysis:
            - Changes in sales revenue and operating profit.
            - Changes in net income.
            3. Cash Flow Analysis:
            - Changes in current assets and liabilities.
            - Liquidity analysis.
            4. Profitability and Performance Analysis:
            - Operating profit and net income.
            - Current vs. previous period profitability.
            5. Financial Health Analysis:
            - Total assets, liabilities, and equity.
            - Current vs. previous period comparison."""}
        ],
        max_tokens=1000, # 비용 발생하므로 시도하며 적당한 값 찾아간다. 200이면 최대 200단어까지 생성. 
        temperature=1.0, # 창의성 발휘 여부. 0~2 사이. 0에 가까우면 strict하게, 2에 가까우면 자유롭게(창의성 필요)
        stop=None # 특정 문자열이 들어오면 멈춘다든지. None이면 없음. .이면 문장이 끝나면 멈춘다든지
    )
    answer = response.choices[0].message.content
    # 영어에서 한국어로 번역
    translated = GoogleTranslator(source='en', target='ko').translate(answer)

    if "tabs_data" not in st.session_state:
        st.session_state.tabs_data = []
        st.session_state.tabs_labels = []

    # Add the translated content and stock name to the session state
    st.session_state.tabs_data.append(translated)
    st.session_state.tabs_labels.append(stock_name)

    # Create tabs
    tabs = st.tabs(st.session_state.tabs_labels)

    for i, translated_text in enumerate(st.session_state.tabs_data):
        with tabs[i]:
            st.write(translated_text)