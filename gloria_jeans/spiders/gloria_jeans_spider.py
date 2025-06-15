import scrapy
from urllib.parse import urljoin
from gloria_jeans.items import ProductItem
from datetime import datetime
import time
import random
from scrapy.utils.response import response_status_message
from twisted.internet.error import TimeoutError, TCPTimedOutError


class GloriaJeansSpider(scrapy.Spider):
    name = 'gloria_jeans'
    allowed_domains = ['gloria-jeans.ru']
    start_urls = ['https://www.gloria-jeans.ru/']

    custom_settings = {
        'DOWNLOAD_DELAY': random.uniform(20, 40),
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [403, 429, 500, 502, 503, 504, 522, 524],
        'DOWNLOAD_TIMEOUT': 180,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 20,
        'AUTOTHROTTLE_MAX_DELAY': 120,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.25
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_urls = []
        self.retry_delays = [30, 60, 120, 240]

    def parse(self, response):
        categories = [
            ('girls', 'Женщины'),
            ('boys', 'Мужчины'),
            ('teenagers', 'Подростки'),
            ('kids', 'Дети'),
            ('sale', 'Скидки')
        ]

        for category_id, category_name in categories:
            url = f"https://www.gloria-jeans.ru/catalog/{category_id}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_category,
                meta={
                    'category': category_name,
                    'retry_times': 0,
                    'max_retry_times': 3,
                    'handle_httpstatus_list': [403, 429, 503],
                    'dont_merge_cookies': False,
                    'cookiejar': category_id,
                    'priority': 1
                },
                errback=self.errback,
                dont_filter=True
            )

    def parse_category(self, response):
        if self._is_blocked(response):
            yield from self._handle_blocked(response)
            return

        time.sleep(random.uniform(8, 15))

        product_links = response.css('a.product-card__link::attr(href)').getall()
        if not product_links:
            product_links = response.css('div.product-card a::attr(href)').getall()

        for link in product_links:
            yield response.follow(
                urljoin(response.url, link),
                callback=self.parse_product,
                meta={
                    'category': response.meta['category'],
                    'dont_merge_cookies': False,
                    'handle_httpstatus_list': [403, 429, 503],
                    'cookiejar': response.meta.get('cookiejar')
                },
                errback=self.errback,
                priority=2
            )

        next_page = response.css('a.pagination__next::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_category,
                meta={
                    'category': response.meta['category'],
                    'dont_merge_cookies': False,
                    'handle_httpstatus_list': [403, 429, 503],
                    'cookiejar': response.meta.get('cookiejar')
                },
                errback=self.errback,
                priority=0
            )

    def parse_product(self, response):
        if self._is_blocked(response):
            self.logger.warning(f"Обнаружена блокировка для {response.url}")
            return

        item = ProductItem()
        item['url'] = response.url
        item['categories'] = [response.meta['category']]
        item['timestamp'] = datetime.now().isoformat()

        # XPath селекторы
        item['name'] = response.xpath("//h1[contains(@class, 'product-info__title')]/text()").get('').strip()

        price = response.xpath("//span[contains(@class, 'price-with-sale__new')]/text()").get()
        try:
            item['price'] = float(price.replace(' ', '').replace('₽', '').strip()) if price else None
        except (ValueError, AttributeError):
            item['price'] = None

        item['code'] = response.xpath("//div[contains(@class, 'more-details-popup__icon--flex')]/text()").get(
            '').strip()

        description = response.xpath("//div[contains(@class, 'product-description')]//text()").getall()
        item['description'] = ' '.join([t.strip() for t in description if t.strip()]) or None

        specs = response.xpath(
            '//div[contains(@class, "more-details-popup_") and contains(@class, "info-table")]//text()').getall()
        item['specifications'] = [spec.strip() for spec in specs if spec.strip()] or None

        item['images'] = [
            urljoin(response.url, img)
            for img in response.xpath('//gj-image/picture/img/@src').getall()
            if img
        ]

        if not item['name'] or not item['price']:
            self.logger.warning(f"Отсутствуют ключевые данные для {response.url}")
            return

        yield item

    def _is_blocked(self, response):
        blocked_indicators = [
            "xpvnsulc" in response.url,
            "access denied" in response.text.lower(),
            "captcha" in response.text.lower(),
            "доступ ограничен" in response.text.lower(),
            response.status in [403, 429, 503],
            "cloudflare" in response.text.lower(),
            "security check" in response.text.lower(),
            "DDoS protection" in response.text.lower(),
            "bot" in response.text.lower(),
            "Please verify you are a human" in response.text
        ]
        return any(blocked_indicators)

    def _handle_blocked(self, response):
        retry_times = response.meta.get('retry_times', 0)
        max_retry_times = response.meta.get('max_retry_times', 3)

        if retry_times < max_retry_times:
            delay = self.retry_delays[min(retry_times, len(self.retry_delays) - 1)] * random.uniform(0.9, 1.1)
            self.logger.warning(
                f"Обнаружена блокировка для {response.url}, повторная попытка через {delay:.1f}с ({retry_times + 1}/{max_retry_times})")
            time.sleep(delay)
            yield self._retry_request(response)
        else:
            self.logger.error(f"Достигнуто максимальное количество попыток для {response.url}")
            self.failed_urls.append(response.url)

    def _retry_request(self, response):
        retry_times = response.meta.get('retry_times', 0) + 1

        return response.request.replace(
            meta={
                **response.meta,
                'retry_times': retry_times,
                'dont_filter': True
            }
        )

    def errback(self, failure):
        url = failure.request.url
        self.logger.error(f"Ошибка запроса: {url} - {failure.value}")
        self.failed_urls.append(url)

        if hasattr(failure.value, 'response'):
            self.logger.error(f"Статус ответа: {failure.value.response.status}")
            self.logger.debug(f"Заголовки ответа: {failure.value.response.headers}")
            self.logger.debug(f"Тело ответа (первые 500 символов): {failure.value.response.text[:500]}")

    def closed(self, reason):
        self.logger.info(f"Паук завершен: {reason}")
        if self.failed_urls:
            self.logger.warning(f"Неудачные URL: {len(self.failed_urls)}")
            for url in self.failed_urls[:10]:
                self.logger.debug(f"- {url}")