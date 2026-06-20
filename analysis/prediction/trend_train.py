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
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from analysis.price_analysis import load_house_data

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
RESULT_DIR = BASE_DIR / "results"

MODEL_PATH = MODEL_DIR / "future_random_forest.pkl"
METRICS_PATH = RESULT_DIR / "future_rf_metrics.json"
COMPARISON_PATH = RESULT_DIR / "future_rf_model_comparison.csv"
MONTHLY_PATH = RESULT_DIR / "future_monthly_region_prices.csv"

CATEGORICAL_FEATURES = [
    "level",
    "city",
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

FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET = "target_price"


def make_scope_key(level, city, region):
    return f"{level}::{city}::{region}"


def load_data(remove_outliers):
    data = load_house_data()[
        [
            "city",
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

    for column in ["city", "region"]:
        data[column] = (
            data[column]
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
        (data["city"] != "")
        & (data["region"] != "")
        & (data["unit_price"] >= 500)
        & (data["unit_price"] <= 200000)
    ].copy()

    if remove_outliers:
        group_columns = [
            "city",
            "region",
        ]

        q1 = data.groupby(group_columns)["unit_price"].transform(
            lambda values: values.quantile(0.25)
        )

        q3 = data.groupby(group_columns)["unit_price"].transform(
            lambda values: values.quantile(0.75)
        )

        distance = q3 - q1

        lower = (
            q1
            - 1.5 * distance
        ).clip(lower=500)

        upper = (
            q3
            + 1.5 * distance
        ).clip(upper=200000)

        data = data[
            (data["unit_price"] >= lower)
            & (data["unit_price"] <= upper)
        ].copy()

    return data.reset_index(drop=True)


def build_one_monthly(data, level, city, region):
    if level == "province":
        subset = data.copy()
        label = "山东省整体"
    elif level == "city":
        subset = data[
            data["city"] == city
        ].copy()
        label = f"{city}整体"
    else:
        subset = data[
            (data["city"] == city)
            & (data["region"] == region)
        ].copy()
        label = f"{city}-{region}"

    if subset.empty:
        return None

    subset["month"] = subset["date"].dt.to_period("M")

    monthly = (
        subset.groupby("month")
        .agg(
            median_unit_price=("unit_price", "median"),
            sample_count=("unit_price", "size"),
        )
        .sort_index()
    )

    selected = None
    threshold_used = None

    for threshold in [40, 30, 20, 10, 5, 1]:
        candidate = monthly[
            monthly["sample_count"] >= threshold
        ].copy()

        if len(candidate) >= 12:
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

    selected = selected.reindex(full_months)

    selected["median_unit_price"] = (
        selected["median_unit_price"]
        .interpolate()
        .ffill()
        .bfill()
    )

    selected["sample_count"] = (
        selected["sample_count"]
        .fillna(0)
        .astype(int)
    )

    selected["trend_price"] = (
        selected["median_unit_price"]
        .ewm(
            span=3,
            adjust=False,
        )
        .mean()
    )

    selected.index.name = "month"
    selected = selected.reset_index()

    selected["level"] = level
    selected["city"] = city
    selected["region"] = region
    selected["scope_key"] = make_scope_key(
        level,
        city,
        region,
    )
    selected["scope_name"] = label
    selected["sample_threshold"] = threshold_used

    return selected


def build_monthly_data(data):
    frames = []

    province_monthly = build_one_monthly(
        data,
        "province",
        "__ALL__",
        "__ALL__",
    )

    if province_monthly is not None:
        frames.append(province_monthly)

    cities = sorted(
        data["city"]
        .dropna()
        .unique()
        .tolist()
    )

    for city in cities:
        city_monthly = build_one_monthly(
            data,
            "city",
            city,
            "__ALL__",
        )

        if city_monthly is not None:
            frames.append(city_monthly)

        regions = sorted(
            data.loc[
                data["city"] == city,
                "region",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        for region in regions:
            region_monthly = build_one_monthly(
                data,
                "region",
                city,
                region,
            )

            if region_monthly is not None:
                frames.append(region_monthly)

    if not frames:
        raise RuntimeError("没有足够的月度趋势数据")

    return pd.concat(
        frames,
        ignore_index=True,
    )


def months_between(first_month, current_month):
    return (
        (current_month.year - first_month.year)
        * 12
        + current_month.month
        - first_month.month
    )


def build_feature_data(monthly_data):
    base_month = monthly_data["month"].min()

    rows = []

    for scope_key, group in monthly_data.groupby("scope_key"):
        group = (
            group.sort_values("month")
            .reset_index(drop=True)
        )

        known_prices = group["trend_price"].to_numpy(dtype=float)
        months = group["month"].tolist()

        for index in range(6, len(group)):
            previous_prices = known_prices[:index]
            target_month = months[index]
            month_number = target_month.month

            price_1 = float(previous_prices[-1])
            price_2 = float(previous_prices[-2])
            price_3 = float(previous_prices[-3])
            price_4 = float(previous_prices[-4])
            price_5 = float(previous_prices[-5])
            price_6 = float(previous_prices[-6])

            rows.append({
                "scope_key": scope_key,
                "scope_name": group.iloc[index]["scope_name"],
                "level": group.iloc[index]["level"],
                "city": group.iloc[index]["city"],
                "region": group.iloc[index]["region"],
                "month_index": float(months_between(base_month, target_month)),
                "month_sin": float(np.sin(2 * np.pi * month_number / 12)),
                "month_cos": float(np.cos(2 * np.pi * month_number / 12)),
                "price_1_month_ago": price_1,
                "price_2_months_ago": price_2,
                "price_3_months_ago": price_3,
                "price_4_months_ago": price_4,
                "price_5_months_ago": price_5,
                "price_6_months_ago": price_6,
                "average_price_last_3_months": float(np.mean(previous_prices[-3:])),
                "average_price_last_6_months": float(np.mean(previous_prices[-6:])),
                "price_std_last_3_months": float(np.std(previous_prices[-3:])),
                "change_from_previous_month": price_1 - price_2,
                "change_from_3_months_ago": price_1 - price_4,
                TARGET: float(known_prices[index]),
                "target_month": str(target_month),
            })

    if not rows:
        raise RuntimeError("无法构造未来趋势训练数据")

    return (
        pd.DataFrame(rows)
        .sort_values(["target_month", "scope_key"])
        .reset_index(drop=True),
        base_month,
    )


def create_pipeline(model):
    numeric_processor = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="median"),
        ),
        (
            "scaler",
            StandardScaler(),
        ),
    ])

    categorical_processor = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="most_frequent"),
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


def calculate_metrics(actual_values, predicted_values):
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
        r2_score(actual_values, predicted_values)
        if len(actual_values) >= 2
        else None
    )

    valid = actual_values != 0

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
        "r2": float(r2) if r2 is not None else None,
        "mape": float(mape) if mape is not None else None,
    }


def split_by_time(dataset):
    months = sorted(
        dataset["target_month"]
        .unique()
        .tolist()
    )

    if len(months) < 12:
        raise RuntimeError("可用月份过少")

    test_month_count = min(
        6,
        max(3, len(months) // 5),
    )

    test_months = set(months[-test_month_count:])

    train_data = dataset[
        ~dataset["target_month"].isin(test_months)
    ].copy()

    test_data = dataset[
        dataset["target_month"].isin(test_months)
    ].copy()

    return (
        train_data.reset_index(drop=True),
        test_data.reset_index(drop=True),
        sorted(test_months),
    )


def make_time_splits(train_data, n_splits=3):
    months = np.asarray(
        sorted(
            train_data["target_month"]
            .unique()
            .tolist()
        )
    )

    splitter = TimeSeriesSplit(
        n_splits=n_splits,
    )

    splits = []

    for train_month_indexes, valid_month_indexes in splitter.split(months):
        train_months = set(months[train_month_indexes])
        valid_months = set(months[valid_month_indexes])

        train_indexes = np.flatnonzero(
            train_data["target_month"].isin(train_months)
        )

        valid_indexes = np.flatnonzero(
            train_data["target_month"].isin(valid_months)
        )

        if len(train_indexes) > 0 and len(valid_indexes) > 0:
            splits.append(
                (
                    train_indexes,
                    valid_indexes,
                )
            )

    if len(splits) < 2:
        raise RuntimeError("无法建立时间交叉验证")

    return splits


def optimize_random_forest(dataset):
    train_data, test_data, test_months = split_by_time(dataset)

    pipeline = create_pipeline(
        RandomForestRegressor(
            random_state=42,
            n_jobs=1,
        )
    )

    parameter_grid = {
        "model__n_estimators": [100, 160],
        "model__max_depth": [8, 12, None],
        "model__min_samples_split": [2, 5],
        "model__min_samples_leaf": [1, 2],
        "model__max_features": ["sqrt"],
    }

    time_splits = make_time_splits(
        train_data,
        3,
    )

    search = GridSearchCV(
        estimator=pipeline,
        param_grid=parameter_grid,
        scoring="neg_mean_absolute_error",
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

    metrics = calculate_metrics(
        test_data[TARGET],
        predictions,
    )

    prediction_result = test_data[
        [
            "scope_key",
            "scope_name",
            "level",
            "city",
            "region",
            "target_month",
            TARGET,
        ]
    ].copy()

    prediction_result["predicted_price"] = predictions
    prediction_result["absolute_error"] = np.abs(
        prediction_result[TARGET]
        - prediction_result["predicted_price"]
    )

    per_scope_metrics = {}

    for scope_key, group in prediction_result.groupby("scope_key"):
        if len(group) >= 2:
            scope_metrics = calculate_metrics(
                group[TARGET],
                group["predicted_price"],
            )

            scope_metrics["records"] = int(len(group))
            scope_metrics["scope_name"] = str(group.iloc[0]["scope_name"])
            scope_metrics["level"] = str(group.iloc[0]["level"])
            scope_metrics["city"] = str(group.iloc[0]["city"])
            scope_metrics["region"] = str(group.iloc[0]["region"])

            per_scope_metrics[scope_key] = scope_metrics

    final_pipeline = clone(search.best_estimator_)
    final_pipeline.set_params(model__n_jobs=-1)

    final_pipeline.fit(
        dataset[FEATURES],
        dataset[TARGET],
    )

    comparison = pd.DataFrame([
        {
            "model": "RandomForest",
            "holdout_mae": metrics["mae"],
            "holdout_rmse": metrics["rmse"],
            "holdout_r2": metrics["r2"],
            "holdout_mape": metrics["mape"],
            "test_months": ",".join(test_months),
        }
    ])

    return {
        "pipeline": final_pipeline,
        "best_params": search.best_params_,
        "metrics": metrics,
        "per_scope_metrics": per_scope_metrics,
        "test_months": test_months,
        "comparison": comparison,
    }


def build_scope_information(monthly_data):
    result = {}

    for scope_key, group in monthly_data.groupby("scope_key"):
        group = (
            group.sort_values("month")
            .reset_index(drop=True)
        )

        history = []

        for row in group.itertuples():
            history.append({
                "month": str(row.month),
                "raw_unit_price": round(float(row.median_unit_price), 2),
                "region_unit_price": round(float(row.trend_price), 2),
                "sample_count": int(row.sample_count),
            })

        result[scope_key] = {
            "level": str(group.iloc[-1]["level"]),
            "city": str(group.iloc[-1]["city"]),
            "region": str(group.iloc[-1]["region"]),
            "scope_name": str(group.iloc[-1]["scope_name"]),
            "last_month": str(group.iloc[-1]["month"]),
            "last_price": float(group.iloc[-1]["trend_price"]),
            "known_prices": [
                float(value)
                for value in group["trend_price"].tolist()
            ],
            "history": history[-12:],
            "month_count": int(len(group)),
            "sample_threshold": int(group.iloc[-1]["sample_threshold"]),
        }

    return result


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    raw_data = load_data(remove_outliers=False)
    cleaned_data = load_data(remove_outliers=True)

    print("异常值处理前房源数：", len(raw_data))
    print("异常值处理后房源数：", len(cleaned_data))

    monthly_data = build_monthly_data(cleaned_data)

    dataset, base_month = build_feature_data(monthly_data)

    print("可用趋势层级数量：", monthly_data["scope_key"].nunique())
    print("趋势训练样本数：", len(dataset))

    optimized = optimize_random_forest(dataset)

    comparison = optimized["comparison"]

    comparison.to_csv(
        COMPARISON_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    monthly_output = monthly_data.copy()
    monthly_output["month"] = monthly_output["month"].astype(str)

    monthly_output.to_csv(
        MONTHLY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    scope_information = build_scope_information(monthly_data)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    bundle = {
        "province": "山东省",
        "city": "ALL",
        "generated_at": generated_at,
        "model_type": "random_forest_province_city_region_time_series",
        "pipeline": optimized["pipeline"],
        "base_month": str(base_month),
        "features": FEATURES,
        "scopes": scope_information,
        "metrics": optimized["metrics"],
        "per_scope_metrics": optimized["per_scope_metrics"],
        "best_params": optimized["best_params"],
        "reliability_rule": {
            "minimum_r2": 0.0,
            "maximum_mape": 6.0,
            "minimum_records": 2,
        },
    }

    joblib.dump(
        bundle,
        MODEL_PATH,
        compress=3,
    )

    metrics_result = {
        "province": "山东省",
        "generated_at": generated_at,
        "clean_house_records": int(len(cleaned_data)),
        "trend_samples": int(len(dataset)),
        "scope_count": int(monthly_data["scope_key"].nunique()),
        "best_params": optimized["best_params"],
        "optimized_random_forest": optimized["metrics"],
        "per_scope_metrics": optimized["per_scope_metrics"],
        "test_months": optimized["test_months"],
    }

    with METRICS_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            metrics_result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("山东省-城市-区县三级未来趋势模型训练完成")
    print("模型文件：", MODEL_PATH)
    print("指标文件：", METRICS_PATH)
    print("最终测试指标：", json.dumps(optimized["metrics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
