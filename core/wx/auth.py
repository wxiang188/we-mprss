"""
微信公众号扫码授权模块
完全复刻自原项目 driver/wx_api.py
"""
import os
import time
import json
import base64
import re
import threading
from threading import Timer
import requests
from typing import Optional, Dict, Any, Callable
from PIL import Image
from io import BytesIO
from sqlalchemy import true

import logging
logger = logging.getLogger(__name__)

def print_info(msg):
    print(f"[INFO] {msg}")

def print_success(msg):
    print(f"[SUCCESS] {msg}")

def print_warning(msg):
    print(f"[WARNING] {msg}")


class WeChatAuth:
    """微信公众平台扫码授权类 - 完全复刻原项目实现"""

    def __init__(self):
        self.base_url = "https://mp.weixin.qq.com"
        self.login_url = f"{self.base_url}/"
        self.home_url = f"{self.base_url}/cgi-bin/home"

        self.session = requests.Session()
        self.token = None
        self.cookies = {}
        self.fingerprint = self._generate_uuid()
        self.qr_code_path = "static/wx_qrcode.png"

        self.is_logged_in = False
        self._islogin = False

        # 回调函数
        self.login_callback = None
        self.notice_callback = None

        # 线程安全
        self._lock = threading.Lock()

        # 确保目录存在
        self.qr_code_path = os.path.abspath("static/wx_qrcode.png")
        os.makedirs(os.path.dirname(self.qr_code_path), exist_ok=True)
        os.makedirs("data", exist_ok=True)

        # 设置更完整的浏览器请求头 (复刻原项目)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Referer': 'https://mp.weixin.qq.com/'
        })

    def _generate_uuid(self) -> str:
        """生成UUID"""
        import uuid
        return str(uuid.uuid4()).replace('-', '')

    def get_qr_code(self) -> Dict[str, Any]:
        """获取登录二维码"""
        try:
            # 获取登录页面
            response = self.session.get(self.login_url)
            response.raise_for_status()

            # 解析页面获取二维码相关信息
            qr_info = self._extract_qr_info(response.text)

            if qr_info:
                # 生成二维码图片
                self._generate_qr_image(qr_info['qr_url'])

                # 启动登录状态检查
                self._start_login_check(qr_info['uuid'])

                return {
                    "code": self._get_qr_base64(),
                    "uuid": qr_info['uuid'],
                    "msg": "请使用微信扫描二维码登录"
                }
            else:
                return {
                    "code": None,
                    "msg": "获取二维码失败"
                }

        except Exception as e:
            print_warning(f"获取二维码失败: {e}")
            return {"code": None, "msg": f"获取二维码失败: {str(e)}"}

    def _get_qr_base64(self) -> str:
        """获取二维码Base64"""
        try:
            if os.path.exists(self.qr_code_path):
                with open(self.qr_code_path, "rb") as f:
                    return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except Exception as e:
            logger.error(f"获取二维码Base64失败: {e}")
        return ""

    def _extract_qr_info(self, html_content: str) -> Optional[Dict[str, str]]:
        """从HTML内容中提取二维码信息"""
        try:
            # 查找二维码URL - 从HTML中提取
            # 格式: https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=getqrcode&param=2200
            qr_pattern = r'(https?:\/\/mp\.weixin\.qq.com\/cgi-bin\/loginqrcode\?action=getqrcode&param=\d+)'
            qr_match = re.search(qr_pattern, html_content)

            # 查找UUID - 从HTML中提取
            # 格式: uuid: "xxx"
            uuid_pattern = r'(?:"|\')uuid(?:"|\')\s*:\s*(?:"|\')([^"\']+)(?:"|\')'
            uuid_match = re.search(uuid_pattern, html_content)

            if qr_match and uuid_match:
                return {
                    'qr_url': qr_match.group(1),
                    'uuid': uuid_match.group(1)
                }

            # 如果没有找到，尝试其他方式获取
            return self._get_qr_info_api()

        except Exception as e:
            print_warning(f"解析二维码信息失败: {e}")
            return None

    def _get_qr_info_api(self) -> Optional[Dict[str, str]]:
        """通过API获取二维码信息"""
        try:
            # 首先访问登录页面
            logger.info("模拟浏览器访问登录页面...")
            login_response = self.session.get(self.login_url)
            login_response.raise_for_status()

            # 设置更完整的浏览器请求头（关键！）
            browser_headers = {
                'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-origin',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.login_url
            }
            self.session.headers.update(browser_headers)

            # 启动登录流程获取UUID
            uuid = self._start_login_flow()
            if not uuid:
                uuid = self._generate_uuid()

            # 构建二维码请求URL
            timestamp = int(time.time() * 1000)
            qr_api_url = f"{self.base_url}/cgi-bin/scanloginqrcode?action=getqrcode&uuid={uuid}&random={timestamp}"

            logger.info(f"请求二维码: {qr_api_url}")
            logger.info(f"使用UUID: {uuid}")

            # 发送请求获取二维码
            response = self.session.get(qr_api_url, allow_redirects=False)

            # 检查响应状态
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')

                # 检查是否返回图片
                if 'image/' in content_type:
                    # 验证图片数据有效性
                    try:
                        Image.open(BytesIO(response.content))

                        # 保存二维码图片
                        with open(self.qr_code_path, 'wb') as f:
                            f.write(response.content)

                        logger.info(f"二维码获取成功，已保存到: {self.qr_code_path}")

                        return {
                            'qr_url': f"{qr_api_url}?",
                            'uuid': uuid
                        }

                    except Exception as e:
                        logger.error(f"验证二维码图片失败: {e}")

            # 如果API获取失败，尝试备用方式
            return {
                'qr_url': f"{self.base_url}/cgi-bin/loginqrcode?action=getqrcode&param=2200",
                'uuid': uuid
            }

        except Exception as e:
            logger.error(f"API获取二维码信息失败: {e}")
            return None

    def _start_login_flow(self) -> Optional[str]:
        """启动登录流程获取UUID"""
        try:
            # 先生成UUID并存入cookies
            uuid = self._generate_uuid()
            self.session.cookies.set("uuid", uuid)

            # 调用startlogin接口
            url = f"{self.base_url}/cgi-bin/bizlogin?action=startlogin"
            fingerprint = self._generate_uuid()
            data = {
                "fingerprint": fingerprint,
                "token": "",
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
                "redirect_url": f"/cgi-bin/settingpage?t=setting/index&action=index&token=&lang=zh_CN",
                "login_type": "3",
            }
            response = self.session.post(url, data=data)

            # 从响应头或Cookie中获取UUID
            uuid = response.cookies.get('uuid') or response.headers.get('X-UUID')

            if uuid:
                return uuid

            # 如果startlogin失败，尝试prelogin
            return self._pre_login_flow()

        except Exception as e:
            logger.error(f"启动登录流程失败: {e}")
            return None

    def _pre_login_flow(self) -> Optional[str]:
        """预登录流程获取UUID"""
        try:
            uuid = self._generate_uuid()
            self.session.cookies.set("uuid", uuid)

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

            # 从响应头或Cookie中获取UUID
            uuid = response.cookies.get('uuid') or response.headers.get('X-UUID')
            return uuid if uuid else None

        except Exception as e:
            logger.error(f"预登录流程失败: {e}")
            return None

    def _generate_qr_image(self, qr_url: str):
        """生成二维码图片"""
        try:
            if qr_url.startswith('http'):
                # 如果是URL，直接请求获取图片
                response = self.session.get(qr_url)
                if response.status_code == 200 and 'image/' in response.headers.get('Content-Type', ''):
                    with open(self.qr_code_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"二维码图片已保存: {self.qr_code_path}")
                    return

            # 否则使用qrcode库生成
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # 保存二维码
            img.save(self.qr_code_path)
            logger.info(f"二维码图片已生成: {self.qr_code_path}")

        except Exception as e:
            logger.error(f"生成二维码图片失败: {e}")

    def _start_login_check(self, uuid: str):
        """启动登录状态检查"""
        def check_login():
            try:
                status = self._check_login_status(uuid)
                if status == 'success':
                    self._islogin = True
                    self._handle_login_success()
                elif status == 'waiting':
                    # 继续等待
                    Timer(2.0, check_login).start()
                elif status == 'scanned':
                    # 已扫描，等待确认
                    if self.notice_callback:
                        self.notice_callback('已扫描，请在手机上确认登录')
                    Timer(2.0, check_login).start()
                elif status == 'expired':
                    # 二维码过期
                    if self.notice_callback:
                        self.notice_callback('二维码已过期，请重新获取')
                    return
                elif status == 'exists':
                    return
                else:
                    # 继续检查
                    Timer(2.0, check_login).start()

            except Exception as e:
                logger.error(f"检查登录状态失败: {e}")
                if self.notice_callback:
                    self.notice_callback('检查登录状态失败,请重试')
                Timer(2.0, check_login).start()

        # 启动检查
        Timer(2.0, check_login).start()

    def _check_login_status(self, uuid: str) -> str:
        """检查登录状态"""
        try:
            check_url = f"{self.base_url}/cgi-bin/scanloginqrcode"
            self.fingerprint = self.cookies.get("fingerprint") or self._generate_uuid()

            params = {
                "action": "ask",
                "fingerprint": self.fingerprint,
                "lang": "zh_CN",
                "f": "json",
                "ajax": 1
            }

            # 状态轮询时也使用适当的请求头
            self.session.headers.update({
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.base_url + '/',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            })

            response = self.session.get(check_url, params=params)
            response.raise_for_status()

            # 解析响应
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                status = data.get('status', 0)

                print(f"登录状态检查: {data}")

                if status == 1:
                    self.cookies = requests.utils.dict_from_cookiejar(self.session.cookies) if self.session.cookies else {}
                    return 'success'  # 登录成功
                elif status == 2:
                    return 'scanned'  # 已扫描
                elif status == 3:
                    self.cookies = requests.utils.dict_from_cookiejar(self.session.cookies) if self.session.cookies else {}
                    return 'success'  # 登录成功
                elif status == 4:
                    return 'expired'  # 二维码过期
                else:
                    return 'waiting'  # 继续等待

            return 'waiting'

        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return 'error'

    def _handle_login_success(self):
        """处理登录成功"""
        try:
            self.is_logged_in = True

            # 提取登录信息
            self._extract_login_info()

            print_success("微信登录成功!")

            if self.login_callback:
                self.login_callback(self.get_session_info())

        except Exception as e:
            logger.error(f"处理登录失败: {e}")

    def _extract_login_info(self):
        """提取登录信息（token和cookies）"""
        try:
            # 执行登录POST请求
            login_data = {
                "userlang": "zh_CN",
                "redirect_url": "",
                "cookie_forbidden": "0",
                "cookie_cleaned": "0",
                "plugin_used": "0",
                "login_type": "3",
                "fingerprint": self.fingerprint,
                "token": "",
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1"
            }

            # 发送登录请求
            response = self.session.post(
                "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login",
                data=login_data
            )

            response.raise_for_status()
            self.cookies = requests.utils.dict_from_cookiejar(self.session.cookies) if self.session.cookies else {}

            # 从URL或页面内容中提取token
            token_match = re.search(r'token=([^&\s"\']+)', response.text)
            if token_match:
                self.token = token_match.group(1)
                logger.info(f"获取到token: {self.token}")

            # 如果URL中有token，也提取
            if 'token=' in response.url:
                token_match = re.search(r'token=([^&\s"\']+)', response.url)
                if token_match:
                    self.token = token_match.group(1)

        except Exception as e:
            logger.error(f"提取登录信息失败: {e}")

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
    # 重新初始化
    auth.__init__()
    auth.login_callback = callback
    auth.notice_callback = notice
    return auth.get_qr_code()


def check_login_status() -> Dict[str, Any]:
    """检查登录状态"""
    auth = get_wechat_auth()
    return auth.get_session_info()
