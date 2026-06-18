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
PREDICTION_PATH = RESULT_DIR / "prediction_results.csv"
IMPORTANCE_PATH = RESULT_DIR / "feature_importance.csv"

NUMERIC_FEATURES = ["area"]

CATEGORICAL_FEATURES = [
    "region",
    "huxing",
    "chaoxiang",
    "zhuangxiu",
]

FEATURES = (
    NUMERIC_FEATURES
    + CATEGORICAL_FEATURES
)

TARGET = "unit_price"


def basic_clean(df):
    """
    整理当前房价估值需要使用的字段，并删除无法用于训练的记录。

    面积和单价会转换为数值。类别字段缺失时统一写为未知，
    这样模型仍然可以处理字段不完整的房源。
    """
    data = df.copy()

    required_columns = FEATURES + [TARGET]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "缺少训练字段："
            + "、".join(missing_columns)
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
        (data["area"] >= 10)
        & (data["area"] <= 1000)
        & (data[TARGET] >= 500)
        & (data[TARGET] <= 200000)
    ].copy()

    data = data.drop_duplicates(
        subset=FEATURES + [TARGET]
    )

    report = {
        "records_after_basic_clean": int(
            len(data)
        ),
        "area_min": float(
            data["area"].min()
        ),
        "area_max": float(
            data["area"].max()
        ),
        "unit_price_min": float(
            data[TARGET].min()
        ),
        "unit_price_max": float(
            data[TARGET].max()
        ),
    }

    return (
        data.reset_index(drop=True),
        report,
    )


def remove_outliers(df):
    """
    使用四分位距过滤面积和单价中的明显异常值。

    处理后的数据主要用于第二次建模和最终模型训练，
    原始清洗数据仍然保留，用于比较异常值处理前后的效果。
    """
    data = df.copy()

    for column in [
        "area",
        TARGET,
    ]:
        first_quartile = (
            data[column].quantile(0.25)
        )

        third_quartile = (
            data[column].quantile(0.75)
        )

        quartile_distance = (
            third_quartile
            - first_quartile
        )

        lower_limit = (
            first_quartile
            - 1.5 * quartile_distance
        )

        upper_limit = (
            third_quartile
            + 1.5 * quartile_distance
        )

        data = data[
            (data[column] >= lower_limit)
            & (data[column] <= upper_limit)
        ].copy()

    return data.reset_index(drop=True)


def create_pipeline(model):
    """
    建立统一的数据处理和模型训练流程。

    面积缺失时使用中位数补充并进行标准化。
    区域、户型、朝向和装修使用独热编码转换为数值。
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
    计算回归模型常用的三项评价指标。
    """
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


def evaluate_default_random_forest(df):
    """
    使用固定的数据划分评估默认随机森林。

    相同的数据划分能够保证异常值处理前后的指标可以直接比较。
    """
    train_data, test_data = (
        train_test_split(
            df,
            test_size=0.2,
            random_state=42,
        )
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
    }


def compare_models(df):
    """
    使用五折交叉验证比较线性回归、决策树和随机森林。

    每一份数据都会轮流作为验证数据，最终使用五次结果的平均值，
    减少单次划分带来的偶然影响。
    """
    models = {
        "LinearRegression": (
            LinearRegression()
        ),
        "DecisionTree": (
            DecisionTreeRegressor(
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

    cross_validation = KFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    scoring = {
        "mae": (
            "neg_mean_absolute_error"
        ),
        "mse": (
            "neg_mean_squared_error"
        ),
        "r2": "r2",
    }

    rows = []

    for model_name, model in models.items():
        pipeline = create_pipeline(
            model
        )

        scores = cross_validate(
            pipeline,
            df[FEATURES],
            df[TARGET],
            cv=cross_validation,
            scoring=scoring,
            n_jobs=-1,
        )

        rows.append({
            "model": model_name,
            "cv_mae": float(
                -scores[
                    "test_mae"
                ].mean()
            ),
            "cv_rmse": float(
                np.sqrt(
                    -scores["test_mse"]
                ).mean()
            ),
            "cv_r2": float(
                scores[
                    "test_r2"
                ].mean()
            ),
            "cv_r2_std": float(
                scores[
                    "test_r2"
                ].std()
            ),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(
            "cv_r2",
            ascending=False,
        )
    )


def optimize_random_forest(df):
    """
    使用网格搜索寻找随机森林的较优参数。

    测试集只用于最终评价，不参与参数选择。
    """
    train_data, test_data = (
        train_test_split(
            df,
            test_size=0.2,
            random_state=42,
        )
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
            None,
            15,
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

    search = GridSearchCV(
        estimator=pipeline,
        param_grid=parameter_grid,
        scoring=(
            "neg_mean_absolute_error"
        ),
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

    prediction_result = test_data[
        FEATURES + [TARGET]
    ].copy()

    prediction_result[
        "predicted_unit_price"
    ] = predictions

    prediction_result[
        "absolute_error"
    ] = np.abs(
        prediction_result[TARGET]
        - prediction_result[
            "predicted_unit_price"
        ]
    )

    return {
        "search": search,
        "metrics": metrics,
        "prediction_result": (
            prediction_result
        ),
    }


def save_feature_importance(pipeline):
    """
    保存最终随机森林最重要的特征，
    便于报告展示和结果解释。
    """
    processor = pipeline.named_steps[
        "processor"
    ]

    model = pipeline.named_steps[
        "model"
    ]

    feature_names = (
        processor.get_feature_names_out()
    )

    importance = pd.DataFrame({
        "feature": feature_names,
        "importance": (
            model.feature_importances_
        ),
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
        importance.head(20)
        .sort_values("importance")
    )

    plt.figure(
        figsize=(10, 7)
    )

    plt.barh(
        top_features["feature"],
        top_features["importance"],
    )

    plt.xlabel(
        "Feature importance"
    )

    plt.title(
        "Random forest feature importance"
    )

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR
        / "feature_importance.png",
        dpi=160,
    )

    plt.close()


def save_figures(
    df,
    comparison,
    prediction_result,
):
    """
    生成课程报告中常用的房价分析和模型效果图片。
    """
    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(
        figsize=(9, 6)
    )

    plt.hist(
        df[TARGET],
        bins=40,
    )

    plt.xlabel("Unit price")
    plt.ylabel("House count")

    plt.title(
        "Qingdao unit price distribution"
    )

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR
        / "unit_price_distribution.png",
        dpi=160,
    )

    plt.close()

    region_price = (
        df.groupby("region")[TARGET]
        .mean()
        .sort_values(
            ascending=False
        )
    )

    plt.figure(
        figsize=(10, 6)
    )

    region_price.plot(
        kind="bar"
    )

    plt.xlabel("Region")

    plt.ylabel(
        "Average unit price"
    )

    plt.title(
        "Average unit price by region"
    )

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR
        / "region_average_unit_price.png",
        dpi=160,
    )

    plt.close()

    plt.figure(
        figsize=(8, 5)
    )

    plt.bar(
        comparison["model"],
        comparison["cv_r2"],
    )

    plt.ylabel(
        "Cross validation R2"
    )

    plt.title(
        "Model comparison"
    )

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR
        / "model_comparison.png",
        dpi=160,
    )

    plt.close()

    plt.figure(
        figsize=(7, 7)
    )

    plt.scatter(
        prediction_result[TARGET],
        prediction_result[
            "predicted_unit_price"
        ],
        alpha=0.35,
    )

    minimum = min(
        prediction_result[
            TARGET
        ].min(),
        prediction_result[
            "predicted_unit_price"
        ].min(),
    )

    maximum = max(
        prediction_result[
            TARGET
        ].max(),
        prediction_result[
            "predicted_unit_price"
        ].max(),
    )

    plt.plot(
        [
            minimum,
            maximum,
        ],
        [
            minimum,
            maximum,
        ],
        linestyle="--",
    )

    plt.xlabel(
        "Actual unit price"
    )

    plt.ylabel(
        "Predicted unit price"
    )

    plt.title(
        "Actual and predicted unit price"
    )

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR
        / "actual_vs_predicted.png",
        dpi=160,
    )

    plt.close()


def main():
    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "正在读取青岛市房源数据"
    )

    raw_data = load_house_data(
        city="青岛"
    )

    print(
        "读取到青岛市原始房源：",
        len(raw_data),
        "条",
    )

    basic_data, quality_report = (
        basic_clean(raw_data)
    )

    print(
        "基础清洗后数据：",
        len(basic_data),
        "条",
    )

    print(
        "正在训练异常值处理前的默认随机森林"
    )

    default_before = (
        evaluate_default_random_forest(
            basic_data
        )
    )

    cleaned_data = remove_outliers(
        basic_data
    )

    print(
        "异常值处理后数据：",
        len(cleaned_data),
        "条",
    )

    print(
        "正在训练异常值处理后的默认随机森林"
    )

    default_after = (
        evaluate_default_random_forest(
            cleaned_data
        )
    )

    print(
        "正在进行三种模型的五折交叉验证"
    )

    comparison = compare_models(
        cleaned_data
    )

    comparison.to_csv(
        COMPARISON_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "正在使用网格搜索优化随机森林"
    )

    optimized = optimize_random_forest(
        cleaned_data
    )

    optimized[
        "prediction_result"
    ].to_csv(
        PREDICTION_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # 网格搜索不一定在独立测试集上优于默认参数。
    # 最终保存测试集平均绝对误差更小的随机森林。
    if (
        optimized["metrics"]["mae"]
        < default_after[
            "metrics"
        ]["mae"]
    ):
        final_model_name = (
            "OptimizedRandomForest"
        )

        final_pipeline = clone(
            optimized[
                "search"
            ].best_estimator_
        )

        final_metrics = optimized[
            "metrics"
        ]
    else:
        final_model_name = (
            "DefaultRandomForestAfterCleaning"
        )

        final_pipeline = (
            create_pipeline(
                RandomForestRegressor(
                    random_state=42,
                    n_jobs=-1,
                )
            )
        )

        final_metrics = (
            default_after["metrics"]
        )

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
        optimized[
            "prediction_result"
        ],
    )

    save_feature_importance(
        final_pipeline
    )

    metrics_result = {
        "data_quality": {
            **quality_report,
            "records_after_outlier_clean": int(
                len(cleaned_data)
            ),
        },
        "default_random_forest_before_price_cleaning": (
            default_before[
                "metrics"
            ]
        ),
        "default_random_forest_after_price_cleaning": (
            default_after[
                "metrics"
            ]
        ),
        "model_comparison": json.loads(
            comparison.to_json(
                orient="records",
                force_ascii=False,
            )
        ),
        "best_params": (
            optimized[
                "search"
            ].best_params_
        ),
        "optimized_random_forest": (
            optimized["metrics"]
        ),
        "final_model": {
            "name": final_model_name,
            "metrics": final_metrics,
        },
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
        "当前房价估值模型训练完成"
    )

    print(
        "最终模型：",
        final_model_name,
    )

    print(
        "模型文件：",
        MODEL_PATH,
    )

    print(
        "指标文件：",
        METRICS_PATH,
    )


if __name__ == "__main__":
    main()
