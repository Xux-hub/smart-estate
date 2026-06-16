import re
from decimal import Decimal, InvalidOperation

from django.db import models


class House(models.Model):
    city = models.CharField('城市', max_length=50, blank=True, null=True)
    region = models.CharField('地区', max_length=50, blank=True, null=True)
    link = models.CharField('房源链接', max_length=500, blank=True, null=True)
    mingcheng = models.CharField('小区名称', max_length=200, blank=True, null=True)
    quyu = models.CharField('所在区域', max_length=200, blank=True, null=True)
    huxing = models.CharField('房屋户型', max_length=100, blank=True, null=True)
    louceng = models.CharField('所在楼层', max_length=100, blank=True, null=True)
    mianji = models.CharField('建筑面积', max_length=50, blank=True, null=True)
    huxingjiegou = models.CharField('户型结构', max_length=50, blank=True, null=True)
    chaoxiang = models.CharField('房屋朝向', max_length=50, blank=True, null=True)
    jianzhujiegou = models.CharField('建筑结构', max_length=50, blank=True, null=True)
    zhuangxiu = models.CharField('装修情况', max_length=50, blank=True, null=True)
    tihu = models.CharField('梯户比例', max_length=50, blank=True, null=True)
    shijian = models.CharField('挂牌时间', max_length=50, blank=True, null=True)
    quanshu = models.CharField('交易权属', max_length=50, blank=True, null=True)
    diya = models.CharField('抵押信息', max_length=200, blank=True, null=True)
    price = models.CharField('总价(万元)', max_length=50, blank=True, null=True)
    unit_price = models.IntegerField('单价(元/平方米)', blank=True, null=True)
    jingdu = models.CharField('经度', max_length=50, blank=True, null=True)
    weidu = models.CharField('纬度', max_length=50, blank=True, null=True)
    maidian = models.TextField('核心卖点', blank=True, null=True)
    jieshao = models.TextField('小区介绍', blank=True, null=True)
    huxingjieshao = models.TextField('户型介绍', blank=True, null=True)
    jiaotong = models.TextField('交通出行', blank=True, null=True)
    mianji_group = models.CharField('面积分组', max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'house_info'
        managed = False
        verbose_name = '房源'
        verbose_name_plural = '房源'

    def __str__(self):
        return self.title

    @property
    def title(self):
        parts = [self.mingcheng, self.huxing, self.mianji]
        return ' '.join(str(part) for part in parts if part) or f'房源 {self.pk}'

    @property
    def total_price(self):
        return _to_decimal(self.price)

    @property
    def area(self):
        return _to_decimal(self.mianji)

    @property
    def layout(self):
        return self.huxing

    @property
    def orientation(self):
        return self.chaoxiang

    @property
    def floor(self):
        return self.louceng

    @property
    def decoration(self):
        return self.zhuangxiu

    @property
    def district_name(self):
        return self.region or self.quyu or ''

    @property
    def community_name(self):
        return self.mingcheng or ''

    @property
    def location_label(self):
        return ' - '.join(part for part in [self.city, self.district_name, self.community_name] if part)


class City(models.Model):
    name = models.CharField(max_length=50)
    province = models.CharField(max_length=50, blank=True, null=True)
    house_count = models.IntegerField(default=0)
    avg_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    community_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'city'
        managed = False

    def __str__(self):
        return self.name


class District(models.Model):
    city_id = models.IntegerField()
    name = models.CharField(max_length=50)
    house_count = models.IntegerField(default=0)
    avg_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    max_unit_price = models.IntegerField(blank=True, null=True)
    min_unit_price = models.IntegerField(blank=True, null=True)
    community_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'district'
        managed = False

    def __str__(self):
        return self.name


class Community(models.Model):
    district_id = models.IntegerField()
    name = models.CharField(max_length=200)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    house_count = models.IntegerField(default=0)
    avg_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'community'
        managed = False

    def __str__(self):
        return self.name


class CityStat(models.Model):
    city = models.CharField(max_length=50, primary_key=True)
    house_count = models.IntegerField(default=0)
    community_count = models.IntegerField(default=0)
    avg_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'house_city_stat'
        managed = False


class RegionStat(models.Model):
    city = models.CharField(max_length=50)
    region = models.CharField(max_length=50)
    house_count = models.IntegerField(default=0)
    community_count = models.IntegerField(default=0)
    avg_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    max_unit_price = models.IntegerField(blank=True, null=True)
    min_unit_price = models.IntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'house_region_stat'
        managed = False


class LayoutStat(models.Model):
    city = models.CharField(max_length=50)
    layout_name = models.CharField(max_length=100)
    house_count = models.IntegerField(default=0)
    avg_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'house_layout_stat'
        managed = False


class DecorationStat(models.Model):
    city = models.CharField(max_length=50)
    decoration_name = models.CharField(max_length=50)
    house_count = models.IntegerField(default=0)
    avg_unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'house_decoration_stat'
        managed = False


def _to_decimal(value):
    if value in (None, ''):
        return None
    match = re.search(r'\d+(?:\.\d+)?', str(value))
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None
