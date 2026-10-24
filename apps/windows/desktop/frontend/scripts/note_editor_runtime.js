(() => {
  'use strict';

  const LIMITS = Object.freeze({TITLE: [256, 1024], CONTENT: [65536, 262144]});
  const IDS = Object.freeze({TITLE: 'note-editor-title-input', CONTENT: 'note-editor-content'});
  const COPY = Object.freeze({
    zh: {loading: '正在加载…', reading: '正在读取完整内容…', saving: '正在保存…', reloading: '正在载入最新记事…', deleting: '正在删除…', open_failed: '无法打开此记事。', init_failed: '记事初始化失败。', request_failed: '安全连接不可用。', read_failed: '无法读取完整记事；当前草稿已保留，请关闭后重试。', title_required: '标题不能为空。', field_limit: '修改后的标题或正文超出允许长度。', save_failed: '保存失败，输入已保留。', conflict: '记事已在别处更改。', reload_cancelled: '已保留当前草稿。', reload_failed: '无法载入最新记事；当前草稿已保留。', missing: '该记事已不存在；当前草稿已保留，请关闭此窗口。', delete_failed: '删除失败，记事和草稿均已保留。', retry: '请在 {seconds} 秒后重试'},
    en: {loading: 'Loading…', reading: 'Reading complete note…', saving: 'Saving…', reloading: 'Loading the latest note…', deleting: 'Deleting…', open_failed: 'This note could not be opened.', init_failed: 'Note initialization failed.', request_failed: 'Secure connection unavailable.', read_failed: 'The complete note could not be read. Your draft is preserved; close and try again.', title_required: 'Title is required.', field_limit: 'The changed title or content exceeds the allowed length.', save_failed: 'Save failed. Your input is preserved.', conflict: 'The note changed elsewhere.', reload_cancelled: 'Your current draft is preserved.', reload_failed: 'The latest note could not be loaded. Your current draft is preserved.', missing: 'This note no longer exists. Your draft is preserved; close this window.', delete_failed: 'Delete failed. The note and your draft are preserved.', retry: 'Try again in {seconds} seconds'},
  });
  const state = {
    bridge: null, instanceId: '', mode: 'NOTE_EDIT', ready: false, busy: false,
    dirty: false, dirtySent: null, original: null, pending: new Map(), read: null,
    stage: null, presented: false, language: 'zh', errorKey: '', errorArgs: {},
    statusKey: '', statusArgs: {},
  };
  const $ = (id) => document.getElementById(id);
  const actionId = () => window.crypto?.randomUUID?.() || `note-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const count = (value) => Array.from(value).length;
  const fits = (field, value) => typeof value === 'string' && !value.includes('\0') && count(value) <= LIMITS[field][0] && new TextEncoder().encode(value).length <= LIMITS[field][1];
  const values = () => ({TITLE: $(IDS.TITLE).value, CONTENT: $(IDS.CONTENT).value, favorite: $('note-editor-favorite').classList.contains('active')});
  function message(key, args = {}) { return String(COPY[state.language][key] || '').replace(/\{(\w+)\}/g, (_match, name) => String(args[name] ?? '')); }
  function setStatus(key = '', args = {}) { state.statusKey = key; state.statusArgs = args; $('note-editor-state').textContent = key ? message(key, args) : ''; }
  function error(key = '', args = {}) { state.errorKey = key; state.errorArgs = args; $('note-editor-error').textContent = key ? message(key, args) : ''; $('note-editor-feedback').classList.toggle('has-error', Boolean(key)); }
  function setBusy(busy, key = '', args = {}) {
    state.busy = busy; $('note-editor-app').dataset.busy = String(busy);
    for (const id of [...Object.values(IDS), 'note-editor-favorite', 'note-editor-delete', 'note-editor-cancel', 'note-editor-save']) $(id).disabled = busy;
    if (key || !busy) setStatus(key, args);
  }
  function setFavorite(value) { const button = $('note-editor-favorite'); button.classList.toggle('active', value === true); button.setAttribute('aria-pressed', String(value === true)); }
  function present() { if (!state.presented && state.bridge) { state.presented = true; state.bridge.presentReadyV1(); } }
  function updateDirty() {
    if (!state.original) return;
    const current = values();
    const dirty = current.TITLE !== state.original.TITLE || current.CONTENT !== state.original.CONTENT || current.favorite !== state.original.favorite;
    state.dirty = dirty;
    if (state.dirtySent !== dirty && state.bridge) { state.dirtySent = dirty; state.bridge.setDirtyV1(dirty); }
  }
  function captureOriginal() { state.original = values(); updateDirty(); }
  function call(method, args, rejected) {
    const id = actionId(); state.pending.set(id, method);
    state.bridge[method](id, ...args, (ack) => {
      if (state.pending.get(id) === method && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
        state.pending.delete(id); rejected?.(ack?.errorCode || 'INTERNAL_FAILURE');
      }
    });
    return id;
  }
  function normalizeInitial(result) {
    if (!result || typeof result !== 'object' || !['NOTE_CREATE', 'NOTE_EDIT'].includes(result.mode) || typeof result.title !== 'string' || typeof result.content !== 'string' || typeof result.favorite !== 'boolean' || !Array.isArray(result.longFields) || result.longFields.length > 2 || new Set(result.longFields).size !== result.longFields.length || result.longFields.some((field) => !IDS[field])) return null;
    if (result.mode === 'NOTE_CREATE') return result.noteId === 0 && result.revision === '' && result.longFields.length === 0 ? result : null;
    return Number.isSafeInteger(result.noteId) && result.noteId > 0 && typeof result.revision === 'string' && /^[0-9a-f]{16,64}$/i.test(result.revision) && typeof result.updatedDate === 'string' ? result : null;
  }
  function scrubWriteResult(result) { if (result?.item) { result.item.title = ''; result.item.contentPreview = ''; result.item.longFields = []; } }
  function clearStage(stage) { if (!stage?.values) return; stage.values.TITLE = ''; stage.values.CONTENT = ''; }
  function releaseRead(read) { if (read?.readId) state.bridge?.releaseNoteFieldReadV1(actionId(), read.readId, () => {}); }
  function requestChunk(read) {
    const request = actionId(); read.request = request; state.pending.set(request, 'readNoteFieldChunkV1');
    state.bridge.readNoteFieldChunkV1(request, read.field, read.readId, read.offset, (ack) => {
      if (state.pending.get(request) === 'readNoteFieldChunkV1' && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) { state.pending.delete(request); finishRead(read, false); }
    });
  }
  function startNextRead(stage) {
    if (state.stage !== stage) return;
    const field = stage.queue.shift();
    if (!field) { applyStage(stage); return; }
    const read = {stage, field, request: '', readId: '', offset: 0, chunks: []}; state.read = read; requestChunk(read);
  }
  function finishRead(read, success) {
    if (state.read !== read) return;
    state.read = null; releaseRead(read);
    if (!success) {
      read.chunks.fill(''); clearStage(read.stage); state.stage = null; state.ready = false; setBusy(false); error('read_failed'); present(); return;
    }
    read.stage.values[read.field] = read.chunks.join(''); read.chunks.fill(''); startNextRead(read.stage);
  }
  function onChunk(action, instanceId, code, _argument, _retry, result) {
    const read = state.read;
    if (!read || read.request !== action || instanceId !== state.instanceId) { if (result) { result.text = ''; if (result.readId) state.bridge?.releaseNoteFieldReadV1(actionId(), result.readId, () => {}); } return; }
    state.pending.delete(action);
    const text = result?.text;
    const length = typeof text === 'string' ? count(text) : -1;
    const valid = code === 'OK' && typeof text === 'string' && length <= 8192 && new TextEncoder().encode(text).length <= 32768 && typeof result.readId === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(result.readId) && (!read.readId || read.readId === result.readId) && Number.isSafeInteger(result.nextOffset) && result.nextOffset === read.offset + length && typeof result.done === 'boolean' && (result.done || result.nextOffset > read.offset);
    if (!valid) { if (result) result.text = ''; finishRead(read, false); return; }
    read.readId = result.readId; read.offset = result.nextOffset; read.chunks.push(text); result.text = '';
    if (result.done) finishRead(read, true); else requestChunk(read);
  }
  function applyStage(stage) {
    if (state.stage !== stage) return;
    $(IDS.TITLE).value = stage.values.TITLE; $(IDS.CONTENT).value = stage.values.CONTENT; setFavorite(stage.favorite);
    state.mode = stage.mode; $('note-editor-delete').hidden = stage.mode !== 'NOTE_EDIT';
    applyProjection({theme: document.documentElement.dataset.pdmEditorTheme, language: state.language, fontScale: document.documentElement.dataset.pdmEditorFont});
    clearStage(stage); state.stage = null; state.ready = true; captureOriginal(); setBusy(false); error(''); present();
  }
  function startStage(initial) {
    const stage = {mode: initial.mode, values: {TITLE: initial.title, CONTENT: initial.content}, favorite: initial.favorite, queue: [...initial.longFields]};
    initial.title = ''; initial.content = ''; state.stage = stage;
    if (stage.queue.length) { setStatus('reading'); startNextRead(stage); } else applyStage(stage);
  }
  function onInitialize(action, instanceId, code, _argument, _retry, result) {
    const matches = !state.instanceId || instanceId === state.instanceId;
    if (state.pending.get(action) !== 'initializeV1' || !matches) { if (result) { result.title = ''; result.content = ''; } return; }
    state.instanceId = instanceId; state.pending.delete(action);
    if (code !== 'OK') { setBusy(false); error('open_failed'); present(); return; }
    const initial = normalizeInitial(result);
    if (!initial) { if (result) { result.title = ''; result.content = ''; } setBusy(false); error('init_failed'); present(); return; }
    startStage(initial);
  }
  function onReload(action, instanceId, code, _argument, _retry, result) {
    if (state.pending.get(action) !== 'reloadLatestV1' || instanceId !== state.instanceId) { if (result) { result.title = ''; result.content = ''; } return; }
    state.pending.delete(action);
    if (code !== 'OK') { setBusy(false); state.ready = code !== 'NOT_FOUND'; error(code === 'CANCELLED' ? 'reload_cancelled' : code === 'NOT_FOUND' ? 'missing' : 'reload_failed'); return; }
    const initial = normalizeInitial(result);
    if (!initial || initial.mode !== 'NOTE_EDIT') { if (result) { result.title = ''; result.content = ''; } setBusy(false); state.ready = false; error('reload_failed'); return; }
    startStage(initial);
  }
  function onWritten(method, action, instanceId, code, _argument, retry, result) {
    if (state.pending.get(action) !== method || instanceId !== state.instanceId) { scrubWriteResult(result); return; }
    state.pending.delete(action); setBusy(false);
    if (code === 'OK') { scrubWriteResult(result); scrub(); return; }
    if (code === 'REVISION_CONFLICT' && method === 'saveNoteV1') { error('conflict'); state.ready = false; setBusy(true, 'reloading'); call('reloadLatestV1', [], () => { setBusy(false); state.ready = true; error('reload_failed'); }); }
    else { error(code === 'NOT_FOUND' ? 'missing' : 'save_failed'); if (retry > 0) setStatus('retry', {seconds: Math.ceil(retry / 1000)}); }
    scrubWriteResult(result);
  }
  function onDeleted(action, instanceId, code) {
    if (state.pending.get(action) !== 'requestDeleteNoteV1' || instanceId !== state.instanceId) return;
    state.pending.delete(action); setBusy(false);
    if (code === 'OK') { scrub(); return; }
    if (code !== 'CANCELLED') error(code === 'NOT_FOUND' ? 'missing' : 'delete_failed');
  }
  function save() {
    if (!state.ready || state.busy || !state.original || state.read) return;
    const current = values(); const title = current.TITLE.trim();
    if (!title) { error('title_required'); $(IDS.TITLE).focus(); return; }
    if ((state.mode === 'NOTE_CREATE' || current.TITLE !== state.original.TITLE) && !fits('TITLE', title)) { error('field_limit'); $(IDS.TITLE).focus(); return; }
    if ((state.mode === 'NOTE_CREATE' || current.CONTENT !== state.original.CONTENT) && !fits('CONTENT', current.CONTENT)) { error('field_limit'); $(IDS.CONTENT).focus(); return; }
    setBusy(true, 'saving'); error('');
    if (state.mode === 'NOTE_CREATE') { call('createNoteV1', [title, current.CONTENT, current.favorite], () => { setBusy(false); error('request_failed'); }); return; }
    const titleChanged = current.TITLE !== state.original.TITLE; const contentChanged = current.CONTENT !== state.original.CONTENT;
    call('saveNoteV1', [titleChanged ? 'REPLACE' : 'KEEP', titleChanged ? title : '', contentChanged ? 'REPLACE' : 'KEEP', contentChanged ? current.CONTENT : '', current.favorite], () => { setBusy(false); error('request_failed'); });
  }
  function requestDelete() {
    if (state.mode !== 'NOTE_EDIT' || !state.ready || state.busy || !state.original) return;
    let label = state.original.TITLE;
    if (!fits('TITLE', label)) {
      label = Array.from(label).slice(0, 255).join('');
      while (new TextEncoder().encode(`${label}…`).length > 1024) label = Array.from(label).slice(0, -1).join('');
      label += '…';
    }
    setBusy(true, 'deleting'); error(''); call('requestDeleteNoteV1', [label], () => { setBusy(false); error('delete_failed'); });
    label = '';
  }
  function scrub() {
    if (state.read) { releaseRead(state.read); state.read.chunks.fill(''); state.read = null; }
    clearStage(state.stage); state.stage = null;
    for (const id of Object.values(IDS)) { $(id).value = ''; $(id).defaultValue = ''; }
    setFavorite(false);
    state.pending.clear(); state.original = null; state.ready = false; state.busy = false; state.dirty = false; state.dirtySent = null; state.presented = false;
  }
  function applyProjection(themeOrProjection = {}, languageValue = 'ZH', fontValue = '100') {
    const projection = typeof themeOrProjection === 'object' ? themeOrProjection : {theme: themeOrProjection, language: languageValue, fontScale: fontValue};
    const theme = projection.theme === 'LIGHT' ? 'LIGHT' : 'DARK'; const language = projection.language === 'EN' || projection.language === 'en' ? 'en' : 'zh'; const font = ['90', '100', '110', '125'].includes(String(projection.fontScale)) ? String(projection.fontScale) : '100';
    state.language = language; document.documentElement.dataset.pdmEditorTheme = theme; document.documentElement.dataset.pdmEditorFont = font; document.documentElement.classList.toggle('light', theme === 'LIGHT'); document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
    const labels = language === 'en' ? {create: 'Add note', edit: 'Edit note', title: 'Title', content: 'Content', titlePlaceholder: 'Enter a note title', contentPlaceholder: 'Enter note content', favorite: 'Favorite', delete: 'Delete', cancel: 'Cancel', save: 'Save'} : {create: '新增记事', edit: '编辑记事', title: '标题', content: '正文', titlePlaceholder: '输入记事标题', contentPlaceholder: '输入记事内容', favorite: '收藏', delete: '删除', cancel: '取消', save: '保存'};
    $('note-editor-title').textContent = state.mode === 'NOTE_CREATE' ? labels.create : labels.edit; $('note-label-title-text').textContent = labels.title; $('note-label-content').textContent = labels.content; $(IDS.TITLE).placeholder = labels.titlePlaceholder; $(IDS.CONTENT).placeholder = labels.contentPlaceholder; $('note-label-favorite').textContent = labels.favorite; $('note-editor-delete').textContent = labels.delete; $('note-editor-cancel').textContent = labels.cancel; $('note-editor-save').textContent = labels.save; error(state.errorKey, state.errorArgs); setStatus(state.statusKey, state.statusArgs);
  }
  function attach(bridge) {
    state.bridge = bridge; const signals = {initializeCompletedV1: onInitialize, reloadLatestCompletedV1: onReload, readNoteFieldChunkCompletedV1: onChunk, createNoteCompletedV1: (...args) => onWritten('createNoteV1', ...args), saveNoteCompletedV1: (...args) => onWritten('saveNoteV1', ...args), deleteNoteCompletedV1: onDeleted};
    for (const [name, handler] of Object.entries(signals)) bridge[name]?.connect(handler);
    bridge.projectionChangedV1?.connect((instanceId, theme, language, fontScale) => { if (instanceId === state.instanceId) applyProjection(theme, language, fontScale); });
    state.ready = true; setBusy(true, 'loading'); call('initializeV1', [], () => { setBusy(false); error('request_failed'); });
  }
  for (const id of Object.values(IDS)) $(id).addEventListener('input', updateDirty);
  $('note-editor-favorite').addEventListener('click', () => { if (!state.busy) { setFavorite(!values().favorite); updateDirty(); } });
  $('note-editor-form').addEventListener('submit', (event) => { event.preventDefault(); save(); });
  $('note-editor-delete').addEventListener('click', requestDelete); $('note-editor-cancel').addEventListener('click', () => { if (!state.busy) state.bridge?.requestCloseV1(); });
  document.addEventListener('keydown', (event) => { if (event.key !== 'Escape' || !event.isTrusted || event.defaultPrevented || event.isComposing || event.keyCode === 229 || state.busy) return; event.preventDefault(); state.bridge?.requestCloseV1(); }, true);
  addEventListener('pagehide', scrub, {capture: true});
  window.pdmNoteEditorRuntime = Object.freeze({attachV1: attach, applyProjectionV1: applyProjection, saveV1: save, scrubV1: scrub, stateV1: () => ({...state, pending: state.pending.size})});
  if (typeof QWebChannel === 'function' && window.qt?.webChannelTransport) new QWebChannel(window.qt.webChannelTransport, (channel) => { const bridge = channel.objects.pdmEditorV1; if (bridge) attach(bridge); else error('request_failed'); });
})();
