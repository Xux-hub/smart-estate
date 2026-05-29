from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator

from .models import House, Community, District, City, Facility


def house_list(request):
    """房源列表页"""
    # 筛选参数
    city_name = request.GET.get('city', '')
    district_id = request.GET.get('district', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    min_area = request.GET.get('min_area', '')
    max_area = request.GET.get('max_area', '')
    layout = request.GET.get('layout', '')
    sort_by = request.GET.get('sort', '-created_at')

    queryset = House.objects.filter(status=1).select_related(
        'community__district__city'
    )

    # 应用筛选条件
    if city_name:
        queryset = queryset.filter(community__district__city__name=city_name)
    if district_id:
        queryset = queryset.filter(community__district_id=district_id)
    if min_price:
        queryset = queryset.filter(total_price__gte=min_price)
    if max_price:
        queryset = queryset.filter(total_price__lte=max_price)
    if min_area:
        queryset = queryset.filter(area__gte=min_area)
    if max_area:
        queryset = queryset.filter(area__lte=max_area)
    if layout:
        queryset = queryset.filter(layout__contains=layout)

    # 排序
    allowed_sorts = ['-created_at', 'total_price', '-total_price', 'unit_price', '-unit_price', 'area', '-area']
    if sort_by in allowed_sorts:
        queryset = queryset.order_by(sort_by)

    # 分页
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 获取城市和区域列表用于筛选
    cities = City.objects.all()
    districts = District.objects.all()
    if city_name:
        districts = districts.filter(city__name=city_name)

    context = {
        'page_obj': page_obj,
        'cities': cities,
        'districts': districts,
        'filters': {
            'city': city_name,
            'district': district_id,
            'min_price': min_price,
            'max_price': max_price,
            'min_area': min_area,
            'max_area': max_area,
            'layout': layout,
            'sort': sort_by,
        }
    }
    return render(request, 'house/list.html', context)


def house_detail(request, house_id):
    """房源详情页"""
    house = get_object_or_404(
        House.objects.select_related('community__district__city'),
        id=house_id
    )
    # 获取同小区其他房源
    similar_houses = House.objects.filter(
        community=house.community, status=1
    ).exclude(id=house.id)[:5]

    # 获取周边配套
    facilities = Facility.objects.filter(community=house.community)

    context = {
        'house': house,
        'similar_houses': similar_houses,
        'facilities': facilities,
    }
    return render(request, 'house/detail.html', context)


def search(request):
    """房源搜索页"""
    keyword = request.GET.get('q', '')
    queryset = House.objects.filter(status=1).select_related(
        'community__district__city'
    )

    if keyword:
        queryset = queryset.filter(
            Q(title__contains=keyword) |
            Q(community__name__contains=keyword) |
            Q(community__district__name__contains=keyword)
        )

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'keyword': keyword,
    }
    return render(request, 'house/search.html', context)


def district_detail(request, district_id):
    """区域详情页"""
    district = get_object_or_404(District.objects.select_related('city'), id=district_id)
    houses = House.objects.filter(
        community__district=district, status=1
    ).select_related('community')

    # 区域统计
    stats = houses.aggregate(
        avg_price=Avg('unit_price'),
        house_count=Count('id'),
        avg_area=Avg('area'),
    )

    # 小区列表
    communities = Community.objects.filter(district=district).annotate(
        house_count=Count('houses', filter=Q(houses__status=1)),
        avg_price=Avg('houses__unit_price', filter=Q(houses__status=1)),
    )

    paginator = Paginator(houses, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'district': district,
        'stats': stats,
        'communities': communities,
        'page_obj': page_obj,
    }
    return render(request, 'house/district.html', context)


# API views for AJAX requests
def api_district_list(request):
    """获取城市下的区域列表 (AJAX)"""
    city_name = request.GET.get('city', '')
    if city_name:
        districts = District.objects.filter(city__name=city_name).values('id', 'name')
        return JsonResponse({'districts': list(districts)})
    return JsonResponse({'districts': []})


def api_house_map_data(request):
    """获取房源地图数据 (AJAX)"""
    city_name = request.GET.get('city', '')
    district_id = request.GET.get('district', '')

    communities = Community.objects.filter(
        longitude__isnull=False, latitude__isnull=False
    )

    if city_name:
        communities = communities.filter(district__city__name=city_name)
    if district_id:
        communities = communities.filter(district_id=district_id)

    communities = communities.annotate(
        house_count=Count('houses', filter=Q(houses__status=1)),
        avg_price=Avg('houses__unit_price', filter=Q(houses__status=1)),
    ).values('name', 'longitude', 'latitude', 'house_count', 'avg_price')

    return JsonResponse({'data': list(communities)})
