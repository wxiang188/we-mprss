"""
微信公众号扫码授权模块
基于原项目 driver/wx_api.py 实现
"""
import os
import time
import json
import base64
import threading
import requests
from typing import Optional, Dict, Any, Callable
from PIL import Image
from io import BytesIO

import logging
logger = logging.getLogger(__name__)

def print_info(msg):
    print(f"[INFO] {msg}")

def print_success(msg):
    print(f"[SUCCESS] {msg}")

def print_warning(msg):
    print(f"[WARNING] {msg}")


class WeChatAuth:
    """微信公众平台扫码授权类"""

    def __init__(self):
        self.base_url = "https://mp.weixin.qq.com"
        self.session = requests.Session()
        self.token = None
        self.cookies = {}
        self.qr_code_path = "static/wx_qrcode.png"
        self.lock_file = "data/auth.lock"
        self.is_logged_in = False

        # 回调函数
        self.login_callback = None
        self.notice_callback = None

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://mp.weixin.qq.com/'
        })

        # 确保目录存在
        os.makedirs("static", exist_ok=True)
        os.makedirs("data", exist_ok=True)

    def get_qr_code(self) -> Dict[str, Any]:
        """获取登录二维码"""
        try:
            # 访问登录页面
            response = self.session.get(self.base_url)
            response.raise_for_status()

            # 获取UUID
            uuid = self._get_uuid()
            if not uuid:
                uuid = self._generate_uuid()

            # 生成UUID的二维码
            import qrcode
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(f"https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=getqrcode&param=2200&uuid={uuid}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # 保存二维码
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_base64 = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

            with open(self.qr_code_path, 'wb') as f:
                f.write(buffer.getvalue())

            print_info("请使用微信扫描二维码登录")

            # 启动登录状态检查线程
            threading.Thread(target=self._check_login, args=(uuid,), daemon=True).start()

            return {
                "code": qr_base64,
                "uuid": uuid,
                "msg": "请使用微信扫描二维码登录"
            }

        except Exception as e:
            print_warning(f"获取二维码失败: {e}")
            return {"code": None, "msg": f"获取二维码失败: {str(e)}"}

        # 旧的获取二维码图片方式（可能已失效）
        try:
            # 获取二维码图片
            qr_url = f"{self.base_url}/cgi-bin/scanloginqrcode?action=getqrcode&uuid={uuid}&random={int(time.time() * 1000)}"

            response = self.session.get(qr_url)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                # 保存二维码
                with open(self.qr_code_path, 'wb') as f:
                    f.write(response.content)

                # 生成Base64
                qr_base64 = f"data:image/png;base64,{base64.b64encode(response.content).decode()}"

                print_info("请使用微信扫描二维码登录")

                # 启动登录状态检查
                threading.Thread(target=self._check_login, args=(uuid,)).start()

                return {
                    "code": qr_base64,
                    "uuid": uuid,
                    "msg": "请使用微信扫描二维码登录"
                }

            return {"code": None, "msg": "获取二维码失败"}

        except Exception as e:
            print_warning(f"获取二维码失败: {e}")
            return {"code": None, "msg": str(e)}

    def _get_uuid(self) -> str:
        """获取登录UUID"""
        try:
            url = f"{self.base_url}/cgi-bin/bizlogin"
            params = {
                "action": "prelogin",
                "fingerprint": self._generate_uuid(),
                "token": "",
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1"
            }
            response = self.session.get(url, params=params)
            uuid = response.cookies.get('uuid') or response.headers.get('X-UUID')
            return uuid
        except:
            return ""

    def _generate_uuid(self) -> str:
        """生成UUID"""
        import uuid
        return str(uuid.uuid4()).replace('-', '')

    def _check_login(self, uuid: str):
        """检查登录状态"""
        check_url = f"{self.base_url}/cgi-bin/scanloginqrcode"

        while True:
            try:
                params = {
                    "action": "ask",
                    "fingerprint": self._generate_uuid(),
                    "lang": "zh_CN",
                    "f": "json",
                    "ajax": 1
                }

                response = self.session.get(check_url, params=params)
                data = response.json()

                status = data.get('status', 0)

                if status == 1 or status == 3:
                    # 登录成功
                    self.is_logged_in = True
                    self.cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
                    self._extract_token()
                    print_success("微信登录成功!")

                    if self.login_callback:
                        self.login_callback(self.get_session_info())

                    break
                elif status == 2:
                    # 已扫描，等待确认
                    if self.notice_callback:
                        self.notice_callback("已扫描，请在手机确认")
                elif status == 4:
                    if self.notice_callback:
                        self.notice_callback("二维码已过期，请重新获取")
                    break

                time.sleep(2)

            except Exception as e:
                print_warning(f"检查登录状态失败: {e}")
                break

    def _extract_token(self):
        """提取token"""
        try:
            response = self.session.get(f"{self.base_url}/cgi-bin/home")
            import re
            token_match = re.search(r'token=([^&\s"\']+)', response.url)
            if token_match:
                self.token = token_match.group(1)
        except:
            pass

    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        return {
            "is_logged_in": self.is_logged_in,
            "token": self.token,
            "cookies": self.cookies,
            "cookies_str": '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
        }

    def is_valid(self) -> bool:
        """检查登录是否有效"""
        if not self.is_logged_in or not self.token:
            return False

        try:
            response = self.session.get(f"{self.base_url}/cgi-bin/home?token={self.token}")
            return 'home' in response.url
        except:
            return False


# 全局实例
_wechat_auth = None


def get_wechat_auth() -> WeChatAuth:
    """获取微信授权实例"""
    global _wechat_auth
    if _wechat_auth is None:
        _wechat_auth = WeChatAuth()
    return _wechat_auth


def generate_qr_code(callback: Optional[Callable] = None, notice: Optional[Callable] = None) -> Dict[str, Any]:
    """生成二维码"""
    auth = get_wechat_auth()
    auth.login_callback = callback
    auth.notice_callback = notice
    return auth.get_qr_code()


def check_login_status() -> Dict[str, Any]:
    """检查登录状态"""
    auth = get_wechat_auth()
    return auth.get_session_info()
