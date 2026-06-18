import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from analysis.price_analysis import load_house_data

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
RESULT_DIR = BASE_DIR / "results"

MODEL_PATH = (
    MODEL_DIR
    / "future_random_forest.pkl"
)

METRICS_PATH = (
    RESULT_DIR
    / "future_rf_metrics.json"
)

COMPARISON_PATH = (
    RESULT_DIR
    / "future_rf_model_comparison.csv"
)

MONTHLY_PATH = (
    RESULT_DIR
    / "future_monthly_region_prices.csv"
)

PREDICTION_PATH = (
    RESULT_DIR
    / "future_rf_test_predictions.csv"
)

CATEGORICAL_FEATURES = [
    "region",
]

NUMERIC_FEATURES = [
    "month_index",
    "month_sin",
    "month_cos",
    "price_1_month_ago",
    "price_2_months_ago",
    "price_3_months_ago",
    "price_4_months_ago",
    "price_5_months_ago",
    "price_6_months_ago",
    "average_price_last_3_months",
    "average_price_last_6_months",
    "price_std_last_3_months",
    "change_from_previous_month",
    "change_from_3_months_ago",
]

FEATURES = (
    CATEGORICAL_FEATURES
    + NUMERIC_FEATURES
)

TARGET = "target_price"


def load_data(remove_outliers):
    """
    读取青岛房源并整理未来趋势建模需要的字段。

    趋势模型只使用区域、挂牌时间和单价。
    其他房屋属性由当前估值模型处理。
    """
    data = load_house_data(
        city="青岛"
    )[
        [
            "region",
            "shijian",
            "unit_price",
        ]
    ].copy()

    data["date"] = pd.to_datetime(
        data["shijian"],
        errors="coerce",
        format="mixed",
    )

    data["unit_price"] = pd.to_numeric(
        data["unit_price"],
        errors="coerce",
    )

    data["region"] = (
        data["region"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    data = data.dropna(
        subset=[
            "date",
            "unit_price",
        ]
    )

    data = data[
        (data["region"] != "")
        & (data["unit_price"] >= 500)
        & (data["unit_price"] <= 200000)
    ].copy()

    if remove_outliers:
        # 每个区域分别计算正常价格范围，
        # 避免高价区域和低价区域相互影响。
        first_quartile = data.groupby(
            "region"
        )["unit_price"].transform(
            lambda values:
            values.quantile(0.25)
        )

        third_quartile = data.groupby(
            "region"
        )["unit_price"].transform(
            lambda values:
            values.quantile(0.75)
        )

        quartile_distance = (
            third_quartile
            - first_quartile
        )

        lower_limit = (
            first_quartile
            - 1.5 * quartile_distance
        ).clip(lower=500)

        upper_limit = (
            third_quartile
            + 1.5 * quartile_distance
        ).clip(upper=200000)

        data = data[
            (
                data["unit_price"]
                >= lower_limit
            )
            & (
                data["unit_price"]
                <= upper_limit
            )
        ].copy()

    return data.reset_index(
        drop=True
    )


def build_one_monthly(
    data,
    region_key,
    region_name=None,
):
    """
    将房源记录整理为连续的月度价格数据。

    每个月使用中位单价代表该区域当月房价，
    减少少量高价房和低价房的影响。
    """
    if region_name is None:
        subset = data.copy()
    else:
        subset = data[
            data["region"]
            == region_name
        ].copy()

    subset["month"] = (
        subset["date"]
        .dt.to_period("M")
    )

    monthly = (
        subset.groupby("month")
        .agg(
            median_unit_price=(
                "unit_price",
                "median",
            ),
            sample_count=(
                "unit_price",
                "size",
            ),
        )
        .sort_index()
    )

    selected = None
    threshold_used = None

    # 优先保留样本数量较充足的月份。
    # 当月份数量不足时逐步降低最低样本要求。
    for threshold in [
        30,
        20,
        10,
        5,
        1,
    ]:
        candidate = monthly[
            monthly["sample_count"]
            >= threshold
        ].copy()

        if len(candidate) >= 18:
            selected = candidate
            threshold_used = threshold
            break

    if selected is None:
        return None

    full_months = pd.period_range(
        selected.index.min(),
        selected.index.max(),
        freq="M",
    )

    selected = selected.reindex(
        full_months
    )

    # 少量缺失月份使用前后月份价格平滑补充，
    # 保持月份连续。
    selected[
        "median_unit_price"
    ] = (
        selected[
            "median_unit_price"
        ]
        .interpolate()
        .ffill()
        .bfill()
    )

    selected["sample_count"] = (
        selected["sample_count"]
        .fillna(0)
        .astype(int)
    )

    # 三个月指数平滑可以降低单个月份
    # 房源组成变化造成的突然波动。
    selected["trend_price"] = (
        selected[
            "median_unit_price"
        ]
        .ewm(
            span=3,
            adjust=False,
        )
        .mean()
    )

    selected.index.name = "month"

    selected = (
        selected.reset_index()
    )

    selected["region"] = (
        region_key
    )

    selected[
        "sample_threshold"
    ] = threshold_used

    return selected


def build_monthly_data(data):
    """
    建立青岛整体和各区域的月度价格数据。
    """
    regions = sorted(
        data["region"]
        .dropna()
        .unique()
        .tolist()
    )

    monthly_frames = []

    overall = build_one_monthly(
        data,
        "__ALL__",
        None,
    )

    if overall is not None:
        monthly_frames.append(
            overall
        )

    for region in regions:
        monthly = build_one_monthly(
            data,
            region,
            region,
        )

        if monthly is not None:
            monthly_frames.append(
                monthly
            )

    if not monthly_frames:
        raise RuntimeError(
            "没有足够的月度数据"
        )

    return pd.concat(
        monthly_frames,
        ignore_index=True,
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


def build_feature_data(
    monthly_data,
):
    """
    根据前六个月房价整理随机森林训练数据。

    每一行数据使用目标月份之前的房价信息，
    预测目标月份的区域价格。
    """
    base_month = (
        monthly_data["month"].min()
    )

    rows = []

    for region, group in monthly_data.groupby(
        "region"
    ):
        group = (
            group.sort_values(
                "month"
            )
            .reset_index(
                drop=True
            )
        )

        known_prices = group[
            "trend_price"
        ].to_numpy(
            dtype=float
        )

        months = group[
            "month"
        ].tolist()

        for index in range(
            6,
            len(group),
        ):
            previous_prices = (
                known_prices[:index]
            )

            target_month = (
                months[index]
            )

            price_1_month_ago = float(
                previous_prices[-1]
            )

            price_2_months_ago = float(
                previous_prices[-2]
            )

            price_3_months_ago = float(
                previous_prices[-3]
            )

            price_4_months_ago = float(
                previous_prices[-4]
            )

            price_5_months_ago = float(
                previous_prices[-5]
            )

            price_6_months_ago = float(
                previous_prices[-6]
            )

            month_number = (
                target_month.month
            )

            rows.append({
                "region": region,
                "month_index": float(
                    months_between(
                        base_month,
                        target_month,
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
                        previous_prices[-3:]
                    )
                ),
                "average_price_last_6_months": float(
                    np.mean(
                        previous_prices[-6:]
                    )
                ),
                "price_std_last_3_months": float(
                    np.std(
                        previous_prices[-3:]
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
                TARGET: float(
                    known_prices[index]
                ),
                "target_month": str(
                    target_month
                ),
            })

    if not rows:
        raise RuntimeError(
            "无法构造随机森林时间特征"
        )

    dataset = pd.DataFrame(
        rows
    )

    dataset = dataset.sort_values(
        [
            "target_month",
            "region",
        ]
    ).reset_index(
        drop=True
    )

    return (
        dataset,
        base_month,
    )


def create_pipeline(model):
    """
    建立统一的数据处理和模型训练流程。

    区域转换为数值编码，
    其他价格和月份信息进行缺失处理和标准化。
    """
    numeric_processor = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="median",
            ),
        ),
        (
            "scaler",
            StandardScaler(),
        ),
    ])

    categorical_processor = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent",
            ),
        ),
        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=True,
            ),
        ),
    ])

    processor = ColumnTransformer([
        (
            "numeric",
            numeric_processor,
            NUMERIC_FEATURES,
        ),
        (
            "categorical",
            categorical_processor,
            CATEGORICAL_FEATURES,
        ),
    ])

    return Pipeline([
        (
            "processor",
            processor,
        ),
        (
            "model",
            model,
        ),
    ])


def calculate_metrics(
    actual_values,
    predicted_values,
):
    """
    计算未来趋势模型的常用评价指标。
    """
    actual_values = np.asarray(
        actual_values,
        dtype=float,
    )

    predicted_values = np.asarray(
        predicted_values,
        dtype=float,
    )

    mae = mean_absolute_error(
        actual_values,
        predicted_values,
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual_values,
            predicted_values,
        )
    )

    r2 = (
        r2_score(
            actual_values,
            predicted_values,
        )
        if len(actual_values) >= 2
        else None
    )

    valid = (
        actual_values != 0
    )

    mape = (
        np.mean(
            np.abs(
                (
                    actual_values[valid]
                    - predicted_values[valid]
                )
                / actual_values[valid]
            )
        )
        * 100
        if valid.any()
        else None
    )

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": (
            float(r2)
            if r2 is not None
            else None
        ),
        "mape": (
            float(mape)
            if mape is not None
            else None
        ),
    }


def split_by_time(dataset):
    """
    按月份先后划分训练集和测试集。

    最后的几个月只用于测试，
    避免未来月份的信息进入模型训练过程。
    """
    months = sorted(
        dataset["target_month"]
        .unique()
        .tolist()
    )

    if len(months) < 12:
        raise RuntimeError(
            "可用月份过少"
        )

    test_month_count = min(
        6,
        max(
            3,
            len(months) // 5,
        ),
    )

    test_months = set(
        months[
            -test_month_count:
        ]
    )

    train_data = dataset[
        ~dataset[
            "target_month"
        ].isin(test_months)
    ].copy()

    test_data = dataset[
        dataset[
            "target_month"
        ].isin(test_months)
    ].copy()

    return (
        train_data.reset_index(
            drop=True
        ),
        test_data.reset_index(
            drop=True
        ),
        sorted(test_months),
    )


def make_time_splits(
    train_data,
    n_splits=3,
):
    """
    建立按时间向后推进的交叉验证划分。

    每次验证使用的月份都晚于对应训练月份，
    更接近真实的未来预测过程。
    """
    months = np.asarray(
        sorted(
            train_data[
                "target_month"
            ]
            .unique()
            .tolist()
        )
    )

    splitter = TimeSeriesSplit(
        n_splits=n_splits,
    )

    splits = []

    for (
        train_month_indexes,
        valid_month_indexes,
    ) in splitter.split(months):

        train_months = set(
            months[
                train_month_indexes
            ]
        )

        valid_months = set(
            months[
                valid_month_indexes
            ]
        )

        train_indexes = np.flatnonzero(
            train_data[
                "target_month"
            ].isin(
                train_months
            )
        )

        valid_indexes = np.flatnonzero(
            train_data[
                "target_month"
            ].isin(
                valid_months
            )
        )

        if (
            len(train_indexes) > 0
            and len(valid_indexes) > 0
        ):
            splits.append(
                (
                    train_indexes,
                    valid_indexes,
                )
            )

    if len(splits) < 2:
        raise RuntimeError(
            "无法建立时间序列交叉验证"
        )

    return splits


def evaluate_default_random_forest(
    dataset,
):
    """
    在最后几个月测试默认随机森林的预测效果。
    """
    (
        train_data,
        test_data,
        test_months,
    ) = split_by_time(
        dataset
    )

    pipeline = create_pipeline(
        RandomForestRegressor(
            random_state=42,
            n_jobs=-1,
        )
    )

    pipeline.fit(
        train_data[FEATURES],
        train_data[TARGET],
    )

    predictions = pipeline.predict(
        test_data[FEATURES]
    )

    return {
        "metrics": calculate_metrics(
            test_data[TARGET],
            predictions,
        ),
        "train_records": int(
            len(train_data)
        ),
        "test_records": int(
            len(test_data)
        ),
        "test_months": (
            test_months
        ),
    }


def compare_models(dataset):
    """
    比较线性回归、决策树和随机森林的未来月份预测效果。

    独立测试集用于最终对比，
    三次时间交叉验证用于观察模型稳定性。
    """
    (
        train_data,
        test_data,
        test_months,
    ) = split_by_time(
        dataset
    )

    models = {
        "LinearRegression": (
            LinearRegression()
        ),
        "DecisionTree": (
            DecisionTreeRegressor(
                max_depth=6,
                min_samples_leaf=2,
                random_state=42,
            )
        ),
        "RandomForest": (
            RandomForestRegressor(
                random_state=42,
                n_jobs=-1,
            )
        ),
    }

    time_splits = make_time_splits(
        train_data,
        3,
    )

    rows = []

    for model_name, model in models.items():
        pipeline = create_pipeline(
            model
        )

        pipeline.fit(
            train_data[FEATURES],
            train_data[TARGET],
        )

        holdout_predictions = (
            pipeline.predict(
                test_data[FEATURES]
            )
        )

        holdout_metrics = (
            calculate_metrics(
                test_data[TARGET],
                holdout_predictions,
            )
        )

        fold_metrics = []

        for (
            train_indexes,
            valid_indexes,
        ) in time_splits:

            fold_pipeline = clone(
                pipeline
            )

            fold_pipeline.fit(
                train_data.iloc[
                    train_indexes
                ][FEATURES],
                train_data.iloc[
                    train_indexes
                ][TARGET],
            )

            fold_predictions = (
                fold_pipeline.predict(
                    train_data.iloc[
                        valid_indexes
                    ][FEATURES]
                )
            )

            fold_metrics.append(
                calculate_metrics(
                    train_data.iloc[
                        valid_indexes
                    ][TARGET],
                    fold_predictions,
                )
            )

        rows.append({
            "model": model_name,
            "holdout_mae": (
                holdout_metrics[
                    "mae"
                ]
            ),
            "holdout_rmse": (
                holdout_metrics[
                    "rmse"
                ]
            ),
            "holdout_r2": (
                holdout_metrics[
                    "r2"
                ]
            ),
            "holdout_mape": (
                holdout_metrics[
                    "mape"
                ]
            ),
            "cv_mae": float(
                np.mean([
                    item["mae"]
                    for item in fold_metrics
                ])
            ),
            "cv_rmse": float(
                np.mean([
                    item["rmse"]
                    for item in fold_metrics
                ])
            ),
            "cv_r2": float(
                np.mean([
                    item["r2"]
                    for item in fold_metrics
                ])
            ),
            "cv_mape": float(
                np.mean([
                    item["mape"]
                    for item in fold_metrics
                ])
            ),
            "test_months": ",".join(
                test_months
            ),
        })

    return pd.DataFrame(
        rows
    )


def optimize_random_forest(
    dataset,
):
    """
    使用网格搜索选择随机森林参数。

    参数选择使用时间交叉验证，
    最终指标仍在独立测试月份上计算。
    """
    (
        train_data,
        test_data,
        test_months,
    ) = split_by_time(
        dataset
    )

    pipeline = create_pipeline(
        RandomForestRegressor(
            random_state=42,
            n_jobs=1,
        )
    )

    parameter_grid = {
        "model__n_estimators": [
            100,
            200,
        ],
        "model__max_depth": [
            6,
            10,
            None,
        ],
        "model__min_samples_split": [
            2,
            5,
        ],
        "model__min_samples_leaf": [
            1,
            2,
        ],
        "model__max_features": [
            "sqrt",
        ],
    }

    time_splits = make_time_splits(
        train_data,
        3,
    )

    search = GridSearchCV(
        estimator=pipeline,
        param_grid=parameter_grid,
        scoring=(
            "neg_mean_absolute_error"
        ),
        cv=time_splits,
        n_jobs=-1,
        verbose=1,
        refit=True,
    )

    search.fit(
        train_data[FEATURES],
        train_data[TARGET],
    )

    predictions = search.predict(
        test_data[FEATURES]
    )

    optimized_metrics = (
        calculate_metrics(
            test_data[TARGET],
            predictions,
        )
    )

    prediction_result = test_data[
        [
            "region",
            "target_month",
            TARGET,
        ]
    ].copy()

    prediction_result[
        "predicted_price"
    ] = predictions

    prediction_result[
        "absolute_error"
    ] = np.abs(
        prediction_result[TARGET]
        - prediction_result[
            "predicted_price"
        ]
    )

    per_region_metrics = {}

    for (
        region,
        group,
    ) in prediction_result.groupby(
        "region"
    ):
        if len(group) >= 2:
            region_metrics = (
                calculate_metrics(
                    group[TARGET],
                    group[
                        "predicted_price"
                    ],
                )
            )

            region_metrics[
                "records"
            ] = int(
                len(group)
            )

            per_region_metrics[
                region
            ] = region_metrics

    final_pipeline = clone(
        search.best_estimator_
    )

    final_pipeline.set_params(
        model__n_jobs=-1
    )

    final_pipeline.fit(
        dataset[FEATURES],
        dataset[TARGET],
    )

    return {
        "pipeline": final_pipeline,
        "best_params": (
            search.best_params_
        ),
        "metrics": (
            optimized_metrics
        ),
        "per_region_metrics": (
            per_region_metrics
        ),
        "test_months": (
            test_months
        ),
        "prediction_result": (
            prediction_result
        ),
    }


def build_region_information(
    monthly_data,
):
    """
    保存各区域最近月份的价格信息。

    网页预测未来月份时，
    会从这些已有月份数据开始逐月向后计算。
    """
    result = {}

    for (
        region,
        group,
    ) in monthly_data.groupby(
        "region"
    ):
        group = (
            group.sort_values(
                "month"
            )
            .reset_index(
                drop=True
            )
        )

        history = []

        for row in group.itertuples():
            history.append({
                "month": str(
                    row.month
                ),
                "raw_unit_price": round(
                    float(
                        row.median_unit_price
                    ),
                    2,
                ),
                "region_unit_price": round(
                    float(
                        row.trend_price
                    ),
                    2,
                ),
                "sample_count": int(
                    row.sample_count
                ),
            })

        result[region] = {
            "last_month": str(
                group.iloc[-1][
                    "month"
                ]
            ),
            "last_region_price": float(
                group.iloc[-1][
                    "trend_price"
                ]
            ),
            "known_prices": [
                float(value)
                for value in group[
                    "trend_price"
                ].tolist()
            ],
            "history": (
                history[-12:]
            ),
            "month_count": int(
                len(group)
            ),
            "sample_threshold": int(
                group.iloc[-1][
                    "sample_threshold"
                ]
            ),
        }

    return result


def main():
    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_data = load_data(
        remove_outliers=False
    )

    cleaned_data = load_data(
        remove_outliers=True
    )

    print(
        "异常值处理前房源数：",
        len(raw_data),
    )

    print(
        "异常值处理后房源数：",
        len(cleaned_data),
    )

    raw_monthly = build_monthly_data(
        raw_data
    )

    cleaned_monthly = (
        build_monthly_data(
            cleaned_data
        )
    )

    raw_dataset, _ = (
        build_feature_data(
            raw_monthly
        )
    )

    (
        cleaned_dataset,
        base_month,
    ) = build_feature_data(
        cleaned_monthly
    )

    print(
        "异常值处理前趋势样本：",
        len(raw_dataset),
    )

    print(
        "异常值处理后趋势样本：",
        len(cleaned_dataset),
    )

    print(
        "训练异常值处理前默认随机森林"
    )

    default_before = (
        evaluate_default_random_forest(
            raw_dataset
        )
    )

    print(
        "训练异常值处理后默认随机森林"
    )

    default_after = (
        evaluate_default_random_forest(
            cleaned_dataset
        )
    )

    print(
        "进行线性回归、决策树和随机森林时间序列验证"
    )

    comparison = compare_models(
        cleaned_dataset
    )

    comparison.to_csv(
        COMPARISON_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        comparison.to_string(
            index=False
        )
    )

    print(
        "使用GridSearchCV优化随机森林"
    )

    optimized = (
        optimize_random_forest(
            cleaned_dataset
        )
    )

    optimized[
        "prediction_result"
    ].to_csv(
        PREDICTION_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    monthly_output = (
        cleaned_monthly.copy()
    )

    monthly_output["month"] = (
        monthly_output[
            "month"
        ].astype(str)
    )

    monthly_output.to_csv(
        MONTHLY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    region_information = (
        build_region_information(
            cleaned_monthly
        )
    )

    generated_at = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    bundle = {
        "city": "青岛",
        "generated_at": (
            generated_at
        ),
        "model_type": (
            "random_forest_time_series"
        ),
        "pipeline": (
            optimized["pipeline"]
        ),
        "base_month": str(
            base_month
        ),
        "features": FEATURES,
        "regions": (
            region_information
        ),
        "metrics": (
            optimized["metrics"]
        ),
        "per_region_metrics": (
            optimized[
                "per_region_metrics"
            ]
        ),
        "best_params": (
            optimized["best_params"]
        ),
        "reliability_rule": {
            "minimum_r2": 0.0,
            "maximum_mape": 5.0,
            "minimum_records": 2,
        },
    }

    joblib.dump(
        bundle,
        MODEL_PATH,
        compress=3,
    )

    metrics_result = {
        "city": "青岛",
        "generated_at": (
            generated_at
        ),
        "raw_house_records": int(
            len(raw_data)
        ),
        "clean_house_records": int(
            len(cleaned_data)
        ),
        "raw_trend_samples": int(
            len(raw_dataset)
        ),
        "clean_trend_samples": int(
            len(cleaned_dataset)
        ),
        "default_before_outlier": (
            default_before
        ),
        "default_after_outlier": (
            default_after
        ),
        "model_comparison": (
            json.loads(
                comparison.to_json(
                    orient="records",
                    force_ascii=False,
                )
            )
        ),
        "best_params": (
            optimized[
                "best_params"
            ]
        ),
        "optimized_random_forest": (
            optimized[
                "metrics"
            ]
        ),
        "per_region_metrics": (
            optimized[
                "per_region_metrics"
            ]
        ),
        "test_months": (
            optimized[
                "test_months"
            ]
        ),
    }

    with METRICS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics_result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()

    print(
        "随机森林未来趋势模型训练完成"
    )

    print(
        "模型文件：",
        MODEL_PATH,
    )

    print(
        "指标文件：",
        METRICS_PATH,
    )

    print(
        "最优参数：",
        json.dumps(
            optimized[
                "best_params"
            ],
            ensure_ascii=False,
        ),
    )

    print(
        "最终测试指标：",
        json.dumps(
            optimized[
                "metrics"
            ],
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
