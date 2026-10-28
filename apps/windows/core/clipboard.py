"""
core.clipboard — 剪贴板管理模块

不依赖 PyQt5/PySide6 等 UI 框架，使用标准库 ctypes 调用 Windows user32.dll
实现剪贴板读写操作，使用 threading.Timer 实现倒计时自动清空。

支持两种工作模式：
- countdown: 复制后启动倒计时定时器，到时自动清空剪贴板
- manual:    复制后不自动清空，由用户手动调用 clear()

所有权判断机制（指纹）：
- copy() 时记录文本指纹（长度 + 内容哈希前缀），不存储原文
- clear() 时读取当前剪贴板内容并计算指纹，仅当与记录匹配才清空
  （避免清空用户后续复制的其他内容）
- force_clear() 无条件清空（用于离开态强制清理）
- is_owned_by_us() 主动判断当前剪贴板内容是否由本程序写入
- is_stale(timeout) 供 UI 层 QTimer 主动判断复制是否过期

通过 on_copy_callback 属性可向 UI 层通知复制事件（如更新状态栏提示）。
所有剪贴板操作均使用 threading.Lock 保证线程安全。
"""

import sys
import ctypes
import hashlib
import threading
import time


# Windows 剪贴板格式常量
_CF_UNICODETEXT = 13

# Windows 全局内存分配标志
_GMEM_MOVEABLE = 0x0002

# 工作模式常量
MODE_COUNTDOWN = "countdown"
MODE_MANUAL = "manual"

# 默认倒计时秒数
_DEFAULT_COUNTDOWN_SEC = 30

# 指纹哈希长度（SHA-256 前 N 个十六进制字符）
_FINGERPRINT_HASH_LEN = 16


def _init_user32():
    """
    初始化 user32 和 kernel32 函数签名

    非 Windows 平台返回 None，调用方需自行处理平台兼容性。
    设置函数签名可避免 64 位系统下指针被截断为 32 位。
    """
    if sys.platform != 'win32':
        return None

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # user32 剪贴板相关函数
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_int
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_int
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
    user32.RegisterClipboardFormatW.restype = ctypes.c_uint
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.IsClipboardFormatAvailable.argtypes = [ctypes.c_uint]
    user32.IsClipboardFormatAvailable.restype = ctypes.c_int
    # GetClipboardOwner：返回当前剪贴板所有者窗口句柄（用于所有权信息查询）
    user32.GetClipboardOwner.argtypes = []
    user32.GetClipboardOwner.restype = ctypes.c_void_p
    user32.IsWindow.argtypes = [ctypes.c_void_p]
    user32.IsWindow.restype = ctypes.c_int

    # kernel32 全局内存相关函数
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    return user32, kernel32


def _compute_fingerprint(text):
    """
    计算文本指纹（用于所有权判断，不存储原文）

    指纹格式："{长度}:{SHA-256前16位}"
    - 长度：文本字符数（快速过滤明显不同的内容）
    - 哈希：内容摘要前缀（精确匹配）

    指纹不可逆推原文（仅取前 16 个十六进制字符），且不包含首尾字符等
    可还原明文片段的信息，适合作为所有权标记。
    """
    if not text:
        return "0:"
    h = hashlib.sha256(text.encode('utf-8')).hexdigest()[:_FINGERPRINT_HASH_LEN]
    return f"{len(text)}:{h}"


class ClipboardManager:
    """
    剪贴板管理类（Windows 实现，不依赖 UI 框架）

    用法示例：
        cm = ClipboardManager()
        cm.bind_window_handle(hwnd)  # 宿主在界面线程取得的有效窗口句柄
        cm.set_mode("countdown", 30)
        cm.copy("hello", label="示例密码")
        # ... 30 秒后自动清空剪贴板（仅当内容仍为本程序写入时）

        cm.set_mode("manual")
        cm.copy("hello")
        # 用户手动清空（仅当内容仍为本程序写入时）
        cm.clear()
        # 离开态强制清空（无条件）
        cm.force_clear()

    可设置回调函数接收复制事件通知：
        cm.on_copy_callback = lambda label, mode: print(f"已复制: {label}")

    所有权判断：
        if cm.is_owned_by_us():
            # 当前剪贴板内容由本程序写入
            ...
        if cm.is_stale(10):
            # 距上次复制已超过 10 秒
            ...
    """

    def __init__(self, mode=MODE_COUNTDOWN, countdown_sec=_DEFAULT_COUNTDOWN_SEC):
        """
        初始化剪贴板管理器

        :param mode: 工作模式（countdown/manual）
        :param countdown_sec: 倒计时秒数（仅 countdown 模式生效）
        """
        self._lock = threading.Lock()
        self._mode = mode if mode in (MODE_COUNTDOWN, MODE_MANUAL) else MODE_COUNTDOWN
        self._countdown_sec = countdown_sec if countdown_sec > 0 else _DEFAULT_COUNTDOWN_SEC
        # 当前倒计时定时器
        self._timer = None
        # 可由 UI 层设置的复制事件回调函数
        self.on_copy_callback = None

        # 所有权判断状态
        # _last_fingerprint: 上次复制内容的指纹（None 表示本程序未写入或已清空）
        self._last_fingerprint = None
        # _last_copy_time: 上次复制的时间戳（time.monotonic，0.0 表示从未复制）
        self._last_copy_time = 0.0
        self._owner_hwnd = 0

        # 初始化 Windows API
        api = _init_user32()
        if api is None:
            raise RuntimeError("ClipboardManager 仅支持 Windows 平台")
        self._user32, self._kernel32 = api

    def bind_window_handle(self, hwnd):
        """宿主只传整数句柄；与发布串行，不能从工作线程访问界面对象。"""
        with self._lock:
            self._owner_hwnd = hwnd if type(hwnd) is int and hwnd > 0 else 0

    def copy(self, text, label=""):
        """
        复制文本到剪贴板

        - countdown 模式：复制后启动倒计时定时器，到时自动清空
        - manual 模式：仅复制，不启动定时器
        - 记录文本指纹与复制时间，供 clear() / is_owned_by_us() / is_stale() 判断
        - 复制成功后触发 on_copy_callback 回调（如已设置）

        :param text: 待复制的文本
        :param label: 复制内容的标签（用于 UI 提示，如账号名）
        :return: True 表示成功，False 表示失败
        """
        if not isinstance(text, str):
            text = str(text)

        timer_to_start = None
        with self._lock:
            # 写入剪贴板
            ok = self._set_clipboard_text_locked(text)
            if ok:
                # 只有新内容已经成功接管剪贴板后才取消旧定时器。
                # 写入失败时保留原内容的保护状态，避免旧秘密失去清理。
                self._cancel_timer_locked()
                # 记录指纹与时间，用于所有权判断与过期判断
                self._last_fingerprint = _compute_fingerprint(text)
                self._last_copy_time = time.monotonic()
                # countdown 模式准备倒计时定时器
                if self._mode == MODE_COUNTDOWN:
                    timer = threading.Timer(self._countdown_sec, self._on_timer_expired)
                    timer.daemon = True
                    self._timer = timer
                    timer_to_start = timer

        # 在锁外触发回调（避免回调耗时操作阻塞剪贴板锁）
        if ok:
            self._notify_callback(label)

        # 在锁外启动定时器（start() 创建线程，不应在锁内执行）
        if timer_to_start is not None:
            timer_to_start.start()

        return ok

    def clear(self):
        """同一次打开内检查与清空；读取未知或清空失败时保留清理责任。"""
        with self._lock:
            if self._last_fingerprint is not None:
                if not self._user32.OpenClipboard(None):
                    return False
                try:
                    current = self._get_clipboard_text_open()
                    if current is not None and _compute_fingerprint(current) == self._last_fingerprint:
                        if not self._user32.EmptyClipboard():
                            return False
                except Exception:
                    return False
                finally:
                    self._user32.CloseClipboard()
            self._cancel_timer_locked()
            self._last_fingerprint = None
            return True

    def force_clear(self):
        """
        无条件强制清空剪贴板（用于离开态强制清理）

        不检查内容所有权，直接调用 Win32 EmptyClipboard 强制释放所有权
        并清空所有格式数据。取消所有尚未触发的倒计时定时器。

        与 clear() 的区别：
        - clear()    : 仅当当前内容指纹与本程序上次写入匹配才清空（保护用户后续复制）
        - force_clear(): 无条件清空，无论当前内容由谁写入
        """
        with self._lock:
            cleared = self._empty_clipboard_locked()
            if cleared:
                self._cancel_timer_locked()
                self._last_fingerprint = None
            return cleared

    def is_stale(self, timeout_seconds):
        """
        判断上次复制是否已过期（供 UI 层 QTimer 主动检查）

        UI 层（如 QuickBar）可设置 QTimer 定期调用此方法，复制内容超过
        阈值后主动触发清理或视觉提示。

        :param timeout_seconds: 过期阈值（秒，支持小数）
        :return: True 表示已过期（距离上次复制已超过阈值，或从未复制过），
                 False 表示未过期
        """
        with self._lock:
            if self._last_copy_time == 0.0:
                return True  # 从未复制过，视为过期
            elapsed = time.monotonic() - self._last_copy_time
            return elapsed >= timeout_seconds

    def get_owner_info(self):
        """
        获取当前剪贴板所有者窗口句柄（Win32 GetClipboardOwner）

        :return: 所有者窗口句柄（int），0 表示无所有者。

        判断"当前内容是否由本程序写入"应使用 is_owned_by_us()，
        避免同一窗口的其他复制操作被当成原有受管内容。
        本方法主要用于诊断/日志场景。
        """
        user32 = self._user32
        with self._lock:
            try:
                return int(user32.GetClipboardOwner() or 0)
            except Exception:
                return 0

    def is_owned_by_us(self):
        """
        判断当前剪贴板内容是否由本程序写入（基于指纹匹配）

        :return: True 表示当前剪贴板文本内容与本程序上次复制的内容指纹匹配；
                 False 表示剪贴板为空、非文本格式或内容已被替换；None 表示暂时读取失败

        实现：读取当前剪贴板文本，计算指纹，与 _last_fingerprint 比较。
        窗口所有者不能区分同一窗口前后两次复制，故仍按内容指纹判断。
        """
        with self._lock:
            return self._is_current_content_owned_locked()

    def set_mode(self, mode, countdown_sec=_DEFAULT_COUNTDOWN_SEC):
        """
        设置工作模式

        :param mode: 工作模式（countdown/manual）
        :param countdown_sec: 倒计时秒数（仅 countdown 模式生效，必须大于 0）
        """
        with self._lock:
            if mode in (MODE_COUNTDOWN, MODE_MANUAL):
                self._mode = mode
            if countdown_sec > 0:
                self._countdown_sec = countdown_sec
            # 切换模式时取消已有定时器，避免旧模式残留定时器误触发
            self._cancel_timer_locked()

    # --- 内部辅助方法 ---

    def _cancel_timer_locked(self):
        """取消当前倒计时定时器（需持锁调用）"""
        if self._timer is not None:
            try:
                self._timer.cancel()
            except Exception:
                pass
            self._timer = None

    def _on_timer_expired(self):
        """兼容计时器复用原子清理；暂时失败继续保留责任。"""
        with self._lock:
            self._timer = None
        if self.clear():
            return
        with self._lock:
            if self._last_fingerprint is None or self._mode != MODE_COUNTDOWN or self._timer is not None:
                return
            self._timer = threading.Timer(0.25, self._on_timer_expired)
            self._timer.daemon = True
            self._timer.start()

    def _notify_callback(self, label):
        """触发复制事件回调（在锁外调用）"""
        cb = self.on_copy_callback
        if cb is None:
            return
        try:
            cb(label, self._mode)
        except Exception:
            # 回调异常不应影响主流程
            pass

    def _is_current_content_owned_locked(self):
        """True 为仍拥有，False 为已替换/无内容，None 为暂时无法确认。"""
        if self._last_fingerprint is None:
            return False
        try:
            current_text = self._get_clipboard_text_locked()
        except Exception:
            return None
        return current_text is not None and _compute_fingerprint(current_text) == self._last_fingerprint

    def _get_clipboard_text_open(self):
        """调用者已打开剪贴板；无文本与访问失败必须可区分。"""
        if not self._user32.IsClipboardFormatAvailable(_CF_UNICODETEXT):
            return None
        handle = self._user32.GetClipboardData(_CF_UNICODETEXT)
        if not handle:
            raise OSError("clipboard text unavailable")
        ptr = self._kernel32.GlobalLock(handle)
        if not ptr:
            raise OSError("clipboard text unavailable")
        try:
            return ctypes.wstring_at(ptr)
        finally:
            self._kernel32.GlobalUnlock(handle)

    def _get_clipboard_text_locked(self):
        if not self._user32.OpenClipboard(None):
            raise OSError("clipboard unavailable")
        try:
            return self._get_clipboard_text_open()
        finally:
            self._user32.CloseClipboard()

    def _set_clipboard_text_locked(self, text):
        """
        将文本写入剪贴板（Windows API 实现，需持锁调用）

        先准备文本与排除标记，在同次 OpenClipboard 内先发布标记再发布文本，
        防止受管复制进入 Windows 剪贴板历史与跨设备同步。

        SetClipboardData 成功后，全局内存所有权转移给系统，调用方不得再释放。
        """
        user32 = self._user32
        kernel32 = self._kernel32
        # NULL owner 经 EmptyClipboard 后不能 SetClipboardData；失败前保留旧内容。
        if not self._owner_hwnd or not user32.IsWindow(self._owner_hwnd):
            return False

        # 文本编码为 UTF-16 LE（Windows UNICODETEXT 格式）
        encoded = text.encode('utf-16-le')
        # 额外分配 2 字节用于结尾的 \0
        buf_size = len(encoded) + 2

        # 分配可移动全局内存
        h_global = kernel32.GlobalAlloc(_GMEM_MOVEABLE, buf_size)
        if not h_global:
            return False
        h_exclusion = None

        try:
            exclusion_format = user32.RegisterClipboardFormatW(
                'ExcludeClipboardContentFromMonitorProcessing'
            )
            if not exclusion_format:
                return False
            # 锁定内存获取指针
            ptr = kernel32.GlobalLock(h_global)
            if not ptr:
                return False

            try:
                # 写入数据 + 结尾 \0
                ctypes.memmove(ptr, encoded, len(encoded))
                ctypes.memset(ptr + len(encoded), 0, 2)
            finally:
                kernel32.GlobalUnlock(h_global)

            h_exclusion = kernel32.GlobalAlloc(_GMEM_MOVEABLE, 1)
            if not h_exclusion:
                return False
            exclusion_ptr = kernel32.GlobalLock(h_exclusion)
            if not exclusion_ptr:
                return False
            try:
                ctypes.memset(exclusion_ptr, 0, 1)
            finally:
                kernel32.GlobalUnlock(h_exclusion)

            if not user32.OpenClipboard(self._owner_hwnd):
                return False

            try:
                if not user32.EmptyClipboard():
                    return False
                # 标记先于秘密；失败不降级为普通复制，空句柄不能代替标记。
                if not user32.SetClipboardData(exclusion_format, h_exclusion):
                    return False
                h_exclusion = None
                # SetClipboardData 接管 h_global 所有权
                result = user32.SetClipboardData(_CF_UNICODETEXT, h_global)
                if not result:
                    return False
                # 所有权已转移，置空避免在 finally 中重复释放
                h_global = None
            finally:
                user32.CloseClipboard()

            return True
        except Exception:
            return False
        finally:
            if h_exclusion:
                kernel32.GlobalFree(h_exclusion)
            if h_global:
                kernel32.GlobalFree(h_global)

    def _empty_clipboard_locked(self):
        """清空剪贴板（需持锁调用，无条件）"""
        user32 = self._user32
        try:
            if not user32.OpenClipboard(None):
                return False
            try:
                return bool(user32.EmptyClipboard())
            finally:
                user32.CloseClipboard()
        except Exception:
            return False
