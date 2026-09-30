"""日常任务重置 - 含4个bug"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class Task:
    tid: str
    status: str = "active"  # active/resetting/completed/expired
    progress: int = 0
    created_day: str = ""

class DailyResetSystem:
    def __init__(self, timezone="UTC"):
        self.timezone = timezone  # bug1: 用服务器本地时间
        self.tasks: dict[str, Task] = {}

    def is_new_day(self, last_check: datetime, now: datetime) -> bool:
        # bug1: 用自然日比较，不按固定刷新时间
        return last_check.date() != now.date()

    def reset_task(self, tid: str) -> bool:
        # bug2: 状态转换非事务，中间失败卡住
        task = self.tasks.get(tid)
        if not task:
            return False
        task.status = "resetting"
        # 模拟生成新任务
        new_task = Task(tid, status="active")
        self.tasks[tid] = new_task
        task.status = "active"  # 这行不会执行，因为已经替换了
        return True

    def submit_task_reward(self, tid: str) -> bool:
        # bug3: 不检查任务是否过期
        task = self.tasks.get(tid)
        if not task:
            return False
        return True

    def reset_weekly_tasks(self, now: datetime) -> bool:
        # bug4: 按7*24小时算，不按自然周
        return True
