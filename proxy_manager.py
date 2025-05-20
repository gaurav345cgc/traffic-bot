import random
import requests
from loguru import logger

class ProxyManager:
    def __init__(self, proxy_file='D:/EOXS/copy for bot/bot/backend/bot-engine/proxies.txt'):
        self.proxy_file = proxy_file
        self.proxies = []
        self.bad_proxies = set()
        self.load_proxies()

    def load_proxies(self):
        try:
            with open(self.proxy_file, 'r') as f:
                lines = f.readlines()
            self.proxies = [line.strip() for line in lines if line.strip()]
            if not self.proxies:
                logger.error("No proxies loaded. Please check proxies.txt")
            else:
                logger.info(f"Loaded {len(self.proxies)} proxies.")
        except FileNotFoundError:
            logger.error(f"Failed to load proxies: {self.proxy_file} not found.")
            self.proxies = []

    def get_random_proxy(self):
        available = [p for p in self.proxies if p not in self.bad_proxies]
        if not available:
            logger.error("No healthy proxies available.")
            return None
        proxy = random.choice(available)
        logger.info(f"Selected proxy: {proxy}")
        return proxy

    def mark_bad_proxy(self, proxy):
        logger.warning(f"Marking proxy as bad: {proxy}")
        self.bad_proxies.add(proxy)

    def parse_proxy(self, proxy_str):
        """Parse proxy string into host, port, username, and password."""
        if not proxy_str:
            logger.error("No proxy provided.")
            return None
        try:
            host, port_str, username, password = proxy_str.split(":")
            port = int(port_str)
            return {
                "host": host,
                "port": port,
                "username": username,
                "password": password
            }
        except ValueError:
            logger.error("Invalid proxy format. Use host:port:username:password")
            return None

    def check_proxy_health(self, proxy_str, test_url="https://httpbin.org/ip", timeout=7):
        """
        Check if a proxy is healthy by sending a test HTTP request through it.
        Returns True if successful, False otherwise.
        """
        proxy = self.parse_proxy(proxy_str)
        if not proxy:
            return False

        proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        try:
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                logger.info(f"Proxy {proxy_str} passed health check.")
                return True
            else:
                logger.warning(f"Proxy {proxy_str} returned status code {response.status_code}.")
        except requests.RequestException as e:
            logger.error(f"Proxy {proxy_str} health check failed: {e}")

        return False

    def get_healthy_proxy(self, max_attempts=5):
        """
        Get a random healthy proxy, retrying up to max_attempts times.
        Marks proxies as bad if they fail health check.
        """
        for _ in range(max_attempts):
            proxy = self.get_random_proxy()
            if not proxy:
                logger.error("No proxies available to test.")
                return None
            if self.check_proxy_health(proxy):
                return proxy
            else:
                self.mark_bad_proxy(proxy)
        logger.error(f"Failed to find a healthy proxy after {max_attempts} attempts.")
        return None
