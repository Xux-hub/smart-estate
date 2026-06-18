from django.http import JsonResponse
from django.shortcuts import render

from analysis.price_analysis import get_db_connection
from analysis.prediction.model_predict import predict_detail
from analysis.prediction.trend_predict import predict_future_trend


def fetch_top_values(column, limit=30):
    """
    从数据库中读取预测页面下拉框常用选项。

    只允许读取固定字段，避免外部参数直接拼接到SQL中。
    """
    allowed_columns = {
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
        WHERE city = %s
          AND {column} IS NOT NULL
          AND {column} <> ''
        GROUP BY {column}
        ORDER BY total DESC
        LIMIT %s
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, ("青岛", limit))
            rows = cursor.fetchall()
    finally:
        connection.close()

    return [
        row[column]
        for row in rows
        if row.get(column)
    ]


def get_region_statistics(region):
    """
    查询指定区域的平均单价和样本数量。

    该结果用于和模型预测单价进行对比，
    帮助用户判断当前输入房源相对区域均价的高低。
    """
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
            cursor.execute(sql, ("青岛", region))
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
    """
    渲染房价预测页面。
    """
    context = {
        "cities": ["青岛"],
        "regions": fetch_top_values("region", 30),
        "layouts": fetch_top_values("huxing", 40),
        "orientations": fetch_top_values("chaoxiang", 30),
        "decorations": fetch_top_values("zhuangxiu", 20),
    }

    return render(
        request,
        "prediction/index.html",
        context,
    )


def api_prediction_data(request):
    """
    房价预测页面的数据接口。

    当前价格由房源估值随机森林给出。
    未来趋势由随机森林时间趋势模型给出。
    """
    city = request.GET.get("city", "青岛").strip()
    region = request.GET.get("district", "").strip()
    area_text = request.GET.get("area", "").strip()
    huxing = request.GET.get("huxing", "").strip()
    chaoxiang = request.GET.get("chaoxiang", "").strip()
    zhuangxiu = request.GET.get("zhuangxiu", "").strip()

    if city != "青岛":
        return JsonResponse(
            {
                "error": "当前预测模型仅支持青岛市房源",
            },
            status=400,
        )

    if not region:
        return JsonResponse(
            {
                "error": "请选择区域",
            },
            status=400,
        )

    try:
        area = float(area_text)
    except ValueError:
        return JsonResponse(
            {
                "error": "建筑面积必须为数字",
            },
            status=400,
        )

    if area <= 0:
        return JsonResponse(
            {
                "error": "建筑面积必须大于0",
            },
            status=400,
        )

    try:
        current_result = predict_detail(
            area=area,
            region=region,
            huxing=huxing,
            chaoxiang=chaoxiang,
            zhuangxiu=zhuangxiu,
        )

        future_result = predict_future_trend(
            region=region,
            current_house_unit_price=current_result[
                "predicted_unit_price"
            ],
            area=area,
            months=6,
        )
    except Exception as error:
        return JsonResponse(
            {
                "error": f"预测失败：{error}",
            },
            status=500,
        )

    region_statistics = get_region_statistics(region)

    region_average = region_statistics[
        "average_price"
    ]

    predicted_unit_price = current_result[
        "predicted_unit_price"
    ]

    difference = None
    difference_rate = None

    if region_average:
        difference = (
            predicted_unit_price
            - region_average
        )

        difference_rate = (
            difference
            / region_average
            * 100
        )

    data = {
        "city": city,
        "region": region,
        "area": area,
        "huxing": huxing,
        "chaoxiang": chaoxiang,
        "zhuangxiu": zhuangxiu,

        "predicted_unit_price": predicted_unit_price,
        "predicted_total_price": current_result[
            "predicted_total_price"
        ],

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

        "mae": current_result.get("mae"),
        "rmse": current_result.get("rmse"),
        "r2": current_result.get("r2"),
        "model_name": current_result.get("model_name"),

        "region_sample_count": region_statistics[
            "sample_count"
        ],

        "requested_region": future_result[
            "requested_region"
        ],
        "trend_source": future_result[
            "source"
        ],
        "used_fallback": future_result[
            "used_fallback"
        ],
        "trend_method": future_result[
            "selected_model"
        ],
        "data_end_month": future_result[
            "data_end_month"
        ],
        "history": future_result[
            "history"
        ],
        "future": future_result[
            "future"
        ],
        "future_summary": future_result[
            "summary"
        ],
        "trend_metrics": future_result[
            "metrics"
        ],
    }

    return JsonResponse(
        {
            "data": data,
        }
    )


def api_district_trend(request):
    """
    保留区域趋势接口，便于其他页面复用。
    """
    region = request.GET.get("district", "").strip()

    if not region:
        return JsonResponse(
            {
                "error": "请选择区域",
            },
            status=400,
        )

    statistics = get_region_statistics(region)
    average_price = statistics["average_price"]

    if average_price is None:
        return JsonResponse(
            {
                "error": "该区域没有有效房价数据",
            },
            status=404,
        )

    try:
        result = predict_future_trend(
            region=region,
            current_house_unit_price=average_price,
            area=100,
            months=6,
        )
    except Exception as error:
        return JsonResponse(
            {
                "error": f"趋势预测失败：{error}",
            },
            status=500,
        )

    return JsonResponse(result)
