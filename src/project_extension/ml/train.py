import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from google.cloud import bigquery
import joblib
from datetime import datetime

PROJECT_ID = 'rba-pipeline-494410'

def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{PROJECT_ID}.gold.mart_rba_decisions` ORDER BY date'
    df = client.query(query).to_dataframe()
    return df

def categorise_change(x):
    if x > 0:
        return 'raise'
    elif x == 0:
        return 'hold'
    else:
        return 'cut'

def prepare_features(df):
    # remove + using .replace
    df['rate_change'] = df['rate_change'].str.replace('+', '')
    # convert from string to float
    df['rate_change'] = df['rate_change'].astype(float)
    # create a new column called rate_change cat
    df['rate_change_cat'] = df['rate_change'].apply(categorise_change)
    #drop NAs
    df = df.dropna()

    return df

def train_model(df):
    # extract columns that will be used for the model
    model_data = df[['rate_change_cat', 
                    'trimmed_mean_yoy_lag1', 
                    'unemployment_rate_lag1',
                    'ratio_commodity_lag1',
                    'GDP_growth_lag1',
                    'government_spending_lag1',
                    'year_ended_productivity_growth_lag1']]

    # extract the target variable as y
    y = model_data['rate_change_cat']

    # extract the predictor variables as X
    X = model_data.drop(columns=['rate_change_cat'])

    # initialize labelencoder and apply to target variable
    le = LabelEncoder()
    y = le.fit_transform(y)

    # split the data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # initialize smote and apply to training set
    smote = SMOTE()
    X_train, y_train = smote.fit_resample(X_train, y_train)
    
    #bring in the models
    models  = [LogisticRegression(), RandomForestClassifier(), XGBClassifier()]
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

def save_predictions(le, model, X_test, y_test):
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

def feature_importance(results, feature_names):
    for model in results.keys():
        if model.__class__.__name__ == 'RandomForestClassifier':
            df = pd.DataFrame(zip(feature_names, model.feature_importances_), columns=['feature', 'importance'])
    save_to_bigquery(df, 'gold.ml_feature_importance')

def save_model(best_model):
    joblib.dump(best_model, f'src/project_extension/ml/models/best_model.pkl')

def predict_next(df, le):
    model = joblib.load(f'src/project_extension/ml/models/best_model.pkl')
    last_row = df.tail(1)[[
                    'trimmed_mean_yoy_lag1', 
                    'unemployment_rate_lag1',
                    'ratio_commodity_lag1',
                    'GDP_growth_lag1',
                    'government_spending_lag1',
                    'year_ended_productivity_growth_lag1'
                    ]]
    pred = model.predict(last_row)
    pred = le.inverse_transform(pred)
    return pred

def save_prediction_next(pred):
    df = pd.DataFrame([{
        'date': datetime.today().date(),
        'predicted_direction': pred[0]
    }])
    save_to_bigquery(df, 'gold.ml_future_prediction')

def main():
    df = load_data()
    df = prepare_features(df)
    best_model, X_test, y_test, le, results = train_model(df)
    save_predictions(le, best_model, X_test, y_test)
    save_model_scores(results, y_test)
    save_model(best_model)
    pred = predict_next(df, le)
    save_prediction_next(pred)
    feature_importance(results, X_test.columns)

if __name__ == '__main__':
    main()


