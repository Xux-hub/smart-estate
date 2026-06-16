import os
import re
import sys

from scrapy.exceptions import DropItem

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
import django

django.setup()


class DataCleanPipeline:
    def process_item(self, item, spider):
        if not item.get('title') and not item.get('community'):
            raise DropItem('missing house title/community')

        item['total_price'] = _number(item.get('total_price'))
        item['unit_price'] = _int_number(item.get('unit_price'))
        item['area'] = _number(item.get('area'))
        return item


class DjangoORMPipeline:
    def open_spider(self, spider):
        from web.apps.house.models import House

        self.House = House

    def process_item(self, item, spider):
        self.House.objects.create(
            city=item.get('city') or '',
            region=item.get('district') or '',
            link=item.get('source_url') or '',
            mingcheng=item.get('community') or item.get('title') or '',
            quyu=item.get('district') or '',
            huxing=item.get('layout') or '',
            louceng=item.get('floor') or '',
            mianji=_area_text(item.get('area')),
            chaoxiang=item.get('orientation') or '',
            zhuangxiu=item.get('decoration') or '',
            shijian=item.get('listing_date') or '',
            price=str(item.get('total_price') or ''),
            unit_price=item.get('unit_price'),
            jingdu=str(item.get('longitude') or ''),
            weidu=str(item.get('latitude') or ''),
        )
        return item


def _number(value):
    if value in (None, ''):
        return None
    match = re.search(r'\d+(?:\.\d+)?', str(value))
    return float(match.group(0)) if match else None


def _int_number(value):
    number = _number(value)
    return int(number) if number is not None else None


def _area_text(value):
    number = _number(value)
    return f'{number:g}㎡' if number is not None else ''
