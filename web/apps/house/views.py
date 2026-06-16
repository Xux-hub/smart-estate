from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import City, Community, District, House, RegionStat


def house_list(request):
    city_name = request.GET.get('city', '').strip()
    region = request.GET.get('district', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    min_area = request.GET.get('min_area', '').strip()
    max_area = request.GET.get('max_area', '').strip()
    layout = request.GET.get('layout', '').strip()
    sort_by = request.GET.get('sort', '-id')

    queryset = _apply_house_filters(
        House.objects.all(),
        city_name=city_name,
        region=region,
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        layout=layout,
    )

    if sort_by == 'price':
        queryset = queryset.extra(select={'price_num': 'CAST(price AS DECIMAL(10,2))'}, order_by=['price_num'])
    elif sort_by == '-price':
        queryset = queryset.extra(select={'price_num': 'CAST(price AS DECIMAL(10,2))'}, order_by=['-price_num'])
    elif sort_by == 'area':
        queryset = queryset.extra(select={'area_num': 'CAST(mianji AS DECIMAL(10,2))'}, order_by=['area_num'])
    elif sort_by == '-area':
        queryset = queryset.extra(select={'area_num': 'CAST(mianji AS DECIMAL(10,2))'}, order_by=['-area_num'])
    elif sort_by in {'unit_price', '-unit_price'}:
        queryset = queryset.order_by(sort_by)
    else:
        queryset = queryset.order_by('-id')

    page_obj = Paginator(queryset, 20).get_page(request.GET.get('page', 1))
    context = {
        'page_obj': page_obj,
        'cities': _city_options(),
        'districts': _region_options(city_name),
        'filters': {
            'city': city_name,
            'district': region,
            'min_price': min_price,
            'max_price': max_price,
            'min_area': min_area,
            'max_area': max_area,
            'layout': layout,
            'sort': sort_by,
        },
    }
    return render(request, 'house/list.html', context)


def house_detail(request, house_id):
    house = get_object_or_404(House, id=house_id)
    similar_houses = House.objects.filter(mingcheng=house.mingcheng).exclude(id=house.id)[:5]
    return render(request, 'house/detail.html', {'house': house, 'similar_houses': similar_houses})


def search(request):
    keyword = request.GET.get('q', '').strip()
    queryset = House.objects.all()
    if keyword:
        queryset = queryset.filter(
            Q(mingcheng__icontains=keyword)
            | Q(region__icontains=keyword)
            | Q(quyu__icontains=keyword)
            | Q(huxing__icontains=keyword)
            | Q(maidian__icontains=keyword)
        )
    page_obj = Paginator(queryset.order_by('-id'), 20).get_page(request.GET.get('page', 1))
    return render(request, 'house/search.html', {'page_obj': page_obj, 'keyword': keyword})


def district_detail(request, district_id):
    region = district_id
    houses = House.objects.filter(Q(region=region) | Q(quyu=region)).order_by('-id')
    stat = RegionStat.objects.filter(region=region).order_by('-house_count').first()
    stats = {
        'avg_price': stat.avg_unit_price if stat else None,
        'house_count': stat.house_count if stat else 0,
    }
    district_ids = list(District.objects.filter(name=region).values_list('id', flat=True))
    communities = Community.objects.filter(district_id__in=district_ids).order_by('-house_count')[:50]
    page_obj = Paginator(houses, 20).get_page(request.GET.get('page', 1))
    context = {
        'district': {'name': region, 'city': stat.city if stat else (houses.values_list('city', flat=True).first() or '')},
        'stats': stats,
        'communities': communities,
        'page_obj': page_obj,
    }
    return render(request, 'house/district.html', context)


def api_district_list(request):
    city_name = request.GET.get('city', '').strip()
    districts = _region_options(city_name)
    return JsonResponse({'districts': [{'id': item['name'], 'name': item['name']} for item in districts]})


def api_house_map_data(request):
    city_name = request.GET.get('city', '').strip()
    region = request.GET.get('district', '').strip()

    district_queryset = District.objects.all()
    if city_name:
        city = City.objects.filter(name=city_name).first()
        district_queryset = district_queryset.filter(city_id=city.id if city else None)
    if region:
        district_queryset = district_queryset.filter(name=region)
    district_map = {district.id: district.name for district in district_queryset.only('id', 'name')}
    data = Community.objects.filter(
        district_id__in=district_map.keys(),
    ).exclude(longitude__isnull=True).exclude(latitude__isnull=True).exclude(longitude='').exclude(latitude='')[:1000]
    return JsonResponse({
        'data': [
            {
                'name': row.name,
                'longitude': row.longitude,
                'latitude': row.latitude,
                'region': district_map.get(row.district_id, ''),
                'house_count': row.house_count,
                'avg_price': row.avg_unit_price,
            }
            for row in data
        ]
    })


def _apply_house_filters(queryset, city_name='', region='', min_price='', max_price='', min_area='', max_area='', layout=''):
    if city_name:
        queryset = queryset.filter(city=city_name)
    if region:
        queryset = queryset.filter(Q(region=region) | Q(quyu=region))
    if layout:
        queryset = queryset.filter(huxing__icontains=layout)
    if min_price:
        queryset = queryset.extra(where=['CAST(price AS DECIMAL(10,2)) >= %s'], params=[min_price])
    if max_price:
        queryset = queryset.extra(where=['CAST(price AS DECIMAL(10,2)) <= %s'], params=[max_price])
    if min_area or max_area:
        if min_area:
            queryset = queryset.extra(where=['CAST(mianji AS DECIMAL(10,2)) >= %s'], params=[min_area])
        if max_area:
            queryset = queryset.extra(where=['CAST(mianji AS DECIMAL(10,2)) <= %s'], params=[max_area])
    return queryset


def _city_options():
    return [{'name': city.name} for city in City.objects.only('name').order_by('name')]


def _region_options(city_name=''):
    queryset = District.objects.all()
    if city_name:
        city = City.objects.filter(name=city_name).first()
        queryset = queryset.filter(city_id=city.id if city else None)
    names = queryset.values_list('name', flat=True).order_by('name')
    return [{'name': name} for name in names]
