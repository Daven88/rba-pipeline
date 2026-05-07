from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import precision_score, recall_score, f1_score
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
    df_wide = df.pivot(index='date', columns='indicator_id', values='value')                                                      
    df_wide = df_wide.rename(columns={'FR.INR.LEND': 'lending_rate',
                                      'FP.CPI.TOTL.ZG': 'CPI_inflation',
                                      'NY.GDP.MKTP.KD.ZG': 'GDP', 
                                      'SP.POP.GROW': 'Population_Growth', 
                                      'SL.UEM.TOTL.ZS': 'Unemployment_rate'})
    df_wide = df_wide.sort_index()
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
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.5, random_state=42)    

    models = [LogisticRegression(), RandomForestClassifier(), XGBClassifier()]      
    results = {}

    for model in models:                                                                                                   
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        score = accuracy_score(y_test, y_pred)
        results[model] = (score, y_pred)
        print(f'{model.__class__.__name__}: {score:.2f}')
        print(classification_report(y_test, y_pred))

    best_model = max(results, key=lambda x: results[x][0])    
    return best_model, X_test, y_test, le, results

def save_to_bigquery(df, table_name):
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f'{PROJECT_ID}.{table_name}'
    job_config = bigquery.LoadJobConfig(write_disposition='WRITE_TRUNCATE')
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

def save_predictions(model, X_test, y_test, le):
    df_preds = X_test.copy()
    df_preds = df_preds.reset_index()
    y_pred = le.inverse_transform(model.predict(X_test))
    df_preds['predicted_direction'] = y_pred
    df_preds['actual_direction'] = le.inverse_transform(y_test)
    save_to_bigquery(df_preds, 'gold.ml_predictions')

def save_model_scores(results, y_test):
    model_list = []
    for model, result in results.items():
        score, y_pred = result
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0) 
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0) 
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0) 
        model_list.append({'model_name': model.__class__.__name__, 
                           'accuracy': score, 
                           'precision': precision,
                           'recall': recall,
                           'f1': f1
                           })
    df_scores = pd.DataFrame(model_list)
    save_to_bigquery(df_scores, 'gold.ml_model_scores')

def save_feature_importance(results, feature_names):
    for model in results.keys():
        if model.__class__.__name__== 'RandomForestClassifier':
            df = pd.DataFrame(zip(feature_names, model.feature_importances_), columns=['feature', 'importance'])
    save_to_bigquery(df, 'gold.ml_feature_importance')

def main():

    df = load_data()
    df_wide = prepare_features(df)
    model, X_test, y_test, le, results = train_model(df_wide)
    save_predictions(model, X_test, y_test, le)
    save_model_scores(results, y_test)
    save_feature_importance(results, X_test.columns)

if __name__ == '__main__':
    main()