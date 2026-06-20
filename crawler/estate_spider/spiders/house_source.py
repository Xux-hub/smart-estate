"""
Requests + XPath crawler for the local house pages.

The spider keeps Scrapy as the command and pipeline runner. Page fetching is
done with requests, parsing is done with lxml XPath, and field cleanup is done
with regular expressions before the item enters the pipeline.
"""
import re
from time import sleep
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
import scrapy
from lxml import html

from estate_spider.items import HouseItem


class HouseSourceSpider(scrapy.Spider):
    name = 'house_source'
    allowed_domains = []

    DEFAULT_BASE_URL = 'http://node4:8000'
    CITY_CODE_NAMES = {
        'heze': '菏泽',
        'jinan': '济南',
        'jining': '济宁',
        'linyi': '临沂',
        'qingdao': '青岛',
        'taian': '泰安',
        'weihai': '威海',
        'weifang': '潍坊',
        'yantai': '烟台',
        'zibo': '淄博',
    }

    def __init__(
        self,
        city='',
        line='',
        pages=1,
        base_url=DEFAULT_BASE_URL,
        detail='1',
        delay='0.3',
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.city = _clean_text(city)
        self.line = _clean_text(line)
        self.pages = None if str(pages).lower() == 'all' else max(1, int(pages))
        self.base_url = base_url.rstrip('/')
        self.fetch_detail = str(detail).lower() not in {'0', 'false', 'no'}
        self.delay = max(0, float(delay))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/126.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def start_requests(self):
        bootstrap_url = self._list_url(self.line, 1) if self.line else self.base_url + '/'
        yield scrapy.Request(bootstrap_url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        region_entries = self._region_entries()
        if not region_entries:
            self.logger.warning('No region entries found. city=%s line=%s', self.city, self.line)
            return

        for entry in region_entries:
            first_url = _set_query(entry['url'], page=1)
            first_doc = self._get_doc(first_url)
            if first_doc is None:
                continue

            total_pages = _detect_total_pages(first_doc)
            page_count = total_pages if self.pages is None else min(self.pages, total_pages)

            self.logger.info(
                'Region %s/%s will crawl %s page(s), detected total=%s',
                entry.get('city', ''),
                entry.get('district', '') or entry.get('line', ''),
                page_count,
                total_pages,
            )

            for page in range(1, page_count + 1):
                list_url = _set_query(entry['url'], page=page)
                doc = first_doc if page == 1 else self._get_doc(list_url)
                if doc is None:
                    continue

                listings = self._parse_list(doc, list_url, entry)
                self.logger.info('Parsed %s listings from %s', len(listings), list_url)
                for item in listings:
                    if self.fetch_detail and item.get('source_url'):
                        detail_doc = self._get_doc(item['source_url'])
                        if detail_doc is not None:
                            for key, value in self._parse_detail(detail_doc, item['source_url']).items():
                                if value not in (None, ''):
                                    item[key] = value
                    yield item

    def _region_entries(self):
        if self.line:
            city_code, region_code = _codes_from_line(self.line)
            return [{
                'city': self.city or self.CITY_CODE_NAMES.get(city_code, city_code),
                'district': '',
                'url': self._list_url(self.line, 1),
                'line': self.line,
                'city_code': city_code,
                'region_code': region_code,
            }]

        home_doc = self._get_doc(self.base_url + '/')
        if home_doc is None:
            return []

        entries = []
        city_blocks = home_doc.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' city_province ')]")
        for block in city_blocks:
            city_name = _first_text(block.xpath(".//div[contains(@class, 'city_list_tit')]//text()"))
            if self.city and city_name != self.city:
                continue
            for link in block.xpath(".//a[contains(@href, '/list?line=')]"):
                href = _first(link.xpath('./@href'))
                region_name = _clean_text(''.join(link.xpath('.//text()')))
                if not href:
                    continue
                line = _line_from_url(href)
                city_code, region_code = _codes_from_line(line)
                entries.append({
                    'city': city_name or self.city or self.CITY_CODE_NAMES.get(city_code, city_code),
                    'district': region_name,
                    'url': urljoin(self.base_url + '/', href),
                    'line': line,
                    'city_code': city_code,
                    'region_code': region_code,
                })
        return entries

    def _list_url(self, line, page):
        return f'{self.base_url}/list?{urlencode({"line": line, "page": page})}'

    def _get_doc(self, url):
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding
            if self.delay:
                sleep(self.delay)
            return html.fromstring(response.text)
        except requests.RequestException as exc:
            self.logger.warning('Request failed: %s (%s)', url, exc)
            return None

    def _parse_list(self, doc, list_url, entry):
        items = []
        nodes = doc.xpath("//ul[contains(@class, 'sellListContent')]/li[contains(@class, 'clear')]")
        for node in nodes:
            item = HouseItem()
            item['city'] = entry.get('city') or ''
            item['district'] = entry.get('district') or ''

            detail_href = _first(node.xpath(".//div[contains(@class, 'title')]/a/@href"))
            item['source_url'] = urljoin(list_url, detail_href) if detail_href else ''
            item['title'] = _first_text(node.xpath(".//div[contains(@class, 'title')]/a//text()"))

            position = [_clean_text(x) for x in node.xpath(".//div[contains(@class, 'positionInfo')]/a//text()")]
            position = [x for x in position if x]
            if position:
                item['community'] = position[0]
            if len(position) > 1:
                item['district'] = position[1]

            house_info = _first_text(node.xpath(".//div[contains(@class, 'houseInfo')]//text()[not(parent::span)]"))
            self._fill_house_info(item, house_info)

            item['total_price'] = _first_text(node.xpath(".//div[contains(@class, 'totalPrice')]//span/text()"))
            item['unit_price'] = _first_text(node.xpath(".//div[contains(@class, 'unitPrice')]//span/text()"))
            item['mianji_group'] = _area_group(item.get('area'))
            items.append(item)
        return items

    def _parse_detail(self, doc, detail_url):
        data = {'source_url': detail_url}
        data['title'] = _first_text(doc.xpath("//h1[contains(@class, 'main')]//text()"))

        overview = _first_text(doc.xpath("//div[contains(@class, 'title-wrapper')]//div[contains(@class, 'sub')]//text()"))
        self._fill_house_info(data, overview)

        data['total_price'] = _first_text(doc.xpath("//div[contains(@class, 'price-container')]//span[contains(@class, 'total')]/text()")) or data.get('total_price')
        data['unit_price'] = _first_text(doc.xpath("//span[contains(@class, 'unitPriceValue')]//text()")) or data.get('unit_price')
        data['community'] = _first_text(doc.xpath("//div[contains(@class, 'aroundInfo')]//div[contains(@class, 'communityName')]//a[contains(@class, 'info')]//text()")) or data.get('community')

        region_texts = doc.xpath("//div[contains(@class, 'aroundInfo')]//div[contains(@class, 'areaName')]//a//text()")
        data['district'] = _pick_region(region_texts) or data.get('district')

        label_values = _label_values(doc)
        data.update({
            'layout': label_values.get('房屋户型') or data.get('layout'),
            'floor': label_values.get('所在楼层') or data.get('floor'),
            'area': label_values.get('建筑面积') or data.get('area'),
            'huxingjiegou': label_values.get('户型结构'),
            'orientation': label_values.get('房屋朝向') or data.get('orientation'),
            'jianzhujiegou': label_values.get('建筑结构') or data.get('jianzhujiegou'),
            'decoration': label_values.get('装修情况') or data.get('decoration'),
            'tihu': label_values.get('梯户比例'),
            'listing_date': label_values.get('挂牌时间') or data.get('listing_date'),
            'quanshu': label_values.get('交易权属'),
            'diya': label_values.get('抵押信息'),
        })

        feature_values = _feature_values(doc)
        data.update({
            'maidian': feature_values.get('核心卖点'),
            'jieshao': feature_values.get('小区介绍'),
            'huxingjieshao': feature_values.get('户型介绍'),
            'jiaotong': feature_values.get('交通出行'),
        })

        point_text = '\n'.join(doc.xpath('//script/text()'))
        point = re.search(r'BMap\.Point\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)', point_text)
        if point:
            data['longitude'] = point.group(1)
            data['latitude'] = point.group(2)

        data['mianji_group'] = _area_group(data.get('area'))
        return data

    def _fill_house_info(self, item, text):
        parts = [_clean_text(part) for part in re.split(r'\s*\|\s*', text or '')]
        parts = [part for part in parts if part]
        fields = [
            ('layout', 0),
            ('area', 1),
            ('orientation', 2),
            ('decoration', 3),
            ('floor', 4),
            ('listing_date', 5),
            ('jianzhujiegou', 6),
        ]
        for field, index in fields:
            if len(parts) > index and parts[index]:
                item[field] = _strip_listing_suffix(parts[index])


def _label_values(doc):
    values = {}
    for li in doc.xpath("//div[contains(@class, 'introContent')]//li[span[contains(@class, 'label')]]"):
        label = _first_text(li.xpath("./span[contains(@class, 'label')]//text()"))
        all_text = _clean_text(''.join(li.xpath('.//text()')))
        value = _clean_text(all_text.replace(label, '', 1)) if label else ''
        if label:
            values[label] = value
    return values


def _feature_values(doc):
    values = {}
    blocks = doc.xpath("//div[contains(@class, 'baseattribute') and .//div[contains(@class, 'name')]]")
    for block in blocks:
        name = _first_text(block.xpath(".//div[contains(@class, 'name')]//text()"))
        value = _first_text(block.xpath(".//div[contains(@class, 'content')]//text()"))
        if name:
            values[name] = value
    return values


def _pick_region(values):
    texts = [_clean_text(value) for value in values]
    texts = [text for text in texts if text]
    for text in texts:
        if re.search(r'(高新区|开发区|新区|区|县|市)$', text):
            return text
    return texts[-1] if texts else ''


def _set_query(url, **params):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key, value in params.items():
        query[key] = [str(value)]
    return parsed._replace(query=urlencode(query, doseq=True)).geturl()


def _line_from_url(url):
    parsed = urlparse(url)
    return _first(parse_qs(parsed.query).get('line')) or ''


def _codes_from_line(line):
    parts = [part for part in str(line or '').strip('/').split('/') if part]
    city_code = parts[0] if parts else ''
    region_code = parts[1] if len(parts) > 1 else ''
    return city_code, region_code


def _detect_total_pages(doc):
    page_numbers = []

    pagination_text = _first_text(doc.xpath("//div[contains(@class, 'pagination')]//text()"))
    for match in re.findall(r'共\s*(\d+)\s*页', pagination_text):
        page_numbers.append(int(match))

    for href in doc.xpath("//div[contains(@class, 'pagination')]//a/@href"):
        parsed = urlparse(href)
        page_value = _first(parse_qs(parsed.query).get('page'))
        if page_value and page_value.isdigit():
            page_numbers.append(int(page_value))

    return max(page_numbers) if page_numbers else 1


def _area_group(value):
    number = _number(value)
    if number is None:
        return ''
    if number < 60:
        return '60平以下'
    if number < 90:
        return '60-90平'
    if number < 120:
        return '90-120平'
    if number < 150:
        return '120-150平'
    if number < 300:
        return '150-300平'
    return '300平以上'


def _strip_listing_suffix(value):
    return re.sub(r'\s*挂牌\s*$', '', _clean_text(value))


def _number(value):
    match = re.search(r'\d+(?:\.\d+)?', str(value or ''))
    return float(match.group(0)) if match else None


def _first(values):
    return values[0] if values else ''


def _first_text(values):
    return _clean_text(''.join(values))


def _clean_text(value):
    text = re.sub(r'\s+', ' ', str(value or '').replace('\xa0', ' '))
    return text.strip()
