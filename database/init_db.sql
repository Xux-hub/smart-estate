-- 智慧房产探索平台 数据库初始化脚本
-- Smart Estate Database Initialization

CREATE DATABASE IF NOT EXISTS smart_estate DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE smart_estate;

-- 城市表
DROP TABLE IF EXISTS facility;
DROP TABLE IF EXISTS price_prediction;
DROP TABLE IF EXISTS house;
DROP TABLE IF EXISTS community;
DROP TABLE IF EXISTS district;
DROP TABLE IF EXISTS city;

CREATE TABLE city (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL COMMENT '城市名称',
    province VARCHAR(50) COMMENT '所属省份',
    code VARCHAR(20) COMMENT '城市编码',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='城市表';

-- 区域表
CREATE TABLE district (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL COMMENT '区域名称',
    city_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES city(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='区域表';

-- 小区表
CREATE TABLE community (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '小区名称',
    district_id INT NOT NULL,
    longitude DECIMAL(10, 7) COMMENT '经度',
    latitude DECIMAL(10, 7) COMMENT '纬度',
    build_year INT COMMENT '建筑年代',
    property_type VARCHAR(50) COMMENT '物业类型',
    total_houses INT COMMENT '总户数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (district_id) REFERENCES district(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小区表';

-- 房源表
CREATE TABLE house (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL COMMENT '房源标题',
    community_id INT NOT NULL,
    total_price DECIMAL(10, 2) COMMENT '总价(万元)',
    unit_price DECIMAL(10, 2) COMMENT '单价(元/平米)',
    area DECIMAL(8, 2) COMMENT '面积(平米)',
    layout VARCHAR(50) COMMENT '户型',
    orientation VARCHAR(50) COMMENT '朝向',
    floor VARCHAR(50) COMMENT '楼层',
    total_floor INT COMMENT '总楼层',
    decoration VARCHAR(50) COMMENT '装修情况',
    elevator TINYINT DEFAULT 0 COMMENT '是否有电梯 0-无 1-有',
    listing_date DATE COMMENT '挂牌日期',
    house_year INT COMMENT '房屋年限',
    source_url VARCHAR(500) COMMENT '来源链接',
    status TINYINT DEFAULT 1 COMMENT '状态 1-在售 0-已下架',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (community_id) REFERENCES community(id) ON DELETE CASCADE,
    INDEX idx_price (total_price),
    INDEX idx_unit_price (unit_price),
    INDEX idx_area (area),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='房源表';

-- 房价预测结果表
CREATE TABLE price_prediction (
    id INT PRIMARY KEY AUTO_INCREMENT,
    district_id INT NOT NULL,
    predict_date DATE COMMENT '预测日期',
    avg_price DECIMAL(10, 2) COMMENT '预测均价(元/平米)',
    trend VARCHAR(20) COMMENT '趋势(上涨/下跌/平稳)',
    change_rate DECIMAL(5, 2) COMMENT '变化率(%)',
    confidence DECIMAL(5, 4) COMMENT '置信度',
    model_name VARCHAR(50) COMMENT '使用的模型名称',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (district_id) REFERENCES district(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='房价预测结果表';

-- 周边配套表
CREATE TABLE facility (
    id INT PRIMARY KEY AUTO_INCREMENT,
    community_id INT NOT NULL,
    type VARCHAR(50) COMMENT '类型(交通/教育/医疗/商业/生活)',
    name VARCHAR(100) COMMENT '设施名称',
    distance DECIMAL(6, 2) COMMENT '距离(米)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (community_id) REFERENCES community(id) ON DELETE CASCADE,
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='周边配套表';

-- 插入初始城市数据
INSERT INTO city (name, province, code) VALUES
('北京', '北京市', 'bj'),
('上海', '上海市', 'sh'),
('广州', '广东省', 'gz'),
('深圳', '广东省', 'sz'),
('杭州', '浙江省', 'hz'),
('成都', '四川省', 'cd'),
('武汉', '湖北省', 'wh'),
('南京', '江苏省', 'nj'),
('重庆', '重庆市', 'cq'),
('西安', '陕西省', 'xa');
