"""
Scrapy settings for estate_spider project.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BOT_NAME = 'estate_spider'
SPIDER_MODULES = ['estate_spider.spiders']
NEWSPIDER_MODULE = 'estate_spider.spiders'

# Crawl responsibly
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 4

# Configure a delay for requests
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies
COOKIES_ENABLED = False

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'estate_spider.middlewares.RandomUserAgentMiddleware': 400,
}

# Configure item pipelines
ITEM_PIPELINES = {
    'estate_spider.pipelines.DataCleanPipeline': 200,
    'estate_spider.pipelines.DjangoORMPipeline': 300,
}

# MySQL Configuration
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password_here'
MYSQL_DATABASE = 'smart_estate'

# Redis Configuration (for Scrapy-Redis)
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'

# Request fingerprinter
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.selectreactor.SelectReactor"
FEED_EXPORT_ENCODING = "utf-8"
