"""
微信公众号 API 模块
获取公众号信息和文章
"""
import json
import time
import requests
import re
import base64
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


def search_biz(keyword: str, limit: int = 5, offset: int = 0) -> Dict[str, Any]:
    """搜索公众号 - 复刻原项目 search_Biz 函数

    Args:
        keyword: 搜索关键词
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        搜索结果字典，包含公众号列表
    """
    auth = get_wechat_auth()
    session_info = auth.get_session_info()

    if not session_info.get('is_logged_in') or not session_info.get('token'):
        return {"list": [], "total": 0, "error": "未登录或登录已过期"}

    try:
        url = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
        params = {
            "action": "search_biz",
            "begin": offset,
            "count": limit,
            "query": keyword,
            "token": session_info['token'],
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1"
        }

        headers = {
            "Cookie": session_info.get('cookies_str', ''),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp.weixin.qq.com/"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # 解析返回的公众号列表
        result_list = []
        if data.get('base_resp', {}).get('ret') == 0:
            biz_list = data.get('list', [])
            for item in biz_list:
                result_list.append({
                    "fakeid": item.get('fakeid', ''),
                    "nickname": item.get('nickname', ''),
                    "alias": item.get('alias', ''),
                    "headimg": item.get('headimg', ''),
                    "intro": item.get('intro', ''),
                    "user_name": item.get('user_name', ''),
                    "service_type": item.get('service_type', 0),
                    "verify_type": item.get('verify_type', 0)
                })

        return {
            "list": result_list,
            "total": len(result_list),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        print(f"搜索公众号失败: {e}")
        return {"list": [], "total": 0, "error": str(e)}


def extract_article_id(url: str) -> Optional[str]:
    """从微信文章URL中提取文章ID

    Args:
        url: 微信文章链接

    Returns:
        文章ID字符串
    """
    # 匹配 pattern: /s/xxx
    match = re.search(r'/s/([^/?]+)', url)
    if match:
        return match.group(1)

    # 匹配 pattern: ?id=xxx
    match = re.search(r'[?&]id=([^&]+)', url)
    if match:
        return match.group(1)

    return None


def extract_biz_from_url(url: str) -> Optional[str]:
    """从URL中提取biz参数

    Args:
        url: 文章URL

    Returns:
        biz参数值
    """
    match = re.search(r'[?&]__biz=([^&]+)', url)
    if match:
        return match.group(1)

    # 也尝试从 __biz 参数提取
    match = re.search(r'[?&]biz=([^&]+)', url)
    if match:
        return match.group(1)

    return None


def get_mp_info_by_article(url: str, cookies: str = "") -> Dict[str, Any]:
    """通过文章链接获取公众号信息 - 复刻原项目 driver/wxarticle.py 逻辑

    Args:
        url: 微信文章链接
        cookies: 可选的微信Cookie

    Returns:
        公众号信息字典
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://mp.weixin.qq.com/",
    }
    if cookies:
        headers["Cookie"] = cookies

    try:
        # 先尝试从URL中提取biz
        biz = extract_biz_from_url(url)

        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        html = response.text

        # 如果URL中没有biz，尝试从页面中提取
        if not biz:
            biz_match = re.search(r'window\.__biz=([^&]+)', html)
            if biz_match:
                biz = biz_match.group(1)
            else:
                biz_match = re.search(r'var biz = "([^"]+)"', html)
                if biz_match:
                    biz = biz_match.group(1)

        # 提取公众号名称
        mp_name = ""
        name_patterns = [
            r'var\s+nick_name\s*=\s*"([^"]+)"',
            r'id="js_wx_follow_nickname"[^>]*>([^<]+)<',
            r'class="profile_nickname"[^>]*>([^<]+)<',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, html)
            if match:
                mp_name = match.group(1).strip()
                break

        # 提取公众号头像
        mp_cover = ""
        cover_patterns = [
            r'class="wx_follow_avatar"[^>]*src="([^"]+)"',
            r'class="profile_avatar"[^>]*src="([^"]+)"',
            r'<img[^>]+class="[^"]*avatar[^"]*"[^>]+src="([^"]+)"',
        ]
        for pattern in cover_patterns:
            match = re.search(pattern, html)
            if match:
                mp_cover = match.group(1)
                if mp_cover.startswith('//'):
                    mp_cover = 'https:' + mp_cover
                break

        # 提取公众号简介
        mp_intro = ""
        intro_patterns = [
            r'var\s+intro\s*=\s*"([^"]+)"',
            r'class="profile_intro"[^>]*>([^<]+)<',
        ]
        for pattern in intro_patterns:
            match = re.search(pattern, html)
            if match:
                mp_intro = match.group(1).strip()
                break

        # 提取文章标题
        title = ""
        title_patterns = [
            r'<meta property="og:title" content="([^"]+)"',
            r'<title>([^<]+)</title>',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, html)
            if match:
                title = match.group(1).strip()
                break

        # 提取文章ID
        article_id = extract_article_id(url)

        # 构建 mp_id (与原项目一致，使用 base64 编码的 biz)
        mp_id = ""
        if biz:
            try:
                mp_id = f"MP_WXS_{base64.b64decode(biz).decode('utf-8')}"
            except:
                mp_id = f"MP_WXS_{biz}"

        return {
            "mp_name": mp_name,
            "mp_cover": mp_cover,
            "mp_intro": mp_intro,
            "biz": biz,
            "mp_id": mp_id,
            "article_url": url,
            "article_id": article_id,
            "title": title
        }

    except Exception as e:
        print(f"获取公众号信息失败: {e}")
        return {
            "mp_name": "",
            "mp_cover": "",
            "mp_intro": "",
            "biz": "",
            "mp_id": "",
            "article_url": url,
            "error": str(e)
        }
