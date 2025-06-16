import random
import os

BOT_NAME = 'gloria_jeans'
SPIDER_MODULES = ['gloria_jeans.spiders']
NEWSPIDER_MODULE = 'gloria_jeans.spiders'

ROBOTSTXT_OBEY = False

# Основные настройки
CONCURRENT_REQUESTS = 1
DOWNLOAD_TIMEOUT = 60
DOWNLOAD_DELAY = random.uniform(15, 25)

# Настройки middleware
DOWNLOADER_MIDDLEWARES = {
    'gloria_jeans.middlewares.WebdriverCookieMiddleware': 100,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}

# Настройки экспорта
FEEDS = {
    'data/products_%(time)s.json': {
        'format': 'json',
        'encoding': 'utf8',
        'overwrite': True
    }
}

# Логирование
LOG_ENABLED = True
LOG_FILE = 'gloria_jeans.log'
LOG_LEVEL = 'INFO'
LOG_FILE_APPEND = False

# Настройки повторных попыток
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408, 429]

# User-Agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'

# Дополнительные настройки
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 15
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5

# Настройки для обхода защиты
COOKIES_ENABLED = True
COOKIES_DEBUG = False
DUPEFILTER_DEBUG = True

# URL для обновления куки
UPDATE_COOKIE_URL = 'https://www.gloria-jeans.ru/'
UPDATE_COOKIES_EVERY_S = 300
DRIVER_UPDATE_WAIT_TIME = 30

# Категории для парсинга
CATEGORIES = {
    'girls': 'Женщины',
    'boys': 'Мужчины',
    'teenagers': 'Подростки',
    'kids': 'Дети',
    'sale': 'Скидки'
}

# Базовые URL
BASE_URL = 'https://www.gloria-jeans.ru/'
CATALOG_URL = 'https://www.gloria-jeans.ru/catalog/'

# Настройки Chrome
CHROME_DRIVER_PATH = os.path.join(os.getenv('APPDATA'), 'undetected_chromedriver', 'undetected_chromedriver.exe')
CHROME_BROWSER_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'