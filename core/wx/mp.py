"""
微信公众号 API 模块
获取公众号信息和文章
"""
import json
import time
import requests
from typing import Optional, Dict, Any, List

from core.config import cfg
from core.wx.auth import get_wechat_auth


class WeChatMP:
    """微信公众号操作类"""

    def __init__(self):
        self.base_url = "https://mp.weixin.qq.com"
        self.session = requests.Session()
        self.token = None

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://mp.weixin.qq.com/'
        })

    def set_auth(self, token: str, cookies: Dict[str, str]):
        """设置授权信息"""
        self.token = token
        self.session.cookies.update(cookies)

    def get_account_list(self) -> List[Dict[str, Any]]:
        """获取公众号账号列表"""
        if not self.token:
            return []

        try:
            url = f"{self.base_url}/cgi-bin/switchacct"
            params = {
                'action': 'get_acct_list',
                'fingerprint': self._generate_fingerprint(),
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1'
            }

            response = self.session.get(url, params=params)
            data = response.json()

            if 'biz_list' in data and 'list' in data['biz_list']:
                return data['biz_list']['list']

        except Exception as e:
            print(f"获取账号列表失败: {e}")

        return []

    def get_article_list(self, fakeid: str, begin: int = 0, count: int = 5) -> List[Dict[str, Any]]:
        """获取公众号文章列表"""
        if not self.token:
            return []

        try:
            url = f"{self.base_url}/cgi-bin/appmsg"
            params = {
                "action": "list_ex",
                "begin": begin,
                "count": count,
                "fakeid": fakeid,
                "type": "9",
                "token": self.token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1"
            }

            response = self.session.get(url, params=params)
            data = response.json()

            if data.get('base_resp', {}).get('ret') == 0 and 'app_msg_list' in data:
                return data['app_msg_list']

        except Exception as e:
            print(f"获取文章列表失败: {e}")

        return []

    def get_article_content(self, url: str) -> str:
        """获取文章详细内容"""
        try:
            response = self.session.get(url)
            response.encoding = 'utf-8'

            # 简单提取文章内容（实际需要更复杂的解析）
            import re
            # 提取 id="js_content" 里面的内容
            match = re.search(r'id="js_content"[^>]*>(.*?)</div>', response.text, re.DOTALL)
            if match:
                return match.group(1)

        except Exception as e:
            print(f"获取文章内容失败: {e}")

        return ""

    def _generate_fingerprint(self) -> str:
        """生成指纹"""
        import uuid
        return str(uuid.uuid4()).replace('-', '')


def get_mp_list() -> List[Dict[str, Any]]:
    """获取公众号列表（快捷函数）"""
    auth = get_wechat_auth()
    session_info = auth.get_session_info()

    if not session_info.get('is_logged_in'):
        return []

    mp = WeChatMP()
    mp.set_auth(session_info['token'], session_info['cookies'])
    return mp.get_account_list()


def get_mp_articles(fakeid: str, max_count: int = 10) -> List[Dict[str, Any]]:
    """获取公众号文章（快捷函数）"""
    auth = get_wechat_auth()
    session_info = auth.get_session_info()

    if not session_info.get('is_logged_in'):
        return []

    mp = WeChatMP()
    mp.set_auth(session_info['token'], session_info['cookies'])

    articles = []
    begin = 0
    count = 5

    while len(articles) < max_count:
        batch = mp.get_article_list(fakeid, begin, count)
        if not batch:
            break
        articles.extend(batch)
        begin += count

    return articles[:max_count]
