import os

import django
import pytest
from django.conf import settings


def pytest_configure():
    """Configure Django settings for in-memory SQLite testing."""
    if not settings.configured:
        settings.configure(
            DEBUG=False,
            SECRET_KEY="test-secret-key",
            ROOT_URLCONF="web.urls",
            ALLOWED_HOSTS=["*"],
            INSTALLED_APPS=[
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "rest_framework",
                "web.apps.home",
                "web.apps.house",
                "web.apps.analysis",
                "web.apps.prediction",
                "web.apps.shandong",
            ],
            MIDDLEWARE=[
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [os.path.join(os.path.dirname(__file__), "web", "templates")],
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.debug",
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                },
            ],
            LANGUAGE_CODE="zh-hans",
            TIME_ZONE="Asia/Shanghai",
            USE_I18N=True,
            USE_TZ=True,
            STATIC_URL="/static/",
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            REST_FRAMEWORK={
                "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
                "PAGE_SIZE": 20,
            },
        )
        django.setup()

    from django.core.management import call_command
    from django.db import connection

    call_command("migrate", "--run-syncdb", verbosity=0, interactive=False)

    # All project models use managed=False, so we must create tables manually
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS house_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city VARCHAR(50), region VARCHAR(50), link VARCHAR(500),
                mingcheng VARCHAR(200), quyu VARCHAR(200),
                huxing VARCHAR(100), louceng VARCHAR(100), mianji VARCHAR(50),
                huxingjiegou VARCHAR(50), chaoxiang VARCHAR(50),
                jianzhujiegou VARCHAR(50), zhuangxiu VARCHAR(50),
                tihu VARCHAR(50), shijian VARCHAR(50),
                quanshu VARCHAR(50), diya VARCHAR(200),
                price VARCHAR(50), unit_price INTEGER,
                jingdu VARCHAR(50), weidu VARCHAR(50),
                maidian TEXT, jieshao TEXT, huxingjieshao TEXT, jiaotong TEXT,
                mianji_group VARCHAR(20)
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS city (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50), province VARCHAR(50),
                house_count INTEGER DEFAULT 0,
                avg_unit_price DECIMAL(12,2),
                community_count INTEGER DEFAULT 0,
                updated_at DATETIME
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS district (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                name VARCHAR(50),
                house_count INTEGER DEFAULT 0,
                avg_unit_price DECIMAL(12,2),
                max_unit_price INTEGER,
                min_unit_price INTEGER,
                community_count INTEGER DEFAULT 0,
                updated_at DATETIME
            )
        """
        )


@pytest.fixture
def house_factory():
    """Create House test instances via raw SQL (models are unmanaged)."""
    from django.db import connection

    def _create(**kwargs):
        defaults = {
            "city": "青岛",
            "region": "市南区",
            "mingcheng": "测试小区",
            "huxing": "3室2厅",
            "louceng": "中楼层",
            "mianji": "120㎡",
            "chaoxiang": "南",
            "zhuangxiu": "精装修",
            "shijian": "2025/06",
            "quanshu": "商品房",
            "diya": "无抵押",
            "price": "200万",
            "unit_price": 16666,
            "mianji_group": "90-120平",
            "link": "http://example.com/house/1",
        }
        defaults.update(kwargs)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO house_info
                    (city, region, mingcheng, huxing, louceng, mianji,
                     chaoxiang, zhuangxiu, shijian, quanshu, diya,
                     price, unit_price, mianji_group, link)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                [
                    defaults["city"], defaults["region"], defaults["mingcheng"],
                    defaults["huxing"], defaults["louceng"], defaults["mianji"],
                    defaults["chaoxiang"], defaults["zhuangxiu"], defaults["shijian"],
                    defaults["quanshu"], defaults["diya"], defaults["price"],
                    defaults["unit_price"], defaults["mianji_group"], defaults["link"],
                ],
            )
        return defaults

    return _create


@pytest.fixture
def city_factory():
    """Create City dimension table records."""
    from django.db import connection

    def _create(name="青岛", house_count=100, avg_unit_price=15000, community_count=10):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO city (name, house_count, avg_unit_price, community_count)
                VALUES (%s, %s, %s, %s)
            """,
                [name, house_count, avg_unit_price, community_count],
            )
        return {
            "name": name,
            "house_count": house_count,
            "avg_unit_price": avg_unit_price,
            "community_count": community_count,
        }

    return _create
