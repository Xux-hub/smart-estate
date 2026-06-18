import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

import django

django.setup()

from web.apps.house.models import House


DISTRICTS_DATA = {
    '济南': ['历下区', '市中区', '槐荫区', '天桥区', '历城区'],
    '青岛': ['市南区', '市北区', '崂山区', '李沧区', '黄岛区'],
    '烟台': ['芝罘区', '莱山区', '福山区', '牟平区'],
}

COMMUNITIES = ['阳光花园', '万科城', '中海国际', '绿地新城', '保利公园', '龙湖天街']
LAYOUTS = ['一室一厅', '两室一厅', '两室两厅', '三室一厅', '三室两厅', '四室两厅']
ORIENTATIONS = ['南', '南北', '东南', '西南', '东', '西']
DECORATIONS = ['精装', '简装', '毛坯', '其他']
FLOORS = ['低楼层', '中楼层', '高楼层']
CITY_BASE_PRICE = {'济南': 18000, '青岛': 24000, '烟台': 13000}


def seed():
    total = 0
    for city_name, districts in DISTRICTS_DATA.items():
        base_price = CITY_BASE_PRICE[city_name]
        for district_name in districts:
            district_factor = random.uniform(0.75, 1.35)
            for _ in range(20):
                area = round(random.uniform(45, 180), 2)
                unit_price = int(base_price * district_factor * random.uniform(0.85, 1.2))
                total_price = round(unit_price * area / 10000, 2)
                community = random.choice(COMMUNITIES) + str(random.randint(1, 9)) + '期'
                House.objects.create(
                    city=city_name,
                    region=district_name,
                    link='',
                    mingcheng=community,
                    quyu=f'{city_name}{district_name}',
                    huxing=random.choice(LAYOUTS),
                    louceng=random.choice(FLOORS),
                    mianji=f'{area}㎡',
                    chaoxiang=random.choice(ORIENTATIONS),
                    zhuangxiu=random.choice(DECORATIONS),
                    shijian=(datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d'),
                    price=str(total_price),
                    unit_price=unit_price,
                    jingdu=str(round(117 + random.uniform(-1, 1), 6)),
                    weidu=str(round(36 + random.uniform(-1, 1), 6)),
                    maidian='交通便利，配套成熟。',
                    jieshao='小区生活氛围较好，周边商业、教育资源较完整。',
                    huxingjieshao='户型方正，采光较好。',
                    jiaotong='临近主干道和公共交通站点。',
                )
                total += 1
    print(f'已生成 {total} 条 house_info 测试数据')


if __name__ == '__main__':
    seed()
