import scrapy
import json
from datetime import datetime
from urllib.parse import urljoin
from scrapy.utils.project import get_project_settings


class GloriaJeansSpider(scrapy.Spider):
    name = 'gloria_jeans'
    allowed_domains = ['gloria-jeans.ru', 'api-web.gloria-jeans.ru']
    api_url = 'https://api-web.gloria-jeans.ru/api/v1/catalog/products'
    product_api_url = 'https://api-web.gloria-jeans.ru/api/v1/catalog/product'
    region_id = '0c5b2444-70a0-4932-980c-b4dc0d3f02b5'  # Москва

    custom_headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'origin': 'https://www.gloria-jeans.ru',
        'referer': 'https://www.gloria-jeans.ru/',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not=A?Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    }

    def start_requests(self):
        categories = get_project_settings().get("CATEGORIES", {})

        for category_id, category_name in categories.items():
            payload = {
                'categoryCode': category_id,
                'sort': 'new',
                'filters': {
                    'productCategories': [],
                    'targetCategories': [],
                    'targetAdditionalCategories': [],
                    'typeId': [],
                    'collectionId': [],
                    'labels': [],
                    'multiProperties': [],
                    'minPrice': None,
                    'maxPrice': None,
                    'size': [],
                    'color': [],
                    'growth': [],
                    'childAge': [],
                    'male': [],
                    'shopId': [],
                },
                'pagination': {
                    'limit': 100,
                    'page': 1,
                },
                'regionId': self.region_id,
                'cityId': self.region_id,
            }

            yield scrapy.Request(
                url=self.api_url,
                method='POST',
                headers=self.custom_headers,
                body=json.dumps(payload),
                callback=self.parse_category,
                meta={'category': category_name, 'page': 1},
                errback=self.handle_error
            )

    def parse_category(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON response from {response.url}")
            return

        products = data.get('products', [])
        self.logger.info(f"Found {len(products)} products in category {response.meta['category']}")

        for product in products:
            product_url = f"{self.product_api_url}?vendorCodeCc={product['vendorCodeCc']}&regionId={self.region_id}&cityId={self.region_id}"
            yield scrapy.Request(
                url=product_url,
                headers=self.custom_headers,
                callback=self.parse_product,
                meta={'category': response.meta['category']},
                errback=self.handle_error
            )

        # Pagination
        if products and len(products) == 100:
            next_page = response.meta['page'] + 1
            payload = json.loads(response.request.body)
            payload['pagination']['page'] = next_page

            yield scrapy.Request(
                url=self.api_url,
                method='POST',
                headers=self.custom_headers,
                body=json.dumps(payload),
                callback=self.parse_category,
                meta={'category': response.meta['category'], 'page': next_page},
                errback=self.handle_error
            )

    def parse_product(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON response from {response.url}")
            return

        product = data.get('product', {})
        if not product:
            return

        item = {
            'url': f"https://www.gloria-jeans.ru{product.get('url', '')}",
            'categories': [response.meta['category']],
            'timestamp': datetime.now().isoformat(),
            'name': product.get('name', ''),
            'price': product.get('price', {}).get('value'),
            'old_price': product.get('oldPrice', {}).get('value'),
            'code': product.get('vendorCodeCc', ''),
            'color': product.get('color', ''),
            'sizes': [size.get('value') for size in product.get('sizes', [])],
            'composition': product.get('composition', ''),
            'description': product.get('description', ''),
            'images': [media['url'] for media in product.get('media', []) if media.get('type') == 'image'],
            'attributes': [
                f"{attr['name']}: {attr['value']}"
                for attr in product.get('attributes', [])
                if attr.get('name') and attr.get('value')
            ],
        }
        yield item

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.getErrorMessage()}")