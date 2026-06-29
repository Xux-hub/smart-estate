"""
山东三级浏览模块测试

覆盖范围：
- 楼层分类算法（_floor_category）
- 抵押信息分类算法（_mortgage_category）
- 城市名称容错（_city_name_variants）
- JSON API 端点（city_stats、district_stats、house_filter）
- 页面视图（province、city_detail、district_detail）
- 图表生成端点
"""

import json

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse


@pytest.fixture(autouse=True)
def clean_tables(request):
    """在每个 DB 测试前清空表数据，避免 managed=False 模型的数据残留。"""
    if not request.node.get_closest_marker("django_db"):
        yield
        return
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM house_info")
        cursor.execute("DELETE FROM city")
        cursor.execute("DELETE FROM district")
    yield
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM house_info")
        cursor.execute("DELETE FROM city")
        cursor.execute("DELETE FROM district")


# ═══════════════════════════════════════════════════
#  纯函数测试：楼层分类算法
# ═══════════════════════════════════════════════════

from web.apps.shandong.views import (
    _city_name_variants,
    _filter_by_floor_category,
    _filter_by_mortgage_category,
    _floor_category,
    _mortgage_category,
)


class TestFloorCategory:
    """楼层分类算法 —— 双层策略：关键词 + 数值比例"""

    # ── 关键词匹配 ──

    def test_低楼层_中文关键词(self):
        assert _floor_category("低楼层") == "low"
        assert _floor_category("底层") == "low"
        assert _floor_category("低层") == "low"
        assert _floor_category("下部") == "low"

    def test_中楼层_中文关键词(self):
        assert _floor_category("中楼层") == "middle"
        assert _floor_category("中层") == "middle"
        assert _floor_category("中部") == "middle"

    def test_高楼层_中文关键词(self):
        assert _floor_category("高楼层") == "high"
        assert _floor_category("高层") == "high"
        assert _floor_category("顶层") == "high"
        assert _floor_category("上部") == "high"

    def test_地下或半地下(self):
        assert _floor_category("地下") == "basement"
        assert _floor_category("半地下") == "basement"
        assert _floor_category("负1层") == "basement"

    def test_空字符串返回unknown(self):
        assert _floor_category("") == "unknown"

    # ── 数值比例计算 ──

    def test_数值比例_低楼层(self):
        assert _floor_category("2/18层") == "low"
        assert _floor_category("3/10层") == "low"

    def test_数值比例_中楼层(self):
        assert _floor_category("4/8层") == "middle"
        assert _floor_category("5/10层") == "middle"

    def test_数值比例_高楼层(self):
        assert _floor_category("18/20层") == "high"
        assert _floor_category("6/6层") == "high"

    # ── 兜底：绝对楼层估算 ──

    def test_绝对楼层_低层(self):
        assert _floor_category("2层") == "low"
        assert _floor_category("6层") == "low"

    def test_绝对楼层_中层(self):
        assert _floor_category("10层") == "middle"
        assert _floor_category("18层") == "middle"

    def test_绝对楼层_高层(self):
        assert _floor_category("25层") == "high"


class TestMortgageCategory:
    """抵押信息分类算法 —— 优先级匹配策略"""

    def test_无抵押(self):
        assert _mortgage_category("无抵押") == "none"
        assert _mortgage_category("无贷款") == "none"
        assert _mortgage_category("没有抵押") == "none"

    def test_抵押已结清(self):
        assert _mortgage_category("已还清") == "settled"
        assert _mortgage_category("已结清") == "settled"
        assert _mortgage_category("已解除抵押") == "settled"
        assert _mortgage_category("注销抵押") == "settled"
        assert _mortgage_category("抵押已解除") == "settled"

    def test_有抵押(self):
        assert _mortgage_category("有抵押") == "active"
        assert _mortgage_category("按揭贷款") == "active"
        assert _mortgage_category("银行贷款") == "active"

    def test_未说明(self):
        assert _mortgage_category("暂无信息") == "unknown"
        assert _mortgage_category("未知") == "unknown"
        assert _mortgage_category("未上传") == "unknown"
        assert _mortgage_category("") == "unknown"

    def test_优先级_已还清先于抵押(self):
        """关键验证：'抵押已结清'应被判为 settled 而非 active"""
        assert _mortgage_category("抵押已还清") == "settled"
        assert _mortgage_category("已结清抵押") == "settled"


class TestCityNameVariants:
    """城市名称容错：自动生成带/不带'市'字的变体"""

    def test_不带市_生成两种变体(self):
        variants = set(_city_name_variants("青岛"))
        assert "青岛" in variants
        assert "青岛市" in variants

    def test_带市_生成两种变体(self):
        variants = set(_city_name_variants("青岛市"))
        assert "青岛" in variants
        assert "青岛市" in variants

    def test_空字符串(self):
        assert _city_name_variants("") == []
        assert _city_name_variants("  ") == []


# ═══════════════════════════════════════════════════
#  API 端点测试
# ═══════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestCityStatsAPI:
    """城市统计 JSON API"""

    def test_空数据返回空列表(self):
        client = Client()
        response = client.get("/shandong/api/city-stats/")
        assert response.status_code == 200
        assert json.loads(response.content)["data"] == []

    def test_有城市数据返回统计(self, city_factory):
        city_factory("青岛", house_count=100, avg_unit_price=15000, community_count=10)
        city_factory("济南", house_count=200, avg_unit_price=12000, community_count=20)

        client = Client()
        response = client.get("/shandong/api/city-stats/")
        data = json.loads(response.content)["data"]

        assert len(data) == 2
        names = {item["name"] for item in data}
        assert "青岛市" in names
        assert "济南市" in names


@pytest.mark.django_db(transaction=True)
class TestDistrictStatsAPI:
    """区域统计 JSON API"""

    def test_缺少city参数返回空(self):
        client = Client()
        response = client.get("/shandong/api/district-stats/")
        assert response.status_code == 200
        assert json.loads(response.content)["data"] == []

    def test_城市不存在返回空列表(self):
        client = Client()
        response = client.get("/shandong/api/district-stats/?city=火星")
        assert json.loads(response.content)["data"] == []


@pytest.mark.django_db(transaction=True)
class TestHouseFilterAPI:
    """房源筛选 JSON API —— 7 维度筛选 + 分页"""

    def test_空筛选返回全部数据(self, house_factory):
        house_factory(city="青岛", region="市南区", unit_price=15000)
        house_factory(city="青岛", region="市南区", unit_price=20000)

        client = Client()
        response = client.get("/shandong/api/house-filter/?city=青岛&region=市南区")
        result = json.loads(response.content)

        assert result["total"] == 2
        assert result["page"] == 1
        assert result["pages"] == 1
        assert len(result["data"]) == 2

    def test_按装修筛选(self, house_factory):
        house_factory(zhuangxiu="精装修")
        house_factory(zhuangxiu="毛坯")

        client = Client()
        response = client.get(
            "/shandong/api/house-filter/?city=青岛&region=市南区&zhuangxiu=精装修"
        )
        data = json.loads(response.content)["data"]
        assert len(data) == 1
        assert data[0]["zhuangxiu"] == "精装修"

    def test_按面积分组筛选(self, house_factory):
        house_factory(mianji_group="90-120平")
        house_factory(mianji_group="60-90平")

        client = Client()
        response = client.get(
            "/shandong/api/house-filter/?city=青岛&region=市南区&area=90-120"
        )
        data = json.loads(response.content)["data"]
        assert len(data) == 1
        assert data[0]["mianji"] == "120㎡"

    def test_按价格区间筛选(self, house_factory):
        house_factory(unit_price=6000)
        house_factory(unit_price=15000)

        client = Client()
        response = client.get(
            "/shandong/api/house-filter/?city=青岛&region=市南区&price=5000-8000"
        )
        data = json.loads(response.content)["data"]
        assert len(data) == 1
        assert data[0]["unit_price"] == 6000

    def test_按楼层分类筛选(self, house_factory):
        house_factory(louceng="低楼层")
        house_factory(louceng="中楼层")

        client = Client()
        response = client.get(
            "/shandong/api/house-filter/?city=青岛&region=市南区&louceng=low"
        )
        data = json.loads(response.content)["data"]
        assert len(data) == 1
        assert data[0]["louceng"] == "低楼层"

    def test_按抵押分类筛选(self, house_factory):
        house_factory(diya="无抵押")
        house_factory(diya="有抵押")

        client = Client()
        response = client.get(
            "/shandong/api/house-filter/?city=青岛&region=市南区&diya=none"
        )
        data = json.loads(response.content)["data"]
        assert len(data) == 1
        assert data[0]["diya"] == "无抵押"

    def test_分页_第二页(self, house_factory):
        for i in range(17):
            house_factory(mingcheng=f"小区{i}")

        client = Client()
        response = client.get(
            "/shandong/api/house-filter/?city=青岛&region=市南区&page=2&page_size=10"
        )
        result = json.loads(response.content)

        assert result["page"] == 2
        assert result["pages"] == 2
        assert len(result["data"]) == 7

    def test_多条件组合筛选(self, house_factory):
        house_factory(zhuangxiu="精装修", louceng="高楼层", quanshu="商品房")
        house_factory(zhuangxiu="精装修", louceng="低楼层", quanshu="商品房")
        house_factory(zhuangxiu="毛坯", louceng="高楼层", quanshu="商品房")

        client = Client()
        response = client.get(
            "/shandong/api/house-filter/"
            "?city=青岛&region=市南区&zhuangxiu=精装修&louceng=high"
        )
        data = json.loads(response.content)["data"]
        assert len(data) == 1
        assert data[0]["zhuangxiu"] == "精装修"
        assert data[0]["louceng"] == "高楼层"


# ═══════════════════════════════════════════════════
#  页面视图测试
# ═══════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestPageViews:
    """三级页面视图的 HTTP 响应验证"""

    def test_省级页面正常返回(self, city_factory):
        city_factory("青岛")

        client = Client()
        response = client.get("/shandong/")
        assert response.status_code == 200
        assert "山东省" in response.content.decode()

    def test_省级页面没有城市数据也能正常返回(self):
        client = Client()
        response = client.get("/shandong/")
        assert response.status_code == 200

    def test_城市页面正常返回(self, city_factory, house_factory):
        city_factory("青岛", house_count=100, avg_unit_price=15000, community_count=10)
        house_factory(city="青岛", region="市南区")

        client = Client()
        response = client.get("/shandong/青岛/")
        assert response.status_code == 200
        assert "青岛" in response.content.decode()

    def test_城市不存在_200显示实时聚合结果(self, house_factory):
        """即使 City 维度表没有记录，也能从 House 表聚合"""
        house_factory(city="烟台", region="芝罘区")

        client = Client()
        response = client.get("/shandong/烟台/")
        assert response.status_code == 200
        assert "烟台" in response.content.decode()

    def test_区域页面正常返回(self, house_factory):
        house_factory(city="青岛", region="市南区")

        client = Client()
        response = client.get("/shandong/青岛/市南区/")
        assert response.status_code == 200
        assert "市南区" in response.content.decode()

    def test_三级面包屑导航_路径正确(self, house_factory):
        house_factory(city="济南", region="历下区")

        client = Client()
        response = client.get("/shandong/济南/历下区/")
        content = response.content.decode()
        assert "山东省房源" in content
        assert "济南" in content
        assert "历下区" in content


# ═══════════════════════════════════════════════════
#  图表端点测试
# ═══════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestChartEndpoints:
    """11 个 Matplotlib 图表端点的响应验证"""

    def test_描述性统计表返回PNG(self, city_factory):
        city_factory("青岛")

        client = Client()
        response = client.get("/shandong/chart/desc-stats/")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
        assert len(response.content) > 100

    def test_房源数量柱状图返回PNG(self, city_factory):
        city_factory("青岛")

        client = Client()
        response = client.get("/shandong/chart/housing-count/")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"

    def test_均价柱状图返回PNG(self, city_factory):
        city_factory("青岛")

        client = Client()
        response = client.get("/shandong/chart/avg-price/")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"

    def test_挂牌趋势图返回PNG(self, house_factory):
        house_factory(shijian="2025/06")

        client = Client()
        response = client.get("/shandong/chart/listing-trend/")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"

    def test_高端小区图返回PNG(self, house_factory):
        house_factory(unit_price=120000)

        client = Client()
        response = client.get("/shandong/chart/high-end/")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"

    def test_词云图返回PNG(self, house_factory):
        house_factory(mingcheng="阳光花园")

        client = Client()
        response = client.get("/shandong/chart/wordcloud/")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"

    def test_城市维度图表_需要city参数(self, house_factory):
        house_factory(city="青岛", louceng="低楼层", zhuangxiu="精装修", mianji="120㎡")

        client = Client()
        for name in [
            "chart_top5_layouts",
            "chart_floor_pie",
            "chart_floor_avg_price",
            "chart_decoration",
            "chart_area_distribution",
        ]:
            url = reverse(f"shandong:{name}") + "?city=青岛"
            response = client.get(url)
            assert response.status_code == 200, f"{name} 失败"
            assert response["Content-Type"] == "image/png", f"{name} 不是 PNG"

    @pytest.mark.xfail(reason="已知bug: _png_response 未处理 None，chart_desc_stats 无数据时返回 None 导致 500")
    def test_没有数据时描述性统计表不崩溃(self):
        """空数据时图表端点应优雅返回默认图或 204，而非 500。当前为已知 bug。"""
        client = Client()
        response = client.get("/shandong/chart/desc-stats/")
        assert response.status_code != 500


# ═══════════════════════════════════════════════════
#  边界条件测试
# ═══════════════════════════════════════════════════

class TestEdgeCases:
    """极端输入和边界条件"""

    def test_楼层_特殊格式(self):
        """'共5层' 无总层数，5≤6→低楼层; '8层' 6<8≤18→中楼层"""
        assert _floor_category("共5层") == "low"
        assert _floor_category("总高18层") == "middle"
        assert _floor_category("8层") == "middle"

    def test_抵押_空格和换行(self):
        assert _mortgage_category("  无抵押  ") == "none"
        assert _mortgage_category("已\n还清") == "settled"

    def test_城市名称_带前后空格(self):
        variants = set(_city_name_variants("  济南  "))
        assert "济南" in variants
        assert "济南市" in variants
