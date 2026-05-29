from django.db import models


class City(models.Model):
    """城市表"""
    name = models.CharField(max_length=50, verbose_name='城市名称')
    province = models.CharField(max_length=50, blank=True, null=True, verbose_name='所属省份')
    code = models.CharField(max_length=20, blank=True, null=True, verbose_name='城市编码')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'city'
        verbose_name = '城市'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class District(models.Model):
    """区域表"""
    name = models.CharField(max_length=50, verbose_name='区域名称')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='districts', verbose_name='所属城市')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'district'
        verbose_name = '区域'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.city.name}-{self.name}"


class Community(models.Model):
    """小区表"""
    name = models.CharField(max_length=100, verbose_name='小区名称')
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='communities', verbose_name='所属区域')
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, verbose_name='经度')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, verbose_name='纬度')
    build_year = models.IntegerField(blank=True, null=True, verbose_name='建筑年代')
    property_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='物业类型')
    total_houses = models.IntegerField(blank=True, null=True, verbose_name='总户数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'community'
        verbose_name = '小区'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class House(models.Model):
    """房源表"""
    DECORATION_CHOICES = [
        ('精装', '精装'),
        ('简装', '简装'),
        ('毛坯', '毛坯'),
        ('其他', '其他'),
    ]
    STATUS_CHOICES = [
        (1, '在售'),
        (0, '已下架'),
    ]

    title = models.CharField(max_length=200, verbose_name='房源标题')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='houses', verbose_name='所属小区')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='总价(万元)')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='单价(元/平米)')
    area = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='面积(平米)')
    layout = models.CharField(max_length=50, blank=True, null=True, verbose_name='户型')
    orientation = models.CharField(max_length=50, blank=True, null=True, verbose_name='朝向')
    floor = models.CharField(max_length=50, blank=True, null=True, verbose_name='楼层')
    total_floor = models.IntegerField(blank=True, null=True, verbose_name='总楼层')
    decoration = models.CharField(max_length=50, blank=True, null=True, choices=DECORATION_CHOICES, verbose_name='装修情况')
    elevator = models.BooleanField(default=False, verbose_name='是否有电梯')
    listing_date = models.DateField(blank=True, null=True, verbose_name='挂牌日期')
    house_year = models.IntegerField(blank=True, null=True, verbose_name='房屋年限')
    source_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='来源链接')
    status = models.IntegerField(default=1, choices=STATUS_CHOICES, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'house'
        verbose_name = '房源'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['total_price'], name='idx_total_price'),
            models.Index(fields=['unit_price'], name='idx_unit_price'),
            models.Index(fields=['area'], name='idx_area'),
            models.Index(fields=['status'], name='idx_status'),
        ]

    def __str__(self):
        return self.title


class PricePrediction(models.Model):
    """房价预测结果表"""
    TREND_CHOICES = [
        ('上涨', '上涨'),
        ('下跌', '下跌'),
        ('平稳', '平稳'),
    ]

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='predictions', verbose_name='所属区域')
    predict_date = models.DateField(verbose_name='预测日期')
    avg_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='预测均价(元/平米)')
    trend = models.CharField(max_length=20, choices=TREND_CHOICES, verbose_name='趋势')
    change_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='变化率(%)')
    confidence = models.DecimalField(max_digits=5, decimal_places=4, blank=True, null=True, verbose_name='置信度')
    model_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='模型名称')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'price_prediction'
        verbose_name = '房价预测'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.district.name} - {self.predict_date}"


class Facility(models.Model):
    """周边配套表"""
    TYPE_CHOICES = [
        ('交通', '交通'),
        ('教育', '教育'),
        ('医疗', '医疗'),
        ('商业', '商业'),
        ('生活', '生活'),
    ]

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='facilities', verbose_name='所属小区')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name='类型')
    name = models.CharField(max_length=100, verbose_name='设施名称')
    distance = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, verbose_name='距离(米)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'facility'
        verbose_name = '周边配套'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.type}-{self.name}"
