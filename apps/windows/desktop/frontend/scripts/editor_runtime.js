(() => {
  'use strict';

  const FIELD_LIMITS = Object.freeze({
    PLATFORM: [128, 512], ACCOUNT: [512, 2048], PASSWORD: [1024, 4096], NOTES: [8192, 32768],
  });
  const FIELDS = Object.freeze({
    PLATFORM: 'editor-platform', ACCOUNT: 'editor-account', PASSWORD: 'editor-password', NOTES: 'editor-notes',
  });
  const PASSWORD_ICONS = Object.freeze({
    eye: 'M247.31,124.76c-.35-.79-8.82-19.58-27.65-38.41C194.57,61.26,162.88,48,128,48S61.43,61.26,36.34,86.35C17.51,105.18,9,124,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208s66.57-13.26,91.66-38.34c18.83-18.83,27.3-37.61,27.65-38.4A8,8,0,0,0,247.31,124.76ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z',
    concealed: 'M230.94,164A8,8,0,1,1,217.05,172l-19-33.2A123.23,123.23,0,0,1,162,155.46l5.87,35.22a8,8,0,0,1-6.58,9.21A8.4,8.4,0,0,1,160,200a8,8,0,0,1-7.88-6.69l-5.77-34.58a133.06,133.06,0,0,1-36.68,0l-5.77,34.58A8,8,0,0,1,96,200a8.4,8.4,0,0,1-1.32-.11,8,8,0,0,1-6.58-9.21L94,155.46a123.23,123.23,0,0,1-36.06-16.69L39,172A8,8,0,1,1,25.06,164l20-35a152.8,152.8,0,0,1-19.3-20,8,8,0,0,1,0-10.06C44.56,75.72,77.55,48,128,48s83.44,27.72,102.22,51a8,8,0,0,1,0,10.06,152.8,152.8,0,0,1-19.3,20Z',
  });
  const COPY = Object.freeze({
    zh: {loading: '正在加载…', reading: '正在读取完整字段…', saving: '正在保存…', generating: '正在生成…', reloading: '正在载入最新记录…', reauthorizing: '正在重新取得保存权限…', open_failed: '无法打开此密码记录。', init_failed: '安全初始化失败。', init_request_failed: '初始化请求失败。', connection_unavailable: '安全连接不可用。', read_failed: '无法读取完整字段；当前草稿已保留，请关闭后重试。', generated_failed: '无法生成密码。', conflict: '记录已在别处更改。', reload_cancelled: '已保留当前草稿。', reload_failed: '无法载入最新记录；当前草稿已保留。', record_missing: '该记录已不存在；当前草稿已保留，请关闭此窗口。', platform_conflict: '平台名称已存在。', invalid_input: '请检查输入后重试。', save_failed: '保存失败，输入已保留。', save_request_failed: '保存请求失败，输入已保留。', reauthorize_failed: '无法重新取得保存权限，请关闭后重试。', platform_required: '平台不能为空。', field_limit: '修改后的字段超出允许长度。', totp_invalid: '动态验证码密钥格式无效。', operation_failed: '操作未完成。', totp_clear: '保存后将移除现有密钥。', totp_keep: '现有密钥不会显示。留空将保留原值。', totp_none: '可选。留空则不保存动态验证码密钥。', retry: '请在 {seconds} 秒后重试'},
    en: {loading: 'Loading…', reading: 'Reading complete fields…', saving: 'Saving…', generating: 'Generating…', reloading: 'Loading the latest record…', reauthorizing: 'Reauthorizing save…', open_failed: 'This password record could not be opened.', init_failed: 'Secure initialization failed.', init_request_failed: 'Initialization request failed.', connection_unavailable: 'Secure connection unavailable.', read_failed: 'The complete field could not be read. Your draft is preserved; close and try again.', generated_failed: 'Password generation failed.', conflict: 'The record changed elsewhere.', reload_cancelled: 'Your current draft is preserved.', reload_failed: 'The latest record could not be loaded. Your current draft is preserved.', record_missing: 'This record no longer exists. Your draft is preserved; close this window.', platform_conflict: 'That platform name already exists.', invalid_input: 'Check the input and try again.', save_failed: 'Save failed. Your input is preserved.', save_request_failed: 'The save request failed. Your input is preserved.', reauthorize_failed: 'Saving could not be reauthorized. Close and try again.', platform_required: 'Platform is required.', field_limit: 'The changed field exceeds the allowed length.', totp_invalid: 'The one-time password secret is invalid.', operation_failed: 'The operation did not complete.', totp_clear: 'The existing secret will be removed when saved.', totp_keep: 'The existing secret is never shown. Leave this empty to keep it.', totp_none: 'Optional. Leave empty to omit the one-time password secret.', retry: 'Try again in {seconds} seconds'},
  });
  const RECOVERY_COPY = Object.freeze({
    zh: {label: '恢复码（可选）', keep: '已保存 {total} 条。现有恢复码不会回填，留空保留原组。', none: '一行一个，可保存网站或应用提供的一组恢复码。', clear: '保存后将移除整组恢复码。', replace: '保存后将替换整组恢复码，并重置本地使用标记。', remove: '移除整组恢复码', undo: '保留原组', backup: '请另留一份独立安全副本；本库打不开时，这里的恢复码也无法取用。', invalid: '第 {line} 行恢复码格式无效。', duplicate: '第 {line} 行与前面的恢复码重复。', limit: '恢复码超出数量或长度上限。', failure: '恢复码输入无效，请检查格式、重复行和长度。', confirming: '等待确认恢复码变更…'},
    en: {label: 'Recovery codes (optional)', keep: '{total} codes stored. Existing values are not prefilled; leave empty to keep them.', none: 'One code per line. Paste codes supplied by a website or app.', clear: 'Saving will remove all stored recovery codes.', replace: 'Saving will replace the entire set and reset local usage marks.', remove: 'Remove all recovery codes', undo: 'Keep existing codes', backup: 'Keep a separate secure copy. These codes are unavailable if this vault cannot be opened.', invalid: 'Invalid recovery code on line {line}.', duplicate: 'The code on line {line} duplicates an earlier code.', limit: 'Recovery codes exceed the count or length limit.', failure: 'Check recovery code format, duplicate lines, and length.', confirming: 'Waiting for confirmation…'},
  });
  const state = {
    bridge: null, instanceId: '', ready: false, busy: false, dirty: false, dirtySent: null,
    original: null, mode: 'EDIT', editLeaseId: '', generatedLeaseId: '', editDomLeaseActive: false, generatedDomLeaseActive: false, editDomExpiresAt: 0, generatedDomExpiresAt: 0, reads: new Map(), pending: new Map(), totpAction: 'KEEP', hasTotp: false, recoveryAction: 'KEEP', recoveryCount: 0, recoveryConfirmed: false,
    generator: {length: 24, useLower: true, useUpper: true, useDigits: true, useSymbols: true, avoidAmbiguous: false}, reload: null, initialized: false, presented: false, generateAfterOpenRequested: false, generateAfterOpenConsumed: false, language: 'zh', errorKey: '', errorArgs: {}, statusKey: '', statusArgs: {}, totpHintKey: 'totp_keep',
  };
  const $ = (id) => document.getElementById(id);
  const text = (id, value) => { const node = $(id); if (node) node.textContent = value; };
  const passwordIcon = (revealed) => `<svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="${PASSWORD_ICONS[revealed ? 'concealed' : 'eye']}"/></svg>`;
  const actionId = () => window.crypto?.randomUUID?.() || `editor-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const count = (value) => Array.from(value).length;
  const fits = (field, value) => typeof value === 'string' && !value.includes('\0') && count(value) <= FIELD_LIMITS[field][0] && new TextEncoder().encode(value).length <= FIELD_LIMITS[field][1];
  const validTotp = (value) => {
    if (!value || !/^[A-Za-z2-7= \-]+$/.test(value)) return false;
    const compact = value.replace(/[\s-]/g, '').toUpperCase();
    return Boolean(compact.replace(/=+$/, '')) && !compact.replace(/=+$/, '').includes('=');
  };
  function values() {
    return { PLATFORM: $('editor-platform').value, ACCOUNT: $('editor-account').value, PASSWORD: $('editor-password').value, NOTES: $('editor-notes').value, favorite: $('editor-favorite').classList.contains('active') };
  }
  function message(key, args = {}) {
    return String((key.startsWith('recovery_') ? RECOVERY_COPY[state.language][key.slice(9)] : COPY[state.language][key]) || '').replace(/\{(\w+)\}/g, (_match, name) => String(args[name] ?? ''));
  }
  function setStatus(key = '', args = {}) {
    state.statusKey = key; state.statusArgs = args; text('editor-state', key ? message(key, args) : '');
  }
  function setBusy(busy, key = '', args = {}) {
    state.busy = busy;
    $('editor-app').dataset.busy = String(busy);
    for (const id of Object.values(FIELDS).concat(['editor-favorite', 'editor-totp', 'editor-save', 'editor-cancel', 'editor-generate', 'editor-toggle-password', 'editor-totp-remove', 'editor-recovery', 'editor-recovery-remove'])) $(id).disabled = busy;
    if (key || !busy) setStatus(key, args);
  }
  function error(key = '', args = {}) { state.errorKey = key; state.errorArgs = args; text('editor-error', key ? message(key, args) : ''); $('editor-feedback')?.classList.toggle('has-error', Boolean(key)); }
  function clearLease(leaseId, reason = 'manual_hide') {
    if (!leaseId) return;
    window.pdmSensitiveDom?.clearLease(leaseId, reason);
    const id = actionId();
    state.bridge?.releaseSecretLeaseV1(id, leaseId, () => {});
  }
  function releaseNativeLease(leaseId) {
    if (leaseId) state.bridge?.releaseSecretLeaseV1(actionId(), leaseId, () => {});
  }
  function passwordSnapshot() {
    const password = $('editor-password');
    return {value: password.value, type: password.type, start: password.selectionStart, end: password.selectionEnd, direction: password.selectionDirection};
  }
  function restorePassword(snapshot) {
    const password = $('editor-password');
    password.type = snapshot.type; password.value = snapshot.value;
    if (snapshot.start !== null && snapshot.end !== null) { try { password.setSelectionRange(snapshot.start, snapshot.end, snapshot.direction); } catch (_error) {} }
  }
  function bindLeaseTo(leaseId, kind, expiresInMs, elements) {
    try { window.pdmSensitiveDom?.bindLease(leaseId, kind, expiresInMs, elements); return Boolean(window.pdmSensitiveDom); }
    catch (_error) { return false; }
  }
  function detachPasswordLease(leaseId) {
    const snapshot = passwordSnapshot();
    window.pdmSensitiveDom?.clearLease(leaseId, 'lease_consumed');
    restorePassword(snapshot);
    return snapshot;
  }
  function scrub() {
    for (const id of Object.values(FIELDS)) $(id).value = '';
    $('editor-totp').value = ''; $('editor-recovery').value = '';
    state.reads.forEach((read) => { read.chunks.fill(''); if (read.readId) state.bridge?.releaseFieldReadV1(actionId(), read.readId, () => {}); });
    state.reads.clear();
    clearLease(state.reload?.leaseId, 'manual_hide'); clearReloadValues(state.reload); state.reload = null;
    clearLease(state.generatedLeaseId, 'manual_hide');
    clearLease(state.editLeaseId, 'manual_hide');
    state.pending.clear(); state.generatedLeaseId = ''; state.editLeaseId = ''; state.editDomLeaseActive = false; state.generatedDomLeaseActive = false; state.editDomExpiresAt = 0; state.generatedDomExpiresAt = 0; state.original = null; state.mode = 'EDIT'; state.totpAction = 'KEEP'; state.hasTotp = false; state.recoveryAction = 'KEEP'; state.recoveryCount = 0; state.recoveryConfirmed = false; state.totpHintKey = 'totp_keep'; state.ready = false; state.initialized = false; state.presented = false; state.generateAfterOpenRequested = false; state.generateAfterOpenConsumed = false;
  }
  function call(method, args, onRejected) {
    const id = actionId(); state.pending.set(id, method);
    state.bridge[method](id, ...args, (ack) => {
      if (state.pending.get(id) === method && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
        state.pending.delete(id); onRejected?.(ack?.errorCode || 'INTERNAL_FAILURE');
      }
    });
    return id;
  }
  function captureOriginal() {
    state.original = values();
    state.original.totpAction = 'KEEP';
    state.totpAction = 'KEEP'; state.recoveryAction = 'KEEP'; state.recoveryConfirmed = false;
    updateRecoveryHint(); updateDirty();
  }
  function present() {
    if (state.presented || !state.bridge) return;
    state.presented = true;
    state.bridge.presentReadyV1();
  }
  function updateDirty() {
    if (!state.original) return;
    const current = values();
    const dirty = Object.keys(FIELDS).some((field) => current[field] !== state.original[field]) || current.favorite !== state.original.favorite || state.totpAction !== 'KEEP' || state.recoveryAction !== 'KEEP';
    state.dirty = dirty;
    if (state.dirtySent === dirty || !state.bridge) return;
    state.dirtySent = dirty;
    state.bridge.setDirtyV1(dirty);
  }
  function bindLease(leaseId, kind, expiresInMs) {
    return Boolean(leaseId) && bindLeaseTo(leaseId, kind, expiresInMs, [$('editor-password')]);
  }
  function setFavorite(value) {
    const favorite = $('editor-favorite');
    const active = value === true;
    favorite.classList.toggle('active', active);
    favorite.setAttribute('aria-pressed', String(active));
  }
  function normalizeInitial(result) {
    if (!result || typeof result !== 'object' || !['CREATE', 'EDIT'].includes(result.mode) || !Array.isArray(result.longFields) || typeof result.favorite !== 'boolean' || typeof result.hasTotp !== 'boolean' || !Number.isInteger(result.recoveryCount) || result.recoveryCount < 0 || result.recoveryCount > 128) return null;
    for (const field of Object.keys(FIELDS)) if (typeof result[field.toLowerCase()] !== 'string') return null;
    if (result.mode === 'EDIT') {
      return Number.isSafeInteger(result.recordId) && result.recordId >= 1 && typeof result.revision === 'string' && Boolean(result.revision) && typeof result.editLeaseId === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(result.editLeaseId) && Number.isSafeInteger(result.expiresInMs) && result.expiresInMs >= 1 && result.expiresInMs <= 300000 ? result : null;
    }
    const hasGenerated = typeof result.generatedLeaseId === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(result.generatedLeaseId);
    return result.recordId === 0 && result.revision === '' && result.editLeaseId === '' && typeof result.generatedLeaseId === 'string' && result.longFields.length === 0 && Number.isSafeInteger(result.expiresInMs) && ((hasGenerated && result.expiresInMs >= 1 && result.expiresInMs <= 300000) || (result.generatedLeaseId === '' && result.expiresInMs === 0 && result.password === '')) ? result : null;
  }
  function startReads(fields, reload = null) {
    for (const field of fields) state.reads.set(field, {field, readId: '', offset: 0, chunks: [], reload});
    requestChunk(state.reads.values().next().value);
  }
  function requestChunk(read) {
    const request = actionId(); read.request = request; state.pending.set(request, 'readFieldChunkV1');
    state.bridge.readFieldChunkV1(request, read.field, read.readId, read.offset, (ack) => {
      if (state.pending.get(request) === 'readFieldChunkV1' && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
        state.pending.delete(request); finishRead(read, false, ack?.errorCode || 'INTERNAL_FAILURE');
      }
    });
  }
  function finishRead(read, success, code = '') {
    if (state.reads.get(read.field) !== read) return;
    state.reads.delete(read.field);
    if (read.readId) state.bridge?.releaseFieldReadV1(actionId(), read.readId, () => {});
    if (!success) {
      read.chunks.fill('');
      if (read.reload) { abortReload(read.reload, 'read_failed'); return; }
      state.reads.clear();
      $(FIELDS[read.field]).value = ''; state.ready = false; setBusy(false); error(code === 'OK' ? '' : 'read_failed'); present(); return;
    }
    const value = read.chunks.join(''); read.chunks.fill('');
    if (read.reload) read.reload.values[read.field] = value;
    else $(FIELDS[read.field]).value = value;
    if (state.reads.size) requestChunk(state.reads.values().next().value);
    else {
      if (read.reload) commitReload(read.reload);
      else { captureOriginal(); setBusy(false); present(); flushGenerateAfterOpen(); }
    }
  }
  function onInitialize(action, instanceId, code, _argument, _retry, result) {
    const matches = !state.instanceId || instanceId === state.instanceId;
    if (state.pending.get(action) !== 'initializeV1' || !matches || typeof instanceId !== 'string' || !instanceId) { if (result) { result.password = ''; if (result.editLeaseId) clearLease(result.editLeaseId); } return; }
    state.instanceId = instanceId;
    state.pending.delete(action);
    if (code !== 'OK') { setBusy(false); error('open_failed'); present(); return; }
    const initial = normalizeInitial(result);
    const leaseId = initial?.mode === 'CREATE' ? initial.generatedLeaseId : initial?.editLeaseId;
    const leaseKind = initial?.mode === 'CREATE' ? 'GENERATED' : 'EDITOR';
    if (!initial || (leaseId && !bindLease(leaseId, leaseKind, initial.expiresInMs))) { if (result) { result.password = ''; if (result.editLeaseId) clearLease(result.editLeaseId); if (result.generatedLeaseId) clearLease(result.generatedLeaseId); } setBusy(false); error('init_failed'); present(); return; }
    state.mode = initial.mode;
    if (initial.mode === 'CREATE') {
      state.generatedLeaseId = initial.generatedLeaseId || '';
      state.generatedDomLeaseActive = Boolean(initial.generatedLeaseId);
      state.generatedDomExpiresAt = initial.generatedLeaseId ? Date.now() + initial.expiresInMs : 0;
      state.totpHintKey = 'totp_none';
    } else {
      state.editLeaseId = initial.editLeaseId; state.editDomLeaseActive = true; state.editDomExpiresAt = Date.now() + initial.expiresInMs;
      state.totpHintKey = 'totp_keep';
    }
    state.hasTotp = initial.hasTotp === true; state.recoveryCount = initial.recoveryCount; state.initialized = true;
    for (const field of Object.keys(FIELDS)) $(FIELDS[field]).value = initial[field.toLowerCase()];
    setFavorite(initial.favorite);
    $('editor-totp-remove').hidden = initial.mode === 'CREATE' || !state.hasTotp;
    applyProjection({theme: document.documentElement.dataset.pdmEditorTheme, language: state.language, fontScale: document.documentElement.dataset.pdmEditorFont, generator: state.generator});
    if (!initial.longFields.length) { captureOriginal(); setBusy(false); present(); flushGenerateAfterOpen(); }
    else { setStatus('reading'); startReads(initial.longFields); }
  }
  function onChunk(action, instanceId, code, _argument, _retry, result) {
    const read = [...state.reads.values()].find((candidate) => candidate.request === action);
    const valid = read && instanceId === state.instanceId && code === 'OK' && result && typeof result.text === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(result.readId) && Number.isSafeInteger(result.nextOffset) && result.nextOffset === read.offset + count(result.text) && typeof result.done === 'boolean';
    if (!valid) { state.pending.delete(action); if (result) { result.text = ''; if (typeof result.readId === 'string') state.bridge?.releaseFieldReadV1(actionId(), result.readId, () => {}); } if (read) finishRead(read, false, code || 'INTERNAL_FAILURE'); return; }
    state.pending.delete(action); read.readId = result.readId; read.chunks.push(result.text); result.text = ''; read.offset = result.nextOffset;
    if (result.done) finishRead(read, true); else requestChunk(read);
  }
  function onGenerated(action, instanceId, code, _argument, _retry, result) {
    if (state.pending.get(action) !== 'generatePasswordV1' || instanceId !== state.instanceId) { if (result?.secretLeaseId) clearLease(result.secretLeaseId); return; }
    state.pending.delete(action); setBusy(false);
    const valid = code === 'OK' && result && typeof result.password === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(result.secretLeaseId) && Number.isSafeInteger(result.expiresInMs) && result.expiresInMs >= 1 && result.expiresInMs <= 300000;
    if (!valid) { if (result) { result.password = ''; releaseNativeLease(result.secretLeaseId); } error('generated_failed'); return; }
    const password = result.password; result.password = '';
    const probe = document.createElement('input');
    if (!bindLeaseTo(result.secretLeaseId, 'GENERATED', result.expiresInMs, [probe])) { releaseNativeLease(result.secretLeaseId); error('generated_failed'); return; }
    const old = passwordSnapshot();
    const oldLease = state.generatedDomLeaseActive
      ? {id: state.generatedLeaseId, kind: 'GENERATED', expiresAt: state.generatedDomExpiresAt, generated: true}
      : state.editDomLeaseActive
        ? {id: state.editLeaseId, kind: 'EDITOR', expiresAt: state.editDomExpiresAt, generated: false}
        : null;
    if (oldLease) {
      detachPasswordLease(oldLease.id);
      state.editDomLeaseActive = false;
      state.generatedDomLeaseActive = false;
    }
    if (!bindLease(result.secretLeaseId, 'GENERATED', result.expiresInMs)) {
      window.pdmSensitiveDom?.clearLease(result.secretLeaseId, 'lease_released'); releaseNativeLease(result.secretLeaseId); restorePassword(old);
      const remaining = oldLease ? Math.floor(oldLease.expiresAt - Date.now()) : 0;
      if (oldLease && remaining > 0 && bindLease(oldLease.id, oldLease.kind, remaining)) {
        state.editDomLeaseActive = !oldLease.generated; state.generatedDomLeaseActive = oldLease.generated;
      } else {
        $('editor-password').value = ''; old.value = '';
        state.editDomLeaseActive = false; state.generatedDomLeaseActive = false;
        state.bridge?.securityFailureV1();
      }
      error('generated_failed'); return;
    }
    if (state.generatedLeaseId) releaseNativeLease(state.generatedLeaseId);
    state.editDomLeaseActive = false; state.generatedDomLeaseActive = true; state.generatedLeaseId = result.secretLeaseId; state.generatedDomExpiresAt = Date.now() + result.expiresInMs;
    $('editor-password').value = password; updateDirty();
  }
  function clearReloadValues(reload) {
    if (!reload?.values) return;
    for (const field of Object.keys(FIELDS)) reload.values[field] = '';
  }
  function abortReload(reload, errorKey = 'reload_failed') {
    if (state.reload !== reload) return;
    for (const [field, read] of [...state.reads]) {
      if (read.reload !== reload) continue;
      state.reads.delete(field); read.chunks.fill('');
      if (read.readId) state.bridge?.releaseFieldReadV1(actionId(), read.readId, () => {});
    }
    clearLease(reload.leaseId, 'lease_released');
    clearReloadValues(reload); state.reload = null; state.ready = false;
    setBusy(false); error(errorKey);
  }
  function commitReload(reload) {
    if (state.reload !== reload) return;
    const old = passwordSnapshot();
    const oldLease = state.generatedDomLeaseActive
      ? {id: state.generatedLeaseId, kind: 'GENERATED', expiresAt: state.generatedDomExpiresAt, generated: true}
      : state.editDomLeaseActive
        ? {id: state.editLeaseId, kind: 'EDITOR', expiresAt: state.editDomExpiresAt, generated: false}
        : null;
    if (oldLease) detachPasswordLease(oldLease.id);
    state.editDomLeaseActive = false; state.generatedDomLeaseActive = false;
    const remaining = Math.floor(reload.expiresAt - Date.now());
    if (remaining <= 0 || !bindLease(reload.leaseId, 'EDITOR', remaining)) {
      restorePassword(old);
      const oldRemaining = oldLease ? Math.floor(oldLease.expiresAt - Date.now()) : 0;
      if (oldLease && oldRemaining > 0 && bindLease(oldLease.id, oldLease.kind, oldRemaining)) {
        state.editDomLeaseActive = !oldLease.generated; state.generatedDomLeaseActive = oldLease.generated;
      } else if (oldLease) {
        $('editor-password').value = ''; old.value = ''; state.bridge?.securityFailureV1();
      }
      abortReload(reload); return;
    }
    if (state.generatedLeaseId) releaseNativeLease(state.generatedLeaseId);
    if (state.editLeaseId && state.editLeaseId !== reload.leaseId) releaseNativeLease(state.editLeaseId);
    state.generatedLeaseId = ''; state.generatedDomExpiresAt = 0;
    state.editLeaseId = reload.leaseId; state.editDomLeaseActive = true; state.editDomExpiresAt = reload.expiresAt;
    for (const field of Object.keys(FIELDS)) $(FIELDS[field]).value = reload.values[field];
    setFavorite(reload.favorite); state.hasTotp = reload.hasTotp; state.recoveryCount = reload.recoveryCount;
    $('editor-recovery').value = '';
    $('editor-totp').value = ''; $('editor-totp-remove').hidden = !state.hasTotp;
    clearReloadValues(reload); state.reload = null; state.ready = true;
    captureOriginal(); setBusy(false); error('');
  }
  function onReload(action, instanceId, code, _argument, _retry, result) {
    if (state.pending.get(action) !== 'reloadLatestV1' || instanceId !== state.instanceId) {
      if (result) { result.password = ''; if (result.editLeaseId) clearLease(result.editLeaseId); }
      return;
    }
    state.pending.delete(action);
    if (code !== 'OK') {
      setBusy(false); state.ready = code !== 'NOT_FOUND';
      error(code === 'CANCELLED' ? 'reload_cancelled' : code === 'NOT_FOUND' ? 'record_missing' : 'reload_failed');
      return;
    }
    const initial = normalizeInitial(result);
    if (!initial) { if (result) result.password = ''; setBusy(false); state.ready = false; error('reload_failed'); return; }
    const probe = document.createElement('input');
    if (!bindLeaseTo(initial.editLeaseId, 'EDITOR', initial.expiresInMs, [probe])) {
      result.password = ''; releaseNativeLease(initial.editLeaseId); setBusy(false); state.ready = false; error('reload_failed'); return;
    }
    const reload = {
      leaseId: initial.editLeaseId,
      expiresAt: Date.now() + initial.expiresInMs,
      values: {},
      favorite: initial.favorite === true,
      hasTotp: initial.hasTotp === true,
      recoveryCount: initial.recoveryCount,
    };
    for (const field of Object.keys(FIELDS)) reload.values[field] = initial[field.toLowerCase()];
    result.password = ''; state.reload = reload;
    if (!initial.longFields.length) commitReload(reload);
    else { setStatus('reading'); startReads(initial.longFields, reload); }
  }
  function reloadLatest() {
    state.ready = false; setBusy(true, 'reloading');
    call('reloadLatestV1', [], () => { state.ready = true; setBusy(false); error('reload_failed'); });
  }
  function onSaved(action, instanceId, code, argument, retry, result) {
    if (state.pending.get(action) !== 'savePasswordV1' || instanceId !== state.instanceId) return;
    state.pending.delete(action); setBusy(false);
    if (code === 'OK') { scrub(); return; }
    if (code === 'REVISION_CONFLICT') { error('conflict'); reloadLatest(); }
    else if (code === 'PLATFORM_CONFLICT') error('platform_conflict');
    else if (code.startsWith('RECOVERY_CODES_')) { error('recovery_failure'); $('editor-recovery').focus(); }
    else if (code === 'INVALID_ARGUMENT' && argument >= 1) error('invalid_input');
    else error('save_failed');
    if (retry > 0) setStatus('retry', {seconds: Math.ceil(retry / 1000)});
    if (!['REVISION_CONFLICT', 'NOT_FOUND', 'SESSION_REQUIRED', 'STALE_SESSION', 'STALE_PAGE'].includes(code)) reauthorize();
    void result;
  }
  function onCreated(action, instanceId, code, argument, retry, result) {
    if (state.pending.get(action) !== 'createPasswordV1' || instanceId !== state.instanceId) return;
    state.pending.delete(action); setBusy(false);
    if (code === 'OK') { scrub(); return; }
    if (code === 'PLATFORM_CONFLICT') error('platform_conflict');
    else if (code.startsWith('RECOVERY_CODES_')) { error('recovery_failure'); $('editor-recovery').focus(); }
    else if (code === 'INVALID_ARGUMENT' && argument >= 1) error('invalid_input');
    else error('save_failed');
    if (retry > 0) setStatus('retry', {seconds: Math.ceil(retry / 1000)});
    void result;
  }
  function reauthorize() {
    if (
      !state.bridge ||
      [...state.pending.values()].includes('reauthorizeV1')
    ) return;
    setBusy(true, 'reauthorizing');
    call('reauthorizeV1', [], () => { setBusy(false); error('reauthorize_failed'); });
  }
  function onReauthorized(action, instanceId, code, _argument, _retry, result) {
    if (state.pending.get(action) !== 'reauthorizeV1' || instanceId !== state.instanceId) {
      if (result) { result.password = ''; result.account = ''; result.notes = ''; }
      return;
    }
    state.pending.delete(action);
    if (result) { result.password = ''; result.account = ''; result.notes = ''; }
    setBusy(false);
    if (code !== 'OK') error('reauthorize_failed');
  }
  function onGeneric(method) { return (action, instanceId, code) => { if (state.pending.get(action) === method && instanceId === state.instanceId) state.pending.delete(action); if (code !== 'OK') error('operation_failed'); }; }
  function updateRecoveryHint() {
    const key = state.recoveryAction === 'CLEAR' ? 'clear' : state.recoveryCount ? (state.recoveryAction === 'REPLACE' ? 'replace' : 'keep') : 'none';
    text('editor-recovery-hint', message('recovery_' + key, {total: state.recoveryCount}));
    $('editor-recovery-remove').hidden = state.mode === 'CREATE' || state.recoveryCount === 0;
    text('editor-recovery-remove', message(state.recoveryAction === 'CLEAR' ? 'recovery_undo' : 'recovery_remove'));
  }
  function checkRecoveryText(value) {
    const encoded = new TextEncoder();
    if (count(value) > 8192 || encoded.encode(value).length > 32768) return {key: 'recovery_limit'};
    const seen = new Set();
    let total = 0;
    const lines = value.replace(/\r\n/g, '\n').split('\n');
    for (let index = 0; index < lines.length; index++) {
      const code = lines[index].trim();
      if (!code) continue;
      if (/[\u0000-\u001f\u007f]/.test(code)) return {key: 'recovery_invalid', line: index + 1};
      if (count(code) > 1024 || encoded.encode(code).length > 4096 || ++total > 128) return {key: 'recovery_limit'};
      if (seen.has(code)) return {key: 'recovery_duplicate', line: index + 1};
      seen.add(code);
    }
    return null;
  }
  function onRecoveryConfirmed(action, instanceId, code, confirmed) {
    if (state.pending.get(action) !== 'confirmRecoveryChangeV1' || instanceId !== state.instanceId) return;
    state.pending.delete(action); setBusy(false);
    if (code === 'OK' && confirmed === true) { state.recoveryConfirmed = true; save(); }
    else if (code !== 'CANCELLED') error('operation_failed');
  }
  function toggleRecovery() {
    if (state.busy) return;
    state.recoveryAction = state.recoveryAction === 'CLEAR' ? 'KEEP' : 'CLEAR';
    state.recoveryConfirmed = false; $('editor-recovery').value = '';
    updateRecoveryHint(); updateDirty();
  }
  function save() {
    if (!state.ready || state.busy || !state.original || state.reads.size) return;
    const current = values();
    if (!current.PLATFORM.trim()) { error('platform_required'); $('editor-platform').focus(); return; }
    for (const field of Object.keys(FIELDS)) if ((state.mode === 'CREATE' || current[field] !== state.original[field]) && !fits(field, current[field])) { error('field_limit'); $(FIELDS[field]).focus(); return; }
    const recovery = state.recoveryAction === 'REPLACE' ? $('editor-recovery').value : '';
    const invalidRecovery = checkRecoveryText(recovery);
    if (invalidRecovery) { error(invalidRecovery.key, invalidRecovery); $('editor-recovery').focus(); return; }
    if (state.mode === 'EDIT' && state.recoveryCount && state.recoveryAction !== 'KEEP' && !state.recoveryConfirmed) {
      setBusy(true, 'recovery_confirming'); error('');
      call('confirmRecoveryChangeV1', [state.recoveryAction === 'CLEAR'], () => { setBusy(false); error('operation_failed'); });
      return;
    }
    let totp = $('editor-totp').value.trim();
    if (state.totpAction === 'REPLACE' && !validTotp(totp)) { error('totp_invalid'); $('editor-totp').focus(); return; }
    if (state.mode === 'CREATE') {
      const totpAction = totp ? 'REPLACE' : 'NONE';
      setBusy(true, 'saving'); error('');
      call('createPasswordV1', [current.PLATFORM, current.ACCOUNT, current.PASSWORD, current.NOTES, totpAction, totp, current.favorite, recovery], () => { setBusy(false); error('save_request_failed'); });
      totp = '';
      return;
    }
    if (state.totpAction !== 'REPLACE') totp = '';
    const args = [];
    for (const field of Object.keys(FIELDS)) { const changed = current[field] !== state.original[field]; args.push(changed ? 'REPLACE' : 'KEEP', changed ? current[field] : ''); }
    setBusy(true, 'saving'); error(''); call('savePasswordV1', [...args, state.totpAction, totp, current.favorite, state.recoveryAction, recovery], (code) => { setBusy(false); error('save_request_failed'); if (code === 'SECRET_LEASE_EXPIRED') reauthorize(); });
    totp = ''; args.fill('');
  }
  function generate() { if (!state.ready || state.busy) return; const p = state.generator; setBusy(true, 'generating'); call('generatePasswordV1', [p.length, p.useLower, p.useUpper, p.useDigits, p.useSymbols, p.avoidAmbiguous], () => { setBusy(false); error('generated_failed'); }); }
  function flushGenerateAfterOpen() {
    if (!state.generateAfterOpenRequested || state.generateAfterOpenConsumed || !state.initialized || state.busy || !state.original || state.reads.size) return;
    state.generateAfterOpenRequested = false; state.generateAfterOpenConsumed = true; generate();
  }
  function close() { if (!state.busy) state.bridge?.requestCloseV1(); }
  function toggleTotp() { state.totpAction = state.totpAction === 'CLEAR' ? 'KEEP' : 'CLEAR'; state.totpHintKey = state.totpAction === 'CLEAR' ? 'totp_clear' : 'totp_keep'; $('editor-totp').value = ''; text('editor-totp-hint', message(state.totpHintKey)); updateDirty(); }
  function applyProjection(projectionOrTheme = {}, languageValue = 'ZH', fontValue = '100', generatorOptions = {}) {
    const projection = typeof projectionOrTheme === 'object' ? projectionOrTheme : {theme: projectionOrTheme, language: languageValue, fontScale: fontValue, generator: generatorOptions};
    const theme = projection.theme === 'LIGHT' ? 'LIGHT' : 'DARK';
    const language = projection.language === 'EN' || projection.language === 'en' ? 'en' : 'zh';
    const font = ['90', '100', '110', '125'].includes(String(projection.fontScale)) ? String(projection.fontScale) : '100';
    const generator = projection.generator || projection.generatorOptions || {};
    if (Number.isSafeInteger(generator.length) && generator.length >= 1 && generator.length <= 1024 && ['useLower', 'useUpper', 'useDigits', 'useSymbols', 'avoidAmbiguous'].every((key) => typeof generator[key] === 'boolean')) state.generator = {...generator};
    state.language = language;
    document.documentElement.dataset.pdmEditorTheme = theme; document.documentElement.dataset.pdmEditorFont = font; document.documentElement.classList?.toggle('light', theme === 'LIGHT'); document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
    const labels = language === 'en'
      ? {create: 'Add password', edit: 'Edit password', platform: 'Platform', account: 'Account', password: 'Password', generate: 'Generate password', notes: 'Notes', totp: 'One-time password secret', favorite: 'Favorite', cancel: 'Cancel', save: 'Save', remove: 'Remove existing secret', reveal: 'Show password', conceal: 'Hide password'}
      : {create: '新增密码', edit: '编辑密码', platform: '平台', account: '账号', password: '密码', generate: '生成密码', notes: '备注', totp: '动态验证码密钥', favorite: '收藏', cancel: '取消', save: '保存', remove: '移除现有密钥', reveal: '显示密码', conceal: '隐藏密码'};
    for (const [id, value] of Object.entries({ 'editor-title': state.mode === 'CREATE' ? labels.create : labels.edit, 'label-platform': labels.platform, 'label-account': labels.account, 'label-password': labels.password, 'label-notes': labels.notes, 'label-totp': labels.totp, 'label-favorite': labels.favorite, 'editor-cancel': labels.cancel, 'editor-save': labels.save, 'editor-totp-remove': labels.remove })) text(id, value);
    text('label-recovery', message('recovery_label')); text('editor-recovery-backup', message('recovery_backup')); updateRecoveryHint();
    const revealed = $('editor-password').type === 'text';
    $('editor-toggle-password')?.setAttribute('aria-label', revealed ? labels.conceal : labels.reveal);
    $('editor-toggle-password')?.setAttribute('title', revealed ? labels.conceal : labels.reveal);
    $('editor-generate')?.setAttribute('aria-label', labels.generate);
    $('editor-generate')?.setAttribute('title', labels.generate);
    error(state.errorKey, state.errorArgs); setStatus(state.statusKey, state.statusArgs); text('editor-totp-hint', message(state.totpHintKey));
  }
  function attach(bridge) {
    state.bridge = bridge; state.instanceId = '';
    const signals = {initializeCompletedV1: onInitialize, reauthorizeCompletedV1: onReauthorized, reloadLatestCompletedV1: onReload, readFieldChunkCompletedV1: onChunk, releaseFieldReadCompletedV1: onGeneric('releaseFieldReadV1'), generatePasswordCompletedV1: onGenerated, releaseSecretLeaseCompletedV1: onGeneric('releaseSecretLeaseV1'), savePasswordCompletedV1: onSaved, createPasswordCompletedV1: onCreated, confirmRecoveryChangeCompletedV1: onRecoveryConfirmed};
    for (const [name, handler] of Object.entries(signals)) bridge[name]?.connect(handler);
    bridge.projectionChangedV1?.connect((instanceId, theme, language, fontScale, generatorOptions) => { if (instanceId === state.instanceId) applyProjection(theme, language, fontScale, generatorOptions); });
    bridge.generateAfterOpenV1?.connect((instanceId) => { if (instanceId === state.instanceId && state.initialized && !state.generateAfterOpenConsumed) { state.generateAfterOpenRequested = true; flushGenerateAfterOpen(); } });
    state.ready = true; setBusy(true, 'loading'); call('initializeV1', [], () => { setBusy(false); error('init_request_failed'); });
  }
  for (const id of Object.values(FIELDS)) $(id).addEventListener('input', updateDirty);
  $('editor-password').addEventListener('input', () => {
    if (state.editDomLeaseActive) { detachPasswordLease(state.editLeaseId); state.editDomLeaseActive = false; }
    if (state.generatedDomLeaseActive) { detachPasswordLease(state.generatedLeaseId); state.generatedDomLeaseActive = false; state.bridge?.releaseSecretLeaseV1(actionId(), state.generatedLeaseId, () => {}); state.generatedLeaseId = ''; }
    updateDirty();
  });
  $('editor-recovery').addEventListener('input', () => { state.recoveryAction = $('editor-recovery').value.trim() ? 'REPLACE' : 'KEEP'; state.recoveryConfirmed = false; updateRecoveryHint(); updateDirty(); });
  $('editor-recovery-remove').addEventListener('click', toggleRecovery);
  $('editor-totp').addEventListener('input', () => { state.totpAction = $('editor-totp').value.trim() ? 'REPLACE' : 'KEEP'; updateDirty(); });
  $('editor-favorite').addEventListener('click', () => { if (state.busy) return; setFavorite(!values().favorite); updateDirty(); });
  $('editor-form').addEventListener('submit', (event) => { event.preventDefault(); save(); });
  $('editor-generate').addEventListener('click', generate); $('editor-cancel').addEventListener('click', close);
  $('editor-totp-remove').addEventListener('click', toggleTotp);
  $('editor-toggle-password').addEventListener('click', () => { const input = $('editor-password'); input.type = input.type === 'password' ? 'text' : 'password'; $('editor-toggle-password').innerHTML = passwordIcon(input.type === 'text'); applyProjection({theme: document.documentElement.dataset.pdmEditorTheme, language: state.language, fontScale: document.documentElement.dataset.pdmEditorFont, generator: state.generator}); });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !event.isTrusted || event.defaultPrevented || event.isComposing || event.keyCode === 229 || state.busy) return;
    event.preventDefault(); close();
  }, true);
  window.addEventListener('pagehide', scrub, {capture: true});
  window.pdmEditorRuntime = Object.freeze({applyProjectionV1: applyProjection, attachV1: attach, saveV1: save, generateV1: generate, scrubV1: scrub, stateV1: () => ({...state, reads: state.reads.size, pending: state.pending.size})});
  if (typeof QWebChannel === 'function' && window.qt?.webChannelTransport) new QWebChannel(window.qt.webChannelTransport, (channel) => { const bridge = channel.objects.pdmEditorV1; if (bridge) attach(bridge); else error('connection_unavailable'); });
})();
