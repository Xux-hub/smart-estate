"""
测试数据填充脚本
生成模拟房源数据用于开发和测试
"""
import os
import sys
import random
from datetime import datetime, timedelta

import pymysql
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


# 模拟数据配置
DISTRICTS = {
    '北京': ['朝阳', '海淀', '西城', '东城', '丰台', '通州', '大兴', '昌平', '顺义', '房山'],
    '上海': ['浦东', '徐汇', '静安', '黄浦', '长宁', '虹口', '杨浦', '闵行', '宝山', '嘉定'],
    '广州': ['天河', '越秀', '海珠', '荔湾', '白云', '番禺', '黄埔', '花都', '南沙', '增城'],
    '深圳': ['南山', '福田', '罗湖', '宝安', '龙岗', '龙华', '光明', '坪山', '盐田', '大鹏'],
}

COMMUNITIES = [
    '阳光花园', '翠苑小区', '金色家园', '碧水湾', '龙湖天街',
    '万科城', '绿城花园', '保利国际', '中海锦城', '华润置地',
    '恒大名都', '融创壹号', '碧桂园', '世茂滨江', '金地格林',
    '远洋天地', '招商花园', '中粮祥云', '龙光玖龙台', '佳兆业',
]

LAYOUTS = ['一室一厅', '两室一厅', '两室两厅', '三室一厅', '三室两厅', '四室两厅', '五室两厅']
ORIENTATIONS = ['南', '南北', '东南', '西南', '东', '西', '北']
DECORATIONS = ['精装', '简装', '毛坯', '其他']
FLOORS = ['低楼层', '中楼层', '高楼层']

# 各城市基准单价 (元/㎡)
CITY_BASE_PRICE = {
    '北京': 65000,
    '上海': 60000,
    '广州': 40000,
    '深圳': 70000,
}


def get_db_connection():
    config_path = os.path.join(ROOT_DIR, 'config', 'database.yml')
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


def seed_data(num_per_city=200):
    """填充测试数据"""
    print("=" * 50)
    print("智慧房产探索平台 - 填充测试数据")
    print("=" * 50)

    conn = get_db_connection()
    cursor = conn.cursor()

    total_count = 0

    for city_name, districts in DISTRICTS.items():
        print(f"\n生成 {city_name} 数据...")

        # 获取城市 ID
        cursor.execute("SELECT id FROM city WHERE name = %s", (city_name,))
        city_row = cursor.fetchone()
        if not city_row:
            cursor.execute("INSERT INTO city (name) VALUES (%s)", (city_name,))
            conn.commit()
            city_id = cursor.lastrowid
        else:
            city_id = city_row['id']

        base_price = CITY_BASE_PRICE.get(city_name, 30000)

        for district_name in districts:
            # 创建区域
            cursor.execute("SELECT id FROM district WHERE name = %s AND city_id = %s", (district_name, city_id))
            district_row = cursor.fetchone()
            if not district_row:
                cursor.execute("INSERT INTO district (name, city_id) VALUES (%s, %s)", (district_name, city_id))
                conn.commit()
                district_id = cursor.lastrowid
            else:
                district_id = district_row['id']

            # 区域价格系数
            district_factor = random.uniform(0.6, 1.5)

            # 每个区域创建几个小区
            num_communities = random.randint(2, 4)
            for i in range(num_communities):
                community_name = random.choice(COMMUNITIES) + str(random.randint(1, 9)) + '期'

                # 创建小区
                longitude = 116.0 + random.uniform(0, 1)  # 简化的经纬度
                latitude = 39.0 + random.uniform(0, 1)
                build_year = random.randint(1995, 2023)

                cursor.execute(
                    "INSERT INTO community (name, district_id, longitude, latitude, build_year) VALUES (%s, %s, %s, %s, %s)",
                    (community_name, district_id, round(longitude, 7), round(latitude, 7), build_year)
                )
                conn.commit()
                community_id = cursor.lastrowid

                # 每个小区生成若干房源
                num_houses = random.randint(3, 8)
                for _ in range(num_houses):
                    area = round(random.uniform(40, 200), 2)
                    layout = random.choice(LAYOUTS)
                    unit_price = round(base_price * district_factor * random.uniform(0.8, 1.2), 2)
                    total_price = round(unit_price * area / 10000, 2)
                    orientation = random.choice(ORIENTATIONS)
                    total_floor = random.randint(6, 33)
                    floor = random.choice(FLOORS)
                    decoration = random.choice(DECORATIONS)
                    elevator = 1 if total_floor > 7 else random.choice([0, 1])
                    house_year = build_year
                    listing_date = (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')

                    title = f"{community_name} {layout} {floor}"

                    cursor.execute("""
                        INSERT INTO house (title, community_id, total_price, unit_price, area,
                            layout, orientation, floor, total_floor, decoration, elevator,
                            listing_date, house_year, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, (
                        title, community_id, total_price, unit_price, area,
                        layout, orientation, floor, total_floor, decoration, elevator,
                        listing_date, house_year,
                    ))
                    total_count += 1

        conn.commit()
        print(f"  ✓ {city_name} 数据生成完成")

    conn.close()
    print(f"\n✓ 共生成 {total_count} 条房源数据")
    print("现在可以启动 Web 服务查看效果: python manage.py runserver")


if __name__ == '__main__':
    seed_data()
