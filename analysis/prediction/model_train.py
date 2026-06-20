import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from analysis.price_analysis import load_house_data

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
RESULT_DIR = BASE_DIR / "results"
FIGURE_DIR = RESULT_DIR / "figures"

MODEL_PATH = MODEL_DIR / "house_price_pipeline.pkl"
METRICS_PATH = RESULT_DIR / "model_metrics.json"
COMPARISON_PATH = RESULT_DIR / "model_comparison.csv"
IMPORTANCE_PATH = RESULT_DIR / "feature_importance.csv"

NUMERIC_FEATURES = ["area"]

CATEGORICAL_FEATURES = [
    "city",
    "region",
    "huxing",
    "chaoxiang",
    "zhuangxiu",
]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

TARGET = "unit_price"


def basic_clean(df):
    data = df.copy()

    required_columns = FEATURES + [TARGET]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "缺少训练字段：" + "、".join(missing_columns)
        )

    data["area"] = pd.to_numeric(
        data["area"],
        errors="coerce",
    )

    data[TARGET] = pd.to_numeric(
        data[TARGET],
        errors="coerce",
    )

    for column in CATEGORICAL_FEATURES:
        data[column] = (
            data[column]
            .fillna("未知")
            .astype(str)
            .str.strip()
            .replace("", "未知")
        )

    data = data.dropna(
        subset=[
            "area",
            TARGET,
        ]
    )

    data = data[
        (data["city"] != "未知")
        & (data["region"] != "未知")
        & (data["area"] >= 10)
        & (data["area"] <= 1000)
        & (data[TARGET] >= 500)
        & (data[TARGET] <= 200000)
    ].copy()

    data = data.drop_duplicates(
        subset=FEATURES + [TARGET]
    )

    report = {
        "records_after_basic_clean": int(len(data)),
        "city_count": int(data["city"].nunique()),
        "region_count": int(data[["city", "region"]].drop_duplicates().shape[0]),
        "area_min": float(data["area"].min()),
        "area_max": float(data["area"].max()),
        "unit_price_min": float(data[TARGET].min()),
        "unit_price_max": float(data[TARGET].max()),
    }

    return data.reset_index(drop=True), report


def remove_outliers(df):
    data = df.copy()

    for column in ["area", TARGET]:
        q1 = data.groupby("city")[column].transform(
            lambda values: values.quantile(0.25)
        )

        q3 = data.groupby("city")[column].transform(
            lambda values: values.quantile(0.75)
        )

        distance = q3 - q1

        lower = q1 - 1.5 * distance
        upper = q3 + 1.5 * distance

        if column == "area":
            lower = lower.clip(lower=10)
            upper = upper.clip(upper=1000)
        else:
            lower = lower.clip(lower=500)
            upper = upper.clip(upper=200000)

        data = data[
            (data[column] >= lower)
            & (data[column] <= upper)
        ].copy()

    return data.reset_index(drop=True)


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

    r2 = r2_score(
        actual_values,
        predicted_values,
    )

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
    }


def build_default_random_forest():
    return RandomForestRegressor(
        n_estimators=120,
        max_depth=22,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )


def evaluate_default_random_forest(df):
    train_data, test_data = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
    )

    pipeline = create_pipeline(
        build_default_random_forest()
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
        "train_records": int(len(train_data)),
        "test_records": int(len(test_data)),
    }


def compare_models(df):
    models = {
        "LinearRegression": LinearRegression(),
        "DecisionTree": DecisionTreeRegressor(
            max_depth=18,
            min_samples_leaf=3,
            random_state=42,
        ),
        "RandomForest": build_default_random_forest(),
    }

    cv = KFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    scoring = {
        "mae": "neg_mean_absolute_error",
        "mse": "neg_mean_squared_error",
        "r2": "r2",
    }

    rows = []

    for model_name, model in models.items():
        pipeline = create_pipeline(model)

        scores = cross_validate(
            pipeline,
            df[FEATURES],
            df[TARGET],
            cv=cv,
            scoring=scoring,
            n_jobs=-1,
        )

        rows.append({
            "model": model_name,
            "cv_mae": float(-scores["test_mae"].mean()),
            "cv_rmse": float(np.sqrt(-scores["test_mse"]).mean()),
            "cv_r2": float(scores["test_r2"].mean()),
            "cv_r2_std": float(scores["test_r2"].std()),
        })

    return (
        pd.DataFrame(rows)
        .sort_values("cv_r2", ascending=False)
        .reset_index(drop=True)
    )


def optimize_random_forest(df):
    train_data, test_data = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
    )

    pipeline = create_pipeline(
        RandomForestRegressor(
            random_state=42,
            n_jobs=1,
        )
    )

    parameter_grid = {
        "model__n_estimators": [80, 120],
        "model__max_depth": [16, 22],
        "model__min_samples_split": [2, 5],
        "model__min_samples_leaf": [1, 2],
        "model__max_features": ["sqrt"],
    }

    search = GridSearchCV(
        estimator=pipeline,
        param_grid=parameter_grid,
        scoring="neg_mean_absolute_error",
        cv=3,
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

    final_pipeline = clone(
        search.best_estimator_
    )

    final_pipeline.set_params(
        model__n_jobs=-1
    )

    return {
        "pipeline": final_pipeline,
        "metrics": metrics,
        "best_params": search.best_params_,
    }


def save_feature_importance(pipeline):
    processor = pipeline.named_steps["processor"]
    model = pipeline.named_steps["model"]

    feature_names = processor.get_feature_names_out()

    importance = pd.DataFrame({
        "feature": feature_names,
        "importance": model.feature_importances_,
    }).sort_values(
        "importance",
        ascending=False,
    )

    importance.to_csv(
        IMPORTANCE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    top_features = (
        importance.head(25)
        .sort_values("importance")
    )

    plt.figure(figsize=(10, 7))
    plt.barh(
        top_features["feature"],
        top_features["importance"],
    )
    plt.xlabel("Feature importance")
    plt.title("Random forest feature importance")
    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR / "feature_importance.png",
        dpi=160,
    )

    plt.close()


def save_figures(df, comparison):
    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(figsize=(9, 6))
    plt.hist(
        df[TARGET],
        bins=50,
    )
    plt.xlabel("Unit price")
    plt.ylabel("House count")
    plt.title("Shandong unit price distribution")
    plt.tight_layout()
    plt.savefig(
        FIGURE_DIR / "unit_price_distribution.png",
        dpi=160,
    )
    plt.close()

    city_price = (
        df.groupby("city")[TARGET]
        .mean()
        .sort_values(ascending=False)
        .head(20)
    )

    plt.figure(figsize=(11, 6))
    city_price.plot(kind="bar")
    plt.xlabel("City")
    plt.ylabel("Average unit price")
    plt.title("Average unit price by city")
    plt.tight_layout()
    plt.savefig(
        FIGURE_DIR / "city_average_unit_price.png",
        dpi=160,
    )
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.bar(
        comparison["model"],
        comparison["cv_r2"],
    )
    plt.ylabel("Cross validation R2")
    plt.title("Model comparison")
    plt.tight_layout()
    plt.savefig(
        FIGURE_DIR / "model_comparison.png",
        dpi=160,
    )
    plt.close()


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    print("正在读取山东省房源数据")

    raw_data = load_house_data()

    print("读取到原始房源：", len(raw_data), "条")

    basic_data, quality_report = basic_clean(raw_data)

    print("基础清洗后数据：", len(basic_data), "条")
    print("城市数量：", quality_report["city_count"])

    print("正在训练异常值处理前的默认随机森林")
    default_before = evaluate_default_random_forest(
        basic_data
    )

    cleaned_data = remove_outliers(
        basic_data
    )

    print("异常值处理后数据：", len(cleaned_data), "条")

    print("正在训练异常值处理后的默认随机森林")
    default_after = evaluate_default_random_forest(
        cleaned_data
    )

    print("正在进行线性回归、决策树和随机森林的五折交叉验证")
    comparison = compare_models(
        cleaned_data
    )

    comparison.to_csv(
        COMPARISON_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(comparison.to_string(index=False))

    print("正在使用GridSearchCV优化随机森林")
    optimized = optimize_random_forest(
        cleaned_data
    )

    if optimized["metrics"]["mae"] < default_after["metrics"]["mae"]:
        final_model_name = "OptimizedRandomForest"
        final_pipeline = optimized["pipeline"]
        final_metrics = optimized["metrics"]
        best_params = optimized["best_params"]
    else:
        final_model_name = "DefaultRandomForestAfterCleaning"
        final_pipeline = create_pipeline(
            build_default_random_forest()
        )
        final_metrics = default_after["metrics"]
        best_params = None

    final_pipeline.fit(
        cleaned_data[FEATURES],
        cleaned_data[TARGET],
    )

    joblib.dump(
        final_pipeline,
        MODEL_PATH,
        compress=3,
    )

    save_figures(
        cleaned_data,
        comparison,
    )

    save_feature_importance(
        final_pipeline,
    )

    metrics_result = {
        "scope": "山东省",
        "data_quality": {
            **quality_report,
            "records_after_outlier_clean": int(len(cleaned_data)),
        },
        "default_random_forest_before_price_cleaning": default_before["metrics"],
        "default_random_forest_after_price_cleaning": default_after["metrics"],
        "model_comparison": json.loads(
            comparison.to_json(
                orient="records",
                force_ascii=False,
            )
        ),
        "best_params": best_params,
        "optimized_random_forest": optimized["metrics"],
        "final_model": {
            "name": final_model_name,
            "metrics": final_metrics,
        },
    }

    with METRICS_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            metrics_result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("山东省当前房价估值模型训练完成")
    print("最终模型：", final_model_name)
    print("模型文件：", MODEL_PATH)
    print("指标文件：", METRICS_PATH)


if __name__ == "__main__":
    main()
