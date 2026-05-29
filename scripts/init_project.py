"""
项目初始化脚本
创建数据库和表结构
"""
import os
import sys

import pymysql
import yaml

# Project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


def init_database():
    """初始化数据库"""
    # 读取配置
    config_path = os.path.join(ROOT_DIR, 'config', 'database.yml')
    with open(config_path, 'r', encoding='utf-8') as f:
        db_config = yaml.safe_load(f)['database']

    print("=" * 50)
    print("智慧房产探索平台 - 数据库初始化")
    print("=" * 50)
    print(f"\n连接数据库: {db_config['host']}:{db_config['port']}")

    # 先连接 MySQL（不指定数据库）
    conn = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        charset=db_config['charset'],
    )

    # 读取 SQL 文件
    sql_path = os.path.join(ROOT_DIR, 'database', 'init_db.sql')
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 执行 SQL
    cursor = conn.cursor()
    try:
        # 分割并执行每条 SQL 语句
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        for statement in statements:
            if statement and not statement.startswith('--'):
                cursor.execute(statement)
                print(f"  ✓ 执行: {statement[:60]}...")

        conn.commit()
        print("\n✓ 数据库初始化完成！")
        print(f"  数据库名: {db_config['name']}")
        print("  已创建表: city, district, community, house, price_prediction, facility")
        print("  已插入初始城市数据")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ 初始化失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    init_database()
