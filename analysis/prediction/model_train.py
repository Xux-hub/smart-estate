"""
房价预测模型训练模块
使用 Scikit-learn 构建房价预测模型
"""
import os
import sys

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analysis.price_analysis import load_house_data


# 模型保存路径
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)


def prepare_features(df):
    """特征工程：准备模型输入特征"""
    # 选择特征列
    feature_cols = ['area', 'total_floor', 'elevator', 'house_year']
    target_col = 'unit_price'

    # 过滤有效数据
    df_clean = df[feature_cols + [target_col, 'district_name', 'decoration', 'layout']].dropna(subset=[target_col, 'area'])

    # 填充缺失值
    df_clean['total_floor'] = df_clean['total_floor'].fillna(df_clean['total_floor'].median())
    df_clean['elevator'] = df_clean['elevator'].fillna(0)
    df_clean['house_year'] = df_clean['house_year'].fillna(df_clean['house_year'].median())

    # 编码分类特征
    le_district = LabelEncoder()
    df_clean['district_encoded'] = le_district.fit_transform(df_clean['district_name'].fillna('未知'))

    le_decoration = LabelEncoder()
    df_clean['decoration_encoded'] = le_decoration.fit_transform(df_clean['decoration'].fillna('其他'))

    # 从户型中提取房间数
    df_clean['room_count'] = df_clean['layout'].str.extract(r'(\d+)').astype(float).fillna(2)

    # 最终特征
    X = df_clean[['area', 'total_floor', 'elevator', 'house_year', 'district_encoded', 'decoration_encoded', 'room_count']]
    y = df_clean[target_col]

    return X, y, le_district, le_decoration


def train_models(X, y):
    """训练多个模型并比较"""
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        'LinearRegression': LinearRegression(),
        'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'GradientBoosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
    }

    results = {}
    best_model = None
    best_score = -np.inf

    for name, model in models.items():
        print(f"\n训练模型: {name}")

        if name == 'LinearRegression':
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

        # 评估
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)

        results[name] = {'r2': r2, 'rmse': rmse, 'mae': mae}
        print(f"  R² Score: {r2:.4f}")
        print(f"  RMSE: {rmse:.2f}")
        print(f"  MAE: {mae:.2f}")

        if r2 > best_score:
            best_score = r2
            best_model = (name, model)

    return results, best_model, scaler


def save_model(model, scaler, le_district, le_decoration, model_name):
    """保存模型和预处理器"""
    joblib.dump(model, os.path.join(MODEL_DIR, f'{model_name}_model.pkl'))
    joblib.dump(scaler, os.path.join(MODEL_DIR, 'scaler.pkl'))
    joblib.dump(le_district, os.path.join(MODEL_DIR, 'le_district.pkl'))
    joblib.dump(le_decoration, os.path.join(MODEL_DIR, 'le_decoration.pkl'))
    print(f"\n模型已保存: {MODEL_DIR}/{model_name}_model.pkl")


def main():
    """主训练流程"""
    print("=" * 60)
    print("智慧房产探索平台 - 房价预测模型训练")
    print("=" * 60)

    # 加载数据
    print("\n加载数据...")
    df = load_house_data()

    if df.empty or len(df) < 50:
        print("数据量不足（需要至少50条记录），请先运行爬虫采集更多数据。")
        return

    print(f"数据量: {len(df)} 条")

    # 特征工程
    print("\n特征工程...")
    X, y, le_district, le_decoration = prepare_features(df)
    print(f"有效样本数: {len(X)}")
    print(f"特征数: {X.shape[1]}")

    # 训练模型
    print("\n开始训练模型...")
    results, (best_name, best_model), scaler = train_models(X, y)

    # 保存最佳模型
    print(f"\n最佳模型: {best_name} (R²={results[best_name]['r2']:.4f})")
    save_model(best_model, scaler, le_district, le_decoration, best_name)

    print("\n训练完成！")


if __name__ == '__main__':
    main()
