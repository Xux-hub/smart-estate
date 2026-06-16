from django.http import JsonResponse
from django.shortcuts import render

from web.apps.house.models import City, DecorationStat, House, LayoutStat, RegionStat


def analysis_index(request):
    return render(request, 'analysis/index.html', {'cities': _city_options()})


def api_price_distribution(request):
    city_name = request.GET.get('city', '').strip()
    queryset = RegionStat.objects.all()
    if city_name:
        queryset = queryset.filter(city=city_name)

    rows = queryset.values('region', 'avg_unit_price', 'house_count').order_by('-avg_unit_price')
    return JsonResponse({'data': [
        {'name': row['region'], 'avg_price': row['avg_unit_price'], 'house_count': row['house_count']}
        for row in rows
    ]})


def api_layout_stats(request):
    city_name = request.GET.get('city', '').strip()
    queryset = LayoutStat.objects.all()
    if city_name:
        queryset = queryset.filter(city=city_name)

    rows = queryset.values('layout_name', 'house_count').order_by('-house_count')[:10]
    return JsonResponse({'data': [{'layout': row['layout_name'], 'count': row['house_count']} for row in rows]})


def api_price_area_scatter(request):
    city_name = request.GET.get('city', '').strip()
    queryset = House.objects.exclude(unit_price__isnull=True)
    if city_name:
        queryset = queryset.filter(city=city_name)

    data = []
    for house in queryset.only('mianji', 'unit_price', 'region').order_by('id')[:1000]:
        if house.area is not None:
            data.append({'area': float(house.area), 'unit_price': house.unit_price, 'region': house.region})
    return JsonResponse({'data': data})


def api_decoration_stats(request):
    city_name = request.GET.get('city', '').strip()
    queryset = DecorationStat.objects.all()
    if city_name:
        queryset = queryset.filter(city=city_name)

    rows = queryset.values('decoration_name', 'house_count', 'avg_unit_price').order_by('-house_count')
    return JsonResponse({'data': [
        {'decoration': row['decoration_name'], 'count': row['house_count'], 'avg_price': row['avg_unit_price']}
        for row in rows
    ]})


def compare(request):
    return render(request, 'analysis/compare.html', {'cities': _city_options()})


def _city_options():
    return [{'name': city.name} for city in City.objects.only('name').order_by('name')]
