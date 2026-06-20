import argparse
import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "models" / "house_price_pipeline.pkl"
METRICS_PATH = BASE_DIR / "results" / "model_metrics.json"


@lru_cache(maxsize=1)
def load_pipeline():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "未找到当前房价估值模型：" + str(MODEL_PATH)
        )

    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def load_metrics():
    if not METRICS_PATH.exists():
        return {}

    with METRICS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(value):
    text = str(value or "").strip()
    return text if text else "未知"


def predict_unit_price(
    area,
    region,
    huxing="",
    chaoxiang="",
    zhuangxiu="",
    city="青岛",
    province="山东省",
    model_name="RandomForest",
):
    area_value = float(area)

    if area_value <= 0:
        raise ValueError("建筑面积必须大于0")

    input_data = pd.DataFrame([
        {
            "city": normalize_text(city),
            "region": normalize_text(region),
            "area": area_value,
            "huxing": normalize_text(huxing),
            "chaoxiang": normalize_text(chaoxiang),
            "zhuangxiu": normalize_text(zhuangxiu),
        }
    ])

    pipeline = load_pipeline()

    predicted_unit_price = float(
        pipeline.predict(input_data)[0]
    )

    return max(predicted_unit_price, 0.0)


def get_final_metrics():
    metrics = load_metrics()

    final_model = metrics.get(
        "final_model",
        {},
    )

    final_metrics = final_model.get(
        "metrics",
        {},
    )

    if final_metrics:
        return final_metrics

    cleaned_default = metrics.get(
        "default_random_forest_after_price_cleaning",
        {},
    )

    if cleaned_default:
        return cleaned_default

    return metrics.get(
        "optimized_random_forest",
        {},
    )


def predict_detail(
    area,
    region,
    huxing="",
    chaoxiang="",
    zhuangxiu="",
    city="青岛",
    province="山东省",
):
    area_value = float(area)

    unit_price = predict_unit_price(
        area=area_value,
        region=region,
        huxing=huxing,
        chaoxiang=chaoxiang,
        zhuangxiu=zhuangxiu,
        city=city,
        province=province,
    )

    total_price = (
        unit_price
        * area_value
        / 10000
    )

    metrics = get_final_metrics()

    model_name = (
        load_metrics()
        .get("final_model", {})
        .get("name", "RandomForest")
    )

    return {
        "predicted_unit_price": round(unit_price, 2),
        "predicted_total_price": round(total_price, 2),
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "r2": metrics.get("r2"),
        "model_name": model_name,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--city", default="青岛")
    parser.add_argument("--region", required=True)
    parser.add_argument("--area", type=float, required=True)
    parser.add_argument("--huxing", default="")
    parser.add_argument("--chaoxiang", default="")
    parser.add_argument("--zhuangxiu", default="")

    args = parser.parse_args()

    result = predict_detail(
        city=args.city,
        region=args.region,
        area=args.area,
        huxing=args.huxing,
        chaoxiang=args.chaoxiang,
        zhuangxiu=args.zhuangxiu,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
