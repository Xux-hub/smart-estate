import os
import re
import sys

from scrapy.exceptions import DropItem

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
import django

django.setup()


class DataCleanPipeline:
    def process_item(self, item, spider):
        if not item.get('title') and not item.get('community'):
            raise DropItem('missing house title/community')

        city = _clean_text(item.get('city'))
        community = _clean_text(item.get('community') or item.get('title'))
        district = _clean_region(item.get('district') or item.get('quyu'), city, community)
        quyu = _clean_region(item.get('quyu') or district, city, community) or district

        item['city'] = city
        item['community'] = community
        item['district'] = district
        item['quyu'] = quyu
        item['layout'] = _compact_text(item.get('layout'))
        item['floor'] = _clean_floor(item.get('floor'))
        item['area'] = _number(item.get('area'))
        item['huxingjiegou'] = _clean_text(item.get('huxingjiegou'))
        item['orientation'] = _clean_orientation(item.get('orientation'))
        item['jianzhujiegou'] = _clean_text(item.get('jianzhujiegou'))
        item['decoration'] = _clean_text(item.get('decoration'))
        item['tihu'] = _compact_text(item.get('tihu'))
        item['listing_date'] = _clean_date(item.get('listing_date'))
        item['quanshu'] = _clean_text(item.get('quanshu'))
        item['diya'] = _clean_text(item.get('diya'))
        item['total_price'] = _number(item.get('total_price'))
        item['unit_price'] = _int_number(item.get('unit_price'))
        item['longitude'] = _clean_text(item.get('longitude'))
        item['latitude'] = _clean_text(item.get('latitude'))

        for field in ('maidian', 'jieshao', 'huxingjieshao', 'jiaotong'):
            item[field] = _clean_long_text(item.get(field))

        item['mianji_group'] = _area_group(item.get('area'))
        return item


class DjangoORMPipeline:
    def open_spider(self, spider):
        from web.apps.house.models import House

        self.House = House

    def process_item(self, item, spider):
        self.House.objects.create(
            city=item.get('city') or '',
            region=item.get('district') or '',
            link=item.get('source_url') or '',
            mingcheng=item.get('community') or item.get('title') or '',
            quyu=item.get('quyu') or item.get('district') or '',
            huxing=item.get('layout') or '',
            louceng=item.get('floor') or '',
            mianji=_area_text(item.get('area')),
            huxingjiegou=item.get('huxingjiegou') or '',
            chaoxiang=item.get('orientation') or '',
            jianzhujiegou=item.get('jianzhujiegou') or '',
            zhuangxiu=item.get('decoration') or '',
            tihu=item.get('tihu') or '',
            shijian=item.get('listing_date') or '',
            quanshu=item.get('quanshu') or '',
            diya=item.get('diya') or '',
            price=str(item.get('total_price') or ''),
            unit_price=item.get('unit_price'),
            jingdu=str(item.get('longitude') or ''),
            weidu=str(item.get('latitude') or ''),
            maidian=item.get('maidian') or '',
            jieshao=item.get('jieshao') or '',
            huxingjieshao=item.get('huxingjieshao') or '',
            jiaotong=item.get('jiaotong') or '',
            mianji_group=item.get('mianji_group') or _area_group(item.get('area')),
        )
        return item


def _clean_region(value, city='', community=''):
    text = _clean_text(value)
    if not text:
        return ''

    city = _clean_text(city)
    community = _clean_text(community)
    if community:
        text = text.replace(community, '')
    if city:
        city_prefixes = [city]
        if not city.endswith('\u5e02'):
            city_prefixes.insert(0, city + '\u5e02')
        for prefix in city_prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        else:
            text = text.replace(city, '')

    text = re.sub(r'[\s/|,\u3001\uff0c\u3002;；-]+', '', text)
    if not text:
        return ''
    if text.startswith('\u5e02') and len(text) > 3:
        text = text[1:]

    half = len(text) // 2
    if len(text) % 2 == 0 and text[:half] == text[half:]:
        text = text[:half]

    city_district = re.match(r'\u5e02[\u4e00-\u9fffA-Za-z0-9]*?\u533a', text)
    if city_district:
        return city_district.group(0)

    suffix = r'(?:\u9ad8\u65b0\u533a|\u5f00\u53d1\u533a|\u65b0\u533a|\u533a|\u53bf|\u5e02)'
    matches = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+?' + suffix, text)
    matches = [match for match in matches if match not in {'\u5e02', '\u533a', '\u53bf'}]
    if matches:
        return sorted(set(matches), key=len)[0]
    return text


def _clean_floor(value):
    text = _clean_text(value).replace('\uff08', '(').replace('\uff09', ')')
    if not text:
        return ''
    text = re.sub(r'\s+', '', text)
    text = text.replace('(', ' (')
    return text.strip()


def _clean_orientation(value):
    text = _clean_text(value)
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text)


def _clean_date(value):
    text = _clean_text(value)
    match = re.search(r'\d{4}\s*/\s*\d{1,2}\s*/\s*\d{1,2}', text)
    return re.sub(r'\s+', '', match.group(0)) if match else text


def _clean_long_text(value):
    text = _clean_text(value)
    if text in {'None', 'none', '\u6682\u65e0\u6570\u636e', '\u6682\u65e0'}:
        return ''
    text = re.sub(r'^[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]\s+', '', text)
    text = re.sub(r'\s*\|\s*', '|', text)
    text = re.sub(r'\s*([\uff0c\u3002\uff1b\u3001])\s*', r'\1', text)
    text = re.sub(r'\s*,\s*', ',', text)
    return text.strip()


def _compact_text(value):
    return re.sub(r'\s+', '', _clean_text(value))


def _clean_text(value):
    text = str(value or '').replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _number(value):
    if value in (None, ''):
        return None
    match = re.search(r'\d+(?:\.\d+)?', str(value))
    return float(match.group(0)) if match else None


def _int_number(value):
    number = _number(value)
    return int(number) if number is not None else None


def _area_text(value):
    number = _number(value)
    return f'{number:g}\u33a1' if number is not None else ''


def _area_group(value):
    number = _number(value)
    if number is None:
        return ''
    if number < 60:
        return '60\u5e73\u4ee5\u4e0b'
    if number < 90:
        return '60-90\u5e73'
    if number < 120:
        return '90-120\u5e73'
    if number < 150:
        return '120-150\u5e73'
    if number < 300:
        return '150-300\u5e73'
    return '300\u5e73\u4ee5\u4e0a'
