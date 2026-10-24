"""
core 包 — 密码管理器核心业务逻辑层

本包提供与 UI 框架无关的核心功能模块，包括：
- crypto:     统一加密解密工具（AES-256-GCM + PBKDF2 密钥派生 + 安全密钥内存管理）
- config:     用户配置文件管理（settings.json）
- clipboard:  剪贴板管理（支持倒计时自动清空和手动清空两种模式）

设计目标：将业务逻辑与 UI 表现层解耦，便于复用与单元测试。
所有模块均不依赖 PyQt5/PySide6 等 UI 框架，仅使用 Python 标准库
及必要的第三方加密库（pycryptodome）。
"""
