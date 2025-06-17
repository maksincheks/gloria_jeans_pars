from scrapy import Request

class CustomHeadersMiddleware:
    def process_request(self, request, spider):
        if 'api-web.gloria-jeans.ru' in request.url:
            request.headers.update(spider.custom_headers)