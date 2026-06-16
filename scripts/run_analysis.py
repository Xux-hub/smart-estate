import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


def run_analysis():
    print('=' * 60)
    print('智慧房源探索平台 - 数据分析与模型训练')
    print('=' * 60)

    from analysis.price_analysis import basic_statistics, district_analysis, layout_analysis, load_house_data

    df = load_house_data()
    if df.empty:
        print('暂无数据，请先导入 house_info 表或运行采集脚本。')
        return

    print(f'数据总量: {len(df)} 条')
    stats = basic_statistics(df)
    print('\n基本统计:')
    print(f"  平均总价: {stats['avg_total_price']:.2f} 万")
    print(f"  平均单价: {stats['avg_unit_price']:.2f} 元/㎡")
    print(f"  平均面积: {stats['avg_area']:.2f} ㎡")

    print('\n区域分析 Top 5:')
    print(district_analysis(df).head(5).to_string())

    print('\n户型分析 Top 5:')
    print(layout_analysis(df).head(5).to_string())

    if len(df) >= 50:
        from analysis.prediction.model_train import main as train_main

        train_main()
    else:
        print(f'数据量不足: 当前 {len(df)} 条，至少需要 50 条数据训练模型。')


if __name__ == '__main__':
    run_analysis()
