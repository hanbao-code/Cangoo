(() => {
  'use strict';

  /*
   * Transitional DOM event adapter for the M1 shared canvas.
   *
   * The old prototype encoded behavior in executable on*= attributes.  The
   * shared canvas keeps those audited expressions as inert data-pdm-on*= data
   * until M3 replaces product operations with typed Bridge commands.  This
   * adapter implements a deliberately small grammar; it never evaluates text.
   */
  const ALLOWED_ACTIONS = new Set([
    'abandonFix',
    'browseDatabase',
    'browseIEFile',
    'captureNoteSaveScrollAnchor',
    'checkDbPasswordMatch',
    'checkIEPasswordMatch',
    'checkStrength',
    'clampGenLength',
    'clampNumInput',
    'clearClipboard',
    'clearDbKeyErrors',
    'clearFieldError',
    'clearGlobalSearch',
    'clearQuickBarSearch',
    'closeFixGuide',
    'closeModal',
    'closeQuickBar',
    'confirmChangeDbPassword',
    'confirmDeleteNote',
    'confirmDeleteRecord',
    'connectDatabase',
    'copyGenerated',
    'copyDemoRecovery',
    'copyText',
    'copyTOTP',
    'deleteNote',
    'deleteRecord',
    'executeIEOperation',
    'expandStartupModal',
    'fillModalGeneratedPassword',
    'fixAll',
    'generatePassword',
    'goFixCurrent',
    'handleQuickBarInput',
    'handleQuickBarKey',
    'handleSearch',
    'hideDemoRecoveryConfirm',
    'lockApp',
    'markDemoRecovery',
    'navigateTo',
    'onPasswordSaved',
    'openAddNoteDialog',
    'openAddPasswordDialog',
    'openChangeDbPasswordDialog',
    'openEditPasswordDialog',
    'openImportExportDialog',
    'openDirectTransferDialog',
    'openQuickBar',
    'prevFix',
    'previewIEImport',
    'quickBarCopyByData',
    'quickBarGenerate',
    'regeneratePassword',
    'reloadLatestEditRecord',
    'resetGenConfig',
    'retryEditAuthorization',
    'resolveAllIEConflicts',
    'resolveIEConflict',
    'saveEditPassword',
    'saveGenerated',
    'saveNewNote',
    'saveNewPassword',
    'saveNote',
    'selectSort',
    'selectSplit',
    'selectSplitFromItem',
    'setFilter',
    'setLang',
    'setNoteFilter',
    'setTheme',
    'setUiFontScale',
    'showFixGuide',
    'skipCurrentInDialog',
    'skipFix',
    'startHotkeyRecording',
    'switchIEMode',
    'switchTool',
    'switchView',
    'syncAutoLockTimeout',
    'syncClipCountdown',
    'syncDemoRecoveryEdit',
    'syncGenLength',
    'syncStaleThreshold',
    'toggleAccordion',
    'toggleAccordionFromSummary',
    'toggleAutoLock',
    'toggleBinarySegment',
    'toggleCharset',
    'toggleDemoRecovery',
    'toggleDemoRecoveryRemoval',
    'toggleCheckPassword',
    'toggleFavorite',
    'toggleGeneratorAvoid',
    'toggleIEConflictSecret',
    'toggleLang',
    'toggleModalFav',
    'toggleModalPwVisibility',
    'toggleEditTotpRemoval',
    'toggleNote',
    'toggleNoteFavorite',
    'togglePasswordVisible',
    'togglePrototypeEditTotpRemoval',
    'toggleSortDropdown',
    'toggleStartupPassword',
    'toggleTheme',
    'updateLongTextHint',
    'updateNoteSaveBtnState',
    'viewDuplicateIssue',
    'viewIssue',
    'windowClose',
    'windowMaximize',
    'windowMinimize',
  ]);
  const ALLOWED_INSPECTOR_ACTIONS = new Set([
    'goBack',
    'goNext',
    'goPrev',
    'selectItem',
  ]);
  const EVENT_NAMES = [
    'blur',
    'change',
    'click',
    'input',
    'keydown',
    'mousedown',
    'scroll',
  ];

  function splitTopLevel(source, separator) {
    const values = [];
    let current = '';
    let quote = '';
    let escaped = false;
    let depth = 0;
    for (const char of source) {
      if (escaped) {
        current += char;
        escaped = false;
      } else if (char === '\\') {
        current += char;
        escaped = true;
      } else if (quote) {
        current += char;
        if (char === quote) quote = '';
      } else if (char === '\'' || char === '"') {
        quote = char;
        current += char;
      } else if (char === '(' || char === '{' || char === '[') {
        depth += 1;
        current += char;
      } else if (char === ')' || char === '}' || char === ']') {
        depth -= 1;
        current += char;
      } else if (char === separator && depth === 0) {
        if (current.trim()) values.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    if (current.trim()) values.push(current.trim());
    return values;
  }

  function parseArgument(raw, target, event) {
    if (raw === 'this') return target;
    if (raw === 'event') return event;
    if (raw === 'this.value') return target.value;
    if (raw === 'this.checked') return Boolean(target.checked);
    if (raw === 'true') return true;
    if (raw === 'false') return false;
    if (raw === 'null') return null;
    if (/^-?\d+(?:\.\d+)?$/.test(raw)) return Number(raw);
    if (
      (raw.startsWith('\'') && raw.endsWith('\'')) ||
      (raw.startsWith('"') && raw.endsWith('"'))
    ) {
      return raw
        .slice(1, -1)
        .replace(/\\n/g, '\n')
        .replace(/\\'/g, '\'')
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\');
    }
    throw new Error(`argument is outside the M1 dispatcher grammar: ${raw}`);
  }

  function resolveAction(name) {
    if (name.startsWith('Insp.')) {
      const method = name.slice('Insp.'.length);
      if (!ALLOWED_INSPECTOR_ACTIONS.has(method) || typeof Insp === 'undefined') return null;
      return Insp[method].bind(Insp);
    }
    if (!ALLOWED_ACTIONS.has(name) || typeof window[name] !== 'function') return null;
    return window[name];
  }

  function runStatement(statement, target, event) {
    const code = statement.trim();
    if (!code) return true;
    if (code === 'event.stopPropagation()') {
      event.stopPropagation();
      return true;
    }
    if (code === 'event.preventDefault()') {
      event.preventDefault();
      return true;
    }
    if (code === "this.classList.toggle('on')") {
      target.classList.toggle('on');
      return true;
    }
    if (code === "this.parentElement.classList.toggle('collapsed')") {
      target.parentElement?.classList.toggle('collapsed');
      return true;
    }
    const assignment = code.match(
      /^IE_STATE\.(path|scope|password|confirmPw)=this\.value$/,
    );
    if (assignment && typeof IE_STATE !== 'undefined') {
      IE_STATE[assignment[1]] = target.value;
      return true;
    }
    const call = code.match(/^([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\((.*)\)$/s);
    if (!call) return false;
    const action = resolveAction(call[1]);
    if (!action) return false;
    const args = call[2].trim()
      ? splitTopLevel(call[2], ',').map((raw) => parseArgument(raw, target, event))
      : [];
    action(...args);
    return true;
  }

  function dispatch(code, target, event) {
    let source = String(code || '').trim();
    const keyGuard = source.match(
      /^if\(event\.key==='Enter'\|\|event\.key===' '\)\{(.+)\}$/,
    );
    if (keyGuard) {
      if (event.key !== 'Enter' && event.key !== ' ') return true;
      source = keyGuard[1];
    }
    const backdropGuard = source.match(/^if\(event\.target===this\)(.+)$/);
    if (backdropGuard) {
      if (event.target !== target) return true;
      source = backdropGuard[1];
    }
    try {
      const statements = splitTopLevel(source, ';');
      const handled = statements.every((statement) => runStatement(statement, target, event));
      if (!handled) {
        window.pdmUnhandledHandlers.push({event: event.type, handler: source});
      }
      return handled;
    } catch (error) {
      window.pdmUnhandledHandlers.push({
        event: event.type,
        handler: source,
        error: String(error),
      });
      return false;
    }
  }

  window.pdmUnhandledHandlers = [];
  window.pdmDispatchInertHandler = dispatch;
  for (const eventName of EVENT_NAMES) {
    document.addEventListener(
      eventName,
      (event) => {
        const target = event.target?.closest?.(`[data-pdm-on${eventName}]`);
        if (!target) return;
        dispatch(target.getAttribute(`data-pdm-on${eventName}`), target, event);
      },
      eventName === 'blur' || eventName === 'scroll',
    );
  }
})();
