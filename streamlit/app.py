from google.cloud import bigquery
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ID = 'rba-pipeline-494410'

BQ_TABLES = ['ml_future_prediction', 'ml_model_scores', 'ml_feature_importance', 'mart_rba_decisions']

def load_data(table):
    client = bigquery.Client(project=PROJECT_ID)
    if table == 'mart_rba_decisions':
        query = f'SELECT * FROM `{PROJECT_ID}.gold.{table}` ORDER BY date'
    else:
        query = f'SELECT * FROM `{PROJECT_ID}.gold.{table}`'
    df = client.query(query).to_dataframe()
    return df

data = {}
for table in BQ_TABLES:
    data[table] = load_data(table)

st.title('Next RBA Meeting Decision')
st.subheader('Next Meeting Prediction')

col1, col2, col3 = st.columns(3)

with col1:
    st.metric('Next Meeting Date', 'June 16 2026')

with col2:
    st.metric('Model Prediction (Raise/Hold/Cut)', data['ml_future_prediction']['predicted_direction'].iloc[0].capitalize())

with col3:
    st.metric('RBA future Prediction', 'No Change')
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
fig, ax = plt.subplots()
ax.barh(df_importance['feature'], df_importance['importance'])
st.pyplot(fig)


# app.py  ├── connect to BigQuery
#   ├── load data (ml_future_prediction, ml_model_scores, ml_feature_importance, mart_rba_decisions)  │
#   ├── HEADER — "RBA Rate Decision Tracker"
#   │
#   ├── Section 1 — Next Meeting Prediction
#   │   ├── Next meeting date (June 16 2026)
#   │   ├── Model prediction (raise/hold/cut) — big bold text
#   │   └── ASX market implied probability — manual input or scraped
#   │
#   ├── Section 2 — Current Economic Conditions
#   │   └── Last row of mart_rba_decisions — 6 metrics shown as cards/tiles
#   │
#   ├── Section 3 — Model Performance
#   │   └── Table of accuracy/F1 per model from ml_model_scores
#   │
#   └── Section 4 — Feature Importances
#       └── Bar chart from ml_feature_importance