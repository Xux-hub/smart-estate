-- Smart Estate database initialization.
-- This script keeps existing data and creates the tables required by the
-- design document and by the current Django code.

CREATE DATABASE IF NOT EXISTS smart_estate
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smart_estate;

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

CREATE TABLE IF NOT EXISTS raw_house_data (
  id INT(11) NOT NULL AUTO_INCREMENT,
  source_url VARCHAR(500) DEFAULT NULL COMMENT '来源链接',
  raw_city VARCHAR(50) DEFAULT NULL COMMENT '原始城市',
  raw_region VARCHAR(50) DEFAULT NULL COMMENT '原始地区',
  raw_title VARCHAR(200) DEFAULT NULL COMMENT '原始标题',
  raw_community VARCHAR(200) DEFAULT NULL COMMENT '原始小区',
  raw_layout VARCHAR(100) DEFAULT NULL COMMENT '原始户型',
  raw_floor VARCHAR(100) DEFAULT NULL COMMENT '原始楼层',
  raw_area VARCHAR(50) DEFAULT NULL COMMENT '原始面积',
  raw_price VARCHAR(50) DEFAULT NULL COMMENT '原始总价',
  raw_unit_price VARCHAR(50) DEFAULT NULL COMMENT '原始单价',
  raw_orientation VARCHAR(50) DEFAULT NULL COMMENT '原始朝向',
  raw_detail TEXT COMMENT '详情页原始补充信息',
  crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
  task_id INT(11) DEFAULT NULL COMMENT '采集任务编号',
  processed TINYINT(1) DEFAULT 0 COMMENT '是否已清洗',
  PRIMARY KEY (id),
  KEY idx_raw_source_url (source_url(191)),
  KEY idx_raw_task_id (task_id),
  KEY idx_raw_processed (processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='原始房源数据表';

CREATE TABLE IF NOT EXISTS abnormal_house_data (
  id INT(11) NOT NULL AUTO_INCREMENT,
  source_url VARCHAR(500) DEFAULT NULL COMMENT '异常数据来源链接',
  raw_data_id INT(11) DEFAULT NULL COMMENT '对应原始数据编号',
  error_type VARCHAR(100) DEFAULT NULL COMMENT '异常类型',
  error_field VARCHAR(100) DEFAULT NULL COMMENT '异常字段',
  error_message TEXT COMMENT '异常说明',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  status VARCHAR(50) DEFAULT 'pending' COMMENT '处理状态',
  PRIMARY KEY (id),
  KEY idx_abnormal_raw_data_id (raw_data_id),
  KEY idx_abnormal_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异常房源数据表';

CREATE TABLE IF NOT EXISTS analysis_result (
  id INT(11) NOT NULL AUTO_INCREMENT,
  analysis_type VARCHAR(100) DEFAULT NULL COMMENT '分析类型',
  city VARCHAR(50) DEFAULT NULL COMMENT '城市',
  region VARCHAR(50) DEFAULT NULL COMMENT '区域',
  target_name VARCHAR(200) DEFAULT NULL COMMENT '统计对象名称',
  result_value FLOAT DEFAULT NULL COMMENT '统计结果或预测结果',
  result_json TEXT COMMENT '复杂图表数据或模型输出结果',
  model_name VARCHAR(100) DEFAULT NULL COMMENT '预测模型名称',
  mae FLOAT DEFAULT NULL COMMENT '平均绝对误差',
  rmse FLOAT DEFAULT NULL COMMENT '均方根误差',
  r2 FLOAT DEFAULT NULL COMMENT '模型决定系数',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '结果生成时间',
  PRIMARY KEY (id),
  KEY idx_analysis_type_city_region (analysis_type, city, region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析结果表';
