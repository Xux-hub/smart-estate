import json

from django.shortcuts import render

from web.apps.house.models import CityStat, RegionStat


def index(request):
    city_stats = list(
        CityStat.objects.all()
        .values('city', 'house_count', 'community_count', 'avg_unit_price')
        .order_by('-house_count')
    )
    total_houses = sum(item['house_count'] or 0 for item in city_stats)
    total_cities = len(city_stats)
    total_communities = sum(item['community_count'] or 0 for item in city_stats)
    avg_price = _weighted_avg(city_stats)

    for item in city_stats:
        item['name'] = item.pop('city')
        item['avg_unit_price'] = float(item['avg_unit_price'] or 0)

    shandong_charts = [
        {
            'number': '01',
            'title': '各城市房价描述性统计',
            'description': '对各城市总价、单价、面积等指标做集中趋势和离散程度概览。',
            'url_name': 'shandong:chart_desc_stats',
            'wide': True,
        },
        {
            'number': '02',
            'title': '各城市房源数量',
            'description': '快速比较山东样本城市的房源供给规模。',
            'url_name': 'shandong:chart_housing_count',
        },
        {
            'number': '03',
            'title': '各城市平均房价',
            'description': '按城市聚合展示二手房平均单价水平。',
            'url_name': 'shandong:chart_avg_price',
        },
        {
            'number': '04',
            'title': '月度挂牌趋势',
            'description': '观察挂牌量随月份变化的节奏。',
            'url_name': 'shandong:chart_listing_trend',
            'wide': True,
        },
        {
            'number': '10',
            'title': '高端小区分布',
            'description': '展示高单价小区在不同区域的分布情况。',
            'url_name': 'shandong:chart_high_end',
            'wide': True,
        },
        {
            'number': '11',
            'title': '热门小区词云',
            'description': '用词云呈现样本中出现频率较高的小区。',
            'url_name': 'shandong:chart_wordcloud',
            'wide': True,
        },
    ]

    context = {
        'total_houses': total_houses,
        'total_cities': total_cities,
        'total_communities': total_communities,
        'avg_price': round(avg_price, 2),
        'city_stats': city_stats,
        'city_stats_json': json.dumps(city_stats, ensure_ascii=False),
        'shandong_charts': shandong_charts,
    }
    return render(request, 'home.html', context)


def city_detail(request, city_name):
    districts = list(
        RegionStat.objects.filter(city=city_name)
        .values('region', 'house_count', 'avg_unit_price', 'max_unit_price', 'min_unit_price')
        .order_by('-house_count')
    )
    for item in districts:
        item['id'] = item['region']
        item['name'] = item.pop('region')
    return render(request, 'city.html', {'city': {'name': city_name}, 'districts': districts})


def _weighted_avg(city_stats):
    total_count = sum(item['house_count'] or 0 for item in city_stats)
    if not total_count:
        return 0
    total_price = sum(float(item['avg_unit_price'] or 0) * (item['house_count'] or 0) for item in city_stats)
    return total_price / total_count
