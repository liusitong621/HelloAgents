"""第八章：工作记忆测试

对照原版 examples/chapter08_memory_rag.py，只保留 WorkingMemory 能覆盖的部分。
当前记忆模块没有情景记忆、语义记忆、感知记忆和 RAG，因此本文件不调用
MemoryTool、SimpleAgent 或知识库。

本文件检查：
1. 添加记忆，并按关键词检索
2. 无关查询返回空结果，limit 生效
3. 容量满时淘汰优先级最低的记忆
4. 超过 TTL 的记忆在检索前被清理
5. 内容相近时，重要性更高的记忆排在前面
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.base import MemoryConfig, MemoryItem
from memory.types.working import WorkingMemory

def make_memory(memory_id, content, importance=0.5, minutes_ago=0):
    """构造一条工作记忆。minutes_ago 用来模拟更早写入的内容。"""
    return MemoryItem(
        id=memory_id,
        content=content,
        memory_type="working",
        user_id="demo_user",
        timestamp=datetime.now() - timedelta(minutes=minutes_ago),
        importance=importance,
    )

def show_hits(results):
    if not results:
        print("    （无命中）")
        return
    for index, memory in enumerate(results, 1):
        print(f"    {index}. [{memory.id}] {memory.content} (重要性: {memory.importance:.2f})")

class CheckResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, name, condition, detail):
        if condition:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            print(f"  ❌ {name}: {detail}")

def test_add_and_retrieve(report):
    """添加几条临时对话，确认能检索到对应内容。"""
    print("\n1️⃣ 添加与检索")
    memory = WorkingMemory(MemoryConfig(working_memory_capacity=10, working_memory_ttl_minutes=120))

    items = [
        ("m1", "用户李明是一名 Python 工程师", 0.6),
        ("m2", "当前正在讨论面向对象编程", 0.5),
        ("m3", "用户对装饰器概念感到困惑", 0.8),
        ("m4", "今天天气适合出门散步", 0.4),
    ]
    for memory_id, content, importance in items:
        saved_id = memory.add(make_memory(memory_id, content, importance))
        print(f"  已添加 {saved_id}: {content}")

    print("  查询「装饰器」:")
    hits = memory.retrieve("装饰器", limit=3)
    show_hits(hits)
    report.check(
        "能检索到装饰器相关记忆",
        bool(hits) and hits[0].id == "m3",
        f"实际命中: {[item.id for item in hits]}",
    )
    report.check(
        "无关的天气记忆不会排到第一",
        all(item.id != "m4" for item in hits[:1]),
        f"实际命中: {[item.id for item in hits]}",
    )

def test_limit_and_miss(report):
    """没有相关内容时应返回空列表，并且遵守 limit。"""
    print("\n2️⃣ 空结果与返回条数")
    memory = WorkingMemory(MemoryConfig())
    for index in range(4):
        memory.add(make_memory(f"p{index}", f"Python 学习笔记 {index}", importance=0.5 + index * 0.1))

    missed = memory.retrieve("量子计算", limit=3)
    limited = memory.retrieve("Python", limit=2)
    print(f"  查询「量子计算」命中 {len(missed)} 条")
    print(f"  查询「Python」并限制 2 条，实际返回 {len(limited)} 条")
    show_hits(limited)

    report.check("无关查询返回空列表", missed == [], f"实际返回 {len(missed)} 条")
    report.check("limit=2 时最多返回 2 条", len(limited) == 2, f"实际返回 {len(limited)} 条")

def test_capacity_eviction(report):
    """容量已满时，新记忆挤掉当前优先级最低的一条。"""
    print("\n3️⃣ 容量淘汰")
    memory = WorkingMemory(MemoryConfig(working_memory_capacity=2, working_memory_ttl_minutes=120))
    memory.add(make_memory("high", "重要：用户姓名是李明", importance=0.95))
    memory.add(make_memory("low", "闲聊：今天中午吃了面条", importance=0.1))
    memory.add(make_memory("mid", "继续：用户正在学习 Python", importance=0.6))

    kept_ids = [item.id for item in memory.memories]
    print(f"  容量为 2，写入 3 条后保留: {kept_ids}")
    report.check("保留条数不超过容量", len(memory.memories) == 2, f"实际保留 {len(memory.memories)} 条")
    report.check("淘汰重要性最低的记忆", "low" not in kept_ids and "high" in kept_ids, f"实际保留 {kept_ids}")

def test_ttl_expiry(report):
    """超过存活时间的记忆，在下一次添加或检索时被清掉。"""
    print("\n4️⃣ TTL 过期清理")
    memory = WorkingMemory(MemoryConfig(working_memory_capacity=10, working_memory_ttl_minutes=30))
    memory.add(make_memory("fresh", "刚刚提到的 Python 函数定义", importance=0.7, minutes_ago=0))
    memory.add(make_memory("stale", "两小时前的 Python 函数定义", importance=0.9, minutes_ago=90))

    print("  检索前内存中的 id:", [item.id for item in memory.memories])
    hits = memory.retrieve("Python 函数", limit=5)
    hit_ids = [item.id for item in hits]
    print("  检索结果:")
    show_hits(hits)
    report.check("过期记忆已被清理", "stale" not in [item.id for item in memory.memories], "过期记忆仍在列表中")
    report.check("检索只返回未过期记忆", hit_ids == ["fresh"], f"实际命中 {hit_ids}")

def test_importance_ranking(report):
    """两条内容几乎相同的记忆，重要性更高的应排在前面。"""
    print("\n5️⃣ 重要性排序")
    memory = WorkingMemory(MemoryConfig(working_memory_capacity=10, working_memory_ttl_minutes=120))
    memory.add(make_memory("low", "Python学习笔记甲", importance=0.2))
    memory.add(make_memory("high", "Python学习笔记乙", importance=0.9))

    hits = memory.retrieve("Python", limit=2)
    print("  查询「Python」:")
    show_hits(hits)
    report.check(
        "高重要性记忆排在前面",
        len(hits) == 2 and hits[0].id == "high",
        f"实际顺序 {[item.id for item in hits]}",
    )

def main():
    print("第八章：WorkingMemory 测试")
    print("只验证工作记忆的添加、检索、容量淘汰、TTL 清理和重要性排序")
    print("=" * 60)

    report = CheckResult()
    test_add_and_retrieve(report)
    test_limit_and_miss(report)
    test_capacity_eviction(report)
    test_ttl_expiry(report)
    test_importance_ranking(report)

    print("\n" + "=" * 60)
    print(f"结果: {report.passed} 项通过, {report.failed} 项失败")
    if report.failed:
        print("WorkingMemory 仍有未通过的检查")
        return 1
    print("WorkingMemory 检查通过")
    return 0

if __name__ == "__main__":
    sys.exit(main())
