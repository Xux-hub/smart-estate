# Generated for the local house_info schema.

from django.db import migrations


CREATE_HOUSE_INFO = """
CREATE TABLE IF NOT EXISTS house_info (
  id INT(11) NOT NULL AUTO_INCREMENT,
  city VARCHAR(50) DEFAULT NULL COMMENT '城市',
  region VARCHAR(50) DEFAULT NULL COMMENT '地区',
  link VARCHAR(500) DEFAULT NULL COMMENT '房源链接',
  mingcheng VARCHAR(200) DEFAULT NULL COMMENT '小区名称',
  quyu VARCHAR(200) DEFAULT NULL COMMENT '所在区域',
  huxing VARCHAR(100) DEFAULT NULL COMMENT '房屋户型',
  louceng VARCHAR(100) DEFAULT NULL COMMENT '所在楼层',
  mianji VARCHAR(50) DEFAULT NULL COMMENT '建筑面积',
  huxingjiegou VARCHAR(50) DEFAULT NULL COMMENT '户型结构',
  chaoxiang VARCHAR(50) DEFAULT NULL COMMENT '房屋朝向',
  jianzhujiegou VARCHAR(50) DEFAULT NULL COMMENT '建筑结构',
  zhuangxiu VARCHAR(50) DEFAULT NULL COMMENT '装修情况',
  tihu VARCHAR(50) DEFAULT NULL COMMENT '梯户比例',
  shijian VARCHAR(50) DEFAULT NULL COMMENT '挂牌时间',
  quanshu VARCHAR(50) DEFAULT NULL COMMENT '交易权属',
  diya VARCHAR(200) DEFAULT NULL COMMENT '抵押信息',
  price VARCHAR(50) DEFAULT NULL COMMENT '总价(万元)',
  unit_price INT(11) DEFAULT NULL COMMENT '单价(元/平方米，整数)',
  jingdu VARCHAR(50) DEFAULT NULL COMMENT '经度',
  weidu VARCHAR(50) DEFAULT NULL COMMENT '纬度',
  maidian TEXT COMMENT '核心卖点',
  jieshao TEXT COMMENT '小区介绍',
  huxingjieshao TEXT COMMENT '户型介绍',
  jiaotong TEXT COMMENT '交通出行',
  mianji_group VARCHAR(20) DEFAULT NULL COMMENT '面积分组',
  PRIMARY KEY (id),
  KEY idx_house_city_region (city, region),
  KEY idx_house_unit_price (unit_price),
  KEY idx_house_mingcheng (mingcheng),
  KEY idx_house_area_group (mianji_group),
  KEY idx_house_link (link(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='标准化房源表';
"""


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(CREATE_HOUSE_INFO, reverse_sql=migrations.RunSQL.noop),
    ]
