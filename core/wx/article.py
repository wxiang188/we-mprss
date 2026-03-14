"""
微信公众号文章解析模块 - 使用 Playwright 浏览器获取
复刻原项目 driver/wxarticle.py 的逻辑

支持同步和异步两种模式：
- 同步模式：使用 PlaywrightController
- 异步模式：使用 PlaywrightAsyncController（用于 FastAPI 等 asyncio 环境）
"""
import re
import base64
import time
import asyncio
import threading
from typing import Optional, Dict, Any

from driver.playwright_driver import PlaywrightController, get_playwright_async


class WeChatArticleFetcher:
    """微信公众号文章获取器 - 使用 Playwright 浏览器（同步版本）"""

    def __init__(self):
        self.controller = None
        self.page = None

    def start_browser(self):
        """启动浏览器"""
        self.controller = PlaywrightController()
        try:
            self.controller.start_browser(headless=True)
            self.page = self.controller.page
        except Exception as e:
            print(f"启动浏览器失败: {e}")
            self.controller = None
            self.page = None
            raise e

    def close(self):
        """关闭浏览器"""
        if self.controller:
            self.controller.Close()
            self.controller = None
            self.page = None

    def get_mp_info(self, url: str) -> Dict[str, Any]:
        """获取公众号信息 - 复刻原项目逻辑（同步版本）

        Args:
            url: 微信文章链接

        Returns:
            公众号信息字典
        """
        info = {
            "mp_name": "",
            "mp_cover": "",
            "mp_intro": "",
            "biz": "",
            "mp_id": "",
            "article_url": url,
            "article_id": "",
            "title": "",
            "author": "",
            "publish_time": ""
        }

        try:
            # 启动浏览器
            if not self.page:
                self.start_browser()

            if not self.page:
                return {"error": "浏览器启动失败", **info}

            print(f"正在打开文章: {url}")
            self.controller.open_url(url)

            # 等待页面加载
            time.sleep(2)

            # 检查是否需要验证
            body = self.page.locator("body").text_content()
            if "当前环境异常" in body or "验证" in body:
                info["error"] = "需要微信环境验证"
                return info

            # 获取公众号名称 - 使用多种选择器
            name_selectors = [
                '#js_wx_follow_nickname',  # 关注栏昵称
                '.profile_nickname',         # 个人资料页昵称
                '.account_nickname',         # 账号昵称
                '#js_like_profile_bar .wx_follow_avatar + .wx_follow_info .nickname',  # 关注栏
                '.wx_follow_avatar + .wx_follow_info .nickname'  # 关注信息
            ]

            mp_name = ""
            for sel in name_selectors:
                try:
                    ele = self.page.locator(sel)
                    if ele.count() > 0:
                        text = ele.first.text_content(timeout=3000)
                        if text:
                            mp_name = text.strip()
                            if mp_name:
                                break
                except:
                    continue

            # 如果选择器失败，尝试从 JavaScript 变量获取
            if not mp_name:
                try:
                    mp_name = self.page.evaluate('''
                        () => {
                            // 尝试多种方式获取公众号名称
                            const nick = document.querySelector('#js_wx_follow_nickname');
                            if (nick) return nick.textContent.trim();

                            const profile = document.querySelector('.profile_nickname');
                            if (profile) return profile.textContent.trim();

                            // 从页面中查找包含"公众号"的元素
                            const elements = document.querySelectorAll('*');
                            for (const el of elements) {
                                if (el.classList && el.classList.contains('nickname')) {
                                    const text = el.textContent.trim();
                                    if (text) return text;
                                }
                            }
                            return '';
                        }
                    ''')
                except:
                    pass

            info["mp_name"] = mp_name

            # 获取公众号头像
            logo_selectors = [
                '#js_like_profile_bar .wx_follow_avatar img',
                '.profile_avatar img',
                '#js_profile_qrcode img',
                'img.avatar',
                '.wx_follow_avatar img'
            ]

            mp_cover = ""
            for sel in logo_selectors:
                try:
                    ele = self.page.locator(sel)
                    if ele.count() > 0:
                        src = ele.first.get_attribute('src', timeout=3000)
                        if src:
                            mp_cover = src
                            if not mp_cover.startswith('data:'):
                                break
                except:
                    continue

            # 如果选择器失败，尝试从 JavaScript 获取
            if not mp_cover:
                try:
                    mp_cover = self.page.evaluate('''
                        () => {
                            const img = document.querySelector('#js_like_profile_bar .wx_follow_avatar img');
                            if (img) return img.src || img.getAttribute('data-src') || '';

                            const avatar = document.querySelector('.profile_avatar img');
                            if (avatar) return avatar.src || avatar.getAttribute('data-src') || '';

                            return '';
                        }
                    ''')
                except:
                    pass

            info["mp_cover"] = mp_cover

            # 获取 biz 参数
            try:
                biz = self.page.evaluate('''() => window.biz || '' ''')
                if not biz:
                    # 尝试从页面源码中提取
                    content = self.page.content()
                    biz_match = re.search(r'window\.__biz=([^&"\']+)', content)
                    if biz_match:
                        biz = biz_match.group(1)
                    else:
                        biz_match = re.search(r'var\s+biz\s*=\s*["\']([^"\']+)["\']', content)
                        if biz_match:
                            biz = biz_match.group(1)

                info["biz"] = biz

                # 生成 mp_id
                if biz:
                    try:
                        # 尝试 base64 解码
                        info["mp_id"] = "MP_WXS_" + base64.b64decode(biz).decode("utf-8")
                    except:
                        info["mp_id"] = "MP_WXS_" + biz
            except Exception as e:
                print(f"获取 biz 失败: {e}")

            # 获取文章信息
            try:
                # 文章标题
                title = self.page.locator('meta[property="og:title"]').get_attribute('content', timeout=2000)
                if not title:
                    title = self.page.title()
                info["title"] = title or ""

                # 作者
                info["author"] = self.page.locator('meta[property="og:article:author"]').get_attribute('content', timeout=2000) or ""

                # 发布时间
                try:
                    publish_time = self.page.locator("#publish_time").text_content(timeout=2000)
                    info["publish_time"] = publish_time.strip()
                except:
                    pass

                # 文章ID
                article_id_match = re.search(r'/s/([^/?]+)', url)
                if article_id_match:
                    info["article_id"] = article_id_match.group(1)

            except Exception as e:
                print(f"获取文章信息失败: {e}")

        except Exception as e:
            info["error"] = str(e)
            print(f"获取公众号信息失败: {e}")

        finally:
            self.close()

        return info


class WeChatArticleFetcherAsync:
    """微信公众号文章获取器 - 使用 Playwright 浏览器（异步版本，用于 FastAPI）"""

    def __init__(self):
        self.controller = None
        self.page = None

    async def start_browser(self):
        """启动浏览器（异步）"""
        self.controller = get_playwright_async()
        try:
            if self.controller.isClose or not self.controller.page:
                await self.controller.start_browser(headless=True)
            self.page = self.controller.page
        except Exception as e:
            print(f"启动异步浏览器失败: {e}")
            self.controller = None
            self.page = None
            raise e

    async def close(self):
        """关闭浏览器（异步）"""
        # 不关闭全局实例，让它复用
        pass

    async def get_mp_info(self, url: str) -> Dict[str, Any]:
        """获取公众号信息（异步版本）

        Args:
            url: 微信文章链接

        Returns:
            公众号信息字典
        """
        info = {
            "mp_name": "",
            "mp_cover": "",
            "mp_intro": "",
            "biz": "",
            "mp_id": "",
            "article_url": url,
            "article_id": "",
            "title": "",
            "author": "",
            "publish_time": ""
        }

        try:
            # 启动/获取浏览器
            if not self.page:
                await self.start_browser()

            if not self.page:
                return {"error": "浏览器启动失败", **info}

            print(f"正在打开文章: {url}")
            await self.controller.open_url(url)

            # 等待页面加载
            await asyncio.sleep(2)

            # 检查是否需要验证
            body = await self.page.locator("body").text_content()
            if "当前环境异常" in body or "验证" in body:
                info["error"] = "需要微信环境验证"
                return info

            # 获取公众号名称
            mp_name = ""
            try:
                mp_name = await self.page.eval_on_selector('#js_wx_follow_nickname', 'el => el.textContent.trim()')
            except:
                pass

            if not mp_name:
                try:
                    mp_name = await self.page.eval_on_selector('.profile_nickname', 'el => el.textContent.trim()')
                except:
                    pass

            info["mp_name"] = mp_name

            # 获取公众号头像
            mp_cover = ""
            try:
                mp_cover = await self.page.eval_on_selector('#js_like_profile_bar .wx_follow_avatar img', 'el => el.src')
            except:
                try:
                    mp_cover = await self.page.eval_on_selector('.profile_avatar img', 'el => el.src')
                except:
                    pass

            info["mp_cover"] = mp_cover

            # 获取 biz 参数
            try:
                biz = await self.page.evaluate('''() => window.biz || '' ''')
                if not biz:
                    content = await self.page.content()
                    biz_match = re.search(r'window\.__biz=([^&"\']+)', content)
                    if biz_match:
                        biz = biz_match.group(1)

                info["biz"] = biz

                if biz:
                    try:
                        info["mp_id"] = "MP_WXS_" + base64.b64decode(biz).decode("utf-8")
                    except:
                        info["mp_id"] = "MP_WXS_" + biz
            except Exception as e:
                print(f"获取 biz 失败: {e}")

            # 获取文章信息
            try:
                title = await self.page.eval_on_selector('meta[property="og:title"]', 'el => el.content')
                if not title:
                    title = await self.page.title()
                info["title"] = title or ""

                info["author"] = await self.page.eval_on_selector('meta[property="og:article:author"]', 'el => el.content') or ""

                article_id_match = re.search(r'/s/([^/?]+)', url)
                if article_id_match:
                    info["article_id"] = article_id_match.group(1)

            except Exception as e:
                print(f"获取文章信息失败: {e}")

        except Exception as e:
            info["error"] = str(e)
            print(f"获取公众号信息失败: {e}")

        finally:
            await self.close()

        return info


# 在新线程中运行同步的浏览器操作
def _run_async_browser(url: str) -> Dict[str, Any]:
    """在新线程中运行异步浏览器操作"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        fetcher = WeChatArticleFetcherAsync()
        return loop.run_until_complete(fetcher.get_mp_info(url))
    finally:
        loop.close()


def get_mp_info_by_article_async(url: str, cookies: str = "") -> Dict[str, Any]:
    """通过文章链接获取公众号信息（异步版本，用于 FastAPI）

    Args:
        url: 微信文章链接
        cookies: 可选的微信Cookie

    Returns:
        公众号信息字典
    """
    import concurrent.futures

    # 在新线程中运行异步代码
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_run_async_browser, url)
        return future.result()


def get_mp_info_by_article(url: str, cookies: str = "") -> Dict[str, Any]:
    """通过文章链接获取公众号信息 - 复刻原项目

    Args:
        url: 微信文章链接
        cookies: 可选的微信Cookie

    Returns:
        公众号信息字典
    """
    fetcher = WeChatArticleFetcher()
    try:
        return fetcher.get_mp_info(url)
    except Exception as e:
        return {
            "mp_name": "",
            "mp_cover": "",
            "mp_intro": "",
            "biz": "",
            "mp_id": "",
            "article_url": url,
            "error": str(e)
        }


# 保留原有的解析器作为备用
def parse_wechat_article(url: str, cookies: str = "") -> Optional[Dict[str, Any]]:
    """解析微信文章链接，获取公众号信息（备用方案）"""
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://mp.weixin.qq.com/",
    }
    if cookies:
        headers["Cookie"] = cookies

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        html = response.text

        # 提取公众号名称 - 避免匹配到 jsdecode 等
        mp_name = ""
        name_patterns = [
            r'id="js_wx_follow_nickname"[^>]*>([^<]+)<',
            r'class="profile_nickname"[^>]*>([^<]+)<',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, html)
            if match:
                mp_name = match.group(1).strip()
                if mp_name and not mp_name.startswith('js'):  # 过滤掉 js 开头的错误匹配
                    break

        # 如果还是匹配到 jsdecode，尝试从 JavaScript 变量获取
        if not mp_name or mp_name.startswith('js'):
            js_pattern = r'nickname["\']?\s*:\s*["\']([^"\']+)["\']'
            match = re.search(js_pattern, html)
            if match:
                mp_name = match.group(1).strip()

        # 提取公众号头像
        mp_cover = ""
        cover_patterns = [
            r'class="wx_follow_avatar"[^>]*src="([^"]+)"',
            r'class="profile_avatar"[^>]*src="([^"]+)"',
        ]
        for pattern in cover_patterns:
            match = re.search(pattern, html)
            if match:
                mp_cover = match.group(1)
                if mp_cover.startswith('//'):
                    mp_cover = 'https:' + mp_cover
                break

        # 提取 biz
        biz = ""
        biz_match = re.search(r'window\.__biz=([^&]+)', html)
        if biz_match:
            biz = biz_match.group(1)
        else:
            biz_match = re.search(r'var\s+biz\s*=\s*"([^"]+)"', html)
            if biz_match:
                biz = biz_match.group(1)

        # 生成 mp_id
        mp_id = ""
        if biz:
            try:
                mp_id = "MP_WXS_" + base64.b64decode(biz).decode("utf-8")
            except:
                mp_id = "MP_WXS_" + biz

        return {
            "mp_name": mp_name,
            "mp_cover": mp_cover,
            "mp_intro": "",
            "biz": biz,
            "mp_id": mp_id,
            "article_url": url,
        }

    except Exception as e:
        print(f"解析文章失败: {e}")
        return None


def get_article_content(url: str) -> str:
    """获取文章正文内容 - 复刻原项目 driver/wxarticle.py 的逻辑

    Args:
        url: 文章链接

    Returns:
        文章HTML内容
    """
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://mp.weixin.qq.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        html = response.text

        # 检查是否需要验证
        if "当前环境异常" in html or "完成验证后即可继续访问" in html:
            print("需要微信环境验证")
            return ""

        # 提取文章内容 - id="js_content"
        match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.DOTALL)
        if match:
            content = match.group(1)
            # 清理内容
            content = clean_article_content(content)
            return content

        return ""

    except Exception as e:
        print(f"获取文章内容失败: {e}")
        return ""


def clean_article_content(html_content: str) -> str:
    """清理文章内容，去除无关元素

    Args:
        html_content: 原始HTML内容

    Returns:
        清理后的HTML内容
    """
    if not html_content:
        return ""

    # 移除脚本标签
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # 移除样式标签
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # 移除注释
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)

    # 移除空白字符
    html_content = re.sub(r'\s+', ' ', html_content)

    return html_content
