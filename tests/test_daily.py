"""日常任务重置 - 红态测试"""
import pytest, sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from task.daily_reset import DailyResetSystem, Task

class TestTimezone:
    def test_reset_uses_configured_refresh_time(self):
        drs = DailyResetSystem(timezone="Asia/Shanghai")
        # 23:59 和 00:01 不应该算新的一天（如果刷新时间是凌晨4点）
        last = datetime(2026, 1, 1, 23, 59)
        now = datetime(2026, 1, 2, 0, 1)
        assert drs.is_new_day(last, now) == False

class TestAtomicReset:
    def test_reset_failure_rolls_back(self):
        drs = DailyResetSystem()
        drs.tasks["t1"] = Task("t1", status="active", progress=5)
        # 重置应该是原子的
        result = drs.reset_task("t1")
        assert result == True
        assert drs.tasks["t1"].status == "active"

class TestExpiredTask:
    def test_expired_task_cannot_submit(self):
        drs = DailyResetSystem()
        drs.tasks["t1"] = Task("t1", status="expired")
        assert drs.submit_task_reward("t1") == False

class TestWeeklyReset:
    def test_weekly_reset_on_monday(self):
        drs = DailyResetSystem()
        # 周一应该重置
        monday = datetime(2026, 1, 5)  # 周一
        assert drs.reset_weekly_tasks(monday) == True
