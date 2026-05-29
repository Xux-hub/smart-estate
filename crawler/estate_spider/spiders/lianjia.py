"""
链家二手房爬虫
从列表页直接提取房源数据
"""
import re
import scrapy
from estate_spider.items import HouseItem


class LianjiaSpider(scrapy.Spider):
    name = 'lianjia'
    allowed_domains = ['lianjia.com']

    # 支持的城市及其链家域名前缀
    CITY_MAP = {
        '北京': 'bj',
        '上海': 'sh',
        '广州': 'gz',
        '深圳': 'sz',
        '杭州': 'hz',
        '成都': 'cd',
        '武汉': 'wh',
        '南京': 'nj',
        '重庆': 'cq',
        '西安': 'xa',
    }

    def __init__(self, city='北京', pages=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.pages = int(pages)
        self.city_code = self.CITY_MAP.get(city, 'bj')
        self.start_urls = [
            f'https://{self.city_code}.lianjia.com/ershoufang/pg{page}/'
            for page in range(1, self.pages + 1)
        ]

    def parse(self, response):
        """从列表页直接提取房源数据"""
        listings = response.css('ul.sellListContent li.clear')
        self.logger.info(f"Found {len(listings)} listings on {response.url}")

        for li in listings:
            item = HouseItem()
            item['city'] = self.city
            item['source_url'] = li.css('div.title a::attr(href)').get('')

            # 标题
            item['title'] = li.css('div.title a::text').get('').strip()

            # 价格
            item['total_price'] = li.css('div.totalPrice span::text').get('')
            item['unit_price'] = li.css('div.unitPrice span::text').get('')

            # 房屋信息: "2室1厅 | 89.3平米 | 南 | 精装 | 高楼层(共18层) ..."
            house_info = li.css('div.houseInfo::text').get('')
            if not house_info:
                # 备用选择器
                house_info = ' | '.join(li.css('div.address div.houseInfo a::text').getall())

            parts = [p.strip() for p in house_info.split('|')]
            if len(parts) >= 1:
                item['layout'] = parts[0].strip()
            if len(parts) >= 2:
                item['area'] = parts[1].strip()
            if len(parts) >= 3:
                item['orientation'] = parts[2].strip()
            if len(parts) >= 4:
                item['decoration'] = parts[3].strip()
            if len(parts) >= 5:
                floor_info = parts[4].strip()
                item['floor'] = floor_info
                floor_match = re.search(r'共(\d+)层', floor_info)
                if floor_match:
                    item['total_floor'] = floor_match.group(1)

            # 位置信息
            position_parts = li.css('div.positionInfo a::text').getall()
            if position_parts:
                item['community'] = position_parts[0].strip()
            if len(position_parts) >= 2:
                item['district'] = position_parts[1].strip()

            # 如果没有从 positionInfo 获取到区域，尝试其他方式
            if not item.get('district'):
                flood_info = li.css('div.flood div.positionInfo::text').get('')
                item['district'] = flood_info.strip(' -\t\n')

            yield item
