"""
启动爬虫脚本
"""
import os
import sys
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWLER_DIR = os.path.join(ROOT_DIR, 'crawler')


def start_spider(city='北京', pages=5):
    """启动链家爬虫"""
    print("=" * 50)
    print("智慧房产探索平台 - 启动爬虫")
    print("=" * 50)
    print(f"\n目标城市: {city}")
    print(f"采集页数: {pages}")
    print(f"爬虫目录: {CRAWLER_DIR}")
    print("\n开始采集...")

    cmd = [
        sys.executable, '-m', 'scrapy', 'crawl', 'lianjia',
        '-a', f'city={city}',
        '-a', f'pages={pages}',
    ]

    result = subprocess.run(cmd, cwd=CRAWLER_DIR, capture_output=True, text=True)

    if result.returncode == 0:
        print("\n✓ 爬虫运行完成！")
    else:
        print(f"\n✗ 爬虫运行出错:")
        print(result.stderr)

    return result.returncode


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='启动房源爬虫')
    parser.add_argument('--city', type=str, default='北京', help='目标城市')
    parser.add_argument('--pages', type=int, default=5, help='采集页数')
    args = parser.parse_args()

    start_spider(city=args.city, pages=args.pages)
