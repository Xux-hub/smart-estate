from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Count, Q

from web.apps.house.models import City, District, House


def analysis_index(request):
    """数据分析首页"""
    cities = City.objects.all()
    context = {'cities': cities}
    return render(request, 'analysis/index.html', context)


def api_price_distribution(request):
    """各区域房价分布数据 (API)"""
    city_name = request.GET.get('city', '北京')

    districts = District.objects.filter(city__name=city_name).annotate(
        avg_price=Avg('communities__houses__unit_price', filter=Q(communities__houses__status=1)),
        house_count=Count('communities__houses', filter=Q(communities__houses__status=1)),
    ).values('name', 'avg_price', 'house_count').order_by('-avg_price')

    return JsonResponse({'data': list(districts)})


def api_layout_stats(request):
    """户型统计数据 (API)"""
    city_name = request.GET.get('city', '北京')

    layout_stats = House.objects.filter(
        community__district__city__name=city_name, status=1
    ).values('layout').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    return JsonResponse({'data': list(layout_stats)})


def api_price_area_scatter(request):
    """面积-价格散点图数据 (API)"""
    city_name = request.GET.get('city', '北京')

    houses = House.objects.filter(
        community__district__city__name=city_name,
        status=1,
        area__isnull=False,
        unit_price__isnull=False,
    ).values('area', 'unit_price', 'community__district__name')[:500]

    return JsonResponse({'data': list(houses)})


def api_decoration_stats(request):
    """装修情况统计 (API)"""
    city_name = request.GET.get('city', '北京')

    stats = House.objects.filter(
        community__district__city__name=city_name,
        status=1,
        decoration__isnull=False,
    ).values('decoration').annotate(
        count=Count('id'),
        avg_price=Avg('unit_price'),
    ).order_by('-count')

    return JsonResponse({'data': list(stats)})


def compare(request):
    """区域对比页面"""
    cities = City.objects.all()
    context = {'cities': cities}
    return render(request, 'analysis/compare.html', context)
