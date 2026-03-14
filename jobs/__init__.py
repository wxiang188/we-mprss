"""
定时任务调度模块
复刻原项目 we-mp-rss 的任务调度系统
"""
import time
import threading
import uuid
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from croniter import croniter
import json

from core.db import DB
from core.models import Feed, Article
from core.config import cfg


class Task:
    """任务类"""
    def __init__(self, func: Callable, *args, **kwargs):
        self.id = str(uuid.uuid4())
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None

    def run(self):
        """执行任务"""
        self.status = "running"
        self.started_at = datetime.now()
        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.status = "completed"
        except Exception as e:
            self.error = str(e)
            self.status = "failed"
            print(f"任务执行失败: {e}")
        finally:
            self.completed_at = datetime.now()


class TaskQueue:
    """任务队列"""
    _instance = None
    _queue: List[Task] = []
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def add_task(cls, func: Callable, *args, **kwargs) -> Task:
        """添加任务到队列"""
        task = Task(func, *args, **kwargs)
        with cls._lock:
            cls._queue.append(task)
        return task

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Task]:
        """获取任务"""
        with cls._lock:
            for task in cls._queue:
                if task.id == task_id:
                    return task
        return None

    @classmethod
    def get_pending_tasks(cls) -> List[Task]:
        """获取待执行任务"""
        with cls._lock:
            return [t for t in cls._queue if t.status == "pending"]

    @classmethod
    def clear_queue(cls):
        """清空队列"""
        with cls._lock:
            cls._queue.clear()

    @classmethod
    def get_queue_info(cls) -> Dict[str, Any]:
        """获取队列信息"""
        with cls._lock:
            return {
                "total": len(cls._queue),
                "pending": len([t for t in cls._queue if t.status == "pending"]),
                "running": len([t for t in cls._queue if t.status == "running"]),
                "completed": len([t for t in cls._queue if t.status == "completed"]),
                "failed": len([t for t in cls._queue if t.status == "failed"])
            }


class CronJob:
    """定时任务"""
    def __init__(self, job_id: str, cron_expr: str, func: Callable, *args, **kwargs):
        self.job_id = job_id
        self.cron_expr = cron_expr
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.next_run = None
        self.update_next_run()

    def update_next_run(self):
        """更新下次执行时间"""
        try:
            cron = croniter(self.cron_expr, datetime.now())
            self.next_run = cron.get_next(datetime)
        except Exception as e:
            print(f"Cron表达式解析失败: {e}")
            self.next_run = None

    def should_run(self) -> bool:
        """检查是否应该执行"""
        if self.next_run is None:
            return False
        return datetime.now() >= self.next_run


class TaskScheduler:
    """任务调度器"""
    def __init__(self):
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_cron_job(self, func: Callable, cron_expr: str, args: List = None, job_id: str = None, **kwargs) -> str:
        """添加定时任务"""
        if job_id is None:
            job_id = str(uuid.uuid4())

        with self._lock:
            job = CronJob(job_id, cron_expr, func, args or [], **kwargs)
            self.jobs[job_id] = job

        return job_id

    def remove_job(self, job_id: str):
        """移除任务"""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]

    def clear_all_jobs(self):
        """清空所有任务"""
        with self._lock:
            self.jobs.clear()

    def start(self):
        """启动调度器"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("任务调度器已启动")

    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("任务调度器已停止")

    def _run_loop(self):
        """运行循环"""
        check_interval = 10  # 每10秒检查一次

        while self.running:
            try:
                now = datetime.now()

                with self._lock:
                    jobs_to_run = []
                    for job_id, job in self.jobs.items():
                        if job.should_run():
                            jobs_to_run.append(job)

                # 执行到期的任务
                for job in jobs_to_run:
                    print(f"执行定时任务: {job.job_id}")
                    try:
                        # 在新线程中执行任务
                        thread = threading.Thread(
                            target=job.func,
                            args=job.args,
                            kwargs=job.kwargs,
                            daemon=True
                        )
                        thread.start()
                    except Exception as e:
                        print(f"执行任务失败: {e}")

                    # 更新下次执行时间
                    job.update_next_run()

            except Exception as e:
                print(f"调度器循环异常: {e}")

            time.sleep(check_interval)

    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        with self._lock:
            return [
                {
                    "job_id": job.job_id,
                    "cron_expr": job.cron_expr,
                    "next_run": job.next_run.isoformat() if job.next_run else None,
                    "func": job.func.__name__
                }
                for job in self.jobs.values()
            ]


# 全局调度器实例
scheduler = TaskScheduler()
