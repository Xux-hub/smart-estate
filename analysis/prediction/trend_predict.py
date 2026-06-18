from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "future_random_forest.pkl"
)


@lru_cache(maxsize=1)
def load_future_model():
    """
    加载随机森林未来趋势模型。

    模型首次使用时读取，后续网页请求直接复用，
    减少重复加载时间。
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "未找到随机森林未来趋势模型"
        )

    return joblib.load(
        MODEL_PATH
    )


def months_between(
    first_month,
    current_month,
):
    """
    计算两个自然月之间相隔的月份数量。
    """
    return (
        (
            current_month.year
            - first_month.year
        )
        * 12
        + current_month.month
        - first_month.month
    )


def select_trend_source(
    model_data,
    region,
):
    """
    根据区域测试结果选择未来趋势来源。

    区域模型表现可靠时使用该区域自己的房价变化。
    区域模型误差较大时改用青岛整体趋势，
    具体房屋当前估值仍保留原区域特征。
    """
    region_information = model_data[
        "regions"
    ]

    region_metrics = model_data.get(
        "per_region_metrics",
        {},
    )

    rule = model_data.get(
        "reliability_rule",
        {},
    )

    minimum_r2 = float(
        rule.get(
            "minimum_r2",
            0.0,
        )
    )

    maximum_mape = float(
        rule.get(
            "maximum_mape",
            5.0,
        )
    )

    minimum_records = int(
        rule.get(
            "minimum_records",
            2,
        )
    )

    if region not in region_information:
        return (
            "__ALL__",
            "青岛整体",
            True,
        )

    metrics = region_metrics.get(
        region
    )

    if not metrics:
        return (
            "__ALL__",
            "青岛整体",
            True,
        )

    r2 = metrics.get(
        "r2"
    )

    mape = metrics.get(
        "mape"
    )

    records = int(
        metrics.get(
            "records",
            0,
        )
    )

    region_result_is_reliable = (
        r2 is not None
        and mape is not None
        and r2 >= minimum_r2
        and mape <= maximum_mape
        and records >= minimum_records
    )

    if region_result_is_reliable:
        return (
            region,
            region,
            False,
        )

    return (
        "__ALL__",
        "青岛整体",
        True,
    )


def build_feature_row(
    region,
    period,
    base_month,
    known_prices,
):
    """
    根据最近六个月房价整理下一个月的模型输入数据。

    列表最后一个值代表最近一个月房价，
    前面的值依次代表更早月份房价。
    """
    price_1_month_ago = float(
        known_prices[-1]
    )

    price_2_months_ago = float(
        known_prices[-2]
    )

    price_3_months_ago = float(
        known_prices[-3]
    )

    price_4_months_ago = float(
        known_prices[-4]
    )

    price_5_months_ago = float(
        known_prices[-5]
    )

    price_6_months_ago = float(
        known_prices[-6]
    )

    month_number = period.month

    return {
        "region": region,
        "month_index": float(
            months_between(
                base_month,
                period,
            )
        ),
        "month_sin": float(
            np.sin(
                2
                * np.pi
                * month_number
                / 12
            )
        ),
        "month_cos": float(
            np.cos(
                2
                * np.pi
                * month_number
                / 12
            )
        ),
        "price_1_month_ago": (
            price_1_month_ago
        ),
        "price_2_months_ago": (
            price_2_months_ago
        ),
        "price_3_months_ago": (
            price_3_months_ago
        ),
        "price_4_months_ago": (
            price_4_months_ago
        ),
        "price_5_months_ago": (
            price_5_months_ago
        ),
        "price_6_months_ago": (
            price_6_months_ago
        ),
        "average_price_last_3_months": float(
            np.mean(
                known_prices[-3:]
            )
        ),
        "average_price_last_6_months": float(
            np.mean(
                known_prices[-6:]
            )
        ),
        "price_std_last_3_months": float(
            np.std(
                known_prices[-3:]
            )
        ),
        "change_from_previous_month": (
            price_1_month_ago
            - price_2_months_ago
        ),
        "change_from_3_months_ago": (
            price_1_month_ago
            - price_4_months_ago
        ),
    }


def predict_future_trend(
    region,
    current_house_unit_price,
    area,
    months=6,
):
    """
    预测目标房屋未来若干个月的参考单价和总价。

    随机森林先预测区域未来价格，
    再将区域变化比例应用到目标房屋当前估值。
    """
    model_data = load_future_model()

    (
        model_region,
        source_name,
        used_fallback,
    ) = select_trend_source(
        model_data,
        region,
    )

    region_information = (
        model_data["regions"]
    )

    info = region_information[
        model_region
    ]

    pipeline = model_data[
        "pipeline"
    ]

    feature_names = model_data[
        "features"
    ]

    base_month = pd.Period(
        model_data["base_month"],
        freq="M",
    )

    last_month = pd.Period(
        info["last_month"],
        freq="M",
    )

    known_prices = [
        float(value)
        for value in info[
            "known_prices"
        ]
    ]

    if len(known_prices) < 6:
        raise ValueError(
            "历史月份不足6个月"
        )

    current_unit_price = float(
        current_house_unit_price
    )

    area_value = float(
        area
    )

    if current_unit_price <= 0:
        raise ValueError(
            "当前预测单价必须大于0"
        )

    if area_value <= 0:
        raise ValueError(
            "建筑面积必须大于0"
        )

    base_region_price = float(
        info["last_region_price"]
    )

    if base_region_price <= 0:
        raise ValueError(
            "区域基准价格无效"
        )

    future_results = []

    for month_number in range(
        1,
        months + 1,
    ):
        forecast_month = (
            last_month
            + month_number
        )

        # 根据最近几个月房价
        # 整理当前月份需要输入模型的数据。
        feature_row = build_feature_row(
            region=model_region,
            period=forecast_month,
            base_month=base_month,
            known_prices=known_prices,
        )

        feature_data = pd.DataFrame([
            feature_row
        ])

        predicted_region_price = float(
            pipeline.predict(
                feature_data[
                    feature_names
                ]
            )[0]
        )

        # 限制单月预测结果的变化范围，
        # 避免少量异常数据造成价格剧烈波动。
        recent_price_level = float(
            np.median(
                known_prices[-6:]
            )
        )

        predicted_region_price = float(
            np.clip(
                predicted_region_price,
                recent_price_level
                * 0.85,
                recent_price_level
                * 1.15,
            )
        )

        # 将本月预测价格加入已有月份数据，
        # 下个月预测时继续使用这个结果。
        known_prices.append(
            predicted_region_price
        )

        region_change_ratio = (
            predicted_region_price
            / base_region_price
        )

        house_unit_price = (
            current_unit_price
            * region_change_ratio
        )

        house_total_price = (
            house_unit_price
            * area_value
            / 10000
        )

        future_results.append({
            "month": str(
                forecast_month
            ),
            "region_unit_price": round(
                predicted_region_price,
                2,
            ),
            "house_unit_price": round(
                house_unit_price,
                2,
            ),
            "house_total_price": round(
                house_total_price,
                2,
            ),
        })

    final_unit_price = (
        future_results[-1][
            "house_unit_price"
        ]
    )

    change_rate = (
        (
            final_unit_price
            - current_unit_price
        )
        / current_unit_price
        * 100
    )

    if change_rate > 2:
        trend = "上涨"
    elif change_rate < -2:
        trend = "下降"
    else:
        trend = "整体平稳"

    region_metrics = model_data.get(
        "per_region_metrics",
        {},
    )

    metrics = region_metrics.get(
        model_region,
        model_data["metrics"],
    )

    month_1 = future_results[0]

    month_3 = future_results[
        min(
            2,
            len(future_results) - 1,
        )
    ]

    month_6 = future_results[
        min(
            5,
            len(future_results) - 1,
        )
    ]

    return {
        "requested_region": region,
        "source": source_name,
        "used_fallback": (
            used_fallback
        ),
        "selected_model": (
            "random_forest_time_series"
        ),
        "data_end_month": (
            info["last_month"]
        ),
        "history": (
            info["history"]
        ),
        "future": (
            future_results
        ),
        "summary": {
            "month_1_unit_price": (
                month_1[
                    "house_unit_price"
                ]
            ),
            "month_1_total_price": (
                month_1[
                    "house_total_price"
                ]
            ),
            "month_3_unit_price": (
                month_3[
                    "house_unit_price"
                ]
            ),
            "month_3_total_price": (
                month_3[
                    "house_total_price"
                ]
            ),
            "month_6_unit_price": (
                month_6[
                    "house_unit_price"
                ]
            ),
            "month_6_total_price": (
                month_6[
                    "house_total_price"
                ]
            ),
            "six_month_change_rate": round(
                float(change_rate),
                2,
            ),
            "trend": trend,
        },
        "metrics": metrics,
        "best_params": (
            model_data[
                "best_params"
            ]
        ),
    }
