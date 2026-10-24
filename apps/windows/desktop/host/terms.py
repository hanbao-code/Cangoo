"""在正式宿主创建前显示许可告知，并尽力保存本机阅读记录。"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QStackedWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from core.config import ConfigManager
from desktop.host.focus_visibility import NativeFocusVisibilityController
from desktop.host.window_chrome import set_win11_caption_colors
from desktop.m4.resources import M4ResourceCatalog
from desktop.m4.settings_store import M4AtomicSettingsStore, M4SettingsCommitError
from desktop.ui_font_scale import normalize_ui_font_scale, scaled_font_pixel_size


ACCEPTED_TERMS_KEY = "accepted_terms_version"


class LicenseList(QListWidget):
    def update(self, *args) -> None:
        # PySide列表的索引重载遮蔽无参刷新；保留现有焦点控件的QWidget接口。
        if args:
            super().update(*args)
        else:
            QWidget.update(self)


class TermsSettings:
    """确认只是本地偏好；不充当身份或防篡改授权。"""

    def __init__(self, path: Path) -> None:
        self.manager = ConfigManager(str(path))
        self.manager.load(create_if_missing=False)
        self.store = M4AtomicSettingsStore(self.manager, path)

    @property
    def language(self) -> str:
        return "en" if self.manager.get("language") == "en" else "zh"

    def accepted(self, version: str) -> bool:
        return self.manager.get(ACCEPTED_TERMS_KEY) == version

    def set_language(self, language: str) -> None:
        if language not in {"zh", "en"}:
            raise ValueError("unsupported language")
        self.store.commit_value(
            "language", language, current_value=lambda: self.language,
        )

    def accept(self, version: str) -> None:
        if type(version) is not str or not version:
            raise ValueError("invalid terms version")
        self.store.commit_value(
            ACCEPTED_TERMS_KEY, version,
            current_value=lambda: self.manager.get(ACCEPTED_TERMS_KEY),
        )


class TermsDialog(QDialog):
    """继续即进入产品；阅读记录写入失败不限制运行许可。"""

    def __init__(self, settings: TermsSettings, content: dict) -> None:
        super().__init__()
        self.settings = settings
        self.content = content
        self._busy = False
        self._document = "home"
        self._scroll_positions: dict[str, int] = {}
        self.setObjectName("pdmTerms")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.resize(760, 680)
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.resize(min(760, area.width() - 40), min(680, area.height() - 60))
        self.setMinimumSize(420, 340)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        header = QHBoxLayout()
        brand = QLabel(self)
        brand.setPixmap(QApplication.windowIcon().pixmap(32, 32))
        header.addWidget(brand)
        self.title = QLabel(self)
        header.addWidget(self.title, 1)
        self.zh = QPushButton("中文", self)
        self.en = QPushButton("English", self)
        for button in (self.zh, self.en):
            button.setCheckable(True)
            button.setAutoDefault(False)
            header.addWidget(button)
        root.addLayout(header)
        self.reader = QTextBrowser(self)
        self.reader.setOpenLinks(False)
        self.reader.setOpenExternalLinks(False)
        self.reader.setReadOnly(True)
        self.license_list = LicenseList(self)
        self.license_list.addItems([item["name"] for item in self.content["licenses"]])
        self.license_list.itemActivated.connect(lambda item: self.open_document(f"third-party/{self.license_list.row(item)}"))
        self.license_list.itemClicked.connect(lambda item: self.open_document(f"third-party/{self.license_list.row(item)}"))
        self.reading_area = QStackedWidget(self)
        self.reading_area.addWidget(self.reader)
        self.reading_area.addWidget(self.license_list)
        self.list_intro = QLabel(self)
        self.list_intro.setWordWrap(True)
        root.addWidget(self.list_intro)
        root.addWidget(self.reading_area, 1)
        self.document_links = QWidget(self)
        link_layout = QHBoxLayout(self.document_links)
        link_layout.setContentsMargins(0, 0, 0, 0)
        link_layout.setSpacing(10)
        self.document_buttons = {}
        for identifier in ("agpl", "openssl", "third-party"):
            button = QPushButton(self.document_links)
            button.setAutoDefault(False)
            button.setMinimumHeight(56)
            button.clicked.connect(lambda _checked=False, key=identifier: self.open_document(key))
            self.document_buttons[identifier] = button
            link_layout.addWidget(button, 1)
        root.addWidget(self.document_links)
        self.error = QLabel(self)
        self.error.setWordWrap(True)
        self.error.setObjectName("termsError")
        root.addWidget(self.error)
        actions = QHBoxLayout()
        self.back = QPushButton(self)
        self.back.setAutoDefault(False)
        self.back.clicked.connect(self.go_back)
        actions.addWidget(self.back)
        actions.addStretch(1)
        self.decline = QPushButton(self)
        self.agree = QPushButton(self)
        self.agree.setObjectName("termsAgree")
        for button in (self.decline, self.agree):
            button.setAutoDefault(False)
            actions.addWidget(button)
        root.addLayout(actions)
        self.zh.clicked.connect(lambda: self.change_language("zh"))
        self.en.clicked.connect(lambda: self.change_language("en"))
        self.decline.clicked.connect(self.reject)
        self.agree.clicked.connect(self.accept)
        self.apply_theme()
        self.focus_visibility = NativeFocusVisibilityController(
            self, lambda: (self.zh, self.en, self.reader, self.license_list,
                           *self.document_buttons.values(), self.back, self.decline, self.agree),
            effective_theme=self.effective_theme, safe_anchor=self,
            default_action=lambda: None, focused_target_action=self.activate_focused_button,
            parent=self,
        )
        QApplication.styleHints().colorSchemeChanged.connect(self.apply_theme)
        self.translate()

    def activate_focused_button(self, target) -> bool:
        if target not in (self.back, self.zh, self.en, *self.document_buttons.values(), self.decline, self.agree):
            return False
        target.click()
        return True

    def apply_theme(self, *_args) -> None:
        preference = self.settings.manager.get("theme")
        dark = preference == "dark" or (
            preference == "auto"
            and QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        )
        self.effective_theme = "DARK" if dark else "LIGHT"
        surface, text, border, accent = (
            ("#151625", "#e2e4f0", "#33354d", "#6366f1") if dark
            else ("#f7f3fb", "#2d2640", "#d8d0e6", "#8b5cf6")
        )
        font = QFont(self.font())
        scale = normalize_ui_font_scale(self.settings.manager.get("ui_font_scale"))
        font.setPixelSize(scaled_font_pixel_size(14, scale))
        self.setFont(font)
        self.reader.setFont(font)
        self.license_list.setFont(font)
        self.setStyleSheet(
            f"QDialog#pdmTerms{{background:{surface};color:{text};}}"
            f"QLabel{{color:{text};}}"
            f"QTextBrowser{{background:{surface};color:{text};border:1px solid {border};padding:14px;}}"
            f"QListWidget{{background:{surface};color:{text};border:1px solid {border};padding:8px;}}"
            f"QListWidget::item{{padding:10px;}}QListWidget::item:selected{{background:{border};}}"
            f"QPushButton{{color:{text};background:transparent;border:1px solid {border};border-radius:6px;padding:9px 15px;}}"
            f"QPushButton:hover,QPushButton:checked{{background:{border};}}"
            "QPushButton:disabled{color:#888888;}"
            f"QPushButton#termsAgree{{background:{accent};color:white;}}"
            "QLabel#termsError{color:#ef4444;}"
        )
        if sys.platform == "win32":
            set_win11_caption_colors(int(self.winId()), surface, text)
        if hasattr(self, "focus_visibility"):
            self.focus_visibility.set_effective_theme(self.effective_theme)

    def translate(self) -> None:
        en = self.settings.language == "en"
        self.setWindowTitle("Cangoo — Open-source license" if en else "小仓 — 开源许可")
        self.title.setText(("Cangoo · " + self.content["version"]) if en else ("小仓 · " + self.content["version"]))
        self.back.setText("Back" if en else "返回")
        for identifier, chinese, english in (("agpl", "许可证全文", "Full\nlicense"),
                                             ("openssl", "OpenSSL 附加许可", "OpenSSL\npermission"),
                                             ("third-party", "第三方声明", "Third-party\nnotices")):
            button = self.document_buttons[identifier]
            button.setText(english if en else chinese)
            button.setAccessibleName((english if en else chinese).replace("\n", " "))
        self.render_document()
        self.zh.setChecked(not en)
        self.en.setChecked(en)
        self.decline.setText("Exit" if en else "退出")
        self.agree.setText("Continue" if en else "继续使用")

    def open_document(self, identifier: str) -> None:
        valid = identifier in {"home", "agpl", "openssl", "third-party"}
        if identifier.startswith("third-party/"):
            index = identifier.removeprefix("third-party/")
            valid = index.isascii() and index.isdecimal() and len(index) <= 3 and int(index) < len(self.content["licenses"])
        if not valid or identifier == self._document:
            return
        current = self.license_list if self._document == "third-party" else self.reader
        self._scroll_positions[self._document] = current.verticalScrollBar().value()
        previous = self._document
        self._document = identifier
        self.render_document()
        target = self.document_buttons.get(previous) if identifier == "home" else None
        (target or (self.license_list if identifier == "third-party" else self.reader)).setFocus()

    def go_back(self) -> None:
        self.open_document("third-party" if self._document.startswith("third-party/") else "home")

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self._document != "home":
            self.go_back()
            event.accept()
            return
        super().keyPressEvent(event)

    def render_document(self) -> None:
        language = self.settings.language
        self.back.setEnabled(self._document != "home")
        self.back.setVisible(self._document != "home")
        self.document_links.setVisible(self._document == "home")
        self.list_intro.setVisible(self._document == "third-party")
        self.list_intro.setText(self.content["licenseIntro"][language])
        self.reading_area.setCurrentWidget(self.license_list if self._document == "third-party" else self.reader)
        self.layout().activate()
        if self._document == "third-party":
            title = "Third-party notices" if language == "en" else "第三方声明"
            self.license_list.setAccessibleName(title)
            self.title.setText(title)
            self.license_list.verticalScrollBar().setValue(self._scroll_positions.get(self._document, 0))
            return
        self.title.setText(("Cangoo · " if language == "en" else "小仓 · ") + self.content["version"])
        if self._document == "home":
            title = "Open-source license" if language == "en" else "开源许可"
            body = self.content["terms"][language]
        elif self._document in {"agpl", "openssl"}:
            document = self.content["license_documents"][self._document]
            title = document["title"][language]
            body = f'<p>{escape(document["intro"][language])}</p>' + self.plain_paragraphs(document["text"])
        else:
            license = self.content["licenses"][int(self._document.split("/")[1])]
            title, body = license["name"], self.plain_paragraphs(license["text"])
        self.reader.setAccessibleName(title)
        self.reader.setHtml(f"<h2>{escape(title)}</h2>{body}")
        self.reader.verticalScrollBar().setValue(self._scroll_positions.get(self._document, 0))

    @staticmethod
    def plain_paragraphs(value: str) -> str:
        return "<p>" + escape(value).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"

    def show_failure(self) -> None:
        self.error.setText(
            "Could not save settings. Check folder permissions and retry. If it keeps failing, exit and restart."
            if self.settings.language == "en" else
            "无法保存设置，请检查目录权限后重试；若持续失败，请退出并重新启动。"
        )
        self.error.setAccessibleName(self.error.text())

    def change_language(self, language: str) -> None:
        current = self.license_list if self._document == "third-party" else self.reader
        self._scroll_positions[self._document] = current.verticalScrollBar().value()
        try:
            self.settings.set_language(language)
        except M4SettingsCommitError:
            self.zh.setChecked(self.settings.language == "zh")
            self.en.setChecked(self.settings.language == "en")
            self.show_failure()
            return
        self.error.clear()
        self.translate()

    def accept(self) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            self.settings.accept(self.content["terms_version"])
        except M4SettingsCommitError:
            # 这里只记录本次告知；AGPL不以接受或成功保存记录作为运行条件。
            pass
        finally:
            self._busy = False
        super().accept()


def ensure_terms_accepted(settings_file: Path) -> bool:
    catalog = M4ResourceCatalog()
    payload = catalog.payload_for_url(QUrl("pdm://app/assets/help/content.json"))
    if payload is None:
        raise RuntimeError("terms resource is unavailable")
    content = json.loads(payload.content)
    settings = TermsSettings(settings_file)
    if settings.accepted(content["terms_version"]):
        return True
    dialog = TermsDialog(settings, content)
    try:
        return dialog.exec() == QDialog.DialogCode.Accepted
    finally:
        dialog.focus_visibility.dispose()
        dialog.deleteLater()
