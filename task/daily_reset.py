"""日常任务重置"""
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

REFRESH_HOUR = 4  # 凌晨4点刷新

@dataclass
class Task:
    tid: str
    status: str = "active"  # active/resetting/completed/expired
    progress: int = 0
    created_day: str = ""
    expire_at: datetime | None = None

class DailyResetSystem:
    def __init__(self, timezone="UTC"):
        self.timezone = timezone
        self._tz = ZoneInfo(timezone)
        self.refresh_hour = REFRESH_HOUR
        self.tasks: dict[str, Task] = {}

    def _local(self, dt: datetime) -> datetime:
        """统一转换到配置时区；naive datetime 视为配置时区的本地时间。"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self._tz)
        return dt.astimezone(self._tz)

    def now(self) -> datetime:
        """配置时区的当前时间（不使用服务器本地时间）。"""
        return datetime.now(self._tz)

    def _day_bucket(self, dt: datetime):
        # 刷新点为凌晨 refresh_hour 点：刷新点之前仍属于前一个任务日
        return (self._local(dt) - timedelta(hours=self.refresh_hour)).date()

    def is_new_day(self, last_check: datetime, now: datetime) -> bool:
        return self._day_bucket(last_check) != self._day_bucket(now)

    def maybe_reset_daily(self, last_check: datetime, now: datetime | None = None) -> bool:
        """定时任务入口：仅在配置时区跨过刷新点后重置。"""
        now = now or self.now()
        if not self.is_new_day(last_check, now):
            return False
        return self.reset_daily_tasks(now)

    def reset_daily_tasks(self, now: datetime | None = None) -> bool:
        now = now or self.now()
        changed = False
        for tid in list(self.tasks):
            if self.reset_task(tid, now=now):
                changed = True
        return changed

    def reset_task(self, tid: str, generator=None, now: datetime | None = None) -> bool:
        """原子重置：生成新任务失败时整体回滚，任务不会卡在 resetting。"""
        task = self.tasks.get(tid)
        if not task:
            return False
        snapshot = replace(task)
        task.status = "resetting"
        try:
            if generator is not None:
                new_task = generator(task)
            else:
                new_task = self._generate_task(task, now or self.now())
            if not isinstance(new_task, Task):
                raise RuntimeError("invalid task generated")
            new_task.status = "active"
        except Exception:
            self.tasks[tid] = snapshot  # 回滚到重置前状态
            return False
        self.tasks[tid] = new_task
        return True

    def _generate_task(self, old: Task, now: datetime) -> Task:
        local = self._local(now)
        bucket = (local - timedelta(hours=self.refresh_hour)).date()
        start = datetime.combine(bucket, time(self.refresh_hour), self._tz)
        return Task(
            tid=old.tid,
            status="active",
            created_day=bucket.isoformat(),
            expire_at=start + timedelta(days=1),
        )

    def _is_within_validity(self, task: Task, now: datetime) -> bool:
        if task.status not in ("active", "completed"):
            return False
        if task.expire_at is not None and self._local(now) >= self._local(task.expire_at):
            return False
        return True

    def update_task_progress(self, tid: str, progress: int, now: datetime | None = None) -> bool:
        task = self.tasks.get(tid)
        if not task:
            return False
        now = now or self.now()
        if not self._is_within_validity(task, now):
            task.status = "expired"
            return False
        task.progress = progress
        return True

    def submit_task_reward(self, tid: str, now: datetime | None = None) -> bool:
        task = self.tasks.get(tid)
        if not task:
            return False
        now = now or self.now()
        if not self._is_within_validity(task, now):
            task.status = "expired"
            return False
        return True

    def _week_monday(self, dt: datetime):
        d = self._local(dt).date()
        return d - timedelta(days=d.weekday())  # 本周一（自然周，周一零点）

    def is_new_week(self, last_check: datetime, now: datetime) -> bool:
        return self._week_monday(last_check) != self._week_monday(now)

    def reset_weekly_tasks(self, now: datetime | None = None, last_check: datetime | None = None) -> bool:
        """按自然周重置（配置时区周一零点），而非 7*24 小时滚动窗口。"""
        now = now or self.now()
        if last_check is not None:
            return self.is_new_week(last_check, now)
        return self._local(now).weekday() == 0
