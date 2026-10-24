"""手动全量体检：有限在途输入，短数据库任务与前台操作共用顺序。"""

from __future__ import annotations

from collections import deque
import hashlib
import json
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor, TimeoutError
import secrets
import threading
from typing import Callable

from core.database import DatabaseService, PasswordStrengthSnapshot
from .strength_worker import (
    StrengthAnalysisCancelled,
    StrengthAnalysisWorker,
    StrengthWorkerError,
    recommended_health_workers,
)


class HealthRescan:
    """体检状态留在原生层；所有数据库调用仍在已有业务执行器中完成。"""

    def __init__(
        self,
        database: DatabaseService,
        database_executor: ThreadPoolExecutor,
        is_editing: Callable[[int], bool],
        *,
        worker_factory: Callable = StrengthAnalysisWorker,
        worker_limit: Callable[[int], int] = recommended_health_workers,
    ) -> None:
        self.scan_id = secrets.token_urlsafe(24)
        self.cancelled = threading.Event()
        self.settled = threading.Event()
        self._database = database
        self._database_executor = database_executor
        self._is_editing = is_editing
        self._worker_factory = worker_factory
        self._worker_limit = worker_limit
        self._lock = threading.Lock()
        self._database_futures: set[Future] = set()
        self._remaining: deque[int] = deque()
        self._status = {
            "scanId": self.scan_id, "state": "RUNNING", "total": 0,
            "completed": 0, "updated": 0, "skipped": 0, "failed": 0,
            "workerCount": 0,
        }
        self._thread = threading.Thread(
            target=self._run, name="pdm-health-rescan", daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return dict(self._status)

    def cancel(self) -> None:
        with self._lock:
            if self.settled.is_set():
                return
            self.cancelled.set()
            self._status["state"] = "CANCELLING"
            pending = tuple(self._database_futures)
        for future in pending:
            future.cancel()

    def wait(self) -> None:
        self._thread.join()

    def close(self) -> None:
        self.cancel()
        self.wait()

    def _db_call(self, action: Callable, cancelled: threading.Event | None = None):
        def stopped():
            return self.cancelled.is_set() or (cancelled is not None and cancelled.is_set())

        def guarded():
            if stopped():
                raise StrengthAnalysisCancelled()
            return action()

        with self._lock:
            if stopped():
                raise StrengthAnalysisCancelled()
            future = self._database_executor.submit(guarded)
            self._database_futures.add(future)
        try:
            while True:
                try:
                    return future.result(timeout=0.05)
                except TimeoutError:
                    if future.done():
                        raise
                    # 排队中的任务可直接撤回；正在执行的短事务须完成后再清理会话。
                    if stopped() and future.cancel():
                        raise StrengthAnalysisCancelled()
                except CancelledError:
                    raise StrengthAnalysisCancelled() from None
        finally:
            with self._lock:
                self._database_futures.discard(future)

    def _read(self, record_id: int) -> PasswordStrengthSnapshot | str:
        if self._is_editing(record_id):
            return "skipped"
        snapshot = self._database.get_password_strength_snapshot(record_id)
        if snapshot is None:
            return "failed" if self._database.error_kind else "skipped"
        return snapshot

    def _write(self, snapshot: PasswordStrengthSnapshot, level: str) -> str:
        if self._is_editing(snapshot.record_id):
            return "skipped"
        result = self._database.update_password_strength(snapshot, level)
        return "updated" if result is True else "skipped" if result is False else "failed"

    def _count(self, outcome: str) -> None:
        with self._lock:
            self._status[outcome] += 1
            self._status["completed"] += 1

    def _next_record(self) -> int | None:
        with self._lock:
            if self.cancelled.is_set() or not self._remaining:
                return None
            return self._remaining.popleft()

    def _run_worker(self) -> None:
        worker = None
        try:
            while (record_id := self._next_record()) is not None:
                snapshot = None
                try:
                    snapshot = self._db_call(lambda: self._read(record_id))
                    if isinstance(snapshot, str):
                        self._count(snapshot)
                        continue
                    if (
                        "\0" in snapshot.password
                        or len(snapshot.password) > 1024
                        or len(snapshot.password.encode("utf-8")) > 4096
                    ):
                        self._count("failed")
                        continue
                    level = "weak"
                    if snapshot.password:
                        if worker is None:
                            worker = self._worker_factory()
                        report = worker.analyze(
                            snapshot.password,
                            snapshot.platform if len(snapshot.platform) <= 32 else "",
                            snapshot.account if len(snapshot.account) <= 32 else "",
                            self.cancelled,
                        )
                        level = str(report["level"]).lower()
                    # 后续 CAS 仅需要加密源列，不继续保留已用完的明文。
                    snapshot.platform = snapshot.account = snapshot.password = ""
                    outcome = self._db_call(lambda: self._write(snapshot, level))
                    self._count(outcome)
                except StrengthAnalysisCancelled:
                    return
                except Exception:
                    if worker is not None:
                        worker.close()
                        worker = None
                    self._count("failed")
                finally:
                    if isinstance(snapshot, PasswordStrengthSnapshot):
                        snapshot.clear()
        finally:
            if worker is not None:
                worker.close()

    def _run(self) -> None:
        terminal = "COMPLETED"
        try:
            record_ids = self._db_call(self._database.get_password_strength_ids)
            if record_ids is None:
                raise StrengthWorkerError("无法读取体检范围")
            count = len(record_ids)
            workers = min(count, max(1, min(8, self._worker_limit(count)))) if count else 0
            with self._lock:
                self._remaining.extend(record_ids)
                self._status["total"] = count
                self._status["workerCount"] = workers
            record_ids.clear()
            if workers:
                with ThreadPoolExecutor(
                    max_workers=workers, thread_name_prefix="pdm-health-worker",
                ) as pool:
                    futures = [pool.submit(self._run_worker) for _ in range(workers)]
                    for future in futures:
                        future.result()
        except StrengthAnalysisCancelled:
            terminal = "CANCELLED"
        except Exception:
            terminal = "FAILED"
        finally:
            with self._lock:
                self._remaining.clear()
                self._status["state"] = "CANCELLED" if self.cancelled.is_set() else terminal
                self._status["workerCount"] = 0
                self._database = None
                self.settled.set()


def strength_input_token(key: bytes, record_id: int, platform: str, account: str, password: str) -> bytes:
    """仅在当前会话内比较评分实际输入，不保留可离线猜测的密码摘要。"""
    value = [record_id, platform if len(platform) <= 32 else "",
             account if len(account) <= 32 else "", password]
    return hashlib.blake2s(json.dumps(value, ensure_ascii=False).encode("utf-8"), key=key).digest()


class SessionStrengthQueue(HealthRescan):
    """一个会话统一拥有自动补测、显式重试与全量体检的评分进程。"""

    def __init__(self, *args, revision_key: bytes, on_change=lambda: None, **kwargs):
        super().__init__(*args, **kwargs)
        self._revision_key = revision_key
        self._on_change = on_change
        self._queued: dict[int, None] = {}
        self._active: dict[int, threading.Event] = {}
        self._states: dict[int, tuple[bytes, str]] = {}
        self._results: dict[int, tuple[bytes, str]] = {}
        self._manual: set[int] = set()
        self._manual_events: dict[int, threading.Event] = {}
        self._scan_serial = 0
        self._suppressed: set[int] = set()
        self._free_workers: list = []
        self._discover = True
        self._full_requested = False
        self._paused = False
        self._activity_cancelled = threading.Event()
        self._read_failed = False
        self._wakeup = threading.Event()
        self._idle = threading.Event()
        self._status["state"] = "COMPLETED"

    @property
    def busy(self) -> bool:
        with self._lock:
            return bool(self._active or self._queued or self._discover or self._full_requested)

    @property
    def full_active(self) -> bool:
        with self._lock:
            return self._full_requested or bool(self._manual)

    def _changed(self):
        # 接收方只排队通知，不在评分线程反向等待界面或适配器锁。
        try:
            self._on_change()
        except RuntimeError:
            pass

    def _db_call(self, action: Callable, cancelled: threading.Event | None = None):
        return super()._db_call(action, cancelled or self._activity_cancelled)

    def wake(self, record_id: int | None = None, *, retry: bool = False) -> None:
        with self._lock:
            if self.cancelled.is_set():
                return
            if record_id is None:
                self._discover = True
            else:
                if retry:
                    self._states.pop(record_id, None)
                    self._suppressed.discard(record_id)
                if record_id not in self._suppressed:
                    self._queued[record_id] = None
            self._idle.clear()
        self._wakeup.set()

    def state_for(self, record_id: int, input_token: bytes) -> str:
        with self._lock:
            token, state = self._states.get(record_id, (b"", "FAILED" if self._read_failed else "PENDING"))
            return state if not token or token == input_token else "PENDING"

    def start_full_scan(self) -> dict[str, object]:
        with self._lock:
            if self._full_requested or self._manual:
                return dict(self._status)
            self.scan_id = secrets.token_urlsafe(24)
            self._scan_serial += 1
            self._status.update(scanId=self.scan_id, state="RUNNING", total=0,
                                completed=0, updated=0, skipped=0, failed=0, workerCount=0)
            self._full_requested = True
            self._idle.clear()
        self._wakeup.set()
        return self.snapshot()

    def cancel_full_scan(self) -> None:
        with self._lock:
            self._scan_serial += 1
            self._full_requested = False
            for record_id in self._manual:
                self._suppressed.add(record_id)
                self._queued.pop(record_id, None)
                if record_id in self._active:
                    self._active[record_id].set()
                self._states.pop(record_id, None)
            self._manual.clear()
            self._manual_events.clear()
            self._status["state"] = "CANCELLED"
        self._wakeup.set()
        self._changed()

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            self._activity_cancelled.set()
            self._full_requested = False
            self._manual.clear()
            self._manual_events.clear()
            self._scan_serial += 1
            if self._status["state"] == "RUNNING":
                self._status["state"] = "CANCELLED"
            for cancelled in self._active.values():
                cancelled.set()
            pending = tuple(self._database_futures)
        for future in pending:
            future.cancel()
        self._wakeup.set()

    def resume(self) -> None:
        with self._lock:
            if self._paused:
                self._activity_cancelled = threading.Event()
            self._paused = False
        self.wake()

    def wait_idle(self, timeout: float | None = None) -> bool:
        return self._idle.wait(timeout)

    def wait(self) -> None:
        self.wait_idle()

    def cancel_all(self) -> None:
        with self._lock:
            self.cancelled.set()
            for cancelled in self._active.values():
                cancelled.set()
            pending = tuple(self._database_futures)
        for future in pending:
            future.cancel()
        self._wakeup.set()

    def cancel(self) -> None:
        self.cancel_all()

    def close(self) -> None:
        self.cancel_all()
        if self._thread.ident is not None:
            self._thread.join()

    def _evaluate(self, record_id: int, cancelled: threading.Event) -> str:
        snapshot = None
        worker = None
        token = b""
        try:
            if self._is_editing(record_id):
                return "deferred"
            def read():
                value = self._database.get_password_strength_snapshot(record_id)
                return value, bool(self._database.error_kind)
            snapshot, read_failed = self._db_call(read, cancelled)
            if snapshot is None:
                if read_failed:
                    raise StrengthWorkerError("读取评级输入失败")
                with self._lock:
                    self._states.pop(record_id, None)
                    self._results.pop(record_id, None)
                return "skipped"
            token = strength_input_token(self._revision_key, record_id, snapshot.platform,
                                         snapshot.account, snapshot.password)
            with self._lock:
                manual = record_id in self._manual
                previous = self._states.get(record_id)
                cached = self._results.get(record_id)
                if not manual and snapshot.strength is not None:
                    self._states.pop(record_id, None)
                    self._results.pop(record_id, None)
                    return "skipped"
                if not manual and previous == (token, "FAILED"):
                    return "suppressed"
                self._states[record_id] = (token, "CHECKING")
            self._changed()
            if ("\0" in snapshot.password or len(snapshot.password) > 1024
                    or len(snapshot.password.encode("utf-8")) > 4096):
                raise StrengthWorkerError("评级输入超限")
            level = "weak"
            if cached is not None and cached[0] == token:
                level = cached[1]
            elif snapshot.password:
                with self._lock:
                    worker = self._free_workers.pop() if self._free_workers else None
                if worker is None:
                    worker = self._worker_factory()
                report = worker.analyze(
                    snapshot.password, snapshot.platform if len(snapshot.platform) <= 32 else "",
                    snapshot.account if len(snapshot.account) <= 32 else "", cancelled)
                level = str(report["level"]).lower()
            if cancelled.is_set() or self.cancelled.is_set():
                raise StrengthAnalysisCancelled()
            snapshot.platform = snapshot.account = snapshot.password = ""
            with self._lock:
                self._results[record_id] = (token, level)
            outcome = self._db_call(lambda: self._write(snapshot, level), cancelled)
            if outcome == "failed":
                raise StrengthWorkerError("写回评级失败")
            with self._lock:
                if outcome == "updated":
                    self._states.pop(record_id, None)
                    self._results.pop(record_id, None)
                else:
                    self._states.pop(record_id, None)
            return "updated" if outcome == "updated" else "stale"
        except StrengthAnalysisCancelled:
            with self._lock:
                if self._states.get(record_id) == (token, "CHECKING"):
                    self._states.pop(record_id, None)
            return "cancelled"
        except Exception:
            with self._lock:
                self._states[record_id] = (token, "FAILED")
                self._results.pop(record_id, None)
            if worker is not None:
                worker.close()
                worker = None
            return "failed"
        finally:
            if snapshot is not None:
                snapshot.clear()
            if worker is not None:
                if cancelled.is_set() or self.cancelled.is_set():
                    worker.close()
                else:
                    with self._lock:
                        self._free_workers.append(worker)

    def _finished(self, record_id: int, cancelled: threading.Event, future: Future) -> None:
        try:
            outcome = future.result()
        except Exception:
            outcome = "failed"
        with self._lock:
            self._active.pop(record_id, None)
            if record_id in self._manual and self._manual_events.get(record_id) is cancelled:
                self._manual.remove(record_id)
                self._manual_events.pop(record_id, None)
                field = outcome if outcome in {"updated", "failed"} else "skipped"
                self._status[field] += 1
                self._status["completed"] += 1
                if not self._manual and not self._full_requested:
                    self._status["state"] = "COMPLETED"
            if outcome == "stale" and record_id not in self._suppressed:
                self._queued[record_id] = None
        self._wakeup.set()
        self._changed()

    def _run(self) -> None:
        try:
            with ThreadPoolExecutor(max_workers=8, thread_name_prefix="pdm-record-strength") as pool:
                while not self.cancelled.is_set():
                    self._wakeup.clear()
                    with self._lock:
                        paused = self._paused
                        discover = self._discover and not paused
                        full = self._full_requested and not paused
                        serial = self._scan_serial
                        if discover:
                            self._discover = False
                    if discover or full:
                        try:
                            ids = self._db_call(self._database.get_password_strength_ids if full
                                                else self._database.get_pending_strength_ids)
                        except StrengthAnalysisCancelled:
                            if self.cancelled.is_set():
                                raise
                            with self._lock:
                                self._discover = True
                            continue
                        with self._lock:
                            self._read_failed = ids is None
                            if full and (not self._full_requested or serial != self._scan_serial):
                                ids = []
                            if full and self._full_requested and serial == self._scan_serial:
                                self._full_requested = False
                                self._manual = set(ids or ())
                                self._manual_events = {
                                    rid: event for rid, event in self._active.items()
                                    if rid in self._manual and not event.is_set()
                                }
                                self._suppressed.difference_update(self._manual)
                                self._status["total"] = len(self._manual)
                                self._status["state"] = "FAILED" if ids is None else "RUNNING" if self._manual else "COMPLETED"
                            for record_id in ids or ():
                                if record_id not in self._suppressed:
                                    self._queued[record_id] = None
                        self._changed()
                    with self._lock:
                        limit = max(1, min(8, self._worker_limit(len(self._manual)))) if self._manual else 1
                        launch = []
                        if not self._paused:
                            for record_id in tuple(self._queued):
                                if len(self._active) >= limit:
                                    break
                                if record_id in self._active:
                                    continue
                                self._queued.pop(record_id)
                                cancelled = threading.Event()
                                self._active[record_id] = cancelled
                                if record_id in self._manual:
                                    self._manual_events[record_id] = cancelled
                                launch.append((record_id, cancelled))
                        self._status["workerCount"] = len(self._active)
                        if not self._active and (self._paused or not self._queued and not self._discover and not self._full_requested):
                            self._idle.set()
                        spare = []
                        if not self._manual and not self._active and len(self._free_workers) > 1:
                            spare, self._free_workers = self._free_workers[1:], self._free_workers[:1]
                    for worker in spare:
                        worker.close()
                    for record_id, cancelled in launch:
                        future = pool.submit(self._evaluate, record_id, cancelled)
                        future.add_done_callback(lambda done, rid=record_id, event=cancelled:
                                                 self._finished(rid, event, done))
                    self._wakeup.wait()
        except StrengthAnalysisCancelled:
            pass
        finally:
            for worker in self._free_workers:
                worker.close()
            with self._lock:
                self._free_workers.clear()
                self._queued.clear()
                self._states.clear()
                self._results.clear()
                self._manual.clear()
                self._manual_events.clear()
                self._suppressed.clear()
                self._revision_key = b""
                self._database = None
                self._status["workerCount"] = 0
                self._idle.set()
                self.settled.set()
