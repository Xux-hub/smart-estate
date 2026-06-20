import json

from django.http import JsonResponse
from django.shortcuts import render

from analysis.price_analysis import get_db_connection
from analysis.prediction.model_predict import predict_detail
from analysis.prediction.trend_predict import predict_future_trend


def fetch_distinct_values(column, city=None, limit=100):
    allowed_columns = {
        "city",
        "region",
        "huxing",
        "chaoxiang",
        "zhuangxiu",
    }

    if column not in allowed_columns:
        raise ValueError("不允许查询该字段")

    connection = get_db_connection()

    sql = f"""
        SELECT {column}, COUNT(*) AS total
        FROM house_info
        WHERE {column} IS NOT NULL
          AND {column} <> ''
    """

    params = []

    if city:
        sql += " AND city = %s"
        params.append(city)

    sql += f"""
        GROUP BY {column}
        ORDER BY total DESC
        LIMIT %s
    """

    params.append(limit)

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    finally:
        connection.close()

    return [
        row[column]
        for row in rows
        if row.get(column)
    ]


def fetch_city_regions():
    connection = get_db_connection()

    sql = """
        SELECT city, region, COUNT(*) AS total
        FROM house_info
        WHERE city IS NOT NULL
          AND city <> ''
          AND region IS NOT NULL
          AND region <> ''
        GROUP BY city, region
        ORDER BY city, total DESC
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
    finally:
        connection.close()

    result = {}

    for row in rows:
        city = row.get("city")
        region = row.get("region")

        if not city or not region:
            continue

        result.setdefault(city, [])
        result[city].append(region)

    return result


def get_region_statistics(city, region):
    connection = get_db_connection()

    sql = """
        SELECT
            AVG(unit_price) AS average_price,
            COUNT(*) AS sample_count
        FROM house_info
        WHERE city = %s
          AND region = %s
          AND unit_price IS NOT NULL
          AND unit_price > 0
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (city, region))
            result = cursor.fetchone()
    finally:
        connection.close()

    average_price = result.get("average_price")

    return {
        "average_price": (
            float(average_price)
            if average_price is not None
            else None
        ),
        "sample_count": int(
            result.get("sample_count") or 0
        ),
    }


def prediction_index(request):
    cities = fetch_distinct_values(
        "city",
        limit=100,
    )

    city_regions = fetch_city_regions()

    first_city = (
        cities[0]
        if cities
        else "青岛"
    )

    context = {
        "provinces": ["山东省"],
        "cities": cities,
        "regions": city_regions.get(first_city, []),
        "city_regions_json": json.dumps(
            city_regions,
            ensure_ascii=False,
        ),
        "layouts": fetch_distinct_values("huxing", limit=60),
        "orientations": fetch_distinct_values("chaoxiang", limit=50),
        "decorations": fetch_distinct_values("zhuangxiu", limit=40),
    }

    return render(
        request,
        "prediction/index.html",
        context,
    )


def api_prediction_data(request):
    province = request.GET.get(
        "province",
        "山东省",
    ).strip()

    city = request.GET.get(
        "city",
        "",
    ).strip()

    region = request.GET.get(
        "district",
        "",
    ).strip()

    area_text = request.GET.get(
        "area",
        "",
    ).strip()

    huxing = request.GET.get(
        "huxing",
        "",
    ).strip()

    chaoxiang = request.GET.get(
        "chaoxiang",
        "",
    ).strip()

    zhuangxiu = request.GET.get(
        "zhuangxiu",
        "",
    ).strip()

    if province != "山东省":
        return JsonResponse(
            {"error": "当前系统仅支持山东省房源预测"},
            status=400,
        )

    if not city:
        return JsonResponse(
            {"error": "请选择城市"},
            status=400,
        )

    if not region:
        return JsonResponse(
            {"error": "请选择区域"},
            status=400,
        )

    try:
        area = float(area_text)
    except ValueError:
        return JsonResponse(
            {"error": "建筑面积必须为数字"},
            status=400,
        )

    if area <= 0:
        return JsonResponse(
            {"error": "建筑面积必须大于0"},
            status=400,
        )

    try:
        current_result = predict_detail(
            province=province,
            city=city,
            region=region,
            area=area,
            huxing=huxing,
            chaoxiang=chaoxiang,
            zhuangxiu=zhuangxiu,
        )

        future_result = predict_future_trend(
            city=city,
            region=region,
            current_house_unit_price=current_result["predicted_unit_price"],
            area=area,
            months=6,
        )
    except Exception as error:
        return JsonResponse(
            {"error": f"预测失败：{error}"},
            status=500,
        )

    region_statistics = get_region_statistics(
        city,
        region,
    )

    region_average = region_statistics["average_price"]
    predicted_unit_price = current_result["predicted_unit_price"]

    difference = None
    difference_rate = None

    if region_average:
        difference = predicted_unit_price - region_average
        difference_rate = difference / region_average * 100

    data = {
        "province": province,
        "city": city,
        "region": region,
        "area": area,
        "huxing": huxing,
        "chaoxiang": chaoxiang,
        "zhuangxiu": zhuangxiu,
        "predicted_unit_price": predicted_unit_price,
        "predicted_total_price": current_result["predicted_total_price"],
        "region_average_unit_price": (
            round(region_average, 2)
            if region_average is not None
            else None
        ),
        "difference": (
            round(difference, 2)
            if difference is not None
            else None
        ),
        "difference_rate": (
            round(difference_rate, 2)
            if difference_rate is not None
            else None
        ),
        "requested_city": future_result["requested_city"],
        "requested_region": future_result["requested_region"],
        "trend_source": future_result["source"],
        "used_fallback": future_result["used_fallback"],
        "trend_method": future_result["selected_model"],
        "data_end_month": future_result["data_end_month"],
        "history": future_result["history"],
        "future": future_result["future"],
        "future_summary": future_result["summary"],
        "trend_metrics": future_result["metrics"],
    }

    return JsonResponse(
        {"data": data}
    )


def api_district_trend(request):
    city = request.GET.get(
        "city",
        "",
    ).strip()

    region = request.GET.get(
        "district",
        "",
    ).strip()

    if not city or not region:
        return JsonResponse(
            {"error": "请选择城市和区域"},
            status=400,
        )

    statistics = get_region_statistics(city, region)
    average_price = statistics["average_price"]

    if average_price is None:
        return JsonResponse(
            {"error": "该城市区域没有有效房价数据"},
            status=404,
        )

    try:
        result = predict_future_trend(
            city=city,
            region=region,
            current_house_unit_price=average_price,
            area=100,
            months=6,
        )
    except Exception as error:
        return JsonResponse(
            {"error": f"趋势预测失败：{error}"},
            status=500,
        )

    return JsonResponse(result)
