"""
House 模型属性方法测试 (web/apps/house/models.py)

覆盖：
  _to_decimal 函数 (1)
  House @property 方法 (10): title, total_price, area, layout,
    orientation, floor, decoration, district_name, community_name, location_label

所有方法均为纯属性访问，零数据库依赖。
"""

import os
import sys
from decimal import Decimal

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
import django

django.setup()

from web.apps.house.models import House, _to_decimal


def make_house(**kwargs):
    """
    构造一个未持久化的 House 实例用于测试属性方法。
    只设置字段值，不调用 .save()。
    """
    defaults = {
        "city": "青岛",
        "region": "市南区",
        "mingcheng": "阳光花园",
        "quyu": "市南核心区",
        "huxing": "3室2厅",
        "louceng": "中楼层（共18层）",
        "mianji": "120㎡",
        "chaoxiang": "南北通透",
        "zhuangxiu": "精装修",
        "price": "200万",
        "unit_price": 16666,
        "jingdu": "120.38",
        "weidu": "36.07",
    }
    defaults.update(kwargs)
    house = House(**defaults)
    return house


# ═══════════════════════════════════════════════════
#  _to_decimal 测试
# ═══════════════════════════════════════════════════

class TestToDecimal:
    def test_纯数字字符串(self):
        assert _to_decimal("200") == Decimal("200")

    def test_带中文单位(self):
        assert _to_decimal("200万") == Decimal("200")

    def test_带面积单位(self):
        assert _to_decimal("98.5㎡") == Decimal("98.5")

    def test_提取第一个数字(self):
        assert _to_decimal("200-300万") == Decimal("200")

    def test_None返回None(self):
        assert _to_decimal(None) is None

    def test_空字符串返回None(self):
        assert _to_decimal("") is None

    def test_无数字文本返回None(self):
        assert _to_decimal("暂无报价") is None

    def test_返回类型是Decimal(self):
        result = _to_decimal("200")
        assert isinstance(result, Decimal)


# ═══════════════════════════════════════════════════
#  House @property 测试
# ═══════════════════════════════════════════════════

class TestHouseTitle:
    def test_拼接小区户型和面积(self):
        h = make_house()
        title = h.title
        assert "阳光花园" in title
        assert "3室2厅" in title
        assert "120㎡" in title

    def test_部分字段为空的拼接(self):
        h = make_house(huxing="", mianji="")
        title = h.title
        assert "阳光花园" in title
        assert title  # 不会崩溃


class TestHouseTotalPrice:
    def test_提取价格数字(self):
        h = make_house(price="200万")
        assert h.total_price == Decimal("200")

    def test_空价格返回None(self):
        h = make_house(price="")
        assert h.total_price is None


class TestHouseArea:
    def test_提取面积数字(self):
        h = make_house(mianji="120㎡")
        assert h.area == Decimal("120")


class TestHouseAliasProperties:
    """layout / orientation / floor / decoration 是字段的别名"""

    def test_layout(self):
        h = make_house(huxing="4室2厅")
        assert h.layout == "4室2厅"

    def test_orientation(self):
        h = make_house(chaoxiang="南")
        assert h.orientation == "南"

    def test_floor(self):
        h = make_house(louceng="低楼层")
        assert h.floor == "低楼层"

    def test_decoration(self):
        h = make_house(zhuangxiu="毛坯")
        assert h.decoration == "毛坯"


class TestHouseDistrictName:
    def test_优先取region(self):
        h = make_house(region="市南区", quyu="核心区")
        assert h.district_name == "市南区"

    def test_region为空时取quyu(self):
        h = make_house(region="", quyu="核心区")
        assert h.district_name == "核心区"

    def test_都为空返回空字符串(self):
        h = make_house(region="", quyu="")
        assert h.district_name == ""


class TestHouseCommunityName:
    def test_返回小区名(self):
        h = make_house(mingcheng="阳光花园")
        assert h.community_name == "阳光花园"

    def test_空返回空字符串(self):
        h = make_house(mingcheng="")
        assert h.community_name == ""


class TestHouseLocationLabel:
    def test_拼接完整位置(self):
        h = make_house(city="青岛", region="市南区", mingcheng="阳光花园")
        label = h.location_label
        assert "青岛" in label
        assert "市南区" in label
        assert "阳光花园" in label
        assert " - " in label

    def test_部分位置缺失(self):
        h = make_house(city="青岛", region="", mingcheng="阳光花园")
        label = h.location_label
        assert "青岛" in label
        assert "阳光花园" in label
