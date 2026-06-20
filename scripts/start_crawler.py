"""Command line entry for the Requests + XPath house crawler."""
import argparse
import os
import sys

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWLER_DIR = os.path.join(ROOT_DIR, 'crawler')
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, CRAWLER_DIR)


def start_spider(city='', line='', pages=1, base_url='http://node4:8000', detail=True):
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'estate_spider.settings')
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(
        'house_source',
        city=city,
        line=line,
        pages=str(pages),
        base_url=base_url,
        detail='1' if detail else '0',
    )
    process.start()
    return 0


def main():
    parser = argparse.ArgumentParser(description='Crawl house records into house_info.')
    parser.add_argument('--city', default='', help='City name on the index page, e.g. 济南. Empty means all cities.')
    parser.add_argument('--line', default='', help='Region line path, e.g. /heze/chengwuxian. Overrides --city.')
    parser.add_argument('--pages', default='1', help="Pages to crawl per region, or 'all'.")
    parser.add_argument('--all-pages', action='store_true', help='Crawl every detected page for each region.')
    parser.add_argument('--base-url', default='http://node4:8000', help='Site base URL.')
    parser.add_argument('--no-detail', action='store_true', help='Only parse list pages, skip detail pages.')
    args = parser.parse_args()
    return start_spider(
        city=args.city,
        line=args.line,
        pages='all' if args.all_pages else args.pages,
        base_url=args.base_url,
        detail=not args.no_detail,
    )


if __name__ == '__main__':
    raise SystemExit(main())
