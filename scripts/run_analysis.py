"""
运行数据分析和模型训练脚本
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


def run_analysis():
    """运行完整的分析流程"""
    print("=" * 60)
    print("智慧房产探索平台 - 数据分析与模型训练")
    print("=" * 60)

    # Step 1: 数据分析
    print("\n" + "=" * 40)
    print("Step 1: 数据探索性分析")
    print("=" * 40)

    from analysis.price_analysis import (
        load_house_data, basic_statistics, district_analysis,
        layout_analysis, price_factors_correlation
    )

    df = load_house_data()

    if df.empty:
        print("暂无数据，请先运行爬虫采集数据。")
        print("运行命令: python scripts/start_crawler.py --city 北京 --pages 5")
        return

    print(f"\n数据总量: {len(df)} 条")

    stats = basic_statistics(df)
    print("\n基本统计:")
    print(f"  平均总价: {stats['avg_total_price']:.2f} 万")
    print(f"  平均单价: {stats['avg_unit_price']:.2f} 元/㎡")
    print(f"  平均面积: {stats['avg_area']:.2f} ㎡")

    print("\n区域分析 (Top 5):")
    district_stats = district_analysis(df)
    print(district_stats.head(5).to_string())

    print("\n户型分析 (Top 5):")
    layout_stats = layout_analysis(df)
    print(layout_stats.head(5).to_string())

    # Step 2: 模型训练
    print("\n" + "=" * 40)
    print("Step 2: 房价预测模型训练")
    print("=" * 40)

    if len(df) >= 50:
        from analysis.prediction.model_train import main as train_main
        train_main()
    else:
        print(f"数据量不足 ({len(df)} 条)，需要至少 50 条数据才能训练模型。")
        print("请采集更多数据后再运行。")

    # Step 3: 运行预测
    print("\n" + "=" * 40)
    print("Step 3: 运行房价预测")
    print("=" * 40)

    model_path = os.path.join(ROOT_DIR, 'analysis', 'prediction', 'models', 'RandomForest_model.pkl')
    if os.path.exists(model_path):
        from analysis.prediction.model_predict import run_prediction
        run_prediction()
    else:
        print("模型文件不存在，跳过预测步骤。")

    print("\n" + "=" * 60)
    print("分析完成！启动 Web 服务查看可视化结果:")
    print("  python manage.py runserver")
    print("=" * 60)


if __name__ == '__main__':
    run_analysis()
