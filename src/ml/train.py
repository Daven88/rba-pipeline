from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = 'rba-pipeline-494410'

def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{PROJECT_ID}.gold.mart_australia_rates` ORDER BY date'
    df = client.query(query).to_dataframe()
    return df

def label_direction(x):
    if pd.isna(x):
        return None
    elif x > 0:
        return 'up'
    else: 
        return 'down'
    
def prepare_features(df):
    df_wide = df.pivot(index='date', columns='indicator_id', values='value').reset_index()                                                       
    df_wide = df_wide.rename(columns={'FR.INR.LEND': 'lending_rate',
                                      'FP.CPI.TOTL.ZG': 'CPI_inflation',
                                      'NY.GDP.MKTP.KD.ZG': 'GDP', 
                                      'SP.POP.GROW': 'Population_Growth', 
                                      'SL.UEM.TOTL.ZS': 'Unemployment_rate'})
    df_wide = df_wide.sort_values('date')
    df_wide['lending_rate_change'] = df_wide['lending_rate'].diff()
    df_wide['direction'] = df_wide['lending_rate_change'].apply(label_direction)
    df_wide['cpi_lag1'] =  df_wide['CPI_inflation'].shift(1)
    df_wide['gdp_lag1'] =  df_wide['GDP'].shift(1)
    df_wide['pop_growth_lag1'] =  df_wide['Population_Growth'].shift(1)
    df_wide['unemployment_lag1'] =  df_wide['Unemployment_rate'].shift(1)
    df_wide = df_wide.dropna()
    return df_wide

def train_model(df_wide):
    X = df_wide[['cpi_lag1', 'gdp_lag1', 'pop_growth_lag1', 'unemployment_lag1']]
    le = LabelEncoder()
    y = le.fit_transform(df_wide['direction'])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)    

    models = [LogisticRegression(), RandomForestClassifier(), XGBClassifier()]      
    results = {}

    for model in models:                                                                                                   
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        score = accuracy_score(y_test, y_pred)
        results[model] = score
        print(f'{model.__class__.__name__}: {score:.2f}')
        print(classification_report(y_test, y_pred))

    best_model = max(results, key=results.get)    
    return best_model, X_test, y_test, le

def save_predictions(model, X_test, y_test, le):
    df_preds = X_test.copy()
    y_pred = le.inverse_transform(model.predict(X_test))
    df_preds['predicted_direction'] = y_pred
    df_preds['actual_direction'] = le.inverse_transform(y_test)
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f'{PROJECT_ID}.gold.ml_predictions'
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_TRUNCATE'
    )
    job = client.load_table_from_dataframe(df_preds, table_id, job_config=job_config)
    job.result()

def main():

    df = load_data()
    df_wide = prepare_features(df)
    model, X_test, y_test, le = train_model(df_wide)
    save_predictions(model, X_test, y_test, le)

if __name__ == '__main__':
    main()