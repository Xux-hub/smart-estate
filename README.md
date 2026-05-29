# 智慧房产探索平台 (Smart Estate)

## 项目简介

基于 Python 构建的智慧房产探索平台，通过采集链家二手房网站数据，存储到数据库中，对整体房价进行分析和预测，构建可视化房产平台。帮助用户快速了解城市与各区域房源及价格情况，找到合适的房源，辅助房地产投资者寻找投资机会。

## 技术架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                      前端展示层                               │
│   Django Templates + ECharts + Bootstrap 5                  │
├─────────────────────────────────────────────────────────────┤
│                      后端服务层                               │
│   Django 4.x (Views + REST API)                             │
├─────────────────────────────────────────────────────────────┤
│                      数据分析层                               │
│   Pandas + Numpy + Matplotlib + Seaborn + Sklearn           │
├─────────────────────────────────────────────────────────────┤
│                      数据采集层                               │
│   Scrapy 2.16 (链家爬虫 + Django ORM 入库)                   │
├─────────────────────────────────────────────────────────────┤
│                      数据存储层                               │
│   SQLite(开发) / MySQL(生产)                                 │
└─────────────────────────────────────────────────────────────┘
```

## 功能模块

### 1. 数据采集模块 (`/crawler`)

| 功能 | 说明 |
|------|------|
| 房源数据爬取 | 采集链家平台二手房列表页数据 |
| 前端爬虫管理 | Web 界面选择城市、启动采集、查看任务状态 |
| 数据清洗 | 价格/面积格式化、装修标准化、缺失值处理 |
| Django ORM 入库 | 通过 Django ORM 存储，兼容 SQLite 和 MySQL |

**采集字段：**
- 房源标题、总价、单价
- 所在城市、区域、小区名称
- 户型、面积、朝向、楼层
- 装修情况

### 2. 数据存储模块

项目支持双数据库模式，自动检测 MySQL 是否可用：
- **开发环境**：SQLite（零配置，开箱即用）
- **生产环境**：MySQL 8.0（大数据量、高并发）

数据模型通过 Django ORM 定义（`web/apps/house/models.py`），包含：
- `City` — 城市表
- `District` — 区域表
- `Community` — 小区表
- `House` — 房源表
- `PricePrediction` — 房价预测结果表
- `Facility` — 周边配套表

### 3. 数据分析与预测模块 (`/analysis`)

| 分析内容 | 技术方案 |
|----------|----------|
| 房价分布分析 | Pandas + ECharts 各区域房价分布 |
| 房价趋势预测 | 基于现有数据实时生成未来6个月趋势 |
| 房价影响因素分析 | 面积-价格散点图、装修-价格关系 |
| 区域对比 | 多区域均价柱状图对比 |
| 户型统计 | 热门户型饼图分布 |

### 4. Web 可视化展示模块 (`/web`)

基于 Django 构建，前端使用 ECharts 图表 + Bootstrap 5 布局。

**页面列表：**

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页大屏 | `/` | 城市房价排行、房源数量分布、核心指标 |
| 城市房价 | `/city/<name>/` | 城市各区域均价对比 |
| 房源列表 | `/house/` | 多条件筛选、排序、分页 |
| 房源详情 | `/house/<id>/` | 房源信息、同小区房源、周边配套 |
| 区域详情 | `/house/district/<id>/` | 区域统计、小区列表 |
| 数据分析 | `/analysis/` | 房价分布、户型统计、面积-价格散点图 |
| 区域对比 | `/analysis/compare/` | 多区域房价对比 |
| 房价预测 | `/prediction/` | 各区域未来房价趋势预测 |
| 爬虫管理 | `/house/crawler/` | 启动采集、任务状态、历史记录 |
| 房源搜索 | `/house/search/` | 关键词搜索 |

## 技术栈详情

| 层级 | 技术 | 用途 |
|------|------|------|
| 数据采集 | Scrapy 2.16 | 爬虫框架 |
| 数据存储 | SQLite / MySQL | 数据库（自动切换） |
| 数据存储 | Django ORM | 数据模型与操作 |
| 数据处理 | Pandas | 数据清洗与处理 |
| 数据分析 | Numpy | 数值计算 |
| 数据可视化 | Matplotlib + Seaborn | 静态图表（分析脚本） |
| 机器学习 | Scikit-learn | 房价预测模型 |
| Web 框架 | Django 4.2 | 后端服务 |
| 前端图表 | ECharts 5.x | 交互式图表（CDN 引入） |
| 前端 UI | Bootstrap 5.3 | 响应式页面布局（CDN 引入） |
| 包管理 | uv | Python 依赖管理与虚拟环境 |

## 项目目录结构

```
smart-estate/
├── README.md                   # 项目说明文档
├── pyproject.toml              # 项目配置与依赖（uv 管理）
├── manage.py                   # Django 管理入口
│
├── crawler/                    # 数据采集模块
│   ├── scrapy.cfg
│   └── estate_spider/
│       ├── settings.py         # Scrapy 配置
│       ├── items.py            # 数据模型定义
│       ├── pipelines.py        # 数据清洗 + Django ORM 入库
│       ├── middlewares.py      # 随机 UA 中间件
│       └── spiders/
│           └── lianjia.py      # 链家爬虫
│
├── database/                   # 数据库模块
│   ├── init_db.sql             # MySQL 初始化脚本
│   └── seed_data.py            # 测试数据填充（PyMySQL 直连）
│
├── analysis/                   # 数据分析模块
│   ├── price_analysis.py       # 房价分析
│   └── prediction/
│       ├── model_train.py      # 模型训练
│       └── model_predict.py    # 模型预测
│
├── web/                        # Django Web 应用
│   ├── settings.py             # Django 配置（自动切换 SQLite/MySQL）
│   ├── urls.py                 # 路由配置
│   ├── wsgi.py
│   ├── apps/
│   │   ├── home/               # 首页
│   │   ├── house/              # 房源 + 爬虫管理
│   │   ├── analysis/           # 数据分析展示
│   │   └── prediction/         # 房价预测
│   ├── static/css/             # 自定义样式
│   └── templates/              # HTML 模板
│
├── config/                     # 配置文件
│   ├── database.yml            # 数据库配置（MySQL）
│   └── redis.yml               # Redis 配置
│
└── scripts/                    # 工具脚本
    ├── seed_django.py          # 填充测试数据（Django ORM）
    ├── start_crawler.py        # 命令行启动爬虫
    ├── run_analysis.py         # 运行分析
    └── init_project.py         # MySQL 初始化
```

## 环境要求

- Python 3.9+（推荐 3.13）
- [uv](https://docs.astral.sh/uv/) — Python 包管理器
- MySQL 8.0+（可选，不装则自动使用 SQLite）
- Redis 6.0+（可选，仅分布式爬虫需要）

## 快速开始

```bash
# 1. 克隆项目
git clone git@github.com:epocode/smart-estate.git
cd smart-estate

# 2. 安装依赖
uv sync

# 3. 数据库迁移
uv run python manage.py migrate

# 4. 填充测试数据
uv run python scripts/seed_django.py

# 5. 启动 Web 服务
uv run python manage.py runserver
```

访问 http://127.0.0.1:8000 即可查看平台。

### 使用爬虫采集真实数据

方式一：通过 Web 界面（推荐）
1. 访问 http://127.0.0.1:8000/house/crawler/
2. 选择城市和页数，点击「启动采集」

方式二：命令行
```bash
uv run python scripts/start_crawler.py --city 北京 --pages 3
```

### 常用 uv 命令

```bash
uv add <package>          # 添加依赖
uv add --dev <package>    # 添加开发依赖
uv lock --upgrade         # 更新所有依赖
uv run <command>          # 在虚拟环境中运行命令
```

## 部署方式

### 方式一：本地开发部署（SQLite，零配置）

无需安装 MySQL，项目自动使用 SQLite。

```bash
uv sync
uv run python manage.py migrate
uv run python scripts/seed_django.py
uv run python manage.py runserver
```

### 方式二：本地开发部署（MySQL）

```bash
# 1. 安装并启动 MySQL 8.0

# 2. 编辑 config/database.yml 填入 MySQL 连接信息

# 3. 初始化
uv sync
uv run python scripts/init_project.py
uv run python manage.py migrate
uv run python scripts/seed_django.py
uv run python manage.py runserver
```

### 方式三：生产环境部署（Gunicorn + Nginx）

#### 服务器准备

```bash
sudo apt update
sudo apt install -y mysql-server nginx
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 项目部署

```bash
git clone git@github.com:epocode/smart-estate.git /opt/smart-estate
cd /opt/smart-estate

uv sync --no-dev
# 编辑 config/database.yml 填入生产数据库信息

uv run python scripts/init_project.py
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
```

#### Gunicorn 服务

```bash
uv add gunicorn
```

创建 `/etc/systemd/system/smart-estate.service`：

```ini
[Unit]
Description=Smart Estate Django App
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/smart-estate
ExecStart=/opt/smart-estate/.venv/bin/gunicorn web.wsgi:application --bind 127.0.0.1:8000 --workers 4 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now smart-estate
```

#### Nginx 配置

创建 `/etc/nginx/sites-available/smart-estate`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /opt/smart-estate/staticfiles/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/smart-estate /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

#### 生产环境配置

修改 `web/settings.py`：

```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']
SECRET_KEY = 'your-random-secret-key'
```

### 方式四：Docker 部署

`Dockerfile`：

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN uv run python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["uv", "run", "gunicorn", "web.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

`docker-compose.yml`：

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DJANGO_SETTINGS_MODULE=web.settings

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: smart_estate_pwd
      MYSQL_DATABASE: smart_estate
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/init_db.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  mysql_data:
```

```bash
docker-compose up -d
```

## License

MIT
