from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "models" / "future_random_forest.pkl"


@lru_cache(maxsize=1)
def load_future_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("未找到随机森林未来趋势模型")

    return joblib.load(MODEL_PATH)


def make_scope_key(level, city, region):
    return f"{level}::{city}::{region}"


def months_between(first_month, current_month):
    return (
        (current_month.year - first_month.year)
        * 12
        + current_month.month
        - first_month.month
    )


def scope_is_reliable(model_data, scope_key):
    metrics = model_data.get("per_scope_metrics", {}).get(scope_key)

    if not metrics:
        return False

    rule = model_data.get("reliability_rule", {})

    minimum_r2 = float(rule.get("minimum_r2", 0.0))
    maximum_mape = float(rule.get("maximum_mape", 6.0))
    minimum_records = int(rule.get("minimum_records", 2))

    r2 = metrics.get("r2")
    mape = metrics.get("mape")
    records = int(metrics.get("records", 0))

    return (
        r2 is not None
        and mape is not None
        and r2 >= minimum_r2
        and mape <= maximum_mape
        and records >= minimum_records
    )


def select_trend_scope(model_data, city, region):
    scopes = model_data["scopes"]

    region_key = make_scope_key(
        "region",
        city,
        region,
    )

    city_key = make_scope_key(
        "city",
        city,
        "__ALL__",
    )

    province_key = make_scope_key(
        "province",
        "__ALL__",
        "__ALL__",
    )

    if region_key in scopes and scope_is_reliable(model_data, region_key):
        return region_key, False

    if city_key in scopes and scope_is_reliable(model_data, city_key):
        return city_key, True

    if province_key in scopes:
        return province_key, True

    if city_key in scopes:
        return city_key, True

    if region_key in scopes:
        return region_key, False

    raise ValueError("没有找到可用的未来趋势数据")


def build_feature_row(scope_info, period, base_month, known_prices):
    price_1 = float(known_prices[-1])
    price_2 = float(known_prices[-2])
    price_3 = float(known_prices[-3])
    price_4 = float(known_prices[-4])
    price_5 = float(known_prices[-5])
    price_6 = float(known_prices[-6])

    month_number = period.month

    return {
        "level": scope_info["level"],
        "city": scope_info["city"],
        "region": scope_info["region"],
        "month_index": float(months_between(base_month, period)),
        "month_sin": float(np.sin(2 * np.pi * month_number / 12)),
        "month_cos": float(np.cos(2 * np.pi * month_number / 12)),
        "price_1_month_ago": price_1,
        "price_2_months_ago": price_2,
        "price_3_months_ago": price_3,
        "price_4_months_ago": price_4,
        "price_5_months_ago": price_5,
        "price_6_months_ago": price_6,
        "average_price_last_3_months": float(np.mean(known_prices[-3:])),
        "average_price_last_6_months": float(np.mean(known_prices[-6:])),
        "price_std_last_3_months": float(np.std(known_prices[-3:])),
        "change_from_previous_month": price_1 - price_2,
        "change_from_3_months_ago": price_1 - price_4,
    }


def predict_future_trend(
    region,
    current_house_unit_price,
    area,
    months=6,
    city="青岛",
):
    model_data = load_future_model()

    scope_key, used_fallback = select_trend_scope(
        model_data,
        city,
        region,
    )

    scope_info = model_data["scopes"][scope_key]

    pipeline = model_data["pipeline"]
    feature_names = model_data["features"]

    base_month = pd.Period(
        model_data["base_month"],
        freq="M",
    )

    last_month = pd.Period(
        scope_info["last_month"],
        freq="M",
    )

    known_prices = [
        float(value)
        for value in scope_info["known_prices"]
    ]

    if len(known_prices) < 6:
        raise ValueError("历史月份不足6个月")

    current_unit_price = float(current_house_unit_price)
    area_value = float(area)

    if current_unit_price <= 0:
        raise ValueError("当前预测单价必须大于0")

    if area_value <= 0:
        raise ValueError("建筑面积必须大于0")

    base_scope_price = float(scope_info["last_price"])

    if base_scope_price <= 0:
        raise ValueError("趋势基准价格无效")

    future_results = []

    for month_number in range(1, months + 1):
        forecast_month = last_month + month_number

        feature_row = build_feature_row(
            scope_info,
            forecast_month,
            base_month,
            known_prices,
        )

        feature_data = pd.DataFrame([feature_row])

        predicted_scope_price = float(
            pipeline.predict(
                feature_data[feature_names]
            )[0]
        )

        recent_price_level = float(
            np.median(known_prices[-6:])
        )

        predicted_scope_price = float(
            np.clip(
                predicted_scope_price,
                recent_price_level * 0.85,
                recent_price_level * 1.15,
            )
        )

        known_prices.append(
            predicted_scope_price
        )

        change_ratio = (
            predicted_scope_price
            / base_scope_price
        )

        house_unit_price = (
            current_unit_price
            * change_ratio
        )

        house_total_price = (
            house_unit_price
            * area_value
            / 10000
        )

        future_results.append({
            "month": str(forecast_month),
            "region_unit_price": round(predicted_scope_price, 2),
            "house_unit_price": round(house_unit_price, 2),
            "house_total_price": round(house_total_price, 2),
        })

    final_unit_price = future_results[-1]["house_unit_price"]

    change_rate = (
        (final_unit_price - current_unit_price)
        / current_unit_price
        * 100
    )

    if change_rate > 2:
        trend = "上涨"
    elif change_rate < -2:
        trend = "下降"
    else:
        trend = "整体平稳"

    metrics = (
        model_data
        .get("per_scope_metrics", {})
        .get(scope_key, model_data["metrics"])
    )

    month_1 = future_results[0]
    month_3 = future_results[min(2, len(future_results) - 1)]
    month_6 = future_results[min(5, len(future_results) - 1)]

    return {
        "requested_city": city,
        "requested_region": region,
        "source": scope_info["scope_name"],
        "used_fallback": used_fallback,
        "selected_model": "random_forest_province_city_region_time_series",
        "data_end_month": scope_info["last_month"],
        "history": scope_info["history"],
        "future": future_results,
        "summary": {
            "month_1_unit_price": month_1["house_unit_price"],
            "month_1_total_price": month_1["house_total_price"],
            "month_3_unit_price": month_3["house_unit_price"],
            "month_3_total_price": month_3["house_total_price"],
            "month_6_unit_price": month_6["house_unit_price"],
            "month_6_total_price": month_6["house_total_price"],
            "six_month_change_rate": round(float(change_rate), 2),
            "trend": trend,
        },
        "metrics": metrics,
        "best_params": model_data["best_params"],
    }
