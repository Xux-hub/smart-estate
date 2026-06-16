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

    context = {
        'total_houses': total_houses,
        'total_cities': total_cities,
        'total_communities': total_communities,
        'avg_price': round(avg_price, 2),
        'city_stats': city_stats,
        'city_stats_json': json.dumps(city_stats, ensure_ascii=False),
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
