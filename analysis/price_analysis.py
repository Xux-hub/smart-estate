"""
房价数据分析模块
使用 Pandas 进行数据探索性分析
"""
import os
import sys

import pandas as pd
import numpy as np
import pymysql
import yaml

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_connection():
    """获取数据库连接"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'database.yml')
    with open(config_path, 'r', encoding='utf-8') as f:
        db_config = yaml.safe_load(f)['database']

    return pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['name'],
        charset=db_config['charset'],
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_house_data(city=None):
    """加载房源数据到 DataFrame"""
    conn = get_db_connection()
    sql = """
        SELECT h.*, c.name as community_name, d.name as district_name, ct.name as city_name
        FROM house h
        JOIN community c ON h.community_id = c.id
        JOIN district d ON c.district_id = d.id
        JOIN city ct ON d.city_id = ct.id
        WHERE h.status = 1
    """
    if city:
        sql += f" AND ct.name = '{city}'"

    df = pd.read_sql(sql, conn)
    conn.close()
    return df


def basic_statistics(df):
    """基本统计分析"""
    stats = {
        'total_count': len(df),
        'avg_total_price': df['total_price'].mean(),
        'median_total_price': df['total_price'].median(),
        'avg_unit_price': df['unit_price'].mean(),
        'median_unit_price': df['unit_price'].median(),
        'avg_area': df['area'].mean(),
        'max_price': df['total_price'].max(),
        'min_price': df['total_price'].min(),
    }
    return stats


def district_analysis(df):
    """区域分析"""
    district_stats = df.groupby('district_name').agg(
        count=('id', 'count'),
        avg_price=('unit_price', 'mean'),
        median_price=('unit_price', 'median'),
        max_price=('unit_price', 'max'),
        min_price=('unit_price', 'min'),
        avg_area=('area', 'mean'),
    ).round(2).sort_values('avg_price', ascending=False)

    return district_stats


def layout_analysis(df):
    """户型分析"""
    layout_stats = df.groupby('layout').agg(
        count=('id', 'count'),
        avg_price=('unit_price', 'mean'),
        avg_total_price=('total_price', 'mean'),
    ).round(2).sort_values('count', ascending=False)

    return layout_stats


def price_factors_correlation(df):
    """房价影响因素相关性分析"""
    # 选择数值型特征
    numeric_cols = ['total_price', 'unit_price', 'area', 'total_floor', 'elevator', 'house_year']
    available_cols = [col for col in numeric_cols if col in df.columns]

    df_numeric = df[available_cols].dropna()
    correlation = df_numeric.corr()

    return correlation


def decoration_analysis(df):
    """装修情况分析"""
    decoration_stats = df.groupby('decoration').agg(
        count=('id', 'count'),
        avg_unit_price=('unit_price', 'mean'),
        avg_total_price=('total_price', 'mean'),
    ).round(2).sort_values('count', ascending=False)

    return decoration_stats


if __name__ == '__main__':
    print("=" * 60)
    print("智慧房产探索平台 - 数据分析")
    print("=" * 60)

    df = load_house_data()

    if df.empty:
        print("暂无数据，请先运行爬虫采集数据。")
    else:
        print(f"\n数据总量: {len(df)} 条")
        print("\n--- 基本统计 ---")
        stats = basic_statistics(df)
        for key, value in stats.items():
            print(f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}")

        print("\n--- 区域分析 (Top 10) ---")
        district_stats = district_analysis(df)
        print(district_stats.head(10).to_string())

        print("\n--- 户型分析 (Top 10) ---")
        layout_stats = layout_analysis(df)
        print(layout_stats.head(10).to_string())

        print("\n--- 相关性分析 ---")
        corr = price_factors_correlation(df)
        print(corr.to_string())
