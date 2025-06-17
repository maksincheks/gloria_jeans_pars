import random

BOT_NAME = 'gloria_jeans'
SPIDER_MODULES = ['gloria_jeans.spiders']
NEWSPIDER_MODULE = 'gloria_jeans.spiders'

ROBOTSTXT_OBEY = False

# Настройки запросов
CONCURRENT_REQUESTS = 2
DOWNLOAD_DELAY = random.uniform(1, 3)
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408, 429]

# Настройки экспорта
FEEDS = {
    'data/products_%(time)s.json': {
        'format': 'json',
        'encoding': 'utf8',
        'indent': 4,
        'overwrite': True
    }
}

# Логирование
LOG_LEVEL = 'INFO'
LOG_FILE = 'gloria_jeans.log'
LOG_FILE_APPEND = False

# Категории для парсинга
CATEGORIES = {
    'girls': 'Для девочек',
    'boys': 'Для мальчиков',
    'women': 'Женщинам',
    'men': 'Мужчинам',
    'newborn': 'Новорожденным',
    'sale': 'Распродажа'
}

# Middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}

# User-Agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'