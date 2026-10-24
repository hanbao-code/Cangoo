"""Qt 顶层表面的局部焦点可见性控制。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import Enum
from weakref import ReferenceType, ref

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QFocusFrame,
    QLineEdit,
    QPlainTextEdit,
    QProxyStyle,
    QStyle,
    QStyleOption,
    QTextEdit,
    QTextBrowser,
    QWidget,
)
from shiboken6 import isValid


_DARK_ACCENT = QColor("#6366f1")
_LIGHT_ACCENT = QColor("#8b5cf6")
_FRAME_EXPANSION = 4
_FRAME_PEN_WIDTH = 2


class FocusVisibilityMode(str, Enum):
    """一个 Qt 焦点作用域的瞬态可见模式。"""

    DEFAULT = "default"
    KEYBOARD = "keyboard"


TargetProvider = Callable[[], Sequence[QWidget]]
DefaultAction = Callable[[], None]
FocusedTargetAction = Callable[[QWidget], bool]


def _is_live_widget(widget: QWidget | None) -> bool:
    return bool(isinstance(widget, QWidget) and isValid(widget))


def _is_descendant(widget: QWidget, scope: QWidget) -> bool:
    current: QWidget | None = widget
    while current is not None:
        if current is scope:
            return True
        current = current.parentWidget()
    return False


def _is_editable_text_widget(widget: QWidget) -> bool:
    if isinstance(widget, QTextBrowser) and widget.isReadOnly():
        return False
    if isinstance(
        widget,
        (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox),
    ):
        return True
    return isinstance(widget, QComboBox) and widget.isEditable()


class ManagedFocusProxyStyle(QProxyStyle):
    """只屏蔽显式受管理控件的 Qt 内部焦点矩形。"""

    def drawPrimitive(  # noqa: N802
        self,
        element: QStyle.PrimitiveElement,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        style_object = option.styleObject or widget
        if (
            element == QStyle.PrimitiveElement.PE_FrameFocusRect
            and style_object is not None
            and bool(style_object.property("pdmFocusVisualManaged"))
        ):
            return
        super().drawPrimitive(element, option, painter, widget)


def install_managed_focus_fallback(
    widget: QWidget,
    *,
    radius: int | None = None,
) -> ManagedFocusProxyStyle:
    """先建立单框回退，再由就绪 controller 接管外围绘制。"""

    if not _is_live_widget(widget):
        raise TypeError("managed focus target must be a live QWidget")
    if radius is not None:
        widget.setProperty("pdmFocusRadius", max(0, int(radius)))
    widget.setProperty("pdmFocusVisualManaged", True)
    widget.setProperty("pdmFocusFrameReady", False)
    proxy = ManagedFocusProxyStyle()
    proxy.setParent(widget)
    widget.setStyle(proxy)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
    return proxy


class PurpleFocusFrame(QFocusFrame):
    """不参与布局或命中的单一主题紫色焦点框。"""

    def __init__(
        self,
        scope: QWidget,
        *,
        effective_theme: str,
    ) -> None:
        super().__init__(scope)
        self.setObjectName("pdmPurpleFocusFrame")
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._scope_ref: ReferenceType[QWidget] = ref(scope)
        self._target_ref: ReferenceType[QWidget] | None = None
        self._tracked_refs: list[ReferenceType[QWidget]] = []
        self._ring_color = QColor()
        self._radius = 0
        self.set_effective_theme(effective_theme)
        self.hide()

    @property
    def ring_color(self) -> QColor:
        return QColor(self._ring_color)

    @property
    def ring_radius(self) -> int:
        return self._radius

    @property
    def target_widget(self) -> QWidget | None:
        if self._target_ref is None:
            return None
        target = self._target_ref()
        return target if _is_live_widget(target) else None

    def set_effective_theme(self, value: str) -> None:
        if value not in {"DARK", "LIGHT"}:
            raise ValueError("effective theme must be DARK or LIGHT")
        self._ring_color = QColor(
            _DARK_ACCENT if value == "DARK" else _LIGHT_ACCENT
        )
        self.update()

    def set_target(self, target: QWidget | None) -> None:
        current = self.target_widget
        if current is target and target is not None:
            self._sync_geometry()
            return
        self._untrack_target()
        if not _is_live_widget(target):
            self.hide()
            return
        scope = self._scope_ref()
        if not _is_live_widget(scope) or not _is_descendant(target, scope):
            self.hide()
            return
        self._target_ref = ref(target, self._on_weak_target_gone)
        target.destroyed.connect(self._on_target_destroyed)
        current_widget: QWidget | None = target
        while current_widget is not None:
            current_widget.installEventFilter(self)
            self._tracked_refs.append(ref(current_widget))
            if current_widget is scope:
                break
            current_widget = current_widget.parentWidget()
        self._radius = max(
            0,
            int(target.property("pdmFocusRadius") or 0),
        )
        self._sync_geometry()

    def clear_target(self) -> None:
        self._untrack_target()
        self.hide()

    def _on_weak_target_gone(self, _reference: object) -> None:
        self._target_ref = None
        self._tracked_refs.clear()
        self.hide()

    def _on_target_destroyed(self, _target: object = None) -> None:
        self._target_ref = None
        self._tracked_refs.clear()
        self.hide()

    def _untrack_target(self) -> None:
        target = self.target_widget
        if target is not None:
            try:
                target.destroyed.disconnect(self._on_target_destroyed)
            except (RuntimeError, TypeError):
                pass
        for tracked_ref in self._tracked_refs:
            tracked = tracked_ref()
            if _is_live_widget(tracked):
                tracked.removeEventFilter(self)
        self._target_ref = None
        self._tracked_refs.clear()

    def _sync_geometry(self) -> None:
        scope = self._scope_ref()
        target = self.target_widget
        if (
            not _is_live_widget(scope)
            or not _is_live_widget(target)
            or not target.isVisible()
            or not target.isEnabled()
        ):
            self.hide()
            return
        top_left = target.mapTo(scope, QPoint(0, 0))
        target_rect = QRect(top_left, target.size())
        self.setGeometry(
            target_rect.adjusted(
                -_FRAME_EXPANSION,
                -_FRAME_EXPANSION,
                _FRAME_EXPANSION,
                _FRAME_EXPANSION,
            )
        )
        self.raise_()
        self.show()
        self.update()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() in {
            QEvent.Type.Move,
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
            QEvent.Type.EnabledChange,
            QEvent.Type.ParentChange,
            QEvent.Type.ZOrderChange,
        }:
            self._sync_geometry()
        return False

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self._ring_color, _FRAME_PEN_WIDTH))
        frame_rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(frame_rect, self._radius, self._radius)


class NativeFocusVisibilityController(QObject):
    """以真实 Tab 证据控制一个 Qt 作用域的唯一外框。"""

    _POINTER_PRESS_TYPES = {
        QEvent.Type.MouseButtonPress,
        QEvent.Type.NonClientAreaMouseButtonPress,
        QEvent.Type.TabletPress,
        QEvent.Type.TouchBegin,
    }

    def __init__(
        self,
        scope: QWidget,
        target_provider: TargetProvider,
        *,
        effective_theme: str,
        safe_anchor: QWidget | None = None,
        default_action: DefaultAction | None = None,
        focused_target_action: FocusedTargetAction | None = None,
        parent: QObject | None = None,
    ) -> None:
        if not _is_live_widget(scope):
            raise TypeError("focus scope must be a live QWidget")
        if not callable(target_provider):
            raise TypeError("target provider must be callable")
        if effective_theme not in {"DARK", "LIGHT"}:
            raise ValueError("effective theme must be DARK or LIGHT")
        if safe_anchor is not None and not _is_descendant(safe_anchor, scope):
            raise ValueError("safe anchor must belong to focus scope")
        super().__init__(parent or scope)
        application = QApplication.instance()
        if not isinstance(application, QApplication):
            raise RuntimeError("focus controller requires QApplication")
        self._application = application
        self._scope_ref: ReferenceType[QWidget] = ref(scope)
        anchor = safe_anchor or scope
        self._safe_anchor_ref: ReferenceType[QWidget] = ref(anchor)
        self._target_provider = target_provider
        self._default_action = default_action
        self._focused_target_action = focused_target_action
        self._mode = FocusVisibilityMode.DEFAULT
        self._ready = False
        self._disposed = False
        self._managed: dict[
            int,
            tuple[ReferenceType[QWidget], ManagedFocusProxyStyle],
        ] = {}
        self._managing_ids: set[int] = set()
        self._frame = PurpleFocusFrame(
            scope,
            effective_theme=effective_theme,
        )
        self._application.installEventFilter(self)
        try:
            self._ready = True
            self._synchronize_managed_targets()
            self.refresh()
        except Exception:
            self._ready = False
            self._application.removeEventFilter(self)
            self._set_managed_ready(False)
            self._frame.clear_target()
            raise

    @property
    def mode(self) -> FocusVisibilityMode:
        return self._mode

    @property
    def ready(self) -> bool:
        return self._ready and not self._disposed

    def reset(self) -> None:
        self._mode = FocusVisibilityMode.DEFAULT
        self._frame.clear_target()

    def clear(self) -> None:
        self.reset()

    def set_effective_theme(self, value: str) -> None:
        self._frame.set_effective_theme(value)
        self.refresh()

    def refresh(self) -> None:
        if not self.ready:
            return
        self._synchronize_managed_targets()
        if self._mode is FocusVisibilityMode.DEFAULT:
            self._frame.clear_target()
            return
        scope = self._scope()
        if scope is None:
            self._frame.clear_target()
            return
        targets = self._valid_targets()
        active = QApplication.focusWidget()
        if active in targets:
            if _is_editable_text_widget(active):
                self._frame.clear_target()
            else:
                self._frame.set_target(active)
            return
        anchor = self._safe_anchor()
        if active is anchor or _is_editable_text_widget(active):
            self._frame.clear_target()
            return
        self._frame.clear_target()
        if targets and (active is None or _is_descendant(active, scope)):
            targets[0].setFocus(Qt.FocusReason.OtherFocusReason)
            if QApplication.focusWidget() is not targets[0]:
                return
            if _is_editable_text_widget(targets[0]):
                self._frame.clear_target()
            else:
                self._frame.set_target(targets[0])

    def focus_safe_anchor(
        self,
        reason: Qt.FocusReason = Qt.FocusReason.OtherFocusReason,
    ) -> None:
        anchor = self._safe_anchor()
        if anchor is None:
            return
        anchor.setFocus(reason)
        self._frame.clear_target()

    def focus_next(self, *, backwards: bool) -> bool:
        if not self.ready:
            return False
        targets = self._valid_targets()
        if not targets:
            return False
        active = QApplication.focusWidget()
        if active in targets:
            current_index = targets.index(active)
            next_index = (
                (current_index - 1) % len(targets)
                if backwards
                else (current_index + 1) % len(targets)
            )
            target = targets[next_index]
            if target is active:
                return False
        else:
            target = targets[-1] if backwards else targets[0]
        previous_mode = self._mode
        self._mode = FocusVisibilityMode.KEYBOARD
        target.setFocus(
            Qt.FocusReason.BacktabFocusReason
            if backwards
            else Qt.FocusReason.TabFocusReason
        )
        if QApplication.focusWidget() is not target:
            self._mode = previous_mode
            self.refresh()
            return False
        self.refresh()
        return True

    def dispose(self) -> None:
        if getattr(self, "_disposed", True):
            return
        self.reset()
        self._ready = False
        self._disposed = True
        self._application.removeEventFilter(self)
        self._set_managed_ready(False)
        self._managed.clear()
        self._managing_ids.clear()
        if _is_live_widget(self._frame):
            self._frame.deleteLater()

    def _scope(self) -> QWidget | None:
        scope = self._scope_ref()
        return scope if _is_live_widget(scope) else None

    def _safe_anchor(self) -> QWidget | None:
        anchor = self._safe_anchor_ref()
        return anchor if _is_live_widget(anchor) else None

    def _belongs_to_scope(self, watched: QObject) -> bool:
        scope = self._scope()
        return bool(
            scope is not None
            and isinstance(watched, QWidget)
            and _is_descendant(watched, scope)
        )

    def _valid_targets(self) -> list[QWidget]:
        scope = self._scope()
        if scope is None:
            return []
        try:
            candidates = tuple(self._target_provider())
        except Exception:
            return []
        targets: list[QWidget] = []
        seen: set[int] = set()
        for candidate in candidates:
            if not _is_live_widget(candidate):
                continue
            identity = id(candidate)
            if identity in seen:
                continue
            seen.add(identity)
            if (
                not _is_descendant(candidate, scope)
                or not candidate.isVisible()
                or not candidate.isEnabled()
                or candidate.focusPolicy() == Qt.FocusPolicy.NoFocus
            ):
                continue
            targets.append(candidate)
        return targets

    def _synchronize_managed_targets(self) -> None:
        for identity, (widget_ref, _proxy) in tuple(self._managed.items()):
            if not _is_live_widget(widget_ref()):
                self._managed.pop(identity, None)
        try:
            candidates = tuple(self._target_provider())
        except Exception:
            candidates = ()
        scope = self._scope()
        if scope is None:
            return
        for candidate in candidates:
            if (
                not _is_live_widget(candidate)
                or not _is_descendant(candidate, scope)
                or _is_editable_text_widget(candidate)
            ):
                continue
            identity = id(candidate)
            if identity in self._managed:
                candidate.setProperty("pdmFocusFrameReady", self.ready)
                continue
            if identity in self._managing_ids:
                continue
            self._managing_ids.add(identity)
            try:
                proxy = install_managed_focus_fallback(candidate)
                self._managed[identity] = (ref(candidate), proxy)
                candidate.setProperty("pdmFocusFrameReady", self.ready)
                candidate.style().unpolish(candidate)
                candidate.style().polish(candidate)
                candidate.update()
            finally:
                self._managing_ids.discard(identity)

    def _set_managed_ready(self, ready: bool) -> None:
        for widget_ref, _proxy in tuple(self._managed.values()):
            widget = widget_ref()
            if not _is_live_widget(widget):
                continue
            widget.setProperty("pdmFocusFrameReady", ready)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    @staticmethod
    def _is_composing_key(event: QKeyEvent) -> bool:
        composing = getattr(event, "isComposing", None)
        if callable(composing) and composing():
            return True
        try:
            return bool(
                int(event.key()) == 229
                or int(event.nativeVirtualKey()) == 229
            )
        except (AttributeError, TypeError, ValueError):
            return False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if getattr(self, "_disposed", True):
            return False
        event_type = event.type()
        belongs = self._belongs_to_scope(watched)

        if event_type == QEvent.Type.WindowDeactivate and belongs:
            self.reset()
            return False
        if event_type in {QEvent.Type.Hide, QEvent.Type.Close} and belongs:
            if watched is self._scope():
                self.reset()
            else:
                self.refresh()
            return False
        if event_type in self._POINTER_PRESS_TYPES and belongs:
            self.reset()
            return False
        if event_type == QEvent.Type.FocusOut and belongs:
            self._frame.clear_target()
            return False
        if event_type == QEvent.Type.FocusIn and belongs:
            self.refresh()
            return False
        if event_type != QEvent.Type.KeyPress or not belongs:
            return False
        if not isinstance(event, QKeyEvent) or self._is_composing_key(event):
            return False

        key = event.key()
        modifiers = event.modifiers()
        is_plain_activation = (
            key in {Qt.Key.Key_Return, Qt.Key.Key_Enter}
            and modifiers
            in {
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.KeypadModifier,
            }
        )
        if is_plain_activation:
            focused = QApplication.focusWidget()
            if (
                focused is self._safe_anchor()
                and self._default_action is not None
            ):
                self._default_action()
                event.accept()
                return True
            if (
                self._focused_target_action is not None
                and focused in self._valid_targets()
                and self._focused_target_action(focused)
            ):
                event.accept()
                return True
        if key not in {Qt.Key.Key_Tab, Qt.Key.Key_Backtab}:
            return False
        blocked_modifiers = (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.MetaModifier
        )
        if modifiers & blocked_modifiers:
            return False
        backwards = bool(
            key == Qt.Key.Key_Backtab
            or modifiers & Qt.KeyboardModifier.ShiftModifier
        )
        if not self.focus_next(backwards=backwards):
            return False
        event.accept()
        return True


__all__ = [
    "FocusVisibilityMode",
    "install_managed_focus_fallback",
    "ManagedFocusProxyStyle",
    "NativeFocusVisibilityController",
    "PurpleFocusFrame",
]
