import time
import logging
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from scrapy import Request


class WebdriverCookieMiddleware:
    def __init__(self, driver_arguments, url, update_every, driver_wait_time=30):
        self.url = url
        self.cookies = {}
        self.user_agent = ""
        self.last_updated = 0
        self.time_to_update = update_every
        self.driver_wait_time = driver_wait_time
        self.driver_arguments = driver_arguments
        self.logger = logging.getLogger(__name__)
        self.ua = UserAgent()
        self.driver = None
        self._initialize_driver()

    def _initialize_options(self):
        options = ChromeOptions()

        basic_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--lang=ru-RU",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--disable-notifications",
            "--remote-debugging-port=9222"
        ]

        for arg in basic_args:
            options.add_argument(arg)

        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
        options.add_argument(f"user-agent={user_agent}")

        return options

    def _initialize_driver(self):
        try:
            if self.driver is not None:
                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.error(f"Ошибка при закрытии старого драйвера: {str(e)}")

            options = self._initialize_options()
            self.driver = uc.Chrome(
                options=options,
                version_main=137  # Указываем основную версию Chrome
            )

            # Скрытие автоматизации
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })

            self.logger.info("WebDriver успешно инициализирован")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка инициализации WebDriver: {str(e)}")
            if hasattr(self, 'driver') and self.driver is not None:
                try:
                    self.driver.quit()
                except:
                    pass
            return False

    def update_cookies(self):
        try:
            if not self._initialize_driver():
                raise Exception("Не удалось инициализировать WebDriver")

            self.logger.info(f"Попытка доступа к: {self.url}")

            self.driver.get(self.url)

            WebDriverWait(self.driver, self.driver_wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body')))

            # Случайная задержка для имитации пользователя
            time.sleep(random.uniform(2, 5))

            if "gloria-jeans" not in self.driver.current_url:
                raise Exception("Не удалось загрузить правильную страницу")

            cookies = self.driver.get_cookies()
            if not cookies:
                raise Exception("Не получены cookies")

            self.cookies = {c['name']: c['value'] for c in cookies}
            self.user_agent = self.driver.execute_script("return navigator.userAgent")
            self.last_updated = time.time()

            self.headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                'Referer': self.url,
                'Sec-Ch-Ua': '"Google Chrome";v="137", "Chromium";v="137", "Not=A?Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"'
            }

            return True

        except Exception as e:
            self.logger.error(f"Ошибка обновления cookies: {str(e)}")
            if hasattr(self, 'driver') and self.driver is not None:
                try:
                    self.driver.quit()
                except:
                    pass
            return False

    def process_request(self, request, spider):
        if request.url != self.url:
            return None

        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            if self.update_cookies():
                break
            retry_count += 1
            time.sleep(10)
        else:
            spider.logger.error("Не удалось обновить cookies после попыток")
            return None

        request.cookies = self.cookies
        request.headers.update(self.headers)
        return None

    def spider_closed(self, spider):
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Ошибка при закрытии драйвера: {str(e)}")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            driver_arguments=[],
            url=crawler.settings.get("UPDATE_COOKIE_URL", "https://www.gloria-jeans.ru/"),
            update_every=crawler.settings.getint("UPDATE_COOKIES_EVERY_S", 300),
            driver_wait_time=crawler.settings.getint("DRIVER_UPDATE_WAIT_TIME", 30)
        )