(() => {
  'use strict';

  /*
   * Best-effort renderer cleanup for values already authorized by native code.
   *
   * This registry stores element references and opaque lease identifiers, never
   * a second copy of a secret. Native page/session revocation is the security
   * boundary; these routines only shorten the lifetime of reachable DOM/JS
   * state and are deliberately safe to call repeatedly.
   */
  const LEASE_ID = /^[A-Za-z0-9_-]{16,64}$/;
  const MAX_ACTIVE_LEASES = 64;
  const MAX_ACTIVE_TRANSIENTS = 64;
  const MAX_TRANSIENT_ID = 2147483647;
  const MAX_LEASE_MS_BY_KIND = Object.freeze({
    CONFLICT_REVEAL: 30000,
    EDITOR: 300000,
    GENERATED: 300000,
    REVEAL: 30000,
  });
  const CLEAR_REASONS = new Set([
    'auto_lock',
    'bridge_close',
    'bridge_destroyed',
    'change_key_failed',
    'change_key_restored',
    'change_key_success',
    'duplicate_lease_id',
    'exit',
    'expired',
    'lease_consumed',
    'lease_expired',
    'lease_released',
    'manual_hide',
    'manual_lock',
    'modal_cancel',
    'modal_close',
    'navigation',
    'parent_released',
    'page_invalidated',
    'page_unload',
    'renderer_failure',
    'save_complete',
    'session_invalidated',
    'suspend_lock',
    'switch_database',
  ]);
  const leases = new Map();
  const transients = new Map();
  let nextTransientId = 1;
  let clearCount = 0;
  let lastReason = '';

  function isElement(value) {
    return value instanceof Element;
  }

  function normalizeElements(value) {
    const candidates = Array.isArray(value) ? value : [value];
    if (!candidates.length || candidates.length > 16) {
      throw new TypeError('secret lease requires 1-16 DOM elements');
    }
    const unique = [];
    const seen = new Set();
    for (const candidate of candidates) {
      if (!isElement(candidate) || seen.has(candidate)) {
        throw new TypeError('secret lease elements must be unique DOM nodes');
      }
      if (candidate.dataset.pdmSecretBound === 'true') {
        throw new TypeError('secret element is already bound');
      }
      seen.add(candidate);
      unique.push(candidate);
    }
    return unique;
  }

  function clearElement(element) {
    if (element instanceof HTMLInputElement) {
      element.value = '';
      element.defaultValue = '';
      if (element.dataset.pdmSecretKind !== 'TOTP') {
        try {
          element.type = 'password';
        } catch (_error) {
          // Native revocation remains authoritative if a custom input refuses.
        }
      }
      try {
        element.setSelectionRange(0, 0);
      } catch (_error) {
        // Non-text inputs do not support a selection range.
      }
    } else if (element instanceof HTMLTextAreaElement) {
      element.value = '';
      element.defaultValue = '';
      try {
        element.setSelectionRange(0, 0);
      } catch (_error) {
        // A detached/custom textarea can reject selection operations.
      }
    } else {
      element.textContent = '';
    }
    element.removeAttribute('data-pdm-secret-bound');
    element.removeAttribute('data-pdm-secret-kind');
  }

  function clearLease(leaseId, reason = 'manual_hide') {
    if (
      typeof leaseId !== 'string' ||
      !LEASE_ID.test(leaseId) ||
      !CLEAR_REASONS.has(reason)
    ) {
      return false;
    }
    const lease = leases.get(leaseId);
    if (!lease) return true;
    window.clearTimeout(lease.timerId);
    for (const element of lease.elements) clearElement(element);
    lease.elements.length = 0;
    leases.delete(leaseId);
    clearCount = Math.min(Number.MAX_SAFE_INTEGER, clearCount + 1);
    lastReason = reason;
    return true;
  }

  function bindLease(
    leaseId,
    kind,
    expiresInMs,
    elements,
    autoClear = true,
  ) {
    const maximumMs = MAX_LEASE_MS_BY_KIND[kind];
    if (
      typeof leaseId !== 'string' ||
      !LEASE_ID.test(leaseId) ||
      typeof kind !== 'string' ||
      !Number.isInteger(maximumMs) ||
      !Number.isInteger(expiresInMs) ||
      expiresInMs < 1 ||
      expiresInMs > maximumMs ||
      typeof autoClear !== 'boolean' ||
      (!autoClear && kind !== 'REVEAL')
    ) {
      throw new TypeError('invalid secret lease metadata');
    }
    const replacing = leases.has(leaseId);
    if (!replacing && leases.size >= MAX_ACTIVE_LEASES) {
      throw new TypeError('secret lease registry is full');
    }
    if (replacing) clearLease(leaseId, 'duplicate_lease_id');
    const bound = normalizeElements(elements);
    for (const element of bound) {
      element.dataset.pdmSecretBound = 'true';
      element.dataset.pdmSecretKind = kind;
    }
    const timerId = autoClear
      ? window.setTimeout(
        () => clearLease(leaseId, 'lease_expired'),
        expiresInMs,
      )
      : 0;
    leases.set(leaseId, {elements: bound, timerId});
    return true;
  }

  function clearTransient(transientId, reason = 'manual_hide') {
    if (
      !Number.isInteger(transientId) ||
      transientId < 1 ||
      !CLEAR_REASONS.has(reason)
    ) {
      return false;
    }
    const transient = transients.get(transientId);
    if (!transient) return true;
    window.clearTimeout(transient.timerId);
    for (const element of transient.elements) clearElement(element);
    transient.elements.length = 0;
    transients.delete(transientId);
    clearCount = Math.min(Number.MAX_SAFE_INTEGER, clearCount + 1);
    lastReason = reason;
    return true;
  }

  function bindTransient(kind, expiresInMs, elements) {
    if (
      kind !== 'TOTP' ||
      !Number.isInteger(expiresInMs) ||
      expiresInMs < 1 ||
      expiresInMs > 30000
    ) {
      throw new TypeError('invalid transient secret metadata');
    }
    if (transients.size >= MAX_ACTIVE_TRANSIENTS) {
      throw new TypeError('transient secret registry is full');
    }
    const bound = normalizeElements(elements);
    let transientId = 0;
    for (let offset = 0; offset < MAX_ACTIVE_TRANSIENTS + 1; offset += 1) {
      const candidate = nextTransientId;
      nextTransientId =
        nextTransientId >= MAX_TRANSIENT_ID ? 1 : nextTransientId + 1;
      if (!transients.has(candidate)) {
        transientId = candidate;
        break;
      }
    }
    if (!transientId) {
      throw new TypeError('transient secret identifier unavailable');
    }
    for (const element of bound) {
      element.dataset.pdmSecretBound = 'true';
      element.dataset.pdmSecretKind = kind;
    }
    const timerId = window.setTimeout(
      () => clearTransient(transientId, 'lease_expired'),
      expiresInMs,
    );
    transients.set(transientId, {elements: bound, timerId});
    return transientId;
  }

  function clearAll(reason) {
    if (!CLEAR_REASONS.has(reason)) return false;
    for (const leaseId of Array.from(leases.keys())) {
      clearLease(leaseId, reason);
    }
    for (const transientId of Array.from(transients.keys())) {
      clearTransient(transientId, reason);
    }
    const unleasedSensitive = document.querySelectorAll(
      'input[type="password"], [data-pdm-secret-bound], [data-pdm-sensitive]',
    );
    for (const element of unleasedSensitive) clearElement(element);
    lastReason = reason;
    return true;
  }

  function snapshot() {
    let boundNodeCount = 0;
    for (const lease of leases.values()) {
      boundNodeCount += lease.elements.length;
    }
    for (const transient of transients.values()) {
      boundNodeCount += transient.elements.length;
    }
    return Object.freeze({
      activeLeaseCount: leases.size,
      activeTransientCount: transients.size,
      boundNodeCount,
      clearCount,
      lastReason,
    });
  }

  window.addEventListener(
    'pagehide',
    () => clearAll('page_unload'),
    {capture: true},
  );
  const api = Object.freeze({
    bindLease,
    bindTransient,
    clearAll,
    clearLease,
    clearTransient,
    snapshot,
  });
  Object.defineProperty(window, 'pdmSensitiveDom', {
    configurable: false,
    enumerable: false,
    value: api,
    writable: false,
  });
})();
