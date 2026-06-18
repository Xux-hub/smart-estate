import re

from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

from web.apps.house.models import City, District, House
from . import charts


def province(request):
    """山东省首页地图。"""
    cities = City.objects.all().order_by('name')
    city_stats = [
        {
            'name': city.name,
            'house_count': city.house_count or 0,
            'avg_price': float(city.avg_unit_price or 0),
            'community_count': city.community_count or 0,
        }
        for city in cities
    ]
    return render(request, 'shandong/province.html', {
        'cities': cities,
        'city_stats_json': city_stats,
    })


def city_detail(request, city_name):
    """城市区县地图。"""
    city = get_object_or_404(City, name=city_name)
    districts = District.objects.filter(city_id=city.id).order_by('name')
    return render(request, 'shandong/city.html', {
        'city': city,
        'districts': districts,
    })


def district_detail(request, city_name, district_name):
    """区县房源筛选表格。"""
    base = House.objects.filter(city=city_name, region=district_name)

    zhuangxiu_opts = base.values_list('zhuangxiu', flat=True) \
        .distinct().exclude(zhuangxiu__isnull=True).exclude(zhuangxiu='')
    louceng_opts = base.values_list('louceng', flat=True) \
        .distinct().exclude(louceng__isnull=True).exclude(louceng='')
    quanshu_opts = base.values_list('quanshu', flat=True) \
        .distinct().exclude(quanshu__isnull=True).exclude(quanshu='')
    diya_opts = base.values_list('diya', flat=True) \
        .distinct().exclude(diya__isnull=True).exclude(diya='')

    return render(request, 'shandong/district.html', {
        'city_name': city_name,
        'district_name': district_name,
        'zhuangxiu_options': list(zhuangxiu_opts),
        'louceng_options': list(louceng_opts),
        'quanshu_options': list(quanshu_opts),
        'diya_options': list(diya_opts),
    })


def api_city_stats(request):
    """各城市统计数据，名称带“市”后缀以匹配地图。"""
    cities = City.objects.all().values(
        'name', 'house_count', 'avg_unit_price', 'community_count')
    data = [{
        'name': c['name'] + '市',
        'house_count': c['house_count'],
        'avg_price': float(c['avg_unit_price']) if c['avg_unit_price'] else 0,
        'community_count': c['community_count'] or 0,
    } for c in cities]
    return JsonResponse({'data': data})


def api_district_stats(request):
    """某城市各区县统计数据。"""
    city_name = request.GET.get('city', '')
    try:
        city = City.objects.get(name=city_name)
        districts = District.objects.filter(city_id=city.id).values(
            'name', 'house_count', 'avg_unit_price', 'community_count')
        data = [{
            'name': d['name'],
            'house_count': d['house_count'],
            'avg_price': float(d['avg_unit_price']) if d['avg_unit_price'] else 0,
            'community_count': d['community_count'] or 0,
        } for d in districts]
    except City.DoesNotExist:
        data = []
    return JsonResponse({'data': data})


def api_house_filter(request):
    """筛选房源列表。"""
    city = request.GET.get('city', '')
    region = request.GET.get('region', '')
    zhuangxiu = request.GET.get('zhuangxiu', '').strip()
    louceng = request.GET.get('louceng', '').strip()
    quanshu = request.GET.get('quanshu', '').strip()
    diya = request.GET.get('diya', '').strip()
    area = request.GET.get('area', '').strip()
    price = request.GET.get('price', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 15))

    qs = House.objects.filter(city=city, region=region)

    if zhuangxiu:
        qs = qs.filter(zhuangxiu=zhuangxiu)
    if louceng:
        qs = qs.filter(louceng__contains=louceng)
    if quanshu:
        qs = qs.filter(quanshu=quanshu)
    if diya:
        qs = qs.filter(diya__contains=diya)

    area_map = {
        '<60': (None, 60),
        '60-90': (60, 90),
        '90-120': (90, 120),
        '120-150': (120, 150),
        '150-200': (150, 200),
        '>200': (200, None),
    }
    if area and area in area_map:
        label_map = {
            '<60': '<60㎡',
            '60-90': '60-90㎡',
            '90-120': '90-120㎡',
            '120-150': '120-150㎡',
            '150-200': '150-200㎡',
            '>200': '>200㎡',
        }
        if area in label_map:
            qs = qs.filter(mianji_group=label_map[area])

    price_map = {
        '<5000': (None, 5000),
        '5000-8000': (5000, 8000),
        '8000-12000': (8000, 12000),
        '12000-20000': (12000, 20000),
        '>20000': (20000, None),
    }
    if price and price in price_map:
        lo, hi = price_map[price]
        if lo is not None and hi is not None:
            qs = qs.filter(unit_price__gte=lo, unit_price__lt=hi)
        elif lo is not None:
            qs = qs.filter(unit_price__gte=lo)
        elif hi is not None:
            qs = qs.filter(unit_price__lt=hi)

    qs = qs.order_by('-shijian')
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    data = [{
        'mingcheng': h.mingcheng or '',
        'huxing': h.huxing or '',
        'mianji': h.mianji or '',
        'louceng': h.louceng or '',
        'zhuangxiu': h.zhuangxiu or '',
        'chaoxiang': h.chaoxiang or '',
        'price': h.price or '',
        'unit_price': h.unit_price or 0,
        'shijian': h.shijian or '',
        'quanshu': h.quanshu or '',
        'diya': h.diya or '',
        'link': h.link or '',
    } for h in page_obj]

    return JsonResponse({
        'data': data,
        'total': paginator.count,
        'page': page,
        'pages': paginator.num_pages,
    })


def _png_response(buf):
    return HttpResponse(buf.getvalue(), content_type='image/png')


def chart_desc_stats(request):
    return _png_response(charts.chart_desc_stats())


def chart_housing_count(request):
    return _png_response(charts.chart_housing_count())


def chart_avg_price(request):
    return _png_response(charts.chart_avg_price())


def chart_listing_trend(request):
    return _png_response(charts.chart_listing_trend())


def chart_high_end(request):
    return _png_response(charts.chart_high_end())


def chart_wordcloud(request):
    return _png_response(charts.chart_wordcloud())


def chart_top5_layouts(request):
    city = request.GET.get('city', '')
    return _png_response(charts.chart_top5_layouts(city))


def chart_floor_pie(request):
    city = request.GET.get('city', '')
    return _png_response(charts.chart_floor_pie(city))


def chart_floor_avg_price(request):
    city = request.GET.get('city', '')
    return _png_response(charts.chart_floor_avg_price(city))


def chart_decoration(request):
    city = request.GET.get('city', '')
    return _png_response(charts.chart_decoration(city))


def chart_area_distribution(request):
    city = request.GET.get('city', '')
    return _png_response(charts.chart_area_distribution(city))
