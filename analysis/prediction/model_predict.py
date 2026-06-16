import json
import os
import sys
from datetime import datetime

import joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analysis.price_analysis import get_db_connection

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


def load_model(model_name='RandomForest'):
    model = joblib.load(os.path.join(MODEL_DIR, f'{model_name}_model.pkl'))
    scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
    encoders = joblib.load(os.path.join(MODEL_DIR, 'encoders.pkl'))
    return model, scaler, encoders


def predict_unit_price(area, region, huxing='', chaoxiang='', zhuangxiu='', model_name='RandomForest'):
    model, scaler, encoders = load_model(model_name)
    row = {
        'area': float(area),
        'region_encoded': _encode(encoders['region'], region),
        'huxing_encoded': _encode(encoders['huxing'], huxing or '未知'),
        'chaoxiang_encoded': _encode(encoders['chaoxiang'], chaoxiang or '未知'),
        'zhuangxiu_encoded': _encode(encoders['zhuangxiu'], zhuangxiu or '未知'),
    }
    X = pd.DataFrame([row])
    if model_name == 'LinearRegression':
        X = scaler.transform(X)
    return float(model.predict(X)[0])


def save_prediction_result(city, region, predicted_price, model_name='RandomForest'):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analysis_result
                    (analysis_type, city, region, target_name, result_value, result_json, model_name, created_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    '房价预测',
                    city,
                    region,
                    region,
                    predicted_price,
                    json.dumps({'unit_price': predicted_price}, ensure_ascii=False),
                    model_name,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _encode(encoder, value):
    value = value if value in encoder.classes_ else encoder.classes_[0]
    return int(encoder.transform([value])[0])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='基于 house_info 的房价单价预测')
    parser.add_argument('--city', type=str, default='')
    parser.add_argument('--region', type=str, required=True)
    parser.add_argument('--area', type=float, required=True)
    parser.add_argument('--huxing', type=str, default='')
    parser.add_argument('--chaoxiang', type=str, default='')
    parser.add_argument('--zhuangxiu', type=str, default='')
    parser.add_argument('--model', type=str, default='RandomForest')
    args = parser.parse_args()

    price = predict_unit_price(args.area, args.region, args.huxing, args.chaoxiang, args.zhuangxiu, args.model)
    save_prediction_result(args.city, args.region, price, args.model)
    print(f'预测单价: {price:.2f} 元/㎡')
