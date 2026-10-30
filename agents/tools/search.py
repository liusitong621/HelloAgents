"""搜索工具 - 基于百度千帆 AI 搜索"""

import os
from typing import Any, Dict, List, Optional

import requests

from .base import Tool, ToolParameter

# 百度千帆「AI搜索」接口地址
BAIDU_SEARCH_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"

class SearchTool(Tool):
    """
    百度千帆网页搜索工具

    调用百度千帆 AI 搜索接口，解析返回的 references，
    返回前几条网页的标题与正文。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        top_k: int = 10,
        max_results: int = 3,
    ):
        super().__init__(
            name="search",
            description="一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
        )
        self.api_key = api_key or os.getenv("BAIDU_API_KEY")
        self.top_k = top_k
        self.max_results = max_results

        if self.api_key:
            print("✅ 百度千帆搜索已初始化")
        else:
            print("⚠️ BAIDU_API_KEY 未设置")

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行搜索

        Args:
            parameters: 包含 input 参数的字典

        Returns:
            搜索结果
        """
        query = parameters.get("input", "").strip()
        if not query:
            return "错误：搜索查询不能为空"

        if not self.api_key:
            return "错误:BAIDU_API_KEY 未在 .env 文件中配置。"

        print(f"🔍 正在执行 [百度千帆] 网页搜索: {query}")

        try:
            return self._search_baidu(query)
        except Exception as e:
            return f"搜索时发生错误: {e}"

    def _search_baidu(self, query: str) -> str:
        """调用百度千帆 AI 搜索并整理前几条结果"""
        payload = {
            "messages": [{"role": "user", "content": query}],
            "search_source": "baidu_search_v2",
            # top_k 最大 50；type 还可以是 video / image 等
            "resource_type_filter": [{"type": "web", "top_k": self.top_k}],
            # 可选时间过滤：week / month / semiyear / year
            "search_recency_filter": "year",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Appbuilder-Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(BAIDU_SEARCH_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        results = resp.json()

        # references 可能挂在顶层，也可能挂在 data 下面，两种都兼容
        references = (
            results.get("references")
            or (results.get("data") or {}).get("references")
            or []
        )
        if not references:
            detail = results.get("message") or results.get("error_msg") or "接口未返回 references"
            return f"对不起，没有找到关于 '{query}' 的信息。（{detail}）"

        snippets = []
        for i, ref in enumerate(references[: self.max_results]):
            title = ref.get("title") or ""
            text = (
                ref.get("content")
                or ref.get("snippet")
                or ref.get("markdown_text")
                or ""
            ).strip()
            if len(text) > 600:
                text = text[:600] + "……"
            block = f"[{i + 1}] {title}\n{text}"
            url = ref.get("url") or ref.get("link") or ""
            if url:
                block += f"\n来源: {url}"
            snippets.append(block)

        return "\n\n".join(snippets)

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="input",
                type="string",
                description="搜索查询关键词",
                required=True,
            )
        ]

def search(query: str) -> str:
    """
    便捷的搜索函数

    Args:
        query: 搜索查询关键词

    Returns:
        搜索结果
    """
    tool = SearchTool()
    return tool.run({"input": query})
