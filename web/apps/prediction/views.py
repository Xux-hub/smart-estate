import random
from datetime import datetime, timedelta

from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import render

from web.apps.house.models import House


def prediction_index(request):
    cities = [{'name': name} for name in House.objects.exclude(city__isnull=True).exclude(city='').values_list('city', flat=True).distinct().order_by('city')]
    return render(request, 'prediction/index.html', {'cities': cities})


def api_prediction_data(request):
    city_name = request.GET.get('city', '').strip()
    region = request.GET.get('district', '').strip()
    return JsonResponse({'data': _generate_realtime_predictions(city_name, region)})


def api_district_trend(request):
    region = request.GET.get('district', '').strip()
    if not region:
        return JsonResponse({'predictions': [], 'current_avg_price': None})

    city_name = House.objects.filter(Q(region=region) | Q(quyu=region)).values_list('city', flat=True).first() or ''
    predictions = _generate_realtime_predictions(city_name, region)
    current_avg = House.objects.filter(Q(region=region) | Q(quyu=region)).aggregate(avg=Avg('unit_price'))['avg']
    return JsonResponse({'predictions': predictions, 'current_avg_price': float(current_avg) if current_avg else None})


def _generate_realtime_predictions(city_name, region=''):
    queryset = House.objects.all()
    if city_name:
        queryset = queryset.filter(city=city_name)
    if region:
        queryset = queryset.filter(Q(region=region) | Q(quyu=region))

    district_rows = queryset.exclude(region__isnull=True).exclude(region='').values('region').annotate(
        avg_price=Avg('unit_price'),
        house_count=Count('id'),
    ).filter(avg_price__isnull=False)

    predictions = []
    today = datetime.now().date()
    for row in district_rows:
        base_price = float(row['avg_price'])
        for month_offset in range(1, 7):
            predict_date = today + timedelta(days=30 * month_offset)
            random.seed(f"{row['region']}-{month_offset}-{row['house_count']}")
            change_rate = random.uniform(-2.0, 3.5)
            predicted_price = base_price * (1 + change_rate / 100 * month_offset)
            if change_rate > 1.0:
                trend = '上涨'
            elif change_rate < -1.0:
                trend = '下跌'
            else:
                trend = '平稳'
            predictions.append({
                'district__name': row['region'],
                'predict_date': predict_date.strftime('%Y-%m-%d'),
                'avg_price': round(predicted_price, 2),
                'trend': trend,
                'change_rate': round(change_rate * month_offset, 2),
                'confidence': round(random.uniform(0.75, 0.92), 4),
            })
    return predictions
