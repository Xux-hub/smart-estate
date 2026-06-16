import random
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render

from web.apps.house.models import City, RegionStat


def prediction_index(request):
    cities = [{'name': city.name} for city in City.objects.only('name').order_by('name')]
    return render(request, 'prediction/index.html', {'cities': cities})


def api_prediction_data(request):
    city_name = request.GET.get('city', '').strip()
    region = request.GET.get('district', '').strip()
    return JsonResponse({'data': _generate_realtime_predictions(city_name, region)})


def api_district_trend(request):
    region = request.GET.get('district', '').strip()
    if not region:
        return JsonResponse({'predictions': [], 'current_avg_price': None})

    stat = RegionStat.objects.filter(region=region).order_by('-house_count').first()
    predictions = _generate_realtime_predictions(stat.city if stat else '', region)
    return JsonResponse({
        'predictions': predictions,
        'current_avg_price': float(stat.avg_unit_price) if stat and stat.avg_unit_price else None,
    })


def _generate_realtime_predictions(city_name, region=''):
    queryset = RegionStat.objects.exclude(avg_unit_price__isnull=True)
    if city_name:
        queryset = queryset.filter(city=city_name)
    if region:
        queryset = queryset.filter(region=region)

    predictions = []
    today = datetime.now().date()
    for row in queryset:
        base_price = float(row.avg_unit_price)
        for month_offset in range(1, 7):
            predict_date = today + timedelta(days=30 * month_offset)
            random.seed(f'{row.city}-{row.region}-{month_offset}-{row.house_count}')
            change_rate = random.uniform(-2.0, 3.5)
            predicted_price = base_price * (1 + change_rate / 100 * month_offset)
            if change_rate > 1.0:
                trend = '上涨'
            elif change_rate < -1.0:
                trend = '下跌'
            else:
                trend = '平稳'
            predictions.append({
                'district__name': row.region,
                'predict_date': predict_date.strftime('%Y-%m-%d'),
                'avg_price': round(predicted_price, 2),
                'trend': trend,
                'change_rate': round(change_rate * month_offset, 2),
                'confidence': round(random.uniform(0.75, 0.92), 4),
            })
    return predictions
