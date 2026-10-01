"""日常任务重置"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

@dataclass
class Task:
    tid: str
    status: str = "active"  # active/resetting/completed/expired
    progress: int = 0
    created_day: str = ""

class DailyResetSystem:
    REFRESH_HOUR = 4  # 每日凌晨4点刷新（配置时区）

    def __init__(self, timezone="UTC"):
        self.timezone = timezone
        self.tz = ZoneInfo(timezone)
        self.tasks: dict[str, Task] = {}

    def _logical_date(self, dt: datetime):
        # 按配置时区换算，刷新点（凌晨4点）之前仍算前一天
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.tz)
        else:
            dt = dt.astimezone(self.tz)
        return (dt - timedelta(hours=self.REFRESH_HOUR)).date()

    def is_new_day(self, last_check: datetime, now: datetime) -> bool:
        return self._logical_date(last_check) != self._logical_date(now)

    def _generate_task(self, tid: str) -> Task:
        # 生成新任务，可能抛异常
        return Task(tid, status="active")

    def reset_task(self, tid: str) -> bool:
        task = self.tasks.get(tid)
        if not task:
            return False
        original_status = task.status
        task.status = "resetting"
        try:
            new_task = self._generate_task(tid)
        except Exception:
            task.status = original_status  # 失败回滚，不卡在resetting
            return False
        self.tasks[tid] = new_task
        return True

    def submit_task_reward(self, tid: str) -> bool:
        task = self.tasks.get(tid)
        if not task:
            return False
        if task.status not in ("active", "completed"):
            return False  # 过期/重置中的任务不能提交奖励
        return True

    def reset_weekly_tasks(self, now: datetime) -> bool:
        # 按自然周重置：周一零点
        return now.weekday() == 0
