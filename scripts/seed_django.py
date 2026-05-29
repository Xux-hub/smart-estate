"""
通过 Django ORM 填充测试数据（兼容 SQLite 和 MySQL）
"""
import os
import sys
import random
from datetime import datetime, timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

import django
django.setup()

from web.apps.house.models import City, District, Community, House

# 模拟数据
DISTRICTS_DATA = {
    '北京': ['朝阳', '海淀', '西城', '东城', '丰台', '通州', '大兴', '昌平'],
    '上海': ['浦东', '徐汇', '静安', '黄浦', '长宁', '虹口', '杨浦', '闵行'],
    '广州': ['天河', '越秀', '海珠', '荔湾', '白云', '番禺', '黄埔', '花都'],
    '深圳': ['南山', '福田', '罗湖', '宝安', '龙岗', '龙华', '光明', '坪山'],
}

COMMUNITIES = ['阳光花园', '翠苑小区', '金色家园', '碧水湾', '龙湖天街',
               '万科城', '绿城花园', '保利国际', '中海锦城', '华润置地']
LAYOUTS = ['一室一厅', '两室一厅', '两室两厅', '三室一厅', '三室两厅', '四室两厅']
ORIENTATIONS = ['南', '南北', '东南', '西南', '东', '西']
DECORATIONS = ['精装', '简装', '毛坯', '其他']
FLOORS = ['低楼层', '中楼层', '高楼层']

CITY_BASE_PRICE = {'北京': 65000, '上海': 60000, '广州': 40000, '深圳': 70000}


def seed():
    print("填充测试数据...")
    total = 0

    for city_name, districts in DISTRICTS_DATA.items():
        city, _ = City.objects.get_or_create(name=city_name, defaults={'province': city_name + '市'})
        base_price = CITY_BASE_PRICE[city_name]

        for district_name in districts:
            district, _ = District.objects.get_or_create(name=district_name, city=city)
            district_factor = random.uniform(0.6, 1.5)

            for i in range(random.randint(2, 4)):
                community_name = random.choice(COMMUNITIES) + str(random.randint(1, 9)) + '期'
                community, _ = Community.objects.get_or_create(
                    name=community_name, district=district,
                    defaults={
                        'longitude': round(116.0 + random.uniform(0, 1), 7),
                        'latitude': round(39.0 + random.uniform(0, 1), 7),
                        'build_year': random.randint(1998, 2023),
                    }
                )

                for _ in range(random.randint(3, 6)):
                    area = round(random.uniform(40, 180), 2)
                    layout = random.choice(LAYOUTS)
                    unit_price = round(base_price * district_factor * random.uniform(0.8, 1.2), 2)
                    total_price = round(unit_price * area / 10000, 2)
                    total_floor = random.randint(6, 33)

                    House.objects.create(
                        title=f"{community_name} {layout} {random.choice(FLOORS)}",
                        community=community,
                        total_price=total_price,
                        unit_price=unit_price,
                        area=area,
                        layout=layout,
                        orientation=random.choice(ORIENTATIONS),
                        floor=random.choice(FLOORS),
                        total_floor=total_floor,
                        decoration=random.choice(DECORATIONS),
                        elevator=total_floor > 7,
                        listing_date=datetime.now() - timedelta(days=random.randint(1, 365)),
                        house_year=community.build_year,
                    )
                    total += 1

    print(f"✓ 共生成 {total} 条房源数据")


if __name__ == '__main__':
    seed()
