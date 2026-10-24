"""Locked-down WebEngine profile, page, and ``pdm://app`` scheme handler."""

from __future__ import annotations

from collections import Counter
import re
from types import MappingProxyType
from typing import Mapping

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QUrl
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestJob,
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
)

from .resources import (
    APP_HOST,
    APP_SCHEME,
    ENTRY_PATH,
    ResourceCatalog,
    ResourcePayload,
)
from .diagnostics import ConsoleLevel, FixedDiagnosticRecorder


_scheme_registered = False
_ENTRY_PATH = re.compile(r"^/[a-z0-9][a-z0-9_./-]{0,127}$")

DISABLED_WEB_ATTRIBUTES: Mapping[str, QWebEngineSettings.WebAttribute] = (
    MappingProxyType(
        {
            "accelerated_2d_canvas": (
                QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled
            ),
            # Qt 6.9 的原生委托不支持此缓存；6.10 起才提供显式开关。
            **(
                {"back_forward_cache": QWebEngineSettings.WebAttribute.BackForwardCacheEnabled}
                if hasattr(QWebEngineSettings.WebAttribute, "BackForwardCacheEnabled")
                else {}
            ),
            "dns_prefetch": QWebEngineSettings.WebAttribute.DnsPrefetchEnabled,
            "error_pages": QWebEngineSettings.WebAttribute.ErrorPageEnabled,
            "full_screen": QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
            "geolocation_on_insecure_origins": (
                QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins
            ),
            "hyperlink_auditing": (
                QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled
            ),
            "javascript_clipboard": (
                QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard
            ),
            "javascript_paste": (
                QWebEngineSettings.WebAttribute.JavascriptCanPaste
            ),
            "javascript_window_activation": (
                QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript
            ),
            "javascript_windows": (
                QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows
            ),
            "local_file_access": (
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls
            ),
            "local_remote_access": (
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls
            ),
            "local_storage": QWebEngineSettings.WebAttribute.LocalStorageEnabled,
            "mixed_content": (
                QWebEngineSettings.WebAttribute.AllowRunningInsecureContent
            ),
            "navigate_on_drop": (
                QWebEngineSettings.WebAttribute.NavigateOnDropEnabled
            ),
            "page_icons": QWebEngineSettings.WebAttribute.AutoLoadIconsForPage,
            "pdf_viewer": QWebEngineSettings.WebAttribute.PdfViewerEnabled,
            "plugins": QWebEngineSettings.WebAttribute.PluginsEnabled,
            "reading_from_canvas": (
                QWebEngineSettings.WebAttribute.ReadingFromCanvasEnabled
            ),
            "screen_capture": QWebEngineSettings.WebAttribute.ScreenCaptureEnabled,
            "touch_icons": QWebEngineSettings.WebAttribute.TouchIconsEnabled,
            "webgl": QWebEngineSettings.WebAttribute.WebGLEnabled,
        }
    )
)

ENABLED_SECURITY_ATTRIBUTES: Mapping[
    str, QWebEngineSettings.WebAttribute
] = MappingProxyType(
    {
        "playback_requires_user_gesture": (
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture
        ),
        "webrtc_public_interfaces_only": (
            QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly
        ),
    }
)

FORBIDDEN_WEB_ACTIONS = frozenset(
    {
        QWebEnginePage.WebAction.CopyImageToClipboard,
        QWebEnginePage.WebAction.CopyImageUrlToClipboard,
        QWebEnginePage.WebAction.CopyLinkToClipboard,
        QWebEnginePage.WebAction.CopyMediaUrlToClipboard,
        QWebEnginePage.WebAction.DownloadImageToDisk,
        QWebEnginePage.WebAction.DownloadLinkToDisk,
        QWebEnginePage.WebAction.DownloadMediaToDisk,
        QWebEnginePage.WebAction.InspectElement,
        QWebEnginePage.WebAction.OpenLinkInNewBackgroundTab,
        QWebEnginePage.WebAction.OpenLinkInNewTab,
        QWebEnginePage.WebAction.OpenLinkInNewWindow,
        QWebEnginePage.WebAction.SavePage,
        QWebEnginePage.WebAction.ViewSource,
    }
)


def register_app_scheme() -> None:
    """Register ``pdm`` before QApplication/WebEngine initialization."""

    global _scheme_registered
    if _scheme_registered:
        return
    scheme = QWebEngineUrlScheme(APP_SCHEME)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
    QWebEngineUrlScheme.registerScheme(scheme)
    _scheme_registered = True


class AppRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Fail closed for every URL outside the immutable app catalog."""

    def __init__(self, catalog: ResourceCatalog, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self.allowed_count = 0
        self.blocked_schemes: Counter[str] = Counter()

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:  # noqa: N802
        if self._catalog.payload_for_url(info.requestUrl()) is not None:
            self.allowed_count += 1
            return
        scheme = info.requestUrl().scheme().lower() or "<empty>"
        self.blocked_schemes[scheme] += 1
        info.block(True)


def payload_for_request(
    catalog: ResourceCatalog,
    method: bytes,
    url: QUrl,
) -> ResourcePayload | None:
    """Resolve only a GET for an exact catalog URL."""

    if bytes(method) != b"GET":
        return None
    return catalog.payload_for_url(url)


class AppSchemeHandler(QWebEngineUrlSchemeHandler):
    """Serve only immutable catalog bytes; no URL is converted into a path."""

    def __init__(self, catalog: ResourceCatalog, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self.served_count = 0
        self.rejected_count = 0

    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:  # noqa: N802
        payload = payload_for_request(
            self._catalog,
            bytes(job.requestMethod()),
            job.requestUrl(),
        )
        if payload is None:
            self.rejected_count += 1
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        buffer = QBuffer(job)
        buffer.setData(QByteArray(payload.content))
        if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            self.rejected_count += 1
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return
        self.served_count += 1
        job.reply(QByteArray(payload.mime_type), buffer)


class AppPage(QWebEnginePage):
    """A page that can never navigate its main frame away from the app entry."""

    def __init__(
        self,
        profile: QWebEngineProfile,
        parent: QObject | None = None,
        *,
        diagnostics: FixedDiagnosticRecorder | None = None,
        page_generation: int = 1,
        entry_path: str = ENTRY_PATH,
    ) -> None:
        super().__init__(profile, parent)
        if type(page_generation) is not int or page_generation <= 0:
            raise ValueError("page generation must be a positive integer")
        if (
            type(entry_path) is not str
            or _ENTRY_PATH.fullmatch(entry_path) is None
            or "/../" in entry_path
            or entry_path.endswith("/..")
        ):
            raise ValueError("entry path must be fixed and absolute")
        self.page_generation = page_generation
        self.entry_path = entry_path
        self.diagnostics = diagnostics or FixedDiagnosticRecorder()
        self.rejected_navigations: Counter[str] = Counter()
        self.rejected_web_actions: Counter[str] = Counter()
        self.denied_feature_count = 0
        self.console_error_count = 0
        self.console_message_counts: Counter[str] = Counter()
        self.rejected_devtools_count = 0
        self.featurePermissionRequested.connect(self._deny_feature)
        for action in FORBIDDEN_WEB_ACTIONS:
            page_action = self.action(action)
            page_action.changed.connect(
                lambda page_action=page_action: self._keep_action_disabled(
                    page_action
                )
            )
            self._keep_action_disabled(page_action)

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:  # noqa: N802
        allowed = (
            is_main_frame
            and url.scheme().lower() == "pdm"
            and url.host().lower() == APP_HOST
            and url.path() == self.entry_path
            and not url.hasQuery()
            and not url.hasFragment()
            and not url.userInfo()
            and url.port(-1) == -1
        )
        if not allowed:
            self.rejected_navigations[url.scheme().lower() or "<empty>"] += 1
        return allowed

    def createWindow(self, _window_type):  # noqa: N802
        self.rejected_navigations["new-window"] += 1
        return None

    def triggerAction(self, action, checked: bool = False) -> None:  # noqa: N802
        if action in FORBIDDEN_WEB_ACTIONS:
            self.rejected_web_actions[action.name] += 1
            return
        super().triggerAction(action, checked)

    @staticmethod
    def _keep_action_disabled(action) -> None:
        if action.isEnabled():
            action.setEnabled(False)

    def javaScriptConsoleMessage(self, level, message: str, line: int, source: str) -> None:  # noqa: N802
        del message, line, source
        if (
            level
            == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel
        ):
            normalized = ConsoleLevel.ERROR
            self.console_error_count += 1
        elif (
            level
            == QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel
        ):
            normalized = ConsoleLevel.WARNING
        else:
            normalized = ConsoleLevel.INFO
        self.console_message_counts[normalized.value] += 1
        self.diagnostics.record_console(
            normalized,
            page_generation=self.page_generation,
        )

    def setDevToolsPage(self, _devtools_page) -> None:  # noqa: N802
        """Reject Python-side DevTools attachment without retaining a page."""

        self.rejected_devtools_count += 1

    def setInspectedPage(self, _inspected_page) -> None:  # noqa: N802
        """Reject Python-side inspected-page attachment."""

        self.rejected_devtools_count += 1

    def _deny_feature(self, origin, feature) -> None:
        self.denied_feature_count += 1
        self.setFeaturePermission(
            origin,
            feature,
            QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
        )


def configure_page_settings(settings: QWebEngineSettings) -> None:
    """Apply the fail-closed production page capability policy."""

    for attribute in DISABLED_WEB_ATTRIBUTES.values():
        settings.setAttribute(attribute, False)
    for attribute in ENABLED_SECURITY_ATTRIBUTES.values():
        settings.setAttribute(attribute, True)
    settings.setUnknownUrlSchemePolicy(
        QWebEngineSettings.UnknownUrlSchemePolicy.DisallowUnknownUrlSchemes
    )


class AppWebProfile:
    """Own all WebEngine objects so their lifetime follows the native host."""

    def __init__(
        self,
        parent: QObject,
        catalog: ResourceCatalog | None = None,
        *,
        diagnostics: FixedDiagnosticRecorder | None = None,
        page_generation: int = 1,
    ) -> None:
        self.catalog = catalog or ResourceCatalog()
        self.diagnostics = diagnostics or FixedDiagnosticRecorder()
        self.profile = QWebEngineProfile(parent)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        self.profile.setSpellCheckEnabled(False)

        self.scheme_handler = AppSchemeHandler(self.catalog, self.profile)
        self.profile.installUrlSchemeHandler(APP_SCHEME, self.scheme_handler)
        self.interceptor = AppRequestInterceptor(self.catalog, self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.cancelled_download_count = 0
        self.profile.downloadRequested.connect(self._cancel_download)

        self.page = AppPage(
            self.profile,
            parent,
            diagnostics=self.diagnostics,
            page_generation=page_generation,
        )
        configure_page_settings(self.page.settings())

    def _cancel_download(self, download) -> None:
        self.cancelled_download_count += 1
        download.cancel()

    @property
    def is_off_the_record(self) -> bool:
        return self.profile.isOffTheRecord()
