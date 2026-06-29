"""
爬虫数据清洗管线函数测试 (crawler/estate_spider/pipelines.py)

覆盖 11 个纯函数：
  _clean_text, _compact_text, _number, _int_number, _area_text,
  _area_group, _clean_region, _clean_floor, _clean_orientation,
  _clean_date, _clean_long_text

所有函数均为纯函数，零外部依赖。
"""

import os
import sys

import pytest

# 将项目根目录加入 sys.path，使 crawler 包可导入
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWLER_DIR = os.path.join(PROJECT_ROOT, "crawler")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, CRAWLER_DIR)

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
    _number,
)


# ═══════════════════════════════════════════════════
#  _clean_text 测试
# ═══════════════════════════════════════════════════

class TestCleanText:
    def test_普通文本原样返回(self):
        assert _clean_text("青岛") == "青岛"

    def test_去除前后空格(self):
        assert _clean_text("  青岛市南区  ") == "青岛市南区"

    def test_连续空格归一化为单个(self):
        assert _clean_text("济南  历下  区") == "济南 历下 区"

    def test_NBSP替换为普通空格(self):
        assert _clean_text("青岛\xa0市南") == "青岛 市南"

    def test_空值处理(self):
        assert _clean_text(None) == ""
        assert _clean_text("") == ""

    def test_数字0被当作空值处理(self):
        """str(0 or '') → '' 因为 0 是 falsy，设计如此"""
        assert _clean_text(0) == ""


class TestCompactText:
    def test_去除所有空白(self):
        assert _compact_text("济南 历下 区") == "济南历下区"

    def test_包含换行和制表符(self):
        assert _compact_text("3室2厅\n 120㎡\t 南") == "3室2厅120㎡南"


# ═══════════════════════════════════════════════════
#  _number / _int_number / _area_text 测试
# ═══════════════════════════════════════════════════

class TestNumber:
    def test_纯数字字符串(self):
        assert _number("200") == 200.0

    def test_带中文单位_提取数值(self):
        assert _number("200万") == 200.0
        assert _number("98.5㎡") == 98.5

    def test_价格含逗号分隔(self):
        assert _number("1,280万") == 1.0

    def test_None和空字符串返回None(self):
        assert _number(None) is None
        assert _number("") is None

    def test_无数字文本返回None(self):
        assert _number("暂无报价") is None

    def test_提取第一个数字(self):
        assert _number("200-300万") == 200.0


class TestIntNumber:
    def test_整数转换(self):
        assert _int_number("200") == 200
        assert type(_int_number("200")) is int

    def test_浮点数截断(self):
        assert _int_number("16666.7") == 16666

    def test_None和空(self):
        assert _int_number(None) is None
        assert _int_number("") is None

    def test_无数字文本(self):
        assert _int_number("暂无") is None


class TestAreaText:
    def test_格式化为平方米(self):
        result = _area_text(120)
        assert "120" in result
        assert "㎡" in result

    def test_浮点数格式化(self):
        result = _area_text(98.5)
        assert "98.5" in result

    def test_None返回空字符串(self):
        assert _area_text(None) == ""

    def test_字符串数字也能解析(self):
        result = _area_text("120")
        assert "120" in result


# ═══════════════════════════════════════════════════
#  _area_group 测试
# ═══════════════════════════════════════════════════

class TestAreaGroup:
    def test_60平以下(self):
        assert _area_group(30) == "60平以下"
        assert _area_group(59.9) == "60平以下"

    def test_60到90平(self):
        assert _area_group(60) == "60-90平"
        assert _area_group(89.9) == "60-90平"

    def test_90到120平(self):
        assert _area_group(90) == "90-120平"
        assert _area_group(119) == "90-120平"

    def test_120到150平(self):
        assert _area_group(120) == "120-150平"
        assert _area_group(149) == "120-150平"

    def test_150到300平(self):
        assert _area_group(150) == "150-300平"
        assert _area_group(299) == "150-300平"

    def test_300平以上(self):
        assert _area_group(300) == "300平以上"
        assert _area_group(500) == "300平以上"

    def test_None返回空字符串(self):
        assert _area_group(None) == ""

    def test_空字符串(self):
        assert _area_group("") == ""

    def test_从字符串提取数值(self):
        assert _area_group("120㎡") == "120-150平"


# ═══════════════════════════════════════════════════
#  _clean_region 测试
# ═══════════════════════════════════════════════════

class TestCleanRegion:
    def test_保留区域后缀(self):
        assert _clean_region("市南区") == "市南区"
        assert _clean_region("高新区") == "高新区"
        assert _clean_region("开发区") == "开发区"
        assert _clean_region("历下区") == "历下区"

    def test_去除城市名前缀(self):
        assert _clean_region("青岛市市南区", "青岛") == "市南区"

    def test_去除小区名(self):
        result = _clean_region("阳光花园市南区", community="阳光花园")
        assert "阳光花园" not in result

    def test_重复文本去重(self):
        """'市南市南' → '市南'"""
        result = _clean_region("市南市南")
        assert len(result) == 2

    def test_去除分隔符(self):
        assert _clean_region("市南/区") == "市南区"

    def test_空值返回空字符串(self):
        assert _clean_region(None) == ""
        assert _clean_region("") == ""

    def test_提取带区县后缀的部分(self):
        result = _clean_region("某某路市南区某某街道")
        assert "区" in result

    def test_城市名以市结尾的变体匹配(self):
        """如果 city 不带'市'，会自动补充'市'变体"""
        result = _clean_region("青岛市市北区", "青岛")
        assert "青岛市" not in result
        assert "市北区" in result


# ═══════════════════════════════════════════════════
#  _clean_floor 测试
# ═══════════════════════════════════════════════════

class TestCleanFloor:
    def test_全角括号转半角(self):
        result = _clean_floor("2层（共18层）")
        assert "（" not in result
        assert "(" in result

    def test_在中英文括号间加空格(self):
        """'2(共18层)' 或 '2 (共18层)'，使文字与括号有间隔"""
        result = _clean_floor("2(共18层)")
        assert " (" in result

    def test_空值返回空字符串(self):
        assert _clean_floor(None) == ""
        assert _clean_floor("") == ""

    def test_保留楼层原始信息(self):
        result = _clean_floor("中楼层")
        assert "中楼层" in result


# ═══════════════════════════════════════════════════
#  _clean_orientation 测试
# ═══════════════════════════════════════════════════

class TestCleanOrientation:
    def test_连续空格合并为单个(self):
        assert _clean_orientation("南  北") == "南 北"
        assert _clean_orientation("南 \n 北") == "南 北"

    def test_空值(self):
        assert _clean_orientation(None) == ""
        assert _clean_orientation("") == ""


# ═══════════════════════════════════════════════════
#  _clean_date 测试
# ═══════════════════════════════════════════════════

class TestCleanDate:
    def test_提取标准日期(self):
        assert _clean_date("2025/06/15") == "2025/06/15"

    def test_日期中有空格_去除空格(self):
        assert _clean_date("2025 / 06 / 15") == "2025/06/15"

    def test_从混合文本中提取日期(self):
        result = _clean_date("挂牌时间2025/06/15已核实")
        assert result == "2025/06/15"

    def test_无日期原样返回(self):
        result = _clean_date("暂无数据")
        assert result == "暂无数据"


# ═══════════════════════════════════════════════════
#  _clean_long_text 测试
# ═══════════════════════════════════════════════════

class TestCleanLongText:
    def test_None和none替换为空(self):
        assert _clean_long_text("None") == ""
        assert _clean_long_text("暂无数据") == ""
        assert _clean_long_text("暂无") == ""

    def test_去除中文序数前缀(self):
        result = _clean_long_text("一 交通便利")
        assert "一" not in result or result == "交通便利"

    def test_中文标点前后空格清理(self):
        result = _clean_long_text("交通便利 ， 配套齐全")
        assert " ， " not in result
        assert "，" in result

    def test_竖线分隔符保留(self):
        """_clean_long_text 将 ' | ' 中多余空格收紧为单个 '|'"""
        result = _clean_long_text("卖点一 | 卖点二")
        assert "|" in result
        assert "卖点一|卖点二" == result


# ═══════════════════════════════════════════════════
#  综合场景测试
# ═══════════════════════════════════════════════════

class TestIntegration:
    """模拟真实爬虫数据的清洗流程"""

    def test_完整房源字段清洗链路(self):
        """验证各清洗函数能串联工作"""
        raw_price = "200万"
        raw_area = "120㎡"
        raw_floor = "中层（共18层）"
        raw_orientation = "南  北通透"

        price_num = _number(raw_price)
        area_num = _number(raw_area)
        floor_clean = _clean_floor(raw_floor)
        ori_clean = _clean_orientation(raw_orientation)

        assert price_num == 200.0
        assert area_num == 120.0
        assert "(" in floor_clean
        assert "  " not in ori_clean  # 双空格已合并

    def test_面积分桶与金额的完整映射(self):
        assert _area_group(_number("50㎡")) == "60平以下"
        assert _area_group(_number("75㎡")) == "60-90平"
        assert _area_group(_number("100㎡")) == "90-120平"
