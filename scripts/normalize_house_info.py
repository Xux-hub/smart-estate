import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

import django

django.setup()

from crawler.estate_spider.pipelines import (
    _area_group,
    _area_text,
    _clean_date,
    _clean_floor,
    _clean_long_text,
    _clean_orientation,
    _clean_region,
    _clean_text,
    _compact_text,
    _int_number,
)
from web.apps.house.models import House


UPDATE_FIELDS = [
    'region',
    'quyu',
    'huxing',
    'louceng',
    'mianji',
    'huxingjiegou',
    'chaoxiang',
    'jianzhujiegou',
    'zhuangxiu',
    'tihu',
    'shijian',
    'quanshu',
    'diya',
    'unit_price',
    'jingdu',
    'weidu',
    'maidian',
    'jieshao',
    'huxingjieshao',
    'jiaotong',
    'mianji_group',
]


def normalize_house(house):
    region = _clean_region(house.region or house.quyu, house.city, house.mingcheng)
    quyu = _clean_region(house.quyu or region, house.city, house.mingcheng) or region

    house.region = region
    house.quyu = quyu
    house.huxing = _compact_text(house.huxing)
    house.louceng = _clean_floor(house.louceng)
    house.mianji = _area_text(house.mianji)
    house.huxingjiegou = _clean_text(house.huxingjiegou)
    house.chaoxiang = _clean_orientation(house.chaoxiang)
    house.jianzhujiegou = _clean_text(house.jianzhujiegou)
    house.zhuangxiu = _clean_text(house.zhuangxiu)
    house.tihu = _compact_text(house.tihu)
    house.shijian = _clean_date(house.shijian)
    house.quanshu = _clean_text(house.quanshu)
    house.diya = _clean_text(house.diya)
    house.unit_price = _int_number(house.unit_price)
    house.jingdu = _clean_text(house.jingdu)
    house.weidu = _clean_text(house.weidu)
    house.maidian = _clean_long_text(house.maidian)
    house.jieshao = _clean_long_text(house.jieshao)
    house.huxingjieshao = _clean_long_text(house.huxingjieshao)
    house.jiaotong = _clean_long_text(house.jiaotong)
    house.mianji_group = _area_group(house.mianji)
    return house


def main():
    parser = argparse.ArgumentParser(description='Normalize existing rows in house_info.')
    parser.add_argument('--limit', type=int, default=0, help='Only normalize the first N rows.')
    parser.add_argument('--dry-run', action='store_true', help='Print count without saving changes.')
    args = parser.parse_args()

    queryset = House.objects.all().order_by('id')
    if args.limit:
        queryset = queryset[:args.limit]

    count = 0
    for house in queryset.iterator():
        normalize_house(house)
        count += 1
        if not args.dry_run:
            house.save(update_fields=UPDATE_FIELDS)

    action = 'checked' if args.dry_run else 'normalized'
    print(f'{action} {count} house_info row(s)')


if __name__ == '__main__':
    main()
