"""
v2.0 统一加密解密工具类 — AES-256-GCM + Argon2id 密钥派生

加密格式: Nonce(12B) || Ciphertext || AuthTag(16B) → 整体 Base64 编码为 str
密钥派生: Argon2id(用户数据库密码, 随机盐值, memory=19MiB, iterations=2, parallelism=1) → 32字节密钥
"""

import os
import base64
import platform as _stdlib_platform
import sys

from Crypto.Cipher import AES


def _prime_windows_platform_cache_without_subprocess() -> None:
    """Resolve CPython 3.10 Windows platform data without ``ver``.

    argon2-cffi 25.1 asks ``platform.machine()`` while importing its public
    low-level API.  CPython 3.10's Windows implementation first probes the
    optional ``ver`` command before falling back to ``sys.getwindowsversion``.
    A password-manager import must not create that helper process, so use the
    same built-in fallback while the process-local platform cache is empty.
    """

    if sys.platform != "win32":
        return
    if getattr(_stdlib_platform, "_uname_cache", None) is not None:
        return
    original_syscmd_ver = getattr(_stdlib_platform, "_syscmd_ver", None)
    if not callable(original_syscmd_ver):
        raise RuntimeError("stdlib platform fallback hook is unavailable")

    def _native_fallback_only(
        system: str = "",
        release: str = "",
        version: str = "",
        supported_platforms: tuple[str, ...] = (),
    ) -> tuple[str, str, str]:
        del supported_platforms
        return system, release, version

    _stdlib_platform._syscmd_ver = _native_fallback_only
    try:
        platform_identity = _stdlib_platform.uname()
    finally:
        _stdlib_platform._syscmd_ver = original_syscmd_ver
    if platform_identity.machine.casefold() in {"wasm32", "wasm64"}:
        raise RuntimeError("Windows platform identity unexpectedly resolved as WASM")


_prime_windows_platform_cache_without_subprocess()

from argon2.low_level import hash_secret_raw, Type

# 安全锁定专用密钥（不依赖用户密码，保持硬编码）
SECURITY_LOCK_KEY = b'VFGL7j8WDLJCdO3ceSxh55XUbTna7UPG'

# Argon2id 参数（OWASP 2023 推荐：memory=19 MiB, iterations=2, parallelism=1）
ARGON2_MEMORY_COST = 19456  # 19 MiB = 19 * 1024 KiB
ARGON2_TIME_COST = 2
ARGON2_PARALLELISM = 1
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 16


class CryptoHelper:
    """v2.0 统一加密解密工具类 — AES-256-GCM"""

    # --- Argon2id 密钥派生 ---

    @staticmethod
    def derive_key(db_password: str, salt: bytes) -> bytes:
        """使用 Argon2id 从用户数据库密码和盐值派生 32 字节加密密钥

        参数遵循 OWASP 2023 推荐基准：
        - memory=19 MiB (19456 KiB)：内存硬，抗 GPU/ASIC 并行攻击
        - iterations=2：2 轮迭代
        - parallelism=1：单线程（桌面应用场景）
        """
        return hash_secret_raw(
            secret=db_password.encode('utf-8'),
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID,
        )

    @staticmethod
    def generate_salt() -> bytes:
        """生成 16 字节随机盐值"""
        return os.urandom(16)

    # --- 数据加密（GCM，密钥由调用方传入） ---

    @staticmethod
    def encrypt_data(plaintext: str, key: bytes) -> str:
        """AES-256-GCM 加密，返回 Base64 编码字符串"""
        nonce = os.urandom(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        return base64.b64encode(nonce + ciphertext + tag).decode('utf-8')

    @staticmethod
    def decrypt_data(encrypted: str, key: bytes) -> str:
        """AES-256-GCM 解密，输入 Base64 编码字符串，返回明文"""
        raw = base64.b64decode(encrypted, validate=True)
        if len(raw) < 28:
            raise ValueError('invalid field ciphertext length')
        nonce, ciphertext, tag = raw[:12], raw[12:-16], raw[-16:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')

    # --- 安全锁定加密（GCM，使用固定 SECURITY_LOCK_KEY） ---

    @staticmethod
    def encrypt_lock_info(plaintext: str) -> str:
        """加密安全锁定信息（数据库路径/时间戳），使用固定密钥"""
        nonce = os.urandom(12)
        cipher = AES.new(SECURITY_LOCK_KEY, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        return base64.b64encode(nonce + ciphertext + tag).decode('utf-8')

    @staticmethod
    def decrypt_lock_info(encrypted: str) -> str:
        """解密安全锁定信息，使用固定密钥"""
        raw = base64.b64decode(encrypted)
        nonce, ciphertext, tag = raw[:12], raw[12:-16], raw[-16:]
        cipher = AES.new(SECURITY_LOCK_KEY, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')


# ---------------------------------------------------------------------------
# SecureKeyBuffer — 使用 Windows 原生 API 的安全密钥内存管理
# ---------------------------------------------------------------------------
import ctypes
import ctypes.wintypes as wt

# Windows API 常量
_MEM_COMMIT = 0x1000
_MEM_RESERVE = 0x2000
_MEM_RELEASE = 0x8000
_PAGE_READWRITE = 0x04
_PAGE_NOACCESS = 0x01
_PAGE_SIZE = 4096  # Windows 内存页大小

# 初始化 kernel32 并设置正确的函数签名
if sys.platform == 'win32':
    _kernel32 = ctypes.windll.kernel32
    _kernel32.VirtualAlloc.restype = ctypes.c_void_p
    _kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
    _kernel32.VirtualFree.restype = wt.BOOL
    _kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]
    _kernel32.VirtualLock.restype = wt.BOOL
    _kernel32.VirtualLock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    _kernel32.VirtualUnlock.restype = wt.BOOL
    _kernel32.VirtualUnlock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    _kernel32.VirtualProtect.restype = wt.BOOL
    _kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.POINTER(wt.DWORD)]
else:
    _kernel32 = None


class SecureKeyBuffer:
    """
    安全密钥缓冲区，使用 Windows 原生内存保护 API：
    - VirtualAlloc: 页对齐内存分配
    - VirtualLock: 防止密钥被换页到磁盘 (pagefile/swap)
    - VirtualProtect: 不使用时将内存标记为 PAGE_NOACCESS
    - memset: 使用后立即安全清零
    密钥可读时间窗口从「整个运行期间」压缩到「use()/lock() 之间」
    """

    def __init__(self, key: bytes):
        if _kernel32 is None:
            raise RuntimeError("SecureKeyBuffer 仅支持 Windows 平台")

        self._key_len = len(key)
        # 分配整页内存（VirtualLock 要求页对齐）
        self._addr = _kernel32.VirtualAlloc(
            None, _PAGE_SIZE, _MEM_COMMIT | _MEM_RESERVE, _PAGE_READWRITE
        )
        if not self._addr:
            raise MemoryError("VirtualAlloc 失败")

        # 写入密钥数据
        ctypes.memmove(self._addr, key, self._key_len)

        # 锁定内存页，防止换页到磁盘
        self._locked = bool(_kernel32.VirtualLock(
            ctypes.c_void_p(self._addr), _PAGE_SIZE
        ))

        # 默认设为不可访问
        self._accessible = True
        self._protect_noaccess()

    def use(self) -> bytes:
        """临时开放密钥读写，返回密钥副本用于加密操作。使用后必须调用 lock()"""
        self._protect_readwrite()
        # 返回密钥数据的副本（bytes 对象），供加密操作使用
        buf = (ctypes.c_char * self._key_len).from_address(self._addr)
        key_copy = bytes(buf)
        return key_copy

    def lock(self):
        """使用完毕后立即将密钥内存标记为不可访问"""
        self._protect_noaccess()

    def destroy(self):
        """安全销毁密钥：清零 → 解锁 → 释放"""
        self._protect_readwrite()
        # 安全清零
        ctypes.memset(self._addr, 0, self._key_len)
        # 解锁内存页
        if self._locked:
            _kernel32.VirtualUnlock(ctypes.c_void_p(self._addr), _PAGE_SIZE)
        # 释放内存
        _kernel32.VirtualFree(ctypes.c_void_p(self._addr), 0, _MEM_RELEASE)
        self._addr = None

    def zero(self) -> None:
        """destroy() 的别名（product_brief §10.2 文档统一用 zero 表述）"""
        self.destroy()

    def __del__(self):
        """析构时自动销毁"""
        if self._addr is not None:
            try:
                self.destroy()
            except Exception:
                pass

    def _protect_noaccess(self):
        """将密钥内存页标记为 PAGE_NOACCESS"""
        if self._accessible and self._addr:
            old = wt.DWORD(0)
            _kernel32.VirtualProtect(
                ctypes.c_void_p(self._addr), _PAGE_SIZE,
                _PAGE_NOACCESS, ctypes.byref(old)
            )
            self._accessible = False

    def _protect_readwrite(self):
        """将密钥内存页恢复为 PAGE_READWRITE"""
        if not self._accessible and self._addr:
            old = wt.DWORD(0)
            _kernel32.VirtualProtect(
                ctypes.c_void_p(self._addr), _PAGE_SIZE,
                _PAGE_READWRITE, ctypes.byref(old)
            )
            self._accessible = True
