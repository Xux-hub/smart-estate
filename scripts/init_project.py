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

    db_name = db_config['name']
    print('=' * 60)
    print('Smart Estate database initialization')
    print('=' * 60)
    print(f"MySQL: {db_config['host']}:{db_config['port']}")
    print(f"Database: {db_name}")

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
        sql_content = f.read().replace('`room-estimate`', f'`{_escape_identifier(db_name)}`')

    cursor = conn.cursor()
    try:
        for statement in _split_sql(sql_content):
            cursor.execute(statement)
        cursor.execute(f"USE `{_escape_identifier(db_name)}`")
        _ensure_house_info_indexes(cursor, db_name)
        _sync_dimension_and_stat_tables(cursor)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    print('Done.')
    print('Created/updated tables in the configured database only.')
    print('Synced dimensions: city, district, community.')
    print('Synced stats: house_city_stat, house_region_stat, house_layout_stat, house_decoration_stat.')


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


def _ensure_house_info_indexes(cursor, db_name):
    index_sql = {
        'idx_house_city_region': 'ALTER TABLE house_info ADD INDEX idx_house_city_region (city, region)',
        'idx_house_city_region_unit': 'ALTER TABLE house_info ADD INDEX idx_house_city_region_unit (city, region, unit_price)',
        'idx_house_city_layout': 'ALTER TABLE house_info ADD INDEX idx_house_city_layout (city, huxing)',
        'idx_house_city_decoration': 'ALTER TABLE house_info ADD INDEX idx_house_city_decoration (city, zhuangxiu)',
        'idx_house_mingcheng': 'ALTER TABLE house_info ADD INDEX idx_house_mingcheng (mingcheng)',
        'idx_house_area_group': 'ALTER TABLE house_info ADD INDEX idx_house_area_group (mianji_group)',
        'idx_house_link': 'ALTER TABLE house_info ADD INDEX idx_house_link (link(191))',
    }
    for index_name, sql in index_sql.items():
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.statistics
            WHERE table_schema = %s AND table_name = 'house_info' AND index_name = %s
            """,
            (db_name, index_name),
        )
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.execute(sql)


def _sync_dimension_and_stat_tables(cursor):
    cursor.execute('DELETE FROM community')
    cursor.execute('DELETE FROM district')
    cursor.execute('DELETE FROM city')

    cursor.execute(
        """
        INSERT INTO city (name, house_count, avg_unit_price, community_count)
        SELECT
          city_name,
          COUNT(*) AS house_count,
          AVG(unit_price) AS avg_unit_price,
          COUNT(DISTINCT community_name) AS community_count
        FROM (
          SELECT
            COALESCE(NULLIF(city, ''), '未知') AS city_name,
            COALESCE(NULLIF(mingcheng, ''), '未知小区') AS community_name,
            unit_price
          FROM house_info
        ) t
        GROUP BY city_name
        """
    )

    cursor.execute(
        """
        INSERT INTO district
          (city_id, name, house_count, avg_unit_price, max_unit_price, min_unit_price, community_count)
        SELECT
          c.id,
          t.region_name,
          COUNT(*) AS house_count,
          AVG(t.unit_price) AS avg_unit_price,
          MAX(t.unit_price) AS max_unit_price,
          MIN(t.unit_price) AS min_unit_price,
          COUNT(DISTINCT t.community_name) AS community_count
        FROM (
          SELECT
            COALESCE(NULLIF(city, ''), '未知') AS city_name,
            COALESCE(NULLIF(region, ''), NULLIF(quyu, ''), '未知区域') AS region_name,
            COALESCE(NULLIF(mingcheng, ''), '未知小区') AS community_name,
            unit_price
          FROM house_info
        ) t
        JOIN city c ON c.name = t.city_name
        GROUP BY c.id, t.region_name
        """
    )

    cursor.execute(
        """
        INSERT INTO community
          (district_id, name, longitude, latitude, house_count, avg_unit_price)
        SELECT
          d.id,
          t.community_name,
          MIN(NULLIF(t.jingdu, '')) AS longitude,
          MIN(NULLIF(t.weidu, '')) AS latitude,
          COUNT(*) AS house_count,
          AVG(t.unit_price) AS avg_unit_price
        FROM (
          SELECT
            COALESCE(NULLIF(city, ''), '未知') AS city_name,
            COALESCE(NULLIF(region, ''), NULLIF(quyu, ''), '未知区域') AS region_name,
            COALESCE(NULLIF(mingcheng, ''), '未知小区') AS community_name,
            jingdu,
            weidu,
            unit_price
          FROM house_info
        ) t
        JOIN city c ON c.name = t.city_name
        JOIN district d ON d.city_id = c.id AND d.name = t.region_name
        GROUP BY d.id, t.community_name
        """
    )

    for table_name in [
        'house_city_stat',
        'house_region_stat',
        'house_layout_stat',
        'house_decoration_stat',
    ]:
        cursor.execute(f'DELETE FROM {table_name}')

    cursor.execute(
        """
        INSERT INTO house_city_stat (city, house_count, community_count, avg_unit_price)
        SELECT
          COALESCE(NULLIF(city, ''), '未知') AS city_name,
          COUNT(*) AS house_count,
          COUNT(DISTINCT COALESCE(NULLIF(mingcheng, ''), '未知小区')) AS community_count,
          AVG(unit_price) AS avg_unit_price
        FROM house_info
        GROUP BY city_name
        """
    )
    cursor.execute(
        """
        INSERT INTO house_region_stat
          (city, region, house_count, community_count, avg_unit_price, max_unit_price, min_unit_price)
        SELECT
          COALESCE(NULLIF(city, ''), '未知') AS city_name,
          COALESCE(NULLIF(region, ''), NULLIF(quyu, ''), '未知区域') AS region_name,
          COUNT(*) AS house_count,
          COUNT(DISTINCT COALESCE(NULLIF(mingcheng, ''), '未知小区')) AS community_count,
          AVG(unit_price) AS avg_unit_price,
          MAX(unit_price) AS max_unit_price,
          MIN(unit_price) AS min_unit_price
        FROM house_info
        GROUP BY city_name, region_name
        """
    )
    cursor.execute(
        """
        INSERT INTO house_layout_stat (city, layout_name, house_count, avg_unit_price)
        SELECT
          COALESCE(NULLIF(city, ''), '未知') AS city_name,
          COALESCE(NULLIF(huxing, ''), '未知户型') AS layout_name,
          COUNT(*) AS house_count,
          AVG(unit_price) AS avg_unit_price
        FROM house_info
        GROUP BY city_name, layout_name
        """
    )
    cursor.execute(
        """
        INSERT INTO house_decoration_stat (city, decoration_name, house_count, avg_unit_price)
        SELECT
          COALESCE(NULLIF(city, ''), '未知') AS city_name,
          COALESCE(NULLIF(zhuangxiu, ''), '未知装修') AS decoration_name,
          COUNT(*) AS house_count,
          AVG(unit_price) AS avg_unit_price
        FROM house_info
        GROUP BY city_name, decoration_name
        """
    )


def _escape_identifier(value):
    return str(value).replace('`', '``')


if __name__ == '__main__':
    init_database()
