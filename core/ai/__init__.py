"""AI 处理模块"""
import json
import re
from typing import Optional, Dict, Any, List
from core.config import cfg


class AIService:
    """AI 服务类"""

    def __init__(self):
        self.provider = cfg.get("ai.provider", "openai")
        self.api_key = cfg.get("ai.api_key", "")
        self.base_url = cfg.get("ai.base_url", "")
        self.model = cfg.get("ai.model", "gpt-4o-mini")

    async def summarize(self, content: str, title: str = "") -> str:
        """AI 总结文章内容"""
        if not self.api_key:
            return "AI 未配置"

        prompt = f"""请为以下文章生成简洁的摘要（100字以内）：

标题：{title}

内容：
{content[:2000]}

摘要："""

        try:
            if self.provider == "openai":
                return await self._openai_summary(prompt)
            elif self.provider == "anthropic":
                return await self._anthropic_summary(prompt)
            else:
                return "不支持的 AI 提供商"
        except Exception as e:
            return f"AI 处理失败: {str(e)}"

    async def categorize(self, content: str, title: str = "") -> str:
        """AI 文章分类"""
        if not self.api_key:
            return "其他"

        categories = [
            "科技", "数码", "互联网", "金融", "财经",
            "时政", "社会", "娱乐", "体育", "汽车",
            "房产", "家居", "教育", "职场", "美食",
            "旅行", "健康", "养生", "情感", "育儿",
            "时尚", "美妆", "摄影", "音乐", "影视",
            "游戏", "动漫", "读书", "历史", "军事",
            "政治", "法律", "环保", "科学", "其他"
        ]

        prompt = f"""请为以下文章选择一个最合适的分类（只能选一个）：

标题：{title}

可选分类：{', '.join(categories)}

分类："""

        try:
            if self.provider == "openai":
                result = await self._openai_request(prompt)
            elif self.provider == "anthropic":
                result = await self._anthropic_request(prompt)
            else:
                return "其他"

            # 提取分类
            for cat in categories:
                if cat in result:
                    return cat
            return "其他"
        except Exception:
            return "其他"

    async def extract_tags(self, content: str, title: str = "", max_tags: int = 5) -> List[str]:
        """AI 提取文章标签"""
        if not self.api_key:
            return []

        prompt = f"""请为以下文章提取 {max_tags} 个关键词标签（用逗号分隔）：

标题：{title}

内容：
{content[:1500]}

标签："""

        try:
            if self.provider == "openai":
                result = await self._openai_request(prompt)
            elif self.provider == "anthropic":
                result = await self._anthropic_request(prompt)
            else:
                return []

            # 提取标签
            tags = [t.strip() for t in result.split(',') if t.strip()]
            return tags[:max_tags]
        except Exception:
            return []

    async def _openai_summary(self, prompt: str) -> str:
        """OpenAI 摘要"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url or None
        )

        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )

        return response.choices[0].message.content.strip()

    async def _anthropic_summary(self, prompt: str) -> str:
        """Anthropic 摘要"""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url or None
        )

        response = await client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    async def _openai_request(self, prompt: str) -> str:
        """OpenAI 请求"""
        return await self._openai_summary(prompt)

    async def _anthropic_request(self, prompt: str) -> str:
        """Anthropic 请求"""
        return await self._anthropic_summary(prompt)


# AI 服务实例
ai_service = AIService()
