"""Scraped house item fields mapped to the house_info table."""
import scrapy


class HouseItem(scrapy.Item):
    title = scrapy.Field()
    city = scrapy.Field()
    district = scrapy.Field()
    source_url = scrapy.Field()
    community = scrapy.Field()
    quyu = scrapy.Field()

    layout = scrapy.Field()
    floor = scrapy.Field()
    area = scrapy.Field()
    huxingjiegou = scrapy.Field()
    orientation = scrapy.Field()
    jianzhujiegou = scrapy.Field()
    decoration = scrapy.Field()
    tihu = scrapy.Field()
    listing_date = scrapy.Field()
    quanshu = scrapy.Field()
    diya = scrapy.Field()

    total_price = scrapy.Field()
    unit_price = scrapy.Field()
    longitude = scrapy.Field()
    latitude = scrapy.Field()

    maidian = scrapy.Field()
    jieshao = scrapy.Field()
    huxingjieshao = scrapy.Field()
    jiaotong = scrapy.Field()
    mianji_group = scrapy.Field()

    total_floor = scrapy.Field()
    elevator = scrapy.Field()
    house_year = scrapy.Field()
