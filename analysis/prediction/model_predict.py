"""
房价预测模块
加载训练好的模型进行房价预测，并将结果写入数据库
"""
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import joblib
import pymysql
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analysis.price_analysis import load_house_data, get_db_connection

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


def load_model(model_name='RandomForest'):
    """加载模型和预处理器"""
    model = joblib.load(os.path.join(MODEL_DIR, f'{model_name}_model.pkl'))
    scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
    le_district = joblib.load(os.path.join(MODEL_DIR, 'le_district.pkl'))
    le_decoration = joblib.load(os.path.join(MODEL_DIR, 'le_decoration.pkl'))
    return model, scaler, le_district, le_decoration


def predict_district_price(model, scaler, le_district, le_decoration, df, district_name):
    """预测某区域的未来房价"""
    district_data = df[df['district_name'] == district_name]

    if district_data.empty:
        return None

    # 计算区域平均特征
    avg_features = {
        'area': district_data['area'].mean(),
        'total_floor': district_data['total_floor'].median(),
        'elevator': district_data['elevator'].mode().iloc[0] if not district_data['elevator'].mode().empty else 0,
        'house_year': district_data['house_year'].median(),
        'district_encoded': le_district.transform([district_name])[0] if district_name in le_district.classes_ else 0,
        'decoration_encoded': 0,
        'room_count': 2,
    }

    # 当前实际均价
    current_avg = district_data['unit_price'].mean()

    # 预测
    X_pred = pd.DataFrame([avg_features])
    predicted_price = model.predict(X_pred)[0]

    # 计算趋势
    change_rate = ((predicted_price - current_avg) / current_avg) * 100

    if change_rate > 2:
        trend = '上涨'
    elif change_rate < -2:
        trend = '下跌'
    else:
        trend = '平稳'

    return {
        'current_avg': current_avg,
        'predicted_price': predicted_price,
        'change_rate': round(change_rate, 2),
        'trend': trend,
    }


def run_prediction(city=None, model_name='RandomForest'):
    """运行预测并保存结果到数据库"""
    print("加载模型...")
    model, scaler, le_district, le_decoration = load_model(model_name)

    print("加载数据...")
    df = load_house_data(city)

    if df.empty:
        print("无数据可预测")
        return

    # 获取所有区域
    districts = df['district_name'].unique()
    print(f"共 {len(districts)} 个区域需要预测")

    conn = get_db_connection()
    cursor = conn.cursor()

    predict_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    results = []
    for district_name in districts:
        result = predict_district_price(model, scaler, le_district, le_decoration, df, district_name)
        if result:
            results.append({
                'district_name': district_name,
                **result,
            })

            # 获取 district_id
            cursor.execute("SELECT d.id FROM district d WHERE d.name = %s", (district_name,))
            row = cursor.fetchone()
            if row:
                district_id = row['id']
                # 写入预测结果
                sql = """
                    INSERT INTO price_prediction (district_id, predict_date, avg_price, trend, change_rate, confidence, model_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    district_id,
                    predict_date,
                    round(result['predicted_price'], 2),
                    result['trend'],
                    result['change_rate'],
                    0.85,  # 默认置信度
                    model_name,
                ))

    conn.commit()
    conn.close()

    # 打印结果
    print(f"\n预测日期: {predict_date}")
    print(f"{'区域':<10} {'当前均价':<12} {'预测均价':<12} {'变化率':<8} {'趋势':<6}")
    print("-" * 50)
    for r in sorted(results, key=lambda x: x['predicted_price'], reverse=True):
        print(f"{r['district_name']:<10} {r['current_avg']:<12.0f} {r['predicted_price']:<12.0f} {r['change_rate']:<8.2f}% {r['trend']:<6}")

    print(f"\n预测完成，共 {len(results)} 条结果已保存到数据库。")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='房价预测')
    parser.add_argument('--city', type=str, default=None, help='城市名称')
    parser.add_argument('--model', type=str, default='RandomForest', help='模型名称')
    args = parser.parse_args()

    run_prediction(city=args.city, model_name=args.model)
