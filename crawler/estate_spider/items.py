"""
Define the data models for scraped items.
"""
import scrapy


class HouseItem(scrapy.Item):
    """房源数据模型"""
    # 基本信息
    title = scrapy.Field()          # 房源标题
    total_price = scrapy.Field()    # 总价(万元)
    unit_price = scrapy.Field()     # 单价(元/平米)
    area = scrapy.Field()           # 面积(平米)

    # 房屋属性
    layout = scrapy.Field()         # 户型
    orientation = scrapy.Field()    # 朝向
    floor = scrapy.Field()          # 楼层描述
    total_floor = scrapy.Field()    # 总楼层
    decoration = scrapy.Field()     # 装修情况
    elevator = scrapy.Field()       # 是否有电梯
    house_year = scrapy.Field()     # 房屋年限/建筑年代

    # 位置信息
    city = scrapy.Field()           # 城市
    district = scrapy.Field()       # 区域
    community = scrapy.Field()      # 小区名称
    longitude = scrapy.Field()      # 经度
    latitude = scrapy.Field()       # 纬度

    # 其他
    listing_date = scrapy.Field()   # 挂牌日期
    source_url = scrapy.Field()     # 来源链接
