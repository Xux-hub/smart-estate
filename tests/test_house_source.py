"""
爬虫辅助函数测试 (crawler/estate_spider/spiders/house_source.py)

覆盖 13 个模块级纯函数：
  _clean_text, _first, _first_text, _number, _area_group,
  _set_query, _line_from_url, _codes_from_line,
  _detect_total_pages, _strip_listing_suffix, _pick_region,
  _label_values, _feature_values

所有函数均为纯函数，label_values/feature_values/detect_total_pages
接受 lxml Element 作为输入。
"""

import os
import sys

import pytest
from lxml import html

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWLER_DIR = os.path.join(PROJECT_ROOT, "crawler")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, CRAWLER_DIR)  # estate_spider 包在 crawler/ 目录下

from crawler.estate_spider.spiders.house_source import (
    _area_group,
    _clean_text,
    _codes_from_line,
    _detect_total_pages,
    _feature_values,
    _first,
    _first_text,
    _label_values,
    _line_from_url,
    _number,
    _pick_region,
    _set_query,
    _strip_listing_suffix,
)


# ═══════════════════════════════════════════════════
#  _clean_text / _number / _area_group
# ═══════════════════════════════════════════════════

class TestCleanText:
    def test_空格归一化(self):
        assert _clean_text("青岛  市南") == "青岛 市南"

    def test_前后空格去除(self):
        assert _clean_text("  济南  ") == "济南"

    def test_NBSP替换(self):
        assert "\xa0" not in _clean_text("青岛\xa0市南")

    def test_空值(self):
        assert _clean_text(None) == ""
        assert _clean_text("") == ""


class TestNumber:
    def test_提取数值(self):
        assert _number("200万") == 200.0

    def test_无数字返回None(self):
        assert _number("暂无") is None

    def test_None返回None(self):
        assert _number(None) is None


class TestAreaGroup:
    def test_各区间分桶(self):
        assert _area_group(50) == "60平以下"
        assert _area_group(80) == "60-90平"
        assert _area_group(100) == "90-120平"
        assert _area_group(130) == "120-150平"
        assert _area_group(200) == "150-300平"
        assert _area_group(350) == "300平以上"

    def test_None返回空字符串(self):
        assert _area_group(None) == ""


# ═══════════════════════════════════════════════════
#  _first / _first_text
# ═══════════════════════════════════════════════════

class TestFirst:
    def test_返回第一个元素(self):
        assert _first(["a", "b", "c"]) == "a"

    def test_空列表返回空字符串(self):
        assert _first([]) == ""


class TestFirstText:
    def test_合并文本(self):
        result = _first_text(["青岛", "市南", "区"])
        assert result == "青岛市南区"

    def test_空列表(self):
        assert _first_text([]) == ""


# ═══════════════════════════════════════════════════
#  URL 辅助函数
# ═══════════════════════════════════════════════════

class TestSetQuery:
    def test_设置参数(self):
        url = "http://example.com/list?line=qingdao"
        result = _set_query(url, page=3)
        assert "page=3" in result
        assert "line=qingdao" in result

    def test_替换已有参数(self):
        url = "http://example.com/list?page=1"
        result = _set_query(url, page=5)
        assert "page=5" in result
        assert "page=1" not in result

    def test_新增参数(self):
        url = "http://example.com/list"
        result = _set_query(url, page=2)
        assert "page=2" in result


class TestLineFromUrl:
    def test_提取line参数(self):
        url = "http://example.com/list?line=qingdao/shinan"
        assert _line_from_url(url) == "qingdao/shinan"

    def test_无line参数(self):
        url = "http://example.com/list"
        assert _line_from_url(url) == ""


class TestCodesFromLine:
    def test_城市和区域拆分(self):
        city_code, region_code = _codes_from_line("qingdao/shinan")
        assert city_code == "qingdao"
        assert region_code == "shinan"

    def test_只有城市(self):
        city_code, region_code = _codes_from_line("jinan")
        assert city_code == "jinan"
        assert region_code == ""

    def test_空字符串(self):
        city_code, region_code = _codes_from_line("")
        assert city_code == ""
        assert region_code == ""


# ═══════════════════════════════════════════════════
#  _detect_total_pages（接受 lxml Element）
# ═══════════════════════════════════════════════════

class TestDetectTotalPages:
    def test_从共X页文本中提取(self):
        doc = html.fromstring(
            '<div class="pagination">共100页</div>'
        )
        assert _detect_total_pages(doc) == 100

    def test_从链接参数中提取最大值(self):
        doc = html.fromstring(
            '<div class="pagination">'
            '<a href="/list?page=1">1</a>'
            '<a href="/list?page=5">5</a>'
            '<a href="/list?page=3">3</a>'
            "</div>"
        )
        assert _detect_total_pages(doc) == 5

    def test_没有分页返回1(self):
        doc = html.fromstring("<div></div>")
        assert _detect_total_pages(doc) == 1

    def test_同时有文本和链接取最大值(self):
        doc = html.fromstring(
            '<div class="pagination">'
            '共50页'
            '<a href="/list?page=100">100</a>'
            "</div>"
        )
        assert _detect_total_pages(doc) == 100


# ═══════════════════════════════════════════════════
#  _strip_listing_suffix / _pick_region
# ═══════════════════════════════════════════════════

class TestStripListingSuffix:
    def test_去除挂牌后缀(self):
        assert _strip_listing_suffix("2025/06/15 挂牌") == "2025/06/15"

    def test_无挂牌后缀原样返回(self):
        assert _strip_listing_suffix("2025/06/15") == "2025/06/15"

    def test_只有挂牌(self):
        result = _strip_listing_suffix("挂牌")
        assert result == "" or "挂牌" not in result


class TestPickRegion:
    def test_从列表中选出区域名(self):
        texts = ["青岛", "市南区", "某某街道"]
        result = _pick_region(texts)
        assert "区" in result

    def test_优先新区开发区(self):
        texts = ["某某街道", "高新区", "市南区"]
        result = _pick_region(texts)
        assert result == "高新区"

    def test_空列表返回空(self):
        assert _pick_region([]) == ""


# ═══════════════════════════════════════════════════
#  _label_values / _feature_values（接受 lxml Element）
# ═══════════════════════════════════════════════════

class TestLabelValues:
    def test_提取键值对(self):
        html_str = (
            '<div class="introContent">'
            '<ul>'
            '<li><span class="label">房屋户型</span>3室2厅</li>'
            '<li><span class="label">所在楼层</span>中楼层</li>'
            '<li><span class="label">建筑面积</span>120㎡</li>'
            "</ul>"
            "</div>"
        )
        doc = html.fromstring(html_str)
        values = _label_values(doc)
        assert values["房屋户型"] == "3室2厅"
        assert values["所在楼层"] == "中楼层"
        assert values["建筑面积"] == "120㎡"


class TestFeatureValues:
    def test_提取卖点等长文本块(self):
        html_str = (
            '<div class="baseattribute">'
            '<div class="name">核心卖点</div>'
            '<div class="content">交通便利，配套齐全</div>'
            "</div>"
            '<div class="baseattribute">'
            '<div class="name">小区介绍</div>'
            '<div class="content">绿化率高</div>'
            "</div>"
        )
        doc = html.fromstring(html_str)
        values = _feature_values(doc)
        assert values["核心卖点"] == "交通便利，配套齐全"
        assert values["小区介绍"] == "绿化率高"

    def test_空页面返回空字典(self):
        doc = html.fromstring("<div></div>")
        assert _feature_values(doc) == {}
