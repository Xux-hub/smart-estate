import json

from django.db.models import Avg, Count, Max, Min
from django.shortcuts import render

from web.apps.house.models import House


def index(request):
    total_houses = House.objects.count()
    total_cities = House.objects.exclude(city__isnull=True).exclude(city='').values('city').distinct().count()
    total_communities = House.objects.exclude(mingcheng__isnull=True).exclude(mingcheng='').values('mingcheng').distinct().count()
    avg_price = House.objects.aggregate(avg=Avg('unit_price'))['avg'] or 0

    city_stats = list(
        House.objects.exclude(city__isnull=True).exclude(city='')
        .values('city')
        .annotate(house_count=Count('id'), avg_unit_price=Avg('unit_price'))
        .order_by('-house_count')
    )
    for item in city_stats:
        item['name'] = item.pop('city')
        item['avg_unit_price'] = float(item['avg_unit_price'] or 0)

    context = {
        'total_houses': total_houses,
        'total_cities': total_cities,
        'total_communities': total_communities,
        'avg_price': round(float(avg_price), 2),
        'city_stats': city_stats,
        'city_stats_json': json.dumps(city_stats, ensure_ascii=False),
    }
    return render(request, 'home.html', context)


def city_detail(request, city_name):
    districts = list(
        House.objects.filter(city=city_name)
        .exclude(region__isnull=True).exclude(region='')
        .values('region')
        .annotate(
            house_count=Count('id'),
            avg_unit_price=Avg('unit_price'),
            max_price=Max('unit_price'),
            min_price=Min('unit_price'),
        )
        .order_by('-house_count')
    )
    for index, item in enumerate(districts, start=1):
        item['id'] = item['region']
        item['name'] = item.pop('region')
    return render(request, 'city.html', {'city': {'name': city_name}, 'districts': districts})
