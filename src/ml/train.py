from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
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
    df_wide = df_wide.rename(columns={'FR.INR.LEND': 'lending_rate','FR.INR.RINR': 'real_interest_rate'})
    df_wide['lending_rate_change'] = df_wide['lending_rate'].diff()
    df_wide['direction'] = df_wide['lending_rate_change'].apply(label_direction)
    df_wide = df_wide.dropna()
    return df_wide
    
def train_model(df_wide):
    X = df_wide[['real_interest_rate', 'lending_rate_change']]
    y = df_wide['direction']                                                                                                                                     
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)                                                                    
    model = LogisticRegression()                                                                                                          
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred))
    return model, X_test, y_test

def save_predictions(model, X_test, y_test):
    df_preds = X_test.copy()
    y_pred = model.predict(X_test)
    df_preds['predicted_direction'] = y_pred
    df_preds['actual_direction'] = y_test.values
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f'{PROJECT_ID}.gold.ml_predictions'
    job = client.load_table_from_dataframe(df_preds, table_id)
    job.result()

def main():

    df = load_data()
    df_wide = prepare_features(df)
    model, X_test, y_test = train_model(df_wide)
    save_predictions(model, X_test, y_test)

if __name__ == '__main__':
    main()