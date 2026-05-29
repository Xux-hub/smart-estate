from django.db import models
from django.shortcuts import render
from django.db.models import Avg, Count, Max, Min, Q

from web.apps.house.models import City, District, House, Community


def index(request):
    """首页大屏"""
    # 统计数据
    total_houses = House.objects.filter(status=1).count()
    total_cities = City.objects.count()
    total_communities = Community.objects.count()
    avg_price = House.objects.filter(status=1).aggregate(avg=Avg('unit_price'))['avg'] or 0

    # 各城市房源数量
    city_stats = City.objects.annotate(
        house_count=Count('districts__communities__houses', filter=Q(districts__communities__houses__status=1)),
        avg_unit_price=Avg('districts__communities__houses__unit_price', filter=Q(districts__communities__houses__status=1))
    ).values('name', 'house_count', 'avg_unit_price')

    import json
    from decimal import Decimal

    # 序列化为 JSON 安全的格式
    city_stats_list = list(city_stats)
    for item in city_stats_list:
        if item['avg_unit_price'] is not None:
            item['avg_unit_price'] = float(item['avg_unit_price'])

    context = {
        'total_houses': total_houses,
        'total_cities': total_cities,
        'total_communities': total_communities,
        'avg_price': round(avg_price, 2),
        'city_stats': city_stats_list,
        'city_stats_json': json.dumps(city_stats_list, ensure_ascii=False),
    }
    return render(request, 'home.html', context)


def city_detail(request, city_name):
    """城市房价详情页"""
    city = City.objects.get(name=city_name)
    districts = District.objects.filter(city=city).annotate(
        house_count=Count('communities__houses', filter=Q(communities__houses__status=1)),
        avg_unit_price=Avg('communities__houses__unit_price', filter=Q(communities__houses__status=1)),
        max_price=Max('communities__houses__unit_price', filter=Q(communities__houses__status=1)),
        min_price=Min('communities__houses__unit_price', filter=Q(communities__houses__status=1)),
    )

    context = {
        'city': city,
        'districts': districts,
    }
    return render(request, 'city.html', context)
