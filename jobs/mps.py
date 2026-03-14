"""
公众号爬取任务模块
复刻原项目 we-mp-rss 的公众号爬取逻辑
"""
import time
import random
import json
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

from core.db import DB
from core.models import Feed, Article
from core.config import cfg
from core.wx.auth import get_wechat_auth
from core.wx.mp import WeChatMP
from jobs.article import UpdateArticle, Update_Over
from jobs import TaskQueue, scheduler


class WxGather:
    """微信公众号爬取基类 - 复刻原项目 core/wx/base.py"""

    articles: List[Dict] = []
    aids: List[str] = []
    start_time: Optional[float] = None

    def __init__(self):
        self.articles = []
        self.aids = []
        self.start_time = None
        self.token = None
        self.cookies = {}
        self.is_add = False
        self.Gather_Content = cfg.get('gather.content', False)

    def all_count(self) -> int:
        """获取已采集文章数量"""
        return len(self.articles)

    def record_aid(self, aid: str):
        """记录已处理的文章ID"""
        self.aids.append(aid)

    def has_gathered(self, aid: str) -> bool:
        """检查文章是否已采集"""
        if aid in self.aids:
            return True
        self.record_aid(aid)
        return False

    def get_session_info(self):
        """获取微信授权会话信息"""
        auth = get_wechat_auth()
        return auth.get_session_info()

    def start(self, mp_id: str = None):
        """开始爬取"""
        self.articles = []
        self.start_time = time.time()
        self.update_mps_sync_time(mp_id)

    def update_mps_sync_time(self, mp_id: str):
        """更新公众号同步时间"""
        if not mp_id:
            return

        session = DB.get_session()
        try:
            feed = session.query(Feed).filter(Feed.id == mp_id).first()
            if feed:
                feed.sync_time = int(time.time())
                session.commit()
        except Exception as e:
            print(f"更新公众号同步时间失败: {e}")
        finally:
            session.close()

    def wait(self, min_seconds: int = 3, max_seconds: int = 10, tips: str = ""):
        """随机等待"""
        wait_time = random.randint(min_seconds, max_seconds)
        print(f"{tips} 等待 {wait_time} 秒...")
        time.sleep(wait_time)

    def fill_back(self, callback: Callable, data: Dict, ext_data: Dict = None):
        """填充文章数据并执行回调"""
        if callback is not None and data is not None:
            art = {
                "id": data.get('aid') or data.get('id'),
                "mp_id": data.get('mp_id'),
                "title": data.get('title'),
                "link": data.get('link') or data.get('url'),
                "cover": data.get('cover') or data.get('pic_url'),
                "content": data.get('content', ''),
                "update_time": data.get('update_time') or data.get('publish_time', 0),
            }
            if 'digest' in data:
                art['digest'] = data['digest']

            if callback(art):
                if ext_data:
                    art["ext"] = ext_data
                self.articles.append(art)

    def item_over(self, item: Dict = None, callback: Callable = None):
        """单个公众号处理完成"""
        print(f"item end: {item}")
        if callback is not None:
            callback(item)
        self.wait(tips=f"{item.get('mps_title', 'Unknown')} 处理完成", min_seconds=3, max_seconds=10)

    def over(self, callback: Callable = None):
        """爬取完成"""
        end_time = time.time()
        execution_time = 0

        if self.start_time is not None:
            execution_time = end_time - self.start_time

        print(f"成功采集 {len(self.articles)} 条文章")

        # 输出执行时间统计
        if execution_time > 0:
            if execution_time < 60:
                print(f"执行耗时: {execution_time:.2f}秒")
            elif execution_time < 3600:
                minutes = int(execution_time // 60)
                seconds = execution_time % 60
                print(f"执行耗时: {minutes}分{seconds:.2f}秒")
            else:
                hours = int(execution_time // 3600)
                minutes = int((execution_time % 3600) // 60)
                seconds = execution_time % 60
                print(f"执行耗时: {hours}小时{minutes}分{seconds:.2f}秒")

        if callback is not None:
            callback(self.articles)


class MpsWeb(WxGather):
    """Web模式爬取实现 - 复刻原项目 core/wx/model/web.py"""

    def get_articles(
        self,
        faker_id: str,
        mp_id: str = None,
        mp_title: str = "",
        callback: Callable = None,
        start_page: int = 0,
        max_page: int = 1,
        interval: int = 10,
        gather_content: bool = False,
        item_over_callback: Callable = None,
        over_callback: Callable = None
    ):
        """获取公众号文章列表

        Args:
            faker_id: 公众号 Faker ID
            mp_id: 公众号数据库ID
            mp_title: 公众号名称
            callback: 文章处理回调
            start_page: 起始页码
            max_page: 最大页码
            interval: 请求间隔(秒)
            gather_content: 是否采集文章正文
            item_over_callback: 单页完成回调
            over_callback: 全部完成回调
        """
        # 获取授权信息
        session_info = self.get_session_info()
        if not session_info.get('is_logged_in'):
            print("请先扫码授权登录")
            return

        self.token = session_info.get('token')
        self.cookies = session_info.get('cookies', {})

        self.start(mp_id=mp_id)
        gather_content = gather_content or self.Gather_Content
        print(f"Web浏览器模式, 是否采集[{mp_title}]内容：{gather_content}\n")

        # 构建请求
        base_url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
        count = 5  # 每页数量

        import requests
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': session_info.get('cookies_str', ''),
            'Referer': 'https://mp.weixin.qq.com/'
        })

        i = start_page
        while True:
            if i >= max_page:
                break

            begin = i * count
            params = {
                "sub": "list",
                "sub_action": "list_ex",
                "begin": str(begin),
                "count": count,
                "fakeid": faker_id,
                "token": self.token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": 1
            }

            print(f"第 {i + 1} 页开始爬取\n")
            time.sleep(random.randint(0, interval))

            try:
                response = session.get(base_url, params=params, timeout=10)
                msg = response.json()

                # 检查错误码
                ret = msg.get('base_resp', {}).get('ret', 0)

                # 频率控制
                if ret == 200013:
                    print("频率控制，停止爬取")
                    break

                # 无效会话
                if ret == 200003:
                    print("登录已失效，请重新登录")
                    break

                if ret != 0:
                    error_msg = msg.get('base_resp', {}).get('err_msg', '未知错误')
                    print(f"错误: {error_msg}")
                    break

                # 检查是否有数据
                if 'publish_page' not in msg:
                    print("所有文章已解析完成")
                    break

                # 解析文章列表
                publish_page = json.loads(msg['publish_page'])
                for item in publish_page.get('publish_list', []):
                    if 'publish_info' in item:
                        publish_info = json.loads(item['publish_info'])

                        if 'appmsgex' in publish_info:
                            for article in publish_info['appmsgex']:
                                # 检查是否已采集
                                aid = article.get('aid')
                                if self.has_gathered(aid):
                                    continue

                                # 采集正文内容
                                if gather_content:
                                    from core.wx.article import get_article_content
                                    article['content'] = get_article_content(article.get('link', ''))
                                    self.wait(tips=f"{article.get('title', '')} 采集完成", min_seconds=3, max_seconds=10)
                                else:
                                    article['content'] = ''

                                article['id'] = aid
                                article['mp_id'] = mp_id

                                # 执行回调
                                if callback:
                                    self.fill_back(
                                        callback=callback,
                                        data=article,
                                        ext_data={"mp_title": mp_title, "mp_id": mp_id}
                                    )

                print(f"第 {i + 1} 页爬取成功\n")

            except requests.exceptions.Timeout:
                print("请求超时")
                break
            except Exception as e:
                print(f"请求错误: {e}")
                break
            finally:
                self.item_over(
                    item={"mps_id": mp_id, "mps_title": mp_title},
                    callback=item_over_callback
                )

            i += 1

        self.over(callback=over_callback)


def fetch_all_articles():
    """获取所有公众号的最新文章"""
    print("开始更新所有公众号...")

    session = DB.get_session()
    try:
        # 获取所有公众号
        feeds = session.query(Feed).filter(Feed.status == 1).all()

        for feed in feeds:
            try:
                wx_gather = MpsWeb()
                wx_gather.get_articles(
                    faker_id=feed.faker_id,
                    mp_id=feed.id,
                    mp_title=feed.mp_name,
                    callback=UpdateArticle,
                    max_page=1,  # 只获取第一页（最新文章）
                    interval=5
                )
            except Exception as e:
                print(f"爬取公众号 {feed.mp_name} 失败: {e}")

        print(f"所有公众号更新完成，共获取 {len(wx_gather.articles) if 'wx_gather' in locals() else 0} 条数据")

    except Exception as e:
        print(f"获取公众号列表失败: {e}")
    finally:
        session.close()


def do_sync_job(mp: Feed, is_test: bool = False) -> Dict[str, Any]:
    """执行单个公众号同步任务

    Args:
        mp: 公众号对象
        is_test: 是否为测试模式

    Returns:
        同步结果字典
    """
    print(f"执行同步任务 (测试模式: {is_test})")

    all_count = 0

    if is_test:
        # 测试模式使用模拟数据
        mock_articles = [{
            "id": "test-article-001",
            "mp_id": mp.id,
            "title": "测试文章标题",
            "link": "https://example.com/test-article",
            "cover": "https://via.placeholder.com/300x200",
            "digest": "这是一篇测试文章的描述内容",
            "content": "<p>这是测试文章的正文内容。</p>",
            "update_time": int(time.time())
        }]
        count = 1
    else:
        # 实际爬取
        wx_gather = MpsWeb()
        try:
            wx_gather.get_articles(
                faker_id=mp.faker_id,
                mp_id=mp.id,
                mp_title=mp.mp_name,
                callback=UpdateArticle,
                max_page=1,
                interval=int(cfg.get('interval', 10))
            )
        except Exception as e:
            print(f"爬取失败: {e}")
            raise

        count = wx_gather.all_count()
        mock_articles = wx_gather.articles

    return {
        "mp_id": mp.id,
        "mp_name": mp.mp_name,
        "article_count": len(mock_articles),
        "success_count": count,
        "timestamp": datetime.now().isoformat()
    }


def add_sync_job(feeds: List[Feed], is_test: bool = False):
    """添加同步任务到队列

    Args:
        feeds: 公众号列表
        is_test: 是否为测试模式
    """
    for feed in feeds:
        TaskQueue.add_task(do_sync_job, feed, is_test)
        if is_test:
            print(f"测试任务: {feed.mp_name} 加入队列成功")
            break
        print(f"{feed.mp_name} 加入队列成功")

    print(f"任务队列: {TaskQueue.get_queue_info()}")


def run_sync_job(job_id: str = None, is_test: bool = False):
    """运行同步任务

    Args:
        job_id: 任务ID (可选)
        is_test: 是否为测试模式
    """
    from core.models import Feed
    import json

    # TODO: 从任务表获取需要执行的公众号
    # 这里暂时获取所有公众号
    session = DB.get_session()
    try:
        feeds = session.query(Feed).filter(Feed.status == 1).all()
        add_sync_job(feeds, is_test=is_test)
    finally:
        session.close()


def start_cron_job(cron_expr: str, feeds: List[Feed] = None):
    """启动定时任务

    Args:
        cron_expr: Cron表达式
        feeds: 公众号列表
    """
    if feeds is None:
        session = DB.get_session()
        try:
            feeds = session.query(Feed).filter(Feed.status == 1).all()
        finally:
            session.close()

    job_id = scheduler.add_cron_job(
        run_sync_job,
        cron_expr=cron_expr,
        args=[None, False],
        job_id=None
    )

    scheduler.start()
    print(f"已添加定时任务: {job_id}, 执行规则: {cron_expr}")
