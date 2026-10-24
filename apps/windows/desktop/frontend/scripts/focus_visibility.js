(() => {
  'use strict';

  const root = document.documentElement;
  if (root.dataset.pdmM4Slice !== '1') return;

  const DEFAULT = 'default';
  const KEYBOARD = 'keyboard';
  const MARKER = 'data-pdm-keyboard-ring';
  const NAVIGABLE_SELECTOR = (
    'button,a[href],input,select,textarea,'
    + '[contenteditable="true"],[tabindex]'
  );
  const NON_TEXT_INPUT_TYPES = new Set([
    'button',
    'checkbox',
    'color',
    'file',
    'hidden',
    'image',
    'radio',
    'range',
    'reset',
    'submit',
  ]);
  const STABLE_KEY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9:_-]{0,127}$/;
  const STABLE_ID_PATTERN = /^[A-Za-z][A-Za-z0-9:_.-]{0,127}$/;
  const NATIVE_SLOT_NAMES = new Set(['tray', 'power']);

  let mode = DEFAULT;
  let nextScopeGeneration = 0;
  const scopeStack = [];
  const nativeSlots = new Map([
    ['tray', null],
    ['power', null],
  ]);

  function clearMarker() {
    for (const element of document.querySelectorAll(`[${MARKER}="true"]`)) {
      element.removeAttribute(MARKER);
    }
  }

  function currentScope() {
    for (let index = scopeStack.length - 1; index >= 0; index -= 1) {
      const entry = scopeStack[index];
      if (entry.overlay.isConnected) return entry.overlay;
    }
    return document;
  }

  function scopeContains(scope, element) {
    if (!(element instanceof HTMLElement)) return false;
    if (scope === document) return document.contains(element);
    return scope instanceof HTMLElement && scope.contains(element);
  }

  function generationForScope(scope) {
    if (scope === document) return 0;
    const entry = scopeStack.find((candidate) => candidate.overlay === scope);
    return entry ? entry.generation : -1;
  }

  function isRendered(element) {
    return Boolean(
      element instanceof HTMLElement
      && element.isConnected
      && !element.hidden
      && element.getClientRects().length > 0
      && element.getAttribute('aria-hidden') !== 'true'
    );
  }

  function isNativeDisabled(element) {
    return Boolean('disabled' in element && element.disabled === true);
  }

  function isNavigable(element, scope = currentScope()) {
    return Boolean(
      isRendered(element)
      && scopeContains(scope, element)
      && !isNativeDisabled(element)
      && element.tabIndex !== -1
    );
  }

  function navigableTargets(scope = currentScope()) {
    return Array.from(scope.querySelectorAll(NAVIGABLE_SELECTOR)).filter(
      (element) => isNavigable(element, scope),
    );
  }

  function isEditableText(element) {
    if (element instanceof HTMLTextAreaElement) return true;
    if (
      element instanceof HTMLElement
      && element.getAttribute('contenteditable') === 'true'
    ) {
      return true;
    }
    if (!(element instanceof HTMLInputElement)) return false;
    return !NON_TEXT_INPUT_TYPES.has(String(element.type || 'text').toLowerCase());
  }

  function refresh() {
    clearMarker();
    if (mode !== KEYBOARD) return;
    const scope = currentScope();
    const active = document.activeElement;
    if (
      !isNavigable(active, scope)
      || isEditableText(active)
    ) {
      return;
    }
    active.setAttribute(MARKER, 'true');
  }

  function reset() {
    mode = DEFAULT;
    clearMarker();
  }

  function clear() {
    reset();
    scopeStack.length = 0;
    nativeSlots.set('tray', null);
    nativeSlots.set('power', null);
  }

  function focusApplicationRoot() {
    reset();
    const applicationRoot = document.getElementById('main-app');
    if (!(applicationRoot instanceof HTMLElement)) return false;
    applicationRoot.tabIndex = -1;
    applicationRoot.focus({preventScroll: true});
    clearMarker();
    return document.activeElement === applicationRoot;
  }

  function stableValue(value, pattern) {
    const normalized = typeof value === 'string' ? value : '';
    return pattern.test(normalized) ? normalized : '';
  }

  function descriptorFor(element, scope = currentScope()) {
    if (!scopeContains(scope, element) || !isRendered(element)) return null;
    const id = stableValue(element.id, STABLE_ID_PATTERN);
    const focusKey = stableValue(
      element.dataset.pdmNativeFocusKey,
      STABLE_KEY_PATTERN,
    );
    const recordId = stableValue(
      element.dataset.pdmRecordId || element.dataset.recordId,
      /^\d{1,18}$/,
    );
    const action = stableValue(
      element.dataset.pdmFocusAction || element.dataset.action,
      STABLE_KEY_PATTERN,
    );
    if (!id && !focusKey && !(recordId && action)) return null;
    return Object.freeze({
      ...(id ? {id} : {}),
      ...(focusKey ? {focusKey} : {}),
      ...(recordId ? {recordId} : {}),
      ...(action ? {action} : {}),
      scopeGeneration: generationForScope(scope),
    });
  }

  function capture(captureRoot = document) {
    if (
      captureRoot !== document
      && !(captureRoot instanceof HTMLElement)
    ) {
      return null;
    }
    const active = document.activeElement;
    if (!scopeContains(captureRoot, active)) return null;
    return descriptorFor(active, currentScope());
  }

  function isRestorable(element, scope) {
    return Boolean(
      isRendered(element)
      && scopeContains(scope, element)
      && !isNativeDisabled(element)
      && !element.matches('.titlebar-controls .titlebar-ctrl')
    );
  }

  function findByStableKey(scope, key) {
    const stableKey = stableValue(key, STABLE_KEY_PATTERN);
    if (!stableKey) return null;
    const byId = document.getElementById(stableKey);
    if (isRestorable(byId, scope)) return byId;
    for (const element of scope.querySelectorAll('[data-pdm-native-focus-key]')) {
      if (
        element.dataset.pdmNativeFocusKey === stableKey
        && isRestorable(element, scope)
      ) {
        return element;
      }
    }
    return null;
  }

  function findFromDescriptor(scope, descriptor) {
    if (!descriptor || typeof descriptor !== 'object') return null;
    if (descriptor.scopeGeneration !== generationForScope(scope)) return null;
    if (typeof descriptor.focusKey === 'string') {
      const byKey = findByStableKey(scope, descriptor.focusKey);
      if (byKey) return byKey;
    }
    if (typeof descriptor.id === 'string') {
      const byId = document.getElementById(descriptor.id);
      if (isRestorable(byId, scope)) return byId;
    }
    if (
      typeof descriptor.recordId === 'string'
      && typeof descriptor.action === 'string'
    ) {
      for (const element of scope.querySelectorAll(
        '[data-pdm-record-id],[data-record-id]',
      )) {
        if (
          (element.dataset.pdmRecordId || element.dataset.recordId)
            === descriptor.recordId
          && (element.dataset.pdmFocusAction || element.dataset.action)
            === descriptor.action
          && isRestorable(element, scope)
        ) {
          return element;
        }
      }
    }
    return null;
  }

  function resolvedKey(element) {
    const recordId = element.dataset.pdmRecordId || element.dataset.recordId;
    const action = element.dataset.pdmFocusAction || element.dataset.action;
    return String(
      element.dataset.pdmNativeFocusKey
      || element.id
      || (
        recordId && action
          ? `${recordId}:${action}`
          : ''
      ),
    );
  }

  function restore(descriptor, fallbackKeys = []) {
    const scope = currentScope();
    let target = findFromDescriptor(scope, descriptor);
    if (!target && Array.isArray(fallbackKeys)) {
      for (const key of fallbackKeys) {
        target = findByStableKey(scope, key);
        if (target) break;
      }
    }
    if (!target && scope === document) {
      const applicationRoot = document.getElementById('main-app');
      if (isRestorable(applicationRoot, document)) target = applicationRoot;
    }
    if (!target && scope instanceof HTMLElement) {
      const scopeRoot = scope.querySelector('.modal') || scope;
      if (isRestorable(scopeRoot, scope)) {
        scopeRoot.tabIndex = -1;
        target = scopeRoot;
      }
    }
    if (!target) {
      clearMarker();
      return '';
    }
    target.focus({preventScroll: true});
    if (document.activeElement !== target) {
      clearMarker();
      return '';
    }
    refresh();
    return resolvedKey(target);
  }

  function preserve(renderRoot, render, fallbackKeys = []) {
    if (typeof render !== 'function') {
      throw new TypeError('render must be a function');
    }
    const descriptor = capture(renderRoot);
    const result = render();
    restore(descriptor, fallbackKeys);
    return result;
  }

  function openScope(overlay, initialSelector = '') {
    if (!(overlay instanceof HTMLElement) || !overlay.isConnected) return false;
    const parentScope = currentScope();
    const returnDescriptor = descriptorFor(
      document.activeElement,
      parentScope,
    );
    nextScopeGeneration += 1;
    const entry = {
      overlay,
      generation: nextScopeGeneration,
      returnDescriptor,
    };
    overlay.dataset.pdmFocusScopeGeneration = String(entry.generation);
    scopeStack.push(entry);
    let target = null;
    if (typeof initialSelector === 'string' && initialSelector) {
      try {
        const selected = overlay.querySelector(initialSelector);
        if (isNavigable(selected, overlay)) target = selected;
      } catch (_error) {
        target = null;
      }
    }
    if (!target) target = navigableTargets(overlay)[0] || null;
    if (!target) {
      clearMarker();
      return false;
    }
    target.focus({preventScroll: true});
    refresh();
    return document.activeElement === target;
  }

  function rememberModalReturn(overlay, returnElement) {
    const entry = scopeStack.find((candidate) => candidate.overlay === overlay);
    if (!entry || !(returnElement instanceof HTMLElement)) return;
    const index = scopeStack.indexOf(entry);
    const parentScope = index > 0 ? scopeStack[index - 1].overlay : document;
    const descriptor = descriptorFor(returnElement, parentScope);
    if (descriptor) entry.returnDescriptor = descriptor;
  }

  function closeScope(detachedOverlay) {
    const index = scopeStack.findIndex(
      (entry) => entry.overlay === detachedOverlay,
    );
    if (index < 0) return '';
    const [entry] = scopeStack.splice(index, 1);
    clearMarker();
    return restore(entry.returnDescriptor);
  }

  function requireNativeSlot(slot) {
    if (!NATIVE_SLOT_NAMES.has(slot)) {
      throw new TypeError('unknown native focus slot');
    }
  }

  function stashNative(slot) {
    requireNativeSlot(slot);
    nativeSlots.set(slot, capture(currentScope()));
    reset();
    return true;
  }

  function restoreNative(slot) {
    requireNativeSlot(slot);
    const descriptor = nativeSlots.get(slot);
    if (!descriptor) return '';
    nativeSlots.set(slot, null);
    reset();
    return restore(descriptor);
  }

  function hotkeyRecordingActive() {
    return Boolean(
      document.querySelector('#quickbar-hotkey-btn.recording')
      || document.querySelector('#quickbar-hotkey-display.recording')
    );
  }

  function onKeyDown(event) {
    if (event.key !== 'Tab') return;
    if (hotkeyRecordingActive()) return;
    if (
      !event.isTrusted
      || event.defaultPrevented
      || event.isComposing
      || event.keyCode === 229
      || event.ctrlKey
      || event.altKey
      || event.metaKey
    ) {
      return;
    }
    const targets = navigableTargets();
    if (!targets.length) return;
    const active = document.activeElement;
    const currentIndex = targets.indexOf(active);
    const nextIndex = currentIndex < 0
      ? (event.shiftKey ? targets.length - 1 : 0)
      : (
        currentIndex + (event.shiftKey ? -1 : 1) + targets.length
      ) % targets.length;
    const target = targets[nextIndex];
    if (!target || target === active) return;
    target.focus();
    if (document.activeElement !== target) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    mode = KEYBOARD;
    refresh();
  }

  function onPointerDown(event) {
    if (!event.isTrusted) return;
    reset();
  }

  function wrapDemoModal() {
    const originalOpen = window.openModal;
    const originalClose = window.closeModal;
    if (
      typeof originalOpen !== 'function'
      || typeof originalClose !== 'function'
    ) {
      return;
    }
    window.openModal = function wrappedOpenModal(html, options = {}) {
      if (document.getElementById('active-modal')) window.closeModal();
      const overlay = originalOpen.call(this, html, options);
      if (!(overlay instanceof HTMLElement)) return overlay;
      if (overlay._focusTimer) {
        window.clearTimeout(overlay._focusTimer);
        overlay._focusTimer = 0;
      }
      openScope(
        overlay,
        options.initialFocusSelector || 'input:not([type="checkbox"]),textarea',
      );
      return overlay;
    };
    window.closeModal = function wrappedCloseModal(...args) {
      const overlay = document.getElementById('active-modal');
      if (overlay instanceof HTMLElement) {
        rememberModalReturn(overlay, overlay._returnFocus);
        overlay._returnFocus = null;
        if (overlay._focusTimer) {
          window.clearTimeout(overlay._focusTimer);
          overlay._focusTimer = 0;
        }
      }
      const result = originalClose.apply(this, args);
      if (overlay instanceof HTMLElement) closeScope(overlay);
      return result;
    };
  }

  const applicationRoot = document.getElementById('main-app');
  if (applicationRoot instanceof HTMLElement) applicationRoot.tabIndex = -1;
  for (const control of document.querySelectorAll(
    '.titlebar-controls .titlebar-ctrl',
  )) {
    control.tabIndex = -1;
  }

  document.addEventListener('keydown', onKeyDown, true);
  document.addEventListener('pointerdown', onPointerDown, true);
  document.addEventListener('focusin', refresh, true);
  document.addEventListener('focusout', (event) => {
    if (event.target instanceof HTMLElement) {
      event.target.removeAttribute(MARKER);
    }
  }, true);
  window.addEventListener('blur', reset);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) reset();
  });

  wrapDemoModal();

  const api = Object.freeze({
    reset,
    clear,
    focusApplicationRoot,
    capture,
    restore,
    preserve,
    openScope,
    closeScope,
    stashNative,
    restoreNative,
    refresh,
  });
  Object.defineProperty(window, 'pdmFocusVisibility', {
    configurable: false,
    enumerable: false,
    value: api,
    writable: false,
  });
  root.dataset.pdmFocusControllerReady = 'true';
  refresh();
})();
