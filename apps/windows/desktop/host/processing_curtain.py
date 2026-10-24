"""全窗口处理中幕布的最低停留协调器。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import secrets
import threading
import time
from typing import Callable, Optional


MINIMUM_DURATION_MS = 1000
MAXIMUM_DURATION_MS = 1500
_NANOSECONDS_PER_MILLISECOND = 1_000_000


class ProcessingCurtainProcess(str, Enum):
    """需要全窗口处理中幕布的固定过程类型。"""

    STARTUP = "STARTUP"
    SECURITY_LOCK = "SECURITY_LOCK"
    RENDERER_REBUILD = "RENDERER_REBUILD"


@dataclass(frozen=True, eq=False)
class ProcessingCurtainToken:
    """一次过程的不透明令牌；对象身份用于拒绝旧回调。"""

    process: ProcessingCurtainProcess
    process_id: int


@dataclass(frozen=True)
class RevealDecision:
    """一次核对结果。

    ``remaining_ms`` 仅在页面已经就绪但最低时间尚未满足时提供，
    调用者可据此安排一次唤醒；它不代表页面或安全状态。
    """

    reveal_now: bool
    remaining_ms: Optional[int] = None


@dataclass
class _ActiveProcess:
    identity: tuple[ProcessingCurtainProcess, int]
    token: ProcessingCurtainToken
    minimum_ms: int
    presentable: bool
    minimum_started_ns: Optional[int]
    ready: bool = False
    revealed: bool = False
    terminated: bool = False


_NO_ACTION = RevealDecision(reveal_now=False)
_REVEAL_NOW = RevealDecision(reveal_now=True)


def _sample_minimum_ms() -> int:
    return 1000 + secrets.randbelow(501)


class ProcessingCurtainCoordinator:
    """协调页面就绪与最低停留时间，不持有任何界面或业务状态。"""

    def __init__(
        self,
        *,
        clock_ns: Callable[[], int] = time.perf_counter_ns,
        sample_minimum_ms: Callable[[], int] = _sample_minimum_ms,
    ) -> None:
        self._clock_ns = clock_ns
        self._sample_minimum_ms = sample_minimum_ms
        self._owner_thread_id = threading.get_ident()
        self._active: Optional[_ActiveProcess] = None

    def begin(
        self,
        process: ProcessingCurtainProcess,
        process_id: int,
        *,
        presentable: bool = True,
    ) -> ProcessingCurtainToken:
        """开始过程；相同的当前身份复用令牌和唯一采样值。"""

        self._assert_owner_thread()
        identity = self._validate_identity(process, process_id)
        self._validate_presentable(presentable)
        active = self._active
        if active is not None and active.identity == identity:
            return active.token

        minimum_ms = self._sample_minimum_ms()
        self._validate_minimum_ms(minimum_ms)
        # 启动说明必须真的出现过才开始计时；安全锁定和渲染重建则从
        # 安全过程开始即计时，隐藏、最小化和睡眠都属于已经经过的时间。
        minimum_started_ns = (
            self._clock_ns()
            if process is not ProcessingCurtainProcess.STARTUP or presentable
            else None
        )
        token = ProcessingCurtainToken(
            process=process,
            process_id=process_id,
        )
        self._active = _ActiveProcess(
            identity=identity,
            token=token,
            minimum_ms=minimum_ms,
            presentable=presentable,
            minimum_started_ns=minimum_started_ns,
        )
        return token

    def set_presentable(
        self,
        token: ProcessingCurtainToken,
        presentable: bool,
    ) -> bool:
        """更新真实可呈现状态；隐藏只作废本轮视觉就绪。"""

        self._assert_owner_thread()
        self._validate_presentable(presentable)
        active = self._current_for(token)
        if active is None or active.revealed or active.terminated:
            return False
        if active.presentable is presentable:
            return True
        active.presentable = presentable
        if not presentable:
            active.ready = False
        if (
            active.token.process is ProcessingCurtainProcess.STARTUP
            and presentable
            and active.minimum_started_ns is None
        ):
            # 仅第一次真正可呈现时启动启动幕布的最低可读时长。
            active.minimum_started_ns = self._clock_ns()
        return True

    def mark_ready(self, token: ProcessingCurtainToken) -> RevealDecision:
        """标记页面已经就绪，并立即重新核对是否可以揭幕。"""

        self._assert_owner_thread()
        active = self._current_for(token)
        if (
            active is None
            or not active.presentable
            or active.revealed
            or active.terminated
        ):
            return _NO_ACTION
        active.ready = True
        return self._reconcile_current(active)

    def reconcile(self, token: ProcessingCurtainToken) -> RevealDecision:
        """重新核对当前令牌；揭幕裁决最多交付一次。"""

        self._assert_owner_thread()
        active = self._current_for(token)
        if active is None or active.revealed or active.terminated:
            return _NO_ACTION
        return self._reconcile_current(active)

    def fail(self, token: ProcessingCurtainToken) -> bool:
        """使失败过程立即失效；失败幕布由调用者管理。"""

        self._assert_owner_thread()
        return self._terminate(token)

    def invalidate(self, token: ProcessingCurtainToken) -> bool:
        """显式作废当前过程，旧令牌随后不能产生裁决。"""

        self._assert_owner_thread()
        return self._terminate(token)

    def _terminate(self, token: ProcessingCurtainToken) -> bool:
        active = self._current_for(token)
        if active is None or active.terminated:
            return False
        active.terminated = True
        return True

    def _current_for(
        self,
        token: ProcessingCurtainToken,
    ) -> Optional[_ActiveProcess]:
        active = self._active
        if active is None or active.token is not token:
            return None
        return active

    def _reconcile_current(self, active: _ActiveProcess) -> RevealDecision:
        if (
            not active.presentable
            or not active.ready
            or active.minimum_started_ns is None
        ):
            return _NO_ACTION

        deadline_ns = (
            active.minimum_started_ns
            + active.minimum_ms * _NANOSECONDS_PER_MILLISECOND
        )
        remaining_ns = deadline_ns - self._clock_ns()
        if remaining_ns <= 0:
            active.revealed = True
            return _REVEAL_NOW

        remaining_ms = (
            remaining_ns + _NANOSECONDS_PER_MILLISECOND - 1
        ) // _NANOSECONDS_PER_MILLISECOND
        return RevealDecision(
            reveal_now=False,
            remaining_ms=remaining_ms,
        )

    def _assert_owner_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            raise RuntimeError("协调器只能由创建它的线程调用")

    @staticmethod
    def _validate_identity(
        process: ProcessingCurtainProcess,
        process_id: int,
    ) -> tuple[ProcessingCurtainProcess, int]:
        if not isinstance(process, ProcessingCurtainProcess):
            raise TypeError("process 必须是 ProcessingCurtainProcess")
        if type(process_id) is not int:
            raise TypeError("process_id 必须是整数")
        if process_id < 0:
            raise ValueError("process_id 必须是非负整数")
        return process, process_id

    @staticmethod
    def _validate_minimum_ms(value: int) -> None:
        if type(value) is not int:
            raise TypeError("最低停留采样值必须是整数")
        if not MINIMUM_DURATION_MS <= value <= MAXIMUM_DURATION_MS:
            raise ValueError("最低停留采样值必须位于 1000 到 1500 毫秒")

    @staticmethod
    def _validate_presentable(value: bool) -> None:
        if type(value) is not bool:
            raise TypeError("presentable 必须是布尔值")


__all__ = [
    "MAXIMUM_DURATION_MS",
    "MINIMUM_DURATION_MS",
    "ProcessingCurtainCoordinator",
    "ProcessingCurtainProcess",
    "ProcessingCurtainToken",
    "RevealDecision",
]
