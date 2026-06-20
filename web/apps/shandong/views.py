import re
from types import SimpleNamespace

from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render

from web.apps.house.models import City, District, House
from . import charts


def province(request):
    city_stats = _city_stats()
    cities = [SimpleNamespace(**item) for item in city_stats]
    return render(request, 'shandong/province.html', {
        'cities': cities,
        'city_stats': city_stats,
        'high_end_communities': _high_end_communities(),
    })


def city_detail(request, city_name):
    city = _resolve_city(city_name)
    districts = _districts_for_city(city)
    return render(request, 'shandong/city.html', {
        'city': city,
        'districts': districts,
    })


def district_detail(request, city_name, district_name):
    base = House.objects.filter(city__in=_city_name_variants(city_name), region=district_name)

    zhuangxiu_opts = base.values_list('zhuangxiu', flat=True) \
        .distinct().exclude(zhuangxiu__isnull=True).exclude(zhuangxiu='')
    floor_options = _floor_category_options(base)
    quanshu_opts = base.values_list('quanshu', flat=True) \
        .distinct().exclude(quanshu__isnull=True).exclude(quanshu='')
    diya_options = _mortgage_category_options(base)

    return render(request, 'shandong/district.html', {
        'city_name': city_name,
        'district_name': district_name,
        'zhuangxiu_options': list(zhuangxiu_opts),
        'louceng_options': floor_options,
        'quanshu_options': list(quanshu_opts),
        'diya_options': diya_options,
    })


def api_city_stats(request):
    data = [{
        'name': _city_map_name(c['name']),
        'house_count': c['house_count'],
        'avg_price': float(c['avg_unit_price'] or 0),
        'community_count': c['community_count'] or 0,
    } for c in _city_stats()]
    return JsonResponse({'data': data})

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
    city_name = request.GET.get('city', '')
    try:
        city = _resolve_city(city_name)
        districts = _districts_for_city(city)
        data = [{
            'name': d.name,
            'house_count': d.house_count or 0,
            'avg_price': float(d.avg_unit_price or 0),
            'community_count': d.community_count or 0,
        } for d in districts]
    except Http404:
        data = []
    return JsonResponse({'data': data})


def api_house_filter(request):
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

    qs = House.objects.filter(city__in=_city_name_variants(city), region=region)

    if zhuangxiu:
        qs = qs.filter(zhuangxiu=zhuangxiu)
    if louceng:
        qs = _filter_by_floor_category(qs, louceng)
    if quanshu:
        qs = qs.filter(quanshu=quanshu)
    if diya:
        qs = _filter_by_mortgage_category(qs, diya)

    area_labels = {
        '60以下': '60平以下',
        '60-90': '60-90平',
        '90-120': '90-120平',
        '120-150': '120-150平',
        '150-300': '150-300平',
        '300以上': '300平以上',
    }
    if area in area_labels:
        qs = qs.filter(mianji_group=area_labels[area])

    price_map = {
        '<5000': (None, 5000),
        '5000-8000': (5000, 8000),
        '8000-12000': (8000, 12000),
        '12000-20000': (12000, 20000),
        '>20000': (20000, None),
    }
    if price in price_map:
        lo, hi = price_map[price]
        if lo is not None:
            qs = qs.filter(unit_price__gte=lo)
        if hi is not None:
            qs = qs.filter(unit_price__lt=hi)

    paginator = Paginator(qs.order_by('-shijian'), page_size)
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


def _resolve_city(city_name):
    names = _city_name_variants(city_name)
    city = City.objects.filter(name__in=names).first()
    if city:
        return city

    qs = House.objects.filter(city__in=names)
    if not qs.exists():
        raise Http404('No City matches the given query.')

    return SimpleNamespace(
        id=None,
        name=_display_city_name(city_name),
        house_count=qs.count(),
        community_count=qs.exclude(mingcheng__isnull=True).exclude(mingcheng='').values('mingcheng').distinct().count(),
        avg_unit_price=qs.aggregate(value=Avg('unit_price'))['value'] or 0,
    )


def _districts_for_city(city):
    if getattr(city, 'id', None):
        districts = list(District.objects.filter(city_id=city.id).order_by('name'))
        if districts:
            return districts

    rows = (
        House.objects.filter(city__in=_city_name_variants(city.name))
        .exclude(region__isnull=True)
        .exclude(region='')
        .values('region')
        .annotate(
            house_count=Count('id'),
            community_count=Count('mingcheng', distinct=True),
            avg_unit_price=Avg('unit_price'),
        )
        .order_by('region')
    )
    return [
        SimpleNamespace(
            name=row['region'],
            house_count=row['house_count'] or 0,
            community_count=row['community_count'] or 0,
            avg_unit_price=row['avg_unit_price'] or 0,
        )
        for row in rows
    ]


def _city_name_variants(city_name):
    name = str(city_name or '').strip()
    if not name:
        return []

    variants = {name}
    city_suffix = '\u5e02'
    if name.endswith(city_suffix):
        variants.add(name[:-1])
    else:
        variants.add(name + city_suffix)
    return list(variants)


def _display_city_name(city_name):
    name = str(city_name or '').strip()
    return name[:-1] if name.endswith('\u5e02') else name


def _city_map_name(city_name):
    name = _display_city_name(city_name)
    return name + '\u5e02'


def _city_stats():
    stats = {}
    for city in City.objects.all().order_by('name'):
        name = _display_city_name(city.name)
        stats[name] = {
            'name': name,
            'house_count': city.house_count or 0,
            'community_count': city.community_count or 0,
            'avg_unit_price': float(city.avg_unit_price or 0),
        }

    rows = (
        House.objects.exclude(city__isnull=True)
        .exclude(city='')
        .values('city')
        .annotate(
            house_count=Count('id'),
            community_count=Count('mingcheng', distinct=True),
            avg_unit_price=Avg('unit_price'),
        )
        .order_by('city')
    )
    for row in rows:
        name = _display_city_name(row['city'])
        if not name:
            continue
        if name not in stats or not stats[name]['house_count']:
            stats[name] = {
                'name': name,
                'house_count': row['house_count'] or 0,
                'community_count': row['community_count'] or 0,
                'avg_unit_price': float(row['avg_unit_price'] or 0),
            }

    return [stats[name] for name in sorted(stats)]


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


MORTGAGE_CATEGORIES = [
    ('none', '无抵押'),
    ('settled', '抵押已结清/可解除'),
    ('active', '有抵押'),
    ('unknown', '未说明'),
]

FLOOR_CATEGORIES = [
    ('low', '低楼层'),
    ('middle', '中楼层'),
    ('high', '高楼层'),
    ('basement', '地下/半地下'),
    ('unknown', '未说明'),
]


def _floor_category(value):
    text = str(value or '').strip()
    if not text:
        return 'unknown'

    compact = re.sub(r'\s+', '', text)
    if any(token in compact for token in ['地下', '半地下', '负']):
        return 'basement'
    if any(token in compact for token in ['低楼层', '底层', '低层', '下部']):
        return 'low'
    if any(token in compact for token in ['中楼层', '中层', '中部']):
        return 'middle'
    if any(token in compact for token in ['高楼层', '高层', '顶层', '上部']):
        return 'high'

    numbers = [int(n) for n in re.findall(r'\d+', compact)]
    if not numbers:
        return 'unknown'

    floor = numbers[0]
    total = numbers[-1] if len(numbers) > 1 else None
    if total and total > 0:
        ratio = floor / total
        if ratio <= 0.33:
            return 'low'
        if ratio <= 0.66:
            return 'middle'
        return 'high'
    if floor <= 6:
        return 'low'
    if floor <= 18:
        return 'middle'
    return 'high'


def _floor_category_options(queryset):
    counts = {key: 0 for key, _ in FLOOR_CATEGORIES}
    for value in queryset.values_list('louceng', flat=True):
        counts[_floor_category(value)] += 1

    return [
        {
            'value': key,
            'label': label,
            'count': counts[key],
        }
        for key, label in FLOOR_CATEGORIES
        if counts[key] > 0
    ]


def _filter_by_floor_category(queryset, category):
    if category not in dict(FLOOR_CATEGORIES):
        return queryset.filter(louceng__contains=category)

    ids = [
        house_id
        for house_id, value in queryset.values_list('id', 'louceng')
        if _floor_category(value) == category
    ]
    return queryset.filter(id__in=ids)


def _mortgage_category(value):
    text = str(value or '').strip()
    if not text:
        return 'unknown'

    compact = re.sub(r'\s+', '', text)
    if any(token in compact for token in ['暂无', '未知', '未上传', '未说明']):
        return 'unknown'
    if any(token in compact for token in ['已还清', '已结清', '已解除', '解除抵押', '注销抵押']):
        return 'settled'
    if any(token in compact for token in ['无抵押', '无贷款', '没有抵押']):
        return 'none'
    if any(token in compact for token in ['抵押', '贷款', '按揭', '银行']):
        return 'active'
    return 'unknown'


def _mortgage_category_options(queryset):
    counts = {key: 0 for key, _ in MORTGAGE_CATEGORIES}
    for value in queryset.values_list('diya', flat=True):
        counts[_mortgage_category(value)] += 1

    return [
        {
            'value': key,
            'label': label,
            'count': counts[key],
        }
        for key, label in MORTGAGE_CATEGORIES
        if counts[key] > 0
    ]


def _filter_by_mortgage_category(queryset, category):
    if category not in dict(MORTGAGE_CATEGORIES):
        return queryset.filter(diya__contains=category)

    ids = [
        house_id
        for house_id, value in queryset.values_list('id', 'diya')
        if _mortgage_category(value) == category
    ]
    return queryset.filter(id__in=ids)


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
