import scrapy
from urllib.parse import urljoin
from gloria_jeans.items import ProductItem
from datetime import datetime
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import CloseSpider
from twisted.internet.error import TimeoutError, TCPTimedOutError
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.web._newclient import ResponseNeverReceived
from scrapy.utils.response import response_status_message


class GloriaJeansSpider(scrapy.Spider):
    name = 'gloria_jeans'
    allowed_domains = ['gloria-jeans.ru']
    start_urls = ['https://www.gloria-jeans.ru/']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = get_project_settings()
        self.categories = self.settings.get("CATEGORIES")
        self.base_url = self.settings.get("BASE_URL")
        self.catalog_url = self.settings.get("CATALOG_URL")
        self.failed_urls = []
        self.retry_delays = [30, 60, 120, 240]

    def parse(self, response):
        for category_id, category_name in self.categories.items():
            category_url = f"{self.catalog_url}{category_id}"
            yield scrapy.Request(
                url=category_url,
                callback=self.parse_category,
                meta={
                    'category': category_name,
                    'category_id': category_id,
                    'page': 1
                },
                errback=self.handle_error
            )

    def parse_category(self, response):
        product_cards = response.xpath("//div[contains(@class, 'product-mini-card') and contains(@class, 'ng-star-inserted')]").getall()
        self.logger.info(f"Найдено карточек товаров: {len(product_cards)}, ссылок: {len(product_links)}")
        if product_cards:
            product_links = response.css('a.product-card__link::attr(href)').getall()
            if not product_links:
                product_links = response.css('div.product-card a::attr(href)').getall()

            for link in product_links:
                product_url = urljoin(self.base_url, link)
                yield scrapy.Request(
                    url=product_url,
                    callback=self.parse_product,
                    meta={'category': response.meta['category']},
                    errback=self.handle_error
                )

        current_page = response.meta.get('page', 1)
        next_page = current_page + 1
        next_page_url = f"{self.catalog_url}{response.meta['category_id']}?page={next_page}"

        if product_cards:
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_category,
                meta={
                    'category': response.meta['category'],
                    'category_id': response.meta['category_id'],
                    'page': next_page
                },
                errback=self.handle_error
            )

    def parse_product(self, response):
        if self._is_blocked(response):
            self.logger.warning("Обнаружена блокировка для URL: %s", response.url)
            yield from self._handle_blocked(response)
            return

        item = ProductItem()
        item['url'] = response.url
        item['categories'] = [response.meta['category']]
        item['timestamp'] = datetime.now().isoformat()

        item['name'] = response.xpath("//h1[contains(@class, 'product-info__title')]/text()").get('').strip()

        price = response.xpath("//span[contains(@class, 'price-with-sale__new')]/text()").get()
        try:
            item['price'] = float(price.replace(' ', '').replace('₽', '').strip()) if price else None
        except (ValueError, AttributeError) as e:
            self.logger.warning("Ошибка парсинга цены для %s: %s", response.url, str(e))
            item['price'] = None

        item['code'] = response.xpath("//div[contains(@class, 'more-details-popup__icon--flex')]/text()").get('').strip()

        description = response.xpath("//div[contains(@class, 'product-description') and contains(@class, 'ng-star-inserted')]//span[contains(@class, 'gjblocksizes')]//text()").getall()
        item['description'] = ' '.join([t.strip() for t in description if t.strip()]) or None

        specs = response.xpath('//div[contains(@class, "more-details-popup_") and contains(@class, "info-table")]//text()').getall()
        item['specifications'] = [spec.strip() for spec in specs if spec.strip()] or None

        item['images'] = [
            urljoin(response.url, img)
            for img in response.xpath('//gj-image/picture/img/@src').getall()
            if img
        ]

        if not item['name'] or not item['price']:
            self.logger.warning("Отсутствуют ключевые данные для URL: %s", response.url)
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
                "Блокировка для %s, повторная попытка через %.1fс (%d/%d)",
                response.url, delay, retry_times + 1, max_retry_times
            )
            yield self._retry_request(response)
        else:
            self.logger.error("Достигнут максимум попыток для URL: %s", response.url)
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

    def handle_error(self, failure):
        if failure.check(HttpError):
            response = failure.value.response
            if response.status == 403:
                self.logger.warning("403 Forbidden для URL: %s", response.url)
                yield from self._handle_blocked(response)
                return

            self.logger.error(
                "HttpError для URL: %s. Код статуса: %d",
                response.url,
                response.status
            )
        elif failure.check(DNSLookupError):
            self.logger.error("DNSLookupError для URL: %s", failure.request.url)
        elif failure.check((TimeoutError, TCPTimedOutError, ResponseNeverReceived)):
            self.logger.error("TimeoutError для URL: %s", failure.request.url)

        self.failed_urls.append(failure.request.url)

    def closed(self, reason):
        self.logger.info("Паук завершил работу. Причина: %s", reason)
        if self.failed_urls:
            self.logger.warning("Количество неудачных URL: %d", len(self.failed_urls))
            for url in self.failed_urls[:10]:
                self.logger.debug("Неудачный URL: %s", url)