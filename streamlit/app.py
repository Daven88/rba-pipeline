from google.cloud import bigquery
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from google.oauth2 import service_account
import google.auth.transport.requests
import google.oauth2.id_token
import requests

PROJECT_ID = 'rba-pipeline-494410'

BQ_TABLES = ['ml_future_prediction', 'ml_model_scores', 
             'ml_feature_importance', 'mart_rba_decisions',
             'rba_meeting_dates']

NARRATIVE_API_URL = "https://rba-narrative-api-2gwbjutlmq-ts.a.run.app"

def get_narrative_token(audience):
    auth_req = google.auth.transport.requests.Request()
    return google.oauth2.id_token.fetch_id_token(auth_req, audience)

@st.cache_data(ttl=86400)
def get_narrative():
    token = get_narrative_token(NARRATIVE_API_URL)
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{NARRATIVE_API_URL}/narrative", headers=headers)
    response.raise_for_status()
    return response.json()['narrative']

# The dashboard is public but the API behind it is not: every /ask runs as
# this app's service account, so the bill lands on the project rather than on
# whoever typed the question. These two limits are the whole cost control.
ASK_QUESTION_LIMIT = 5


@st.cache_data(ttl=3600, show_spinner=False)
def ask_minutes(question):
    """
    Keyed on the question text, and st.cache_data is shared across everyone
    hitting this server instance — so a question two visitors both ask costs
    one Gemini call, not two. Unlike get_narrative there is no fixed daily
    result to cache, which is exactly why the free-text route needs the
    per-session cap below as well.
    """
    token = get_narrative_token(NARRATIVE_API_URL)
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{NARRATIVE_API_URL}/ask",
        headers=headers,
        params={"query": question},
        timeout=90,
    )
    response.raise_for_status()
    return response.json()["answer"]


def calculate_taylor_rule(current_inflation, current_unemployment):
    NEUTRAL_REAL_RATE = 1.0   # standard textbook estimate, not derived from this data
    INFLATION_TARGET = 2.5    # RBA's target midpoint (2-3% band)
    NAIRU = 4.25              # standard full-employment estimate

    inflation_gap = current_inflation - INFLATION_TARGET
    unemployment_gap = NAIRU - current_unemployment  # positive = tight labour market

    return NEUTRAL_REAL_RATE + current_inflation + 0.5 * inflation_gap + 0.5 * unemployment_gap

def load_data(table):
    client = bigquery.Client(project=PROJECT_ID)
    if table == 'mart_rba_decisions':
        query = f'SELECT * FROM `{PROJECT_ID}.gold.{table}` ORDER BY date'
    else:
        query = f'SELECT * FROM `{PROJECT_ID}.gold.{table}`'
    df = client.query(query).to_dataframe()
    return df

st.set_page_config(
    page_title="Next RBA Meeting Decision",    
    page_icon="🏦",
    layout="wide"
)

data = {}
for table in BQ_TABLES:
    data[table] = load_data(table)

st.title('Next RBA Meeting Decision')

meeting_dates = pd.to_datetime(data['rba_meeting_dates']['meeting_date'])

last_decision_date = pd.Timestamp(data['mart_rba_decisions']['date'].max())
today = pd.Timestamp.now().normalize()
upcoming_meetings = [d for d in meeting_dates if d > today]
next_meeting_date = min(upcoming_meetings) if upcoming_meetings else None

if next_meeting_date is not None:
    st.caption(f"Data last updated: {last_decision_date:%B %d %Y} — the pipeline refreshes "
               f"automatically two days before each RBA meeting. Meeting dates come from the "
               f"RBA's published calendar.")
else:
    st.caption(f"Data last updated: {last_decision_date:%B %d %Y} — the pipeline refreshes "
               f"automatically two days before each RBA meeting. All published meeting dates "
               f"have passed; next year's calendar needs adding.")
st.subheader('Next Meeting Prediction')

col1, col2, col3 = st.columns(3)

with col1:
    if next_meeting_date is not None:
        st.metric('Next Meeting Date', f'{next_meeting_date:%B %d %Y}')
    else:
        st.metric('Next Meeting Date', 'Calendar needs updating')

with col2:
    st.metric('Model Prediction (Raise/Hold/Cut)', data['ml_future_prediction']['predicted_direction'].iloc[0].capitalize())

with col3:
    current_inflation = data['mart_rba_decisions']['trimmed_mean_yoy'].iloc[-1]
    current_unemployment = data['mart_rba_decisions']['unemployment_rate'].iloc[-1]
    current_cash_rate = float(data['mart_rba_decisions']['cash_rate'].iloc[-1])

    taylor_target = calculate_taylor_rule(current_inflation, current_unemployment)
    gap = taylor_target - current_cash_rate

    if gap > 0.25:
        signal = "Raise"
    elif gap < -0.25:
        signal = "Cut"
    else:
        signal = "Hold"

    st.metric('Taylor Rule Signal', signal, delta=f'{gap:+.2f}% vs actual {current_cash_rate:.2f}%')
    st.caption('Illustrative reference point, not a forecast. Uses standard textbook estimates for the '
               'neutral *real* interest rate (1%, distinct from the 2-3% inflation target above) and '
               'NAIRU (4.25%) — not derived from this data.')
    st.text(
        f"Calculation: {taylor_target:.2f}% = 1.00% (neutral real rate) + {current_inflation:.2f}% (current inflation) "
        f"+ 0.5 × ({current_inflation:.2f}% − 2.50%) (inflation gap) "
        f"+ 0.5 × (4.25% − {current_unemployment:.2f}%) (unemployment gap)"
    )
st.divider()

st.subheader('AI-Generated Market Commentary')

with st.spinner('Generating narrative...'):
    try:
        narrative = get_narrative()
        st.write(narrative)
    except Exception as e:
        st.error(f"Could not load narrative {e}")

st.subheader('Ask the minutes')
st.caption(
    "The commentary above answers one fixed question. This searches all 1,321 sections "
    "of RBA board minutes since 2006 and answers from the retrieved text alone — no "
    "outside knowledge. Try: *What did the Board say about the labour market in 2023?*"
)

if 'ask_count' not in st.session_state:
    st.session_state.ask_count = 0
if 'last_answer' not in st.session_state:
    st.session_state.last_answer = None

asks_left = ASK_QUESTION_LIMIT - st.session_state.ask_count

with st.form('ask_minutes_form'):
    question = st.text_input(
        'Your question',
        max_chars=500,
        placeholder='e.g. How did the Board describe the housing market in 2017?',
    )
    submitted = st.form_submit_button('Ask', disabled=asks_left <= 0)

# Streamlit runs this file top to bottom on every interaction, so asks_left and
# the button's disabled state are both fixed before the answer is fetched.
# Incrementing here and rendering further down would report the count from
# before the question, and leave the button enabled for one question too many.
# Stash the answer, bump the count, and rerun so the next pass renders both
# from the updated state. The rerun stays outside the try: st.rerun signals
# itself by raising, and an `except Exception` would swallow it.
if submitted and asks_left > 0:
    asked = question.strip()
    if len(asked) < 3:
        st.warning('Please enter a question of at least three characters.')
    else:
        answer = None
        with st.spinner('Searching the minutes...'):
            try:
                answer = ask_minutes(asked)
            except Exception as e:
                st.error(f'Could not answer that one: {e}')
        if answer is not None:
            st.session_state.last_answer = answer
            st.session_state.ask_count += 1
            st.rerun()

if st.session_state.last_answer:
    st.write(st.session_state.last_answer)

if asks_left > 0:
    st.caption(f'{asks_left} of {ASK_QUESTION_LIMIT} questions remaining this session.')
else:
    st.info(
        f'Question limit reached for this session ({ASK_QUESTION_LIMIT}). '
        'Refresh to start a new one.'
    )

st.divider()

st.subheader('Current economic conditions')

col1, col2, col3 = st.columns(3)

with col1:
    current = data['mart_rba_decisions']['trimmed_mean_yoy'].iloc[-1]
    previous = data['mart_rba_decisions']['trimmed_mean_yoy'].iloc[-2]
    st.metric('Trimmed Mean (yoy)', f"{current:.2f}%", delta=round(current - previous, 2))
    st.caption('Inflation measure (yoy) | RBA target: 2-3%')

with col2:
    current = data['mart_rba_decisions']['unemployment_rate'].iloc[-1]
    previous = data['mart_rba_decisions']['unemployment_rate'].iloc[-2]
    st.metric('Unemployment Rate', f"{current:.2f}%", delta=round(current - previous, 2))
    st.caption('% of labour force seeking work | Full employment: ~4-4.5%')

with col3:
    current = data['mart_rba_decisions']['ratio_commodity'].iloc[-1]
    previous = data['mart_rba_decisions']['ratio_commodity'].iloc[-2]
    st.metric('Ratio Commodity (AU$/Bulk$)', f"{current:.2f}%", delta=round(current - previous, 2))
    st.caption('Bulk vs overall commodity prices in AUD | Higher = bulk commodities outperforming')

col1, col2, col3 = st.columns(3)

with col1:
    current = data['mart_rba_decisions']['GDP_growth'].iloc[-1]
    previous = data['mart_rba_decisions']['GDP_growth'].iloc[-2]
    st.metric('GDP Growth %', f"{current:.2f}%", delta=round(current - previous, 2))
    st.caption('Annual GDP growth rate (yoy) | Positive = expanding economy')

with col2:
    current = data['mart_rba_decisions']['government_spending'].iloc[-1]
    previous = data['mart_rba_decisions']['government_spending'].iloc[-1]
    st.metric('Government Spending', f"{current:.2f}%", delta=round(current - previous, 2))
    st.caption('Annual govt spending growth (yoy) | High spending can be inflationary')

with col3:
    current = data['mart_rba_decisions']['year_ended_productivity_growth'].iloc[-1]
    previous = data['mart_rba_decisions']['year_ended_productivity_growth'].iloc[-2]
    st.metric('Productivity (yoy)', f"{current:.2f}%", delta=round(current - previous, 2))
    st.caption('Annual productivity growth | Higher productivity reduces inflationary pressure')

st.divider()
st.subheader('Model Performance')

st.dataframe(data['ml_model_scores'])

st.divider()
st.subheader('Feature Importance')

df_importance = data['ml_feature_importance'].sort_values('importance')
fig, ax = plt.subplots(figsize=(8,4))
ax.barh(df_importance['feature'], df_importance['importance'])
st.pyplot(fig)


df_plot = data['mart_rba_decisions'][data['mart_rba_decisions']['date'] >= pd.Timestamp('2020-01-01')]

st.divider()
st.subheader('Economic Indicators')

col1, col2 = st.columns(2)

with col1:
    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(df_plot['date'], df_plot['trimmed_mean_yoy'])
    ax.set_title('CPI Trimmed Mean (Year ended %)')
    ax.axhline(y=2, color='r', linestyle='--')
    ax.axhline(y=3, color='r', linestyle='--')
    st.pyplot(fig)

    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(df_plot['date'], df_plot['unemployment_rate'])
    ax.set_title('Unemployment Rate (%)')
    ax.axhline(y=4, color='r', linestyle='--')
    ax.axhline(y=4.5, color='r', linestyle='--')
    st.pyplot(fig)

with col2:
    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(df_plot['date'], df_plot['GDP_growth'])
    ax.set_title('GDP (Year ended %)')
    ax.axhline(y=2.5, color='r', linestyle='--')
    st.pyplot(fig)

    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(df_plot['date'], df_plot['cash_rate'])
    ax.set_title('Cash Rate (%)')
    st.pyplot(fig)

