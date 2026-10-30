

from typing import Optional

from memory.base import MemoryConfig
from memory.types.working import WorkingMemory


class MemoryManager:
    """记忆管理器 - 统一的记忆操作接口
    
    负责：
    - 记忆生命周期管理
    - 记忆优先级和重要性评估
    - 记忆遗忘和清理机制
    - 多类型记忆的协调管理
    """
    
    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        user_id: str = "default_user",
        enable_working: bool = True,
        enable_episodic: bool = True,
        enable_semantic: bool = True,
        enable_perceptual: bool = False
    ):    
        self.config = config or MemoryConfig()
        self.user_id = user_id

        self.memory_types = {}

        if enable_working:
            self.memory_types["working"] = WorkingMemory(self.config)