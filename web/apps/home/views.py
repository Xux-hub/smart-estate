import re
from collections import Counter

from django.db.models import Avg, Count
from django.shortcuts import render

from web.apps.house.models import CityStat, House, RegionStat


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
        'monthly_trend': _monthly_trend(),
        'high_end_communities': _high_end_communities(),
        'community_words': _community_words(),
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


def _monthly_trend():
    counter = Counter()
    for row in House.objects.all().values('shijian'):
        match = re.match(r'(\d{4}/\d{1,2})', str(row['shijian'] or ''))
        if match:
            year, month = match.group(1).split('/')
            counter[f'{year}/{int(month):02d}'] += 1
    return [{'month': month, 'count': counter[month]} for month in sorted(counter)]


def _high_end_communities():
    data = (
        House.objects.filter(unit_price__gt=60000)
        .values('mingcheng', 'city', 'region')
        .annotate(count=Count('id'), avg_price=Avg('unit_price'))
        .order_by('-count', '-avg_price')[:20]
    )
    return [
        {
            'name': item['mingcheng'] or '未知小区',
            'city': item['city'] or '',
            'region': item['region'] or '',
            'count': item['count'] or 0,
            'avg_price': round(float(item['avg_price'] or 0)),
        }
        for item in data
    ]


def _community_words():
    counter = Counter()
    for row in House.objects.all().values('mingcheng'):
        name = str(row['mingcheng'] or '').strip()
        if name:
            counter[name] += 1
    return [{'name': name, 'value': count} for name, count in counter.most_common(80)]
