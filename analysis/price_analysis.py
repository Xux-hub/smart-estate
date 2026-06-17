import os
import re
import sys

import pandas as pd
import pymysql
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_connection():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'database.yml')
    with open(config_path, 'r', encoding='utf-8') as f:
        db_config = yaml.safe_load(f)['database']

    return pymysql.connect(
        host=os.getenv('DB_HOST', db_config['host']),
        port=int(os.getenv('DB_PORT', db_config['port'])),
        user=os.getenv('DB_USER', db_config['user']),
        password=os.getenv('DB_PASSWORD', db_config.get('password') or ''),
        database=os.getenv('DB_NAME', db_config['name']),
        charset=os.getenv('DB_CHARSET', db_config.get('charset', 'utf8mb4')),
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_house_data(city=None):
    conn = get_db_connection()
    sql = "SELECT * FROM house_info WHERE 1=1"
    params = []

    if city:
        sql += " AND city = %s"
        params.append(city)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        df = pd.DataFrame(rows)
    finally:
        conn.close()

    if not df.empty:
        df["total_price"] = df["price"].apply(_number)
        df["area"] = df["mianji"].apply(_number)
        df["unit_price"] = pd.to_numeric(
            df["unit_price"],
            errors="coerce",
        )

    return df


def basic_statistics(df):
    return {
        'total_count': len(df),
        'avg_total_price': df['total_price'].mean(),
        'median_total_price': df['total_price'].median(),
        'avg_unit_price': df['unit_price'].mean(),
        'median_unit_price': df['unit_price'].median(),
        'avg_area': df['area'].mean(),
        'max_price': df['total_price'].max(),
        'min_price': df['total_price'].min(),
    }


def district_analysis(df):
    return df.groupby('region').agg(
        count=('id', 'count'),
        avg_price=('unit_price', 'mean'),
        median_price=('unit_price', 'median'),
        max_price=('unit_price', 'max'),
        min_price=('unit_price', 'min'),
        avg_area=('area', 'mean'),
    ).round(2).sort_values('avg_price', ascending=False)


def layout_analysis(df):
    return df.groupby('huxing').agg(
        count=('id', 'count'),
        avg_price=('unit_price', 'mean'),
        avg_total_price=('total_price', 'mean'),
    ).round(2).sort_values('count', ascending=False)


def decoration_analysis(df):
    return df.groupby('zhuangxiu').agg(
        count=('id', 'count'),
        avg_unit_price=('unit_price', 'mean'),
        avg_total_price=('total_price', 'mean'),
    ).round(2).sort_values('count', ascending=False)


def _number(value):
    if value in (None, ''):
        return None
    match = re.search(r'\d+(?:\.\d+)?', str(value))
    return float(match.group(0)) if match else None


if __name__ == '__main__':
    df = load_house_data()
    if df.empty:
        print('暂无数据，请先导入 house_info 表。')
    else:
        print(f'数据总量: {len(df)} 条')
        print('\n--- 基本统计 ---')
        for key, value in basic_statistics(df).items():
            print(f'{key}: {value:.2f}' if isinstance(value, float) else f'{key}: {value}')
        print('\n--- 区域分析 Top 10 ---')
        print(district_analysis(df).head(10).to_string())
        print('\n--- 户型分析 Top 10 ---')
        print(layout_analysis(df).head(10).to_string())
