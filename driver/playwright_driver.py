"""
Playwright 浏览器控制器
复刻原项目 driver/playwright_driver.py

支持同步和异步两种模式：
- 同步模式：用于非 asyncio 环境
- 异步模式：用于 FastAPI 等 asyncio 环境
"""
import os
import sys
import json
import random
import uuid
import asyncio
import platform
import threading


class PlaywrightController:
    """Playwright 浏览器控制器（同步版本）- 非 asyncio 环境使用"""

    def __init__(self):
        self.system = platform.system().lower()
        self.driver = None
        self.browser = None
        self.context = None
        self.page = None
        self.isClose = True

    def is_browser_started(self):
        """检测浏览器是否已启动"""
        return (not self.isClose and
                self.driver is not None and
                self.browser is not None and
                self.context is not None and
                self.page is not None)

    def start_browser(self, headless=True, mobile_mode=False):
        """启动浏览器"""
        try:
            # 检查环境变量
            if os.getenv("NOT_HEADLESS") == "True":
                headless = False
            else:
                headless = True

            if self.system != "windows":
                headless = True

            # 设置事件循环
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            from playwright.sync_api import sync_playwright
            self.driver = sync_playwright().start()

            # 选择浏览器
            browser_name = os.getenv("BROWSER_TYPE", "chromium").lower()
            if browser_name == "firefox":
                browser_type = self.driver.firefox
            elif browser_name == "webkit":
                browser_type = self.driver.webkit
            else:
                browser_type = self.driver.chromium

            # 启动选项
            launch_options = {"headless": headless}
            if self.system == "windows":
                launch_options["handle_sigint"] = False
                launch_options["handle_sigterm"] = False
                launch_options["handle_sighup"] = False

            self.browser = browser_type.launch(**launch_options)

            # 创建上下文
            context_options = {
                "locale": "zh-CN",
                "viewport": {"width": 1280, "height": 720},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            self.context = self.browser.new_context(**context_options)
            self.page = self.context.new_page()

            # 反爬虫脚本
            self._apply_anti_crawler_scripts()

            self.isClose = False
            return self.page

        except Exception as e:
            print(f"启动浏览器失败: {e}")
            self.cleanup()
            raise Exception(f"启动浏览器失败: {str(e)}")

    def _apply_anti_crawler_scripts(self):
        """应用反爬虫脚本"""
        self.page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        Object.defineProperty(window, 'chrome', {
            get: () => false,
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en'],
        });
        """)

    def open_url(self, url, wait_until="domcontentloaded"):
        """打开URL"""
        try:
            self.page.goto(url, wait_until=wait_until, timeout=30000)
        except Exception as e:
            raise Exception(f"打开URL失败: {str(e)}")

    def add_cookies(self, cookies):
        """添加Cookie"""
        if self.context is None:
            raise Exception("浏览器未启动")
        self.context.add_cookies(cookies)

    def get_cookies(self):
        """获取Cookie"""
        if self.context is None:
            raise Exception("浏览器未启动")
        return self.context.cookies()

    def Close(self):
        """关闭浏览器"""
        self.cleanup()

    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'page') and self.page:
                self.page.close()
            if hasattr(self, 'context') and self.context:
                self.context.close()
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'driver') and self.driver:
                self.driver.stop()
            self.isClose = True
        except Exception as e:
            print(f"资源清理失败: {e}")


class PlaywrightAsyncController:
    """Playwright 异步浏览器控制器 - 用于 asyncio 环境（如 FastAPI）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式，确保全局只有一个浏览器实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.system = platform.system().lower()
        self.driver = None
        self.browser = None
        self.context = None
        self.page = None
        self.isClose = True
        self._initialized = True

    async def start_browser(self, headless=True, mobile_mode=False):
        """启动浏览器（异步）"""
        try:
            # 检查环境变量
            if os.getenv("NOT_HEADLESS") == "True":
                headless = False
            else:
                headless = True

            if self.system != "windows":
                headless = True

            # 使用异步 API
            from playwright.async_api import async_playwright
            self.driver = await async_playwright().start()

            # 选择浏览器
            browser_name = os.getenv("BROWSER_TYPE", "chromium").lower()
            if browser_name == "firefox":
                browser_type = self.driver.firefox
            elif browser_name == "webkit":
                browser_type = self.driver.webkit
            else:
                browser_type = self.driver.chromium

            # 启动选项
            launch_options = {"headless": headless}
            if self.system == "windows":
                launch_options["handle_sigint"] = False
                launch_options["handle_sigterm"] = False
                launch_options["handle_sighup"] = False

            self.browser = await browser_type.launch(**launch_options)

            # 创建上下文
            context_options = {
                "locale": "zh-CN",
                "viewport": {"width": 1280, "height": 720},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()

            # 反爬虫脚本
            await self._apply_anti_crawler_scripts()

            self.isClose = False
            print("异步浏览器启动成功")
            return self.page

        except Exception as e:
            print(f"启动异步浏览器失败: {e}")
            await self.cleanup()
            raise Exception(f"启动浏览器失败: {str(e)}")

    async def _apply_anti_crawler_scripts(self):
        """应用反爬虫脚本（异步）"""
        await self.page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        Object.defineProperty(window, 'chrome', {
            get: () => false,
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en'],
        });
        """)

    async def open_url(self, url, wait_until="domcontentloaded"):
        """打开URL（异步）"""
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=30000)
        except Exception as e:
            raise Exception(f"打开URL失败: {str(e)}")

    async def add_cookies(self, cookies):
        """添加Cookie（异步）"""
        if self.context is None:
            raise Exception("浏览器未启动")
        await self.context.add_cookies(cookies)

    async def get_cookies(self):
        """获取Cookie（异步）"""
        if self.context is None:
            raise Exception("浏览器未启动")
        return await self.context.cookies()

    async def close(self):
        """关闭浏览器（异步）"""
        await self.cleanup()

    async def cleanup(self):
        """清理资源（异步）"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.driver:
                await self.driver.stop()
            self.isClose = True
        except Exception as e:
            print(f"异步资源清理失败: {e}")


def get_playwright_async():
    """获取异步 Playwright 控制器实例"""
    return PlaywrightAsyncController()
