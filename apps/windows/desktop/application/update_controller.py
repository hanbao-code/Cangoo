"""设备级更新任务；不读取密码库，也不随网页或库会话重建。"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .update_feed import UpdateFeedClient, parse_version, release_url
from .update_state import MAX_INTERVAL_DAYS, UpdateStateError


class UpdateController(QObject):
    changed = Signal(object)
    _stored = Signal(object, object, object)

    def __init__(self, store, submit_storage, current_version: str, parent=None,
                 *, client_factory=None, clock=None, open_url=None):
        super().__init__(parent)
        if parse_version(current_version) is None:
            raise ValueError("invalid installed version")
        self._store, self._submit = store, submit_storage
        self._version = current_version
        self._client_factory = client_factory or (lambda: UpdateFeedClient(self))
        self._clock = clock or (lambda: int(time.time() * 1000))
        self._open_url = open_url or (lambda url: QDesktopServices.openUrl(QUrl(url)))
        self._state = None
        self._settings_ready = False
        self._status, self._error = "CHECKING", "NONE"
        self._query_error = "NONE"
        self._revision = 0
        self._auto_notice = False
        self._closed = False
        self._startup_done = False
        self._running = False
        self._manual = False
        self._run = 0
        self._attempt_id = ""
        self._client = None
        self._waiters = []
        self._stored.connect(self._storage_finished, Qt.ConnectionType.QueuedConnection)
        self._storage(self._store.load, self._loaded)

    def _storage(self, action, done):
        if self._closed:
            return
        try:
            future = self._submit(action)
        except Exception as error:
            self._stored.emit(done, None, error)
            return

        def finished(result):
            try:
                value, error = result.result(), None
            except Exception as failure:
                value, error = None, failure
            try:
                self._stored.emit(done, value, error)
            except RuntimeError:
                pass

        future.add_done_callback(finished)

    @Slot(object, object, object)
    def _storage_finished(self, done, value, error):
        if not self._closed:
            if error is None:
                self._settings_ready = True
            done(value, error)

    def _storage_error(self, error):
        self._error = error.kind if isinstance(error, UpdateStateError) else "SETTINGS_WRITE_FAILED"
        if self._error == "SETTINGS_UNAVAILABLE":
            self._settings_ready = False
        self._status = "FAILED"
        self._auto_notice = False

    def _loaded(self, value, error):
        if error is not None:
            self._storage_error(error)
        else:
            self._state = value
            if not self._running:
                self._status, self._error = self._settled_status()
        self._publish()

    def _saved_status(self):
        result = self._state.get("lastResult") if self._state else None
        if result is None:
            return "IDLE"
        if not result["version"]:
            return "NO_RELEASE"
        return "UPDATE_AVAILABLE" if parse_version(result["version"]) > parse_version(self._version) else "UP_TO_DATE"

    def _settled_status(self):
        # 保存设置不代表完成了新的查询，仍保留最近查询失败。
        return ("FAILED", self._query_error) if self._query_error != "NONE" else (self._saved_status(), "NONE")

    def snapshot(self):
        state = self._state
        result = state.get("lastResult") if state else None
        available = bool(result and result["version"] and parse_version(result["version"]) > parse_version(self._version))
        reminder, until = "NORMAL", 0
        if result and result["version"]:
            saved_reminder = state["ignoredVersions"].get(result["version"])
            if saved_reminder == 0:
                reminder = "IGNORED"
            elif saved_reminder is not None and saved_reminder > self._clock():
                reminder, until = "SNOOZED", saved_reminder
        return {
            "revision": self._revision, "currentVersion": self._version,
            "settingsReady": self._settings_ready and state is not None, "enabled": bool(state and state["enabled"]),
            "intervalDays": state["intervalDays"] if state else 1,
            "lastAttemptMs": state["lastAttemptMs"] if state else 0,
            "status": self._status, "available": available,
            "releaseVersion": result["version"] if result else "",
            "releaseTag": result["tag"] if result else "",
            "publishedAt": result["publishedAt"] if result else "",
            "releaseNotes": result["notes"] if result else "",
            "resultAtMs": result["checkedAtMs"] if result else 0,
            "error": self._error, "reminder": reminder, "remindAfterMs": until,
            "autoNotice": self._auto_notice and available and reminder == "NORMAL",
        }

    def _publish(self):
        self._revision += 1
        self.changed.emit(self.snapshot())

    def start_for_startup(self):
        if self._startup_done or self._closed:
            return
        self._startup_done = True
        self._check(False, None)

    def dispatch(self, command: str, arguments: tuple, complete):
        if self._closed:
            complete(None, "STALE_PAGE")
            return
        if command == "C82":
            complete(self.snapshot(), "OK")
        elif command == "C83":
            self._check(True, complete)
        elif command == "C84":
            enabled, days = arguments
            if type(enabled) is not bool or type(days) is not int or not 1 <= days <= MAX_INTERVAL_DAYS:
                complete(None, "INVALID_ARGUMENT")
                return
            self._storage(lambda: self._store.set_policy(enabled, days),
                          lambda value, error: self._policy_saved(value, error, complete))
        elif command in {"C85", "C86"}:
            tag = arguments[0]
            result = self._state.get("lastResult") if self._state else None
            if not result or not tag or tag != result["tag"]:
                complete(None, "INVALID_ARGUMENT")
                return
            if command == "C86":
                try:
                    opened = self._open_url(release_url(tag))
                except Exception:
                    opened = False
                complete({} if opened else None, "OK" if opened else "INTERNAL_FAILURE")
                return
            action = arguments[1]
            if action == "DISMISS":
                self._auto_notice = False
                self._publish()
                complete(self.snapshot(), "OK")
            elif action in {"SNOOZE", "IGNORE"} and self.snapshot()["available"]:
                self._storage(lambda: self._store.set_reminder(result["version"], action, self._clock()),
                              lambda value, error: self._reminder_saved(value, error, complete))
            else:
                complete(None, "INVALID_ARGUMENT")
        else:
            complete(None, "INVALID_ARGUMENT")

    def _check(self, manual, complete):
        if complete is not None:
            self._waiters.append(complete)
        if self._running:
            self._manual = self._manual or manual
            return
        self._run += 1
        run = self._run
        self._running, self._manual = True, manual
        self._status, self._error, self._auto_notice = "CHECKING", "NONE", False
        self._publish()
        self._storage(lambda: self._store.claim_attempt(self._clock(), manual),
                      lambda value, error: self._claimed(run, value, error))

    def _claimed(self, run, value, error):
        if run != self._run or not self._running:
            return
        if error is not None:
            self._storage_error(error)
            self._finish()
            return
        claimed, self._state = value
        if not claimed:
            # 自动认领尚未完成时加入的手动意图仍须执行，不受间隔或开关限制。
            if self._manual:
                self._storage(lambda: self._store.claim_attempt(self._clock(), True),
                              lambda value, error: self._claimed(run, value, error))
                return
            self._status, self._error = self._settled_status()
            self._finish()
            return
        self._attempt_id = self._state["attemptId"]
        self._publish()
        try:
            self._client = self._client_factory()
            self._client.finished.connect(lambda result, error: self._received(run, result, error))
            self._client.start()
        except Exception:
            self._received(run, None, "NETWORK")

    def _received(self, run, result, error):
        if self._closed or run != self._run or not self._running:
            return
        client, self._client = self._client, None
        if client is not None:
            client.deleteLater()
        attempt = self._attempt_id
        if error == "NONE":
            self._storage(lambda: self._store.save_result(result, self._clock(), attempt),
                          lambda value, failure: self._result_saved(run, attempt, value, failure))
        else:
            self._storage(self._store.load,
                          lambda value, failure: self._query_failed(run, value, failure, error))

    def _result_saved(self, run, attempt, value, error):
        if run != self._run or not self._running:
            return
        if error is not None:
            self._storage_error(error)
        else:
            self._state = value
            if value["attemptId"] != attempt:
                self._query_error = "CANCELLED"
                self._status, self._error, self._auto_notice = "FAILED", "CANCELLED", False
            else:
                self._query_error = "NONE"
                self._status, self._error = self._saved_status(), "NONE"
                self._auto_notice = bool(not self._manual and value["enabled"]
                                         and self._status == "UPDATE_AVAILABLE" and self.snapshot()["reminder"] == "NORMAL")
        self._finish()

    def _query_failed(self, run, value, failure, error):
        if run != self._run or not self._running:
            return
        self._query_error = error
        if failure is not None:
            self._storage_error(failure)
        else:
            self._state = value
            self._status, self._error, self._auto_notice = "FAILED", error, False
        self._finish()

    def _finish(self):
        self._running = False
        waiters, self._waiters = self._waiters, []
        self._publish()
        for complete in waiters:
            complete(self.snapshot(), "OK")

    def _policy_saved(self, value, error, complete):
        if error is not None:
            self._storage_error(error)
        else:
            self._state = value
            if not value["enabled"]:
                self._auto_notice = False
                if self._running and not self._manual:
                    self._run += 1
                    self._running = False
                    client, self._client = self._client, None
                    if client is not None:
                        client.cancel()
                        client.deleteLater()
            if not self._running:
                self._status, self._error = self._settled_status()
            elif self._error in {"SETTINGS_UNAVAILABLE", "SETTINGS_WRITE_FAILED"}:
                self._status, self._error = "CHECKING", "NONE"
        self._publish()
        complete(self.snapshot(), "OK")

    def _reminder_saved(self, value, error, complete):
        if error is not None:
            self._storage_error(error)
        else:
            self._state, self._auto_notice = value, False
        self._publish()
        complete(self.snapshot(), "OK")

    def close(self):
        self._closed = True
        self._run += 1
        self._waiters.clear()
        client, self._client = self._client, None
        if client is not None:
            client.cancel()
            client.deleteLater()


__all__ = ["UpdateController"]
