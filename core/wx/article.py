"""微信公众号文章解析模块"""
import re
import json
import requests
from typing import Optional, Dict, Any


class WeChatArticleParser:
    """微信公众号文章解析器"""

    def __init__(self, cookies: str = ""):
        self.cookies = cookies
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp.weixin.qq.com/",
        }
        if cookies:
            self.headers["Cookie"] = cookies

    def parse_article_url(self, url: str) -> Optional[Dict[str, Any]]:
        """解析文章链接，提取公众号信息"""
        try:
            # 从URL中提取文章ID
            # 格式: https://mp.weixin.qq.com/s/xxx 或 https://mp.weixin.qq.com/s?id=xxx
            article_id = self._extract_article_id(url)
            if not article_id:
                return None

            # 访问文章页面获取公众号信息
            # 注意：这里需要微信Cookie才能获取完整信息
            # 这里返回模拟数据，实际需要通过其他方式获取
            return self._get_mp_info_from_article(url, article_id)

        except Exception as e:
            print(f"解析文章链接失败: {e}")
            return None

    def _extract_article_id(self, url: str) -> Optional[str]:
        """从URL中提取文章ID"""
        # 匹配 pattern: /s/xxx
        match = re.search(r'/s/([^/?]+)', url)
        if match:
            return match.group(1)

        # 匹配 pattern: ?id=xxx
        match = re.search(r'[?&]id=([^&]+)', url)
        if match:
            return match.group(1)

        return None

    def _get_mp_info_from_article(self, url: str, article_id: str) -> Dict[str, Any]:
        """从文章页面获取公众号信息"""
        # 尝试获取文章页面
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            html = response.text

            # 提取公众号名称
            mp_name = self._extract_mp_name(html)

            # 提取公众号头像
            mp_cover = self._extract_mp_avatar(html)

            # 提取公众号简介
            mp_intro = self._extract_mp_intro(html)

            # 提取公众号ID (fakeid)
            mp_id = self._extract_mp_id(html)

            if not mp_name:
                raise Exception("无法获取公众号名称")

            return {
                "mp_name": mp_name,
                "mp_cover": mp_cover or "",
                "mp_intro": mp_intro or "",
                "mp_id": mp_id or "",
                "article_url": url,
                "article_id": article_id
            }

        except Exception as e:
            # 如果无法获取，返回基本信息
            return {
                "mp_name": "未知公众号",
                "mp_cover": "",
                "mp_intro": "",
                "mp_id": "",
                "article_url": url,
                "article_id": article_id,
                "error": str(e)
            }

    def _extract_mp_name(self, html: str) -> str:
        """提取公众号名称"""
        # 尝试从HTML中提取
        patterns = [
            r'var\s+nick_name\s*=\s*"([^"]+)"',
            r'nick_name["\s:]+([^",\s]+)',
            r'id="js_nick_name"[^>]*>([^<]+)<',
            r'公众号[：:]\s*([^<\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_mp_avatar(self, html: str) -> str:
        """提取公众号头像"""
        patterns = [
            r'var\s+head_img\s*=\s*"([^"]+)"',
            r'head_img["\s:]+([^",\s]+)',
            r'<img[^>]+class="[^"]*avatar[^"]*"[^>]+src="([^"]+)"',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                url = match.group(1)
                # 处理相对路径
                if url.startswith('//'):
                    url = 'https:' + url
                return url

        return ""

    def _extract_mp_intro(self, html: str) -> str:
        """提取公众号简介"""
        patterns = [
            r'var\s+intro\s*=\s*"([^"]+)"',
            r'intro["\s:]+([^",\s]+)',
            r'简介[：:]\s*([^<\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_mp_id(self, html: str) -> str:
        """提取公众号fakeid"""
        patterns = [
            r'var\s+fakeid\s*=\s*"([^"]+)"',
            r'fakeId["\s:]+([^",\s]+)',
            r'data-fakeid="([^"]+)"',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1).strip()

        return ""


def parse_wechat_article(url: str, cookies: str = "") -> Optional[Dict[str, Any]]:
    """解析微信文章链接，获取公众号信息"""
    parser = WeChatArticleParser(cookies)
    return parser.parse_article_url(url)
