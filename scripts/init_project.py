import os
import sys

import pymysql
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


def init_database():
    config_path = os.path.join(ROOT_DIR, 'config', 'database.yml')
    with open(config_path, 'r', encoding='utf-8') as f:
        db_config = yaml.safe_load(f)['database']

    print('=' * 50)
    print('智慧房源探索平台 - 数据库初始化')
    print('=' * 50)
    print(f"连接 MySQL: {db_config['host']}:{db_config['port']}")

    conn = pymysql.connect(
        host=db_config['host'],
        port=int(db_config['port']),
        user=db_config['user'],
        password=db_config.get('password') or '',
        charset=db_config.get('charset', 'utf8mb4'),
        autocommit=False,
    )

    sql_path = os.path.join(ROOT_DIR, 'database', 'init_db.sql')
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    cursor = conn.cursor()
    try:
        for statement in _split_sql(sql_content):
            cursor.execute(statement)
        conn.commit()
        print('数据库初始化完成')
        print(f"数据库名: {db_config['name']}")
        print('已确保表存在: house_info, raw_house_data, abnormal_house_data, analysis_result')
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def _split_sql(sql_content):
    statements = []
    current = []
    for line in sql_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        current.append(line)
        if stripped.endswith(';'):
            statements.append('\n'.join(current).rstrip(';').strip())
            current = []
    if current:
        statements.append('\n'.join(current).strip())
    return statements


if __name__ == '__main__':
    init_database()
