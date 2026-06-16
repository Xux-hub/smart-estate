from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import render

from web.apps.house.models import House


def analysis_index(request):
    return render(request, 'analysis/index.html', {'cities': _city_options()})


def api_price_distribution(request):
    city_name = request.GET.get('city', '').strip()
    queryset = House.objects.all()
    if city_name:
        queryset = queryset.filter(city=city_name)

    districts = queryset.exclude(region__isnull=True).exclude(region='').values('region').annotate(
        avg_price=Avg('unit_price'),
        house_count=Count('id'),
    ).order_by('-avg_price')

    return JsonResponse({'data': [
        {'name': row['region'], 'avg_price': row['avg_price'], 'house_count': row['house_count']}
        for row in districts
    ]})


def api_layout_stats(request):
    city_name = request.GET.get('city', '').strip()
    queryset = House.objects.all()
    if city_name:
        queryset = queryset.filter(city=city_name)

    layout_stats = queryset.exclude(huxing__isnull=True).exclude(huxing='').values('huxing').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    return JsonResponse({'data': [{'layout': row['huxing'], 'count': row['count']} for row in layout_stats]})


def api_price_area_scatter(request):
    city_name = request.GET.get('city', '').strip()
    queryset = House.objects.exclude(unit_price__isnull=True)
    if city_name:
        queryset = queryset.filter(city=city_name)

    data = []
    for house in queryset.only('mianji', 'unit_price', 'region')[:1000]:
        if house.area is not None:
            data.append({'area': float(house.area), 'unit_price': house.unit_price, 'region': house.region})
    return JsonResponse({'data': data})


def api_decoration_stats(request):
    city_name = request.GET.get('city', '').strip()
    queryset = House.objects.exclude(zhuangxiu__isnull=True).exclude(zhuangxiu='')
    if city_name:
        queryset = queryset.filter(city=city_name)

    stats = queryset.values('zhuangxiu').annotate(
        count=Count('id'),
        avg_price=Avg('unit_price'),
    ).order_by('-count')

    return JsonResponse({'data': [
        {'decoration': row['zhuangxiu'], 'count': row['count'], 'avg_price': row['avg_price']}
        for row in stats
    ]})


def compare(request):
    return render(request, 'analysis/compare.html', {'cities': _city_options()})


def _city_options():
    return [{'name': name} for name in House.objects.exclude(city__isnull=True).exclude(city='').values_list('city', flat=True).distinct().order_by('city')]
