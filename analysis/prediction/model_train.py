import os
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analysis.price_analysis import load_house_data

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)


def prepare_features(df):
    df_clean = df[['area', 'region', 'huxing', 'chaoxiang', 'zhuangxiu', 'unit_price']].dropna(subset=['area', 'unit_price']).copy()
    df_clean['region'] = df_clean['region'].fillna('未知')
    df_clean['huxing'] = df_clean['huxing'].fillna('未知')
    df_clean['chaoxiang'] = df_clean['chaoxiang'].fillna('未知')
    df_clean['zhuangxiu'] = df_clean['zhuangxiu'].fillna('未知')

    encoders = {}
    for column in ['region', 'huxing', 'chaoxiang', 'zhuangxiu']:
        encoder = LabelEncoder()
        df_clean[column + '_encoded'] = encoder.fit_transform(df_clean[column])
        encoders[column] = encoder

    X = df_clean[['area', 'region_encoded', 'huxing_encoded', 'chaoxiang_encoded', 'zhuangxiu_encoded']]
    y = df_clean['unit_price']
    return X, y, encoders


def train_models(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        'LinearRegression': (LinearRegression(), X_train_scaled, X_test_scaled),
        'RandomForest': (RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1), X_train, X_test),
    }

    results = {}
    best_name = None
    best_model = None
    best_score = -np.inf
    for name, (model, train_data, test_data) in models.items():
        model.fit(train_data, y_train)
        y_pred = model.predict(test_data)
        r2 = r2_score(y_test, y_pred)
        results[name] = {
            'r2': r2,
            'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred))),
            'mae': float(mean_absolute_error(y_test, y_pred)),
        }
        if r2 > best_score:
            best_name = name
            best_model = model
            best_score = r2
    return results, best_name, best_model, scaler


def main():
    df = load_house_data()
    if df.empty or len(df) < 50:
        print('数据量不足，至少需要 50 条 house_info 记录。')
        return

    X, y, encoders = prepare_features(df)
    results, best_name, best_model, scaler = train_models(X, y)
    joblib.dump(best_model, os.path.join(MODEL_DIR, f'{best_name}_model.pkl'))
    joblib.dump(scaler, os.path.join(MODEL_DIR, 'scaler.pkl'))
    joblib.dump(encoders, os.path.join(MODEL_DIR, 'encoders.pkl'))

    print(f'最佳模型: {best_name}')
    for name, metrics in results.items():
        print(f"{name}: R2={metrics['r2']:.4f}, RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}")


if __name__ == '__main__':
    main()
