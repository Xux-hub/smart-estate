import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Count, Q

from web.apps.house.models import City, District, PricePrediction, House


def prediction_index(request):
    """房价预测首页"""
    cities = City.objects.all()
    context = {'cities': cities}
    return render(request, 'prediction/index.html', context)


def api_prediction_data(request):
    """获取预测数据 (API) - 基于现有数据生成预测"""
    city_name = request.GET.get('city', '北京')
    district_id = request.GET.get('district', '')

    # 先检查是否有预存的预测数据
    queryset = PricePrediction.objects.select_related('district__city')
    if city_name:
        queryset = queryset.filter(district__city__name=city_name)
    if district_id:
        queryset = queryset.filter(district_id=district_id)

    predictions = list(queryset.order_by('predict_date').values(
        'district__name', 'predict_date', 'avg_price', 'trend', 'change_rate', 'confidence'
    ))

    # 如果没有预存数据，基于现有房源实时生成预测
    if not predictions:
        predictions = _generate_realtime_predictions(city_name, district_id)

    return JsonResponse({'data': predictions})


def _generate_realtime_predictions(city_name, district_id=None):
    """基于现有房源数据生成简易预测"""
    import random

    # 获取各区域当前均价
    districts_qs = District.objects.filter(city__name=city_name)
    if district_id:
        districts_qs = districts_qs.filter(id=district_id)

    districts_qs = districts_qs.annotate(
        avg_price=Avg('communities__houses__unit_price',
                      filter=Q(communities__houses__status=1)),
        house_count=Count('communities__houses',
                          filter=Q(communities__houses__status=1)),
    ).filter(avg_price__isnull=False)

    predictions = []
    today = datetime.now().date()

    for district in districts_qs:
        base_price = float(district.avg_price)

        # 生成未来6个月的预测数据（简易模拟）
        for month_offset in range(1, 7):
            predict_date = today + timedelta(days=30 * month_offset)
            # 模拟价格波动（基于房源数量和随机因素）
            random.seed(hash(f"{district.name}{month_offset}"))
            change_rate = random.uniform(-3.0, 5.0)
            predicted_price = base_price * (1 + change_rate / 100 * month_offset)

            if change_rate > 1.5:
                trend = '上涨'
            elif change_rate < -1.5:
                trend = '下跌'
            else:
                trend = '平稳'

            predictions.append({
                'district__name': district.name,
                'predict_date': predict_date.strftime('%Y-%m-%d'),
                'avg_price': round(predicted_price, 2),
                'trend': trend,
                'change_rate': round(change_rate * month_offset, 2),
                'confidence': round(random.uniform(0.75, 0.92), 4),
            })

    return predictions


def api_district_trend(request):
    """获取区域历史价格趋势 (API)"""
    district_id = request.GET.get('district', '')

    if not district_id:
        return JsonResponse({'predictions': [], 'current_avg_price': None})

    # 获取预测数据
    predictions = list(PricePrediction.objects.filter(
        district_id=district_id
    ).order_by('predict_date').values('predict_date', 'avg_price', 'trend'))

    # 如果没有预存数据，生成实时预测
    if not predictions:
        district = District.objects.filter(id=district_id).first()
        if district:
            city_name = district.city.name
            all_preds = _generate_realtime_predictions(city_name, district_id)
            predictions = [
                {'predict_date': p['predict_date'], 'avg_price': p['avg_price'], 'trend': p['trend']}
                for p in all_preds
            ]

    # 获取当前实际均价
    current_avg = House.objects.filter(
        community__district_id=district_id, status=1
    ).aggregate(avg=Avg('unit_price'))['avg']

    if current_avg:
        current_avg = float(current_avg)

    return JsonResponse({
        'predictions': predictions,
        'current_avg_price': current_avg,
    })
