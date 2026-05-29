"""
Item pipelines for data cleaning and storage.
Supports both Django ORM (SQLite/MySQL) and direct MySQL connection.
"""
import os
import sys
import re

from scrapy.exceptions import DropItem

# Add project root to path so we can import Django models
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
import django
django.setup()


class DataCleanPipeline:
    """数据清洗管道"""

    def process_item(self, item):
        # 标题不能为空
        if not item.get('title'):
            raise DropItem("Missing title")

        # 清洗价格
        if item.get('total_price'):
            try:
                item['total_price'] = float(re.sub(r'[^\d.]', '', str(item['total_price'])))
            except (ValueError, TypeError):
                item['total_price'] = None

        if item.get('unit_price'):
            try:
                item['unit_price'] = float(re.sub(r'[^\d.]', '', str(item['unit_price'])))
            except (ValueError, TypeError):
                item['unit_price'] = None

        # 清洗面积
        if item.get('area'):
            try:
                item['area'] = float(re.sub(r'[^\d.]', '', str(item['area'])))
            except (ValueError, TypeError):
                item['area'] = None

        # 清洗楼层
        if item.get('total_floor'):
            try:
                item['total_floor'] = int(re.sub(r'[^\d]', '', str(item['total_floor'])))
            except (ValueError, TypeError):
                item['total_floor'] = None

        # 标准化装修情况
        decoration = item.get('decoration', '')
        if '精' in str(decoration):
            item['decoration'] = '精装'
        elif '简' in str(decoration):
            item['decoration'] = '简装'
        elif '毛坯' in str(decoration):
            item['decoration'] = '毛坯'
        else:
            item['decoration'] = '其他'

        # 电梯处理
        elevator = item.get('elevator', '')
        item['elevator'] = 1 if '有' in str(elevator) else 0

        return item


class DjangoORMPipeline:
    """通过 Django ORM 存储数据（兼容 SQLite 和 MySQL）"""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self):
        from web.apps.house.models import City, District, Community, House
        self.City = City
        self.District = District
        self.Community = Community
        self.House = House

    def process_item(self, item):
        from asgiref.sync import sync_to_async
        # Use synchronous DB access wrapped for async context
        self._save_item(item)
        return item

    def _save_item(self, item):
        from django.db import connection
        # Force a new connection in this context
        connection.ensure_connection()
        try:
            # 获取或创建城市
            city, _ = self.City.objects.get_or_create(
                name=item.get('city', '未知'),
            )

            # 获取或创建区域
            district_name = item.get('district', '').strip()
            if not district_name:
                district_name = '未知'
            district, _ = self.District.objects.get_or_create(
                name=district_name,
                city=city,
            )

            # 获取或创建小区
            community_name = item.get('community', '').strip()
            if not community_name:
                community_name = '未知'
            community, _ = self.Community.objects.get_or_create(
                name=community_name,
                district=district,
                defaults={
                    'longitude': item.get('longitude'),
                    'latitude': item.get('latitude'),
                    'build_year': item.get('house_year'),
                }
            )

            # 创建房源
            self.House.objects.create(
                title=item.get('title', ''),
                community=community,
                total_price=item.get('total_price'),
                unit_price=item.get('unit_price'),
                area=item.get('area'),
                layout=item.get('layout'),
                orientation=item.get('orientation'),
                floor=item.get('floor'),
                total_floor=item.get('total_floor'),
                decoration=item.get('decoration'),
                elevator=bool(item.get('elevator', 0)),
                listing_date=item.get('listing_date') or None,
                house_year=item.get('house_year'),
                source_url=item.get('source_url'),
            )

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error saving item: {e}")
