(() => {
  'use strict';

  const CONTRACT_VERSION = '1.1.0';
  const runtime = {
    pendingStrengthRetries: new Map(),
    ratingVaultDirty: false,
    ratingHealthDirty: false,
    ratingRefreshQueued: false,
    pendingRatingLocation: '',
    ratingLocationKey: '',
    recoveryInvalidListRequest: '',
    recoveryInvalidRatingRequest: '',
    recoveryFollow: null,
    bridge: null,
    editorLauncher: null,
    transferLauncher: null,
    transferOpening: false,
    editorIntentId: '',
    editorInstanceId: '',
    editorTarget: null,
    pageEpoch: 0,
    sessionEpoch: 0,
    state: 'STARTING',
    ready: false,
    selectionTicket: '',
    backup: null,
    targetKind: 'NONE',
    targetLocked: false,
    displayPath: '',
    databaseLabel: '',
    upgradeBackupName: '',
    pendingHandshake: '',
    pendingContact: null,
    updateState: null,
    updatePending: new Map(),
    queuedUpdatePolicy: null,
    updateError: '',
    updateNoticeKey: '',
    pendingChoose: '',
    openAfterChoose: false,
    pendingRecent: '',
    pendingRecentEntry: null,
    recentTimeTimer: 0,
    recentTimeGeneration: 0,
    pendingRemove: '',
    pendingRemoveIndex: -1,
    pendingRemoveFocusKey: '',
    pendingOpen: '',
    pendingLock: '',
    pendingList: '',
    pendingListKey: '',
    pendingDetails: '',
    pendingDetailsTarget: null,
    queuedDetailsTarget: null,
    retiredDetailsRequest: '',
    pendingFavorite: '',
    pendingFavoriteRecordId: 0,
    fieldRead: null,
    fieldReadQueue: [],
    editorFieldMeta: null,
    editorPreparing: false,
    recordTextModal: null,
    totpDisplay: null,
    pendingTotpCopy: '',
    pendingTotpCopyTarget: null,
    pendingReveal: '',
    revealTarget: null,
    activeReveal: null,
    pendingRecoveryReveal: '',
    recoveryRevealTarget: null,
    activeRecoveryReveal: null,
    pendingRecoveryCopy: '',
    recoveryCopyTarget: null,
    pendingRecoveryMark: '',
    recoveryMarkTarget: null,
    pendingAccountCopy: '',
    pendingPasswordCopy: '',
    pendingClipboardClear: '',
    pendingCreate: '',
    pendingGenerate: '',
    pendingGeneratedCopy: '',
    pendingStrength: '',
    pendingStrengthVersion: 0,
    retiredStrengthRequest: '',
    strengthInputVersion: 0,
    strengthReport: null,
    generateTarget: '',
    toolGeneratedLeaseId: '',
    toolGeneratedElement: null,
    formGeneratedLeaseId: '',
    formGeneratedElement: null,
    createModalActive: false,
    createCooldownUntil: 0,
    createCooldownTimer: 0,
    pendingEditOpen: '',
    editOpenPurpose: '',
    editOpenRecordId: 0,
    editOpenRevision: '',
    pendingEditSave: '',
    editSubmittedLeaseId: '',
    editModalActive: false,
    editRecordId: 0,
    editRevision: '',
    editLeaseId: '',
    editHasTotp: false,
    editTotpAction: 'KEEP',
    editPasswordDirty: false,
    editConflict: false,
    editReloadRevision: '',
    editGenerateAfterOpen: false,
    editCooldownUntil: 0,
    editCooldownTimer: 0,
    pendingDeletePrepare: '',
    pendingDeleteCommit: '',
    deleteModalActive: false,
    deleteRecordId: 0,
    deleteRevision: '',
    deleteLabel: '',
    clipboardKind: 'NONE',
    clipboardMode: 'COUNTDOWN',
    clipboardRemaining: 0,
    clipboardOwned: false,
    vaultItems: [],
    vaultCounts: {all: 0, favorite: 0, weak: 0, duplicate: 0, similar: 0},
    vaultTotal: 0,
    vaultRevision: '',
    vaultNextCursor: '',
    vaultCursor: '',
    vaultCursorHistory: [],
    vaultQuery: '',
    vaultFilter: 'ALL',
    vaultSort: 'UPDATED',
    vaultView: 'LIST',
    pendingHealthSummary: '',
    healthRescan: null,
    pendingHealthRescan: null,
    healthRescanTimer: 0,
    healthRescanCancelQueued: false,
    healthRescanError: '',
    healthRescanRefreshPending: false,
    healthRescanVaultDirty: false,
    healthRescanVaultRequest: '',
    pendingHealthIssues: {WEAK: '', DUPLICATE: '', STALE: ''},
    healthPagerFocus: {WEAK: '', DUPLICATE: '', STALE: ''},
    pendingHealthLocate: '',
    healthLocateTarget: null,
    healthEditRecordId: 0,
    healthSingleOrigin: null,
    pendingHealthOverview: '',
    healthOverviewMode: '',
    pendingHealthGuidance: '',
    healthGuideTargetIndex: 0,
    healthGuideRequestCursor: '',
    healthGuideResetIndex: -1,
    healthGuide: null,
    healthGuideEditTarget: null,
    pendingStaleThreshold: '',
    pendingStaleDays: 0,
    healthRevision: '',
    healthSummary: null,
    healthPages: {
      WEAK: {items: [], groups: [], total: 0, nextCursor: '', previousCursor: '', pageIndex: 0, error: ''},
      DUPLICATE: {items: [], groups: [], total: 0, nextCursor: '', previousCursor: '', pageIndex: 0, error: ''},
      STALE: {items: [], groups: [], total: 0, nextCursor: '', previousCursor: '', pageIndex: 0, error: ''},
    },
    healthError: '',
    selectedRecordId: 0,
    selectedRevision: '',
    selectedDetails: null,
    searchTimer: 0,
    pendingNoteList: '',
    pendingNoteListKey: '',
    noteListFocusKeys: [],
    noteListFocusGuard: null,
    pendingNoteDetails: '',
    pendingNoteFieldRead: '',
    noteFieldRead: null,
    pendingNoteSave: '',
    pendingNoteFavorite: '',
    pendingNoteFavoriteId: 0,
    pendingNoteDeletePrepare: '',
    pendingNoteDeleteCommit: '',
    noteDraft: null,
    noteEditReturnToOverview: false,
    noteEditRequestedId: 0,
    noteDelete: null,
    pendingNoteCreate: '',
    noteCreateModalActive: false,
    noteCreateReturnFocus: '',
    noteCreateCooldownUntil: 0,
    noteCreateCooldownTimer: 0,
    noteItems: [],
    noteTotal: 0,
    noteAllCount: 0,
    noteFavoriteCount: 0,
    noteRevision: '',
    noteNextCursor: '',
    noteCursor: '',
    noteCursorHistory: [],
    notePageInvalidated: false,
    notePageTarget: 0,
    noteQuery: '',
    noteFilter: 'ALL',
    noteSort: 'UPDATED',
    selectedNoteId: 0,
    selectedNoteRevision: '',
    selectedNoteDetails: null,
    noteSearchTimer: 0,
    pendingChangeKey: '',
    changeKeyModalActive: false,
    changeKeyCooldownUntil: 0,
    changeKeyCooldownTimer: 0,
    changeKeyProgressPhase: '',
    changeKeyBusyRevealTimer: 0,
    changeKeyBusyVisible: false,
    changeKeyTerminalReason: '',
    settingsRevision: '',
    settings: null,
    themePreference: 'DARK',
    effectiveTheme: 'DARK',
    language: 'ZH',
    uiFontScale: '100',
    pendingTheme: '',
    pendingThemeValue: '',
    pendingThemeChanged: false,
    pendingThemeRevision: '',
    pendingThemeSettings: null,
    pendingLanguage: '',
    pendingLanguageValue: '',
    pendingLanguageRevision: '',
    pendingLanguageSettings: null,
    pendingUiFontScale: '',
    pendingUiFontScaleValue: '',
    pendingUiFontScaleRevision: '',
    pendingUiFontScaleSettings: null,
    pendingStartupAutofill: '',
    pendingStartupAutofillValue: false,
    pendingStartupAutofillRevision: '',
    pendingStartupAutofillSettings: null,
    pendingDefaultView: '',
    pendingDefaultViewValue: '',
    pendingDefaultViewRevision: '',
    pendingDefaultViewSettings: null,
    pendingSidebarText: '',
    pendingSidebarTextValue: false,
    pendingSidebarTextRevision: '',
    pendingSidebarTextSettings: null,
    pendingClipboardPolicy: '',
    pendingClipboardMode: '',
    pendingClipboardSeconds: 30,
    pendingClipboardRevision: '',
    pendingClipboardSettings: null,
    pendingSort: '',
    pendingSortValue: '',
    pendingSortRevision: '',
    pendingSortSettings: null,
    pendingClose: '',
    pendingCloseValue: '',
    pendingCloseRevision: '',
    pendingCloseSettings: null,
    pendingAutoLock: '',
    pendingAutoLockEnabled: false,
    pendingAutoLockMinutes: 5,
    pendingAutoLockRevision: '',
    pendingAutoLockSettings: null,
    pendingGeneratorDefaults: '',
    pendingGeneratorPolicy: null,
    queuedGeneratorPolicy: null,
    pendingGeneratorRevision: '',
    pendingGeneratorSettings: null,
    generatorCommittedPolicy: null,
    generatorDraftDirty: false,
    generatorLastValidLength: 20,
    generatorGenerateAfterSaveKey: '',
    pendingQuickbarOpen: '',
    pendingQuickbarEnabled: '',
    pendingQuickbarEnabledValue: false,
    pendingQuickbarIdleSeconds: 30,
    pendingQuickbarEnabledRevision: '',
    pendingQuickbarEnabledSettings: null,
    pendingQuickbarHotkey: '',
    pendingQuickbarHotkeyValue: '',
    pendingQuickbarHotkeyRevision: '',
    pendingQuickbarHotkeySettings: null,
    pendingQuickbarHotkeyWarning: 'NONE',
    hotkeyRecording: false,
    lastLockReason: '',
    lockedNotice: '',
    projectedSettingsSignals: [],
    settingsProjectionSource: 'DEFAULT',
    settingsProjectionCount: 0,
    systemThemeProjectionCount: 0,
    themeSuccessToastCount: 0,
    hostWindowPresentable: false,
    pageUnloading: false,
  };

  const TOAST_PRESENTATION_AVAILABLE = (
    typeof setToastPresentationVisible === 'function'
  );
  if (TOAST_PRESENTATION_AVAILABLE) setToastPresentationVisible(false);

  const publicProduct = {};
  Object.defineProperties(publicProduct, {
    ready: {enumerable: true, get: () => runtime.ready},
    bootstrapVersion: {enumerable: true, value: 1},
  });
  Object.freeze(publicProduct);
  Object.defineProperty(window, 'pdmProduct', {
    configurable: false,
    enumerable: false,
    value: publicProduct,
    writable: false,
  });

  function snapshot() {
    return Object.freeze({
      ready: runtime.ready,
      state: runtime.state,
      pageEpoch: runtime.pageEpoch,
      sessionEpoch: runtime.sessionEpoch,
      targetKind: runtime.targetKind,
      displayPath: runtime.displayPath,
      pendingChoose: Boolean(runtime.pendingChoose),
      pendingRecent: Boolean(runtime.pendingRecent),
      pendingRemove: Boolean(runtime.pendingRemove),
      pendingOpen: Boolean(runtime.pendingOpen),
      pendingLock: Boolean(runtime.pendingLock),
      pendingList: Boolean(runtime.pendingList),
      pendingDetails: Boolean(runtime.pendingDetails),
      pendingReveal: Boolean(runtime.pendingReveal),
      activeReveal: Boolean(runtime.activeReveal),
      pendingAccountCopy: Boolean(runtime.pendingAccountCopy),
      pendingPasswordCopy: Boolean(runtime.pendingPasswordCopy),
      pendingClipboardClear: Boolean(runtime.pendingClipboardClear),
      pendingCreate: Boolean(runtime.pendingCreate),
      pendingGenerate: Boolean(runtime.pendingGenerate),
      hasToolGeneratedLease: Boolean(runtime.toolGeneratedLeaseId),
      hasFormGeneratedLease: Boolean(runtime.formGeneratedLeaseId),
      pendingGeneratedCopy: Boolean(runtime.pendingGeneratedCopy),
      pendingStrength: Boolean(runtime.pendingStrength),
      pendingGeneratorDefaults: Boolean(runtime.pendingGeneratorDefaults),
      generatorDraftDirty: runtime.generatorDraftDirty,
      createModalActive: runtime.createModalActive,
      createCoolingDown: runtime.createCooldownUntil > Date.now(),
      pendingEditOpen: Boolean(runtime.pendingEditOpen),
      pendingEditSave: Boolean(runtime.pendingEditSave),
      editModalActive: runtime.editModalActive,
      editCoolingDown: runtime.editCooldownUntil > Date.now(),
      editConflict: runtime.editConflict,
      editHasLease: Boolean(runtime.editLeaseId),
      editReloadReady: Boolean(runtime.editReloadRevision),
      pendingDeletePrepare: Boolean(runtime.pendingDeletePrepare),
      pendingDeleteCommit: Boolean(runtime.pendingDeleteCommit),
      deleteModalActive: runtime.deleteModalActive,
      clipboardKind: runtime.clipboardKind,
      clipboardMode: runtime.clipboardMode,
      clipboardRemaining: runtime.clipboardRemaining,
      clipboardOwned: runtime.clipboardOwned,
      vaultItemCount: runtime.vaultItems.length,
      vaultTotal: runtime.vaultTotal,
      vaultHasNextPage: Boolean(runtime.vaultNextCursor),
      selectedRecordId: runtime.selectedRecordId,
      pendingNoteList: Boolean(runtime.pendingNoteList),
      pendingNoteDetails: Boolean(runtime.pendingNoteDetails),
      pendingNoteCreate: Boolean(runtime.pendingNoteCreate),
      noteCreateModalActive: runtime.noteCreateModalActive,
      noteCreateCoolingDown: (
        runtime.noteCreateCooldownUntil > Date.now()
      ),
      noteItemCount: runtime.noteItems.length,
      noteTotal: runtime.noteTotal,
      noteHasNextPage: Boolean(runtime.noteNextCursor),
      selectedNoteId: runtime.selectedNoteId,
      pendingChangeKey: Boolean(runtime.pendingChangeKey),
      changeKeyModalActive: runtime.changeKeyModalActive,
      changeKeyCoolingDown: runtime.changeKeyCooldownUntil > Date.now(),
      changeKeyProgressPhase: runtime.changeKeyProgressPhase,
      changeKeyBusyVisible: runtime.changeKeyBusyVisible,
      settingsRevision: runtime.settingsRevision,
      hasSettingsSnapshot: Boolean(runtime.settings),
      themePreference: runtime.themePreference,
      effectiveTheme: runtime.effectiveTheme,
      language: runtime.language,
      pendingTheme: Boolean(runtime.pendingTheme),
      pendingThemeValue: runtime.pendingThemeValue,
      pendingLanguage: Boolean(runtime.pendingLanguage),
      pendingLanguageValue: runtime.pendingLanguageValue,
      pendingUiFontScale: Boolean(runtime.pendingUiFontScale),
      pendingUiFontScaleValue: runtime.pendingUiFontScaleValue,
      pendingClose: Boolean(runtime.pendingClose),
      pendingCloseValue: runtime.pendingCloseValue,
      pendingAutoLock: Boolean(runtime.pendingAutoLock),
      pendingAutoLockEnabled: runtime.pendingAutoLockEnabled,
      pendingAutoLockMinutes: runtime.pendingAutoLockMinutes,
      pendingQuickbarOpen: Boolean(runtime.pendingQuickbarOpen),
      pendingQuickbarEnabled: Boolean(runtime.pendingQuickbarEnabled),
      pendingQuickbarEnabledValue: runtime.pendingQuickbarEnabledValue,
      pendingQuickbarIdleSeconds: runtime.pendingQuickbarIdleSeconds,
      pendingQuickbarHotkey: Boolean(runtime.pendingQuickbarHotkey),
      pendingQuickbarHotkeyValue: runtime.pendingQuickbarHotkeyValue,
      hotkeyRecording: runtime.hotkeyRecording,
      quickbarEnabled: runtime.settings?.quickbarEnabled ?? false,
      quickbarIdleSeconds: runtime.settings?.quickbarIdleSeconds ?? 30,
      quickbarHotkey: runtime.settings?.quickbarHotkey ?? '',
      quickbarRegistration: runtime.settings?.quickbarRegistration ?? 'DISABLED',
      autoLockEnabled: runtime.settings?.autoLockEnabled ?? false,
      autoLockMinutes: runtime.settings?.autoLockMinutes ?? 0,
      lastLockReason: runtime.lastLockReason,
      settingsProjectionSource: runtime.settingsProjectionSource,
      settingsProjectionCount: runtime.settingsProjectionCount,
      systemThemeProjectionCount: runtime.systemThemeProjectionCount,
      themeSuccessToastCount: runtime.themeSuccessToastCount,
      localizedRuntimeTextIssueCount: localizedRuntimeTextIssueCount(),
    });
  }

  function isLockedConnectionReady(expectedTerminalReason) {
    const password = byId('db-password');
    const path = byId('db-path');
    const startup = byId('startup-page');
    const minimizedBar = byId('startup-minimized-bar');
    const recentsList = byId('recent-list');
    const sortDropdown = byId('sort-dropdown');
    const quickbar = byId('quickbar-overlay');
    const generatedOutput = byId('gen-output');
    const feedback = byId('connection-feedback');
    const topbarTitle = byId('topbar-title');
    const navigation = Array.from(
      document.querySelectorAll('.nav-item[data-nav]'),
    );
    const activeNavigation = navigation.filter(
      (item) => item.classList.contains('active'),
    );
    const currentNavigation = navigation.filter(
      (item) => item.getAttribute('aria-current') === 'page',
    );
    const sensitive = (
      window.pdmSensitiveDom &&
      typeof window.pdmSensitiveDom.snapshot === 'function'
    ) ? window.pdmSensitiveDom.snapshot() : null;
    const expectedTerminalMatches = (
      typeof expectedTerminalReason === 'undefined' ||
      (
        [
          'CHANGE_KEY_SUCCESS',
          'CHANGE_KEY_RESTORED',
        ].includes(expectedTerminalReason) &&
        runtime.changeKeyTerminalReason === expectedTerminalReason
      )
    );
    const noPendingRequests = [
      runtime.pendingHandshake,
      runtime.pendingChoose,
      runtime.pendingRecent,
      runtime.pendingRemove,
      runtime.pendingOpen,
      runtime.pendingLock,
      runtime.pendingList,
      runtime.pendingListKey,
      runtime.pendingDetails,
      runtime.retiredDetailsRequest,
      runtime.pendingFavorite,
      runtime.pendingReveal,
      runtime.pendingAccountCopy,
      runtime.pendingPasswordCopy,
      runtime.pendingClipboardClear,
      runtime.pendingCreate,
      runtime.pendingGenerate,
      runtime.pendingGeneratedCopy,
      runtime.pendingStrength,
      runtime.retiredStrengthRequest,
      runtime.pendingEditOpen,
      runtime.pendingEditSave,
      runtime.pendingDeletePrepare,
      runtime.pendingDeleteCommit,
      runtime.pendingNoteList,
      runtime.pendingNoteListKey,
      runtime.pendingNoteDetails,
      runtime.pendingNoteCreate,
      runtime.pendingChangeKey,
      runtime.pendingTheme,
      runtime.pendingLanguage,
      runtime.pendingUiFontScale,
      runtime.pendingSort,
      runtime.pendingClose,
      runtime.pendingAutoLock,
      runtime.pendingGeneratorDefaults,
      runtime.pendingQuickbarOpen,
      runtime.pendingQuickbarEnabled,
      runtime.pendingQuickbarHotkey,
    ].every((value) => !value);
    return Boolean(
      runtime.ready &&
      runtime.state === 'LOCKED' &&
      Number.isSafeInteger(runtime.pageEpoch) &&
      runtime.pageEpoch > 0 &&
      runtime.sessionEpoch === 0 &&
      password instanceof HTMLInputElement &&
      password.value === '' &&
      password.type === 'password' &&
      path instanceof HTMLInputElement &&
      path.value === runtime.displayPath &&
      runtime.selectionTicket === '' &&
      noPendingRequests &&
      !runtime.createModalActive &&
      !runtime.editModalActive &&
      !runtime.deleteModalActive &&
      !runtime.noteCreateModalActive &&
      !runtime.changeKeyModalActive &&
      !activeCreateModal() &&
      !activeEditModal() &&
      !activeDeleteModal() &&
      !activeNoteCreateModal() &&
      !activeChangeKeyModal() &&
      sortDropdown &&
      !sortDropdown.classList.contains('open') &&
      quickbar &&
      !quickbar.classList.contains('visible') &&
      runtime.vaultItems.length === 0 &&
      runtime.noteItems.length === 0 &&
      runtime.selectedDetails === null &&
      runtime.selectedNoteDetails === null &&
      runtime.selectedRecordId === 0 &&
      runtime.selectedNoteId === 0 &&
      passwords.length === 0 &&
      notes.length === 0 &&
      runtime.revealTarget === null &&
      runtime.activeReveal === null &&
      !runtime.toolGeneratedLeaseId &&
      runtime.toolGeneratedElement === null &&
      !runtime.formGeneratedLeaseId &&
      runtime.formGeneratedElement === null &&
      state.genPassword === '' &&
      generatedOutput &&
      !generatedOutput.hasAttribute('data-pdm-sensitive') &&
      runtime.clipboardKind === 'NONE' &&
      runtime.clipboardRemaining === 0 &&
      !runtime.clipboardOwned &&
      sensitive &&
      sensitive.activeLeaseCount === 0 &&
      sensitive.activeTransientCount === 0 &&
      sensitive.boundNodeCount === 0 &&
      startup &&
      !startup.classList.contains('hidden') &&
      !startup.classList.contains('minimized') &&
      state.currentNav === 'vault' &&
      navigation.length > 0 &&
      navigation[0].dataset.nav === 'vault' &&
      activeNavigation.length === 1 &&
      activeNavigation[0] === navigation[0] &&
      currentNavigation.length === 1 &&
      currentNavigation[0] === navigation[0] &&
      topbarTitle &&
      topbarTitle.dataset.i18n === 'topbar.title.connect' &&
      minimizedBar &&
      !minimizedBar.classList.contains('show') &&
      recentsList &&
      recentsList.dataset.pdmM4RecentsReady === 'true' &&
      typeof runtime.settingsRevision === 'string' &&
      runtime.settingsRevision.length > 0 &&
      runtime.settings &&
      ['LIGHT', 'DARK', 'AUTO'].includes(runtime.themePreference) &&
      ['LIGHT', 'DARK'].includes(runtime.effectiveTheme) &&
      ['ZH', 'EN'].includes(runtime.language) &&
      runtime.settings.theme === runtime.themePreference &&
      runtime.settings.effectiveTheme === runtime.effectiveTheme &&
      runtime.settings.language === runtime.language &&
      document.documentElement.lang === (
        runtime.language === 'EN' ? 'en' : 'zh-CN'
      ) &&
      document.documentElement.classList.contains('light') === (
        runtime.effectiveTheme === 'LIGHT'
      ) &&
      expectedTerminalMatches &&
      (
        runtime.changeKeyTerminalReason === '' ||
        (
          runtime.changeKeyTerminalReason === 'CHANGE_KEY_SUCCESS' &&
          feedback &&
          feedback.getAttribute('aria-hidden') === 'false' &&
          feedback.dataset.pdmFixedZh === (
            '数据库密码已修改，请使用新密码重新连接。'
          ) &&
          feedback.dataset.pdmFixedEn === (
            'The database password was changed. Reconnect with the new password.'
          )
        ) ||
        (
          runtime.changeKeyTerminalReason === 'CHANGE_KEY_RESTORED' &&
          feedback &&
          feedback.getAttribute('aria-hidden') === 'false' &&
          feedback.dataset.pdmErrorCode === 'CHANGE_KEY_FAILED_RESTORED'
        )
      )
    );
  }

  function lockedConnectionPresentationSample(expectedTerminalReason) {
    if (!isLockedConnectionReady(expectedTerminalReason)) return '';
    if (
      typeof expectedTerminalReason !== 'undefined' &&
      ![
        'CHANGE_KEY_SUCCESS',
        'CHANGE_KEY_RESTORED',
      ].includes(expectedTerminalReason)
    ) {
      return '';
    }
    const startup = byId('startup-page');
    const card = document.querySelector('.startup-card');
    const recents = byId('recent-list');
    const notice = byId('connection-feedback');
    if (
      !(startup instanceof HTMLElement) ||
      !(card instanceof HTMLElement) ||
      !(recents instanceof HTMLElement) ||
      !(notice instanceof HTMLElement)
    ) {
      return '';
    }
    const roundedRect = (element) => {
      const rect = element.getBoundingClientRect();
      return [
        Math.round(rect.x),
        Math.round(rect.y),
        Math.round(rect.width),
        Math.round(rect.height),
      ];
    };
    const navigation = Array.from(
      document.querySelectorAll('.nav-item[data-nav]'),
    );
    const connectionOnly = Boolean(
      document.documentElement.classList.contains(
        'pdm-security-lock-handoff-static',
      ) &&
      !startup.classList.contains('hidden') &&
      !startup.classList.contains('minimized')
    );
    const firstSidebarOnly = Boolean(
      navigation.length > 0 &&
      navigation[0].dataset.nav === 'vault' &&
      navigation.filter((item) => item.classList.contains('active')).length
        === 1 &&
      navigation.filter(
        (item) => item.getAttribute('aria-current') === 'page',
      ).length === 1 &&
      navigation[0].classList.contains('active') &&
      navigation[0].getAttribute('aria-current') === 'page'
    );
    const themeMatches = Boolean(
      runtime.settings &&
      runtime.settings.theme === runtime.themePreference &&
      runtime.settings.effectiveTheme === runtime.effectiveTheme &&
      document.documentElement.classList.contains('light') === (
        runtime.effectiveTheme === 'LIGHT'
      )
    );
    const languageMatches = Boolean(
      runtime.settings &&
      runtime.settings.language === runtime.language &&
      document.documentElement.lang === (
        runtime.language === 'EN' ? 'en' : 'zh-CN'
      )
    );
    if (![
      connectionOnly,
      firstSidebarOnly,
      themeMatches,
      languageMatches,
    ].every(Boolean)) {
      return '';
    }
    return JSON.stringify([
      connectionOnly,
      firstSidebarOnly,
      themeMatches,
      languageMatches,
      true,
      true,
      true,
      true,
      roundedRect(startup),
      roundedRect(card),
      roundedRect(recents),
      roundedRect(notice),
      recents.querySelectorAll('.recent-item').length,
    ]);
  }

  function rememberLockedNotice(notice) {
    if (
      runtime.lockedNotice ||
      !['AUTO', 'SUSPEND'].includes(notice)
    ) {
      return;
    }
    runtime.lockedNotice = notice;
  }

  function consumeLockedNotice() {
    if (
      !runtime.lockedNotice ||
      !isLockedConnectionReady() ||
      document.visibilityState !== 'visible'
    ) {
      return false;
    }
    const notice = runtime.lockedNotice;
    runtime.lockedNotice = '';
    if (notice === 'AUTO') {
      showI18nToast('toast.autolocked', 'info');
      return true;
    }
    if (notice === 'SUSPEND') {
      showI18nToast('toast.suspendLocked', 'info');
      return true;
    }
    return false;
  }

  function showClaimedChangeKeySuccessToast() {
    showI18nToast('toast.keyChanged', 'success');
    return true;
  }

  function showNativeClipboardUnavailableToast() {
    if (
      arguments.length ||
      !runtime.ready ||
      runtime.pageEpoch <= 0 ||
      !['LOCKED', 'UNLOCKED'].includes(runtime.state) ||
      document.visibilityState !== 'visible'
    ) {
      return false;
    }
    showErrorToast('CLIPBOARD_UNAVAILABLE');
    return true;
  }

  function setHostWindowPresentable(presentable) {
    if (
      arguments.length !== 1 ||
      typeof presentable !== 'boolean' ||
      runtime.pageUnloading ||
      !TOAST_PRESENTATION_AVAILABLE
    ) {
      return false;
    }
    runtime.hostWindowPresentable = presentable;
    syncRecentTimeRefresh();
    if (presentable) queueRatingRefresh();
    const result = setToastPresentationVisible(
      presentable && document.visibilityState === 'visible',
    );
    renderProductUpdates();
    return result;
  }

  Object.defineProperty(window, 'pdmM4', {
    configurable: false,
    enumerable: false,
    value: Object.freeze({
      snapshot,
      isLockedConnectionReady,
      lockedConnectionPresentationSample,
      consumeLockedNotice,
      showClaimedChangeKeySuccessToast,
      showNativeClipboardUnavailableToast,
      setHostWindowPresentable,
    }),
    writable: false,
  });

  function requestId() {
    if (
      !window.crypto ||
      typeof window.crypto.randomUUID !== 'function'
    ) {
      throw new Error('secure request identity unavailable');
    }
    return window.crypto.randomUUID();
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function focusKeyForElement(element) {
    if (!(element instanceof HTMLElement)) return '';
    return String(
      element.dataset.pdmNativeFocusKey || element.id || '',
    );
  }

  function appendNearestFocusKeys(keys, elements, activeElement) {
    const activeIndex = elements.indexOf(activeElement);
    if (activeIndex < 0) return;
    for (let distance = 1; distance < elements.length; distance += 1) {
      for (const index of [activeIndex + distance, activeIndex - distance]) {
        if (index < 0 || index >= elements.length) continue;
        const key = focusKeyForElement(elements[index]);
        if (key && !keys.includes(key)) keys.push(key);
        if (keys.length >= 16) return;
      }
    }
  }

  function focusFallbackKeys(activeElement = document.activeElement) {
    if (!(activeElement instanceof HTMLElement)) return [];
    const keys = [];
    const activeKey = focusKeyForElement(activeElement);
    if (activeKey) keys.push(activeKey);

    const recordPattern = /^(vault-action|note-action):(\d+):([A-Za-z0-9_-]+)$/;
    const recordMatch = recordPattern.exec(activeKey);
    if (recordMatch) {
      if (recordMatch[1] === 'note-action') {
        const prefix = `note-action:${recordMatch[2]}:`;
        const transitions = {
          read: ['body', 'edit'],
          edit: ['title'],
          save: ['title', 'content', 'edit', 'body', 'read'],
          pending: ['title', 'edit', 'body', 'read'],
          cancel: ['edit', 'body', 'read'],
          back: ['read', 'edit'],
          title: ['edit', 'body', 'read'],
          content: ['edit', 'body', 'read'],
        };
        for (const action of transitions[recordMatch[3]] || []) {
          keys.push(prefix + action);
        }
      }
      const peers = Array.from(document.querySelectorAll(
        '[data-pdm-native-focus-key]',
      )).filter((element) => {
        const match = recordPattern.exec(
          String(element.dataset.pdmNativeFocusKey || ''),
        );
        return Boolean(
          match &&
          match[1] === recordMatch[1] &&
          match[3] === recordMatch[3]
        );
      });
      appendNearestFocusKeys(keys, peers, activeElement);
    } else {
      const stableGroup = /^(vault-list|vault-split|note):(\d+)$/;
      const groupMatch = stableGroup.exec(activeKey);
      if (groupMatch) {
        const peers = Array.from(document.querySelectorAll(
          '[data-pdm-native-focus-key]',
        )).filter((element) => String(
          element.dataset.pdmNativeFocusKey || '',
        ).startsWith(`${groupMatch[1]}:`));
        appendNearestFocusKeys(keys, peers, activeElement);
        if (groupMatch[1] === 'vault-list' || groupMatch[1] === 'vault-split') {
          if (keys.length >= 16) keys.length = 15;
          if (!keys.includes('global-search')) keys.push('global-search');
        }
      }
    }

    const group = activeElement.closest(
      '.sidebar,.filter-chips,.view-switcher,.quick-actions,.actions,'
      + '.detail-buttons,.note-actions,.modal-footer,.modal-footer-right,'
      + '.setting-control',
    );
    if (group) {
      appendNearestFocusKeys(
        keys,
        Array.from(group.querySelectorAll(
          '[data-pdm-native-focus-key],[id]',
        )),
        activeElement,
      );
    }
    return keys.slice(0, 16);
  }

  function preserveProductFocus(renderRoot, render, fallbackKeys = null) {
    const focusVisibility = window.pdmFocusVisibility;
    if (!focusVisibility) return render();
    return focusVisibility.preserve(
      renderRoot instanceof HTMLElement ? renderRoot : document,
      render,
      Array.isArray(fallbackKeys) ? fallbackKeys : focusFallbackKeys(),
    );
  }

  function vaultRecordFocusKeys(recordId) {
    const prefix = runtime.vaultView === 'SPLIT' ? 'vault-split' : 'vault-list';
    return Number.isSafeInteger(recordId) && recordId > 0
      ? [`${prefix}:${recordId}`, 'global-search']
      : ['global-search'];
  }

  function vaultDeleteFocusKeys(recordId) {
    const index = runtime.vaultItems.findIndex((item) => item.recordId === recordId);
    const neighbor = index >= 0
      ? (runtime.vaultItems[index + 1] || runtime.vaultItems[index - 1])
      : null;
    return vaultRecordFocusKeys(neighbor?.recordId || 0);
  }

  function noteDeleteFocusKeys(noteId) {
    const index = runtime.noteItems.findIndex((item) => item.noteId === noteId);
    const neighbor = index >= 0
      ? (runtime.noteItems[index + 1] || runtime.noteItems[index - 1])
      : null;
    return neighbor
      ? [`note-action:${neighbor.noteId}:read`, 'note-sort-trigger', 'global-search']
      : ['note-sort-trigger', 'global-search'];
  }

  function hardFocusTargetUnavailable(element) {
    if (!(element instanceof HTMLElement)) return false;
    return Boolean(
      !element.isConnected ||
      element.hidden ||
      element.getClientRects().length === 0 ||
      element.getAttribute('aria-hidden') === 'true' ||
      element.tabIndex === -1 ||
      ('disabled' in element && element.disabled === true)
    );
  }

  function setFeedback(
    kind,
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const feedback = byId('connection-feedback');
    if (!feedback) return;
    feedback.className = 'connection-feedback';
    if (kind) feedback.classList.add(kind);
    const visible = setRuntimeText(
      feedback,
      text,
      fixedZh,
      fixedEn,
      i18nKey,
    );
    if (!visible) feedback.className = 'connection-feedback';
    feedback.setAttribute('aria-hidden', visible ? 'false' : 'true');
  }

  function restoreChangeKeyConnectionNotice() {
    const feedback = byId('connection-feedback');
    if (!feedback) return false;
    if (runtime.changeKeyTerminalReason === 'CHANGE_KEY_SUCCESS') {
      setFeedback(
        'success',
        '',
        '数据库密码已修改，请使用新密码重新连接。',
        'The database password was changed. Reconnect with the new password.',
      );
      return true;
    }
    if (runtime.changeKeyTerminalReason === 'CHANGE_KEY_RESTORED') {
      setFeedback('error', errorText('CHANGE_KEY_FAILED_RESTORED'));
      return true;
    }
    return false;
  }

  function focusLockedDatabasePassword() {
    const password = byId('db-password');
    if (
      runtime.state !== 'LOCKED' ||
      runtime.sessionEpoch !== 0 ||
      !(password instanceof HTMLInputElement)
    ) {
      return false;
    }
    password.focus({preventScroll: true});
    if (document.activeElement !== password) return false;
    window.__pdmNativeFocusDescriptor = 'connection:password';
    return true;
  }

  function fixedText(zh, en) {
    return state.lang === 'en' ? en : zh;
  }

  function connectionTargetErrorText(code) {
    if (code === 'INVALID_ARGUMENT') {
      return fixedText(
        '数据库路径格式无效或不在当前允许目录内，请使用右侧“…”重新选择。',
        'The database path is invalid or outside the current allowed directory. Use the path-side “…” button to select it again.',
      );
    }
    return errorText(code);
  }

  function errorPair(code) {
    const values = {
      AUTH_FAILED_RETRY_2: [
        '主密码错误，还可尝试 2 次。',
        'Incorrect master password. 2 attempts remaining.',
      ],
      AUTH_FAILED_RETRY_1: [
        '主密码错误，还可尝试 1 次。',
        'Incorrect master password. 1 attempt remaining.',
      ],
      LOCKED_OUT: [
        '密码错误次数过多，该数据库已锁定 24 小时。',
        'Too many failed attempts. This database is locked for 24 hours.',
      ],
      NOT_FOUND: [
        '数据库文件不存在，请重新选择。',
        'The database file no longer exists. Select it again.',
      ],
      REQUEST_BUSY: [
        '已有操作正在进行，请稍候。',
        'Another operation is in progress.',
      ],
      SELECTION_EXPIRED: [
        '数据库目标授权已过期，请重新选择。',
        'The database selection expired. Select it again.',
      ],
      DATABASE_INVALID: [
        '数据库文件已损坏、无法读取或在选择后发生变化。',
        'The database is damaged, unreadable, or changed after selection.',
      ],
      DATABASE_IO_FAILED: [
        '无法访问该位置，请检查读取或写入权限后重试。',
        'This location cannot be accessed. Check its read or write permissions and retry.',
      ],
      DATABASE_LIMIT_EXCEEDED: [
        '当前可用内存不足以完成此操作。请释放一些内存后重试。',
        'There is not enough memory to complete this operation. Free some memory and retry.',
      ],
      DATABASE_SPACE_INSUFFICIENT: [
        '磁盘空间不足以完成此操作。请释放空间后重试。',
        'There is not enough disk space to complete this operation. Free some space and retry.',
      ],
      CLIPBOARD_UNAVAILABLE: [
        '剪贴板暂时不可用，请稍后重试。',
        'The clipboard is temporarily unavailable. Try again.',
      ],
      EMPTY_FIELD: [
        '目标字段为空，未复制。',
        'The field is empty and was not copied.',
      ],
      PLATFORM_CONFLICT: [
        '平台名已存在，请使用不同的名称',
        'Platform name already exists, use a different name',
      ],
      EMPTY_CHARACTER_SET: [
        '请至少选择一种字符类型。',
        'Select at least one character set.',
      ],
      GENERATOR_LENGTH_TOO_SHORT: [
        '密码长度不能小于已选择的字符类型数量。',
        'Password length cannot be shorter than the selected character-set count.',
      ],
      PASSWORD_STRENGTH_FAILED: [
        '密码强度检测失败，记录未保存，请重试。',
        'Password strength check failed. The record was not saved. Try again.',
      ],
      BACKUP_TARGET_IS_DATABASE: [
        '不能用备份覆盖当前数据库，请选择其他保存位置。',
        'A backup cannot overwrite the current database. Choose another destination.',
      ],
      BACKUP_PASSWORD_MISMATCH: ['两次备份密码不一致，请重新确认。', 'The backup passwords do not match. Confirm the password again.'],
      BACKUP_AUTH_FAILED: ['备份密码不正确，请重新输入并预览。', 'The backup password is incorrect. Enter it again and preview.'],
      BACKUP_INVALID: ['备份无效或已损坏，请重新选择。', 'The backup is invalid or damaged. Choose another file.'],
      BACKUP_LIMIT_EXCEEDED: ['备份超过可处理的大小或记录数上限。', 'The backup exceeds the supported size or record count.'],
      BACKUP_CONFLICTS_UNRESOLVED: ['仍有未处理的冲突，请先完成选择。', 'Some conflicts are unresolved. Complete the choices first.'],
      CANCELLED: [
        '操作已安全取消。',
        'The operation was cancelled safely.',
      ],
      INVALID_ARGUMENT: [
        '请求状态无效，请重新加载当前列表。',
        'The request state is invalid. Reload the current list.',
      ],
      REQUEST_TOO_LARGE: [
        '密码库记录过多，请先使用搜索缩小范围。',
        'The vault is too large. Narrow it with search.',
      ],
      SESSION_REQUIRED: [
        '数据库会话已结束，请重新连接。',
        'The database session ended. Connect again.',
      ],
      STALE_SESSION: [
        '数据库会话已变化，请重新连接。',
        'The database session changed. Connect again.',
      ],
      REVISION_CONFLICT: [
        '记录已发生变化，列表将自动刷新。',
        'The record changed. The list will refresh.',
      ],
      SECRET_LEASE_EXPIRED: [
        '删除确认已失效，请重新确认。',
        'The delete confirmation expired. Confirm again.',
      ],
      STALE_PAGE: [
        '页面授权已失效，界面将保持锁定。',
        'Page authorization expired. The app remains locked.',
      ],
      INTERNAL_FAILURE: [
        '安全连接未完成，请退出隔离候选后重试。',
        'The secure operation did not complete. Exit and retry.',
      ],
      AUTH_FAILED: [
        '当前数据库密码不正确。',
        'The current database password is incorrect.',
      ],
      CHANGE_KEY_FAILED_UNCHANGED: [
        '修改未完成，原数据库未改变。请稍后重试。',
        'The change did not complete. The original database is unchanged. Try again shortly.',
      ],
      CHANGE_KEY_FAILED_RESTORED: [
        '原数据库已恢复，请使用旧密码重新连接。',
        'The original database was restored. Reconnect with the old password.',
      ],
      CHANGE_KEY_RECOVERY_FAILED: [
        '自动恢复未完成。数据库操作已停止，请退出应用。',
        'Automatic recovery did not complete. Database activity has stopped. Exit the app.',
      ],
      HOTKEY_INVALID: [
        '该快捷键组合无效，请同时按下至少一个修饰键和主键。',
        'That shortcut is invalid. Hold at least one modifier with a main key.',
      ],
      HOTKEY_REGISTER_FAILED: [
        '新快捷键无法注册，原设置和旧快捷键保持不变。',
        'The new shortcut could not be registered. The previous setting and shortcut remain active.',
      ],
      UNSUPPORTED_STATE: [
        'Quick Bar 当前不可用，请检查开关和热键设置。',
        'Quick Bar is unavailable. Check its switch and shortcut setting.',
      ],
    };
    return values[code] || values.INTERNAL_FAILURE;
  }

  function errorText(code) {
    const pair = errorPair(code);
    return fixedText(pair[0], pair[1]);
  }

  const KNOWN_ERROR_CODES = [
    'AUTH_FAILED_RETRY_2', 'AUTH_FAILED_RETRY_1', 'LOCKED_OUT',
    'NOT_FOUND', 'REQUEST_BUSY', 'SELECTION_EXPIRED',
    'BACKUP_TARGET_IS_DATABASE', 'BACKUP_PASSWORD_MISMATCH', 'BACKUP_AUTH_FAILED',
    'BACKUP_INVALID', 'BACKUP_LIMIT_EXCEEDED', 'BACKUP_CONFLICTS_UNRESOLVED',
    'DATABASE_INVALID', 'DATABASE_IO_FAILED', 'DATABASE_LIMIT_EXCEEDED',
    'DATABASE_SPACE_INSUFFICIENT', 'CLIPBOARD_UNAVAILABLE',
    'EMPTY_FIELD',
    'PLATFORM_CONFLICT', 'EMPTY_CHARACTER_SET',
    'GENERATOR_LENGTH_TOO_SHORT', 'PASSWORD_STRENGTH_FAILED',
    'CANCELLED', 'INVALID_ARGUMENT',
    'REQUEST_TOO_LARGE', 'SESSION_REQUIRED', 'STALE_SESSION',
    'REVISION_CONFLICT', 'SECRET_LEASE_EXPIRED', 'STALE_PAGE',
    'INTERNAL_FAILURE', 'AUTH_FAILED', 'CHANGE_KEY_FAILED_UNCHANGED',
    'CHANGE_KEY_FAILED_RESTORED', 'CHANGE_KEY_RECOVERY_FAILED',
    'HOTKEY_INVALID', 'HOTKEY_REGISTER_FAILED', 'UNSUPPORTED_STATE',
  ];

  function knownErrorCodeForText(text) {
    for (const code of KNOWN_ERROR_CODES) {
      if (errorPair(code).includes(text)) return code;
    }
    return '';
  }

  function tagKnownError(element, text) {
    if (!element) return;
    const code = knownErrorCodeForText(text);
    if (code) element.dataset.pdmErrorCode = code;
    else delete element.dataset.pdmErrorCode;
  }

  function clearRuntimeTextMetadata(element) {
    if (!element) return;
    delete element.dataset.pdmErrorCode;
    delete element.dataset.pdmFixedZh;
    delete element.dataset.pdmFixedEn;
    delete element.dataset.pdmI18nKey;
    delete element.dataset.pdmI18nPrefixKey;
    delete element.dataset.pdmI18nSuffixKey;
    delete element.pdmI18nLabel;
  }

  function setRuntimeText(
    element,
    text = '',
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    if (!element) return false;
    clearRuntimeTextMetadata(element);
    if (i18nKey) {
      element.dataset.pdmI18nKey = i18nKey;
      element.textContent = t(i18nKey);
    } else if (fixedZh || fixedEn) {
      element.dataset.pdmFixedZh = fixedZh;
      element.dataset.pdmFixedEn = fixedEn;
      element.textContent = fixedText(fixedZh, fixedEn);
    } else {
      const value = String(text || '');
      element.textContent = value;
      tagKnownError(element, value);
    }
    return Boolean(element.textContent);
  }

  function setRuntimeI18nText(element, key) {
    return setRuntimeText(element, '', '', '', key);
  }

  function setRuntimeCompositeI18nText(
    element,
    prefixKey,
    label,
    suffixKey,
  ) {
    if (!element) return false;
    clearRuntimeTextMetadata(element);
    element.dataset.pdmI18nPrefixKey = prefixKey || '';
    element.dataset.pdmI18nSuffixKey = suffixKey || '';
    element.pdmI18nLabel = String(label || '');
    element.textContent = (
      (prefixKey ? t(prefixKey) : '') +
      element.pdmI18nLabel +
      (suffixKey ? t(suffixKey) : '')
    );
    return Boolean(element.textContent);
  }

  function lastToastMessage() {
    return byId('toast-container')?.lastElementChild?.querySelector(
      'span:last-child',
    ) || null;
  }

  function showErrorToast(code) {
    const text = errorText(code);
    showToast(text, 'error');
    setRuntimeText(lastToastMessage(), text);
    announceOperationText(text);
  }

  function showFixedToast(zh, en, type = 'info') {
    const text = fixedText(zh, en);
    showToast(text, type);
    setRuntimeText(lastToastMessage(), '', zh, en);
    announceOperationText(text);
  }

  function showI18nToast(key, type = 'info') {
    showToast(t(key), type);
    setRuntimeI18nText(lastToastMessage(), key);
    if (type === 'error') announceOperationText(t(key));
    else if (type === 'success') announceOperationStatus(key);
  }

  function clearRuntimeToasts() {
    byId('toast-container')?.querySelectorAll('.toast').forEach(
      (element) => dismissToast(element),
    );
    clearOperationStatus();
  }

  function showCompositeI18nToast(
    prefixKey,
    label,
    suffixKey,
    type = 'info',
  ) {
    const message = (
      (prefixKey ? t(prefixKey) : '') +
      String(label || '') +
      (suffixKey ? t(suffixKey) : '')
    );
    showToast(message, type);
    setRuntimeCompositeI18nText(
      lastToastMessage(),
      prefixKey,
      label,
      suffixKey,
    );
    if (type === 'error') announceOperationStatus('toast.operation.failed');
  }

  function localizedRuntimeTextIssueCount() {
    const selectors = [
      '#connection-feedback',
      '#m4-delete-error',
      '#nf-title-err',
      '#nf-save-err',
      '#kf-current-err',
      '#kf-form-error',
      '#mf-save-err',
      '[id^="mf-"][id$="-err"]',
      '#mf-totp-hint',
      '#mf-totp-remove',
      '#mf-edit-reload',
      '#mf-edit-retry',
      '#kf-confirm-btn[aria-busy="true"]',
      '#toast-container .toast > span:last-child',
    ];
    return [...document.querySelectorAll(selectors.join(','))].filter(
      (element) => {
        if (!String(element.textContent || '').trim()) return false;
        if (element.closest('[data-pdm-settings-error]')) return false;
        return !(
          element.dataset.i18n ||
          element.dataset.pdmErrorCode ||
          element.dataset.pdmFixedZh ||
          element.dataset.pdmI18nKey ||
          element.dataset.pdmI18nPrefixKey
        );
      },
    ).length;
  }

  function formatRelativeTime(unixMs, nowMs = Date.now()) {
    if (!Number.isSafeInteger(unixMs) || unixMs < 0) return '';
    const now = new Date(nowMs);
    const past = new Date(unixMs);
    if (Number.isNaN(past.getTime())) return '';
    const elapsed = Math.max(0, now - past);
    const minutes = Math.floor(elapsed / 60000);
    if (minutes < 1) {
      return fixedText('刚刚', 'Just now');
    }
    if (minutes < 60) {
      return fixedText(`${minutes} 分钟前`, `${minutes}m ago`);
    }
    const day = (value) => Date.UTC(
      value.getFullYear(), value.getMonth(), value.getDate(),
    ) / 86400000;
    const days = day(now) - day(past);
    if (days === 0) return fixedText('今天', 'Today');
    if (days === 1) return fixedText('昨天', 'Yesterday');
    if (days < 7) {
      return fixedText(`${days} 天前`, `${days}d ago`);
    }
    if (days < 30) {
      const weeks = Math.floor(days / 7);
      return fixedText(`${weeks} 周前`, `${weeks}w ago`);
    }
    const months = Math.floor(days / 30);
    return fixedText(`${months} 个月前`, `${months}mo ago`);
  }

  function stopRecentTimeRefresh() {
    window.clearTimeout(runtime.recentTimeTimer);
    runtime.recentTimeTimer = 0;
    runtime.recentTimeGeneration += 1;
  }

  function syncRecentTimeRefresh() {
    stopRecentTimeRefresh();
    const startup = byId('startup-page');
    if (!runtime.ready || runtime.pageUnloading || runtime.state !== 'LOCKED' ||
        !runtime.hostWindowPresentable || document.hidden || !startup ||
        startup.classList.contains('hidden') || startup.classList.contains('minimized')) return;
    const now = Date.now();
    const midnight = new Date(now);
    midnight.setHours(24, 0, 0, 0);
    // 最长一分钟重读墙钟，避免系统改时后一直沿用旧的截止时间。
    let delay = Math.min(60000, midnight.getTime() - now);
    let valid = false;
    startup.querySelectorAll('[data-pdm-relative-time]').forEach((label) => {
      const timestamp = Number(label.dataset.pdmRelativeTime);
      const text = formatRelativeTime(timestamp, now);
      if (label.textContent !== text) label.textContent = text;
      if (!text) return;
      valid = true;
      const elapsed = Math.max(0, now - timestamp);
      if (elapsed < 3600000) {
        delay = Math.min(delay, timestamp + (Math.floor(elapsed / 60000) + 1) * 60000 - now);
      }
    });
    if (!valid) return;
    const generation = runtime.recentTimeGeneration;
    runtime.recentTimeTimer = window.setTimeout(() => {
      if (generation !== runtime.recentTimeGeneration) return;
      syncRecentTimeRefresh();
    }, Math.max(1, delay));
  }

  function setStatusDisconnected() {
    const dot = byId('status-dot');
    const text = byId('status-text');
    if (dot) dot.classList.remove('connected');
    if (text) {
      text.dataset.i18n = 'status.disconnected';
      text.textContent = t('status.disconnected');
    }
  }

  function setStatusConnected(label) {
    const dot = byId('status-dot');
    const text = byId('status-text');
    if (dot) dot.classList.add('connected');
    if (!text) return;
    text.removeAttribute('data-i18n');
    text.replaceChildren(
      document.createTextNode(t('status.connect.prefix')),
    );
    const strong = document.createElement('strong');
    strong.className = 'pdm-inline-1552366efe';
    strong.textContent = label;
    text.append(strong);
  }

  function renderBoundedRecents(values) {
    const list = byId('recent-list');
    if (!list) return;
    list.dataset.pdmM4RecentsReady = 'false';
    list.replaceChildren();
    for (const [index, value] of (Array.isArray(values) ? values.slice(0, 5) : []).entries()) {
      if (
        !value ||
        typeof value.recentDatabaseId !== 'string' ||
        !/^[A-Za-z0-9_-]{16,64}$/.test(value.recentDatabaseId) ||
        typeof value.displayName !== 'string' ||
        typeof value.displayPath !== 'string' ||
        !Number.isSafeInteger(value.lastUsedUnixMs) ||
        !Number.isSafeInteger(value.lockedUntilUnixMs)
      ) {
        continue;
      }
      const entry = Object.freeze({
        recentDatabaseId: value.recentDatabaseId,
        displayName: value.displayName,
        displayPath: value.displayPath,
        lastUsedUnixMs: value.lastUsedUnixMs,
        lockedUntilUnixMs: value.lockedUntilUnixMs,
      });
      const item = document.createElement('li');
      item.className = 'recent-item';
      const select = document.createElement('button');
      select.type = 'button';
      select.className = 'recent-select';
      select.dataset.pdmRecentAction = 'select';
      select.dataset.pdmRecentName = entry.displayName;
      select.dataset.pdmNativeFocusKey = `recent-select:${entry.recentDatabaseId}`;
      select.setAttribute('aria-label', fixedText(
        `选择最近数据库：${entry.displayName}`,
        `Select recent database: ${entry.displayName}`,
      ));
      const icon = document.createElement('div');
      icon.className = 'recent-icon';
      icon.innerHTML = svgIcon('database', 16);
      const info = document.createElement('div');
      info.className = 'recent-info';
      const name = document.createElement('div');
      name.className = 'recent-name';
      name.textContent = entry.displayName;
      const path = document.createElement('div');
      path.className = 'recent-path';
      path.textContent = entry.displayPath;
      const time = document.createElement('div');
      time.className = 'recent-time';
      time.dataset.pdmRelativeTime = String(entry.lastUsedUnixMs);
      time.textContent = formatRelativeTime(entry.lastUsedUnixMs);
      info.append(name, path);
      select.append(icon, info, time);
      select.addEventListener('click', () => {
        if (select.dataset.pdmM4Disabled === 'true') return;
        selectRecentDatabase(entry);
      });
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'recent-remove';
      remove.dataset.pdmRecentAction = 'remove';
      remove.dataset.pdmRecentName = entry.displayName;
      remove.dataset.pdmNativeFocusKey = `recent-remove:${entry.recentDatabaseId}`;
      remove.textContent = fixedText('移除', 'Remove');
      remove.setAttribute('aria-label', fixedText(
        `从最近列表移除：${entry.displayName}`,
        `Remove from recent list: ${entry.displayName}`,
      ));
      remove.addEventListener('click', () => {
        if (remove.dataset.pdmM4Disabled === 'true') return;
        removeRecentDatabase(entry, index);
      });
      item.append(select, remove);
      list.append(item);
    }
    list.dataset.pdmM4RecentsReady = 'true';
    syncRecentTimeRefresh();
  }

  const renderDemoVault = window.renderVault;
  const renderDemoAddPasswordDialog = window.openAddPasswordDialog;
  const renderDemoAddNoteDialog = window.openAddNoteDialog;
  const renderDemoChangeKeyDialog = window.openChangeDbPasswordDialog;
  const openDemoModal = window.openModal;
  const closeDemoModal = window.closeModal;
  const navigateDemoView = window.navigateTo;
  const switchDemoTool = window.switchTool;
  const toggleDemoModalFavorite = window.toggleModalFav;
  const toggleDemoModalPassword = window.toggleModalPwVisibility;
  const toggleDemoCheckPassword = window.toggleCheckPassword;
  const setSharedCanvasLanguage = window.setLang;

  const SETTINGS_KEYS = [
    'autoLockEnabled',
    'autoLockMinutes',
    'clipboardMode',
    'clipboardSeconds',
    'closeBehavior',
    'defaultView',
    'effectiveTheme',
    'generator',
    'language',
    'quickbarEnabled',
    'quickbarHotkey',
    'quickbarIdleSeconds',
    'quickbarRegistration',
    'sidebarText',
    'sortMode',
    'staleDays',
    'startupAutofill',
    'theme',
    'uiFontScale',
  ];
  const GENERATOR_KEYS = [
    'avoidAmbiguous',
    'length',
    'useDigits',
    'useLower',
    'useSymbols',
    'useUpper',
  ];

  function hasExactKeys(value, keys) {
    return (
      value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      JSON.stringify(Object.keys(value).sort()) === JSON.stringify(keys)
    );
  }

  function normalizeSettingsSnapshot(value) {
    if (!hasExactKeys(value, SETTINGS_KEYS)) return null;
    const generator = value.generator;
    if (
      !hasExactKeys(generator, GENERATOR_KEYS) ||
      !Number.isSafeInteger(generator.length) ||
      generator.length < 1 ||
      generator.length > 1024 ||
      typeof generator.useLower !== 'boolean' ||
      typeof generator.useUpper !== 'boolean' ||
      typeof generator.useDigits !== 'boolean' ||
      typeof generator.useSymbols !== 'boolean' ||
      typeof generator.avoidAmbiguous !== 'boolean' ||
      !['LIGHT', 'DARK', 'AUTO'].includes(value.theme) ||
      !['LIGHT', 'DARK'].includes(value.effectiveTheme) ||
      (
        value.theme !== 'AUTO' &&
        value.theme !== value.effectiveTheme
      ) ||
      !['ZH', 'EN'].includes(value.language) ||
      !['90', '100', '110', '125'].includes(value.uiFontScale) ||
      typeof value.startupAutofill !== 'boolean' ||
      !['LIST', 'SPLIT'].includes(value.defaultView) ||
      typeof value.sidebarText !== 'boolean' ||
      !['UPDATED', 'NAME', 'STRENGTH'].includes(value.sortMode) ||
      !['COUNTDOWN', 'MANUAL'].includes(value.clipboardMode) ||
      !Number.isSafeInteger(value.clipboardSeconds) ||
      value.clipboardSeconds < 5 ||
      value.clipboardSeconds > 60 ||
      !['TO_TRAY', 'EXIT'].includes(value.closeBehavior) ||
      typeof value.quickbarEnabled !== 'boolean' ||
      !Number.isSafeInteger(value.quickbarIdleSeconds) ||
      value.quickbarIdleSeconds < 10 ||
      value.quickbarIdleSeconds > 600 ||
      typeof value.quickbarHotkey !== 'string' ||
      value.quickbarHotkey.length < 3 ||
      value.quickbarHotkey.length > 64 ||
      !/^[A-Za-z0-9+`=\[\]\\;',.\/ -]+$/.test(value.quickbarHotkey) ||
      !['DISABLED', 'REGISTERED', 'UNAVAILABLE'].includes(
        value.quickbarRegistration,
      ) ||
      !Number.isSafeInteger(value.staleDays) ||
      value.staleDays < 30 ||
      value.staleDays > 365 ||
      typeof value.autoLockEnabled !== 'boolean' ||
      !Number.isSafeInteger(value.autoLockMinutes) ||
      value.autoLockMinutes < 1 ||
      value.autoLockMinutes > 60
    ) {
      return null;
    }
    return Object.freeze({
      theme: value.theme,
      effectiveTheme: value.effectiveTheme,
      language: value.language,
      uiFontScale: value.uiFontScale,
      startupAutofill: value.startupAutofill,
      defaultView: value.defaultView,
      sidebarText: value.sidebarText,
      sortMode: value.sortMode,
      clipboardMode: value.clipboardMode,
      clipboardSeconds: value.clipboardSeconds,
      closeBehavior: value.closeBehavior,
      quickbarEnabled: value.quickbarEnabled,
      quickbarIdleSeconds: value.quickbarIdleSeconds,
      quickbarHotkey: value.quickbarHotkey,
      quickbarRegistration: value.quickbarRegistration,
      staleDays: value.staleDays,
      autoLockEnabled: value.autoLockEnabled,
      autoLockMinutes: value.autoLockMinutes,
      generator: Object.freeze({
        length: generator.length,
        useLower: generator.useLower,
        useUpper: generator.useUpper,
        useDigits: generator.useDigits,
        useSymbols: generator.useSymbols,
        avoidAmbiguous: generator.avoidAmbiguous,
      }),
    });
  }

  function normalizeSettingsResult(value) {
    if (
      !hasExactKeys(value, ['settings', 'settingsRevision']) ||
      !isRevision(value.settingsRevision)
    ) {
      return null;
    }
    const settings = normalizeSettingsSnapshot(value.settings);
    if (!settings) return null;
    return Object.freeze({
      settingsRevision: value.settingsRevision,
      settings,
    });
  }

  function normalizeHotkeySettingsResult(value) {
    if (
      !hasExactKeys(value, ['settings', 'settingsRevision', 'warning']) ||
      !['NONE', 'KNOWN_CONFLICT'].includes(value.warning)
    ) {
      return null;
    }
    const normalized = normalizeSettingsResult({
      settingsRevision: value.settingsRevision,
      settings: value.settings,
    });
    if (!normalized) return null;
    return Object.freeze({...normalized, warning: value.warning});
  }

  function setProductTopbarTitle() {
    const title = byId('topbar-title');
    if (!title) return;
    const view = String(state.currentNav || 'vault');
    const key = (
      runtime.state !== 'UNLOCKED' && view === 'vault'
        ? 'topbar.title.connect'
        : `topbar.title.${view}`
    );
    title.dataset.i18n = key;
    title.textContent = t(key);
  }

  function setProductCurrentDatabaseInfo() {
    const info = document.querySelector('#page-settings .db-info');
    if (!info) return;
    let notice = byId('upgrade-backup-notice');
    if (runtime.state === 'UNLOCKED' && runtime.upgradeBackupName) {
      if (!notice) {
        notice = document.createElement('p');
        notice.id = 'upgrade-backup-notice';
        notice.className = 'db-info recovery-backup-warning';
        info.after(notice);
      }
      notice.textContent = fixedText(
        `升级前的原样加密副本已保存在数据库同目录：${runtime.upgradeBackupName}。旧版程序请打开此副本。`,
        `An unchanged encrypted copy was saved beside the database before upgrade: ${runtime.upgradeBackupName}. Open this copy with the older app.`,
      );
    } else {
      notice?.remove();
    }
    if (runtime.state === 'UNLOCKED' && runtime.databaseLabel) {
      info.removeAttribute('data-i18n');
      info.textContent = (
        `${runtime.databaseLabel} · ${runtime.vaultTotal} `
        + t('settings.db.current.records')
      );
      return;
    }
    info.dataset.i18n = 'settings.db.current.disconnected';
    info.textContent = t('settings.db.current.disconnected');
  }

  function refreshSettingsFailureToasts() {
    document.querySelectorAll('[data-pdm-settings-error]').forEach(
      (toast) => {
        const text = toast.querySelector('span:last-child');
        if (text) {
          text.textContent = settingsFailureText(
            toast.dataset.pdmSettingsError,
          );
        }
      },
    );
  }

  function refreshProductLocalizedContent() {
    if (runtime.state === 'UNLOCKED') {
      setStatusConnected(runtime.databaseLabel);
    } else {
      setStatusDisconnected();
    }
    setProductTopbarTitle();
    setProductCurrentDatabaseInfo();
    renderClipboardState();
    refreshSettingsFailureToasts();
    document.querySelectorAll('[data-pdm-error-code]').forEach((element) => {
      element.textContent = errorText(element.dataset.pdmErrorCode);
    });
    document.querySelectorAll('[data-pdm-i18n-key]').forEach((element) => {
      element.textContent = t(element.dataset.pdmI18nKey);
    });
    document.querySelectorAll('[data-pdm-i18n-prefix-key]').forEach(
      (element) => {
        element.textContent = (
          (element.dataset.pdmI18nPrefixKey
            ? t(element.dataset.pdmI18nPrefixKey)
            : '') +
          String(element.pdmI18nLabel || '') +
          (element.dataset.pdmI18nSuffixKey
            ? t(element.dataset.pdmI18nSuffixKey)
            : '')
        );
      },
    );
    document.querySelectorAll('[data-pdm-duplicate-group]').forEach(
      (tag) => {
        tag.textContent = (
          t('vault.dup.tag') + tag.dataset.pdmDuplicateGroup
        );
      },
    );
    document.querySelectorAll('[data-pdm-similar-group]').forEach((tag) => {
      tag.textContent = (
        t('vault.similar.tag') + tag.dataset.pdmSimilarGroup
      );
    });
    document.querySelectorAll('[data-pdm-detail-subtitle="true"]').forEach(
      (subtitle) => {
        updateDetailSubtitle(subtitle, subtitle.dataset.strength);
      },
    );
    document.querySelectorAll('[data-pdm-updated-date]').forEach((label) => {
      label.textContent = (
        `${t('vault.detail.updated')} ${label.dataset.pdmUpdatedDate}`
      );
    });
    document.querySelectorAll('[data-pdm-pager-total]').forEach((label) => {
      const total = label.dataset.pdmPagerTotal;
      label.textContent = fixedText(`共 ${total} 条`, `${total} records`);
    });
    document.querySelectorAll('[data-pdm-pager-direction]').forEach(
      (button) => {
        button.textContent = (
          button.dataset.pdmPagerDirection === 'previous'
            ? fixedText('上一页', 'Previous')
            : fixedText('下一页', 'Next')
        );
      },
    );
    document.querySelectorAll('[data-pdm-fixed-zh]').forEach((label) => {
      label.textContent = fixedText(
        label.dataset.pdmFixedZh || '',
        label.dataset.pdmFixedEn || '',
      );
    });
    document.querySelectorAll('[data-pdm-relative-time]').forEach((label) => {
      label.textContent = formatRelativeTime(
        Number(label.dataset.pdmRelativeTime),
      );
    });
    document.querySelectorAll('[data-pdm-recent-action]').forEach((button) => {
      const name = button.dataset.pdmRecentName || '';
      if (button.dataset.pdmRecentAction === 'remove') {
        button.textContent = fixedText('移除', 'Remove');
        button.setAttribute('aria-label', fixedText(
          `从最近列表移除：${name}`,
          `Remove from recent list: ${name}`,
        ));
      } else {
        button.setAttribute('aria-label', fixedText(
          `选择最近数据库：${name}`,
          `Select recent database: ${name}`,
        ));
      }
    });
    syncOpenModalAccessibility();
    if (runtime.editModalActive) {
      updateEditTotpUi();
      updateEditRecoveryUi();
    }
    if (runtime.changeKeyModalActive) {
      checkDbPasswordMatch();
      if (runtime.changeKeyProgressPhase && runtime.pendingChangeKey) {
        onRequestProgress(
          runtime.pageEpoch,
          runtime.sessionEpoch,
          runtime.pendingChangeKey,
          runtime.changeKeyProgressPhase,
          0,
          0,
        );
      }
    }
    refreshCloseBehaviorAccessibility();
    document.querySelectorAll('.note-textarea').forEach((textarea) => {
      if (textarea.id) {
        updateLongTextHint(textarea, `${textarea.id.replace('content', 'scroll-hint')}`);
      }
    });
    const noteContent = byId('nf-content');
    if (noteContent instanceof HTMLTextAreaElement) {
      updateLongTextHint(noteContent, 'nf-content-scroll-hint');
    }
    if (runtime.state === 'UNLOCKED' && state.currentNav === 'security') {
      renderM4Health();
    }
    if (runtime.strengthReport) {
      renderStrengthReport(runtime.strengthReport);
    }
  }

  function projectProductLanguage(language) {
    const lang = language === 'EN' ? 'en' : 'zh';
    runtime.language = language;
    setSharedCanvasLanguage(lang, {skipDynamicRender: true});
    refreshProductLocalizedContent();
    syncRecentTimeRefresh();
    syncProductGlobalSearch();
    if (runtime.state === 'UNLOCKED' && state.currentNav === 'vault') renderM4Vault();
    if (runtime.state === 'UNLOCKED' && state.currentNav === 'notes') renderM4Notes();
    if (runtime.pendingStrength) clearStrengthSurface(false, true);
    if (runtime.settings) projectQuickbarSettings(runtime.settings);
  }

  function projectProductTheme(theme, effectiveTheme) {
    const root = document.documentElement;
    const atomicThemeProjection = root.classList.contains(
      'pdm-native-qt-titlebar',
    );
    if (atomicThemeProjection) root.classList.add('pdm-theme-switching');
    runtime.themePreference = theme;
    runtime.effectiveTheme = effectiveTheme;
    state.theme = theme.toLowerCase();
    document.querySelectorAll('#theme-segment button').forEach((button) => {
      button.classList.toggle(
        'active',
        String(button.dataset.pdmTheme || '').toUpperCase() === theme,
      );
    });
    syncThemeAccessibility();
    const isDark = effectiveTheme === 'DARK';
    root.classList.toggle('light', !isDark);
    const shortcut = byId('theme-btn');
    if (shortcut) shortcut.innerHTML = svgIcon(isDark ? 'moon' : 'sun', 16);
    if (atomicThemeProjection) {
      void root.offsetWidth;
      root.classList.remove('pdm-theme-switching');
    }
  }

  function projectUiFontScale(scale) {
    if (!['90', '100', '110', '125'].includes(scale)) return false;
    runtime.uiFontScale = scale;
    const root = document.documentElement;
    root.dataset.pdmUiFontScale = scale;
    root.style.setProperty('--pdm-ui-font-scale', String(Number(scale) / 100));
    document.querySelectorAll('#ui-font-scale-segment button').forEach(
      (button) => {
        const active = button.dataset.pdmUiFontScale === scale;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      },
    );
    syncBinarySegmentAccessibility(byId('ui-font-scale-segment'));
    return true;
  }

  function refreshCloseBehaviorAccessibility() {
    const segment = byId('tray-close-segment');
    if (!segment || !runtime.settings) return;
    const isTray = runtime.settings.closeBehavior === 'TO_TRAY';
    const label = t(
      isTray
        ? 'settings.tray.close.minimize'
        : 'settings.tray.close.exit',
    );
    segment.title = fixedText(
      `点击切换（当前：${label}）`,
      `Toggle option (current: ${label})`,
    );
    segment.setAttribute(
      'aria-label',
      fixedText(
        `切换选项，当前：${label}`,
        `Toggle option. Current: ${label}`,
      ),
    );
  }

  function projectCloseBehavior(behavior) {
    const segment = byId('tray-close-segment');
    if (!segment) return;
    segment.dataset.pdmCloseBehavior = behavior;
    segment.querySelectorAll('button').forEach((button, index) => {
      button.classList.toggle(
        'active',
        index === (behavior === 'TO_TRAY' ? 0 : 1),
      );
    });
    refreshCloseBehaviorAccessibility();
  }

  function projectAutoLockPolicy(enabled, minutes) {
    state.autoLock.enabled = enabled;
    state.autoLock.timeout = minutes;
    const toggle = byId('autolock-toggle');
    const slider = byId('autolock-slider');
    const number = byId('autolock-num');
    const thresholdRow = slider?.closest('.setting-row');
    toggle?.classList.toggle('on', enabled);
    toggle?.setAttribute('aria-checked', enabled ? 'true' : 'false');
    if (slider) slider.value = String(minutes);
    if (number) number.value = String(minutes);
    thresholdRow?.classList.toggle('is-disabled', !enabled);
  }

  function projectStartupAutofill(enabled) {
    const toggle = byId('autofill-toggle');
    toggle?.classList.toggle('on', enabled);
    toggle?.setAttribute('aria-checked', enabled ? 'true' : 'false');
  }

  function projectDefaultView(view) {
    document.querySelectorAll('#view-default-segment button').forEach(
      (button, index) => {
        button.classList.toggle('active', index === (view === 'LIST' ? 0 : 1));
      },
    );
    syncBinarySegmentAccessibility(byId('view-default-segment'));
  }

  function projectSidebarText(enabled) {
    document.documentElement.classList.toggle('pdm-sidebar-text-hidden', !enabled);
    const toggle = byId('sidebar-text-toggle');
    toggle?.classList.toggle('on', enabled);
    toggle?.setAttribute('aria-checked', enabled ? 'true' : 'false');
  }

  function projectClipboardPolicy(mode, seconds) {
    document.querySelectorAll('#clip-clear-segment button').forEach(
      (button, index) => {
        button.classList.toggle('active', index === (mode === 'COUNTDOWN' ? 0 : 1));
      },
    );
    const slider = byId('clip-slider');
    const number = byId('clip-num');
    if (slider) slider.value = String(seconds);
    if (number) number.value = String(seconds);
    byId('setting-clip-duration')?.classList.toggle('is-disabled', mode !== 'COUNTDOWN');
    syncBinarySegmentAccessibility(byId('clip-clear-segment'));
  }

  function projectStaleThreshold(days) {
    const slider = byId('stale-slider');
    const number = byId('stale-num');
    if (slider) slider.value = String(days);
    if (number) number.value = String(days);
  }

  function projectQuickbarSettings(settings) {
    const toggle = byId('quickbar-toggle');
    const timeoutSlider = byId('quickbar-timeout-slider');
    const timeoutNumber = byId('quickbar-timeout-num');
    const timeoutLabel = byId('quickbar-autohide-label');
    const display = byId('quickbar-hotkey-display');
    const row = byId('quickbar-hotkey-row');
    const topbar = byId('topbar-quickbar-btn');
    state.quickBarHotkey = settings.quickbarHotkey;
    toggle?.classList.toggle('on', settings.quickbarEnabled);
    toggle?.setAttribute(
      'aria-checked',
      settings.quickbarEnabled ? 'true' : 'false',
    );
    toggle?.setAttribute(
      'data-pdm-quickbar-registration',
      settings.quickbarRegistration,
    );
    if (timeoutSlider) {
      timeoutSlider.value = String(settings.quickbarIdleSeconds);
    }
    if (timeoutNumber) {
      timeoutNumber.value = String(settings.quickbarIdleSeconds);
    }
    if (timeoutLabel) {
      timeoutLabel.textContent = fixedText(
        `${settings.quickbarIdleSeconds} 秒无操作自动隐藏`,
        `Auto-hide after ${settings.quickbarIdleSeconds}s of inactivity`,
      );
    }
    if (row) row.dataset.pdmQuickbarRegistration = settings.quickbarRegistration;
    if (display && !runtime.hotkeyRecording) {
      display.textContent = formatHotkeyDisplay(settings.quickbarHotkey);
    }
    if (topbar) {
      topbar.title = (
        !settings.quickbarEnabled
          ? fixedText('Quick Bar 已禁用', 'Quick Bar is disabled')
          : settings.quickbarRegistration === 'UNAVAILABLE'
            ? fixedText(
              '快捷键不可用，仍可点击打开；请在设置中修改',
              'Shortcut unavailable; you can still click to open. Change it in Settings',
            )
            : t('topbar.button.quickbar').replace(
              '{key}',
              formatHotkeyDisplay(settings.quickbarHotkey),
            )
      );
      topbar.dataset.pdmQuickbarRegistration = settings.quickbarRegistration;
    }
  }

  function projectVaultSort(sortMode) {
    if (!['UPDATED', 'NAME', 'STRENGTH'].includes(sortMode)) return;
    runtime.vaultSort = sortMode;
    state.sortMode = sortMode.toLowerCase();
    const option = document.querySelector(
      `#sort-menu .sort-option[data-value="${sortMode.toLowerCase()}"]`,
    );
    document.querySelectorAll('#sort-menu .sort-option').forEach((item) => {
      item.classList.toggle('active', item === option);
      item.setAttribute('aria-selected', String(item === option));
    });
    const label = byId('sort-trigger-label');
    const text = option?.querySelector('span');
    if (label && text) {
      label.textContent = text.textContent || '';
      label.dataset.i18n = text.dataset.i18n || '';
    }
    syncSortDropdownAccessibility('sort-dropdown');
  }

  function projectNoteSort(sortMode) {
    if (!['UPDATED', 'NAME'].includes(sortMode)) return;
    runtime.noteSort = sortMode;
    state.noteSort = sortMode;
    const option = document.querySelector(
      `#note-sort-menu [data-pdm-note-sort="${sortMode}"]`,
    );
    document.querySelectorAll('#note-sort-menu .sort-option').forEach((item) => {
      item.classList.toggle('active', item === option);
      item.setAttribute('aria-selected', String(item === option));
    });
    const label = byId('note-sort-trigger-label');
    const text = option?.querySelector('span');
    if (label && text) {
      label.textContent = text.textContent || '';
      label.dataset.i18n = text.dataset.i18n || '';
    }
    syncSortDropdownAccessibility('note-sort-dropdown');
  }

  function generatorPolicyKey(policy) {
    return JSON.stringify(policy);
  }

  function projectGeneratorPolicy(policy) {
    syncGeneratorLength(policy.length);
    runtime.generatorLastValidLength = policy.length;
    for (const [key, field] of [
      ['lower', 'useLower'],
      ['upper', 'useUpper'],
      ['digit', 'useDigits'],
      ['symbol', 'useSymbols'],
    ]) {
      state.genCharset[key] = policy[field];
      const item = document.querySelector(`.check-item[data-charset="${key}"]`);
      item?.classList.toggle('checked', policy[field]);
      const mark = item?.querySelector('.check-box');
      if (mark) mark.textContent = policy[field] ? '✓' : '';
    }
    state.genAvoidAmbiguous = policy.avoidAmbiguous;
    const avoid = byId('gen-avoid');
    if (avoid instanceof HTMLInputElement) avoid.checked = policy.avoidAmbiguous;
    const avoidItem = byId('gen-avoid-item');
    avoidItem?.classList.toggle('checked', policy.avoidAmbiguous);
    const avoidMark = avoidItem?.querySelector('.check-box');
    if (avoidMark) avoidMark.textContent = policy.avoidAmbiguous ? '✓' : '';
    showGeneratorConfigError('');
  }

  function projectBootstrapSettings(settings) {
    projectUiFontScale(settings.uiFontScale);
    runtime.vaultView = settings.defaultView;
    projectVaultSort(settings.sortMode);
    runtime.clipboardMode = settings.clipboardMode;
    state.viewMode = settings.defaultView.toLowerCase();
    state.autoLock.enabled = settings.autoLockEnabled;
    state.autoLock.timeout = settings.autoLockMinutes;
    runtime.generatorCommittedPolicy = settings.generator;
    runtime.generatorDraftDirty = false;
    projectGeneratorPolicy(settings.generator);
    projectStartupAutofill(settings.startupAutofill);
    projectDefaultView(settings.defaultView);
    projectSidebarText(settings.sidebarText);
    projectClipboardPolicy(settings.clipboardMode, settings.clipboardSeconds);
    const staleSlider = byId('stale-slider');
    const staleNumber = byId('stale-num');
    const autoLockSlider = byId('autolock-slider');
    const autoLockNumber = byId('autolock-num');
    if (staleSlider) staleSlider.value = String(settings.staleDays);
    if (staleNumber) staleNumber.value = String(settings.staleDays);
    if (autoLockSlider) {
      autoLockSlider.value = String(settings.autoLockMinutes);
    }
    if (autoLockNumber) {
      autoLockNumber.value = String(settings.autoLockMinutes);
    }
    projectAutoLockPolicy(
      settings.autoLockEnabled,
      settings.autoLockMinutes,
    );
    projectQuickbarSettings(settings);
  }

  function applySettingsProjection(settingsRevision, settings, source) {
    if (
      source !== 'BOOTSTRAP' &&
      settingsRevision === runtime.settingsRevision &&
      runtime.settings &&
      JSON.stringify(settings) === JSON.stringify(runtime.settings)
    ) {
      runtime.settingsProjectionSource = `${source}_NOOP`;
      return false;
    }
    const languageChanged = settings.language !== runtime.language;
    const uiFontScaleChanged = settings.uiFontScale !== runtime.uiFontScale;
    const startupAutofillChanged = !runtime.settings || (
      settings.startupAutofill !== runtime.settings.startupAutofill
    );
    const defaultViewChanged = !runtime.settings || (
      settings.defaultView !== runtime.settings.defaultView
    );
    const sidebarTextChanged = !runtime.settings || (
      settings.sidebarText !== runtime.settings.sidebarText
    );
    const clipboardPolicyChanged = !runtime.settings || (
      settings.clipboardMode !== runtime.settings.clipboardMode ||
      settings.clipboardSeconds !== runtime.settings.clipboardSeconds
    );
    const themeChanged = (
      settings.theme !== runtime.themePreference ||
      settings.effectiveTheme !== runtime.effectiveTheme
    );
    const closeBehaviorChanged = (
      !runtime.settings ||
      settings.closeBehavior !== runtime.settings.closeBehavior
    );
    const sortChanged = !runtime.settings || (
      settings.sortMode !== runtime.settings.sortMode
    );
    const autoLockChanged = (
      !runtime.settings ||
      settings.autoLockEnabled !== runtime.settings.autoLockEnabled ||
      settings.autoLockMinutes !== runtime.settings.autoLockMinutes
    );
    const staleDaysChanged = !runtime.settings || settings.staleDays !== runtime.settings.staleDays;
    const quickbarChanged = (
      !runtime.settings ||
      settings.quickbarEnabled !== runtime.settings.quickbarEnabled ||
      settings.quickbarIdleSeconds !== runtime.settings.quickbarIdleSeconds ||
      settings.quickbarHotkey !== runtime.settings.quickbarHotkey ||
      settings.quickbarRegistration !== runtime.settings.quickbarRegistration
    );
    const generatorChanged = (
      !runtime.settings ||
      generatorPolicyKey(settings.generator) !==
        generatorPolicyKey(runtime.settings.generator)
    );
    runtime.settingsRevision = settingsRevision;
    runtime.settings = settings;
    if (source === 'BOOTSTRAP') projectBootstrapSettings(settings);
    if (
      source !== 'BOOTSTRAP' &&
      generatorChanged &&
      !runtime.generatorDraftDirty &&
      !runtime.pendingGeneratorDefaults
    ) {
      runtime.generatorCommittedPolicy = settings.generator;
      projectGeneratorPolicy(settings.generator);
    }
    if (source !== 'BOOTSTRAP' && staleDaysChanged) {
      invalidateHealthRequests();
      if (runtime.state === 'UNLOCKED' && state.currentNav === 'security') {
        requestHealthSummary();
      }
    }
    if (
      source !== 'BOOTSTRAP' &&
      sortChanged &&
      !runtime.pendingSort
    ) {
      projectVaultSort(settings.sortMode);
      resetVaultPagePosition();
      if (runtime.state === 'UNLOCKED') queueVaultReload();
    }
    if (source === 'BOOTSTRAP' || languageChanged) {
      projectProductLanguage(settings.language);
    }
    if (source !== 'BOOTSTRAP' && uiFontScaleChanged) {
      projectUiFontScale(settings.uiFontScale);
    }
    if (source === 'BOOTSTRAP' || (
      startupAutofillChanged && !runtime.pendingStartupAutofill
    )) projectStartupAutofill(settings.startupAutofill);
    if (source === 'BOOTSTRAP' || (
      defaultViewChanged && !runtime.pendingDefaultView
    )) projectDefaultView(settings.defaultView);
    if (source === 'BOOTSTRAP' || (
      sidebarTextChanged && !runtime.pendingSidebarText
    )) projectSidebarText(settings.sidebarText);
    if (source === 'BOOTSTRAP' || (
      clipboardPolicyChanged && !runtime.pendingClipboardPolicy
    )) projectClipboardPolicy(settings.clipboardMode, settings.clipboardSeconds);
    if (source === 'BOOTSTRAP' || themeChanged) {
      projectProductTheme(settings.theme, settings.effectiveTheme);
    }
    if (
      source === 'BOOTSTRAP' ||
      (closeBehaviorChanged && !runtime.pendingClose)
    ) {
      projectCloseBehavior(settings.closeBehavior);
    }
    if (
      source === 'BOOTSTRAP' ||
      (autoLockChanged && !runtime.pendingAutoLock)
    ) {
      projectAutoLockPolicy(
        settings.autoLockEnabled,
        settings.autoLockMinutes,
      );
    }
    if (source === 'BOOTSTRAP' || (staleDaysChanged && !runtime.pendingStaleThreshold)) {
      projectStaleThreshold(settings.staleDays);
    }
    if (
      source === 'BOOTSTRAP' ||
      (
        (quickbarChanged || languageChanged) &&
        !runtime.pendingQuickbarEnabled &&
        !runtime.pendingQuickbarHotkey
      )
    ) {
      projectQuickbarSettings(settings);
    }
    runtime.settingsProjectionSource = source;
    runtime.settingsProjectionCount += 1;
    refreshControls();
    return true;
  }

  function settingsCommitKey(settingsRevision, settings) {
    const {
      effectiveTheme: _nativeEffectiveTheme,
      ...committedSettings
    } = settings;
    return `${settingsRevision}:${JSON.stringify(committedSettings)}`;
  }

  function rememberSettingsSignal(settingsRevision, settings) {
    const key = settingsCommitKey(settingsRevision, settings);
    if (!runtime.projectedSettingsSignals.includes(key)) {
      runtime.projectedSettingsSignals.push(key);
      if (runtime.projectedSettingsSignals.length > 32) {
        runtime.projectedSettingsSignals.splice(
          0,
          runtime.projectedSettingsSignals.length - 32,
        );
      }
    }
  }

  function hasProjectedSettingsSignal(settingsRevision, settings) {
    return runtime.projectedSettingsSignals.includes(
      settingsCommitKey(settingsRevision, settings),
    );
  }

  function settingsFailureText(code) {
    if (code === 'REQUEST_BUSY') return errorText(code);
    if (
      code === 'HOTKEY_INVALID' ||
      code === 'HOTKEY_REGISTER_FAILED'
    ) {
      return errorText(code);
    }
    if (code === 'STALE_PAGE' || code === 'INVALID_ARGUMENT') {
      return errorText(code);
    }
    return fixedText(
      '设置未保存，请重试；若重复失败，请重启应用确认设置。',
      'The setting was not saved. Try again; if it keeps failing, restart the app to confirm the setting.',
    );
  }

  function showSettingsFailure(code) {
    showToast(settingsFailureText(code), 'error');
    const toast = byId('toast-container')?.lastElementChild;
    if (toast) toast.dataset.pdmSettingsError = String(code || 'INTERNAL_FAILURE');
  }

  function clearPendingTheme() {
    runtime.pendingTheme = '';
    runtime.pendingThemeValue = '';
    runtime.pendingThemeChanged = false;
    runtime.pendingThemeRevision = '';
    runtime.pendingThemeSettings = null;
  }

  function clearPendingLanguage() {
    runtime.pendingLanguage = '';
    runtime.pendingLanguageValue = '';
    runtime.pendingLanguageRevision = '';
    runtime.pendingLanguageSettings = null;
  }

  function clearPendingUiFontScale() {
    runtime.pendingUiFontScale = '';
    runtime.pendingUiFontScaleValue = '';
    runtime.pendingUiFontScaleRevision = '';
    runtime.pendingUiFontScaleSettings = null;
  }

  function clearPendingStartupAutofill() {
    runtime.pendingStartupAutofill = '';
    runtime.pendingStartupAutofillValue = false;
    runtime.pendingStartupAutofillRevision = '';
    runtime.pendingStartupAutofillSettings = null;
  }

  function clearPendingDefaultView() {
    runtime.pendingDefaultView = '';
    runtime.pendingDefaultViewValue = '';
    runtime.pendingDefaultViewRevision = '';
    runtime.pendingDefaultViewSettings = null;
  }

  function clearPendingSidebarText() {
    runtime.pendingSidebarText = '';
    runtime.pendingSidebarTextValue = false;
    runtime.pendingSidebarTextRevision = '';
    runtime.pendingSidebarTextSettings = null;
  }

  function clearPendingClipboardPolicy() {
    runtime.pendingClipboardPolicy = '';
    runtime.pendingClipboardMode = '';
    runtime.pendingClipboardSeconds = 30;
    runtime.pendingClipboardRevision = '';
    runtime.pendingClipboardSettings = null;
  }

  function clearPendingSort() {
    runtime.pendingSort = '';
    runtime.pendingSortValue = '';
    runtime.pendingSortRevision = '';
    runtime.pendingSortSettings = null;
  }

  function clearPendingClose() {
    runtime.pendingClose = '';
    runtime.pendingCloseValue = '';
    runtime.pendingCloseRevision = '';
    runtime.pendingCloseSettings = null;
  }

  function clearPendingAutoLock() {
    runtime.pendingAutoLock = '';
    runtime.pendingAutoLockEnabled = false;
    runtime.pendingAutoLockMinutes = 5;
    runtime.pendingAutoLockRevision = '';
    runtime.pendingAutoLockSettings = null;
  }

  function clearPendingGeneratorDefaults() {
    runtime.pendingGeneratorDefaults = '';
    runtime.pendingGeneratorPolicy = null;
    runtime.pendingGeneratorRevision = '';
    runtime.pendingGeneratorSettings = null;
  }

  function clearPendingQuickbarEnabled() {
    runtime.pendingQuickbarEnabled = '';
    runtime.pendingQuickbarEnabledValue = false;
    runtime.pendingQuickbarIdleSeconds = 30;
    runtime.pendingQuickbarEnabledRevision = '';
    runtime.pendingQuickbarEnabledSettings = null;
  }

  function clearPendingQuickbarHotkey() {
    runtime.pendingQuickbarHotkey = '';
    runtime.pendingQuickbarHotkeyValue = '';
    runtime.pendingQuickbarHotkeyRevision = '';
    runtime.pendingQuickbarHotkeySettings = null;
    runtime.pendingQuickbarHotkeyWarning = 'NONE';
  }

  function settingsResultMatches(
    settingsRevision,
    settings,
    expectedRevision,
    expectedSettings,
  ) {
    return (
      Boolean(expectedRevision) &&
      Boolean(expectedSettings) &&
      settingsCommitKey(settingsRevision, settings) ===
        settingsCommitKey(expectedRevision, expectedSettings)
    );
  }

  function finishPendingThemeProjection() {
    const requestedTheme = runtime.pendingThemeValue;
    const showSuccess = runtime.pendingThemeChanged;
    clearPendingTheme();
    if (showSuccess) {
      const key = (
        requestedTheme === 'AUTO'
          ? 'toast.theme.auto'
          : requestedTheme === 'DARK'
            ? 'toast.theme.dark'
            : 'toast.theme.light'
      );
      showI18nToast(key, 'info');
      runtime.themeSuccessToastCount += 1;
    }
    refreshControls();
  }

  function finishPendingLanguageProjection() {
    clearPendingLanguage();
    refreshControls();
  }

  function finishPendingUiFontScaleProjection() {
    clearPendingUiFontScale();
    refreshControls();
  }

  function finishPendingStartupAutofillProjection() {
    const settings = runtime.pendingStartupAutofillSettings;
    if (settings) projectStartupAutofill(settings.startupAutofill);
    clearPendingStartupAutofill();
    refreshControls();
  }

  function finishPendingDefaultViewProjection() {
    const settings = runtime.pendingDefaultViewSettings;
    if (settings) projectDefaultView(settings.defaultView);
    clearPendingDefaultView();
    refreshControls();
  }

  function finishPendingSidebarTextProjection() {
    const settings = runtime.pendingSidebarTextSettings;
    if (settings) projectSidebarText(settings.sidebarText);
    clearPendingSidebarText();
    refreshControls();
  }

  function finishPendingClipboardPolicyProjection() {
    const settings = runtime.pendingClipboardSettings;
    if (settings) projectClipboardPolicy(settings.clipboardMode, settings.clipboardSeconds);
    clearPendingClipboardPolicy();
    refreshControls();
  }

  function finishPendingSortProjection() {
    const settings = runtime.pendingSortSettings;
    if (settings) {
      projectVaultSort(settings.sortMode);
      resetVaultPagePosition();
      if (runtime.state === 'UNLOCKED') queueVaultReload();
    }
    clearPendingSort();
    refreshControls();
  }

  function finishPendingCloseProjection() {
    const settings = runtime.pendingCloseSettings;
    if (settings) projectCloseBehavior(settings.closeBehavior);
    clearPendingClose();
    refreshControls();
  }

  function finishPendingAutoLockProjection() {
    const settings = runtime.pendingAutoLockSettings;
    if (settings) {
      projectAutoLockPolicy(
        settings.autoLockEnabled,
        settings.autoLockMinutes,
      );
    }
    clearPendingAutoLock();
    refreshControls();
  }

  function finishPendingGeneratorProjection() {
    const saved = runtime.pendingGeneratorSettings?.generator;
    if (!saved) return;
    runtime.generatorCommittedPolicy = saved;
    const queued = runtime.queuedGeneratorPolicy;
    runtime.queuedGeneratorPolicy = null;
    clearPendingGeneratorDefaults();
    const current = generatorPolicy();
    if (queued && generatorPolicyKey(queued) !== generatorPolicyKey(saved)) {
      submitGeneratorDefaults(queued);
      return;
    }
    if (generatorPolicyKey(current) === generatorPolicyKey(saved)) {
      runtime.generatorDraftDirty = false;
      projectGeneratorPolicy(saved);
    }
    if (
      runtime.generatorGenerateAfterSaveKey &&
      runtime.generatorGenerateAfterSaveKey === generatorPolicyKey(saved) &&
      generatorPolicyKey(current) === generatorPolicyKey(saved)
    ) {
      runtime.generatorGenerateAfterSaveKey = '';
      requestGeneratedPassword('tool');
    }
    refreshControls();
  }

  function finishPendingQuickbarEnabledProjection() {
    const settings = runtime.pendingQuickbarEnabledSettings;
    if (settings) projectQuickbarSettings(settings);
    clearPendingQuickbarEnabled();
    refreshControls();
  }

  function finishPendingQuickbarHotkeyProjection() {
    const settings = runtime.pendingQuickbarHotkeySettings;
    const warning = runtime.pendingQuickbarHotkeyWarning;
    if (settings) projectQuickbarSettings(settings);
    clearPendingQuickbarHotkey();
    if (warning === 'KNOWN_CONFLICT') {
      showFixedToast(
        '该快捷键与常见系统或软件快捷键冲突；已保存，但可能无法稳定使用。',
        'This shortcut conflicts with a common system or app shortcut. It was saved, but may not work reliably.',
        'warning',
      );
    }
    refreshControls();
  }

  function settleProjectedSettingsWaiters(settingsRevision, settings) {
    if (
      runtime.pendingTheme &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingThemeRevision,
        runtime.pendingThemeSettings,
      )
    ) {
      finishPendingThemeProjection();
    }
    if (
      runtime.pendingLanguage &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingLanguageRevision,
        runtime.pendingLanguageSettings,
      )
    ) {
      finishPendingLanguageProjection();
    }
    if (
      runtime.pendingUiFontScale &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingUiFontScaleRevision,
        runtime.pendingUiFontScaleSettings,
      )
    ) {
      finishPendingUiFontScaleProjection();
    }
    if (
      runtime.pendingStartupAutofill &&
      settingsResultMatches(settingsRevision, settings, runtime.pendingStartupAutofillRevision, runtime.pendingStartupAutofillSettings)
    ) finishPendingStartupAutofillProjection();
    if (
      runtime.pendingDefaultView &&
      settingsResultMatches(settingsRevision, settings, runtime.pendingDefaultViewRevision, runtime.pendingDefaultViewSettings)
    ) finishPendingDefaultViewProjection();
    if (
      runtime.pendingSidebarText &&
      settingsResultMatches(settingsRevision, settings, runtime.pendingSidebarTextRevision, runtime.pendingSidebarTextSettings)
    ) finishPendingSidebarTextProjection();
    if (
      runtime.pendingClipboardPolicy &&
      settingsResultMatches(settingsRevision, settings, runtime.pendingClipboardRevision, runtime.pendingClipboardSettings)
    ) finishPendingClipboardPolicyProjection();
    if (
      runtime.pendingSort &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingSortRevision,
        runtime.pendingSortSettings,
      )
    ) {
      finishPendingSortProjection();
    }
    if (
      runtime.pendingClose &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingCloseRevision,
        runtime.pendingCloseSettings,
      )
    ) {
      finishPendingCloseProjection();
    }
    if (
      runtime.pendingAutoLock &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingAutoLockRevision,
        runtime.pendingAutoLockSettings,
      )
    ) {
      finishPendingAutoLockProjection();
    }
    if (
      runtime.pendingQuickbarEnabled &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingQuickbarEnabledRevision,
        runtime.pendingQuickbarEnabledSettings,
      )
    ) {
      finishPendingQuickbarEnabledProjection();
    }
    if (
      runtime.pendingQuickbarHotkey &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingQuickbarHotkeyRevision,
        runtime.pendingQuickbarHotkeySettings,
      )
    ) {
      finishPendingQuickbarHotkeyProjection();
    }
    if (
      runtime.pendingGeneratorDefaults &&
      settingsResultMatches(
        settingsRevision,
        settings,
        runtime.pendingGeneratorRevision,
        runtime.pendingGeneratorSettings,
      )
    ) {
      finishPendingGeneratorProjection();
    }
  }

  function requestProductTheme(value) {
    const theme = String(value || '').toUpperCase();
    if (
      !['LIGHT', 'DARK', 'AUTO'].includes(theme) ||
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0 ||
      runtime.pendingTheme ||
      theme === runtime.themePreference
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingTheme = id;
    runtime.pendingThemeValue = theme;
    runtime.pendingThemeChanged = theme !== runtime.themePreference;
    refreshControls();
    runtime.bridge.setThemeV1(
      id,
      runtime.pageEpoch,
      theme,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingTheme === id) {
            clearPendingTheme();
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestProductLanguage(value = '') {
    if (
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0 ||
      runtime.pendingLanguage
    ) {
      return;
    }
    const requested = String(value || '').toUpperCase();
    const language = (
      ['ZH', 'EN'].includes(requested)
        ? requested
        : (runtime.language === 'ZH' ? 'EN' : 'ZH')
    );
    if (language === runtime.language) return;
    const id = requestId();
    runtime.pendingLanguage = id;
    runtime.pendingLanguageValue = language;
    refreshControls();
    runtime.bridge.setLanguageV1(
      id,
      runtime.pageEpoch,
      language,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingLanguage === id) {
            clearPendingLanguage();
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestProductUiFontScale(value) {
    const scale = String(value || '');
    if (
      !['90', '100', '110', '125'].includes(scale) ||
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0 ||
      runtime.pendingUiFontScale ||
      scale === runtime.uiFontScale
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingUiFontScale = id;
    runtime.pendingUiFontScaleValue = scale;
    refreshControls();
    runtime.bridge.setUiFontScaleV1(
      id,
      runtime.pageEpoch,
      scale,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingUiFontScale === id) {
            clearPendingUiFontScale();
            projectUiFontScale(runtime.settings?.uiFontScale || '100');
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestProductStartupAutofill() {
    if (
      !runtime.bridge || !runtime.ready || runtime.state !== 'UNLOCKED' ||
      runtime.pageEpoch <= 0 || runtime.sessionEpoch <= 0 || !runtime.settings ||
      runtime.pendingStartupAutofill
    ) return;
    const enabled = !runtime.settings.startupAutofill;
    projectStartupAutofill(runtime.settings.startupAutofill);
    const id = requestId();
    runtime.pendingStartupAutofill = id;
    runtime.pendingStartupAutofillValue = enabled;
    refreshControls();
    runtime.bridge.setStartupAutofillV1(
      id, runtime.pageEpoch, runtime.sessionEpoch, enabled, (ack) => {
        if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingStartupAutofill === id) {
          clearPendingStartupAutofill();
          projectStartupAutofill(runtime.settings.startupAutofill);
          showSettingsFailure(ack?.errorCode || 'INTERNAL_FAILURE');
          refreshControls();
        }
      },
    );
  }

  function requestProductDefaultView(value = '') {
    if (
      !runtime.bridge || !runtime.ready || runtime.state !== 'UNLOCKED' ||
      runtime.pageEpoch <= 0 || runtime.sessionEpoch <= 0 || !runtime.settings ||
      runtime.pendingDefaultView
    ) return;
    const requested = String(value || '').toUpperCase();
    const view = ['LIST', 'SPLIT'].includes(requested) ? requested : (
      runtime.settings.defaultView === 'LIST' ? 'SPLIT' : 'LIST'
    );
    if (view === runtime.settings.defaultView) return;
    projectDefaultView(runtime.settings.defaultView);
    const id = requestId();
    runtime.pendingDefaultView = id;
    runtime.pendingDefaultViewValue = view;
    refreshControls();
    runtime.bridge.setDefaultViewV1(
      id, runtime.pageEpoch, runtime.sessionEpoch, view, (ack) => {
        if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingDefaultView === id) {
          clearPendingDefaultView();
          projectDefaultView(runtime.settings.defaultView);
          showSettingsFailure(ack?.errorCode || 'INTERNAL_FAILURE');
          refreshControls();
        }
      },
    );
  }

  function requestProductSidebarText() {
    if (
      !runtime.bridge || !runtime.ready ||
      !['LOCKED', 'UNLOCKED'].includes(runtime.state) ||
      runtime.pageEpoch <= 0 || !runtime.settings ||
      runtime.pendingSidebarText
    ) return;
    const enabled = !runtime.settings.sidebarText;
    projectSidebarText(runtime.settings.sidebarText);
    const id = requestId();
    runtime.pendingSidebarText = id;
    runtime.pendingSidebarTextValue = enabled;
    refreshControls();
    runtime.bridge.setSidebarTextV1(
      id, runtime.pageEpoch, enabled, (ack) => {
        if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingSidebarText === id) {
          clearPendingSidebarText();
          projectSidebarText(runtime.settings.sidebarText);
          showSettingsFailure(ack?.errorCode || 'INTERNAL_FAILURE');
          refreshControls();
        }
      },
    );
  }

  function requestProductClipboardPolicy(mode = '', seconds = 0) {
    if (
      !runtime.bridge || !runtime.ready || runtime.state !== 'UNLOCKED' ||
      runtime.pageEpoch <= 0 || runtime.sessionEpoch <= 0 || !runtime.settings ||
      runtime.pendingClipboardPolicy
    ) return;
    const requestedMode = String(mode || '').toUpperCase();
    const nextMode = ['COUNTDOWN', 'MANUAL'].includes(requestedMode) ? requestedMode : (
      runtime.settings.clipboardMode === 'COUNTDOWN' ? 'MANUAL' : 'COUNTDOWN'
    );
    const parsed = Number.parseInt(String(seconds || runtime.settings.clipboardSeconds), 10);
    const nextSeconds = Number.isSafeInteger(parsed) ? Math.max(5, Math.min(60, parsed)) : runtime.settings.clipboardSeconds;
    if (nextMode === runtime.settings.clipboardMode && nextSeconds === runtime.settings.clipboardSeconds) return;
    projectClipboardPolicy(runtime.settings.clipboardMode, runtime.settings.clipboardSeconds);
    const id = requestId();
    runtime.pendingClipboardPolicy = id;
    runtime.pendingClipboardMode = nextMode;
    runtime.pendingClipboardSeconds = nextSeconds;
    refreshControls();
    runtime.bridge.setClipboardPolicyV1(
      id, runtime.pageEpoch, runtime.sessionEpoch, nextMode, nextSeconds, (ack) => {
        if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingClipboardPolicy === id) {
          clearPendingClipboardPolicy();
          projectClipboardPolicy(runtime.settings.clipboardMode, runtime.settings.clipboardSeconds);
          showSettingsFailure(ack?.errorCode || 'INTERNAL_FAILURE');
          refreshControls();
        }
      },
    );
  }

  function requestProductSort(value) {
    const sortMode = String(value || '').toUpperCase();
    if (
      !['UPDATED', 'NAME', 'STRENGTH'].includes(sortMode) ||
      !runtime.bridge ||
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      runtime.pageEpoch <= 0 ||
      runtime.sessionEpoch <= 0 ||
      runtime.pendingSort ||
      sortMode === runtime.vaultSort
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingSort = id;
    runtime.pendingSortValue = sortMode;
    refreshControls();
    runtime.bridge.setSortModeV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      sortMode,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingSort === id) {
            clearPendingSort();
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function selectNoteSort(value) {
    const sortMode = String(value || '').toUpperCase();
    if (
      !['UPDATED', 'NAME'].includes(sortMode) ||
      runtime.state !== 'UNLOCKED' ||
      noteWritePending() ||
      noteDraftDirty()
    ) {
      if (noteDraftDirty()) showUnsavedNoteWarning();
      return;
    }
    closeSortDropdown('note-sort-dropdown', true);
    if (sortMode === runtime.noteSort) return;
    projectNoteSort(sortMode);
    resetNotePagePosition();
    requestNotePage();
  }

  function requestProductCloseBehavior(value = '') {
    if (
      !runtime.bridge ||
      !runtime.ready ||
      runtime.state !== 'UNLOCKED' ||
      runtime.pageEpoch <= 0 ||
      runtime.sessionEpoch <= 0 ||
      !runtime.settings ||
      runtime.pendingClose
    ) {
      return;
    }
    const requested = String(value || '').toUpperCase();
    const behavior = (
      ['TO_TRAY', 'EXIT'].includes(requested)
        ? requested
        : (
          runtime.settings.closeBehavior === 'TO_TRAY'
            ? 'EXIT'
            : 'TO_TRAY'
        )
    );
    if (behavior === runtime.settings.closeBehavior) return;
    const id = requestId();
    runtime.pendingClose = id;
    runtime.pendingCloseValue = behavior;
    refreshControls();
    runtime.bridge.setCloseBehaviorV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      behavior,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingClose === id) {
            clearPendingClose();
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestProductAutoLock(enabled, minutes) {
    if (
      !runtime.bridge ||
      !runtime.ready ||
      runtime.state !== 'UNLOCKED' ||
      runtime.pageEpoch <= 0 ||
      runtime.sessionEpoch <= 0 ||
      !runtime.settings ||
      runtime.pendingAutoLock ||
      typeof enabled !== 'boolean' ||
      !Number.isSafeInteger(minutes) ||
      minutes < 1 ||
      minutes > 60
    ) {
      if (runtime.settings) {
        projectAutoLockPolicy(
          runtime.settings.autoLockEnabled,
          runtime.settings.autoLockMinutes,
        );
      }
      return;
    }
    if (
      enabled === runtime.settings.autoLockEnabled &&
      minutes === runtime.settings.autoLockMinutes
    ) {
      projectAutoLockPolicy(enabled, minutes);
      return;
    }
    // Native persistence is authoritative.  Undo the input element's own
    // eager browser paint until C47 and S02 prove the complete policy.
    projectAutoLockPolicy(
      runtime.settings.autoLockEnabled,
      runtime.settings.autoLockMinutes,
    );
    const id = requestId();
    runtime.pendingAutoLock = id;
    runtime.pendingAutoLockEnabled = enabled;
    runtime.pendingAutoLockMinutes = minutes;
    refreshControls();
    runtime.bridge.setAutoLockPolicyV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      enabled,
      minutes,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingAutoLock === id) {
            clearPendingAutoLock();
            if (runtime.settings) {
              projectAutoLockPolicy(
                runtime.settings.autoLockEnabled,
                runtime.settings.autoLockMinutes,
              );
            }
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestProductAutoLockToggle() {
    if (!runtime.settings) return;
    requestProductAutoLock(
      !runtime.settings.autoLockEnabled,
      runtime.settings.autoLockMinutes,
    );
  }

  function requestProductAutoLockMinutes(value) {
    if (!runtime.settings) return;
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isSafeInteger(parsed)) {
      projectAutoLockPolicy(
        runtime.settings.autoLockEnabled,
        runtime.settings.autoLockMinutes,
      );
      return;
    }
    requestProductAutoLock(
      runtime.settings.autoLockEnabled,
      Math.max(1, Math.min(60, parsed)),
    );
  }

  function requestStaleThreshold(value) {
    const rawDays = String(value).trim();
    const days = /^\d+$/.test(rawDays) ? Number(rawDays) : Number.NaN;
    if (!runtime.bridge || !runtime.ready || runtime.state !== 'UNLOCKED' || !runtime.settings ||
        runtime.pendingStaleThreshold || !Number.isSafeInteger(days) || days < 30 || days > 365) {
      if (runtime.settings) projectStaleThreshold(runtime.settings.staleDays);
      return;
    }
    if (days === runtime.settings.staleDays) {
      projectStaleThreshold(days);
      return;
    }
    projectStaleThreshold(runtime.settings.staleDays);
    const id = requestId();
    runtime.pendingStaleThreshold = id;
    runtime.pendingStaleDays = days;
    refreshControls();
    runtime.bridge.setStaleThresholdV1(id, runtime.pageEpoch, runtime.sessionEpoch, days, (ack) => {
      if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingStaleThreshold === id) {
        runtime.pendingStaleThreshold = '';
        runtime.pendingStaleDays = 0;
        projectStaleThreshold(runtime.settings.staleDays);
        showSettingsFailure(ack?.errorCode || 'INTERNAL_FAILURE');
        refreshControls();
      }
    });
  }

  function onStaleThresholdSet(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingStaleThreshold || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    const requestedDays = runtime.pendingStaleDays;
    runtime.pendingStaleThreshold = '';
    runtime.pendingStaleDays = 0;
    if (errorCode !== 'OK') {
      projectStaleThreshold(runtime.settings?.staleDays || 180);
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.staleDays !== requestedDays) {
      projectStaleThreshold(runtime.settings?.staleDays || 180);
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    applySettingsProjection(normalized.settingsRevision, normalized.settings, 'C46');
    if (state.currentNav === 'security') requestHealth();
  }

  function requestQuickbarOpen() {
    if (
      !runtime.bridge ||
      !runtime.ready ||
      runtime.state !== 'UNLOCKED' ||
      runtime.pageEpoch <= 0 ||
      runtime.sessionEpoch <= 0 ||
      !runtime.settings?.quickbarEnabled ||
      runtime.pendingQuickbarOpen
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingQuickbarOpen = id;
    refreshControls();
    runtime.bridge.openQuickbarV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingQuickbarOpen === id) {
            runtime.pendingQuickbarOpen = '';
            if (ack?.errorCode) showErrorToast(ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestQuickbarPolicy(enabled, idleSeconds) {
    if (
      !runtime.bridge ||
      !runtime.ready ||
      runtime.state !== 'UNLOCKED' ||
      runtime.pageEpoch <= 0 ||
      runtime.sessionEpoch <= 0 ||
      !runtime.settings ||
      runtime.pendingQuickbarEnabled ||
      runtime.pendingQuickbarHotkey ||
      typeof enabled !== 'boolean' ||
      !Number.isSafeInteger(idleSeconds) ||
      idleSeconds < 10 ||
      idleSeconds > 600
    ) {
      if (runtime.settings) projectQuickbarSettings(runtime.settings);
      return;
    }
    if (
      enabled === runtime.settings.quickbarEnabled &&
      idleSeconds === runtime.settings.quickbarIdleSeconds
    ) {
      projectQuickbarSettings(runtime.settings);
      return;
    }
    projectQuickbarSettings(runtime.settings);
    const id = requestId();
    runtime.pendingQuickbarEnabled = id;
    runtime.pendingQuickbarEnabledValue = enabled;
    runtime.pendingQuickbarIdleSeconds = idleSeconds;
    refreshControls();
    runtime.bridge.setQuickbarEnabledV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      enabled,
      idleSeconds,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingQuickbarEnabled === id) {
            clearPendingQuickbarEnabled();
            projectQuickbarSettings(runtime.settings);
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestQuickbarEnabled() {
    if (!runtime.settings) return;
    requestQuickbarPolicy(
      !runtime.settings.quickbarEnabled,
      runtime.settings.quickbarIdleSeconds,
    );
  }

  function requestQuickbarIdleSeconds(value) {
    if (!runtime.settings) return;
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isSafeInteger(parsed)) {
      projectQuickbarSettings(runtime.settings);
      return;
    }
    requestQuickbarPolicy(
      runtime.settings.quickbarEnabled,
      Math.max(10, Math.min(600, parsed)),
    );
  }

  function normalizedHotkeyMain(key) {
    if (typeof key !== 'string') return '';
    if (/^[a-z0-9]$/i.test(key)) return key.toUpperCase();
    if (/^F(?:[1-9]|1[0-2])$/i.test(key)) return key.toUpperCase();
    if (["`", '-', '=', '[', ']', '\\', ';', "'", ',', '.', '/'].includes(key)) {
      return key;
    }
    const special = {
      ' ': 'Space',
      Spacebar: 'Space',
      Tab: 'Tab',
      Enter: 'Enter',
      Backspace: 'Backspace',
    };
    return special[key] || '';
  }

  function canonicalHotkeyFromEvent(event) {
    const main = normalizedHotkeyMain(event.key);
    if (!main) return '';
    const modifiers = [];
    if (event.ctrlKey) modifiers.push('Ctrl');
    if (event.altKey) modifiers.push('Alt');
    if (event.shiftKey) modifiers.push('Shift');
    if (event.metaKey) modifiers.push('Win');
    if (!modifiers.length) return '';
    return [...modifiers, main].join('+');
  }

  function eventMatchesQuickbarHotkey(event) {
    if (!runtime.settings) return false;
    const parts = runtime.settings.quickbarHotkey.split('+');
    const main = parts.pop();
    return (
      normalizedHotkeyMain(event.key) === main &&
      event.ctrlKey === parts.includes('Ctrl') &&
      event.altKey === parts.includes('Alt') &&
      event.shiftKey === parts.includes('Shift') &&
      event.metaKey === parts.includes('Win')
    );
  }

  function resetHotkeyRecordingVisual() {
    runtime.hotkeyRecording = false;
    const button = byId('quickbar-hotkey-btn');
    const display = byId('quickbar-hotkey-display');
    button?.classList.remove('recording');
    display?.classList.remove('recording');
    if (button) {
      button.dataset.i18n = 'settings.hotkey.modify';
      button.textContent = t('settings.hotkey.modify');
    }
    if (runtime.settings) projectQuickbarSettings(runtime.settings);
  }

  function startProductHotkeyRecording() {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.settings ||
      runtime.pendingQuickbarEnabled ||
      runtime.pendingQuickbarHotkey
    ) {
      return;
    }
    runtime.hotkeyRecording = true;
    const button = byId('quickbar-hotkey-btn');
    const display = byId('quickbar-hotkey-display');
    button?.classList.add('recording');
    display?.classList.add('recording');
    if (button) {
      button.removeAttribute('data-i18n');
      button.textContent = fixedText('录制中…', 'Recording…');
    }
    if (display) {
      display.textContent = fixedText('请按下新快捷键', 'Press new shortcut');
    }
    refreshControls();
  }

  function requestQuickbarHotkey(hotkey) {
    resetHotkeyRecordingVisual();
    if (
      !runtime.bridge ||
      runtime.state !== 'UNLOCKED' ||
      !runtime.settings ||
      runtime.pendingQuickbarEnabled ||
      runtime.pendingQuickbarHotkey ||
      hotkey === runtime.settings.quickbarHotkey
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingQuickbarHotkey = id;
    runtime.pendingQuickbarHotkeyValue = hotkey;
    refreshControls();
    runtime.bridge.setQuickbarHotkeyV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      hotkey,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingQuickbarHotkey === id) {
            clearPendingQuickbarHotkey();
            projectQuickbarSettings(runtime.settings);
            showSettingsFailure(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function requestProductThemeShortcut() {
    requestProductTheme(
      runtime.themePreference === 'DARK' ? 'LIGHT' : 'DARK',
    );
  }

  const RECORD_FIELDS = Object.freeze({
    PLATFORM: {id: 'mf-platform', key: 'platform', limit: 128, bytes: 512},
    ACCOUNT: {id: 'mf-account', key: 'account', limit: 512, bytes: 2048},
    PASSWORD: {id: 'mf-password', key: 'password', limit: 1024, bytes: 4096},
    NOTES: {id: 'mf-notes', key: 'notes', limit: 8192, bytes: 32768},
  });

  function normalizedLongFields(value, allowPassword = true) {
    if (!Array.isArray(value) || value.length > 4 || new Set(value).size !== value.length) return null;
    if (value.some((field) => !RECORD_FIELDS[field] || (!allowPassword && field === 'PASSWORD'))) return null;
    return Object.freeze([...value]);
  }

  function recordFieldCharacterCount(value, maximum) {
    // 按 Python 同样的 Unicode 码点计数，不为长备注生成逐字符数组；超限即停止。
    let count = 0;
    for (let offset = 0; offset < value.length; offset += value.codePointAt(offset) > 0xffff ? 2 : 1) {
      if (++count > maximum) return count;
    }
    return count;
  }

  function recordFieldFits(field, value) {
    if (typeof value !== 'string' || value.includes('\0')) return false;
    return recordFieldCharacterCount(value, RECORD_FIELDS[field].limit) <= RECORD_FIELDS[field].limit &&
      new TextEncoder().encode(value).length <= RECORD_FIELDS[field].bytes;
  }

  async function recordFieldDigest(value) {
    const encoded = new TextEncoder().encode(value);
    try {
      const digest = await crypto.subtle.digest('SHA-256', encoded);
      return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
    } finally {
      encoded.fill(0);
    }
  }

  function fieldTargetValue(target) {
    return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement
      ? target.value : target.textContent || '';
  }

  function setFieldTargetValue(target, value) {
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) target.value = value;
    else target.textContent = value;
  }

  function fieldReadIsCurrent(read) {
    if (!read || read.cancelled || runtime.state !== 'UNLOCKED' || !runtime.ready ||
        read.page !== runtime.pageEpoch || read.session !== runtime.sessionEpoch || !read.target.isConnected) return false;
    if (read.owner === 'editor') {
      return Boolean(activeEditModal() && runtime.editRecordId === read.recordId &&
        runtime.editRevision === read.revision && runtime.editLeaseId === read.leaseId);
    }
    if (read.owner === 'name') {
      return runtime.recordTextModal?.recordId === read.recordId && runtime.recordTextModal?.revision === read.revision;
    }
    return state.currentNav === 'vault' && runtime.selectedRecordId === read.recordId && runtime.selectedRevision === read.revision;
  }

  function releaseFieldRead(readId, page, session) {
    if (readId && runtime.bridge && runtime.ready && page === runtime.pageEpoch && session === runtime.sessionEpoch) {
      runtime.bridge.releaseRecordFieldReadV1(requestId(), page, session, readId, () => {});
    }
  }

  function cancelFieldReads(owner = '') {
    const matches = (read) => !owner || read.owner === owner;
    const cancelled = runtime.fieldReadQueue.filter(matches);
    runtime.fieldReadQueue = runtime.fieldReadQueue.filter((read) => !matches(read));
    if (runtime.fieldRead && matches(runtime.fieldRead)) {
      cancelled.push(runtime.fieldRead);
      runtime.fieldRead = null;
    }
    for (const read of cancelled) {
      read.cancelled = true;
      window.clearTimeout(read.timer);
      if (read.request && runtime.bridge && read.page === runtime.pageEpoch) {
        runtime.bridge.cancelRequestV1(requestId(), read.page, read.request, () => {});
      }
      releaseFieldRead(read.readId, read.page, read.session);
      if (!read.completed) setFieldTargetValue(read.target, '');
      if ('readOnly' in read.target) read.target.readOnly = read.wasReadOnly;
      read.target.removeAttribute('aria-busy');
      read.resolve(false);
    }
    if (cancelled.length) window.queueMicrotask(pumpFieldReads);
  }

  function readRecordField(record, field, target, owner, leaseId = '', completeField = null) {
    return new Promise((resolve) => {
      if (owner !== 'editor') record = currentRecordForAction(record);
      if (!runtime.bridge || runtime.fieldReadQueue.length >= 4) {
        resolve(false);
        return;
      }
      runtime.fieldReadQueue.push({
        recordId: record.recordId, revision: record.revision, field, target, owner,
        leaseId, page: runtime.pageEpoch, session: runtime.sessionEpoch,
        readId: '', offset: 0, request: '', timer: 0, cancelled: false, completed: false,
        wasReadOnly: Boolean(target.readOnly), resolve, onComplete: completeField,
        deadline: performance.now() + (owner === 'reveal' ? 30000 : 300000),
      });
      pumpFieldReads();
    });
  }

  function pumpFieldReads() {
    if (runtime.fieldRead) return;
    const read = runtime.fieldReadQueue.shift();
    if (!read) return;
    if (!fieldReadIsCurrent(read)) {
      read.resolve(false);
      window.queueMicrotask(pumpFieldReads);
      return;
    }
    runtime.fieldRead = read;
    setFieldTargetValue(read.target, '');
    read.target.dataset.pdmSensitive = 'true';
    read.target.setAttribute('aria-busy', 'true');
    if ('readOnly' in read.target) read.target.readOnly = true;
    read.timer = window.setTimeout(() => finishFieldRead(read, false, 'SECRET_LEASE_EXPIRED'),
      Math.max(1, read.deadline - performance.now()));
    requestFieldChunk(read);
  }

  function requestFieldChunk(read) {
    if (!fieldReadIsCurrent(read)) {
      finishFieldRead(read, false);
      return;
    }
    read.request = requestId();
    const sent = read.request;
    runtime.bridge.readRecordFieldChunkV1(sent, read.page, read.session,
      read.recordId, read.revision, read.field, read.leaseId, read.readId, read.offset,
      (ack) => {
        if (runtime.fieldRead === read && read.request === sent && (!ack || ack.accepted !== true)) {
          finishFieldRead(read, false, ack?.errorCode || 'INTERNAL_FAILURE');
        }
      });
  }

  async function finishFieldRead(read, success, errorCode = '') {
    if (runtime.fieldRead !== read) return;
    window.clearTimeout(read.timer);
    if (!success) {
      if (read.request && runtime.bridge && read.page === runtime.pageEpoch) {
        runtime.bridge.cancelRequestV1(requestId(), read.page, read.request, () => {});
      }
      releaseFieldRead(read.readId, read.page, read.session);
      setFieldTargetValue(read.target, '');
    }
    read.request = '';
    read.completed = success;
    read.target.removeAttribute('aria-busy');
    if ('readOnly' in read.target) read.target.readOnly = read.wasReadOnly;
    if (success && read.onComplete && fieldReadIsCurrent(read)) {
      try { await read.onComplete(read.target); }
      catch (_error) { success = false; errorCode = 'INTERNAL_FAILURE'; }
    }
    if (errorCode && fieldReadIsCurrent(read)) {
      if (read.owner === 'editor') showCreateFormError(errorText(errorCode));
      else showErrorToast(errorCode);
    }
    if (runtime.fieldRead === read) runtime.fieldRead = null;
    read.resolve(success && fieldReadIsCurrent(read));
    pumpFieldReads();
  }

  function onRecordFieldChunk(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    const read = runtime.fieldRead;
    if (!read || read.request !== request || read.page !== pageEpoch || read.session !== sessionEpoch || !fieldReadIsCurrent(read)) {
      if (result && typeof result === 'object') {
        result.text = '';
        releaseFieldRead(result.readId, pageEpoch, sessionEpoch);
      }
      if (read && read.request === request) finishFieldRead(read, false);
      return;
    }
    read.request = '';
    if (errorCode !== 'OK') {
      if (result) result.text = '';
      finishFieldRead(read, false, errorCode);
      return;
    }
    const text = result?.text;
    const characters = typeof text === 'string' ? recordFieldCharacterCount(text, 8192) : -1;
    const valid = typeof text === 'string' && characters <= 8192 &&
      new TextEncoder().encode(text).length <= 32768 && typeof result.readId === 'string' &&
      /^[A-Za-z0-9_-]{16,64}$/.test(result.readId) && (!read.readId || read.readId === result.readId) &&
      Number.isSafeInteger(result.nextOffset) && result.nextOffset === read.offset + characters &&
      typeof result.done === 'boolean' && (result.done || result.nextOffset > read.offset);
    if (!valid) {
      if (result) result.text = '';
      finishFieldRead(read, false, 'INTERNAL_FAILURE');
      return;
    }
    read.readId = result.readId;
    read.offset = result.nextOffset;
    setFieldTargetValue(read.target, fieldTargetValue(read.target) + text);
    result.text = '';
    if (result.done) finishFieldRead(read, true);
    else requestFieldChunk(read);
  }

  function appendFullNameAction(container, record) {
    if (!record.longFields?.includes('PLATFORM')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-sm';
    button.dataset.pdmM4VaultAction = 'true';
    const location = container.classList.contains('split-name') ? 'split' : container.tagName === 'H2' ? 'detail' : 'list';
    setRecordActionFocusIdentity(button, record.recordId, `${location}-full-name`);
    setRuntimeText(button, '', '查看完整', 'View full name');
    button.addEventListener('click', (event) => {
      record = currentRecordForAction(record);
      event.preventDefault();
      event.stopPropagation();
      if (runtime.state !== 'UNLOCKED' || activeEditModal()) return;
      openModal('<div class="modal-header"><div class="modal-title"></div></div>' +
        '<div class="modal-body"><textarea class="modal-field-input" id="full-record-name" readonly></textarea></div>' +
        '<div class="modal-footer"><button type="button" class="btn btn-primary" data-pdm-onclick="closeModal()"></button></div>');
      runtime.recordTextModal = {recordId: record.recordId, revision: record.revision};
      setRuntimeText(byId('active-modal').querySelector('.modal-title'), '', '完整名称', 'Full name');
      setRuntimeText(byId('active-modal').querySelector('.btn-primary'), '', '关闭', 'Close');
      readRecordField(record, 'PLATFORM', byId('full-record-name'), 'name');
      refreshControls();
    });
    container.append(button);
  }

  function releaseActiveReveal(reason = 'manual_hide') {
    cancelFieldReads('reveal');
    const active = runtime.activeReveal;
    runtime.activeReveal = null;
    runtime.pendingReveal = '';
    runtime.revealTarget = null;
    if (!active) return;
    if (window.pdmSensitiveDom) {
      window.pdmSensitiveDom.clearLease(active.leaseId, reason);
    }
    if (active.textElement && active.textElement.isConnected) {
      active.textElement.textContent = (
        active.hasPassword ? '••••••••••••' : ''
      );
      active.textElement.removeAttribute('data-pdm-sensitive');
    }
    if (active.button && active.button.isConnected) {
      active.button.replaceChildren();
      appendStaticIcon(active.button, 'eye', 15);
      syncRecordRevealAccessibility(active.button, false);
    }
    if (
      runtime.bridge &&
      runtime.ready &&
      runtime.state === 'UNLOCKED' &&
      runtime.pageEpoch > 0 &&
      runtime.sessionEpoch > 0
    ) {
      const id = requestId();
      runtime.bridge.releaseSecretLeaseV1(
        id,
        runtime.pageEpoch,
        active.leaseId,
        () => {},
      );
    }
  }

  function syncRecordRevealAccessibility(button, visible) {
    if (!(button instanceof HTMLElement)) return;
    const label = t(visible ? 'common.password.hide' : 'common.password.show');
    button.title = label;
    button.setAttribute('aria-label', label);
    button.setAttribute('aria-pressed', String(visible));
  }

  function cancelPendingRecordDetails() {
    const pending = runtime.pendingDetails;
    if (pending) runtime.retiredDetailsRequest = pending;
    runtime.pendingDetails = '';
    runtime.pendingDetailsTarget = null;
    runtime.queuedDetailsTarget = null;
    if (pending && runtime.bridge && runtime.ready && runtime.pageEpoch > 0) {
      runtime.bridge.cancelRequestV1(
        requestId(),
        runtime.pageEpoch,
        pending,
        () => {},
      );
    }
  }

  function clearSelectedDetailContent() {
    runtime.recoveryFollow = null;
    cancelFieldReads('detail');
    cancelFieldReads('name');
    stopRecordTotp();
    cancelTotpCopy();
    releaseActiveReveal('navigation');
    clearRecoveryActions('navigation');
    runtime.selectedDetails = null;
    cancelPendingRecordDetails();
    document.querySelectorAll('#view-list .item-detail, #split-detail').forEach((detail) => {
      detail.replaceChildren();
      detail.pdmDetailIdentity = '';
      delete detail.pdmSetDetailRecord;
      delete detail.dataset.pdmDetailReady;
    });
  }

  function clearSelectedDetails() {
    clearSelectedDetailContent();
    runtime.selectedRecordId = 0;
    runtime.selectedRevision = '';
    state.expandedId = null;
    state.splitSelectedId = null;
  }

  function clearVaultAuthority() {
    runtime.pendingStrengthRetries.clear();
    runtime.pendingRatingLocation = runtime.ratingLocationKey = '';
    runtime.recoveryInvalidListRequest = runtime.recoveryInvalidRatingRequest = '';
    runtime.recoveryFollow = null;
    runtime.ratingVaultDirty = runtime.ratingHealthDirty = false;
    cancelHealthLocate();
    runtime.healthEditRecordId = 0;
    cancelFieldReads();
    for (const id of ['view-list', 'split-list']) {
      const list = byId(id);
      if (list) delete list.pdmRowsIdentity;
    }
    clearPendingSort();
    stopRecordTotp();
    runtime.pendingTotpCopy = '';
    runtime.recordTextModal = null;
    runtime.pendingFavoriteRecordId = 0;
    if (runtime.searchTimer) {
      window.clearTimeout(runtime.searchTimer);
      runtime.searchTimer = 0;
    }
    runtime.pendingList = '';
    runtime.pendingListKey = '';
    runtime.pendingFavorite = '';
    runtime.pendingReveal = '';
    runtime.revealTarget = null;
    runtime.pendingAccountCopy = '';
    runtime.pendingPasswordCopy = '';
    clearRecoveryActions('session_invalidated');
    runtime.pendingClipboardClear = '';
    clearSelectedDetails();
    runtime.retiredDetailsRequest = '';
    runtime.vaultItems = [];
    runtime.vaultCounts = {
      all: 0,
      favorite: 0,
      weak: 0,
      duplicate: 0,
      similar: 0,
    };
    runtime.vaultTotal = 0;
    runtime.vaultRevision = '';
    runtime.vaultNextCursor = '';
    runtime.vaultCursor = '';
    runtime.vaultCursorHistory = [];
  }

  function clearSelectedNoteDetails() {
    cancelNoteFieldRead();
    runtime.pendingNoteDetails = '';
    if (runtime.selectedNoteDetails) {
      runtime.selectedNoteDetails.title = '';
      runtime.selectedNoteDetails.content = '';
    }
    runtime.selectedNoteId = 0;
    runtime.selectedNoteRevision = '';
    runtime.selectedNoteDetails = null;
    runtime.noteDraft = null;
    runtime.noteEditRequestedId = 0;
    runtime.noteEditReturnToOverview = false;
    state.expandedId = null;
  }

  function clearNoteAuthority() {
    if (runtime.noteSearchTimer) {
      window.clearTimeout(runtime.noteSearchTimer);
      runtime.noteSearchTimer = 0;
    }
    runtime.pendingNoteList = '';
    runtime.pendingNoteListKey = '';
    runtime.noteListFocusKeys = [];
    runtime.noteListFocusGuard = null;
    runtime.pendingNoteSave = '';
    runtime.pendingNoteFavorite = '';
    runtime.pendingNoteFavoriteId = 0;
    runtime.pendingNoteDeletePrepare = '';
    runtime.pendingNoteDeleteCommit = '';
    runtime.noteDelete = null;
    clearSelectedNoteDetails();
    for (const item of runtime.noteItems) {
      item.title = '';
      item.contentPreview = '';
    }
    runtime.noteItems = [];
    runtime.noteTotal = 0;
    runtime.noteAllCount = 0;
    runtime.noteFavoriteCount = 0;
    runtime.noteRevision = '';
    runtime.noteNextCursor = '';
    runtime.noteCursor = '';
    runtime.noteCursorHistory = [];
    runtime.notePageInvalidated = false;
    runtime.notePageTarget = 0;
    runtime.noteQuery = '';
    runtime.noteFilter = 'ALL';
    notes.splice(0, notes.length);
  }

  function clearLockedProductSurfaces() {
    for (const id of ['view-list', 'split-list', 'split-detail', 'notes-list']) {
      byId(id)?.replaceChildren();
    }
    for (const id of [
      'count-all', 'count-fav', 'count-weak', 'count-dup', 'count-similar',
      'ncount-all', 'ncount-fav',
    ]) {
      const counter = byId(id);
      if (counter) counter.textContent = '0';
    }
  }

  function resetClipboardState() {
    runtime.clipboardKind = 'NONE';
    runtime.clipboardMode = 'COUNTDOWN';
    runtime.clipboardRemaining = 0;
    runtime.clipboardOwned = false;
    renderClipboardState();
  }

  function appendStaticIcon(element, name, size) {
    element.innerHTML = svgIcon(name, size);
  }

  function appendEmptyState(
    container,
    text,
    iconName = 'search',
    i18nKey = '',
    fixedZh = '',
    fixedEn = '',
    className = 'empty-state',
  ) {
    const empty = document.createElement('div');
    empty.className = className;
    const icon = document.createElement('div');
    icon.className = 'icon';
    appendStaticIcon(icon, iconName, 40);
    const label = document.createElement('div');
    if (i18nKey) label.dataset.i18n = i18nKey;
    if (fixedZh || fixedEn) {
      label.dataset.pdmFixedZh = fixedZh;
      label.dataset.pdmFixedEn = fixedEn;
    }
    label.textContent = text;
    empty.append(icon, label);
    container.replaceChildren(empty);
  }

  function currentRecordForAction(record) {
    const selected = runtime.selectedDetails;
    return selected && selected.recordId === record?.recordId &&
      selected.revision === runtime.selectedRevision ? selected : record;
  }

  function appendFavorite(container, favorite, size = 16, record = null) {
    const star = document.createElement(record ? 'button' : 'span');
    star.className = `fav-star${favorite ? ' active' : ''}`;
    if (record) {
      const label = t('vault.filter.favorite');
      star.type = 'button';
      star.title = label;
      star.setAttribute('aria-label', label);
      star.setAttribute('aria-pressed', favorite ? 'true' : 'false');
      star.dataset.pdmM4VaultAction = 'true';
      const location = container.classList.contains('item-summary') ? 'list' :
        container.classList.contains('detail-header') ? 'split-detail' : 'split-list';
      setRecordActionFocusIdentity(star, record.recordId, `${location}-favorite`);
      star.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        requestRecordFavorite(currentRecordForAction(record), !favorite);
      });
    } else {
      star.setAttribute('aria-hidden', 'true');
    }
    appendStaticIcon(star, 'star', size);
    container.append(star);
  }

  function appendPlatformIdentity(
    container,
    platform,
    account,
    duplicateGroup,
    similarGroup,
    record = null,
  ) {
    const icon = document.createElement('div');
    icon.className = `platform-icon ${platformColorClass(platform)}`;
    icon.textContent = platform.trim().slice(0, 1).toUpperCase() || '?';
    const text = document.createElement('div');
    text.className = 'pdm-inline-22a08c80a9';
    const name = document.createElement('div');
    name.className = 'platform-name';
    const nameText = document.createElement('span');
    nameText.className = 'platform-name-text';
    nameText.textContent = platform;
    name.append(nameText);
    if (record) appendFullNameAction(name, record);
    if (duplicateGroup > 0) {
      const duplicate = document.createElement('span');
      duplicate.className = 'dup-tag';
      duplicate.dataset.pdmDuplicateGroup = String(duplicateGroup);
      duplicate.textContent = `${t('vault.dup.tag')}${duplicateGroup}`;
      name.append(duplicate);
    }
    if (similarGroup > 0) {
      const similar = document.createElement('span');
      similar.className = 'similar-tag';
      similar.dataset.pdmSimilarGroup = String(similarGroup);
      similar.textContent = `${t('vault.similar.tag')}${similarGroup}`;
      name.append(similar);
    }
    const accountText = document.createElement('div');
    accountText.className = 'platform-account';
    accountText.dataset.pdmSensitive = 'true';
    accountText.textContent = account;
    text.append(name, accountText);
    container.append(icon, text);
  }

  function appendStrengthMeta(container, summary) {
    const dot = document.createElement('span');
    const strength = summary.strength.toLowerCase();
    dot.className = `strength-dot strength-${strength}`;
    dot.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.className = `item-strength-label ${strength}`;
    label.dataset.i18n = `common.strength.${strength}`;
    label.textContent = t(`common.strength.${strength}`);
    container.append(dot, label);
    renderStrengthRetry(container, summary);
  }

  function renderStrengthRetry(container, record) {
    let button = container.querySelector?.('[data-pdm-strength-retry]');
    if (record.strength !== 'FAILED') {
      if (button) button.remove();
      return;
    }
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.className = 'item-strength-label strength-retry';
      button.dataset.pdmStrengthRetry = 'true';
      setRecordActionFocusIdentity(button, record.recordId, 'retry-strength');
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        requestStrengthRetry(button.pdmStrengthRecord);
      });
      container.append(button);
    }
    button.pdmStrengthRecord = record;
    button.textContent = fixedText('重试', 'Retry');
    button.setAttribute('aria-label', fixedText('重试检测：', 'Retry strength check: ') + record.platform);
    button.disabled = runtime.pendingStrengthRetries.has(record.recordId);
  }

  function requestStrengthRetry(record) {
    record = currentRecordForAction(record);
    if (runtime.state !== 'UNLOCKED' || !runtime.ready || !runtime.bridge ||
        !record || !Number.isSafeInteger(record.recordId) || !isRevision(record.revision) ||
        runtime.pendingStrengthRetries.has(record.recordId)) return;
    const id = requestId();
    runtime.pendingStrengthRetries.set(record.recordId, id);
    refreshControls();
    runtime.bridge.retryRecordStrengthV1(id, runtime.pageEpoch, runtime.sessionEpoch,
      record.recordId, record.revision, (ack) => {
        if (ack?.accepted !== true) onStrengthRetried(id, runtime.pageEpoch, runtime.sessionEpoch,
          ack?.errorCode || 'INTERNAL_FAILURE', 0, 0, null);
      });
  }

  function onStrengthRetried(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    const entry = [...runtime.pendingStrengthRetries].find(([_id, pending]) => pending === request);
    if (!entry) return;
    runtime.pendingStrengthRetries.delete(entry[0]);
    if (errorCode !== 'OK') showErrorToast(errorCode);
    else if (!result || result.recordId !== entry[0] || !isRevision(result.revision) ||
        !['WEAK', 'FAIR', 'STRONG', 'PENDING', 'CHECKING', 'FAILED'].includes(result.strength)) {
      showErrorToast('INTERNAL_FAILURE');
    }
    runtime.ratingVaultDirty = runtime.ratingHealthDirty = true;
    refreshControls();
    queueRatingRefresh();
  }

  function queueRatingRefresh() {
    if (runtime.ratingRefreshQueued) return;
    runtime.ratingRefreshQueued = true;
    Promise.resolve().then(() => {
      runtime.ratingRefreshQueued = false;
      if (runtime.state !== 'UNLOCKED' || !runtime.ready || document.hidden) return;
      if (state.currentNav === 'vault' && runtime.ratingVaultDirty &&
          !runtime.pendingList && !runtime.pendingRatingLocation) {
        runtime.ratingVaultDirty = false;
        if (!requestRatingVaultLocation()) requestVaultPage();
      }
      if (state.currentNav === 'security' && runtime.ratingHealthDirty &&
          !runtime.pendingHealthSummary && !runtime.pendingHealthOverview) {
        runtime.ratingHealthDirty = false;
        requestHealthSummary(true);
      }
    });
  }

  function requestRatingVaultLocation() {
    if (!runtime.vaultCursor || !globalSearchFits(runtime.vaultQuery)) return false;
    const anchor = runtime.vaultItems.find(item => item.recordId === runtime.selectedRecordId)
      || runtime.vaultItems[0];
    if (!anchor) {
      resetVaultPagePosition(true);
      return false;
    }
    const id = requestId();
    runtime.pendingRatingLocation = id;
    runtime.ratingLocationKey = currentVaultRequestKey();
    runtime.bridge.locateVaultAnchorV1(id, runtime.pageEpoch, runtime.sessionEpoch,
      anchor.recordId, runtime.vaultQuery, runtime.vaultFilter, runtime.vaultSort, (ack) => {
        if (ack?.accepted !== true) onRatingVaultLocated(id, runtime.pageEpoch, runtime.sessionEpoch,
          ack?.errorCode || 'INTERNAL_FAILURE', 0, 0, null);
      });
    return true;
  }

  function onRatingVaultLocated(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingRatingLocation ||
        pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    if (request === runtime.recoveryInvalidRatingRequest) {
      runtime.recoveryInvalidRatingRequest = '';
      runtime.pendingRatingLocation = runtime.ratingLocationKey = '';
      scrubVaultPageResult(result?.page);
      runtime.ratingVaultDirty = true;
      queueRatingRefresh();
      return;
    }
    const key = runtime.ratingLocationKey;
    runtime.pendingRatingLocation = runtime.ratingLocationKey = '';
    if (key !== currentVaultRequestKey()) {
      scrubVaultPageResult(result?.page);
      queueRatingRefresh();
      return;
    }
    const location = errorCode === 'OK' ? normalizeVaultLocation(result) : null;
    if (location) {
      runtime.vaultCursor = location.cursor;
      runtime.vaultCursorHistory = [...location.cursorHistory];
      runtime.pendingList = request;
      runtime.pendingListKey = currentVaultRequestKey();
      onVaultListed(request, pageEpoch, sessionEpoch, 'OK', 0, 0, result.page);
    } else if (errorCode === 'NOT_FOUND' || errorCode === 'INVALID_ARGUMENT') {
      resetVaultPagePosition(true);
      requestVaultPage();
    } else {
      runtime.vaultError = errorCode === 'OK' ? 'INTERNAL_FAILURE' : errorCode;
      renderM4Vault();
    }
    queueRatingRefresh();
  }

  function setRecordActionFocusIdentity(
    element,
    recordId,
    action,
  ) {
    if (
      !(element instanceof HTMLElement) ||
      !Number.isSafeInteger(recordId) ||
      recordId < 1 ||
      typeof action !== 'string' ||
      !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(action)
    ) {
      return;
    }
    element.dataset.pdmNativeFocusKey = (
      `vault-action:${recordId}:${action}`
    );
    element.dataset.pdmRecordId = String(recordId);
    element.dataset.pdmFocusAction = action;
  }

  function createRecordActionButton(
    iconName,
    title,
    activate,
    titleKey = '',
    focusKey = '',
  ) {
    const button = document.createElement('button');
    button.className = 'btn-icon';
    button.type = 'button';
    button.title = title;
    button.setAttribute('aria-label', title);
    if (titleKey) button.dataset.i18nTitle = titleKey;
    button.dataset.pdmM4VaultAction = 'true';
    const focusMatch = /^vault-action:(\d+):([A-Za-z0-9_-]+)$/.exec(
      focusKey,
    );
    if (focusMatch) {
      setRecordActionFocusIdentity(
        button,
        Number.parseInt(focusMatch[1], 10),
        focusMatch[2],
      );
    }
    appendStaticIcon(button, iconName, 15);
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      activate(button);
    });
    return button;
  }

  function appendDetailRow(
    container,
    labelText,
    valueText,
    valueClass = '',
    sensitive = false,
    labelKey = '',
  ) {
    const row = document.createElement('div');
    row.className = 'detail-row';
    const label = document.createElement('div');
    label.className = 'detail-label';
    if (labelKey) label.dataset.i18n = labelKey;
    label.textContent = labelText;
    const value = document.createElement('div');
    value.className = `detail-value${valueClass ? ` ${valueClass}` : ''}`;
    const text = document.createElement('span');
    text.className = 'text';
    if (valueClass === 'account' || valueClass === 'password') {
      text.tabIndex = 0;
      text.setAttribute('role', 'group');
      text.setAttribute('aria-label', labelText);
    }
    if (sensitive) text.dataset.pdmSensitive = 'true';
    text.textContent = valueText;
    value.append(text);
    row.append(label, value);
    container.append(row);
    return value;
  }

  function updateDetailSubtitle(subtitle, strength) {
    if (!subtitle) return;
    subtitle.dataset.strength = strength;
    subtitle.textContent = `${t('vault.detail.updated')} ${subtitle.dataset.updatedDate || ''} · `
      + `${t('vault.strength.label')}: ${t(`common.strength.${String(strength || '').toLowerCase()}`)}`;
  }

  function appendRecordDetails(
    container,
    details,
    includeHeader = false,
  ) {
    const identity = currentRecordDetailIdentity(details, includeHeader);
    if (identity && container.pdmDetailIdentity === identity) {
      container.pdmSetDetailRecord?.(details);
      const subtitle = container.querySelector('[data-pdm-detail-subtitle="true"]');
      if (subtitle && (subtitle.dataset.strength !== details.strength ||
          subtitle.dataset.updatedDate !== details.updatedDate)) {
        subtitle.dataset.updatedDate = details.updatedDate;
        updateDetailSubtitle(subtitle, details.strength);
      }
      const updated = container.querySelector('[data-pdm-updated-date]');
      if (updated && updated.dataset.pdmUpdatedDate !== details.updatedDate) {
        updated.dataset.pdmUpdatedDate = details.updatedDate;
        updated.textContent = `${t('vault.detail.updated')} ${details.updatedDate}`;
      }
      renderStrengthRetry(container.querySelector('.detail-header') || container, details);
      return;
    }
    if (!includeHeader) {
      container.dataset.pdmDetailReady = 'false';
      container.hidden = true;
    }
    cancelFieldReads('detail');
    stopRecordTotp();
    clearRecoveryActions('navigation');
    const afterAttach = [];
    let activateTotp = null;
    const focusLocation = includeHeader ? 'split-detail' : 'list-detail';
    const inner = includeHeader
      ? document.createDocumentFragment()
      : document.createElement('div');
    if (!includeHeader) inner.className = 'detail-inner';
    let detailBody = inner;
    if (includeHeader) {
      const header = document.createElement('div');
      header.className = 'detail-header';
      const icon = document.createElement('div');
      icon.className = (
        `platform-icon pdm-platform-icon-large ${
          platformColorClass(details.platform)
        }`
      );
      icon.textContent = (
        details.platform.trim().slice(0, 1).toUpperCase() || '?'
      );
      const heading = document.createElement('div');
      heading.className = 'pdm-inline-83725d2c6e';
      const title = document.createElement('h2');
      const titleText = document.createElement('span');
      titleText.className = 'platform-name-text';
      titleText.textContent = details.platform;
      title.append(titleText);
      appendFullNameAction(title, details);
      const subtitle = document.createElement('div');
      subtitle.className = 'sub';
      subtitle.dataset.pdmDetailSubtitle = 'true';
      subtitle.dataset.updatedDate = details.updatedDate;
      updateDetailSubtitle(subtitle, details.strength);
      heading.append(title, subtitle);
      renderStrengthRetry(heading, details);
      header.append(icon, heading);
      appendFavorite(header, details.favorite, 16, details);
      inner.append(header);
      detailBody = document.createElement('div');
      detailBody.className = 'pdm-inline-022625b12b';
      inner.append(detailBody);
    }
    const accountValue = appendDetailRow(
      detailBody,
      t('vault.detail.account'),
      details.account,
      'account',
      true,
      'vault.detail.account',
    );
    setRecordActionFocusIdentity(accountValue.querySelector('.text'), details.recordId, `${focusLocation}-account-text`);
    const accountActions = document.createElement('div');
    accountActions.className = 'actions';
    accountActions.append(
      createRecordActionButton(
        'user',
        t('vault.copy.account'),
        () => copyRecordField(details, 'ACCOUNT'),
        'vault.copy.account',
        `vault-action:${details.recordId}:${focusLocation}-copy-account`,
      ),
    );
    accountValue.append(accountActions);
    if (details.longFields.includes('ACCOUNT')) {
      afterAttach.push(attachLongFieldRead(accountValue, details, 'ACCOUNT'));
    }
    const passwordValue = appendDetailRow(
      detailBody,
      t('vault.detail.password'),
      details.hasPassword ? '••••••••••••' : '',
      'password',
      false,
      'vault.detail.password',
    );
    const passwordText = passwordValue.querySelector('.text');
    setRecordActionFocusIdentity(passwordText, details.recordId, `${focusLocation}-password-text`);
    const passwordActions = document.createElement('div');
    passwordActions.className = 'actions';
    const revealButton = createRecordActionButton(
      'eye',
      t('common.password.show'),
      (button) => toggleRecordReveal(
        details,
        passwordText,
        button,
        includeHeader ? 'SPLIT' : 'LIST',
      ),
      'common.password.show',
      `vault-action:${details.recordId}:${focusLocation}-reveal-password`,
    );
    syncRecordRevealAccessibility(revealButton, false);
    passwordActions.append(
      revealButton,
      createRecordActionButton(
        'dice',
        t('vault.regenerate'),
        () => requestRecordEditor(details, 'initial', true),
        'vault.regenerate',
        `vault-action:${details.recordId}:${focusLocation}-regenerate-password`,
      ),
      createRecordActionButton(
        'key',
        t('vault.copy.password'),
        () => copyRecordField(details, 'PASSWORD'),
        'vault.copy.password',
        `vault-action:${details.recordId}:${focusLocation}-copy-password`,
      ),
    );
    passwordValue.append(passwordActions);
    const notesValue = appendDetailRow(
      detailBody,
      t('vault.detail.notes'),
      details.notes,
      'notes',
      true,
      'vault.detail.notes',
    );
    if (details.longFields.includes('NOTES')) {
      afterAttach.push(attachLongFieldRead(notesValue, details, 'NOTES'));
    }
    if (details.hasTotp) {
      const value = appendDetailRow(detailBody, t('vault.detail.totp'), '', 'totp', true, 'vault.detail.totp');
      const actions = document.createElement('div');
      actions.className = 'actions';
      const ring = document.createElement('div');
      ring.className = 'totp-ring';
      ring.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">' +
        '<circle class="bg" cx="12" cy="12" r="10"/>' +
        '<circle class="fg" cx="12" cy="12" r="10" stroke-dasharray="62.83" stroke-dashoffset="0"/></svg>';
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'btn btn-sm';
      retry.dataset.pdmM4VaultAction = 'true';
      retry.hidden = true;
      setRuntimeText(retry, '', '重试', 'Retry');
      retry.addEventListener('click', () => requestRecordTotp(runtime.totpDisplay));
      const copy = createRecordActionButton('key', t('vault.copy.totp'),
        () => copyRecordTotp(details), 'vault.copy.totp',
        `vault-action:${details.recordId}:${focusLocation}-copy-totp`);
      actions.append(ring, retry, copy);
      value.append(actions);
      activateTotp = () => startRecordTotp(details, value.querySelector('.text'), ring, retry);
    }
    if (details.recoveryUsed.length) {
      const value = appendDetailRow(
        detailBody,
        fixedText(`恢复码（${details.recoveryUsed.length}）`, `Recovery codes (${details.recoveryUsed.length})`),
        '', 'recovery', false,
      );
      const list = document.createElement('div');
      list.className = 'recovery-code-list';
      details.recoveryUsed.forEach((used, index) => {
        const item = document.createElement('div');
        item.className = 'recovery-code-item';
        const text = document.createElement('span');
        text.className = 'recovery-code-text';
        text.textContent = '••••••••';
        text.setAttribute('aria-label', fixedText(`第 ${index + 1} 条恢复码，已遮掩`, `Recovery code ${index + 1}, hidden`));
        const status = document.createElement('span');
        status.className = 'recovery-code-status';
        status.textContent = used ? fixedText('已标记已用', 'Marked used') : fixedText('未标记已用', 'Not marked used');
        const actions = document.createElement('div');
        actions.className = 'actions';
        const reveal = createRecordActionButton('eye', fixedText('查看恢复码', 'Show recovery code'),
          (button) => toggleRecoveryReveal(details, index, text, button), '',
          `vault-action:${details.recordId}:${focusLocation}-recovery-${index}-reveal`);
        reveal.setAttribute('aria-pressed', 'false');
        const copy = createRecordActionButton('key', fixedText('复制恢复码', 'Copy recovery code'),
          () => copyRecoveryCode(details, index), '',
          `vault-action:${details.recordId}:${focusLocation}-recovery-${index}-copy`);
        const mark = createRecordActionButton(used ? 'repeat' : 'check',
          used ? fixedText('撤销已用标记', 'Undo used mark') : fixedText('标记已用', 'Mark used'),
          (button) => setRecoveryCodeUsed(details, index, !details.recoveryUsed[index], button), '',
          `vault-action:${details.recordId}:${focusLocation}-recovery-${index}-mark`);
        actions.append(reveal, copy, mark);
        item.append(text, status, actions);
        list.append(item);
      });
      value.replaceChildren(list);
    }
    const footer = document.createElement('div');
    footer.className = 'detail-footer';
    const updated = document.createElement('span');
    updated.className = 'detail-time';
    updated.dataset.pdmUpdatedDate = details.updatedDate;
    updated.textContent = (
      `${t('vault.detail.updated')} ${details.updatedDate}`
    );
    const buttons = document.createElement('div');
    buttons.className = includeHeader
      ? 'detail-buttons pdm-inline-92f0e40814'
      : 'detail-buttons';
    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'btn btn-sm';
    edit.dataset.pdmM4VaultAction = 'true';
    setRecordActionFocusIdentity(
      edit,
      details.recordId,
      `${focusLocation}-edit`,
    );
    edit.innerHTML = `${svgIcon('pencil', 16)} <span data-i18n="vault.button.edit">${t('vault.button.edit')}</span>`;
    edit.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      requestRecordEditor(details, 'initial', false);
    });
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'btn btn-danger btn-sm';
    remove.dataset.pdmM4VaultAction = 'true';
    setRecordActionFocusIdentity(
      remove,
      details.recordId,
      `${focusLocation}-delete`,
    );
    remove.innerHTML = `${svgIcon('trash', 16)} <span data-i18n="vault.button.delete">${t('vault.button.delete')}</span>`;
    remove.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      openDeleteRecordDialog(details);
    });
    buttons.append(edit, remove);
    if (includeHeader) {
      detailBody.append(buttons);
    } else {
      footer.append(updated, buttons);
      detailBody.append(footer);
    }
    container.replaceChildren(inner);
    container.pdmDetailIdentity = identity;
    container.pdmSetDetailRecord = (next) => { details = next; };
    window.queueMicrotask(() => {
      if (container.isConnected && container.pdmDetailIdentity === identity) {
        if (includeHeader) {
          for (const action of afterAttach) action();
          activateTotp?.();
          return;
        }
        if (container.firstChild !== inner) return;
        // 列表隐藏准备正文；用本次正文节点身份拒绝收起/重开后的旧回调。
        const preparations = afterAttach.map((action) => Promise.resolve().then(action));
        Promise.allSettled(preparations).then((results) => {
          if (!container.isConnected || container.firstChild !== inner || container.pdmDetailIdentity !== identity ||
              currentRecordDetailIdentity(runtime.selectedDetails) !== identity) return;
          if (results.some((result) => result.status === 'rejected')) showErrorToast('INTERNAL_FAILURE');
          container.dataset.pdmDetailReady = 'true';
          updateListItemDisclosure(container.parentElement, details.recordId);
          activateTotp?.();
          window.pdmFocusVisibility?.refresh();
        });
      }
    });
  }

  function currentRecordDetailIdentity(details, splitMode = false) {
    if (!details || runtime.state !== 'UNLOCKED' || details.recordId !== runtime.selectedRecordId ||
        details.revision !== runtime.selectedRevision) return '';
    return [runtime.pageEpoch, runtime.sessionEpoch, details.recordId, details.revision, splitMode].join(':');
  }

  function attachLongFieldRead(value, record, field) {
    value.classList.add('pdm-complete-field');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-sm';
    button.dataset.pdmM4VaultAction = 'true';
    setRuntimeText(button, '', '读取完整内容', 'Load full content');
    const activate = async () => {
      if (button.getAttribute('aria-busy') === 'true') return;
      button.setAttribute('aria-busy', 'true');
      const success = await readRecordField(record, field, value.querySelector('.text'), 'detail');
      button.removeAttribute('aria-busy');
      if (!button.isConnected) return;
      if (success) button.hidden = true;
      else setRuntimeText(button, '', '重试读取', 'Retry loading');
    };
    button.pdmActivateLongFieldRead = activate;
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      activate();
    });
    value.append(button);
    return activate;
  }

  function stopRecordTotp() {
    const current = runtime.totpDisplay;
    runtime.totpDisplay = null;
    if (!current) return;
    window.clearInterval(current.timer);
    if (current.request && runtime.bridge && current.page === runtime.pageEpoch) {
      runtime.bridge.cancelRequestV1(requestId(), current.page, current.request, () => {});
    }
    if (current.transientId) window.pdmSensitiveDom.clearTransient(current.transientId, 'navigation');
    current.text.textContent = '';
  }

  function totpIsCurrent(current) {
    return current && runtime.totpDisplay === current && runtime.state === 'UNLOCKED' &&
      runtime.ready && state.currentNav === 'vault' && !document.hidden && current.text.isConnected &&
      runtime.selectedRecordId === current.recordId && runtime.selectedRevision === current.revision &&
      runtime.pageEpoch === current.page && runtime.sessionEpoch === current.session;
  }

  function startRecordTotp(record, text, ring, retry) {
    stopRecordTotp();
    const current = {
      recordId: record.recordId, revision: record.revision, text, ring, retry,
      page: runtime.pageEpoch, session: runtime.sessionEpoch, request: '', requestWall: 0,
      transientId: 0, deadline: 0, timer: 0, failed: false,
    };
    runtime.totpDisplay = current;
    current.timer = window.setInterval(() => {
      if (!totpIsCurrent(current)) {
        stopRecordTotp();
        return;
      }
      if (current.deadline && performance.now() >= current.deadline) current.text.textContent = '';
      if (current.request && Math.floor(Date.now() / 30000) !== Math.floor(current.requestWall / 30000)) {
        runtime.bridge.cancelRequestV1(requestId(), current.page, current.request, () => {});
        current.request = '';
      }
      if (!current.failed) requestRecordTotp(current);
    }, 1000);
    requestRecordTotp(current);
  }

  function requestRecordTotp(current) {
    if (!totpIsCurrent(current) || current.request) return;
    current.failed = false;
    current.retry.hidden = true;
    current.request = requestId();
    current.requestWall = Date.now();
    const sent = current.request;
    runtime.bridge.getRecordTotpCodeV1(sent, current.page, current.session, current.recordId, current.revision,
      (ack) => {
        if (runtime.totpDisplay === current && current.request === sent && (!ack || ack.accepted !== true)) {
          current.request = '';
          current.failed = true;
          current.retry.hidden = false;
          current.text.textContent = fixedText('验证码暂不可用', 'Code unavailable');
        }
      });
  }

  function onRecordTotpCode(request, page, session, errorCode, _argument, _retry, result) {
    const current = runtime.totpDisplay;
    if (!totpIsCurrent(current) || current.request !== request || current.page !== page || current.session !== session) {
      if (result) result.code = '';
      return;
    }
    current.request = '';
    if (errorCode !== 'OK' || !result || typeof result.code !== 'string' || !/^\d{6}$/.test(result.code) ||
        !Number.isInteger(result.remainingSeconds) || result.remainingSeconds < 1 || result.remainingSeconds > 30) {
      if (result) result.code = '';
      current.failed = true;
      current.retry.hidden = false;
      current.text.textContent = fixedText('验证码暂不可用', 'Code unavailable');
      return;
    }
    const wall = Date.now();
    // 主线程跨周期才处理旧回调时丢弃；网页只用同一系统时钟呈现，不生成验证码。
    if (Math.floor(wall / 30000) !== Math.floor(current.requestWall / 30000)) {
      result.code = '';
      current.text.textContent = '';
      requestRecordTotp(current);
      return;
    }
    const ttl = Math.min(result.remainingSeconds * 1000, 30000 - (wall % 30000));
    if (current.transientId) window.pdmSensitiveDom.clearTransient(current.transientId, 'navigation');
    current.transientId = window.pdmSensitiveDom.bindTransient('TOTP', Math.max(1, Math.floor(ttl)), [current.text]);
    current.text.textContent = `${result.code.slice(0, 3)} ${result.code.slice(3)}`;
    result.code = '';
    current.deadline = performance.now() + ttl;
    const remaining = Math.ceil(ttl / 1000);
    current.ring.classList.toggle('urgent', remaining <= 5);
    current.ring.title = fixedText(`剩余 ${remaining} 秒`, `${remaining} seconds remaining`);
    current.ring.querySelector('.fg').setAttribute('stroke-dashoffset', String(62.83 * (1 - remaining / 30)));
  }

  function copyRecordTotp(record) {
    if (!runtime.bridge || runtime.state !== 'UNLOCKED' || runtime.pendingTotpCopy ||
        runtime.selectedRecordId !== record.recordId || runtime.selectedRevision !== record.revision) return;
    const id = requestId();
    runtime.pendingTotpCopy = id;
    runtime.pendingTotpCopyTarget = {recordId: record.recordId, revision: record.revision};
    runtime.bridge.copyRecordTotpV1(id, runtime.pageEpoch, runtime.sessionEpoch, record.recordId, record.revision,
      (ack) => {
        if (runtime.pendingTotpCopy === id && (!ack || ack.accepted !== true)) {
          runtime.pendingTotpCopy = '';
          runtime.pendingTotpCopyTarget = null;
          handleRecordActionError(ack?.errorCode || 'INTERNAL_FAILURE');
        }
      });
  }

  function onRecordTotpCopied(request, page, session, errorCode, _argument, _retry, result) {
    const target = runtime.pendingTotpCopyTarget;
    if (request !== runtime.pendingTotpCopy || !target || target.recordId !== runtime.selectedRecordId ||
        target.revision !== runtime.selectedRevision) return;
    onRecordCopied('pendingTotpCopy', 'TOTP', 'vault.detail.totp', request, page, session, errorCode, result);
    runtime.pendingTotpCopyTarget = null;
  }

  function cancelTotpCopy() {
    const pending = runtime.pendingTotpCopy;
    runtime.pendingTotpCopy = '';
    runtime.pendingTotpCopyTarget = null;
    if (pending && runtime.bridge && runtime.ready) {
      runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, pending, () => {});
    }
  }

  function recoveryTargetCurrent(target) {
    return target && runtime.state === 'UNLOCKED' && runtime.ready &&
      state.currentNav === 'vault' && !document.hidden &&
      runtime.pageEpoch === target.page && runtime.sessionEpoch === target.session &&
      runtime.selectedRecordId === target.recordId && runtime.selectedRevision === target.revision &&
      runtime.selectedDetails?.recoveryUsed.length > target.index;
  }

  function clearRecoveryReveal(reason = 'manual_hide') {
    const pending = runtime.pendingRecoveryReveal;
    runtime.pendingRecoveryReveal = '';
    runtime.recoveryRevealTarget = null;
    if (pending && runtime.bridge && runtime.ready) {
      runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, pending, () => {});
    }
    const active = runtime.activeRecoveryReveal;
    runtime.activeRecoveryReveal = null;
    if (!active) return;
    window.pdmSensitiveDom?.clearLease(active.leaseId, reason);
    if (active.text.isConnected) {
      active.text.textContent = '••••••••';
      active.text.setAttribute('aria-label', fixedText(`第 ${active.index + 1} 条恢复码，已遮掩`, `Recovery code ${active.index + 1}, hidden`));
    }
    if (active.button.isConnected) {
      active.button.replaceChildren();
      appendStaticIcon(active.button, 'eye', 15);
      const label = fixedText('查看恢复码', 'Show recovery code');
      active.button.title = label;
      active.button.setAttribute('aria-label', label);
      active.button.setAttribute('aria-pressed', 'false');
    }
    if (runtime.bridge && runtime.ready && runtime.state === 'UNLOCKED') {
      runtime.bridge.releaseSecretLeaseV1(requestId(), runtime.pageEpoch, active.leaseId, () => {});
    }
  }

  function clearRecoveryActions(reason = 'navigation') {
    clearRecoveryReveal(reason);
    for (const field of ['pendingRecoveryCopy', 'pendingRecoveryMark']) {
      const pending = runtime[field];
      runtime[field] = '';
      if (pending && runtime.bridge && runtime.ready) {
        runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, pending, () => {});
      }
    }
    runtime.recoveryCopyTarget = null;
    runtime.recoveryMarkTarget = null;
  }

  function toggleRecoveryReveal(record, index, text, button) {
    const active = runtime.activeRecoveryReveal;
    if (active?.recordId === record.recordId && active.revision === record.revision && active.index === index) {
      clearRecoveryReveal();
      return;
    }
    if (!runtime.bridge || runtime.pendingRecoveryReveal || !text.isConnected || !button.isConnected ||
        !recoveryTargetCurrent({recordId: record.recordId, revision: record.revision, index,
          page: runtime.pageEpoch, session: runtime.sessionEpoch})) return;
    clearRecoveryReveal('navigation');
    const id = requestId();
    const target = {recordId: record.recordId, revision: record.revision, index, text, button,
      page: runtime.pageEpoch, session: runtime.sessionEpoch};
    runtime.pendingRecoveryReveal = id;
    runtime.recoveryRevealTarget = target;
    runtime.bridge.revealRecoveryCodeV1(id, target.page, target.session, target.recordId, target.revision, index,
      (ack) => {
        if (runtime.pendingRecoveryReveal !== id || (ack?.accepted === true && ack.errorCode === 'OK')) return;
        runtime.pendingRecoveryReveal = '';
        runtime.recoveryRevealTarget = null;
        handleRecordActionError(ack?.errorCode || 'INTERNAL_FAILURE');
      });
  }

  function onRecoveryCodeRevealed(request, page, session, errorCode, _argument, _retry, result) {
    const target = runtime.recoveryRevealTarget;
    if (request !== runtime.pendingRecoveryReveal || !recoveryTargetCurrent(target) ||
        target.page !== page || target.session !== session || !target.text.isConnected || !target.button.isConnected) {
      releaseReturnedLease(result);
      return;
    }
    runtime.pendingRecoveryReveal = '';
    runtime.recoveryRevealTarget = null;
    if (errorCode !== 'OK') {
      releaseReturnedLease(result);
      handleRecordActionError(errorCode);
      return;
    }
    const lease = normalizeSecretLease(result);
    if (!lease || !lease.value || lease.longFields.length) {
      releaseReturnedLease(result);
      handleRecordActionError('INTERNAL_FAILURE');
      return;
    }
    try {
      window.pdmSensitiveDom.bindLease(lease.secretLeaseId, 'REVEAL', lease.expiresInMs, [target.text], false);
      target.text.textContent = lease.value;
      target.text.setAttribute('aria-label', fixedText(`第 ${target.index + 1} 条恢复码，已显示`, `Recovery code ${target.index + 1}, visible`));
      target.button.replaceChildren();
      appendStaticIcon(target.button, 'eye-closed', 15);
      const label = fixedText('隐藏恢复码', 'Hide recovery code');
      target.button.title = label;
      target.button.setAttribute('aria-label', label);
      target.button.setAttribute('aria-pressed', 'true');
      runtime.activeRecoveryReveal = {...target, leaseId: lease.secretLeaseId};
    } catch (_error) {
      releaseReturnedLease(result);
      target.text.textContent = '••••••••';
      handleRecordActionError('INTERNAL_FAILURE');
    } finally {
      lease.value = '';
      if (result && typeof result === 'object') result.value = '';
    }
  }

  function copyRecoveryCode(record, index) {
    if (!runtime.bridge || runtime.pendingRecoveryCopy || !recoveryTargetCurrent({
      recordId: record.recordId, revision: record.revision, index,
      page: runtime.pageEpoch, session: runtime.sessionEpoch,
    })) return;
    const id = requestId();
    runtime.pendingRecoveryCopy = id;
    runtime.recoveryCopyTarget = {recordId: record.recordId, revision: record.revision, index};
    runtime.bridge.copyRecoveryCodeV1(id, runtime.pageEpoch, runtime.sessionEpoch, record.recordId, record.revision, index,
      (ack) => {
        if (runtime.pendingRecoveryCopy !== id || (ack?.accepted === true && ack.errorCode === 'OK')) return;
        runtime.pendingRecoveryCopy = '';
        runtime.recoveryCopyTarget = null;
        handleRecordActionError(ack?.errorCode || 'INTERNAL_FAILURE');
      });
  }

  function onRecoveryCodeCopied(request, page, session, errorCode, _argument, _retry, result) {
    const target = runtime.recoveryCopyTarget;
    if (request !== runtime.pendingRecoveryCopy || !recoveryTargetCurrent({...target, page, session})) return;
    runtime.recoveryCopyTarget = null;
    onRecordCopied('pendingRecoveryCopy', 'RECOVERY_CODE', 'vault.detail.recovery',
      request, page, session, errorCode, result);
  }

  function recoveryFollowSurface(intent) {
    if (intent.view === 'SPLIT') {
      const scroller = byId('split-list');
      return [scroller, scroller?.querySelector('.split-item.active')];
    }
    const detail = document.querySelector(
      `#view-list .list-item[data-id="${intent.recordId}"] > .item-detail`
    );
    return [document.querySelector('.content'),
      detail?.querySelector('.recovery-code-list')?.children[intent.index]];
  }

  function recoveryFollowCurrent(intent) {
    return intent && runtime.state === 'UNLOCKED' && runtime.ready && !document.hidden &&
      state.currentNav === 'vault' && runtime.pageEpoch === intent.page &&
      runtime.sessionEpoch === intent.session && runtime.vaultView === intent.view &&
      runtime.vaultQuery === intent.query && runtime.vaultFilter === intent.filter &&
      runtime.vaultSort === intent.sort && runtime.selectedRecordId === intent.recordId &&
      runtime.selectedRevision === intent.revision &&
      runtime.selectedDetails?.revision === intent.revision &&
      (intent.view === 'SPLIT' ? state.splitSelectedId : state.expandedId) === intent.recordId;
  }

  function recoveryFollowVisible(intent) {
    const [scroller, target] = recoveryFollowSurface(intent);
    if (!scroller?.isConnected || !target?.isConnected) return false;
    const bounds = scroller.getBoundingClientRect();
    const row = target.getBoundingClientRect();
    return row.bottom > bounds.top && row.top < bounds.bottom;
  }

  function restoreRecoveryFollow(intent) {
    if (!recoveryFollowCurrent(intent)) return;
    const [scroller, codeRow] = recoveryFollowSurface(intent);
    if (!scroller?.isConnected || !codeRow?.isConnected) return;
    let target = codeRow;
    if (intent.view === 'LIST') {
      const card = document.querySelector(`#view-list .list-item[data-id="${intent.recordId}"]`);
      if (card?.isConnected) {
        const cardBounds = card.getBoundingClientRect();
        if (cardBounds.bottom - cardBounds.top <= scroller.clientHeight) target = card;
      }
    }
    const bounds = scroller.getBoundingClientRect();
    const row = target.getBoundingClientRect();
    const top = bounds.top + scroller.clientTop;
    const bottom = top + scroller.clientHeight;
    if (row.top >= top && row.bottom <= bottom) return;
    scroller.scrollTop += row.top < top ? row.top - top : row.bottom - bottom;
  }

  function setRecoveryCodeUsed(record, index, used, button) {
    if (!runtime.bridge || runtime.pendingRecoveryMark || !recoveryTargetCurrent({
      recordId: record.recordId, revision: record.revision, index,
      page: runtime.pageEpoch, session: runtime.sessionEpoch,
    }) || !button?.isConnected) return;
    const id = requestId();
    runtime.pendingRecoveryMark = id;
    runtime.recoveryMarkTarget = {recordId: record.recordId, revision: record.revision, index, used, button};
    runtime.bridge.setRecoveryCodeUsedV1(id, runtime.pageEpoch, runtime.sessionEpoch,
      record.recordId, record.revision, index, used, (ack) => {
        if (runtime.pendingRecoveryMark !== id || (ack?.accepted === true && ack.errorCode === 'OK')) return;
        runtime.pendingRecoveryMark = '';
        runtime.recoveryMarkTarget = null;
        handleRecordActionError(ack?.errorCode || 'INTERNAL_FAILURE');
      });
  }

  function onRecoveryCodeUsed(request, page, session, errorCode, _argument, _retry, result) {
    const target = runtime.recoveryMarkTarget;
    if (request !== runtime.pendingRecoveryMark) {
      scrubRecordWriteResult(result);
      return;
    }
    if (!recoveryTargetCurrent({...target, page, session})) {
      runtime.pendingRecoveryMark = '';
      runtime.recoveryMarkTarget = null;
      if (runtime.state === 'UNLOCKED' && page === runtime.pageEpoch && session === runtime.sessionEpoch) {
        runtime.ratingVaultDirty = true;
        queueRatingRefresh();
      }
      scrubRecordWriteResult(result);
      return;
    }
    runtime.pendingRecoveryMark = '';
    runtime.recoveryMarkTarget = null;
    if (errorCode !== 'OK') {
      scrubRecordWriteResult(result);
      handleRecordActionError(errorCode);
      return;
    }
    const item = normalizeRecordWriteItem(result?.item);
    if (!item || item.recordId !== target.recordId || !isRevision(result.vaultRevision) ||
        !isRevision(result.healthRevision) || item.revision === target.revision ||
        item.favorite !== runtime.selectedDetails?.favorite) {
      scrubRecordWriteResult(result);
      handleRecordActionError('INTERNAL_FAILURE');
      return;
    }
    const details = runtime.selectedDetails;
    const usage = [...details.recoveryUsed];
    usage[target.index] = target.used;
    const nextDetails = Object.freeze({...details, revision: item.revision,
      recoveryUsed: Object.freeze(usage)});
    const detail = runtime.vaultView === 'SPLIT' ? byId('split-detail') :
      document.querySelector(`#view-list .list-item[data-id="${target.recordId}"] > .item-detail`);
    const interruptedReads = Array.from(detail?.querySelectorAll?.(
      '.detail-value.pdm-complete-field .btn-sm[aria-busy="true"]'
    ) || []);
    const follow = {recordId: item.recordId, index: target.index, revision: item.revision,
      page: runtime.pageEpoch, session: runtime.sessionEpoch, view: runtime.vaultView,
      query: runtime.vaultQuery, filter: runtime.vaultFilter, sort: runtime.vaultSort};
    const wasVisible = recoveryFollowVisible(follow);
    releaseActiveReveal('navigation');
    clearRecoveryActions('navigation');
    stopRecordTotp();
    cancelTotpCopy();
    cancelFieldReads('detail');
    runtime.selectedDetails = nextDetails;
    runtime.selectedRevision = item.revision;
    runtime.vaultItems = runtime.vaultItems.map((summary) => summary.recordId === item.recordId &&
      summary.revision === target.revision ? Object.freeze({...summary, revision: item.revision}) : summary);
    runtime.vaultRevision = result.vaultRevision;
    runtime.healthRevision = result.healthRevision;
    runtime.recoveryInvalidListRequest = runtime.pendingList;
    runtime.recoveryInvalidRatingRequest = runtime.pendingRatingLocation;
    runtime.recoveryFollow = wasVisible && recoveryFollowCurrent(follow) ? follow : null;
    const mark = target.button.isConnected ? target.button : detail?.querySelector(
      `[data-pdm-native-focus-key="vault-action:${target.recordId}:${runtime.vaultView === 'SPLIT' ? 'split-detail' : 'list-detail'}-recovery-${target.index}-mark"]`
    );
    const status = mark?.closest('.recovery-code-item')?.querySelector('.recovery-code-status');
    if (detail && mark && status) {
      detail.pdmSetDetailRecord?.(nextDetails);
      detail.pdmDetailIdentity = currentRecordDetailIdentity(nextDetails, runtime.vaultView === 'SPLIT');
      status.textContent = target.used ? fixedText('已标记已用', 'Marked used') :
        fixedText('未标记已用', 'Not marked used');
      mark.replaceChildren();
      appendStaticIcon(mark, target.used ? 'repeat' : 'check', 15);
      const label = target.used ? fixedText('撤销已用标记', 'Undo used mark') :
        fixedText('标记已用', 'Mark used');
      mark.title = label;
      mark.setAttribute('aria-label', label);
      if (nextDetails.hasTotp && !document.hidden) {
        const totp = detail.querySelector('.detail-value.totp');
        if (totp) startRecordTotp(nextDetails, totp.querySelector('.text'),
          totp.querySelector('.totp-ring'), totp.querySelector('.btn-sm'));
      }
      if (interruptedReads.length) window.queueMicrotask(() => {
        if (detail.pdmDetailIdentity !== currentRecordDetailIdentity(nextDetails,
            runtime.vaultView === 'SPLIT') || document.hidden) return;
        for (const button of interruptedReads) {
          if (button.isConnected) button.pdmActivateLongFieldRead?.();
        }
      });
    }
    runtime.ratingVaultDirty = runtime.ratingHealthDirty = true;
    queueRatingRefresh();
    showFixedToast(target.used ? '已标记已用' : '已撤销已用标记',
      target.used ? 'Marked used' : 'Used mark removed', 'success');
  }

  function selectVaultRecord(summary, splitMode) {
    summary = currentRecordForAction(summary);
    if (runtime.state !== 'UNLOCKED') return;
    if (
      !splitMode &&
      runtime.selectedRecordId === summary.recordId &&
      state.expandedId === summary.recordId
    ) {
      cancelPendingRecordDetails();
      clearSelectedDetails();
      renderM4Vault();
      return;
    }
    const target = Object.freeze({
      recordId: summary.recordId,
      revision: summary.revision,
      splitMode: Boolean(splitMode),
    });
    if (runtime.retiredDetailsRequest) {
      runtime.queuedDetailsTarget = target;
      renderM4Vault();
      return;
    }
    if (runtime.pendingDetails) {
      runtime.queuedDetailsTarget = target;
      runtime.bridge.cancelRequestV1(
        requestId(),
        runtime.pageEpoch,
        runtime.pendingDetails,
        () => {},
      );
      renderM4Vault();
      return;
    }
    requestRecordDetails(summary, splitMode);
  }

  function appendListItem(container, summary, retainedDetail = null) {
    const item = document.createElement('div');
    item.className = 'list-item';
    item.dataset.id = String(summary.recordId);
    const row = document.createElement('div');
    row.className = 'item-summary';
    row.dataset.pdmNativeFocusKey = `vault-list:${summary.recordId}`;
    row.dataset.pdmM4VaultAction = 'true';
    row.setAttribute('role', 'button');
    row.tabIndex = 0;
    appendFavorite(row, summary.favorite, 16, summary);
    const identity = document.createElement('div');
    identity.className = 'item-platform';
    appendPlatformIdentity(
      identity,
      summary.platform,
      summary.accountDisplay,
      summary.duplicateGroup,
      summary.similarGroup,
      summary,
    );
    row.append(identity);
    const meta = document.createElement('div');
    meta.className = 'item-meta';
    appendStrengthMeta(meta, summary);
    const quickActions = document.createElement('div');
    quickActions.className = 'quick-actions';
    quickActions.append(
      createRecordActionButton(
        'user',
        t('vault.copy.account'),
        () => copyRecordField(summary, 'ACCOUNT'),
        'vault.copy.account',
        `vault-action:${summary.recordId}:summary-copy-account`,
      ),
      createRecordActionButton(
        'key',
        t('vault.copy.password'),
        () => copyRecordField(summary, 'PASSWORD'),
        'vault.copy.password',
        `vault-action:${summary.recordId}:summary-copy-password`,
      ),
    );
    meta.append(quickActions);
    const reading = document.createElement('span');
    reading.className = 'pdm-detail-status';
    reading.hidden = true;
    reading.setAttribute('role', 'status');
    setRuntimeText(reading, '', '读取中…', 'Loading…');
    meta.append(reading);
    const chevron = document.createElement('span');
    chevron.className = 'chevron';
    chevron.textContent = '▼';
    meta.append(chevron);
    row.append(meta);
    const activate = () => selectVaultRecord(summary, false);
    let namePointerGesture = false;
    row.addEventListener('pointerdown', (event) => {
      namePointerGesture = Boolean(
        event.target?.closest?.('.platform-name-text'),
      );
    }, true);
    row.addEventListener('pointerup', () => {
      window.setTimeout(() => {
        namePointerGesture = false;
      }, 0);
    }, true);
    row.addEventListener('pointercancel', () => {
      namePointerGesture = false;
    }, true);
    row.addEventListener('click', (event) => {
      if (
        namePointerGesture ||
        event.target?.closest?.('.platform-name-text')
      ) {
        return;
      }
      activate();
    });
    row.addEventListener('keydown', (event) => {
      if (event.target !== row && event.target?.closest?.('button,input,textarea')) return;
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      activate();
    });
    item.append(row);
    const detail = (state.expandedId === summary.recordId && retainedDetail) || document.createElement('div');
    detail.className = 'item-detail';
    detail.id = `vault-detail-${summary.recordId}`;
    row.setAttribute('aria-controls', detail.id);
    renderListItemDetail(detail, summary);
    item.append(detail);
    container.append(item);
    updateListItemDisclosure(item, summary.recordId);
  }

  function updateListItemDisclosure(item, recordId) {
    if (!item) return;
    const requested = state.expandedId === recordId;
    const pendingTarget = runtime.queuedDetailsTarget || runtime.pendingDetailsTarget;
    const detail = item.querySelector(':scope > .item-detail');
    const expanded = requested && detail?.dataset.pdmDetailReady === 'true';
    const pending = Boolean(
      pendingTarget &&
      pendingTarget.splitMode === false &&
      pendingTarget.recordId === recordId,
    );
    if (detail) detail.hidden = !expanded;
    item.classList.toggle('expanded', expanded);
    item.classList.toggle('pdm-detail-pending', pending);
    const row = item.querySelector(':scope > .item-summary');
    row.setAttribute('aria-expanded', String(expanded));
    row.setAttribute('aria-busy', String(pending));
    row.querySelector('.pdm-detail-status').hidden = !pending;
  }

  function renderListItemDetail(detail, summary) {
    if (state.expandedId === summary.recordId) {
      if (
        runtime.selectedDetails &&
        runtime.selectedDetails.recordId === summary.recordId
      ) {
        appendRecordDetails(detail, runtime.selectedDetails);
      } else {
        detail.replaceChildren();
        detail.pdmDetailIdentity = '';
        delete detail.pdmSetDetailRecord;
        delete detail.dataset.pdmDetailReady;
      }
    } else {
      detail.replaceChildren();
      detail.pdmDetailIdentity = '';
      delete detail.pdmSetDetailRecord;
      delete detail.dataset.pdmDetailReady;
    }
  }

  function appendPager(container) {
    if (
      !runtime.vaultCursorHistory.length &&
      !runtime.vaultNextCursor
    ) {
      return;
    }
    const pager = document.createElement('div');
    pager.className = 'detail-footer';
    const label = document.createElement('span');
    label.className = 'detail-time';
    label.dataset.pdmPagerTotal = String(runtime.vaultTotal);
    label.textContent = fixedText(
      `共 ${runtime.vaultTotal} 条`,
      `${runtime.vaultTotal} records`,
    );
    const actions = document.createElement('div');
    actions.className = 'detail-buttons';
    const previous = document.createElement('button');
    previous.className = 'btn btn-sm';
    previous.type = 'button';
    previous.dataset.pdmPagerDirection = 'previous';
    previous.dataset.pdmNativeFocusKey = 'vault-page:previous';
    previous.textContent = fixedText('上一页', 'Previous');
    previous.disabled = runtime.vaultCursorHistory.length === 0;
    if (!previous.disabled) {
      previous.dataset.pdmM4VaultAction = 'true';
    }
    previous.addEventListener('click', loadPreviousVaultPage);
    const next = document.createElement('button');
    next.className = 'btn btn-sm';
    next.type = 'button';
    next.dataset.pdmPagerDirection = 'next';
    next.dataset.pdmNativeFocusKey = 'vault-page:next';
    next.textContent = fixedText('下一页', 'Next');
    next.disabled = !runtime.vaultNextCursor;
    if (!next.disabled) {
      next.dataset.pdmM4VaultAction = 'true';
    }
    next.addEventListener('click', loadNextVaultPage);
    actions.append(previous, next);
    pager.append(label, actions);
    container.append(pager);
  }

  function ensureSplitContainers() {
    const split = byId('view-split');
    if (!split) return null;
    let list = byId('split-list');
    let detail = byId('split-detail');
    if (!list || !detail) {
      split.replaceChildren();
      list = document.createElement('div');
      list.className = 'split-list';
      list.id = 'split-list';
      detail = document.createElement('div');
      detail.className = 'split-detail';
      detail.id = 'split-detail';
      split.append(list, detail);
    }
    return {split, list, detail};
  }

  function renderM4ListView() {
    const list = byId('view-list');
    const splitParts = ensureSplitContainers();
    if (!list || !splitParts) return;
    if (runtime.vaultView !== 'LIST') {
      list.style.display = 'none';
      return;
    }
    list.style.display = 'flex';
    splitParts.split.style.setProperty('display', 'none', 'important');
    const rowsIdentity = currentVaultRowsIdentity();
    const previousRows = Array.from(list.querySelectorAll(':scope > .list-item'));
    const reuseRows = runtime.vaultItems.length > 0 && list.pdmRowsIdentity === rowsIdentity &&
      previousRows.length === runtime.vaultItems.length;
    const previousDetail = list.querySelector('.list-item.expanded > .item-detail');
    const identity = currentRecordDetailIdentity(runtime.selectedDetails);
    const retainedDetail = identity && previousDetail?.pdmDetailIdentity === identity ? previousDetail : null;
    if (!reuseRows) {
      delete list.pdmRowsIdentity;
      list.replaceChildren();
    }
    if (runtime.pendingList && runtime.vaultItems.length === 0) {
      appendEmptyState(
        list,
        fixedText('正在读取密码库…', 'Loading vault…'),
        'database',
        '',
        '正在读取密码库…',
        'Loading vault…',
      );
      return;
    }
    if (runtime.vaultItems.length === 0) {
      appendEmptyState(list, t('vault.empty'), 'search', 'vault.empty');
      return;
    }
    for (const [index, summary] of runtime.vaultItems.entries()) {
      if (reuseRows) {
        const item = previousRows[index];
        const expanded = state.expandedId === summary.recordId;
        const pendingTarget = runtime.queuedDetailsTarget || runtime.pendingDetailsTarget;
        const pending = Boolean(
          pendingTarget && !pendingTarget.splitMode && pendingTarget.recordId === summary.recordId,
        );
        if (!expanded && !pending && !item.classList.contains('expanded') &&
            !item.classList.contains('pdm-detail-pending')) continue;
        renderListItemDetail(item.querySelector('.item-detail'), summary);
        updateListItemDisclosure(item, summary.recordId);
      } else {
        appendListItem(list, summary, retainedDetail);
      }
    }
    if (!reuseRows) appendPager(list);
    list.pdmRowsIdentity = rowsIdentity;
  }

  function currentVaultRowsIdentity() {
    // 与详情复用一样按不可变 ID/版本匹配；只保留非正文元数据，不缓存账号或名称。
    return JSON.stringify([
      runtime.pageEpoch, runtime.sessionEpoch, state.lang, runtime.vaultTotal,
      runtime.vaultNextCursor, runtime.vaultCursorHistory.length,
      runtime.vaultItems.map((item) => [item.recordId, item.revision, item.favorite,
        item.strength, item.duplicateGroup, item.similarGroup, item.hasTotp, item.longFields]),
    ]);
  }

  function renderM4SplitView() {
    const listView = byId('view-list');
    const splitParts = ensureSplitContainers();
    if (!listView || !splitParts) return;
    if (runtime.vaultView !== 'SPLIT') {
      splitParts.split.style.setProperty('display', 'none', 'important');
      return;
    }
    listView.style.display = 'none';
    splitParts.split.style.setProperty('display', 'grid', 'important');
    const {list, detail} = splitParts;
    const pendingTarget = runtime.queuedDetailsTarget || runtime.pendingDetailsTarget;
    const rowsIdentity = currentVaultRowsIdentity();
    const previousRows = Array.from(list.querySelectorAll(':scope > .split-item'));
    const reuseRows = runtime.vaultItems.length > 0 && list.pdmRowsIdentity === rowsIdentity &&
      previousRows.length === runtime.vaultItems.length;
    if (!reuseRows) {
      delete list.pdmRowsIdentity;
      list.replaceChildren();
    }
    const identity = currentRecordDetailIdentity(runtime.selectedDetails, true);
    if (!identity || detail.pdmDetailIdentity !== identity) {
      detail.replaceChildren();
      detail.pdmDetailIdentity = '';
      delete detail.pdmSetDetailRecord;
    }
    if (runtime.pendingList && runtime.vaultItems.length === 0) {
      appendEmptyState(
        list,
        fixedText('正在读取密码库…', 'Loading vault…'),
        'database',
        '',
        '正在读取密码库…',
        'Loading vault…',
      );
      return;
    }
    if (runtime.vaultItems.length === 0) {
      appendEmptyState(list, t('vault.empty'), 'search', 'vault.empty');
      return;
    }
    for (const [index, summary] of runtime.vaultItems.entries()) {
      if (reuseRows) {
        const selected = state.splitSelectedId === summary.recordId;
        previousRows[index].classList.toggle('active', selected);
        previousRows[index].setAttribute('aria-pressed', String(selected));
        previousRows[index].classList.toggle(
          'pdm-detail-pending',
          Boolean(pendingTarget?.splitMode && pendingTarget.recordId === summary.recordId),
        );
        continue;
      }
      const item = document.createElement('div');
      item.className = [
        'split-item',
        state.splitSelectedId === summary.recordId ? 'active' : '',
        pendingTarget?.splitMode && pendingTarget.recordId === summary.recordId
          ? 'pdm-detail-pending'
          : '',
      ].filter(Boolean).join(' ');
      item.dataset.pdmNativeFocusKey = `vault-split:${summary.recordId}`;
      item.dataset.pdmM4VaultAction = 'true';
      item.setAttribute('role', 'button');
      item.setAttribute('aria-pressed', String(state.splitSelectedId === summary.recordId));
      item.tabIndex = 0;
      appendFavorite(item, summary.favorite, 14, summary);
      const icon = document.createElement('div');
      icon.className = (
        `platform-icon ${platformColorClass(summary.platform)}`
      );
      icon.textContent = (
        summary.platform.trim().slice(0, 1).toUpperCase() || '?'
      );
      const name = document.createElement('div');
      name.className = 'split-name';
      const nameText = document.createElement('span');
      nameText.className = 'split-name-text';
      nameText.textContent = summary.platform;
      name.append(nameText);
      appendFullNameAction(name, summary);
      if (summary.duplicateGroup > 0) {
        const duplicate = document.createElement('span');
        duplicate.className = 'dup-tag';
        duplicate.dataset.pdmDuplicateGroup = String(summary.duplicateGroup);
        duplicate.textContent = `${t('vault.dup.tag')}${summary.duplicateGroup}`;
        name.append(duplicate);
      }
      if (summary.similarGroup > 0) {
        const similar = document.createElement('span');
        similar.className = 'similar-tag';
        similar.dataset.pdmSimilarGroup = String(summary.similarGroup);
        similar.textContent = `${t('vault.similar.tag')}${summary.similarGroup}`;
        name.append(similar);
      }
      const dot = document.createElement('span');
      dot.className = (
        `strength-dot strength-${summary.strength.toLowerCase()}`
      );
      item.append(icon, name, dot);
      if (['PENDING', 'CHECKING', 'FAILED'].includes(summary.strength)) {
        dot.setAttribute('aria-label', t('common.strength.' + summary.strength.toLowerCase()));
        dot.title = t('common.strength.' + summary.strength.toLowerCase());
        const status = document.createElement('span');
        status.className = 'split-strength-status';
        status.textContent = dot.title;
        name.append(status);
        renderStrengthRetry(name, summary);
      }
      const activate = () => selectVaultRecord(summary, true);
      let namePointerGesture = false;
      item.addEventListener('pointerdown', (event) => {
        namePointerGesture = Boolean(
          event.target?.closest?.('.split-name-text'),
        );
      }, true);
      item.addEventListener('pointerup', () => {
        window.setTimeout(() => {
          namePointerGesture = false;
        }, 0);
      }, true);
      item.addEventListener('pointercancel', () => {
        namePointerGesture = false;
      }, true);
      item.addEventListener('click', (event) => {
        if (
          namePointerGesture ||
          event.target?.closest?.('.split-name-text')
        ) {
          return;
        }
        activate();
      });
      item.addEventListener('keydown', (event) => {
        if (event.target !== item && event.target?.closest?.('button,input,textarea')) return;
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        activate();
      });
      list.append(item);
    }
    if (!reuseRows) appendPager(list);
    list.pdmRowsIdentity = rowsIdentity;
    if (
      runtime.selectedDetails &&
      runtime.selectedDetails.recordId === state.splitSelectedId
    ) {
      appendRecordDetails(detail, runtime.selectedDetails, true);
    } else if (pendingTarget?.splitMode) {
      appendEmptyState(
        detail,
        fixedText('正在读取记录详情…', 'Loading record details…'),
        'database',
        '',
        '正在读取记录详情…',
        'Loading record details…',
        'split-detail-empty',
      );
    } else {
      appendEmptyState(
        detail,
        t('vault.split.empty'),
        'arrow-left',
        'vault.split.empty',
        '',
        '',
        'split-detail-empty',
      );
    }
  }

  function renderM4VaultBody() {
    if (runtime.activeReveal) {
      releaseActiveReveal('navigation');
    }
    if (runtime.state !== 'UNLOCKED') {
      renderDemoVault();
      return;
    }
    const counts = runtime.vaultCounts;
    const countAll = byId('count-all');
    const countFavorite = byId('count-fav');
    const countWeak = byId('count-weak');
    const countDuplicate = byId('count-dup');
    const countSimilar = byId('count-similar');
    if (countAll) countAll.textContent = String(counts.all);
    if (countFavorite) countFavorite.textContent = String(counts.favorite);
    if (countWeak) countWeak.textContent = String(counts.weak);
    if (countDuplicate) {
      countDuplicate.textContent = String(counts.duplicate);
    }
    if (countSimilar) countSimilar.textContent = String(counts.similar);
    document.querySelectorAll('#filter-chips .chip').forEach((chip) => {
      const active = String(chip.dataset.filter || '').toUpperCase() === runtime.vaultFilter;
      chip.classList.toggle('active', active);
      chip.setAttribute('aria-pressed', String(active));
    });
    document.querySelectorAll('.view-switcher .btn-icon').forEach(
      (button) => {
        const active = String(button.dataset.view || '').toUpperCase() === runtime.vaultView;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      },
    );
    document.querySelectorAll('#sort-menu .sort-option').forEach(
      (option) => {
        option.classList.toggle(
          'active',
          String(option.dataset.value || '').toUpperCase() === (
            runtime.vaultSort
          ),
        );
      },
    );
    const activeSort = document.querySelector(
      `#sort-menu .sort-option[data-value="${runtime.vaultSort.toLowerCase()}"]`,
    );
    const sortLabel = byId('sort-trigger-label');
    const activeText = activeSort?.querySelector('span');
    if (sortLabel && activeText) {
      sortLabel.textContent = activeText.textContent;
      const key = activeText.getAttribute('data-i18n');
      if (key) sortLabel.setAttribute('data-i18n', key);
    }
    renderM4ListView();
    renderM4SplitView();
    if (state.currentNav === 'vault') syncGlobalSearchStatus(runtime.vaultTotal, runtime.vaultQuery);
  }

  function renderM4Vault(fallbackKeys = null) {
    return preserveProductFocus(
      byId('page-vault'),
      renderM4VaultBody,
      fallbackKeys,
    );
  }

  function setHealthIssueCount(container, count, kind) {
    const label = container?.parentElement?.querySelector('.issue-count');
    if (label) {
      const key = kind === 'DUPLICATE'
        ? 'security.count.group'
        : 'security.count.items';
      label.textContent = t(key).replace('{n}', String(count));
    }
  }

  function appendHealthPager(container, kind, page) {
    if (!page.nextCursor && page.pageIndex === 0) return;
    const pager = document.createElement('div');
    pager.className = 'note-pagination';
    const previous = document.createElement('button');
    previous.type = 'button'; previous.className = 'btn btn-sm';
    previous.dataset.pdmM4HealthAction = 'true';
    previous.dataset.pdmM4HealthKind = kind;
    previous.dataset.pdmM4HealthPager = 'previous';
    previous.dataset.pdmNativeFocusKey = `health:${kind}:previous`;
    previous.textContent = fixedText('上一页', 'Previous');
    previous.disabled = page.pageIndex === 0;
    previous.addEventListener('click', () => changeHealthPage(kind, false));
    const next = document.createElement('button');
    next.type = 'button'; next.className = 'btn btn-sm';
    next.dataset.pdmM4HealthAction = 'true';
    next.dataset.pdmM4HealthKind = kind;
    next.dataset.pdmM4HealthPager = 'next';
    next.dataset.pdmNativeFocusKey = `health:${kind}:next`;
    next.textContent = fixedText('下一页', 'Next');
    next.disabled = !page.nextCursor;
    next.addEventListener('click', () => changeHealthPage(kind, true));
    pager.append(previous, next);
    container.append(pager);
  }

  function appendHealthItem(container, item, kind) {
    const row = document.createElement('div');
    row.className = 'issue-row';
    const icon = document.createElement('div');
    icon.className = kind === 'STALE'
      ? 'platform-icon pdm-inline-cc1dfa662a'
      : `platform-icon ${platformColorClass(item.platform)}`;
    icon.innerHTML = kind === 'STALE'
      ? '<svg class="svg-fill" width="14" height="14" viewBox="0 0 256 256" aria-hidden="true"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm56,112H128a8,8,0,0,1-8-8V72a8,8,0,0,1,16,0v48h48a8,8,0,0,1,0,16Z"/></svg>'
      : platformIcon(item.platform);
    const info = document.createElement('div');
    info.className = 'info';
    const name = document.createElement('div');
    name.className = 'name'; name.textContent = item.platform;
    const desc = document.createElement('div');
    desc.className = 'desc';
    if (kind === 'STALE') {
      name.textContent += ` · ${t('security.name.stale').replace('{n}', String(item.daysSinceChange))}`;
      desc.textContent = t('security.desc.stale').replace(
        '{n}',
        String(runtime.settings?.staleDays || 180),
      );
    } else {
      desc.textContent = t('security.desc.weak');
    }
    const action = document.createElement('button');
    action.type = 'button'; action.className = 'btn btn-ghost btn-sm';
    action.dataset.pdmM4HealthAction = 'true';
    action.dataset.pdmNativeFocusKey = `health:${kind}:${item.recordId}`;
    action.textContent = t('security.button.fix');
    action.addEventListener('click', () => openHealthRecord(item, kind));
    info.append(name, desc); row.append(icon, info, action); container.append(row);
  }

  function appendHealthGroup(container, group) {
    const row = document.createElement('div');
    row.className = 'issue-row';
    const icon = document.createElement('div');
    icon.className = 'platform-icon pdm-inline-7e2d119a49';
    icon.innerHTML = '<svg class="svg-fill" width="14" height="14" viewBox="0 0 256 256" aria-hidden="true"><path d="M224,48V96a8,8,0,0,1-8,8H168a8,8,0,0,1-5.66-13.66L180.65,72a79.48,79.48,0,0,0-54.72-22.09h-.45A79.52,79.52,0,0,0,69.59,72.71,8,8,0,0,1,58.41,61.27,96,96,0,0,1,192,60.7l18.36-18.36A8,8,0,0,1,224,48ZM186.41,183.29A80,80,0,0,1,75.35,184l18.31-18.31A8,8,0,0,0,88,152H40a8,8,0,0,0-8,8v48a8,8,0,0,0,13.66,5.66L64,195.3a95.42,95.42,0,0,0,66,26.76h.53a95.36,95.36,0,0,0,67.07-27.33,8,8,0,0,0-11.18-11.44Z"/></svg>';
    const info = document.createElement('div');
    info.className = 'info';
    const name = document.createElement('div');
    name.className = 'name';
    const connector = t('security.dup.join');
    const more = group.memberCount - group.members.length;
    name.textContent = group.members.map((member) => member.platform).join(connector) +
      (more > 0 ? fixedText(` 等 ${more} 项`, ` and ${more} more`) : '') +
      ` ${t('security.desc.dupName')}`;
    const desc = document.createElement('div');
    desc.className = 'desc';
    desc.textContent = t('security.desc.dup') + (
      more > 0
        ? ` · ${fixedText(`共 ${group.memberCount} 条记录`, `${group.memberCount} records total`)}`
        : ''
    );
    const action = document.createElement('button');
    action.type = 'button'; action.className = 'btn btn-ghost btn-sm'; action.textContent = t('security.button.view');
    action.dataset.pdmM4HealthAction = 'true';
    action.dataset.pdmNativeFocusKey = `health:DUPLICATE:${group.duplicateGroup}`;
    action.addEventListener('click', () => openDuplicateHealthGroup());
    info.append(name, desc); row.append(icon, info, action); container.append(row);
  }

  function renderM4HealthCard(kind, id) {
    const container = byId(id);
    if (!container) return;
    const page = healthPage(kind);
    container.replaceChildren();
    setHealthIssueCount(container, page.total, kind);
    if (runtime.pendingHealthIssues[kind]) {
      appendHealthCardMessage(container, fixedText('正在读取安全问题…', 'Loading security issues…'));
      return;
    }
    if (page.error) {
      appendHealthCardMessage(container, errorText(page.error));
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'btn btn-sm';
      retry.dataset.pdmM4HealthAction = 'true';
      retry.dataset.pdmM4HealthKind = kind;
      retry.dataset.pdmNativeFocusKey = `health:${kind}:retry`;
      retry.textContent = fixedText('重新读取', 'Reload');
      retry.addEventListener('click', () => requestHealthPageRecovery(kind));
      container.append(retry);
      return;
    }
    if (runtime.healthError) {
      appendHealthCardMessage(container, errorText(runtime.healthError));
      return;
    }
    if (kind === 'DUPLICATE') page.groups.forEach((group) => appendHealthGroup(container, group));
    else page.items.forEach((item) => appendHealthItem(container, item, kind));
    if (page.total === 0) {
      appendHealthCardMessage(container, t({
        WEAK: 'security.empty.weak',
        DUPLICATE: 'security.empty.dup',
        STALE: 'security.empty.stale',
      }[kind]));
    }
    appendHealthPager(container, kind, page);
  }

  function appendHealthCardMessage(container, text) {
    const message = document.createElement('div');
    message.className = 'pdm-inline-8008da88de';
    message.textContent = text;
    container.replaceChildren(message);
  }

  function setHealthCardBusy(kind, busy) {
    const id = {
      WEAK: 'weak-issues',
      DUPLICATE: 'dup-issues',
      STALE: 'stale-issues',
    }[kind];
    const container = byId(id);
    if (!container) return;
    if (busy) {
      const height = Math.ceil(container.getBoundingClientRect().height);
      const retained = Number.parseFloat(container.style.minHeight) || 0;
      if (height > retained) container.style.minHeight = `${height}px`;
      container.classList.add('pdm-health-page-stable');
    }
    container.setAttribute('aria-busy', busy ? 'true' : 'false');
  }

  function renderM4HealthBody() {
    if (runtime.state !== 'UNLOCKED') return;
    renderM4HealthRescan();
    const summary = runtime.healthSummary;
    const score = document.querySelector('#page-security .score-num');
    const grade = document.querySelector('#page-security .hero-grade');
    const title = document.querySelector('#page-security .hero-info h2');
    const desc = document.querySelector('#page-security .hero-info p');
    const progress = document.querySelector('#page-security .score-ring .progress');
    const firstStop = document.querySelector('#page-security #scoreGrad stop:first-child');
    const lastStop = document.querySelector('#page-security #scoreGrad stop:last-child');
    if (!summary) {
      if (score) score.textContent = runtime.healthError ? '--' : '…';
      if (grade) grade.textContent = runtime.healthError ? fixedText('读取失败', 'Unavailable') : fixedText('加载中', 'Loading');
      if (title) {
        title.textContent = runtime.healthError
          ? fixedText('暂时无法读取安全体检', 'Unable to load security check')
          : fixedText('正在读取安全体检', 'Loading security check');
      }
      if (desc) desc.textContent = runtime.healthError ? errorText(runtime.healthError) : '';
      if (progress) progress.setAttribute('stroke-dashoffset', '377');
      if (firstStop) firstStop.setAttribute('stop-color', '#cbd5e1');
      if (lastStop) lastStop.setAttribute('stop-color', '#cbd5e1');
      if (grade) { grade.style.color = 'var(--text-weak)'; grade.style.background = 'rgba(203,213,225,.15)'; }
    } else if (summary.hasRecords && summary.scoreAvailable === false) {
      if (score) score.textContent = '--';
      if (grade) {
        grade.textContent = fixedText('待检测', 'Pending');
        grade.style.color = 'var(--text-weak)';
        grade.style.background = 'rgba(203,213,225,.15)';
      }
      if (title) title.textContent = fixedText('密码强度尚未全部检测', 'Password checks are not complete');
      if (desc) desc.textContent = fixedText(
        `有 ${summary.pendingCount} 条待检测，其中 ${summary.failedCount} 条失败；已确认的问题显示在下方。`,
        `${summary.pendingCount} pending, including ${summary.failedCount} failed. Confirmed issues are shown below.`);
      if (progress) progress.setAttribute('stroke-dashoffset', '377');
      if (firstStop) firstStop.setAttribute('stop-color', '#cbd5e1');
      if (lastStop) lastStop.setAttribute('stop-color', '#cbd5e1');
    } else {
      const key = summary.grade.toLowerCase();
      const color = {excellent: 'var(--success)', good: 'var(--accent)', fair: '#f59e0b', risk: '#ef4444', empty: 'var(--text-weak)'}[key];
      const background = {excellent: '40,167,69', good: '124,127,245', fair: '245,158,11', risk: '239,68,68', empty: '203,213,225'}[key];
      if (score) score.textContent = summary.hasRecords ? String(summary.score) : '--';
      if (progress) progress.setAttribute('stroke-dashoffset', String(summary.hasRecords ? 377 * (1 - summary.score / 100) : 377));
      if (firstStop) firstStop.setAttribute('stop-color', color);
      if (lastStop) lastStop.setAttribute('stop-color', summary.hasRecords ? 'var(--accent)' : '#cbd5e1');
      if (grade) { grade.textContent = t(`security.grade.${key === 'empty' ? 'none' : key}`); grade.style.color = color; grade.style.background = `rgba(${background},.12)`; }
      if (title) title.textContent = t(`security.hero.title.${key === 'empty' ? 'none' : key}`);
      const issues = [
          summary.weakCount && t('security.hero.weak').replace('{n}', String(summary.weakCount)),
          summary.duplicateGroupCount && t('security.hero.dup').replace('{n}', String(summary.duplicateGroupCount)),
          summary.staleCount && t('security.hero.stale').replace('{n}', String(summary.staleCount)),
        ].filter(Boolean).join('、');
      if (desc) desc.textContent = summary.hasRecords
        ? (issues ? t('security.hero.desc').replace('{issues}', issues) : t('security.hero.clean')) : t('security.hero.empty');
    }
    renderM4HealthCard('WEAK', 'weak-issues');
    renderM4HealthCard('DUPLICATE', 'dup-issues');
    renderM4HealthCard('STALE', 'stale-issues');
  }

  function renderM4Health() {
    return preserveProductFocus(byId('page-security'), renderM4HealthBody);
  }

  function renderM4HealthCardWithFocus(kind) {
    const id = {WEAK: 'weak-issues', DUPLICATE: 'dup-issues', STALE: 'stale-issues'}[kind];
    return preserveProductFocus(byId(id), () => renderM4HealthCard(kind, id));
  }

  function changeHealthPage(kind, forward) {
    const page = healthPage(kind);
    if (runtime.pendingHealthIssues[kind]) return;
    if (forward) {
      if (!page.nextCursor) return;
      runtime.healthPagerFocus[kind] = 'next';
      requestHealthIssues(kind, page.nextCursor);
      return;
    } else {
      if (page.pageIndex === 0 || !page.previousCursor) return;
      runtime.healthPagerFocus[kind] = 'previous';
      requestHealthIssues(kind, page.previousCursor);
      return;
    }
    return;
  }

  function openDuplicateHealthGroup() {
    runtime.vaultQuery = '';
    runtime.vaultFilter = 'DUPLICATE';
    resetVaultPagePosition();
    switchProductView('vault');
    requestVaultPage();
  }

  function openHealthRecord(item, kind) {
    const content = document.querySelector('.content');
    runtime.healthSingleOrigin = {
      kind, pageIndex: healthPage(kind).pageIndex, scrollTop: content?.scrollTop || 0,
      focusKey: `health:${kind}:${item.recordId}`,
    };
    runtime.vaultQuery = '';
    runtime.vaultFilter = 'ALL';
    runtime.vaultView = 'LIST';
    resetVaultPagePosition();
    switchProductView('vault');
    locateHealthRecord({recordId: item.recordId, revision: item.recordRevision}, true);
  }

  function restoreHealthSingleOrigin() {
    const origin = runtime.healthSingleOrigin;
    if (!origin || runtime.state !== 'UNLOCKED' || !runtime.healthSummary) return false;
    cancelHealthLocate();
    clearSelectedDetails();
    renderM4Vault();
    navigateDemoView('security');
    syncHealthRescanPolling(true);
    setProductTopbarTitle();
    setProductGlobalSearchValue('');
    renderM4Health();
    const content = document.querySelector('.content');
    if (content) content.scrollTop = origin.scrollTop;
    document.querySelector(`[data-pdm-native-focus-key="${origin.focusKey}"]`)?.focus({preventScroll: true});
    runtime.healthSingleOrigin = null;
    return true;
  }

  function requestHealthOverview(origin) {
    if (!origin) return;
    requestHealthOverviewAt(origin.kind, origin.pageIndex, 'RETURN');
  }

  function requestHealthPageRecovery(kind) {
    const page = healthPage(kind);
    if (!page) return;
    requestHealthOverviewAt(kind, page.pageIndex, 'RECOVERY');
  }

  function requestHealthOverviewAt(kind, pageIndex, mode) {
    if (!['WEAK', 'DUPLICATE', 'STALE'].includes(kind) || !Number.isSafeInteger(pageIndex) || pageIndex < 0 ||
        !['RETURN', 'RECOVERY'].includes(mode) || !runtime.bridge || !runtime.ready ||
        runtime.state !== 'UNLOCKED' || runtime.pendingHealthOverview) return;
    const id = requestId();
    runtime.pendingHealthOverview = id;
    runtime.healthOverviewMode = mode;
    runtime.healthRescanRefreshPending = false;
    runtime.bridge.getHealthOverviewAtV1(id, runtime.pageEpoch, runtime.sessionEpoch, kind, pageIndex, (ack) => {
      if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingHealthOverview === id) {
        runtime.pendingHealthOverview = '';
        runtime.healthOverviewMode = '';
        if (mode === 'RETURN') runtime.healthSingleOrigin = null;
        showErrorToast(ack?.errorCode || 'INTERNAL_FAILURE');
        refreshControls();
      }
    });
    refreshControls();
  }

  function cancelPendingHealthOverview() {
    const pending = runtime.pendingHealthOverview;
    runtime.pendingHealthOverview = '';
    runtime.healthOverviewMode = '';
    runtime.healthSingleOrigin = null;
    if (!pending || !runtime.bridge || runtime.pageEpoch <= 0) return;
    runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, pending, () => {});
  }

  function onHealthOverview(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingHealthOverview || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    runtime.pendingHealthOverview = '';
    const mode = runtime.healthOverviewMode;
    runtime.healthOverviewMode = '';
    const summary = errorCode === 'OK' ? normalizeHealthSummary(result) : null;
    if (!summary) {
      if (mode === 'RETURN') runtime.healthSingleOrigin = null;
      showErrorToast(errorCode === 'OK' ? 'INTERNAL_FAILURE' : errorCode);
      refreshControls();
      return;
    }
    runtime.healthSummary = summary;
    runtime.healthError = '';
    for (const kind of ['WEAK', 'DUPLICATE', 'STALE']) runtime.healthPages[kind] = {...summary.pages[kind], error: ''};
    if (mode === 'RECOVERY') renderM4Health();
    else restoreHealthSingleOrigin();
    refreshHealthRescanSummary();
    refreshControls();
  }

  function locateHealthRecord(record, openEditor) {
    if (!runtime.bridge || !runtime.ready || runtime.state !== 'UNLOCKED' || runtime.pendingHealthLocate) return;
    const id = requestId();
    runtime.pendingHealthLocate = id;
    runtime.healthLocateTarget = {...record, openEditor: Boolean(openEditor)};
    refreshControls();
    runtime.bridge.locateVaultRecordV1(id, runtime.pageEpoch, runtime.sessionEpoch, record.recordId, record.revision, runtime.vaultSort, (ack) => {
      if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingHealthLocate === id) {
        const target = runtime.healthLocateTarget;
        runtime.pendingHealthLocate = '';
        runtime.healthLocateTarget = null;
        recoverHealthLocateFailure(target, ack?.errorCode || 'INTERNAL_FAILURE');
      }
    });
  }

  function recoverHealthLocateFailure(target, errorCode) {
    showErrorToast(errorCode);
    if (runtime.healthGuideEditTarget) {
      runtime.healthGuideEditTarget = null;
      pauseHealthGuidance();
      return;
    }
    if (target?.openEditor && runtime.healthSingleOrigin) {
      restoreHealthSingleOrigin();
      runtime.healthSingleOrigin = null;
      refreshControls();
      return;
    }
    if (target && target.openEditor === false && state.currentNav === 'vault') {
      resetVaultPagePosition(true);
      requestVaultPage();
    }
    refreshControls();
  }

  function isRevision(value) {
    return (
      typeof value === 'string' &&
      /^[0-9a-f]{16,64}$/.test(value)
    );
  }

  function isDateIso(value) {
    return (
      typeof value === 'string' &&
      /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)
    );
  }

  function normalizeVaultSummary(value) {
    const longFields = normalizedLongFields(value?.longFields, false);
    if (
      !longFields ||
      !value ||
      !Number.isSafeInteger(value.recordId) ||
      value.recordId < 1 ||
      !isRevision(value.revision) ||
      typeof value.platform !== 'string' ||
      !value.platform ||
      typeof value.accountDisplay !== 'string' ||
      !['WEAK', 'FAIR', 'STRONG', 'PENDING', 'CHECKING', 'FAILED'].includes(value.strength) ||
      typeof value.favorite !== 'boolean' ||
      !Number.isSafeInteger(value.duplicateGroup) ||
      value.duplicateGroup < 0 ||
      !Number.isSafeInteger(value.similarGroup) ||
      value.similarGroup < 0 ||
      typeof value.hasTotp !== 'boolean' ||
      !isDateIso(value.updatedDate) ||
      !isDateIso(value.passwordChangedDate)
    ) {
      return null;
    }
    return Object.freeze({
      recordId: value.recordId,
      revision: value.revision,
      platform: value.platform,
      accountDisplay: value.accountDisplay,
      longFields,
      strength: value.strength,
      favorite: value.favorite,
      duplicateGroup: value.duplicateGroup,
      similarGroup: value.similarGroup,
      hasTotp: value.hasTotp,
      updatedDate: value.updatedDate,
      passwordChangedDate: value.passwordChangedDate,
    });
  }

  function normalizeVaultPage(result) {
    if (
      !result ||
      !Array.isArray(result.items) ||
      result.items.length > 100 ||
      !Number.isSafeInteger(result.total) ||
      result.total < 0 ||
      result.total > 100000 ||
      typeof result.nextCursor !== 'string' ||
      !/^[A-Za-z0-9_-]{0,128}$/.test(result.nextCursor) ||
      !isRevision(result.vaultRevision) ||
      !hasExactKeys(result.counts, ['all', 'duplicate', 'favorite', 'similar', 'weak'])
    ) {
      return null;
    }
    const countNames = ['all', 'favorite', 'weak', 'duplicate', 'similar'];
    for (const name of countNames) {
      const value = result.counts[name];
      if (
        !Number.isSafeInteger(value) ||
        value < 0 ||
        value > 100000
      ) {
        return null;
      }
    }
    const items = [];
    for (const value of result.items) {
      const summary = normalizeVaultSummary(value);
      if (!summary) return null;
      items.push(summary);
    }
    return Object.freeze({
      items,
      total: result.total,
      nextCursor: result.nextCursor,
      counts: Object.freeze({
        all: result.counts.all,
        favorite: result.counts.favorite,
        weak: result.counts.weak,
        duplicate: result.counts.duplicate,
        similar: result.counts.similar,
      }),
      vaultRevision: result.vaultRevision,
    });
  }

  function normalizeVaultLocation(result) {
    if (!hasExactKeys(result, ['cursor', 'cursorHistory', 'page']) ||
        typeof result.cursor !== 'string' || !/^[A-Za-z0-9_-]{0,128}$/.test(result.cursor) ||
        !Array.isArray(result.cursorHistory) || result.cursorHistory.length > 999) return null;
    if (result.cursorHistory.some((cursor) => typeof cursor !== 'string' || !/^[A-Za-z0-9_-]{0,128}$/.test(cursor))) return null;
    const page = normalizeVaultPage(result.page);
    return page ? Object.freeze({page, cursor: result.cursor, cursorHistory: Object.freeze([...result.cursorHistory])}) : null;
  }

  function cancelHealthLocate() {
    const pending = runtime.pendingHealthLocate;
    runtime.pendingHealthLocate = '';
    runtime.healthLocateTarget = null;
    if (!pending || !runtime.bridge || !runtime.ready || runtime.pageEpoch <= 0) return;
    runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, pending, () => {});
  }

  function onHealthLocated(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingHealthLocate || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    const target = runtime.healthLocateTarget;
    runtime.pendingHealthLocate = '';
    runtime.healthLocateTarget = null;
    if (errorCode !== 'OK') {
      recoverHealthLocateFailure(target, errorCode);
      return;
    }
    const location = normalizeVaultLocation(result);
    const summary = location?.page.items.find((item) => item.recordId === target?.recordId && item.revision === target?.revision);
    if (!location || !summary) {
      recoverHealthLocateFailure(target, 'INTERNAL_FAILURE');
      return;
    }
    runtime.vaultItems = location.page.items;
    runtime.vaultTotal = location.page.total;
    runtime.vaultNextCursor = location.page.nextCursor;
    runtime.vaultCounts = location.page.counts;
    runtime.vaultRevision = location.page.vaultRevision;
    runtime.vaultCursor = location.cursor;
    runtime.vaultCursorHistory = [...location.cursorHistory];
    clearSelectedDetails();
    renderM4Vault();
    selectVaultRecord(summary, false);
    const row = document.querySelector(`.list-item[data-id="${summary.recordId}"]`);
    if (row) {
      row.scrollIntoView({behavior: 'smooth', block: 'center'});
      row.style.boxShadow = '0 0 0 2px var(--accent)';
      window.setTimeout(() => { if (row.isConnected && runtime.state === 'UNLOCKED') row.style.boxShadow = ''; }, 2000);
    }
    if (target.openEditor) {
      runtime.healthEditRecordId = runtime.healthSingleOrigin ? summary.recordId : 0;
      requestRecordEditor(summary);
    }
  }

  function normalizeHealthSummary(value) {
    if (!hasExactKeys(value, ['duplicateGroupCount', 'duplicatePage', 'failedCount', 'grade', 'hasRecords', 'healthRevision', 'pendingCount', 'score', 'scoreAvailable', 'staleCount', 'stalePage', 'weakCount', 'weakPage']) ||
        typeof value.scoreAvailable !== 'boolean' ||
        typeof value.hasRecords !== 'boolean' || !Number.isSafeInteger(value.score) || value.score < 0 || value.score > 100 ||
        !['EMPTY', 'RISK', 'FAIR', 'GOOD', 'EXCELLENT'].includes(value.grade) || !isRevision(value.healthRevision)) return null;
    for (const name of ['weakCount', 'duplicateGroupCount', 'staleCount', 'pendingCount', 'failedCount']) {
      if (!Number.isSafeInteger(value[name]) || value[name] < 0 || value[name] > 100000) return null;
    }
    if (value.failedCount > value.pendingCount ||
        value.scoreAvailable !== (value.hasRecords && value.pendingCount === 0) ||
        (!value.scoreAvailable && value.score !== 0) ||
        (!value.hasRecords && value.pendingCount !== 0)) return null;
    if ((value.hasRecords && value.grade === 'EMPTY') || (!value.hasRecords && value.grade !== 'EMPTY')) return null;
    const pages = {WEAK: normalizeHealthIssuePage(value.weakPage, 'WEAK'), DUPLICATE: normalizeHealthIssuePage(value.duplicatePage, 'DUPLICATE'), STALE: normalizeHealthIssuePage(value.stalePage, 'STALE')};
    if (Object.values(pages).includes(null) || Object.values(pages).some((page) => page.healthRevision !== value.healthRevision)) return null;
    if (pages.WEAK.total !== value.weakCount || pages.DUPLICATE.total !== value.duplicateGroupCount || pages.STALE.total !== value.staleCount) return null;
    if (!value.hasRecords && (value.score !== 0 || value.weakCount !== 0 || value.duplicateGroupCount !== 0 || value.staleCount !== 0 || Object.values(pages).some((page) => page.total !== 0))) return null;
    return Object.freeze({...value, pages: Object.freeze(pages)});
  }

  function normalizeHealthItem(value, kind) {
    if (!hasExactKeys(value, ['daysSinceChange', 'duplicateGroup', 'issueId', 'issueTypes', 'platform', 'recordId', 'recordRevision']) ||
        typeof value.issueId !== 'string' || !/^[A-Za-z0-9_-]{16,64}$/.test(value.issueId) ||
        !Number.isSafeInteger(value.recordId) || value.recordId < 1 || !isRevision(value.recordRevision) ||
        typeof value.platform !== 'string' || !value.platform || !Array.isArray(value.issueTypes) ||
        value.issueTypes.length === 0 || new Set(value.issueTypes).size !== value.issueTypes.length ||
        (kind !== 'ALL' && !value.issueTypes.includes(kind)) || value.issueTypes.some((type) => !['WEAK', 'DUPLICATE', 'STALE'].includes(type)) ||
        !Number.isSafeInteger(value.duplicateGroup) || value.duplicateGroup < 0 || value.duplicateGroup > 100000 ||
        !Number.isSafeInteger(value.daysSinceChange) || value.daysSinceChange < 0 || value.daysSinceChange > 3652058 ||
        !recordFieldFits('PLATFORM', value.platform)) return null;
    return Object.freeze({...value});
  }

  function normalizeHealthGroup(value) {
    if (!hasExactKeys(value, ['duplicateGroup', 'issueId', 'memberCount', 'members']) ||
        typeof value.issueId !== 'string' || !/^[A-Za-z0-9_-]{16,64}$/.test(value.issueId) ||
        !Number.isSafeInteger(value.duplicateGroup) || value.duplicateGroup < 1 ||
        !Number.isSafeInteger(value.memberCount) || value.memberCount < 2 || value.memberCount > 100000 ||
        !Array.isArray(value.members) || value.members.length < 2 || value.members.length > 3 || value.members.length > value.memberCount) return null;
    const members = [];
    for (const member of value.members) {
      if (!hasExactKeys(member, ['platform', 'recordId', 'recordRevision']) || !Number.isSafeInteger(member.recordId) ||
          member.recordId < 1 || !isRevision(member.recordRevision) || typeof member.platform !== 'string' || !member.platform || !recordFieldFits('PLATFORM', member.platform)) return null;
      members.push(Object.freeze({...member}));
    }
    return Object.freeze({...value, members: Object.freeze(members)});
  }

  function normalizeHealthIssuePage(result, kind) {
    if (!hasExactKeys(result, ['groups', 'healthRevision', 'items', 'nextCursor', 'pageIndex', 'previousCursor', 'total']) ||
        !Array.isArray(result.items) || !Array.isArray(result.groups) || result.items.length + result.groups.length > 100 ||
        !Number.isSafeInteger(result.total) || result.total < 0 || result.total > 100000 ||
        typeof result.nextCursor !== 'string' || !/^[A-Za-z0-9_-]{0,128}$/.test(result.nextCursor) ||
        typeof result.previousCursor !== 'string' || !/^[A-Za-z0-9_-]{0,128}$/.test(result.previousCursor) ||
        !Number.isSafeInteger(result.pageIndex) || result.pageIndex < 0 || result.pageIndex > 4999 || !isRevision(result.healthRevision)) return null;
    if ((kind === 'DUPLICATE' && result.items.length) || (kind !== 'DUPLICATE' && result.groups.length)) return null;
    const items = result.items.map((item) => normalizeHealthItem(item, kind));
    const groups = result.groups.map(normalizeHealthGroup);
    if (items.includes(null) || groups.includes(null)) return null;
    if ((result.pageIndex === 0 && result.previousCursor) || (result.pageIndex > 0 && !result.previousCursor)) return null;
    return Object.freeze({items: Object.freeze(items), groups: Object.freeze(groups), total: result.total,
      nextCursor: result.nextCursor, previousCursor: result.previousCursor, pageIndex: result.pageIndex, healthRevision: result.healthRevision});
  }

  function normalizeHealthGuidanceItem(value) {
    if (!hasExactKeys(value, ['available', 'daysSinceChange', 'duplicateGroup', 'issueId', 'issueTypes', 'platform', 'recordId', 'recordRevision']) ||
        typeof value.available !== 'boolean' || typeof value.issueId !== 'string' || !/^[A-Za-z0-9_-]{16,64}$/.test(value.issueId) ||
        !Number.isSafeInteger(value.recordId) || value.recordId < 1 || !Array.isArray(value.issueTypes) || !value.issueTypes.length ||
        value.issueTypes.some((type) => !['WEAK', 'DUPLICATE', 'STALE'].includes(type)) || new Set(value.issueTypes).size !== value.issueTypes.length ||
        !Number.isSafeInteger(value.duplicateGroup) || value.duplicateGroup < 0 || !Number.isSafeInteger(value.daysSinceChange) || value.daysSinceChange < 0 || value.daysSinceChange > 3652058) return null;
    if (!value.available && (value.recordRevision !== '' || value.platform !== '' || value.duplicateGroup !== 0 || value.daysSinceChange !== 0)) return null;
    if (value.available && (!isRevision(value.recordRevision) || typeof value.platform !== 'string' || !value.platform || !recordFieldFits('PLATFORM', value.platform))) return null;
    return Object.freeze({...value});
  }

  function normalizeHealthGuidancePage(value) {
    if (!hasExactKeys(value, ['guidanceId', 'items', 'nextCursor', 'pageIndex', 'previousCursor', 'total']) ||
        typeof value.guidanceId !== 'string' || !/^[A-Za-z0-9_-]{16,64}$/.test(value.guidanceId) || !Array.isArray(value.items) || value.items.length > 100 ||
        !Number.isSafeInteger(value.total) || value.total < 0 || value.total > 100000 || !Number.isSafeInteger(value.pageIndex) || value.pageIndex < 0 || value.pageIndex > 999 ||
        typeof value.nextCursor !== 'string' || typeof value.previousCursor !== 'string' || !/^[A-Za-z0-9_-]{0,128}$/.test(value.nextCursor) || !/^[A-Za-z0-9_-]{0,128}$/.test(value.previousCursor)) return null;
    if ((value.total === 0 && (value.pageIndex !== 0 || value.items.length !== 0)) ||
        (value.total > 0 && value.pageIndex * 100 >= value.total) ||
        (value.pageIndex === 0 ? Boolean(value.previousCursor) : !value.previousCursor) ||
        (value.total > (value.pageIndex + 1) * 100 && (!value.nextCursor || value.items.length !== 100)) ||
        (value.total <= (value.pageIndex + 1) * 100 && (value.nextCursor || value.items.length !== value.total - value.pageIndex * 100))) return null;
    const items = value.items.map(normalizeHealthGuidanceItem);
    return items.includes(null) ? null : Object.freeze({...value, items: Object.freeze(items)});
  }

  function startHealthGuidance() {
    if (!runtime.bridge || !runtime.ready || runtime.state !== 'UNLOCKED' || runtime.pendingHealthGuidance || !runtime.healthSummary || runtime.healthGuide) return;
    const id = requestId();
    runtime.pendingHealthGuidance = id;
    runtime.healthGuideRequestCursor = '';
    runtime.healthGuideResetIndex = -1;
    runtime.bridge.getHealthGuidancePageV1(id, runtime.pageEpoch, runtime.sessionEpoch, '', '', (ack) => {
      if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingHealthGuidance === id) {
        runtime.pendingHealthGuidance = '';
        runtime.healthGuideResetIndex = -1;
        showErrorToast(ack?.errorCode || 'INTERNAL_FAILURE');
      }
    });
    refreshControls();
  }

  function onHealthGuidancePage(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingHealthGuidance || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    runtime.pendingHealthGuidance = '';
    const requestCursor = runtime.healthGuideRequestCursor;
    const resetIndex = runtime.healthGuideResetIndex;
    runtime.healthGuideRequestCursor = '';
    runtime.healthGuideResetIndex = -1;
    const page = errorCode === 'OK' ? normalizeHealthGuidancePage(result) : null;
    if (!page) {
      showErrorToast(errorCode === 'OK' ? 'INTERNAL_FAILURE' : errorCode);
      if (runtime.healthGuide) pauseHealthGuidance();
      else refreshControls();
      return;
    }
    if (runtime.healthGuide && (page.guidanceId !== runtime.healthGuide.guidanceId || page.total !== runtime.healthGuide.total)) {
      showErrorToast('INTERNAL_FAILURE');
      pauseHealthGuidance();
      return;
    }
    const states = runtime.healthGuide?.states instanceof Uint8Array && runtime.healthGuide.states.length === page.total
      ? runtime.healthGuide.states : new Uint8Array(page.total);
    if (runtime.healthGuide && resetIndex >= 0 && resetIndex < states.length) {
      states[resetIndex] = 0;
    }
    page.items.forEach((item, index) => {
      const globalIndex = page.pageIndex * 100 + index;
      if (!item.available && states[globalIndex] === 0) states[globalIndex] = 2;
    });
    runtime.healthGuide = {guidanceId: page.guidanceId, items: page.items, total: page.total, pageIndex: page.pageIndex,
      currentCursor: requestCursor,
      previousCursor: page.previousCursor, nextCursor: page.nextCursor, itemIndex: Math.max(0, Math.min(page.items.length - 1, runtime.healthGuideTargetIndex - page.pageIndex * 100)), states};
    const banner = byId('fix-banner');
    if (banner) {
      banner.hidden = true;
      banner.style.setProperty('display', 'none', 'important');
    }
    showCurrentHealthGuideItem();
    refreshControls();
  }

  function showCurrentHealthGuideItem() {
    const guide = runtime.healthGuide;
    if (!guide) return;
    while (guide.itemIndex < guide.items.length && !guide.items[guide.itemIndex].available) {
      const globalIndex = guide.pageIndex * 100 + guide.itemIndex;
      if (guide.states[globalIndex] === 0) guide.states[globalIndex] = 2;
      guide.itemIndex += 1;
    }
    if (guide.itemIndex >= guide.items.length) {
      if (guide.nextCursor) {
        requestHealthGuidancePage(guide, guide.nextCursor, (guide.pageIndex + 1) * 100);
      } else {
        finishHealthGuidance();
      }
      return;
    }
    const item = guide.items[guide.itemIndex];
    const globalIndex = guide.pageIndex * 100 + guide.itemIndex;
    const badges = item.issueTypes.map((type) =>
      `<span class="pdm-security-issue-pill pdm-security-issue-${type.toLowerCase()}">${escapeHtml(t('security.issue.' + type.toLowerCase()))}</span>`,
    ).join(' ');
    const multi = item.issueTypes.length > 1
      ? `<div class="pdm-inline-0bc9a9c252">${escapeHtml(t('fix.guide.multiIssue').replace('{n}', item.issueTypes.length))}</div>`
      : '';
    openModal(`
      <div class="modal-header">
        <div class="modal-title">${svgIcon('wrench', 16)} ${escapeHtml(t('fix.modal.title'))}</div>
        <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body"><div class="pdm-inline-10532f003b">
        <div class="pdm-inline-d061091441">${escapeHtml(t('fix.progress.label'))} <strong class="pdm-inline-be74bc7ba3">${globalIndex + 1} / ${guide.total}</strong></div>
        <div class="pdm-inline-42a6ced8b6">${badges}</div>${multi}
        <div class="pdm-inline-f8689d220b">${escapeHtml(item.platform)}</div>
        <div class="pdm-inline-2ddc165c05">${t('fix.guide.hint')}</div>
      </div></div>
      <div class="modal-footer">
        <button class="btn btn-sm" id="health-guide-abandon">${escapeHtml(t('fix.button.abandon'))}</button>
        <div class="modal-footer-right">
          <button class="btn btn-sm" id="health-guide-prev">${escapeHtml(t('fix.button.prev'))}</button>
          <button class="btn btn-sm" id="health-guide-skip">${escapeHtml(t('fix.button.skip'))}</button>
          <button class="btn btn-primary btn-sm" id="health-guide-edit">${escapeHtml(t('fix.button.goto'))}</button>
        </div>
      </div>`);
    const modal = byId('active-modal');
    if (modal) {
      modal.dataset.pdmM4HealthGuide = 'true';
      byId('health-guide-prev')?.addEventListener('click', previousHealthGuideItem);
      byId('health-guide-skip')?.addEventListener('click', skipHealthGuideItem);
      byId('health-guide-abandon')?.addEventListener('click', abandonHealthGuidance);
      byId('health-guide-edit')?.addEventListener('click', editHealthGuideItem);
    }
    refreshControls();
  }

  function skipHealthGuideItem() {
    const guide = runtime.healthGuide;
    if (!guide) return;
    guide.states[guide.pageIndex * 100 + guide.itemIndex] = 2;
    guide.itemIndex += 1;
    if (guide.itemIndex >= guide.items.length && guide.nextCursor) {
      requestHealthGuidancePage(guide, guide.nextCursor, (guide.pageIndex + 1) * 100);
      return;
    }
    showCurrentHealthGuideItem();
  }

  function previousHealthGuideItem() {
    const guide = runtime.healthGuide;
    if (!guide) return;
    const currentIndex = guide.pageIndex * 100 + guide.itemIndex;
    if (currentIndex <= 0) return;
    const targetIndex = currentIndex - 1;
    const cursor = guide.itemIndex === 0 ? guide.previousCursor : guide.currentCursor;
    requestHealthGuidancePage(guide, cursor, targetIndex, targetIndex);
  }

  function requestHealthGuidancePage(guide, cursor, globalIndex, resetIndex = -1) {
    if (runtime.pendingHealthGuidance || !runtime.bridge) return;
    const id = requestId();
    runtime.pendingHealthGuidance = id;
    runtime.healthGuideTargetIndex = globalIndex;
    runtime.healthGuideRequestCursor = cursor;
    runtime.healthGuideResetIndex = resetIndex;
    runtime.bridge.getHealthGuidancePageV1(id, runtime.pageEpoch, runtime.sessionEpoch, guide.guidanceId, cursor, (ack) => {
      if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingHealthGuidance === id) {
        runtime.pendingHealthGuidance = '';
        runtime.healthGuideRequestCursor = '';
        runtime.healthGuideResetIndex = -1;
        showErrorToast(ack?.errorCode || 'INTERNAL_FAILURE');
        refreshControls();
      }
    });
    refreshControls();
  }

  function cancelHealthGuidanceRequest() {
    const pending = runtime.pendingHealthGuidance;
    runtime.pendingHealthGuidance = '';
    runtime.healthGuideRequestCursor = '';
    runtime.healthGuideResetIndex = -1;
    if (!pending || !runtime.bridge || runtime.pageEpoch <= 0) return;
    runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, pending, () => {});
  }

  function currentHealthGuideEntry() {
    const guide = runtime.healthGuide;
    if (!guide || guide.itemIndex < 0 || guide.itemIndex >= guide.items.length) return null;
    const globalIndex = guide.pageIndex * 100 + guide.itemIndex;
    return {guide, item: guide.items[guide.itemIndex], globalIndex};
  }

  function releaseHealthGuidance() {
    const guide = runtime.healthGuide;
    runtime.healthGuide = null;
    runtime.healthGuideEditTarget = null;
    runtime.healthGuideTargetIndex = 0;
    runtime.healthGuideRequestCursor = '';
    runtime.healthGuideResetIndex = -1;
    const banner = byId('fix-banner');
    if (banner) {
      banner.hidden = true;
      banner.style.setProperty('display', 'none', 'important');
      banner.replaceChildren();
    }
    if (!guide?.guidanceId || !runtime.bridge || runtime.pageEpoch <= 0 || runtime.sessionEpoch <= 0) return;
    runtime.bridge.releaseHealthGuidanceV1(requestId(), runtime.pageEpoch, runtime.sessionEpoch, guide.guidanceId, () => {});
  }

  function pauseHealthGuidance() {
    if (!runtime.healthGuide) return;
    cancelHealthGuidanceRequest();
    closeDemoModal();
    const banner = byId('fix-banner');
    if (banner) {
      banner.hidden = false;
      banner.style.setProperty('display', 'flex', 'important');
      banner.replaceChildren();
      const icon = document.createElement('span');
      icon.className = 'fix-banner-icon';
      icon.innerHTML = svgIcon('wrench', 16);
      const text = document.createElement('span');
      text.className = 'fix-banner-text';
      const remaining = Array.from(runtime.healthGuide.states).filter((value) => value === 0).length;
      text.textContent = `${t('fix.banner.title')} · ${t('fix.banner.remaining').replace('{n}', remaining)}`;
      const actions = document.createElement('span');
      actions.className = 'fix-banner-actions';
      const resume = document.createElement('button');
      resume.type = 'button'; resume.className = 'btn btn-primary btn-sm'; resume.id = 'health-guide-resume';
      resume.textContent = t('fix.banner.continue');
      resume.addEventListener('click', () => {
        const guide = runtime.healthGuide;
        if (!guide) return;
        if (guide.itemIndex >= guide.items.length) {
          if (guide.nextCursor) {
            requestHealthGuidancePage(guide, guide.nextCursor, (guide.pageIndex + 1) * 100);
          } else {
            finishHealthGuidance();
          }
        } else {
          requestHealthGuidancePage(
            guide,
            guide.currentCursor,
            guide.pageIndex * 100 + guide.itemIndex,
          );
        }
      });
      const abandon = document.createElement('button');
      abandon.type = 'button'; abandon.className = 'btn btn-sm'; abandon.id = 'health-guide-banner-abandon';
      abandon.textContent = t('fix.banner.abandon');
      abandon.addEventListener('click', abandonHealthGuidance);
      actions.append(abandon, resume);
      banner.append(icon, text, actions);
    }
    refreshControls();
  }

  function editHealthGuideItem() {
    const current = currentHealthGuideEntry();
    if (!current || !current.item.available || current.guide.states[current.globalIndex] !== 0) return;
    runtime.healthGuideEditTarget = {
      guidanceId: current.guide.guidanceId,
      issueId: current.item.issueId,
      recordId: current.item.recordId,
      globalIndex: current.globalIndex,
    };
    closeDemoModal();
    runtime.vaultQuery = ''; runtime.vaultFilter = 'ALL'; runtime.vaultView = 'LIST';
    resetVaultPagePosition(); switchProductView('vault');
    locateHealthRecord({recordId: current.item.recordId, revision: current.item.recordRevision}, true);
  }

  function finishHealthGuidance() {
    const guide = runtime.healthGuide;
    if (!guide) return;
    const processed = Array.from(guide.states).filter((value) => value === 1).length;
    const skipped = Array.from(guide.states).filter((value) => value === 2).length;
    const total = guide.total;
    closeDemoModal();
    releaseHealthGuidance();
    openModal(`
      <div class="modal-header"><div class="modal-title">${escapeHtml(t('fix.progress.label'))}</div><button class="modal-close" data-pdm-onclick="closeModal()">✕</button></div>
      <div class="modal-body"><div class="pdm-inline-670b19889e">
        <div class="pdm-inline-f11bfb69de">✓</div>
        <div class="pdm-inline-30e294142f">${escapeHtml(t('fix.progress.complete'))}</div>
        <div class="pdm-inline-db0d356a5d">${escapeHtml(t('fix.progress.summary').replace('{total}', total).replace('{done}', processed).replace('{skipped}', skipped))}</div>
      </div></div>
      <div class="modal-footer"><div class="modal-footer-right"><button class="btn btn-primary btn-sm" data-pdm-onclick="closeModal()">${escapeHtml(t('fix.button.finish'))}</button></div></div>`);
    const modal = byId('active-modal');
    if (modal) modal.dataset.pdmM4HealthGuideComplete = 'true';
    refreshControls();
  }

  function showHealthGuidanceProgress() {
    const guide = runtime.healthGuide;
    if (!guide) return;
    const processed = Array.from(guide.states).filter((value) => value === 1).length;
    openModal(`
      <div class="modal-header">
        <div class="modal-title">${escapeHtml(t('fix.progress.label'))}</div>
        <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body"><div class="pdm-inline-670b19889e">
        <div class="pdm-inline-f11bfb69de">✓</div>
        <div class="pdm-inline-30e294142f">${escapeHtml(t('fix.progress.fixed').replace('{done}', processed).replace('{total}', guide.total))}</div>
        <div class="pdm-inline-db0d356a5d">${escapeHtml(t('fix.progress.continue'))}</div>
      </div></div>
      <div class="modal-footer">
        <button class="btn btn-sm" id="health-guide-progress-pause">${escapeHtml(t('fix.button.back'))}</button>
        <div class="modal-footer-right"><button class="btn btn-primary btn-sm" id="health-guide-progress-continue">${escapeHtml(t('fix.button.continue'))}</button></div>
      </div>`);
    const modal = byId('active-modal');
    if (modal) modal.dataset.pdmM4HealthGuideProgress = 'true';
    byId('health-guide-progress-pause')?.addEventListener('click', pauseHealthGuidance);
    byId('health-guide-progress-continue')?.addEventListener('click', () => {
      closeDemoModal();
      showCurrentHealthGuideItem();
    });
    refreshControls();
  }

  function abandonHealthGuidance() {
    closeDemoModal();
    releaseHealthGuidance();
    showFixedToast('已放弃逐个引导', 'Guidance abandoned', 'info');
    refreshControls();
  }

  function normalizeHealthRescan(value) {
    if (!hasExactKeys(value, ['completed', 'failed', 'scanId', 'skipped', 'state', 'total', 'updated', 'workerCount']) ||
        typeof value.scanId !== 'string' || !/^[A-Za-z0-9_-]{16,64}$/.test(value.scanId) ||
        !['RUNNING', 'CANCELLING', 'COMPLETED', 'CANCELLED', 'FAILED'].includes(value.state) ||
        !Number.isSafeInteger(value.workerCount) || value.workerCount < 0 || value.workerCount > 8) return null;
    for (const key of ['total', 'completed', 'updated', 'skipped', 'failed']) {
      if (!Number.isSafeInteger(value[key]) || value[key] < 0 || value[key] > 2147483647) return null;
    }
    if (value.completed > value.total || value.updated + value.skipped + value.failed > value.completed ||
        value.state === 'COMPLETED' && value.completed !== value.total) return null;
    return Object.freeze({...value});
  }

  function healthRescanActive() {
    return ['RUNNING', 'CANCELLING'].includes(runtime.healthRescan?.state);
  }

  function renderM4HealthRescan() {
    renderHealthRescanStatus(runtime.healthRescan,
      runtime.healthRescanCancelQueued ? 'CANCEL' : runtime.pendingHealthRescan?.action || '',
      runtime.healthRescanError ? errorText(runtime.healthRescanError) : '');
  }

  function stopHealthRescanPolling() {
    window.clearTimeout(runtime.healthRescanTimer);
    runtime.healthRescanTimer = 0;
  }

  function refreshHealthRescanSummary() {
    if (runtime.healthRescanRefreshPending && state.currentNav === 'security' && !document.hidden &&
        !runtime.pendingHealthOverview && !Object.values(runtime.pendingHealthIssues).some(Boolean)) {
      requestHealthSummary(true);
    }
  }

  function syncHealthRescanPolling(immediate = false) {
    stopHealthRescanPolling();
    if (runtime.state !== 'UNLOCKED' || state.currentNav !== 'security' || document.hidden ||
        !healthRescanActive() || runtime.pendingHealthRescan || runtime.healthRescanError) return;
    if (immediate) requestHealthRescan('STATUS');
    else runtime.healthRescanTimer = window.setTimeout(() => {
      runtime.healthRescanTimer = 0;
      syncHealthRescanPolling(true);
    }, 500);
  }

  function startHealthRescan() {
    if (healthRescanActive()) {
      if (runtime.healthRescanError) requestHealthRescan('STATUS');
      return;
    }
    requestHealthRescan('START');
  }

  function cancelHealthRescan() {
    if (!healthRescanActive() || runtime.healthRescan?.state === 'CANCELLING' ||
        runtime.pendingHealthRescan?.action === 'CANCEL') return;
    // 状态读取很短；记住点击，回执后先取消，不让轮询造成按钮反复禁用。
    runtime.healthRescanCancelQueued = true;
    stopHealthRescanPolling();
    if (!runtime.pendingHealthRescan) requestHealthRescan('CANCEL');
    renderM4HealthRescan();
    refreshControls();
  }

  function requestHealthRescan(action) {
    if (runtime.state !== 'UNLOCKED' || !runtime.ready || !runtime.bridge || runtime.pendingHealthRescan ||
        (action !== 'START' && !healthRescanActive())) return;
    stopHealthRescanPolling();
    const id = requestId();
    const scanId = action === 'START' ? '' : runtime.healthRescan.scanId;
    runtime.pendingHealthRescan = {id, action, scanId};
    runtime.healthRescanError = '';
    if (action === 'CANCEL') runtime.healthRescanCancelQueued = false;
    renderM4HealthRescan();
    refreshControls();
    const callback = (ack) => {
      if (runtime.pendingHealthRescan?.id === id && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
        onHealthRescan(id, runtime.pageEpoch, runtime.sessionEpoch, ack?.errorCode || 'INTERNAL_FAILURE', 0, 0, null);
      }
    };
    const args = [id, runtime.pageEpoch, runtime.sessionEpoch];
    if (action !== 'START') args.push(scanId);
    args.push(callback);
    runtime.bridge[{
      START: 'startHealthRescanV1', STATUS: 'getHealthRescanStatusV1', CANCEL: 'cancelHealthRescanV1',
    }[action]](...args);
  }

  function onHealthRescan(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    const pending = runtime.pendingHealthRescan;
    if (!pending || pending.id !== request || pageEpoch !== runtime.pageEpoch ||
        sessionEpoch !== runtime.sessionEpoch || runtime.state !== 'UNLOCKED') return;
    runtime.pendingHealthRescan = null;
    const scan = errorCode === 'OK' ? normalizeHealthRescan(result) : null;
    const previous = runtime.healthRescan;
    if (scan && (!pending.scanId || scan.scanId === pending.scanId) &&
        (scan.scanId !== previous?.scanId || scan.completed >= previous.completed && scan.total >= previous.total)) {
      runtime.healthRescan = scan;
      runtime.healthRescanError = '';
      if (!healthRescanActive()) {
        runtime.healthRescanCancelQueued = false;
        runtime.healthRescanRefreshPending = true;
        runtime.healthRescanVaultDirty = true;
        runtime.healthRescanVaultRequest = '';
        refreshHealthRescanSummary();
      }
    } else {
      runtime.healthRescanError = errorCode === 'OK' ? 'INTERNAL_FAILURE' : errorCode;
      if (errorCode === 'NOT_FOUND' && previous) {
        runtime.healthRescan = Object.freeze({...previous, state: 'FAILED', workerCount: 0});
        runtime.healthRescanCancelQueued = false;
      }
      if (['SESSION_REQUIRED', 'STALE_SESSION', 'STALE_PAGE'].includes(runtime.healthRescanError)) {
        applyLocked('session_invalidated');
        return;
      }
    }
    if (runtime.healthRescanCancelQueued && healthRescanActive()) requestHealthRescan('CANCEL');
    else syncHealthRescanPolling();
    renderM4HealthRescan();
    refreshControls();
  }

  function clearHealthAuthority() {
    stopHealthRescanPolling();
    runtime.healthRescan = null;
    runtime.pendingHealthRescan = null;
    runtime.healthRescanCancelQueued = false;
    runtime.healthRescanError = '';
    runtime.healthRescanRefreshPending = false;
    runtime.healthRescanVaultDirty = false;
    runtime.healthRescanVaultRequest = '';
    renderM4HealthRescan();
    const modal = byId('active-modal');
    if (
      modal?.dataset.pdmM4HealthGuide === 'true' ||
      modal?.dataset.pdmM4HealthGuideProgress === 'true' ||
      modal?.dataset.pdmM4HealthGuideComplete === 'true'
    ) {
      closeDemoModal();
    }
    runtime.pendingHealthSummary = '';
    runtime.pendingHealthOverview = '';
    runtime.healthOverviewMode = '';
    runtime.healthSingleOrigin = null;
    runtime.pendingHealthGuidance = '';
    runtime.healthGuideRequestCursor = '';
    releaseHealthGuidance();
    runtime.pendingStaleThreshold = '';
    runtime.pendingStaleDays = 0;
    runtime.healthRevision = '';
    resetHealthSnapshot();
    refreshControls();
  }

  function resetHealthSnapshot() {
    runtime.healthSummary = null;
    runtime.healthError = '';
    for (const kind of ['WEAK', 'DUPLICATE', 'STALE']) {
      runtime.pendingHealthIssues[kind] = '';
      runtime.healthPagerFocus[kind] = '';
      runtime.healthPages[kind] = {items: [], groups: [], total: 0, nextCursor: '', previousCursor: '', pageIndex: 0, error: ''};
    }
    clearHealthSurface();
  }

  function invalidateHealthRequests() {
    const pending = [
      runtime.pendingHealthSummary,
      ...Object.values(runtime.pendingHealthIssues),
    ].filter(Boolean);
    runtime.pendingHealthSummary = '';
    resetHealthSnapshot();
    if (!runtime.bridge || !runtime.ready || runtime.pageEpoch <= 0) return;
    for (const request of pending) {
      runtime.bridge.cancelRequestV1(
        requestId(),
        runtime.pageEpoch,
        request,
        () => {},
      );
    }
  }

  function clearHealthSurface() {
    for (const id of ['weak-issues', 'dup-issues', 'stale-issues']) {
      const container = byId(id);
      container?.replaceChildren();
      if (container) {
        container.style.minHeight = '';
        container.classList.remove('pdm-health-page-stable');
        container.removeAttribute('aria-busy');
      }
      const count = container?.parentElement?.querySelector('.issue-count');
      if (count) count.textContent = '';
    }
    const root = byId('page-security');
    root?.querySelector('.score-num')?.replaceChildren();
    root?.querySelector('.hero-grade')?.replaceChildren();
    root?.querySelector('.hero-info h2')?.replaceChildren();
    root?.querySelector('.hero-info p')?.replaceChildren();
    const progress = root?.querySelector('.score-ring .progress');
    progress?.setAttribute('stroke-dashoffset', '377');
  }

  function healthPage(kind) { return runtime.healthPages[kind]; }

  function requestHealthSummary(preserveSnapshot = false) {
    if (runtime.state !== 'UNLOCKED' || !runtime.ready || !runtime.bridge || runtime.pendingHealthSummary) return;
    if (!preserveSnapshot) resetHealthSnapshot();
    runtime.healthRescanRefreshPending = false;
    const id = requestId();
    runtime.pendingHealthSummary = id;
    if (!preserveSnapshot || !runtime.healthSummary) renderM4Health();
    runtime.bridge.getHealthSummaryV1(id, runtime.pageEpoch, runtime.sessionEpoch, (ack) => {
      if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingHealthSummary === id) {
        runtime.pendingHealthSummary = '';
        runtime.healthError = ack?.errorCode || 'INTERNAL_FAILURE';
        renderM4Health();
      }
    });
  }

  function requestHealthIssues(kind, cursor = '') {
    const page = healthPage(kind);
    if (runtime.state !== 'UNLOCKED' || !runtime.ready || !runtime.bridge || runtime.pendingHealthIssues[kind]) return;
    const id = requestId();
    runtime.pendingHealthIssues[kind] = id;
    setHealthCardBusy(kind, true);
    refreshControls();
    runtime.bridge.listHealthIssuesV1(id, runtime.pageEpoch, runtime.sessionEpoch, kind, cursor, 20, (ack) => {
      if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
        if (runtime.pendingHealthIssues[kind] === id) {
          runtime.pendingHealthIssues[kind] = '';
          runtime.healthPages[kind] = {...healthPage(kind), error: ack?.errorCode || 'INTERNAL_FAILURE'};
          setHealthCardBusy(kind, false);
          renderM4HealthCardWithFocus(kind);
          refreshControls();
        }
      }
    });
  }

  function requestHealth() {
    requestHealthSummary();
  }

  function onHealthSummary(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingHealthSummary || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    runtime.pendingHealthSummary = '';
    queueRatingRefresh();
    if (errorCode !== 'OK') {
      runtime.healthError = errorCode;
    } else {
      const summary = normalizeHealthSummary(result);
      if (!summary) runtime.healthError = 'INTERNAL_FAILURE';
      else {
        runtime.healthSummary = summary;
        runtime.healthError = '';
        for (const kind of ['WEAK', 'DUPLICATE', 'STALE']) {
          const page = summary.pages[kind];
          runtime.healthPages[kind] = {...page, error: ''};
        }
      }
    }
    renderM4Health();
    refreshControls();
    refreshHealthRescanSummary();
  }

  function onHealthIssues(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    const kind = ['WEAK', 'DUPLICATE', 'STALE'].find((value) => runtime.pendingHealthIssues[value] === request);
    if (!kind || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    const focusedPager = document.activeElement;
    const shouldRestorePager = Boolean(
      runtime.healthPagerFocus[kind] &&
      focusedPager instanceof HTMLElement &&
      focusedPager.dataset.pdmM4HealthPager === runtime.healthPagerFocus[kind]
    );
    runtime.pendingHealthIssues[kind] = '';
    setHealthCardBusy(kind, false);
    if (errorCode !== 'OK') {
      runtime.healthPages[kind] = {...healthPage(kind), error: errorCode};
    } else {
      const page = normalizeHealthIssuePage(result, kind);
      if (!page || (runtime.healthSummary && page.healthRevision !== runtime.healthSummary.healthRevision)) {
        runtime.healthPages[kind] = {...healthPage(kind), error: 'INTERNAL_FAILURE'};
      } else {
        runtime.healthPages[kind] = {...page, error: ''};
      }
    }
    renderM4HealthCardWithFocus(kind);
    refreshHealthRescanSummary();
    refreshControls();
    restoreHealthPagerFocus(kind, shouldRestorePager);
  }

  function restoreHealthPagerFocus(kind, shouldRestore) {
    const direction = runtime.healthPagerFocus[kind];
    runtime.healthPagerFocus[kind] = '';
    if (!direction || !shouldRestore) return;
    const id = {
      WEAK: 'weak-issues',
      DUPLICATE: 'dup-issues',
      STALE: 'stale-issues',
    }[kind];
    const container = byId(id);
    const opposite = direction === 'next' ? 'previous' : 'next';
    const candidates = [direction, opposite].map((value) =>
      container?.querySelector(`[data-pdm-m4-health-pager="${value}"]`)
    );
    const target = candidates.find((button) =>
      button instanceof HTMLButtonElement && !button.disabled
    );
    target?.focus({preventScroll: true});
  }

  function normalizeRecordWriteItem(value) {
    if (!value || !Number.isSafeInteger(value.recordId) || value.recordId < 1 ||
        !isRevision(value.revision) || typeof value.favorite !== 'boolean') return null;
    return {recordId: value.recordId, revision: value.revision, favorite: value.favorite};
  }

  function normalizeRecordDetails(result) {
    const longFields = normalizedLongFields(result?.longFields, false);
    if (
      !longFields ||
      !result ||
      !Number.isSafeInteger(result.recordId) ||
      result.recordId < 1 ||
      !isRevision(result.revision) ||
      typeof result.platform !== 'string' ||
      !result.platform ||
      typeof result.account !== 'string' ||
      typeof result.notes !== 'string' ||
      typeof result.favorite !== 'boolean' ||
      !['WEAK', 'FAIR', 'STRONG', 'PENDING', 'CHECKING', 'FAILED'].includes(result.strength) ||
      typeof result.hasPassword !== 'boolean' ||
      typeof result.hasTotp !== 'boolean' ||
      !Array.isArray(result.recoveryUsed) || result.recoveryUsed.length > 128 ||
      result.recoveryUsed.some((used) => typeof used !== 'boolean') ||
      !isDateIso(result.updatedDate) ||
      !isDateIso(result.passwordChangedDate)
    ) {
      return null;
    }
    return Object.freeze({
      recordId: result.recordId,
      revision: result.revision,
      platform: result.platform,
      account: result.account,
      notes: result.notes,
      longFields,
      favorite: result.favorite,
      strength: result.strength,
      hasPassword: result.hasPassword,
      hasTotp: result.hasTotp,
      recoveryUsed: Object.freeze([...result.recoveryUsed]),
      updatedDate: result.updatedDate,
      passwordChangedDate: result.passwordChangedDate,
    });
  }

  function normalizeSecretLease(result) {
    const longFields = normalizedLongFields(result?.longFields);
    if (
      !longFields || longFields.some((field) => field !== 'PASSWORD') ||
      !result ||
      typeof result.secretLeaseId !== 'string' ||
      !/^[A-Za-z0-9_-]{16,64}$/.test(result.secretLeaseId) ||
      typeof result.value !== 'string' ||
      recordFieldCharacterCount(result.value, 1024) > 1024 ||
      !recordFieldFits('PASSWORD', result.value) ||
      !Number.isSafeInteger(result.expiresInMs) ||
      result.expiresInMs < 1 ||
      result.expiresInMs > 30000
    ) {
      return null;
    }
    return {
      secretLeaseId: result.secretLeaseId,
      value: result.value,
      expiresInMs: result.expiresInMs,
      longFields,
    };
  }

  function normalizeClipboardResult(result) {
    if (
      !result ||
      !['NONE', 'ACCOUNT', 'PASSWORD', 'TOTP', 'GENERATED_PASSWORD', 'RECOVERY_CODE'].includes(
        result.contentKind,
      ) ||
      typeof result.owned !== 'boolean' ||
      !['COUNTDOWN', 'MANUAL'].includes(result.mode) ||
      !Number.isSafeInteger(result.remainingSeconds) ||
      result.remainingSeconds < 0 ||
      result.remainingSeconds > 60 ||
      (
        !result.owned &&
        (
          result.contentKind !== 'NONE' ||
          result.remainingSeconds !== 0
        )
      ) ||
      (
        result.owned &&
        (
          result.contentKind === 'NONE' ||
          (
            result.mode === 'COUNTDOWN' &&
            result.remainingSeconds < 1
          ) ||
          (
            result.mode === 'MANUAL' &&
            result.remainingSeconds !== 0
          )
        )
      )
    ) {
      return null;
    }
    return {
      contentKind: result.contentKind,
      owned: result.owned,
      mode: result.mode,
      remainingSeconds: result.remainingSeconds,
    };
  }

  function resetVaultPagePosition(preserveSelection = false) {
    runtime.vaultCursor = '';
    runtime.vaultCursorHistory = [];
    runtime.vaultNextCursor = '';
    if (!preserveSelection) clearSelectedDetails();
  }

  function currentVaultRequestKey() {
    return JSON.stringify([
      runtime.vaultQuery,
      runtime.vaultFilter,
      runtime.vaultSort,
      runtime.vaultCursor,
    ]);
  }

  function scrubVaultPageResult(result) {
    if (!result || !Array.isArray(result.items)) return;
    for (const item of result.items) {
      if (item && typeof item === 'object') {
        item.accountDisplay = '';
      }
    }
  }

  function requestVaultPage() {
    if (
      !globalSearchFits(runtime.vaultQuery) ||
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pendingList
    ) {
      return;
    }
    if (runtime.healthRescanVaultDirty) resetVaultPagePosition(true);
    const id = requestId();
    runtime.pendingList = id;
    if (runtime.healthRescanVaultDirty) runtime.healthRescanVaultRequest = id;
    runtime.pendingListKey = currentVaultRequestKey();
    if (runtime.vaultItems.length === 0) renderM4Vault();
    runtime.bridge.listVaultSummariesV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      runtime.vaultQuery,
      runtime.vaultFilter,
      runtime.vaultSort,
      runtime.vaultCursor,
      100,
      (ack) => {
        if (!acknowledge(ack, 'pendingList', id)) {
          renderM4Vault();
        }
      },
    );
  }

  function requestRecordDetails(summary, splitMode = false) {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pendingDetails ||
      runtime.retiredDetailsRequest
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingDetails = id;
    runtime.pendingDetailsTarget = Object.freeze({
      recordId: summary.recordId,
      revision: summary.revision,
      splitMode: Boolean(splitMode),
    });
    renderM4Vault();
    runtime.bridge.getRecordDetailsV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      summary.recordId,
      summary.revision,
      (ack) => {
        if (
          runtime.pendingDetails === id &&
          (!ack || ack.accepted !== true || ack.errorCode !== 'OK')
        ) {
          runtime.pendingDetails = '';
          runtime.pendingDetailsTarget = null;
          const queued = runtime.queuedDetailsTarget;
          runtime.queuedDetailsTarget = null;
          if (queued) {
            const next = runtime.vaultItems.find(
              (item) => item.recordId === queued.recordId && item.revision === queued.revision,
            );
            if (next) requestRecordDetails(next, queued.splitMode);
          } else {
            showErrorToast(ack && ack.errorCode);
            renderM4Vault();
          }
        }
      },
    );
  }

  function releaseReturnedLease(result) {
    const leaseId = result && result.secretLeaseId;
    if (result && typeof result === 'object') {
      result.value = '';
    }
    if (
      typeof leaseId !== 'string' ||
      !/^[A-Za-z0-9_-]{16,64}$/.test(leaseId) ||
      !runtime.bridge ||
      runtime.pageEpoch <= 0
    ) {
      return;
    }
    runtime.bridge.releaseSecretLeaseV1(
      requestId(),
      runtime.pageEpoch,
      leaseId,
      () => {},
    );
  }

  function toggleRecordReveal(
    details,
    textElement,
    button,
    location,
  ) {
    const active = runtime.activeReveal;
    if (
      active &&
      active.recordId === details.recordId &&
      active.revision === details.revision &&
      active.location === location
    ) {
      releaseActiveReveal('manual_hide');
      return;
    }
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pendingReveal ||
      !textElement ||
      !textElement.isConnected ||
      runtime.selectedRecordId !== details.recordId ||
      runtime.selectedRevision !== details.revision
    ) {
      return;
    }
    releaseActiveReveal('navigation');
    const id = requestId();
    runtime.pendingReveal = id;
    runtime.revealTarget = {
      recordId: details.recordId,
      revision: details.revision,
      hasPassword: details.hasPassword,
      location,
      textElement,
      button,
    };
    runtime.bridge.revealRecordPasswordV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      details.recordId,
      details.revision,
      (ack) => {
        if (
          !ack ||
          ack.accepted !== true ||
          ack.errorCode !== 'OK'
        ) {
          runtime.pendingReveal = '';
          runtime.revealTarget = null;
          showErrorToast(ack && ack.errorCode);
        }
      },
    );
  }

  function copyRecordField(record, contentKind) {
    record = currentRecordForAction(record);
    const pendingField = (
      contentKind === 'ACCOUNT'
        ? 'pendingAccountCopy'
        : 'pendingPasswordCopy'
    );
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      runtime[pendingField] ||
      !Number.isSafeInteger(record.recordId) ||
      !isRevision(record.revision)
    ) {
      return;
    }
    const id = requestId();
    runtime[pendingField] = id;
    const method = (
      contentKind === 'ACCOUNT'
        ? runtime.bridge.copyRecordAccountV1
        : runtime.bridge.copyRecordPasswordV1
    );
    method.call(
      runtime.bridge,
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      record.recordId,
      record.revision,
      (ack) => {
        if (
          !ack ||
          ack.accepted !== true ||
          ack.errorCode !== 'OK'
        ) {
          runtime[pendingField] = '';
          showErrorToast(ack && ack.errorCode);
        }
      },
    );
  }

  function clearClipboardOwned() {
    if (
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pendingClipboardClear ||
      !runtime.clipboardOwned
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingClipboardClear = id;
    refreshControls();
    runtime.bridge.clearClipboardV1(
      id,
      runtime.pageEpoch,
      (ack) => {
        if (
          !ack ||
          ack.accepted !== true ||
          ack.errorCode !== 'OK'
        ) {
          runtime.pendingClipboardClear = '';
          showErrorToast(ack && ack.errorCode);
          refreshControls();
        }
      },
    );
  }

  function renderClipboardState() {
    const status = byId('clipboard-status');
    if (!status) return;
    status.replaceChildren();
    if (!runtime.clipboardOwned) {
      const ready = document.createElement('span');
      ready.dataset.i18n = 'status.clipboard.ready';
      ready.textContent = t('status.clipboard.ready');
      status.append(ready);
      return;
    }
    const value = document.createElement('span');
    if (runtime.clipboardMode === 'COUNTDOWN') {
      value.className = (
        `clipboard-countdown ${
          runtime.clipboardRemaining <= 5 ? 'danger' : ''
        }`
      ).trim();
      value.textContent = t('status.clipboard.countdown').replace(
        '{n}',
        String(runtime.clipboardRemaining),
      );
    } else {
      setRuntimeText(
        value,
        '',
        '剪贴板: 等待手动清空',
        'Clipboard: waiting for manual clear',
      );
    }
    const clear = document.createElement('button');
    clear.className = 'clear-clip-btn';
    clear.type = 'button';
    clear.dataset.pdmM4VaultAction = 'true';
    clear.textContent = t('status.clipboard.clearNow');
    clear.addEventListener('click', clearClipboardOwned);
    status.append(value, clear);
  }

  function loadNextVaultPage() {
    if (
      !globalSearchFits(runtime.vaultQuery) ||
      runtime.pendingList ||
      !runtime.vaultNextCursor
    ) {
      return;
    }
    runtime.vaultCursorHistory.push(runtime.vaultCursor);
    runtime.vaultCursor = runtime.vaultNextCursor;
    runtime.vaultNextCursor = '';
    clearSelectedDetails();
    requestVaultPage();
  }

  function loadPreviousVaultPage() {
    if (
      !globalSearchFits(runtime.vaultQuery) ||
      runtime.pendingList ||
      runtime.vaultCursorHistory.length === 0
    ) {
      return;
    }
    runtime.vaultCursor = runtime.vaultCursorHistory.pop();
    runtime.vaultNextCursor = '';
    clearSelectedDetails();
    requestVaultPage();
  }

  function queueVaultReload() {
    if (runtime.searchTimer) {
      window.clearTimeout(runtime.searchTimer);
    }
    runtime.searchTimer = 0;
    if (!globalSearchFits(runtime.vaultQuery)) return;
    runtime.searchTimer = window.setTimeout(() => {
      runtime.searchTimer = 0;
      if (runtime.pendingList) {
        queueVaultReload();
        return;
      }
      resetVaultPagePosition();
      requestVaultPage();
    }, 120);
  }

  function onVaultListed(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingList ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      if (request === runtime.recoveryInvalidListRequest) runtime.recoveryInvalidListRequest = '';
      scrubVaultPageResult(result);
      return;
    }
    if (request === runtime.recoveryInvalidListRequest) {
      runtime.recoveryInvalidListRequest = '';
      runtime.pendingList = runtime.pendingListKey = '';
      if (runtime.healthRescanVaultRequest === request) runtime.healthRescanVaultRequest = '';
      scrubVaultPageResult(result);
      runtime.ratingVaultDirty = true;
      queueRatingRefresh();
      return;
    }
    const completedKey = runtime.pendingListKey;
    runtime.pendingList = '';
    queueRatingRefresh();
    runtime.pendingListKey = '';
    if (errorCode === 'INVALID_ARGUMENT' && runtime.vaultCursor &&
        completedKey === currentVaultRequestKey() && runtime.vaultItems.length) {
      runtime.ratingVaultDirty = true;
      queueRatingRefresh();
      return;
    }
    if (completedKey !== currentVaultRequestKey()) {
      scrubVaultPageResult(result);
      queueVaultReload();
      renderM4Vault();
      return;
    }
    if (errorCode !== 'OK') {
      renderM4Vault();
      if (
        errorCode === 'SESSION_REQUIRED' ||
        errorCode === 'STALE_SESSION' ||
        errorCode === 'STALE_PAGE'
      ) {
        applyLocked('session_invalidated');
        return;
      }
      showErrorToast(errorCode);
      return;
    }
    const page = normalizeVaultPage(result);
    scrubVaultPageResult(result);
    if (!page) {
      showErrorToast('INTERNAL_FAILURE');
      renderM4Vault();
      return;
    }
    const follow = runtime.recoveryFollow;
    const shouldFollow = recoveryFollowCurrent(follow) && recoveryFollowVisible(follow) &&
      page.items.some((item) => item.recordId === follow.recordId && item.revision === follow.revision);
    runtime.recoveryFollow = null;
    runtime.vaultItems = page.items;
    runtime.vaultTotal = page.total;
    runtime.vaultNextCursor = page.nextCursor;
    runtime.vaultCounts = page.counts;
    runtime.vaultRevision = page.vaultRevision;
    if (request === runtime.healthRescanVaultRequest) {
      runtime.healthRescanVaultDirty = false;
      runtime.healthRescanVaultRequest = '';
    }
    if (runtime.selectedRecordId && !page.items.some((item) => item.recordId === runtime.selectedRecordId)) {
      clearSelectedDetails();
    }
    if (state.currentNav === 'settings') {
      setProductCurrentDatabaseInfo();
    }
    if (activeEditModal() && runtime.editConflict) {
      const latest = runtime.vaultItems.find(
        (item) => item.recordId === runtime.editRecordId,
      );
      runtime.editReloadRevision = latest ? latest.revision : '';
      updateEditRecoveryUi();
    }
    const selected = runtime.vaultItems.find((item) => item.recordId === runtime.selectedRecordId);
    if (selected && runtime.selectedDetails?.recordId === selected.recordId &&
        runtime.selectedDetails.revision === selected.revision &&
        (runtime.selectedDetails.strength !== selected.strength ||
          runtime.selectedDetails.updatedDate !== selected.updatedDate)) {
      runtime.selectedDetails = Object.freeze({...runtime.selectedDetails,
        strength: selected.strength, updatedDate: selected.updatedDate});
    }
    if (selected && !runtime.pendingDetails && (!runtime.selectedDetails || runtime.selectedDetails.revision !== selected.revision)) {
      clearSelectedDetailContent();
      runtime.selectedRevision = selected.revision;
      requestRecordDetails(selected, runtime.vaultView === 'SPLIT');
    } else {
      renderM4Vault();
      if (shouldFollow) restoreRecoveryFollow(follow);
    }
    refreshControls();
  }

  function onRecordDetails(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request === runtime.retiredDetailsRequest &&
      pageEpoch === runtime.pageEpoch &&
      sessionEpoch === runtime.sessionEpoch
    ) {
      runtime.retiredDetailsRequest = '';
      if (result && typeof result === 'object') {
        result.account = '';
        result.notes = '';
      }
      const queued = runtime.queuedDetailsTarget;
      runtime.queuedDetailsTarget = null;
      const next = queued && runtime.vaultItems.find(
        (item) => item.recordId === queued.recordId && item.revision === queued.revision,
      );
      if (next) requestRecordDetails(next, queued.splitMode);
      else renderM4Vault();
      return;
    }
    if (
      request !== runtime.pendingDetails ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      if (result && typeof result === 'object') {
        result.account = '';
        result.notes = '';
      }
      return;
    }
    const target = runtime.pendingDetailsTarget;
    runtime.pendingDetails = '';
    runtime.pendingDetailsTarget = null;
    const queued = runtime.queuedDetailsTarget;
    runtime.queuedDetailsTarget = null;
    if (queued) {
      if (result && typeof result === 'object') {
        result.account = '';
        result.notes = '';
      }
      const next = runtime.vaultItems.find(
        (item) => item.recordId === queued.recordId && item.revision === queued.revision,
      );
      if (next) requestRecordDetails(next, queued.splitMode);
      else renderM4Vault();
      return;
    }
    if (!target) {
      if (result && typeof result === 'object') {
        result.account = '';
        result.notes = '';
      }
      return;
    }
    if (errorCode !== 'OK') {
      const missing = errorCode === 'NOT_FOUND';
      const conflict = errorCode === 'REVISION_CONFLICT';
      const latest = runtime.vaultItems.find((item) => item.recordId === target.recordId);
      if (conflict && latest && latest.revision !== target.revision) {
        requestRecordDetails(latest, target.splitMode);
        return;
      }
      if (missing || conflict) {
        handleRecordActionError(errorCode);
        return;
      }
      renderM4Vault();
      if (
        errorCode === 'SESSION_REQUIRED' ||
        errorCode === 'STALE_SESSION' ||
        errorCode === 'STALE_PAGE'
      ) {
        applyLocked('session_invalidated');
        return;
      }
      showErrorToast(errorCode);
      return;
    }
    const details = normalizeRecordDetails(result);
    if (result && typeof result === 'object') {
      result.account = '';
      result.notes = '';
    }
    if (
      !details ||
      details.recordId !== target.recordId ||
      details.revision !== target.revision
    ) {
      renderM4Vault();
      showErrorToast('INTERNAL_FAILURE');
      return;
    }
    const summary = runtime.vaultItems.find(
      (item) => item.recordId === target.recordId && item.revision === target.revision,
    );
    if (!summary) {
      renderM4Vault();
      showErrorToast('INTERNAL_FAILURE');
      return;
    }
    clearSelectedDetails();
    runtime.selectedRecordId = target.recordId;
    runtime.selectedRevision = target.revision;
    runtime.selectedDetails = Object.freeze({...details, strength: summary.strength});
    if (target.splitMode) {
      state.splitSelectedId = target.recordId;
      state.expandedId = null;
    } else {
      state.expandedId = target.recordId;
      state.splitSelectedId = null;
    }
    renderM4Vault();
    refreshControls();
  }

  function handleRecordActionError(errorCode) {
    if (
      errorCode === 'NOT_FOUND' ||
      errorCode === 'REVISION_CONFLICT'
    ) {
      clearSelectedDetails();
      renderM4Vault();
      if (errorCode === 'NOT_FOUND') {
        showFixedToast(
          '记录已不存在，列表将自动刷新。',
          'The record no longer exists. The list will refresh.',
          'error',
        );
      } else {
        showErrorToast(errorCode);
      }
      resetVaultPagePosition();
      requestVaultPage();
      return;
    }
    if (
      errorCode === 'SESSION_REQUIRED' ||
      errorCode === 'STALE_SESSION' ||
      errorCode === 'STALE_PAGE'
    ) {
      applyLocked('session_invalidated');
      return;
    }
    showErrorToast(errorCode);
  }

  function onRecordPasswordRevealed(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingReveal ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      releaseReturnedLease(result);
      return;
    }
    const target = runtime.revealTarget;
    runtime.pendingReveal = '';
    runtime.revealTarget = null;
    if (errorCode !== 'OK') {
      releaseReturnedLease(result);
      handleRecordActionError(errorCode);
      return;
    }
    const lease = normalizeSecretLease(result);
    if (result && typeof result === 'object') {
      result.value = '';
    }
    if (!lease) {
      releaseReturnedLease(result);
      handleRecordActionError('INTERNAL_FAILURE');
      return;
    }
    const targetIsCurrent = (
      target &&
      runtime.state === 'UNLOCKED' &&
      runtime.ready &&
      runtime.selectedRecordId === target.recordId &&
      runtime.selectedRevision === target.revision &&
      target.textElement &&
      target.textElement.isConnected &&
      target.button &&
      target.button.isConnected &&
      (lease.value !== '' || lease.longFields.includes('PASSWORD')) === target.hasPassword
    );
    if (!targetIsCurrent) {
      releaseReturnedLease(result);
      lease.value = '';
      return;
    }
    if (lease.longFields.includes('PASSWORD')) {
      window.pdmSensitiveDom.bindLease(lease.secretLeaseId, 'REVEAL', lease.expiresInMs, [target.textElement], false);
      target.button.replaceChildren();
      appendStaticIcon(target.button, 'eye-closed', 15);
      syncRecordRevealAccessibility(target.button, true);
      runtime.activeReveal = {
        leaseId: lease.secretLeaseId, recordId: target.recordId, revision: target.revision,
        location: target.location, hasPassword: true, textElement: target.textElement, button: target.button,
      };
      readRecordField(target, 'PASSWORD', target.textElement, 'reveal', lease.secretLeaseId).then((success) => {
        if (!success && runtime.activeReveal?.leaseId === lease.secretLeaseId) releaseActiveReveal('manual_hide');
      });
      lease.value = '';
      return;
    }
    if (lease.value === '') {
      releaseReturnedLease(result);
      target.textElement.textContent = '';
      lease.value = '';
      return;
    }
    try {
      window.pdmSensitiveDom.bindLease(
        lease.secretLeaseId,
        'REVEAL',
        lease.expiresInMs,
        [target.textElement],
        false,
      );
      target.textElement.textContent = lease.value;
      target.button.replaceChildren();
      appendStaticIcon(target.button, 'eye-closed', 15);
      syncRecordRevealAccessibility(target.button, true);
      runtime.activeReveal = {
        leaseId: lease.secretLeaseId,
        recordId: target.recordId,
        revision: target.revision,
        location: target.location,
        hasPassword: target.hasPassword,
        textElement: target.textElement,
        button: target.button,
      };
    } catch (_error) {
      if (window.pdmSensitiveDom) {
        window.pdmSensitiveDom.clearLease(
          lease.secretLeaseId,
          'manual_hide',
        );
      }
      releaseReturnedLease(result);
      target.textElement.textContent = (
        target.hasPassword ? '••••••••••••' : ''
      );
      handleRecordActionError('INTERNAL_FAILURE');
    } finally {
      lease.value = '';
    }
  }

  function onRecordCopied(
    pendingField,
    expectedKind,
    labelKey,
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    result,
  ) {
    if (
      request !== runtime[pendingField] ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    runtime[pendingField] = '';
    if (errorCode !== 'OK') {
      if (errorCode === 'EMPTY_FIELD') {
        showFixedToast(
          expectedKind === 'ACCOUNT' ? '账号为空，未复制。' : '密码为空，未复制。',
          expectedKind === 'ACCOUNT'
            ? 'The account is empty and was not copied.'
            : 'The password is empty and was not copied.',
          'info',
        );
        return;
      }
      handleRecordActionError(errorCode);
      return;
    }
    const clipboard = normalizeClipboardResult(result);
    if (
      !clipboard ||
      !clipboard.owned ||
      clipboard.contentKind !== expectedKind
    ) {
      handleRecordActionError('INTERNAL_FAILURE');
      return;
    }
    showCompositeI18nToast(
      labelKey,
      '',
      'toast.copied.suffix',
      'success',
    );
  }

  function onClipboardCleared(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingClipboardClear ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== 0
    ) {
      return;
    }
    runtime.pendingClipboardClear = '';
    if (errorCode !== 'OK') {
      handleRecordActionError(errorCode);
      return;
    }
    const clipboard = normalizeClipboardResult(result);
    if (
      !clipboard ||
      clipboard.owned ||
      clipboard.contentKind !== 'NONE'
    ) {
      handleRecordActionError('INTERNAL_FAILURE');
      return;
    }
    runtime.clipboardKind = clipboard.contentKind;
    runtime.clipboardMode = clipboard.mode;
    runtime.clipboardRemaining = clipboard.remainingSeconds;
    runtime.clipboardOwned = clipboard.owned;
    renderClipboardState();
    showI18nToast('status.clipboard.cleared', 'info');
    refreshControls();
  }

  function onRecordAccountCopied(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    onRecordCopied(
      'pendingAccountCopy',
      'ACCOUNT',
      'vault.detail.account',
      request,
      pageEpoch,
      sessionEpoch,
      errorCode,
      result,
    );
  }

  function onRecordPasswordCopied(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    onRecordCopied(
      'pendingPasswordCopy',
      'PASSWORD',
      'vault.detail.password',
      request,
      pageEpoch,
      sessionEpoch,
      errorCode,
      result,
    );
  }

  function onClipboardStateChanged(
    pageEpoch,
    sessionEpoch,
    contentKind,
    mode,
    remainingSeconds,
    owned,
  ) {
    const sessionClipboard = (
      runtime.state === 'UNLOCKED' &&
      sessionEpoch === runtime.sessionEpoch
    );
    const generatedClipboard = (
      runtime.ready &&
      sessionEpoch === 0 &&
      ['PASSWORD', 'NONE'].includes(contentKind)
    );
    if (pageEpoch !== runtime.pageEpoch || (!sessionClipboard && !generatedClipboard)) {
      return;
    }
    const clipboard = normalizeClipboardResult({
      contentKind,
      owned,
      mode,
      remainingSeconds,
    });
    if (!clipboard) {
      if (sessionClipboard) applyLocked('session_invalidated');
      return;
    }
    runtime.clipboardKind = clipboard.contentKind;
    runtime.clipboardMode = clipboard.mode;
    runtime.clipboardRemaining = clipboard.remainingSeconds;
    runtime.clipboardOwned = clipboard.owned;
    renderClipboardState();
    refreshControls();
  }

  function activeCreateModal() {
    const overlay = byId('active-modal');
    if (
      !overlay ||
      overlay.dataset.pdmM4Create !== 'true' ||
      !overlay.querySelector('#mf-platform')
    ) {
      return null;
    }
    return overlay;
  }

  function activeEditModal() {
    const overlay = byId('active-modal');
    if (
      !overlay ||
      overlay.dataset.pdmM4Edit !== 'true' ||
      !overlay.querySelector('#mf-platform')
    ) {
      return null;
    }
    return overlay;
  }

  function activeDeleteModal() {
    const overlay = byId('active-modal');
    if (
      !overlay ||
      overlay.dataset.pdmM4Delete !== 'true' ||
      !overlay.querySelector('#m4-delete-confirm')
    ) {
      return null;
    }
    return overlay;
  }

  function activeChangeKeyModal() {
    const overlay = byId('active-modal');
    if (
      !overlay ||
      overlay.dataset.pdmM4ChangeKey !== 'true' ||
      !overlay.querySelector('#kf-current') ||
      !overlay.querySelector('#kf-new') ||
      !overlay.querySelector('#kf-confirm')
    ) {
      return null;
    }
    return overlay;
  }

  function activeBackupModal() {
    const overlay = byId('active-modal');
    return overlay?.dataset.pdmM4Backup === 'true' && overlay.querySelector('#ie-preview')
      ? overlay : null;
  }

  function backupState() {
    const backup = runtime.backup;
    return backup && activeBackupModal() ? backup : null;
  }

  function backupText(key, fallback) {
    const value = t(key);
    return value === key ? fallback : value;
  }

  function createBackupState(mode) {
    return {
      generation: 1,
      mode,
      sourceKind: 'FILE',
      sourceDisplayName: '',
      scope: 'ALL',
      exportSelection: null,
      picker: null,
      kind: 'PASSWORD',
      destinationTicket: '',
      sourceTicket: '',
      pathLabel: '',
      previewTicket: '',
      previewIdentity: '',
      retryIdentity: '',
      draft: new Map(),
      restoreQueue: [],
      pendingDecision: '',
      pendingConflictId: '',
      statusFilter: 'ALL',
      fieldFilter: 'ALL',
      selected: {PASSWORD: new Map(), NOTE: new Map()},
      activeConflictId: '',
      batch: null,
      batchMessage: '',
      cursor: '',
      cursors: [],
      page: null,
      pending: null,
      reads: new Map(),
      readQueue: [],
      activeRead: null,
    };
  }

  function backupCurrent(backup, generation) {
    return runtime.backup === backup && backup.generation === generation && Boolean(activeBackupModal());
  }

  function clearBackupRead(read, reason, keepOrdinaryValue = false, releaseNative = true) {
    window.clearTimeout(read.timer);
    if (read.request && runtime.bridge && read.page === runtime.pageEpoch) {
      runtime.bridge.cancelRequestV1(requestId(), read.page, read.request, () => {});
    }
    for (const target of read.targets) {
      if (!keepOrdinaryValue) target.textContent = '';
      target.classList.remove('ie-loading-dots');
      target.removeAttribute('data-pdm-sensitive');
      target.removeAttribute('aria-busy');
    }
    read.values = ['', ''];
    if (read.readId && window.pdmSensitiveDom) {
      window.pdmSensitiveDom.clearLease(read.readId, 'lease_released');
    }
    if (releaseNative && read.readId && runtime.bridge && read.page === runtime.pageEpoch && runtime.state === 'UNLOCKED') {
      runtime.bridge.closeBackupPreviewV1(requestId(), read.page, read.session, read.readId, () => {});
    }
    read.readId = '';
    read.deadline = 0;
    read.request = '';
    read.row?.removeAttribute('aria-busy');
    if (keepOrdinaryValue) return;
    if (read.secret) for (const target of read.targets) target.textContent = target.dataset.pdmBackupPlaceholder || '';
    if (read.button?.isConnected) {
      read.button.hidden = !read.secret && reason !== 'field_failure';
      read.button.innerHTML = read.secret ? svgIcon('eye', 16) : svgIcon('repeat', 14);
      read.button.setAttribute('aria-pressed', 'false');
      read.button.setAttribute('aria-label', fixedText('重新查看两侧', 'Read both sides'));
    }
    read.row?.querySelectorAll('[data-pdm-backup-action="field-previous"], [data-pdm-backup-action="field-next"]')
      .forEach(button => setEnabled(button, false));
    const position = read.row?.querySelector('.ie-field-position');
    if (position) position.textContent = reason === 'lease_expired' ? fixedText('已隐藏，点击重新查看', 'Hidden. Read again to continue.') : '';
  }

  function clearBackupReads(backup, reason, keepOrdinaryValues = false, releaseNative = true) {
    backup.readQueue = [];
    backup.activeRead = null;
    for (const [key, read] of backup.reads) {
      const keep = keepOrdinaryValues && !read.secret && read.complete && read.row.isConnected;
      clearBackupRead(read, reason, keep, releaseNative);
      if (!keep) backup.reads.delete(key);
    }
    if (!keepOrdinaryValues) document.querySelectorAll('[data-pdm-backup-sensitive="true"]').forEach((element) => {
      element.textContent = '';
      element.removeAttribute('data-pdm-sensitive');
      element.removeAttribute('data-pdm-backup-sensitive');
    });
  }

  function clearBackupPreviewState(backup, reason, keepDraft = false, releaseNativeReads = true) {
    if (!backup) return;
    backup.picker?.dispose(); backup.picker = null;
    backup.generation += 1;
    clearBackupReads(backup, reason, false, releaseNativeReads);
    backup.previewTicket = '';
    backup.preview = null;
    backup.kind = 'PASSWORD';
    backup.previewIdentity = '';
    backup.cursor = '';
    backup.cursors = [];
    backup.page = null;
    backup.pending = null;
    backup.statusFilter = 'ALL';
    backup.fieldFilter = 'ALL';
    backup.selected.PASSWORD.clear();
    backup.selected.NOTE.clear();
    backup.activeConflictId = '';
    backup.batch = null;
    backup.batchMessage = '';
    if (!keepDraft) {
      backup.draft.clear();
      backup.retryIdentity = '';
    }
  }

  function closeBackupPreview(backup, reason, keepDraft = false) {
    if (!backup) return;
    const previewTicket = backup.previewTicket || backup.sourceTicket || backup.destinationTicket;
    const canCloseParent = Boolean(previewTicket && runtime.bridge && runtime.ready && runtime.state === 'UNLOCKED' &&
      runtime.pageEpoch > 0 && runtime.sessionEpoch > 0);
    // 父预览关闭会原生级联清除读取；重复子释放会挤占父关闭的请求额度。
    clearBackupPreviewState(backup, reason, keepDraft, !canCloseParent);
    if (canCloseParent) {
      runtime.bridge.closeBackupPreviewV1(
        requestId(), runtime.pageEpoch, runtime.sessionEpoch, previewTicket, () => {},
      );
    }
  }

  function scrubBackupInputs() {
    for (const id of ['ie-password', 'ie-confirm']) {
      const input = byId(id);
      if (input instanceof HTMLInputElement) {
        input.value = '';
        input.type = 'password';
      }
    }
  }

  function closeBackupDialog(reason = 'modal_close', force = false) {
    const modal = activeBackupModal();
    const backup = runtime.backup;
    if (!modal || !backup) return false;
    if (backup.pending && !force && !backup.batch) return true;
    if (backup.batch && backup.pending && runtime.bridge) {
      runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, backup.pending.id, () => {});
    }
    closeBackupPreview(backup, reason);
    backup.destinationTicket = '';
    backup.sourceTicket = '';
    backup.exportSelection = null;
    scrubBackupInputs();
    runtime.backup = null;
    closeDemoModal();
    if (window.pdmBackupWindow) runtime.bridge.requestCloseV1();
    refreshControls();
    return true;
  }

  function setBackupBusy(backup, busy, message = '') {
    const modal = activeBackupModal();
    if (!modal || runtime.backup !== backup) return;
    modal.dataset.pdmBackupPending = String(busy);
    if (busy) clearBackupErrorTarget();
    modal.querySelectorAll('input,select,button').forEach((control) => {
      if (busy && backup.batch && control.dataset.pdmBackupAction === 'cancel') {
        setEnabled(control, true);
        control.setAttribute('aria-busy', 'false');
        return;
      }
      if (busy) control.dataset.pdmBackupWasDisabled = String(control.disabled);
      setEnabled(
        control,
        !busy && control.dataset.pdmBackupWasDisabled !== 'true',
        busy &&
          control instanceof HTMLButtonElement &&
          (document.activeElement === control ||
            Boolean(backup.previewTicket) && control.dataset.pdmBackupWasDisabled !== 'true'),
      );
      if (!busy) delete control.dataset.pdmBackupWasDisabled;
      control.setAttribute('aria-busy', busy ? 'true' : 'false');
    });
    updateBackupProgress(backup, busy, message);
    updateBackupExportSelection(backup);
  }

  function updateBackupProgress(backup, busy, message = '') {
    const status = byId('ie-inline-status');
    if (runtime.backup !== backup) return;
    if (status) {
      if (!busy && !message) message = backup.batchMessage;
      const loading = busy && message.endsWith('…');
      status.classList.toggle('ie-loading-dots', loading);
      if (loading) message = message.slice(0, -1);
      status.hidden = !message && !backup.previewTicket;
      status.classList.toggle('ie-status-empty', !message);
      if (status.textContent !== message) setRuntimeText(status, message);
      status.classList.toggle('error', false);
    }
  }

  function clearBackupErrorTarget() {
    activeBackupModal()?.querySelectorAll(
      '[data-pdm-backup-error-target="true"]',
    ).forEach((target) => {
      target.removeAttribute('aria-invalid');
      target.removeAttribute('aria-errormessage');
      const describedBy = String(
        target.getAttribute('aria-describedby') || '',
      ).split(/\s+/).filter((id) => id && id !== 'ie-inline-status');
      if (describedBy.length) {
        target.setAttribute('aria-describedby', describedBy.join(' '));
      } else {
        target.removeAttribute('aria-describedby');
      }
      delete target.dataset.pdmBackupErrorTarget;
    });
  }

  function clearBackupStatus(backup) {
    const status = byId('ie-inline-status');
    if (!status || runtime.backup !== backup) return;
    clearBackupErrorTarget();
    status.hidden = !backup.previewTicket;
    status.classList.add('ie-status-empty');
    status.classList.remove('error', 'ie-loading-dots');
    if (status.textContent) setRuntimeText(status);
  }

  function showBackupStatus(backup, text, focusTarget = null) {
    const status = byId('ie-inline-status');
    if (!status || runtime.backup !== backup) return;
    clearBackupErrorTarget();
    status.hidden = false;
    status.classList.remove('ie-status-empty', 'ie-loading-dots');
    status.classList.add('error');
    if (status.textContent !== text) setRuntimeText(status, text);
    const target = (
      typeof focusTarget === 'string'
        ? document.querySelector(focusTarget)
        : focusTarget
    );
    if (!(target instanceof HTMLElement)) return;
    target.dataset.pdmBackupErrorTarget = 'true';
    const descriptions = new Set(
      String(target.getAttribute('aria-describedby') || '')
        .split(/\s+/)
        .filter(Boolean),
    );
    descriptions.add(status.id);
    target.setAttribute('aria-describedby', [...descriptions].join(' '));
    if (
      target instanceof HTMLInputElement ||
      target instanceof HTMLSelectElement ||
      target instanceof HTMLTextAreaElement
    ) {
      target.setAttribute('aria-invalid', 'true');
      target.setAttribute('aria-errormessage', status.id);
    }
    target.focus({preventScroll: true});
  }

  function showBackupError(backup, errorCode, focusTarget = null) {
    const message = errorText(errorCode || 'INTERNAL_FAILURE');
    showBackupStatus(
      backup,
      backup.batchMessage ? `${backup.batchMessage} ${fixedText('当前操作失败：', 'The current operation failed: ')}${message}` : message,
      focusTarget,
    );
  }

  function showBackupMessage(
    backup,
    key,
    replacements = {},
    focusTarget = null,
  ) {
    let message = t(key);
    for (const [name, value] of Object.entries(replacements)) {
      message = message.replace(`{${name}}`, String(value));
    }
    showBackupStatus(backup, message, focusTarget);
  }

  function discardConsumedBackupPreview(backup, errorCode) {
    if (backup.sourceKind === 'TRANSFER') {
      discardReceivedBackupPreview(backup, errorCode);
      return;
    }
    const preserveSource = errorCode === 'DATABASE_IO_FAILED';
    clearBackupPreviewState(backup, 'import_failure', preserveSource);
    if (!preserveSource) {
      backup.sourceTicket = '';
      backup.pathLabel = '';
      backup.draft.clear();
      backup.retryIdentity = '';
    }
    byId('ie-path').value = backup.pathLabel;
    renderBackupPreview(backup);
    showBackupMessage(
      backup,
      preserveSource ? 'dialog.ie.recovery.repreview' : 'dialog.ie.recovery.reselect',
      {},
      preserveSource ? '#ie-preview-btn' : '#ie-browse-btn',
    );
  }

  function discardBackupSource(backup, reason = 'preview_failure') {
    if (backup.sourceKind === 'TRANSFER') {
      discardReceivedBackupPreview(backup, 'SELECTION_EXPIRED');
      return;
    }
    closeBackupPreview(backup, reason);
    backup.sourceTicket = '';
    backup.pathLabel = '';
    backup.draft.clear();
    backup.retryIdentity = '';
    byId('ie-path').value = '';
    renderBackupPreview(backup);
    showBackupMessage(
      backup,
      'dialog.ie.recovery.reselect',
      {},
      '#ie-browse-btn',
    );
  }

  function showBackupFieldError(backup, errorCode) {
    if (errorCode === 'SECRET_LEASE_EXPIRED') {
      showBackupMessage(backup, 'dialog.ie.recovery.reread');
    } else {
      showBackupError(backup, errorCode);
    }
  }

  function discardReceivedBackupPreview(backup, errorCode) {
    closeBackupPreview(backup, 'preview_failure');
    renderBackupPreview(backup);
    const message = ['SELECTION_EXPIRED', 'SECRET_LEASE_EXPIRED'].includes(errorCode) ?
      fixedText('本次比较已失效。', 'This comparison is no longer valid.') : errorText(errorCode);
    showBackupStatus(backup, message + fixedText(
      ' 本次接收的预览已清除，请返回设备传输重新接收。',
      ' This received preview has been cleared. Return to device transfer to receive a new copy.'), '#ie-back-btn');
  }

  function setBackupPending(backup, kind, id) {
    backup.pending = {kind, id, generation: backup.generation, page: runtime.pageEpoch, session: runtime.sessionEpoch};
    const messages = {
      list: ['正在读取核对资料…', 'Loading comparison…'],
      preview: ['正在校验备份…', 'Checking backup…'],
      decision: ['正在暂存决定…', 'Saving preview decision…'],
      'all-decision': ['正在暂存所选项目的决定…', 'Saving selected preview decisions…'],
      'replay-decision': ['正在恢复预览决定…', 'Restoring preview decisions…'],
      'choose-export': ['请选择备份保存位置。', 'Choose a backup destination.'],
      'choose-import': ['请选择备份文件。', 'Choose a backup file.'],
    };
    setBackupBusy(backup, true, messages[kind] ? fixedText(...messages[kind]) : backupText(
      kind === 'export' ? 'dialog.ie.progress.export' : 'dialog.ie.progress.import',
      kind === 'export' ? '正在加密并写入备份，请稍候…' : '正在安全导入数据，请稍候…'));
  }

  function finishBackupPending(backup, request, pageEpoch, sessionEpoch, kind) {
    const pending = backup?.pending;
    if (!pending || pending.id !== request || pending.kind !== kind ||
        pending.page !== pageEpoch || pending.session !== sessionEpoch ||
        !backupCurrent(backup, pending.generation)) return false;
    backup.pending = null;
    setBackupBusy(backup, false);
    return true;
  }

  function rejectBackupPendingAck(backup, request, kind, ack) {
    if (ack?.accepted) return false;
    if (
      finishBackupPending(
        backup, request, runtime.pageEpoch, runtime.sessionEpoch, kind,
      )
    ) {
      if (kind === 'list' && backup.page) renderBackupPreview(backup);
      const focusTarget = {
        'choose-export': '#ie-browse-btn',
        'choose-import': '#ie-browse-btn',
        preview: '#ie-preview-btn',
        export: '#ie-execute-btn',
        import: '#ie-execute-btn',
      }[kind] || null;
      showBackupError(
        backup,
        ack?.errorCode || 'INTERNAL_FAILURE',
        focusTarget,
      );
      if (kind === 'decision') loadBackupComparisonFields(backup);
    }
    return true;
  }

  function backupFileSelection(result) {
    if (!hasExactKeys(result, ['backupLabel', 'expiresInMs', 'selected', 'selectionTicket']) ||
        typeof result.selected !== 'boolean' || !isBackupLabel(result.backupLabel) ||
        typeof result.selectionTicket !== 'string' || !isOptionalOpaqueId(result.selectionTicket) ||
        !isBackupExpiry(result.expiresInMs) || (result.selected && !isOpaqueId(result.selectionTicket))) return null;
    return result;
  }

  function backupPreview(result) {
    if (!hasExactKeys(result, ['backupLabel', 'conflictCount', 'expiresInMs', 'legacyRecoveryMissing', 'noteConflictCount', 'noteCount', 'passwordConflictCount', 'passwordCount', 'previewTicket', 'retryIdentity', 'summary']) ||
        !isOpaqueId(result.previewTicket) || !isBackupLabel(result.backupLabel) ||
        !isBackupCount(result.passwordCount) || !isBackupCount(result.noteCount) ||
        !isBackupCount(result.conflictCount) || !isBackupCount(result.passwordConflictCount) || !isBackupCount(result.noteConflictCount) ||
        result.conflictCount !== result.passwordConflictCount + result.noteConflictCount ||
        result.passwordConflictCount > result.passwordCount || result.noteConflictCount > result.noteCount || !isRevision(result.retryIdentity) ||
        result.expiresInMs !== 0 || typeof result.legacyRecoveryMissing !== 'boolean' || !isBackupSummary(result.summary)) return null;
    return result;
  }

  function backupPage(result) {
    if (!hasExactKeys(result, ['appliedIds', 'cursor', 'items', 'kind', 'nextCursor', 'remainingIds', 'summary', 'total', 'uncomparedCount', 'unresolved', 'updatedItems']) || !Array.isArray(result.items) || !Array.isArray(result.updatedItems) ||
        !['PASSWORD','NOTE'].includes(result.kind) || result.items.length > 100 || result.updatedItems.length > 100 || !isBackupCount(result.total) || !isBackupCount(result.unresolved) ||
        !isBackupCursor(result.cursor) || !isBackupCursor(result.nextCursor) || !isBackupCount(result.uncomparedCount) || !isBackupSummary(result.summary)) return null;
    for (const ids of [result.appliedIds, result.remainingIds]) {
      if (!Array.isArray(ids) || ids.length > 100 || ids.some(id => !isOpaqueId(id)) || new Set(ids).size !== ids.length) return null;
    }
    if (result.appliedIds.some(id => result.remainingIds.includes(id))) return null;
    if ([...result.items, ...result.updatedItems].some(item => !item || typeof item !== 'object')) return null;
    if (new Set(result.items.map(item => item.conflictId)).size !== result.items.length ||
        new Set(result.updatedItems.map(item => item.conflictId)).size !== result.updatedItems.length) return null;
    for (const item of [...result.items, ...result.updatedItems]) {
      const keys = ['conflictId', 'currentAccountDisplay', 'currentLongFields', 'decision', 'hasCurrentNotes', 'hasCurrentPassword', 'hasCurrentTotp', 'hasCurrentRecovery', 'hasIncomingNotes', 'hasIncomingPassword', 'hasIncomingTotp', 'hasIncomingRecovery', 'incomingAccountDisplay', 'incomingLongFields', 'platform'];
      keys.push('kind', 'targetCount', 'targetIndex', 'exactTitle', 'status', 'decisionRequired', 'targetSelected', 'targetProtected', 'businessDifferent', 'differentFields');
      if (item.kind !== result.kind || !isBackupCount(item.targetCount) || !isBackupCount(item.targetIndex) ||
          item.targetIndex >= Math.max(1,item.targetCount) || typeof item.exactTitle !== 'boolean' ||
          !['NEW', 'CONFLICT', 'IDENTICAL'].includes(item.status) ||
          ['decisionRequired', 'targetSelected', 'targetProtected', 'businessDifferent'].some(key => typeof item[key] !== 'boolean') ||
          !Array.isArray(item.differentFields) || new Set(item.differentFields).size !== item.differentFields.length ||
          item.differentFields.some(field => ![...backupBusinessFields(item.kind), 'STRENGTH', 'PASSWORD_CHANGED_AT', 'CREATED_AT', 'UPDATED_AT', 'SORT_ORDER'].includes(field))) return null;
      if (!hasExactKeys(item, keys.sort()) ||
          !isOpaqueId(item.conflictId) || !isBackupPlatform(item.platform) ||
          !isBackupAccount(item.currentAccountDisplay) || !isBackupAccount(item.incomingAccountDisplay) ||
          typeof item.hasCurrentPassword !== 'boolean' || typeof item.hasIncomingPassword !== 'boolean' ||
          typeof item.hasCurrentNotes !== 'boolean' || typeof item.hasIncomingNotes !== 'boolean' ||
          typeof item.hasCurrentTotp !== 'boolean' || typeof item.hasIncomingTotp !== 'boolean' ||
          typeof item.hasCurrentRecovery !== 'boolean' || typeof item.hasIncomingRecovery !== 'boolean' ||
          !Array.isArray(item.currentLongFields) || !Array.isArray(item.incomingLongFields) ||
          item.currentLongFields.length > 2 || item.incomingLongFields.length > 2 ||
          new Set(item.currentLongFields).size !== item.currentLongFields.length ||
          new Set(item.incomingLongFields).size !== item.incomingLongFields.length ||
          item.currentLongFields.some((field) => !['PLATFORM', 'ACCOUNT'].includes(field)) ||
          item.incomingLongFields.some((field) => !['PLATFORM', 'ACCOUNT'].includes(field)) ||
          !['OVERWRITE', 'SKIP', 'UNDECIDED', ...(item.kind === 'NOTE' ? ['KEEP'] : [])].includes(item.decision)) return null;
    }
    return result;
  }

  function isBackupSummary(summary) {
    return hasExactKeys(summary, ['imported', 'overwritten', 'recoveryCleared', 'skipped', 'unresolved']) &&
      Object.values(summary).every(isBackupCount) && summary.recoveryCleared <= summary.overwritten;
  }

  function backupBusinessFields(kind) {
    return kind === 'NOTE' ? ['PLATFORM', 'NOTES', 'FAVORITE'] :
      ['PLATFORM', 'ACCOUNT', 'PASSWORD', 'NOTES', 'TOTP', 'RECOVERY_CODES', 'FAVORITE'];
  }

  function backupFieldLabel(field, kind) {
    const labels = {
      PLATFORM: kind === 'NOTE' ? ['标题', 'Title'] : ['名称', 'Name'],
      ACCOUNT: ['账号', 'Account'], PASSWORD: ['密码', 'Password'],
      NOTES: kind === 'NOTE' ? ['正文', 'Content'] : ['备注', 'Notes'],
      TOTP: ['动态口令密钥', 'Authenticator key'], RECOVERY_CODES: ['恢复码', 'Recovery codes'],
      FAVORITE: ['收藏', 'Favorite'], STRENGTH: ['强度', 'Strength'],
      PASSWORD_CHANGED_AT: ['密码修改时间', 'Password changed'], CREATED_AT: ['创建时间', 'Created'],
      UPDATED_AT: ['修改时间', 'Updated'], SORT_ORDER: ['排序值', 'Sort order'],
    };
    return fixedText(...labels[field]);
  }

  function isOpaqueId(value) {
    return typeof value === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(value);
  }

  function isOptionalOpaqueId(value) {
    return typeof value === 'string' && /^[A-Za-z0-9_-]{0,64}$/.test(value);
  }

  function isBackupExpiry(value) {
    return Number.isSafeInteger(value) && value >= 0 && value <= 300000;
  }

  function isBackupCount(value) {
    return Number.isSafeInteger(value) && value >= 0 && value <= 100000;
  }

  function isBackupCursor(value) {
    return typeof value === 'string' && /^[A-Za-z0-9_-]{0,128}$/.test(value);
  }

  function isBackupLabel(value) {
    return typeof value === 'string' && !value.includes('\0') &&
      recordFieldCharacterCount(value, 256) <= 256 && new TextEncoder().encode(value).length <= 1024;
  }

  function isBackupPlatform(value) {
    return typeof value === 'string' && !value.includes('\0') && value.length > 0 &&
      recordFieldCharacterCount(value, 128) <= 128 && new TextEncoder().encode(value).length <= 512;
  }

  function isBackupAccount(value) {
    return typeof value === 'string' && !value.includes('\0') &&
      recordFieldCharacterCount(value, 512) <= 512 && new TextEncoder().encode(value).length <= 2048;
  }

  function isBackupImportResult(value) {
    return hasExactKeys(value, ['changed', 'healthRevision', 'imported', 'noteRevision', 'overwritten', 'skipped', 'vaultRevision']) &&
      typeof value.changed === 'boolean' && isBackupCount(value.imported) &&
      isBackupCount(value.overwritten) && isBackupCount(value.skipped) &&
      isRevision(value.vaultRevision) && isRevision(value.noteRevision) && isRevision(value.healthRevision) &&
      value.changed === (value.imported + value.overwritten > 0);
  }

  function isBackupExportResult(value) {
    return hasExactKeys(value, ['backupLabel', 'noteCount', 'passwordCount']) &&
      isBackupLabel(value.backupLabel) && isBackupCount(value.passwordCount) &&
      isBackupCount(value.noteCount);
  }

  function backupPreviewFocusKeys(element = document.activeElement) {
    const key = focusKeyForElement(element);
    if (key?.startsWith('backup-bulk:')) return [key, 'backup-selection:page'];
    if (key === 'backup-selection:clear') return [key, 'backup-selection:page', 'backup-filter:ALL'];
    if (key === 'backup-page:previous') {
      return [key, 'backup-page:next'];
    }
    if (key === 'backup-page:next') {
      return [key, 'backup-page:previous'];
    }
    return key ? [key] : [];
  }

  function updateBackupStepControls(backup) {
    const reviewing = backup.mode === 'import' && (Boolean(backup.previewTicket) || backup.sourceKind === 'TRANSFER');
    activeBackupModal()?.classList.toggle('ie-review-mode', reviewing);
    const preview = byId('ie-preview-btn');
    if (preview) preview.hidden = backup.mode !== 'import' || reviewing;
    const next = backup.mode === 'import' && backup.previewTicket && backup.kind === 'PASSWORD' && backup.preview?.noteCount > 0;
    const execute = byId('ie-execute-btn');
    if (execute) {
      execute.hidden = backup.mode === 'import' && !reviewing;
      updateBackupText(execute, next ? fixedText('下一步：记事', 'Next: notes') :
        t(backup.mode === 'export' ? 'dialog.ie.execute.export' : 'dialog.ie.execute.import'));
      if (reviewing && backup.page) {
        setEnabled(execute, !backup.pending && (next ? backup.page.unresolved : backup.preview.summary.unresolved) === 0);
      } else if (backup.sourceKind === 'TRANSFER') {
        setEnabled(execute, false);
      }
    }
    const back = byId('ie-back-btn');
    if (back) {
      const passwords = backup.kind === 'NOTE' && backup.preview?.passwordCount > 0;
      back.hidden = !reviewing;
      back.dataset.pdmBackupAction = passwords ? 'back-passwords' : 'back-setup';
      updateBackupText(back, passwords ? fixedText('返回密码', 'Back to passwords') : backup.sourceKind === 'TRANSFER' ?
        fixedText('返回设备传输', 'Back to device transfer') : fixedText('返回文件与密码', 'Back to file and password'));
    }
  }

  function switchBackupStep(kind) {
    const backup = backupState();
    if (!backup || backup.pending || !backup.previewTicket || kind === backup.kind || !['PASSWORD','NOTE'].includes(kind)) return;
    clearBackupStatus(backup);
    backup.batchMessage = '';
    listBackupConflicts(backup, '', false, false, {kind, statusFilter: 'ALL', fieldFilter: 'ALL'});
  }

  function backupButton(action, label, key = '') {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn btn-sm';
    button.dataset.pdmBackupAction = action;
    if (key) button.dataset.pdmNativeFocusKey = key;
    button.textContent = label;
    return button;
  }

  function backupDecisionLabel(decision) {
    return decision === 'KEEP' ? fixedText('保留两份', 'Keep both') :
      t('dialog.ie.conflict.' + ({OVERWRITE: 'overwrite', SKIP: 'skip', UNDECIDED: 'undecided'}[decision]));
  }

  function backupSelectedMatches(item, backup) {
    if (backup.statusFilter === 'PENDING' && !(item.decisionRequired && item.decision === 'UNDECIDED')) return false;
    if (backup.statusFilter === 'DIFFERENT' && !(item.businessDifferent || (item.targetCount > 1 && !item.targetSelected))) return false;
    if (backup.statusFilter === 'SKIPPED' && item.decision !== 'SKIP') return false;
    return backup.fieldFilter === 'ALL' || item.targetSelected && item.differentFields.includes(backup.fieldFilter);
  }

  function backupSelectionProjection(item) {
    return Object.fromEntries(['status', 'decision', 'decisionRequired', 'businessDifferent', 'differentFields',
      'targetSelected', 'targetProtected', 'targetCount', 'hasCurrentRecovery', 'hasIncomingRecovery'].map(key => [key, item[key]]));
  }

  function updateBackupText(node, text) {
    if (node && node.textContent !== text) node.textContent = text;
  }

  function renderBackupFixedActions(backup) {
    const bulk = byId('ie-bulk-actions');
    if (!bulk || !backup.page) return;
    if (!byId('ie-selected-count')) {
      const toolbar = document.createElement('div'); toolbar.className = 'ie-selection-toolbar';
      const count = document.createElement('strong'); count.id = 'ie-selected-count';
      toolbar.append(count, backupButton('select-page', '', 'backup-selection:page'),
        backupButton('clear-selection', '', 'backup-selection:clear'));
      const confirmation = document.createElement('div'); confirmation.className = 'ie-batch-confirm';
      confirmation.setAttribute('role', 'group');
      const label = document.createElement('div'); label.id = 'ie-selected-scope'; label.className = 'ie-conflict-help';
      const warning = document.createElement('div'); warning.className = 'ie-conflict-help recovery-backup-warning';
      warning.dataset.pdmBackupRecoveryWarning = 'selection';
      const actions = document.createElement('div'); actions.className = 'ie-conflict-actions';
      for (const decision of ['OVERWRITE', 'KEEP', 'SKIP']) {
        const button = backupButton('batch-confirm', '', `backup-bulk:${decision}`);
        button.dataset.pdmBackupDecision = decision; actions.append(button);
      }
      confirmation.append(label, warning, actions);
      bulk.append(toolbar, confirmation);
    }
    const selected = backup.selected[backup.kind];
    updateBackupText(byId('ie-selected-count'), fixedText(`已选 ${selected.size} 项`, `${selected.size} selected`));
    const selectPage = bulk.querySelector('[data-pdm-backup-action="select-page"]');
    updateBackupText(selectPage, fixedText('选中本页', 'Select page'));
    setEnabled(selectPage, !backup.pending && backup.page.items.some(item => item.decisionRequired));
    const clear = bulk.querySelector('[data-pdm-backup-action="clear-selection"]');
    updateBackupText(clear, fixedText('清除选择', 'Clear selection')); setEnabled(clear, !backup.pending && selected.size > 0);
    const confirmation = bulk.querySelector('.ie-batch-confirm');
    confirmation.classList.toggle('ie-batch-empty', selected.size === 0);
    confirmation.setAttribute('aria-hidden', String(selected.size === 0));
    confirmation.setAttribute('aria-label', fixedText('处理所选项目', 'Apply to selected items'));
    const outside = [...selected.values()].filter(item => !backupSelectedMatches(item, backup)).length;
    const scope = byId('ie-selected-scope'); scope.hidden = !outside;
    updateBackupText(scope, outside ? fixedText(`其中 ${outside} 项在当前筛选外。`, `${outside} items outside this filter.`) : '');
    const clearing = [...selected.values()].filter(item => item.hasCurrentRecovery && !item.hasIncomingRecovery).length;
    const warning = bulk.querySelector('[data-pdm-backup-recovery-warning="selection"]');
    warning.hidden = !clearing;
    updateBackupText(warning, clearing ? fixedText(`覆盖将清空 ${clearing} 条记录的整组恢复码；跳过可保留。`,
      `Overwrite removes all recovery codes from ${clearing} records. Skip to keep them.`) : '');
    for (const button of confirmation.querySelectorAll('[data-pdm-backup-decision]')) {
      const decision = button.dataset.pdmBackupDecision;
      button.hidden = decision === 'KEEP' && backup.kind !== 'NOTE';
      setEnabled(button, !backup.pending && selected.size > 0 && (decision !== 'KEEP' || backup.kind === 'NOTE'));
      updateBackupText(button, decision === 'OVERWRITE' ? fixedText('覆盖所选', 'Overwrite selected') :
        decision === 'SKIP' ? fixedText('跳过所选', 'Skip selected') : fixedText('所选保留两份', 'Keep both for selected'));
    }
    const summary = backup.preview.summary;
    updateBackupText(byId('ie-conflict-count'), fixedText(
      `新增 ${summary.imported} · 覆盖 ${summary.overwritten} · 跳过 ${summary.skipped} · 待处理 ${summary.unresolved}`,
      `Add ${summary.imported} · Overwrite ${summary.overwritten} · Skip ${summary.skipped} · Pending ${summary.unresolved}`));
    let final = byId('ie-final-consequence');
    if (!final) {
      final = document.createElement('div'); final.id = 'ie-final-consequence';
      final.className = 'ie-conflict-help recovery-backup-warning'; final.dataset.pdmBackupRecoveryWarning = 'final';
      activeBackupModal().querySelector('.ie-fixed-actions').append(final);
    }
    final.hidden = !summary.recoveryCleared;
    updateBackupText(final, summary.recoveryCleared ? fixedText(
      `本次覆盖将清空 ${summary.recoveryCleared} 条记录的整组恢复码。`,
      `This import will remove all recovery codes from ${summary.recoveryCleared} records.`) : '');
    const pager = byId('ie-pager');
    if (!byId('ie-conflict-prev')) {
      const row = document.createElement('div'); row.className = 'ie-conflict-toolbar';
      const previous = backupButton('previous', '←', 'backup-page:previous'); previous.id = 'ie-conflict-prev';
      const next = backupButton('next', '→', 'backup-page:next'); next.id = 'ie-conflict-next';
      const position = document.createElement('span'); position.className = 'ie-conflict-help'; position.id = 'ie-page-position';
      row.append(previous, position, next); pager.append(row);
    }
    const previous = byId('ie-conflict-prev'); setEnabled(previous, !backup.pending && backup.cursors.length > 0);
    previous.setAttribute('aria-label', fixedText('上一页', 'Previous'));
    const next = byId('ie-conflict-next'); setEnabled(next, !backup.pending && Boolean(backup.page.nextCursor));
    next.setAttribute('aria-label', fixedText('下一页', 'Next'));
    updateBackupText(byId('ie-page-position'), fixedText(`${backup.page.total} 项 · 第 ${backup.cursors.length + 1} 页`,
      `${backup.page.total} items · Page ${backup.cursors.length + 1}`));
  }

  function renderBackupPreviewBody(backup, box) {
    box.dataset.pdmBackupStep = backup.kind;
    updateBackupStepControls(backup);
    if (!backup.previewTicket) {
      const fixed = activeBackupModal()?.querySelector('.ie-fixed-actions');
      for (const id of ['ie-bulk-actions', 'ie-pager']) {
        const node = byId(id); if (node) { node.replaceChildren(); fixed?.append(node); }
      }
      byId('ie-final-consequence')?.remove();
      updateBackupText(byId('ie-conflict-count'), '');
      const empty = document.createElement('span'); empty.className = 'ie-preview-empty';
      empty.textContent = backup.sourceKind === 'TRANSFER' ? fixedText('本次接收的预览已清除。', 'This received preview has been cleared.') :
        t('dialog.ie.preview.empty'); box.replaceChildren(empty); return;
    }
    if (!backup.page) {
      if (byId('ie-conflict-list')) {
        byId('ie-conflict-list').replaceChildren();
        updateBackupText(byId('ie-comparison-detail')?.querySelector('.ie-comparison-heading strong'), '');
      } else {
        const empty = document.createElement('span'); empty.className = 'ie-preview-empty';
        empty.textContent = fixedText('正在读取预览…', 'Loading preview…'); box.replaceChildren(empty);
      }
      return;
    }
    if (!box.querySelector('.ie-comparison-workspace')) {
      const content = document.createDocumentFragment();
      const heading = document.createElement('div'); heading.className = 'ie-review-heading';
      const title = document.createElement('div'); title.id = 'ie-step-title'; title.className = 'ie-preview-summary';
      const total = document.createElement('span'); total.id = 'ie-source-total'; total.className = 'ie-conflict-help';
      heading.append(title, total); content.append(heading);
      if (backup.sourceKind === 'TRANSFER') {
        const sourceLabel = document.createElement('p'); sourceLabel.id = 'ie-source-device'; sourceLabel.className = 'ie-transfer-source'; content.append(sourceLabel);
      }
      const filters = document.createElement('div'); filters.className = 'ie-review-filters';
      for (const filter of ['ALL', 'PENDING', 'DIFFERENT', 'SKIPPED']) {
        const button = backupButton('filter', '', `backup-filter:${filter}`); button.dataset.pdmBackupFilter = filter; filters.append(button);
      }
      const label = document.createElement('label'); label.className = 'ie-field-filter-label';
      const caption = document.createElement('span'); caption.id = 'ie-field-filter-label';
      const fields = document.createElement('select'); fields.className = 'modal-field-input'; fields.id = 'ie-field-filter';
      fields.dataset.pdmNativeFocusKey = 'backup-filter:field';
      fields.addEventListener('change', () => changeBackupFilter(backup.statusFilter, fields.value));
      label.append(caption, fields); filters.append(label); content.append(filters);
      const notice = document.createElement('div'); notice.className = 'ie-uncompared-notice';
      const text = document.createElement('span'); text.id = 'ie-uncompared-count';
      notice.append(text, backupButton('uncompared', '', 'backup-filter:uncompared')); content.append(notice);
      const workspace = document.createElement('div'); workspace.className = 'ie-comparison-workspace';
      const source = document.createElement('div'); source.className = 'ie-source-panel';
      const list = document.createElement('div'); list.id = 'ie-conflict-list';
      source.append(byId('ie-bulk-actions'), list, byId('ie-pager'));
      const detail = document.createElement('div'); detail.id = 'ie-comparison-detail';
      workspace.append(source, detail); content.append(workspace); box.replaceChildren(content);
    }
    updateBackupText(byId('ie-step-title'), backup.kind === 'PASSWORD' ? fixedText('核对密码', 'Review passwords') : fixedText('核对记事', 'Review notes'));
    updateBackupText(byId('ie-source-total'), fixedText(`本次共 ${backup.preview.passwordCount} 条密码、${backup.preview.noteCount} 篇记事`,
      `${backup.preview.passwordCount} passwords and ${backup.preview.noteCount} notes`));
    if (backup.sourceKind === 'TRANSFER') updateBackupText(byId('ie-source-device'),
      fixedText('来源设备：', 'Source device: ') + backup.sourceDisplayName);
    for (const [filter, zh, en] of [['ALL', '全部', 'All'], ['PENDING', '待处理', 'Pending'], ['DIFFERENT', '有差异', 'Different'], ['SKIPPED', '已跳过', 'Skipped']]) {
      const button = box.querySelector(`[data-pdm-backup-filter="${filter}"]`);
      setEnabled(button, !backup.pending);
      updateBackupText(button, fixedText(zh, en)); button.classList.toggle('active', backup.statusFilter === filter);
      button.setAttribute('aria-pressed', String(backup.statusFilter === filter));
    }
    const fields = byId('ie-field-filter');
    if (fields.dataset.pdmBackupKind !== backup.kind) {
      const options = ['ALL', ...backupBusinessFields(backup.kind)].map(field => {
        const option = document.createElement('option'); option.value = field; return option;
      });
      fields.replaceChildren(...options); fields.dataset.pdmBackupKind = backup.kind;
    }
    for (const option of fields.options) updateBackupText(option, option.value === 'ALL' ? fixedText('全部字段', 'All fields') : backupFieldLabel(option.value, backup.kind));
    fields.value = backup.fieldFilter;
    setEnabled(fields, !backup.pending);
    updateBackupText(byId('ie-field-filter-label'), fixedText('差异字段', 'Changed field'));
    const notice = box.querySelector('.ie-uncompared-notice'); notice.classList.toggle('ie-notice-empty', !backup.page.uncomparedCount);
    updateBackupText(byId('ie-uncompared-count'), backup.page.uncomparedCount ? fixedText(
      `${backup.page.uncomparedCount} 项需先选择比较目标。`, `${backup.page.uncomparedCount} items need a comparison target.`) : '');
    const clearField = notice.querySelector('button'); clearField.hidden = !backup.page.uncomparedCount || backup.fieldFilter === 'ALL';
    setEnabled(clearField, !backup.pending);
    updateBackupText(clearField, fixedText('清除字段筛选', 'Clear field filter'));
    const list = byId('ie-conflict-list'); list.setAttribute('aria-label', fixedText('本次来源资料', 'Incoming items'));
    if (!backup.page.items.some(item => item.conflictId === backup.activeConflictId)) backup.activeConflictId = backup.page.items[0]?.conflictId || '';
    const rows = new Map(Array.from(list.children).map(row => [row.dataset.pdmBackupConflictId, row]));
    const wanted = new Set(backup.page.items.map(item => item.conflictId));
    for (const [id, row] of rows) if (!wanted.has(id)) row.remove();
    let next = list.firstElementChild;
    for (const item of backup.page.items) {
      const row = renderBackupConflict(backup, item, rows.get(item.conflictId));
      if (row !== next) list.insertBefore(row, next);
      next = row.nextElementSibling;
    }
    if (!backup.page.items.length && !list.firstElementChild) {
      const empty = document.createElement('div'); empty.className = 'ie-preview-empty';
      empty.textContent = fixedText('当前筛选没有项目', 'No items match this filter'); list.append(empty);
    }
    const detail = byId('ie-comparison-detail');
    const item = backup.page.items.find(entry => entry.conflictId === backup.activeConflictId);
    if (item) renderBackupComparison(backup, item, detail);
    else { clearBackupReads(backup, 'navigation'); detail.replaceChildren(); delete detail.dataset.pdmBackupIdentity; }
    renderBackupFixedActions(backup);
    queueMicrotask(() => { if (backupState() === backup) loadBackupComparisonFields(backup); });
  }

  function renderBackupPreview(backup) {
    const box = byId('ie-preview');
    if (!box || runtime.backup !== backup) return;
    const focused = document.activeElement; const surface = activeBackupModal();
    if (focused instanceof HTMLElement && surface?.contains(focused)) {
      preserveProductFocus(surface, () => renderBackupPreviewBody(backup, box), backupPreviewFocusKeys(focused));
    } else renderBackupPreviewBody(backup, box);
  }

  function renderBackupConflict(backup, item, row = null) {
    if (!row) {
      row = document.createElement('div'); row.className = 'ie-conflict-item';
      row.dataset.pdmBackupConflictId = item.conflictId; row.dataset.pdmBackupKind = item.kind;
      if (item.decisionRequired) {
        const checkbox = backupButton('select-item', '', `backup-selection:${item.conflictId}`);
        checkbox.className = 'ie-item-check'; checkbox.setAttribute('role', 'checkbox'); row.append(checkbox);
      }
      const open = backupButton('inspect-item', '', `backup-item:${item.conflictId}`); open.className = 'ie-item-open';
      const name = document.createElement('span'); name.className = 'ie-conflict-platform';
      const tag = document.createElement('span'); tag.className = 'ie-conflict-tag';
      open.append(name, tag); row.append(open);
    }
    row.classList.toggle('active', backup.activeConflictId === item.conflictId);
    const checkbox = row.querySelector('.ie-item-check');
    if (checkbox) {
      setEnabled(checkbox, !backup.pending);
      const checked = backup.selected[backup.kind].has(item.conflictId);
      checkbox.setAttribute('aria-label', fixedText('选择此项', 'Select item'));
      checkbox.setAttribute('aria-checked', String(checked)); updateBackupText(checkbox, checked ? '✓' : '');
    }
    const open = row.querySelector('.ie-item-open'); open.setAttribute('aria-current', String(backup.activeConflictId === item.conflictId));
    setEnabled(open, !backup.pending);
    updateBackupText(row.querySelector('.ie-conflict-platform'), item.platform);
    const tag = row.querySelector('.ie-conflict-tag');
    const classes = `ie-conflict-tag ${item.status === 'CONFLICT' ? item.decision.toLowerCase() : item.status === 'IDENTICAL' ? 'skip' : ''} ${item.status.toLowerCase()}`;
    if (tag.className !== classes) tag.className = classes;
    updateBackupText(tag, item.status === 'NEW' ? fixedText('将新增', 'New') : item.status === 'IDENTICAL' ?
      fixedText('相同 · 已跳过', 'Identical · skipped') : backupDecisionLabel(item.decision));
    return row;
  }

  function renderBackupComparison(backup, item, detail) {
    const identity = JSON.stringify([backup.previewTicket, item.kind, item.conflictId, item.targetIndex, item.targetSelected, state.lang]);
    if (detail.dataset.pdmBackupIdentity === identity) {
      for (const button of detail.querySelectorAll('[data-pdm-backup-decision]')) {
        const decision = button.dataset.pdmBackupDecision;
        const available = decision === 'OVERWRITE' ? item.targetSelected && !item.targetProtected && item.targetCount > 0 :
          decision === 'PREVIOUS_TARGET' ? item.targetIndex > 0 :
          decision === 'NEXT_TARGET' ? item.targetIndex + 1 < item.targetCount : true;
        setEnabled(button, !backup.pending && available);
        button.setAttribute('aria-pressed', String(decision === item.decision));
      }
      return;
    }
    clearBackupReads(backup, 'navigation');
    const content = document.createDocumentFragment();
    detail.dataset.pdmBackupConflictId = item.conflictId; detail.dataset.pdmBackupKind = item.kind;
    const head = document.createElement('div'); head.className = 'ie-comparison-heading';
    const name = document.createElement('strong'); name.textContent = item.platform; head.append(name);
    const actions = document.createElement('div'); actions.className = 'ie-conflict-actions';
    const targets = document.createElement('div'); targets.className = 'ie-comparison-targets ie-conflict-actions';
    if (item.decisionRequired) {
      if (item.targetCount > 0 && !item.targetSelected) {
        const select = backupButton('decision', fixedText('选择首个目标', 'Select first target'), `backup-conflict:${item.conflictId}:SELECT_TARGET`);
        setEnabled(select, !backup.pending);
        select.dataset.pdmBackupDecision = 'SELECT_TARGET'; targets.append(select);
      }
      if (item.targetCount > 1 && item.targetSelected) {
        for (const [decision, zh, en] of [['PREVIOUS_TARGET', '上个目标', 'Previous target'], ['NEXT_TARGET', '下个目标', 'Next target']]) {
          const button = backupButton('decision', fixedText(zh, en), `backup-conflict:${item.conflictId}:${decision}`);
          button.dataset.pdmBackupDecision = decision;
          setEnabled(button, !backup.pending && (decision === 'PREVIOUS_TARGET' ? item.targetIndex > 0 : item.targetIndex + 1 < item.targetCount));
          targets.append(button);
        }
      }
      for (const decision of (item.kind === 'NOTE' ? ['OVERWRITE', 'KEEP', 'SKIP'] : ['OVERWRITE', 'SKIP'])) {
        const button = backupButton('decision', backupDecisionLabel(decision), `backup-conflict:${item.conflictId}:${decision}`);
        button.dataset.pdmBackupDecision = decision;
        setEnabled(button, !backup.pending && (decision !== 'OVERWRITE' || item.targetSelected && !item.targetProtected && item.targetCount > 0));
        actions.append(button);
      }
    }
    head.append(actions); content.append(head);
    if (targets.childElementCount) content.append(targets);
    if (item.status === 'IDENTICAL' || item.targetProtected) {
      const protectedText = document.createElement('div'); protectedText.className = 'ie-conflict-help';
      protectedText.textContent = item.status === 'IDENTICAL' ? fixedText('业务内容相同，保留当前记录及其时间、排序。', 'Identical content. Keep the existing record, dates and order.') :
        fixedText('此目标用于保留另一条相同资料，不能覆盖。可换目标、保留两份或跳过。', 'This target preserves an identical item and cannot be overwritten. Choose another target, keep both, or skip.');
      content.append(protectedText);
    }
    if (item.hasCurrentRecovery && !item.hasIncomingRecovery && item.decisionRequired) {
      const warning = document.createElement('div'); warning.className = 'ie-conflict-help recovery-backup-warning';
      warning.textContent = fixedText('覆盖会清空当前整组恢复码；跳过可保留。', 'Overwrite removes the existing recovery codes. Skip to keep them.'); content.append(warning);
    }
    const columns = document.createElement('div'); columns.className = 'ie-comparison-columns';
    for (const side of ['current', 'incoming']) {
      const title = document.createElement('div'); title.className = 'ie-conflict-side-title';
      title.textContent = side === 'incoming' && backup.sourceKind === 'TRANSFER' ? fixedText('接收资料', 'Received contents') :
        t(side === 'current' ? 'dialog.ie.conflict.current' : 'dialog.ie.conflict.incoming');
      if (side === 'current' && item.targetSelected && item.targetCount) title.textContent += ` (${item.targetIndex + 1}/${item.targetCount})`;
      columns.append(title);
    }
    content.append(columns);
    const fields = item.kind === 'NOTE' ? ['PLATFORM', 'NOTES', 'FAVORITE', 'CREATED_AT', 'UPDATED_AT', 'SORT_ORDER'] :
      ['PLATFORM', 'ACCOUNT', 'PASSWORD', 'NOTES', 'TOTP', 'RECOVERY_CODES', 'FAVORITE', 'STRENGTH', 'PASSWORD_CHANGED_AT', 'UPDATED_AT'];
    const references = document.createElement('div'); references.className = 'ie-reference-group';
    const referenceTitle = document.createElement('div'); referenceTitle.className = 'ie-reference-title';
    referenceTitle.textContent = fixedText('参考信息', 'Reference information'); references.append(referenceTitle);
    for (const field of fields) {
      const secret = ['PASSWORD', 'TOTP', 'RECOVERY_CODES'].includes(field);
      const row = document.createElement('section'); row.className = 'ie-comparison-field'; row.dataset.pdmBackupField = field;
      row.classList.toggle('different', item.differentFields.includes(field));
      row.classList.toggle('reference', !backupBusinessFields(item.kind).includes(field));
      const label = document.createElement('div'); label.className = 'ie-field-heading';
      const text = document.createElement('span'); text.textContent = backupFieldLabel(field, item.kind);
      if (item.differentFields.includes(field)) text.textContent += fixedText(' · 不同', ' · Different');
      const reveal = backupButton('read-field', '', `backup-field:${item.conflictId}:${field}`);
      setEnabled(reveal, !backup.pending);
      reveal.dataset.pdmBackupField = field; reveal.className = 'ie-secret-toggle';
      reveal.hidden = !secret;
      reveal.innerHTML = secret ? svgIcon('eye', 16) : svgIcon('repeat', 14);
      reveal.setAttribute('aria-label', fixedText('查看两侧', 'Read both sides')); reveal.setAttribute('aria-pressed', 'false');
      label.append(text, reveal); row.append(label);
      const values = document.createElement('div'); values.className = 'ie-conflict-compare';
      for (const side of ['current', 'incoming']) {
        const value = document.createElement('div'); value.className = `ie-conflict-value ${side}`;
        value.dataset.pdmBackupSide = side; value.dataset.pdmBackupSensitive = 'true';
        value.textContent = side === 'current' && !item.targetSelected ?
          fixedText(item.targetCount ? '请选择比较目标' : '无目标记录', item.targetCount ? 'Select a target' : 'No existing record') :
          secret ? fixedText('已隐藏', 'Hidden') : fixedText('正在读取', 'Loading');
        value.classList.toggle('ie-loading-dots', !secret && (side !== 'current' || item.targetSelected));
        if (secret) value.dataset.pdmBackupPlaceholder = value.textContent;
        values.append(value);
      }
      row.append(values);
      const navigation = document.createElement('div'); navigation.className = 'ie-field-navigation';
      const previous = backupButton('field-previous', '←', `backup-field:${field}:previous`);
      const next = backupButton('field-next', '→', `backup-field:${field}:next`);
      previous.setAttribute('aria-label', fixedText('上一片', 'Previous part')); next.setAttribute('aria-label', fixedText('下一片', 'Next part'));
      setEnabled(previous, false); setEnabled(next, false);
      const position = document.createElement('span'); position.className = 'ie-field-position';
      navigation.append(previous, position, next); row.append(navigation);
      if (backupBusinessFields(item.kind).includes(field)) content.append(row); else references.append(row);
    }
    content.append(references);
    detail.replaceChildren(content);
    detail.dataset.pdmBackupIdentity = identity;
  }

  function updateBackupPasswordMatch() {
    const backup = backupState();
    const password = byId('ie-password');
    const confirm = byId('ie-confirm');
    const indicator = byId('ie-match-indicator');
    if (!backup || !(password instanceof HTMLInputElement) || !(confirm instanceof HTMLInputElement) || !indicator) return;
    if (backup.mode !== 'export') return;
    if (!password.value && !confirm.value) {
      indicator.className = 'match-indicator empty'; indicator.textContent = t('dialog.ie.password.indicator.empty');
    } else if (password.value === confirm.value) {
      indicator.className = 'match-indicator match'; indicator.textContent = t('dialog.ie.password.indicator.match');
    } else {
      indicator.className = 'match-indicator mismatch'; indicator.textContent = t('dialog.ie.password.indicator.mismatch');
    }
  }

  function updateBackupExportSelection(backup) {
    if (!backup || runtime.backup !== backup || backup.mode !== 'export') return;
    const custom = backup.scope === 'CUSTOM', summary = byId('ie-custom-selection');
    const counts = window.PdmExportSelection.counts(backup.exportSelection);
    const option = byId('ie-scope')?.querySelector('[value="CUSTOM"]');
    if (option) option.textContent = fixedText('自定义', 'Custom');
    if (byId('ie-select-records')) byId('ie-select-records').textContent = fixedText('选择记录', 'Choose records');
    if (summary) {
      summary.hidden = !custom;
      summary.firstElementChild.textContent = fixedText(`密码 ${counts.passwordCount} · 记事 ${counts.noteCount}`,
        `${counts.passwordCount} passwords · ${counts.noteCount} notes`);
    }
    // 在途禁用由 setBackupBusy 管理，避免打断回车提交后的焦点保持。
    if (!backup.pending) setEnabled(byId('ie-execute-btn'), !custom || counts.passwordCount + counts.noteCount > 0);
  }

  function chooseBackupExportSelection(previousScope) {
    const backup = backupState();
    if (!backup || backup.pending || backup.picker || backup.mode !== 'export') return;
    const generation = backup.generation;
    backup.scope = 'CUSTOM'; updateBackupExportSelection(backup);
    backup.picker = window.PdmExportSelection.openNative(activeBackupModal().querySelector('.modal'), runtime.bridge,
      runtime.pageEpoch, runtime.sessionEpoch, state.lang === 'en' ? 'EN' : 'ZH', backup.exportSelection, result => {
        if (!backupCurrent(backup,generation)) return;
        backup.picker = null;
        if (result !== null) backup.exportSelection = result;
        else backup.scope = previousScope;
        byId('ie-scope').value = backup.scope; updateBackupExportSelection(backup);
      });
  }

  function openDirectTransferDialog() {
    if (!runtime.ready || runtime.state !== 'UNLOCKED' || !runtime.transferLauncher || runtime.transferOpening) return;
    const page = runtime.pageEpoch, session = runtime.sessionEpoch;
    const button = byId('setting-db-transfer')?.querySelector('button');
    runtime.transferOpening = true;
    button?.setAttribute('aria-disabled', 'true');
    runtime.transferLauncher.openV1((ack) => {
      runtime.transferOpening = false;
      button?.removeAttribute('aria-disabled');
      if (!runtime.ready || runtime.state !== 'UNLOCKED' || page !== runtime.pageEpoch || session !== runtime.sessionEpoch) return;
      if (!ack?.accepted) showErrorToast(ack?.errorCode || 'INTERNAL_FAILURE');
    });
  }

  function openBackupDialog(mode = 'export', source = null) {
    if (runtime.backupLauncher && !window.pdmBackupWindow) {
      runtime.backupLauncher.openV1(mode, (ack) => {
        if (!ack?.accepted) showErrorToast(ack?.errorCode || 'INTERNAL_FAILURE');
      });
      return;
    }
    if (runtime.state !== 'UNLOCKED' || !runtime.ready || !runtime.bridge) return;
    if (activeBackupModal()) return;
    const initial = mode === 'import' ? 'import' : 'export';
    const html = `
      <div class="modal-header"><div class="modal-title" id="ie-title"></div><button class="modal-close" type="button" data-pdm-onclick="closeModal()">✕</button></div>
      <div class="modal-body">
        <div class="segment" id="ie-mode-seg"><button type="button" data-pdm-backup-action="mode" data-pdm-backup-mode="export"></button><button type="button" data-pdm-backup-action="mode" data-pdm-backup-mode="import"></button></div>
        <div class="modal-field"><label class="modal-field-label" data-i18n="dialog.ie.format.label">${t('dialog.ie.format.label')}</label><div class="ie-format-info"><span class="ie-format-name" data-i18n="dialog.ie.format.encrypted">${t('dialog.ie.format.encrypted')}</span><span class="modal-field-hint" data-i18n="dialog.ie.format.encrypted.hint">${t('dialog.ie.format.encrypted.hint')}</span></div></div>
        <div class="modal-field"><label class="modal-field-label" data-i18n="dialog.ie.path.label">${t('dialog.ie.path.label')}</label><div class="modal-field-row"><input class="modal-field-input" id="ie-path" readonly><button class="btn btn-sm" id="ie-browse-btn" type="button" data-pdm-backup-action="choose" data-i18n="dialog.ie.browse">${t('dialog.ie.browse')}</button></div></div>
        <div class="modal-field"><label class="modal-field-label" data-i18n="dialog.ie.password.label">${t('dialog.ie.password.label')}</label><div class="password-field-wrap"><input class="modal-field-input" id="ie-password" type="password"><div class="pw-actions"><button class="pw-action-btn" type="button" data-pdm-backup-action="toggle-password" data-pdm-backup-input="ie-password">${svgIcon('eye', 16)}</button></div></div><span class="modal-field-hint" data-i18n="dialog.ie.password.hint">${t('dialog.ie.password.hint')}</span></div>
        <div class="ie-mode-stack"><div class="ie-mode-page" id="ie-export-page"><div class="modal-field"><label class="modal-field-label" data-i18n="dialog.ie.password.confirm.label">${t('dialog.ie.password.confirm.label')}</label><div class="password-field-wrap"><input class="modal-field-input" id="ie-confirm" type="password"><div class="pw-actions"><button class="pw-action-btn" type="button" data-pdm-backup-action="toggle-password" data-pdm-backup-input="ie-confirm">${svgIcon('eye', 16)}</button></div></div><div class="match-indicator empty" id="ie-match-indicator"></div></div><div class="modal-field"><label class="modal-field-label" data-i18n="dialog.ie.scope.label">${t('dialog.ie.scope.label')}</label><select class="modal-field-input" id="ie-scope"><option value="ALL" data-i18n="dialog.ie.scope.all">${t('dialog.ie.scope.all')}</option><option value="PASSWORDS" data-i18n="dialog.ie.scope.passwords">${t('dialog.ie.scope.passwords')}</option><option value="NOTES" data-i18n="dialog.ie.scope.notes">${t('dialog.ie.scope.notes')}</option><option value="CUSTOM">${fixedText('自定义', 'Custom')}</option></select><div class="export-selection-summary" id="ie-custom-selection" hidden><span></span><button type="button" class="btn btn-sm" id="ie-select-records">${fixedText('选择记录', 'Choose records')}</button></div></div><div class="ie-warning-box" data-i18n="dialog.ie.warning.export">${t('dialog.ie.warning.export')}</div></div><div class="ie-mode-page" id="ie-import-page"><div class="modal-field"><label class="modal-field-label" data-i18n="dialog.ie.preview.label">${t('dialog.ie.preview.label')}</label><div class="ie-preview-box" id="ie-preview"></div><button class="btn btn-sm" id="ie-preview-btn" type="button" data-pdm-backup-action="preview" data-i18n="dialog.ie.preview.button">${t('dialog.ie.preview.button')}</button></div></div></div>
        <div class="ie-inline-status" id="ie-inline-status" role="status" aria-live="polite" aria-atomic="true" hidden></div>
      </div>
      <div class="modal-footer"><button class="btn btn-sm" type="button" data-pdm-backup-action="cancel" data-i18n="dialog.button.cancel">${t('dialog.button.cancel')}</button><div class="modal-footer-right"><button class="btn btn-sm" id="ie-back-btn" type="button" data-pdm-backup-action="back-passwords" hidden></button><button class="btn btn-primary btn-sm" id="ie-execute-btn" type="button" data-pdm-backup-action="execute"></button></div></div>`;
    openDemoModal(html, {wide: true, initialFocusSelector: '#ie-browse-btn'});
    const modal = activeBackupModal() || byId('active-modal');
    if (!modal) return;
    modal.dataset.pdmM4Backup = 'true';
    runtime.backup = createBackupState(initial);
    if (source?.sourceKind === 'TRANSFER') {
      runtime.backup.sourceKind = 'TRANSFER';
      runtime.backup.sourceDisplayName = source.displayName;
    }
    byId('ie-password')?.addEventListener('input', () => {
      clearBackupStatus(runtime.backup);
      updateBackupPasswordMatch();
    });
    byId('ie-confirm')?.addEventListener('input', () => {
      clearBackupStatus(runtime.backup);
      updateBackupPasswordMatch();
    });
    modal.addEventListener('keydown', (event) => {
      if (!event.isComposing && event.keyCode !== 229 &&
          (event.key === 'Enter' || event.key === ' ') &&
          event.target?.closest?.('[data-pdm-m4-disabled="true"]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      if (
        event.key !== 'Enter' ||
        event.isComposing ||
        event.keyCode === 229 ||
        !(event.target instanceof HTMLInputElement)
      ) {
        return;
      }
      const execute = byId(runtime.backup?.mode === 'import' && !runtime.backup.previewTicket ? 'ie-preview-btn' : 'ie-execute-btn');
      if (
        !(execute instanceof HTMLButtonElement) ||
        execute.disabled ||
        execute.dataset.pdmM4Disabled === 'true'
      ) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      execute.focus({preventScroll: true});
      execute.click();
    });
    byId('ie-scope')?.addEventListener('change', (event) => {
      const backup = backupState();
      if (
        backup &&
        event.target instanceof HTMLSelectElement &&
        ['ALL', 'PASSWORDS', 'NOTES', 'CUSTOM'].includes(event.target.value)
      ) {
        const previous = backup.scope;
        backup.scope = event.target.value;
        if (backup.scope === 'CUSTOM') chooseBackupExportSelection(previous);
        else updateBackupExportSelection(backup);
      }
    });
    byId('ie-select-records')?.addEventListener('click', () => chooseBackupExportSelection('CUSTOM'));
    arrangeBackupWindow(modal);
    projectBackupMode(initial);
    byId('ie-browse-btn')?.focus({preventScroll: true});
  }


  function projectBackupMode(mode) {
    const backup = backupState();
    if (!backup || !['export', 'import'].includes(mode) || backup.pending) return;
    if (backup.sourceKind === 'TRANSFER' && mode !== 'import') return;
    if (mode === 'import' && runtime.editorInstanceId) {
      showFixedToast(
        '请先保存或取消当前编辑，再恢复备份。',
        'Save or cancel the current edit before restoring a backup.',
        'warning',
      );
      return;
    }
    if (backup.mode !== mode) {
      closeBackupPreview(backup, 'mode_change');
      backup.sourceTicket = ''; backup.destinationTicket = ''; backup.pathLabel = '';
      backup.draft.clear(); backup.retryIdentity = '';
      scrubBackupInputs();
    }
    backup.mode = mode;
    const exportMode = mode === 'export';
    activeBackupModal()?.classList.toggle('ie-export-mode', exportMode);
    if (byId('ie-preview-btn')) byId('ie-preview-btn').hidden = exportMode;
    clearBackupStatus(backup);
    byId('ie-title').textContent = backup.sourceKind === 'TRANSFER' ? fixedText('比较接收的资料', 'Compare received contents') :
      t(exportMode ? 'dialog.ie.title.export' : 'dialog.ie.title.import');
    byId('ie-execute-btn').textContent = t(exportMode ? 'dialog.ie.execute.export' : 'dialog.ie.execute.import');
    byId('ie-path').value = backup.pathLabel;
    byId('ie-export-page')?.classList.toggle('active', exportMode);
    byId('ie-import-page')?.classList.toggle('active', !exportMode);
    const modeSegment = byId('ie-mode-seg');
    modeSegment?.setAttribute('role', 'group');
    modeSegment?.setAttribute(
      'aria-label',
      fixedText('备份操作模式', 'Backup operation mode'),
    );
    document.querySelectorAll('#ie-mode-seg button').forEach((button) => {
      const buttonMode = button.dataset.pdmBackupMode;
      button.textContent = t(
        buttonMode === 'import'
          ? 'dialog.ie.mode.import'
          : 'dialog.ie.mode.export',
      );
      button.classList.toggle('active', buttonMode === mode);
      button.setAttribute('aria-pressed', buttonMode === mode ? 'true' : 'false');
    });
    updateBackupPasswordMatch(); renderBackupPreview(backup);
    updateBackupExportSelection(backup);
    backup.picker?.appearance(state.lang === 'en' ? 'EN' : 'ZH');
  }

  function chooseBackupPath() {
    const backup = backupState();
    if (!backup || backup.pending || !runtime.bridge || backup.sourceKind === 'TRANSFER') return;
    const id = requestId();
    setBackupPending(backup, backup.mode === 'export' ? 'choose-export' : 'choose-import', id);
    const kind = backup.mode === 'export' ? 'choose-export' : 'choose-import';
    const callback = (ack) => rejectBackupPendingAck(backup, id, kind, ack);
    if (backup.mode === 'export') runtime.bridge.chooseBackupDestinationV1(id, runtime.pageEpoch, runtime.sessionEpoch, callback);
    else runtime.bridge.chooseBackupSourceV1(id, runtime.pageEpoch, runtime.sessionEpoch, callback);
  }

  function onBackupSelection(kind, request, pageEpoch, sessionEpoch, errorCode, result) {
    const backup = runtime.backup;
    if (!finishBackupPending(backup, request, pageEpoch, sessionEpoch, kind)) return;
    if (errorCode !== 'OK') {
      if (errorCode !== 'CANCELLED') {
        showBackupError(backup, errorCode, '#ie-browse-btn');
      }
      return;
    }
    const selection = backupFileSelection(result);
    if (!selection) { showBackupError(backup, 'INTERNAL_FAILURE'); return; }
    if (selection.selected) {
      if (!selection.selectionTicket) { showBackupError(backup, 'INTERNAL_FAILURE'); return; }
      closeBackupPreview(backup, 'source_change');
      backup.sourceTicket = ''; backup.destinationTicket = ''; backup.pathLabel = '';
      backup.pathLabel = selection.backupLabel;
      if (kind === 'choose-export') backup.destinationTicket = selection.selectionTicket;
      else backup.sourceTicket = selection.selectionTicket;
      renderBackupPreview(backup);
    }
    byId('ie-path').value = backup.pathLabel;
    clearBackupStatus(backup);
  }

  function previewBackupImport() {
    const backup = backupState();
    if (backup?.sourceKind === 'TRANSFER') return;
    const password = byId('ie-password');
    if (!backup || backup.mode !== 'import' || backup.pending || !(password instanceof HTMLInputElement)) return;
    if (!backup.sourceTicket) {
      showBackupMessage(
        backup,
        'dialog.ie.error.path',
        {},
        '#ie-browse-btn',
      );
      return;
    }
    if (!password.value) {
      showBackupMessage(
        backup,
        'dialog.ie.error.password',
        {},
        password,
      );
      return;
    }
    clearBackupPreviewState(backup, 'repreview', true);
    const id = requestId(); const generation = backup.generation;
    setBackupPending(backup, 'preview', id);
    const secret = password.value; password.value = '';
    runtime.bridge.previewEncryptedBackupV1(id, runtime.pageEpoch, runtime.sessionEpoch, backup.sourceTicket, secret, (ack) => {
      if (backupCurrent(backup, generation)) {
        rejectBackupPendingAck(backup, id, 'preview', ack);
      }
    });
  }

  function onBackupPreviewed(
    request, pageEpoch, sessionEpoch, errorCode,
    _errorArgumentIndex, _retryAfterMs, result,
  ) {
    const backup = runtime.backup;
    if (!finishBackupPending(backup, request, pageEpoch, sessionEpoch, 'preview')) return;
    if (errorCode !== 'OK') {
      if (errorCode === 'BACKUP_AUTH_FAILED') {
        renderBackupPreview(backup);
        showBackupMessage(
          backup,
          'dialog.ie.recovery.repreview',
          {},
          '#ie-password',
        );
      } else {
        discardBackupSource(backup);
      }
      return;
    }
    adoptBackupPreview(backup, result);
  }

  function adoptBackupPreview(backup, result) {
    const preview = backupPreview(result);
    if (!preview) { showBackupError(backup, 'INTERNAL_FAILURE'); return; }
    // 记事重新认证后必须明确选择目标，不能重放旧覆盖关系。
    const sameIdentity = backup.retryIdentity === preview.retryIdentity && preview.noteCount === 0;
    backup.previewTicket = preview.previewTicket; backup.preview = preview;
    backup.kind = preview.passwordCount === 0 && preview.noteCount > 0 ? 'NOTE' : 'PASSWORD';
    backup.previewIdentity = preview.retryIdentity;
    if (!sameIdentity) backup.draft.clear();
    backup.retryIdentity = preview.retryIdentity;
    backup.restoreQueue = sameIdentity ? Array.from(backup.draft.entries()) : [];
    renderBackupPreview(backup);
    replayNextBackupDecision(backup);
  }

  function replayNextBackupDecision(backup) {
    const next = backup.restoreQueue.shift();
    if (!next) { listBackupConflicts(backup, '', false); return; }
    const [conflictId, decision] = next;
    const id = requestId(); setBackupPending(backup, 'replay-decision', id);
    runtime.bridge.setBackupConflictDecisionV1(
      id, runtime.pageEpoch, runtime.sessionEpoch, backup.previewTicket, conflictId, decision,
      (ack) => {
        if (rejectBackupPendingAck(backup, id, 'replay-decision', ack)) {
          backup.restoreQueue = []; backup.draft.clear(); listBackupConflicts(backup, '', false);
        }
      },
    );
  }

  function changeBackupFilter(statusFilter, fieldFilter) {
    const backup = backupState();
    if (!backup || backup.pending || !['ALL', 'PENDING', 'DIFFERENT', 'SKIPPED'].includes(statusFilter) ||
        !['ALL', ...backupBusinessFields(backup.kind)].includes(fieldFilter)) return;
    if (statusFilter === backup.statusFilter && fieldFilter === backup.fieldFilter) return;
    // 查询成功前，筛选标签、选择和清单仍属于当前已展示的页面。
    byId('ie-field-filter').value = backup.fieldFilter;
    listBackupConflicts(backup, '', false, false, {kind: backup.kind, statusFilter, fieldFilter});
  }

  function listBackupConflicts(backup, cursor, previous, keepOrdinaryValues = false, view = null) {
    if (!backup?.previewTicket || backup.pending || !runtime.bridge) return;
    clearBackupReads(backup, 'navigation', keepOrdinaryValues);
    const detail = byId('ie-comparison-detail');
    if (!keepOrdinaryValues && detail) {
      delete detail.dataset.pdmBackupIdentity;
      const item = backup.page?.items.find(entry => entry.conflictId === backup.activeConflictId);
      if (item) detail.querySelectorAll('.ie-comparison-field').forEach(row => {
        const secret = ['PASSWORD', 'TOTP', 'RECOVERY_CODES'].includes(row.dataset.pdmBackupField);
        row.querySelectorAll('[data-pdm-backup-side]').forEach(target => {
          const noTarget = target.dataset.pdmBackupSide === 'current' && !item.targetSelected;
          target.textContent = noTarget ? fixedText(item.targetCount ? '请选择比较目标' : '无目标记录',
            item.targetCount ? 'Select a target' : 'No existing record') :
            secret ? fixedText('已隐藏', 'Hidden') : fixedText('正在读取', 'Loading');
          target.classList.toggle('ie-loading-dots', !secret && !noTarget);
        });
      });
    }
    const id = requestId(); setBackupPending(backup, 'list', id);
    backup.requestedView = view || {kind: backup.kind, statusFilter: backup.statusFilter, fieldFilter: backup.fieldFilter};
    backup.requestedCursor = cursor;
    backup.requestedCursors = view ? [] : previous ? backup.cursors.slice(0, -1) :
      cursor && cursor === backup.page?.nextCursor ? [...backup.cursors, backup.cursor] : [...backup.cursors];
    runtime.bridge.listBackupConflictsV1(id, runtime.pageEpoch, runtime.sessionEpoch, backup.previewTicket,
      backup.requestedView.kind, backup.requestedView.statusFilter, backup.requestedView.fieldFilter,
      cursor, 100, (ack) => rejectBackupPendingAck(backup, id, 'list', ack));
  }

  function onBackupConflictsListed(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    const backup = runtime.backup;
    if (!finishBackupPending(backup, request, pageEpoch, sessionEpoch, 'list')) return;
    if (errorCode !== 'OK') {
      if (errorCode === 'SECRET_LEASE_EXPIRED') discardBackupSource(backup);
      else { renderBackupPreview(backup); showBackupError(backup, errorCode); }
      return;
    }
    const page = backupPage(result);
    if (!page || page.kind !== backup.requestedView?.kind) { discardBackupSource(backup); return; }
    Object.assign(backup, backup.requestedView);
    backup.page = page; backup.cursor = page.cursor;
    backup.cursors = page.cursor === backup.requestedCursor ? backup.requestedCursors : [];
    backup.preview.summary = page.summary;
    for (const item of page.items) {
      if (backup.selected[backup.kind].has(item.conflictId)) {
        if (item.decisionRequired) backup.selected[backup.kind].set(item.conflictId, backupSelectionProjection(item));
        else backup.selected[backup.kind].delete(item.conflictId);
      }
    }
    renderBackupPreview(backup);
  }

  function setBackupDecision(target, decision) {
    const backup = backupState(); const conflictId = target?.closest?.('[data-pdm-backup-conflict-id]')?.dataset.pdmBackupConflictId;
    const item = backup?.page?.items.find(entry => entry.conflictId === conflictId);
    if (!backup || !backup.previewTicket || backup.pending || !item?.decisionRequired ||
        !['OVERWRITE', 'SKIP', 'KEEP', 'SELECT_TARGET', 'PREVIOUS_TARGET', 'NEXT_TARGET'].includes(decision) ||
        decision === 'OVERWRITE' && (!item.targetSelected || item.targetProtected || !item.targetCount)) return;
    clearBackupReads(backup, 'decision', ['OVERWRITE', 'KEEP', 'SKIP'].includes(decision)); backup.batchMessage = '';
    const id = requestId(); setBackupPending(backup, 'decision', id);
    backup.pendingConflictId = conflictId; backup.pendingDecision = decision;
    runtime.bridge.setBackupConflictDecisionV1(id, runtime.pageEpoch, runtime.sessionEpoch, backup.previewTicket, conflictId, decision,
      (ack) => rejectBackupPendingAck(backup, id, 'decision', ack));
  }

  function changeBackupSelection(target, action) {
    const backup = backupState(); if (!backup?.page || backup.pending) return;
    const selected = backup.selected[backup.kind];
    if (action === 'clear-selection') selected.clear();
    else if (action === 'select-page') {
      for (const item of backup.page.items) if (item.decisionRequired) selected.set(item.conflictId, backupSelectionProjection(item));
    } else {
      const id = target.closest('[data-pdm-backup-conflict-id]')?.dataset.pdmBackupConflictId;
      const item = backup.page.items.find(entry => entry.conflictId === id);
      if (!item?.decisionRequired) return;
      if (selected.has(id)) selected.delete(id); else selected.set(id, backupSelectionProjection(item));
    }
    backup.batchMessage = '';
    clearBackupStatus(backup);
    byId('ie-conflict-list')?.querySelectorAll('.ie-item-check').forEach(button => {
      const checked = selected.has(button.closest('[data-pdm-backup-conflict-id]').dataset.pdmBackupConflictId);
      button.setAttribute('aria-checked', String(checked)); updateBackupText(button, checked ? '✓' : '');
    });
    preserveProductFocus(activeBackupModal(), () => renderBackupFixedActions(backup), backupPreviewFocusKeys());
  }

  function setAllBackupDecisions(decision) {
    const backup = backupState();
    if (!backup?.previewTicket || backup.pending ||
        !['OVERWRITE', 'SKIP', ...(backup.kind === 'NOTE' ? ['KEEP'] : [])].includes(decision)) return;
    const ids = [...backup.selected[backup.kind].keys()]; if (!ids.length) return;
    clearBackupReads(backup, 'decision', true);
    backup.batch = {ids, completed: 0, offset: 0, decision, chunk: []}; backup.batchMessage = '';
    submitNextBackupBatch(backup);
  }

  function submitNextBackupBatch(backup) {
    const batch = backup.batch; if (!batch) return;
    batch.chunk = batch.ids.slice(batch.offset, batch.offset + 100);
    if (!batch.chunk.length) {
      const remaining = batch.ids.length - batch.completed;
      backup.batchMessage = fixedText(`本次批量已暂存 ${batch.completed} 项决定，所选项目中 ${remaining} 项未更新，保留原决定。`,
        `This batch saved ${batch.completed} decisions; ${remaining} selected items were unchanged and kept their previous decisions.`);
      if (backup.kind === 'NOTE' && batch.decision === 'OVERWRITE' &&
          [...backup.selected.NOTE.values()].some(item => item.targetCount > 1)) backup.batchMessage = fixedText(
        `已暂存 ${batch.completed} 项决定；${remaining} 项保留原决定。多候选记事请逐项选择目标并确认覆盖。`,
        `Saved ${batch.completed} decisions; ${remaining} unchanged. For notes with multiple targets, choose a target and confirm overwrite individually.`);
      backup.batch = null; refreshBackupDecisions(backup, true); return;
    }
    const id = requestId(); setBackupPending(backup, 'all-decision', id);
    runtime.bridge.setAllBackupConflictDecisionsV1(id, runtime.pageEpoch, runtime.sessionEpoch, backup.previewTicket,
      backup.kind, batch.chunk, batch.decision, ack => {
        if (rejectBackupPendingAck(backup, id, 'all-decision', ack)) finishBackupBatchFailure(backup, ack?.errorCode || 'INTERNAL_FAILURE');
      });
  }

  function finishBackupBatchFailure(backup, errorCode) {
    const batch = backup.batch; if (!batch) return;
    backup.batchMessage = fixedText(`本次批量已暂存 ${batch.completed} 项，剩余 ${batch.ids.length - batch.completed} 项仍选中。${errorText(errorCode)}`,
      `This batch saved ${batch.completed} decisions; ${batch.ids.length - batch.completed} items remain selected. ${errorText(errorCode)}`);
    backup.batch = null;
    if (errorCode === 'SECRET_LEASE_EXPIRED') discardBackupSource(backup);
    else listBackupConflicts(backup, backup.cursor, false, true);
  }

  function refreshBackupDecisions(backup, sameTarget) {
    // 全部清单的成员、顺序与分页不随决定变化，回执已含变化项和权威汇总。
    if (sameTarget && backup.page && backup.statusFilter === 'ALL' && backup.fieldFilter === 'ALL') {
      updateBackupProgress(backup, false);
      renderBackupPreview(backup);
    } else listBackupConflicts(backup, backup.cursor, false, sameTarget);
  }

  function onBackupDecisionChanged(kind, request, pageEpoch, sessionEpoch, errorCode, result) {
    const backup = runtime.backup;
    if (kind === 'decision' && backup?.pending?.kind === 'replay-decision') kind = 'replay-decision';
    if (!finishBackupPending(backup, request, pageEpoch, sessionEpoch, kind)) return;
    if (errorCode !== 'OK') {
      if (kind === 'replay-decision') {
        backup.draft.clear(); backup.restoreQueue = []; listBackupConflicts(backup, '', false); return;
      }
      if (kind === 'all-decision') { finishBackupBatchFailure(backup, errorCode); return; }
      if (errorCode === 'SECRET_LEASE_EXPIRED') { discardBackupSource(backup); return; }
      showBackupError(backup, errorCode); loadBackupComparisonFields(backup); return;
    }
    const page = backupPage(result);
    if (!page || page.kind !== backup.kind) {
      discardBackupSource(backup);
      return;
    }
    backup.preview.summary = page.summary;
    if (backup.page) {
      const updated = new Map(page.updatedItems.map(item => [item.conflictId, item]));
      backup.page.items = backup.page.items.map(item => updated.get(item.conflictId) || item);
      backup.page.unresolved = page.unresolved;
      backup.page.summary = page.summary;
    }
    if (kind === 'all-decision') {
      const batch = backup.batch;
      if (!batch) return;
      if (page.appliedIds.length + page.remainingIds.length !== batch.chunk.length ||
          [...page.appliedIds, ...page.remainingIds].some(id => !batch.chunk.includes(id)) ||
          page.updatedItems.length !== batch.chunk.length || page.updatedItems.some(item => !batch.chunk.includes(item.conflictId))) {
        discardBackupSource(backup); return;
      }
      for (const id of page.appliedIds) {
        backup.draft.set(id, batch.decision); backup.selected[backup.kind].delete(id);
      }
      for (const id of page.remainingIds) {
        const selected = backup.selected[backup.kind].get(id);
        const updated = page.updatedItems.find(item => item.conflictId === id);
        if (selected && updated) backup.selected[backup.kind].set(id, backupSelectionProjection(updated));
        backup.draft.delete(id);
      }
      batch.completed += page.appliedIds.length; batch.offset += batch.chunk.length;
      submitNextBackupBatch(backup); return;
    }
    if (kind === 'replay-decision') { replayNextBackupDecision(backup); return; }
    if (page.updatedItems.length !== 1 || page.updatedItems[0].conflictId !== backup.pendingConflictId) {
      discardBackupSource(backup); return;
    }
    if (['OVERWRITE', 'KEEP', 'SKIP'].includes(backup.pendingDecision)) backup.draft.set(backup.pendingConflictId, backup.pendingDecision);
    else backup.draft.delete(backup.pendingConflictId);
    const selected = backup.selected[backup.kind].get(backup.pendingConflictId);
    const projected = page.updatedItems.find(item => item.conflictId === backup.pendingConflictId);
    if (selected && projected) backup.selected[backup.kind].set(backup.pendingConflictId, backupSelectionProjection(projected));
    const keepOrdinaryValues = ['OVERWRITE', 'KEEP', 'SKIP'].includes(backup.pendingDecision);
    backup.pendingConflictId = ''; backup.pendingDecision = '';
    refreshBackupDecisions(backup, keepOrdinaryValues);
  }

  function loadBackupComparisonFields(backup) {
    if (!backup?.previewTicket || !backup.page || backup.pending || document.hidden ||
        !runtime.ready || runtime.state !== 'UNLOCKED' || runtime.pageEpoch <= 0 || runtime.sessionEpoch <= 0 ||
        !runtime.bridge || !backupCurrent(backup, backup.generation)) return;
    const detail = byId('ie-comparison-detail');
    const item = backup.page.items.find(entry => entry.conflictId === backup.activeConflictId);
    if (!detail || !item || detail.dataset.pdmBackupIdentity !== JSON.stringify([
      backup.previewTicket, item.kind, item.conflictId, item.targetIndex, item.targetSelected, state.lang,
    ])) return;
    detail.querySelectorAll('.ie-comparison-field').forEach(row => {
      if (!['PASSWORD', 'TOTP', 'RECOVERY_CODES'].includes(row.dataset.pdmBackupField)) beginBackupFieldRead(backup, row, false);
      else if (!backup.reads.has(`${item.conflictId}:${row.dataset.pdmBackupField}`)) {
        row.querySelectorAll('[data-pdm-backup-placeholder]').forEach(target => {
          target.textContent = target.dataset.pdmBackupPlaceholder;
        });
      }
    });
  }

  function beginBackupFieldRead(backup, row, priority) {
    const conflictId = row.closest('[data-pdm-backup-conflict-id]')?.dataset.pdmBackupConflictId;
    const field = row.dataset.pdmBackupField;
    if (!conflictId || backup.pending) return;
    const key = `${conflictId}:${field}`;
    if (backup.reads.has(key)) return;
    const read = {key, conflictId, field, row, button: row.querySelector('[data-pdm-backup-action="read-field"]'),
      targets: [...row.querySelectorAll('[data-pdm-backup-side]')], secret: ['PASSWORD', 'TOTP', 'RECOVERY_CODES'].includes(field),
      page: runtime.pageEpoch, session: runtime.sessionEpoch, generation: backup.generation,
      request: '', readId: '', offset: 0, offsets: [], nextOffset: 0, done: false, side: 0,
      values: ['', ''], deadline: 0, timer: 0, complete: false};
    for (const target of read.targets) target.dataset.pdmBackupSensitive = 'true';
    backup.reads.set(key, read); queueBackupRead(backup, read, priority);
  }

  function queueBackupRead(backup, read, priority) {
    read.complete = false;
    read.side = 0; read.values = ['', ''];
    for (const target of read.targets) {
      if (read.secret) target.textContent = target.dataset.pdmBackupPlaceholder || '';
      target.setAttribute('aria-busy', 'true');
    }
    read.row.setAttribute('aria-busy', 'true');
    if (priority) backup.readQueue.unshift(read); else backup.readQueue.push(read);
    runNextBackupRead(backup);
  }

  function runNextBackupRead(backup) {
    if (backup.activeRead || backup.pending || !backupCurrent(backup, backup.generation)) return;
    const read = backup.readQueue.shift(); if (!read) return;
    if (backup.reads.get(read.key) !== read || !read.row.isConnected) { runNextBackupRead(backup); return; }
    backup.activeRead = read; requestBackupFieldChunk(backup, read);
  }

  function readBackupConflictField(target) {
    const backup = backupState(); const row = target.closest('.ie-comparison-field');
    if (!backup?.previewTicket || backup.pending || !row) return;
    const key = `${row.closest('[data-pdm-backup-conflict-id]').dataset.pdmBackupConflictId}:${row.dataset.pdmBackupField}`;
    const existing = backup.reads.get(key);
    if (existing) {
      clearBackupRead(existing, 'manual_hide'); backup.reads.delete(key);
      backup.readQueue = backup.readQueue.filter(read => read !== existing);
      if (backup.activeRead === existing) backup.activeRead = null;
      runNextBackupRead(backup);
    } else beginBackupFieldRead(backup, row, true);
  }

  function navigateBackupField(target, previous) {
    const backup = backupState(); const row = target.closest('.ie-comparison-field');
    if (!backup || backup.pending || !row) return;
    const read = backup.reads.get(`${row.closest('[data-pdm-backup-conflict-id]').dataset.pdmBackupConflictId}:${row.dataset.pdmBackupField}`);
    if (!read || read.request || backup.readQueue.includes(read) || read.secret && read.deadline <= performance.now()) return;
    if (previous) { if (!read.offsets.length) return; read.offset = read.offsets.pop(); }
    else { if (read.done) return; read.offsets.push(read.offset); read.offset = read.nextOffset; }
    if (!read.secret && read.deadline <= performance.now()) { read.readId = ''; read.deadline = 0; }
    if (read.secret && read.readId) window.pdmSensitiveDom?.clearLease(read.readId, 'navigation');
    queueBackupRead(backup, read, true);
  }

  function requestBackupFieldChunk(backup, read) {
    if (!backupCurrent(backup, read.generation) || backup.reads.get(read.key) !== read) return;
    const id = requestId(); read.request = id;
    const method = read.secret ? 'readBackupConflictFieldChunkV1' : 'readBackupComparisonFieldChunkV1';
    runtime.bridge[method](id, read.page, read.session, backup.previewTicket, read.conflictId,
      read.side === 0 ? 'CURRENT' : 'INCOMING', read.field, read.readId, read.offset, ack => {
        if (!ack?.accepted && backup.reads.get(read.key) === read) failBackupRead(backup, read, ack?.errorCode || 'INTERNAL_FAILURE');
      });
  }

  function failBackupRead(backup, read, errorCode) {
    if (!read.secret && read.readId && errorCode === 'SECRET_LEASE_EXPIRED') {
      read.readId = ''; read.deadline = 0; read.side = 0; read.values = ['', ''];
      requestBackupFieldChunk(backup, read); return;
    }
    clearBackupRead(read, 'field_failure'); backup.reads.delete(read.key);
    if (backup.activeRead === read) backup.activeRead = null;
    showBackupFieldError(backup, errorCode);
    runNextBackupRead(backup);
  }

  function formatBackupFieldValue(text, read) {
    if (read.field === 'RECOVERY_CODES') {
      const values = JSON.parse(text);
      if (!Array.isArray(values) || values.some(item => !hasExactKeys(item, ['used', 'value']) ||
          typeof item.value !== 'string' || typeof item.used !== 'boolean')) throw new TypeError('invalid recovery comparison');
      return values.map((item, index) => `${read.offset + index + 1}. ${item.value} · ${fixedText(item.used ? '已用' : '未用', item.used ? 'Used' : 'Unused')}`).join('\n');
    }
    if (read.field === 'FAVORITE' && ['true', 'false', '0', '1'].includes(text)) return fixedText(
      ['true', '1'].includes(text) ? '已收藏' : '未收藏', ['true', '1'].includes(text) ? 'Favorite' : 'Not favorite');
    if (read.field === 'STRENGTH' && ['weak', 'fair', 'strong'].includes(text)) return t(`common.strength.${text}`);
    return text;
  }

  function onBackupFieldChunk(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    const backup = runtime.backup; const read = backup?.activeRead;
    if (!backup || !read || read.request !== request || !backupCurrent(backup, read.generation) ||
        read.page !== pageEpoch || read.session !== sessionEpoch || backup.reads.get(read.key) !== read) {
      if (result && typeof result === 'object') {
        result.text = '';
        if (isOpaqueId(result.readId) && runtime.bridge && runtime.state === 'UNLOCKED' &&
            pageEpoch === runtime.pageEpoch && sessionEpoch === runtime.sessionEpoch &&
            !Array.from(backup?.reads.values() || []).some(current => current.readId === result.readId)) {
          runtime.bridge.closeBackupPreviewV1(requestId(), pageEpoch, sessionEpoch, result.readId, () => {});
        }
      }
      return;
    }
    read.request = '';
    const chars = typeof result?.text === 'string' ? recordFieldCharacterCount(result.text, 8192) : -1;
    if (errorCode !== 'OK' || !hasExactKeys(result, ['done', 'expiresInMs', 'nextOffset', 'readId', 'text']) ||
        chars < 0 || chars > 8192 || result.text.includes('\0') || new TextEncoder().encode(result.text).length > 32768 ||
        !isOpaqueId(result.readId) || read.readId && read.readId !== result.readId ||
        !Number.isSafeInteger(result.nextOffset) || result.nextOffset < read.offset ||
        typeof result.done !== 'boolean' || !result.done && result.nextOffset <= read.offset ||
        !Number.isSafeInteger(result.expiresInMs) || result.expiresInMs < 1 || result.expiresInMs > 30000 ||
        read.side === 1 && (read.nextOffset !== result.nextOffset || read.done !== result.done)) {
      if (result && typeof result === 'object') result.text = '';
      failBackupRead(backup, read, errorCode === 'OK' ? 'INTERNAL_FAILURE' : errorCode); return;
    }
    read.readId = result.readId;
    read.deadline = Math.min(read.deadline || Infinity, performance.now() + result.expiresInMs);
    try { read.values[read.side] = formatBackupFieldValue(result.text, read); }
    catch (_error) { result.text = ''; failBackupRead(backup, read, 'INTERNAL_FAILURE'); return; }
    result.text = '';
    if (read.side === 0) {
      read.nextOffset = result.nextOffset; read.done = result.done; read.side = 1;
      requestBackupFieldChunk(backup, read); return;
    }
    const ttl = Math.floor(read.deadline - performance.now());
    if (ttl < 1 || !read.row.isConnected) { failBackupRead(backup, read, 'SECRET_LEASE_EXPIRED'); return; }
    try {
      if (read.secret) {
        for (const target of read.targets) target.dataset.pdmSensitive = 'true';
        window.pdmSensitiveDom.bindLease(read.readId, 'CONFLICT_REVEAL', ttl, read.targets, true);
      }
      const item = backup.page.items.find(entry => entry.conflictId === read.conflictId);
      read.targets.forEach((target, index) => {
        target.classList.remove('ie-loading-dots');
        target.textContent = index === 0 && !item.targetSelected ?
          fixedText(item.targetCount ? '请选择比较目标' : '无目标记录', item.targetCount ? 'Select a target' : 'No existing record') :
          read.values[index] || '—';
        target.removeAttribute('aria-busy');
      });
    } catch (_error) { failBackupRead(backup, read, 'INTERNAL_FAILURE'); return; }
    read.values = ['', '']; read.complete = true; read.row.removeAttribute('aria-busy');
    setEnabled(read.button, !backup.pending);
    read.button.hidden = !read.secret;
    read.button.setAttribute('aria-pressed', 'true'); read.button.setAttribute('aria-label', fixedText('隐藏两侧', 'Hide both sides'));
    if (read.secret) read.button.innerHTML = svgIcon('eye-closed', 16);
    setEnabled(read.row.querySelector('[data-pdm-backup-action="field-previous"]'), !backup.pending && read.offsets.length > 0);
    setEnabled(read.row.querySelector('[data-pdm-backup-action="field-next"]'), !backup.pending && !read.done);
    read.row.querySelector('.ie-field-position').textContent = read.offsets.length || !read.done ?
      fixedText(`第 ${read.offsets.length + 1} 片`, `Part ${read.offsets.length + 1}`) : '';
    window.clearTimeout(read.timer);
    read.timer = read.secret ? window.setTimeout(() => {
      if (backup.reads.get(read.key) !== read) return;
      clearBackupRead(read, 'lease_expired'); backup.reads.delete(read.key);
      if (backup.activeRead === read) backup.activeRead = null;
      runNextBackupRead(backup);
    }, ttl) : 0;
    backup.activeRead = null; runNextBackupRead(backup);
  }

  function executeBackupOperation() {
    const backup = backupState(); const password = byId('ie-password'); const confirm = byId('ie-confirm');
    if (!backup || backup.pending || !(password instanceof HTMLInputElement) || !(confirm instanceof HTMLInputElement)) return;
    if (backup.mode === 'export') {
      const counts = window.PdmExportSelection.counts(backup.exportSelection);
      if (backup.scope === 'CUSTOM' && counts.passwordCount + counts.noteCount === 0) return;
      if (!backup.destinationTicket) {
        showBackupMessage(
          backup,
          'dialog.ie.error.path',
          {},
          '#ie-browse-btn',
        );
        return;
      }
      if (!password.value) {
        showBackupMessage(
          backup,
          'dialog.ie.error.password',
          {},
          password,
        );
        return;
      }
      if (password.value !== confirm.value) {
        showBackupMessage(
          backup,
          'dialog.ie.error.mismatch',
          {},
          confirm,
        );
        return;
      }
      const id = requestId(); setBackupPending(backup, 'export', id); const secret = password.value; const confirmation = confirm.value;
      scrubBackupInputs();
      runtime.bridge.exportEncryptedBackupV1(id, runtime.pageEpoch, runtime.sessionEpoch, backup.destinationTicket, backup.scope, secret, confirmation, (ack) => {
        rejectBackupPendingAck(backup, id, 'export', ack);
      });
      return;
    }
    if (!backup.previewTicket || !backup.page) {
      showBackupMessage(
        backup,
        'dialog.ie.error.preview',
        {},
        '#ie-preview-btn',
      );
      return;
    }
    const unresolved = backup.kind === 'PASSWORD' && backup.preview.noteCount > 0 ? backup.page.unresolved : backup.preview.summary.unresolved;
    if (unresolved > 0) {
      const firstUnresolved = document.querySelector(
        '.ie-conflict-tag.undecided',
      )?.closest('.ie-conflict-item')?.querySelector(
        '[data-pdm-backup-action="decision"]',
      );
      showBackupMessage(
        backup,
        'dialog.ie.error.undecided',
        {n: unresolved},
        firstUnresolved || '#ie-execute-btn',
      );
      return;
    }
    clearBackupReads(backup, 'save_complete');
    if (backup.kind === 'PASSWORD' && backup.preview.noteCount > 0) {
      switchBackupStep('NOTE');
      return;
    }
    const id = requestId(); setBackupPending(backup, 'import', id);
    runtime.bridge.executeEncryptedBackupImportV1(id, runtime.pageEpoch, runtime.sessionEpoch, backup.previewTicket, (ack) => {
      rejectBackupPendingAck(backup, id, 'import', ack);
    });
  }

  function onBackupExported(
    request, pageEpoch, sessionEpoch, errorCode,
    _errorArgumentIndex, _retryAfterMs, result,
  ) {
    const backup = runtime.backup;
    if (!finishBackupPending(backup, request, pageEpoch, sessionEpoch, 'export')) return;
    if (errorCode !== 'OK' || !isBackupExportResult(result)) {
      if (errorCode === 'REVISION_CONFLICT' && backup.scope === 'CUSTOM') {
        showBackupStatus(backup, fixedText('所选记录已修改或删除，请重新选择并核对后再导出。',
          'Selected records changed or were removed. Choose and review them again before exporting.'), '#ie-select-records');
        return;
      }
      showBackupError(
        backup,
        errorCode || 'INTERNAL_FAILURE',
        ['SELECTION_EXPIRED', 'BACKUP_TARGET_IS_DATABASE'].includes(errorCode)
          ? '#ie-browse-btn'
          : '#ie-execute-btn',
      );
      return;
    }
    const text = t('toast.ie.exported').replace('{n}', String((result.passwordCount || 0) + (result.noteCount || 0))).replace('{file}', result.backupLabel);
    closeBackupDialog('export_complete', true); showToast(text, 'success');
  }

  function onBackupImported(
    request, pageEpoch, sessionEpoch, errorCode,
    _errorArgumentIndex, _retryAfterMs, result,
  ) {
    const backup = runtime.backup;
    if (!finishBackupPending(backup, request, pageEpoch, sessionEpoch, 'import')) return;
    if (errorCode !== 'OK') {
      discardConsumedBackupPreview(backup, errorCode);
      return;
    }
    if (!isBackupImportResult(result)) {
      discardConsumedBackupPreview(backup, 'INTERNAL_FAILURE');
      return;
    }
    if (!result.changed) {
      closeBackupDialog('import_complete', true);
      showToast(t('toast.ie.no_changes'), 'info');
      return;
    }
    const text = t('toast.ie.imported').replace('{added}', String(result.imported)).replace('{updated}', String(result.overwritten)).replace('{skipped}', String(result.skipped));
    closeBackupDialog('import_complete', true); showToast(text, 'success');
    if (!window.pdmBackupWindow) { resetVaultPagePosition(); requestVaultPage(); }
  }

  function showDeleteError(
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const error = byId('m4-delete-error');
    if (!error) return;
    error.setAttribute('role', 'status');
    error.setAttribute('aria-live', 'polite');
    error.setAttribute('aria-atomic', 'true');
    const visible = setRuntimeText(
      error,
      text,
      fixedZh,
      fixedEn,
      i18nKey,
    );
    error.classList.toggle('show', visible);
    error.setAttribute('aria-hidden', visible ? 'false' : 'true');
  }

  function clearDeleteRecordState() {
    runtime.pendingDeletePrepare = '';
    runtime.pendingDeleteCommit = '';
    runtime.deleteModalActive = false;
    runtime.deleteRecordId = 0;
    runtime.deleteRevision = '';
    runtime.deleteLabel = '';
  }

  function closeDeleteRecordDialog(
    reason = 'modal_close',
    force = false,
  ) {
    void reason;
    if (
      !force &&
      (runtime.pendingDeletePrepare || runtime.pendingDeleteCommit)
    ) {
      return;
    }
    clearDeleteRecordState();
    closeDemoModal();
    refreshControls();
  }

  function openDeleteRecordDialog(details) {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      activeCreateModal() ||
      activeEditModal() ||
      activeDeleteModal() ||
      runtime.pendingDeletePrepare ||
      runtime.pendingDeleteCommit ||
      !details ||
      !Number.isSafeInteger(details.recordId) ||
      !isRevision(details.revision) ||
      typeof details.platform !== 'string' ||
      details.platform.length < 1
    ) {
      return;
    }
    const html = `
      <div class="modal-header">
        <div class="modal-title">${t('dialog.delete.title')}</div>
        <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div class="delete-confirm-icon">${svgIcon('warning', 32)}</div>
        <div class="delete-confirm-text" id="m4-delete-text"></div>
        <div class="delete-confirm-desc" id="m4-delete-desc">${t('dialog.delete.desc')}</div>
        <div class="modal-form-error" id="m4-delete-error"
             aria-hidden="true"></div>
      </div>
      <div class="modal-footer">
        <div class="modal-footer-right">
          <button class="btn btn-sm delete-cancel"
                  data-pdm-onclick="closeModal()">
            ${t('dialog.button.cancel')}
          </button>
          <button class="btn btn-danger btn-sm" id="m4-delete-confirm"
                  data-pdm-onclick="confirmDeleteRecord(${details.recordId})">
            ${t('dialog.button.delete')}
          </button>
        </div>
      </div>
    `;
    const overlay = openDemoModal(
      html,
      {
        closeOnBackdrop: false,
        initialFocusSelector: '.delete-cancel',
      },
    );
    if (!overlay) {
      showErrorToast('INTERNAL_FAILURE');
      return;
    }
    overlay.dataset.pdmM4Delete = 'true';
    overlay.querySelector('.modal')?.setAttribute(
      'aria-describedby',
      'm4-delete-text m4-delete-desc',
    );
    const text = byId('m4-delete-text');
    if (text) {
      text.textContent = t('dialog.delete.confirm').replace(
        '{platform}',
        details.platform,
      );
    }
    runtime.deleteModalActive = true;
    runtime.deleteRecordId = details.recordId;
    runtime.deleteRevision = details.revision;
    runtime.deleteLabel = details.platform;
    refreshControls();
  }

  function normalizeDeleteChallenge(result) {
    if (
      !result ||
      typeof result.deleteTicket !== 'string' ||
      !/^[A-Za-z0-9_-]{16,64}$/.test(result.deleteTicket) ||
      typeof result.entityLabel !== 'string' ||
      result.entityLabel.includes('\0') ||
      recordFieldCharacterCount(result.entityLabel, 256) < 1 ||
      recordFieldCharacterCount(result.entityLabel, 256) > 256 ||
      new TextEncoder().encode(result.entityLabel).length > 1024 ||
      !Number.isSafeInteger(result.expiresInMs) ||
      result.expiresInMs < 1 ||
      result.expiresInMs > 60000
    ) {
      return null;
    }
    return {
      deleteTicket: result.deleteTicket,
      entityLabel: result.entityLabel,
    };
  }

  function submitDeleteRecord() {
    if (
      !activeDeleteModal() ||
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pendingDeletePrepare ||
      runtime.pendingDeleteCommit ||
      !Number.isSafeInteger(runtime.deleteRecordId) ||
      !isRevision(runtime.deleteRevision)
    ) {
      return;
    }
    showDeleteError('');
    const id = requestId();
    runtime.pendingDeletePrepare = id;
    refreshControls();
    runtime.bridge.prepareDeleteRecordV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      runtime.deleteRecordId,
      runtime.deleteRevision,
      (ack) => {
        if (
          runtime.pendingDeletePrepare === id &&
          (
            !ack ||
            ack.accepted !== true ||
            ack.errorCode !== 'OK'
          )
        ) {
          runtime.pendingDeletePrepare = '';
          showDeleteError(errorText(ack && ack.errorCode));
          refreshControls();
        }
      },
    );
  }

  function onDeletePrepared(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingDeletePrepare ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch ||
      !activeDeleteModal()
    ) {
      if (result && typeof result === 'object') {
        result.deleteTicket = '';
      }
      return;
    }
    runtime.pendingDeletePrepare = '';
    if (errorCode !== 'OK') {
      if (
        errorCode === 'SESSION_REQUIRED' ||
        errorCode === 'STALE_SESSION' ||
        errorCode === 'STALE_PAGE'
      ) {
        closeDeleteRecordDialog('session_invalidated', true);
        applyLocked('session_invalidated');
        return;
      }
      if (
        errorCode === 'NOT_FOUND' ||
        errorCode === 'REVISION_CONFLICT'
      ) {
        closeDeleteRecordDialog('record_changed');
        if (errorCode === 'NOT_FOUND') {
          showFixedToast(
            '记录已不存在，列表将自动刷新。',
            'The record no longer exists. The list will refresh.',
            'error',
          );
        } else {
          showErrorToast(errorCode);
        }
        resetVaultPagePosition();
        requestVaultPage();
        return;
      }
      showDeleteError(errorText(errorCode));
      refreshControls();
      return;
    }
    const challenge = normalizeDeleteChallenge(result);
    if (result && typeof result === 'object') {
      result.deleteTicket = '';
    }
    if (!challenge) {
      showDeleteError(errorText('INTERNAL_FAILURE'));
      refreshControls();
      return;
    }
    runtime.deleteLabel = challenge.entityLabel;
    const id = requestId();
    runtime.pendingDeleteCommit = id;
    refreshControls();
    runtime.bridge.deleteRecordV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      challenge.deleteTicket,
      (ack) => {
        challenge.deleteTicket = '';
        if (
          runtime.pendingDeleteCommit === id &&
          (
            !ack ||
            ack.accepted !== true ||
            ack.errorCode !== 'OK'
          )
        ) {
          runtime.pendingDeleteCommit = '';
          showDeleteError(errorText(ack && ack.errorCode));
          refreshControls();
        }
      },
    );
  }

  function onRecordDeleted(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingDeleteCommit ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch ||
      !activeDeleteModal()
    ) {
      return;
    }
    runtime.pendingDeleteCommit = '';
    if (errorCode !== 'OK') {
      if (
        errorCode === 'SESSION_REQUIRED' ||
        errorCode === 'STALE_SESSION' ||
        errorCode === 'STALE_PAGE'
      ) {
        closeDeleteRecordDialog('session_invalidated', true);
        applyLocked('session_invalidated');
        return;
      }
      if (
        errorCode === 'NOT_FOUND' ||
        errorCode === 'REVISION_CONFLICT'
      ) {
        closeDeleteRecordDialog('record_changed');
        if (errorCode === 'NOT_FOUND') {
          showFixedToast(
            '记录已不存在，列表将自动刷新。',
            'The record no longer exists. The list will refresh.',
            'error',
          );
        } else {
          showErrorToast(errorCode);
        }
        resetVaultPagePosition();
        requestVaultPage();
        return;
      }
      showDeleteError(errorText(errorCode));
      refreshControls();
      return;
    }
    const validResult = Boolean(
      result &&
      result.deletedId === runtime.deleteRecordId &&
      isRevision(result.dataRevision) &&
      isRevision(result.healthRevision)
    );
    if (!validResult) {
      closeDeleteRecordDialog('invalid_completion');
      showErrorToast('INTERNAL_FAILURE');
      resetVaultPagePosition();
      requestVaultPage();
      return;
    }
    const focusKeys = vaultDeleteFocusKeys(runtime.deleteRecordId);
    const label = runtime.deleteLabel;
    closeDeleteRecordDialog('delete_complete');
    clearSelectedDetails();
    showCompositeI18nToast(
      'toast.deleted.prefix',
      label,
      '',
      'success',
    );
    resetVaultPagePosition();
    requestVaultPage();
    window.pdmFocusVisibility?.restore(null, focusKeys);
  }

  function normalizeNoteSummary(value) {
    const longFields = normalizedNoteLongFields(value?.longFields);
    const expectedKeys = ['contentPreview', 'favorite', 'longFields', 'noteId',
      'previewTruncated', 'revision', 'title', 'updatedDate'];
    if (
      !value ||
      typeof value !== 'object' ||
      JSON.stringify(Object.keys(value).sort()) !== JSON.stringify(expectedKeys) ||
      !Number.isSafeInteger(value.noteId) ||
      value.noteId < 1 ||
      !isRevision(value.revision) || !longFields ||
      typeof value.title !== 'string' ||
      (!longFields.includes('TITLE') && !noteFieldFits('TITLE', value.title)) ||
      (longFields.includes('TITLE') && !noteFieldFits('TITLE', value.title)) ||
      typeof value.contentPreview !== 'string' ||
      value.contentPreview.includes('\0') ||
      recordFieldCharacterCount(value.contentPreview, 160) > 160 ||
      new TextEncoder().encode(value.contentPreview).length > 640 ||
      typeof value.previewTruncated !== 'boolean' ||
      typeof value.favorite !== 'boolean' ||
      typeof value.updatedDate !== 'string' ||
      !/^\d{4}-\d{2}-\d{2}$/.test(value.updatedDate)
    ) {
      return null;
    }
    return {
      noteId: value.noteId,
      revision: value.revision,
      title: value.title,
      contentPreview: value.contentPreview,
      previewTruncated: value.previewTruncated,
      longFields,
      favorite: value.favorite,
      updatedDate: value.updatedDate,
    };
  }

  function normalizeNotePage(value) {
    const counts = value?.counts;
    if (
      !value ||
      typeof value !== 'object' ||
      !Array.isArray(value.items) ||
      value.items.length > 100 ||
      !Number.isSafeInteger(value.total) ||
      value.total < value.items.length ||
      !counts || typeof counts !== 'object' ||
      JSON.stringify(Object.keys(counts).sort()) !== '["all","favorite"]' ||
      !Number.isSafeInteger(counts.all) || counts.all < value.total ||
      !Number.isSafeInteger(counts.favorite) || counts.favorite < 0 || counts.favorite > counts.all ||
      typeof value.nextCursor !== 'string' ||
      value.nextCursor.length > 128 ||
      !/^[A-Za-z0-9_-]*$/.test(value.nextCursor) ||
      !isRevision(value.noteRevision)
    ) {
      return null;
    }
    const items = [];
    const ids = new Set();
    for (const valueItem of value.items) {
      const item = normalizeNoteSummary(valueItem);
      if (!item || ids.has(item.noteId)) return null;
      ids.add(item.noteId);
      items.push(item);
    }
    return {
      items,
      total: value.total,
      counts: {all: counts.all, favorite: counts.favorite},
      nextCursor: value.nextCursor,
      noteRevision: value.noteRevision,
    };
  }

  function normalizeNoteDetails(value) {
    const longFields = normalizedNoteLongFields(value?.longFields);
    const expectedKeys = ['content', 'favorite', 'longFields', 'noteId', 'revision',
      'title', 'updatedDate'];
    if (
      !value ||
      typeof value !== 'object' ||
      JSON.stringify(Object.keys(value).sort()) !== JSON.stringify(expectedKeys) ||
      !Number.isSafeInteger(value.noteId) ||
      value.noteId < 1 ||
      !isRevision(value.revision) || !longFields ||
      typeof value.title !== 'string' || typeof value.content !== 'string' ||
      (!longFields.includes('TITLE') && !noteFieldFits('TITLE', value.title)) ||
      (!longFields.includes('CONTENT') && !noteFieldFits('CONTENT', value.content)) ||
      (longFields.includes('TITLE') && !noteFieldFits('TITLE', value.title)) ||
      (longFields.includes('CONTENT') && !noteFieldFits('CONTENT', value.content)) ||
      typeof value.favorite !== 'boolean' ||
      typeof value.updatedDate !== 'string' ||
      !/^\d{4}-\d{2}-\d{2}$/.test(value.updatedDate)
    ) {
      return null;
    }
    return {
      noteId: value.noteId,
      revision: value.revision,
      title: value.title,
      content: value.content,
      longFields,
      favorite: value.favorite,
      updatedDate: value.updatedDate,
    };
  }

  function scrubNotePageResult(result) {
    if (!result || !Array.isArray(result.items)) return;
    for (const item of result.items) {
      if (!item || typeof item !== 'object') continue;
      item.title = '';
      item.contentPreview = '';
      item.longFields = [];
    }
  }

  function scrubNoteDetailsResult(result) {
    if (!result || typeof result !== 'object') return;
    result.title = '';
    result.content = '';
    result.longFields = [];
  }

  const NOTE_FIELDS = Object.freeze({
    TITLE: {key: 'title', limit: 256, bytes: 1024},
    CONTENT: {key: 'content', limit: 65536, bytes: 262144},
  });

  function normalizedNoteLongFields(value) {
    if (!Array.isArray(value) || value.length > 2 || new Set(value).size !== value.length) return null;
    if (value.some((field) => !NOTE_FIELDS[field])) return null;
    return Object.freeze([...value]);
  }

  function noteFieldFits(field, value) {
    const definition = NOTE_FIELDS[field];
    return Boolean(definition && typeof value === 'string' && !value.includes('\0') &&
      recordFieldCharacterCount(value, definition.limit) <= definition.limit &&
      new TextEncoder().encode(value).length <= definition.bytes);
  }

  function noteDraftDirty() {
    const draft = runtime.noteDraft;
    return Boolean(draft && (draft.title !== draft.originalTitle || draft.content !== draft.originalContent));
  }

  function cancelNoteFieldRead() {
    const read = runtime.noteFieldRead;
    runtime.noteFieldRead = null;
    runtime.pendingNoteFieldRead = '';
    if (!read) return;
    read.cancelled = true;
    if (read.request && runtime.bridge && read.page === runtime.pageEpoch) {
      runtime.bridge.cancelRequestV1(requestId(), read.page, read.request, () => {});
    }
    if (read.readId && runtime.bridge && read.page === runtime.pageEpoch && read.session === runtime.sessionEpoch) {
      runtime.bridge.releaseNoteFieldReadV1(requestId(), read.page, read.session, read.readId, () => {});
    }
  }

  function noteFieldReadCurrent(read) {
    return Boolean(read && !read.cancelled && runtime.state === 'UNLOCKED' &&
      runtime.noteFieldRead === read && read.page === runtime.pageEpoch &&
      read.session === runtime.sessionEpoch && runtime.selectedNoteId === read.noteId &&
      runtime.selectedNoteRevision === read.revision && runtime.selectedNoteDetails);
  }

  function syncNoteSummaryFromDetails(details) {
    const item = runtime.noteItems.find(
      (value) => value.noteId === details?.noteId,
    );
    if (!item || details.longFields.length) return;
    item.revision = details.revision;
    item.title = details.title;
    item.contentPreview = details.content.slice(0, 160);
    item.favorite = details.favorite;
    item.longFields = [...(details.summaryLongFields || [])];
    item.previewTruncated = (
      details.content.length > 160 || item.longFields.includes('TITLE')
    );
    item.updatedDate = details.updatedDate;
  }

  function readNoteField(details, field) {
    if (!details.longFields.includes(field) || runtime.noteFieldRead || !runtime.bridge) return;
    const read = {noteId: details.noteId, revision: details.revision, field,
      page: runtime.pageEpoch, session: runtime.sessionEpoch, readId: '', offset: 0,
      request: '', text: '', cancelled: false};
    runtime.noteFieldRead = read;
    requestNoteFieldChunk(read);
  }

  function requestNoteFieldChunk(read) {
    if (!noteFieldReadCurrent(read)) {
      cancelNoteFieldRead();
      return;
    }
    const id = requestId();
    read.request = id;
    runtime.pendingNoteFieldRead = id;
    runtime.bridge.readNoteFieldChunkV1(id, read.page, read.session, read.noteId,
      read.revision, read.field, read.readId, read.offset, (ack) => {
        if (noteFieldReadCurrent(read) && read.request === id && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
          finishNoteFieldRead(read, false, ack?.errorCode || 'INTERNAL_FAILURE');
        }
      });
  }

  function finishNoteFieldRead(read, success, errorCode = '') {
    if (runtime.noteFieldRead !== read) return;
    const details = runtime.selectedNoteDetails;
    runtime.noteFieldRead = null;
    runtime.pendingNoteFieldRead = '';
    if (read.readId && runtime.bridge && read.page === runtime.pageEpoch && read.session === runtime.sessionEpoch) {
      runtime.bridge.releaseNoteFieldReadV1(requestId(), read.page, read.session, read.readId, () => {});
    }
    if (success && details && details.noteId === read.noteId && details.revision === read.revision) {
      details[NOTE_FIELDS[read.field].key] = read.text;
      details.longFields = details.longFields.filter((field) => field !== read.field);
      if (runtime.noteEditRequestedId !== details.noteId) renderM4Notes();
      if (details.longFields.length) readNoteField(details, details.longFields[0]);
      else {
        syncNoteSummaryFromDetails(details);
        renderM4Notes();
      }
      return;
    }
    clearSelectedNoteDetails();
    if (errorCode) showErrorToast(errorCode);
    renderM4Notes();
  }

  function onNoteFieldChunk(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    const read = runtime.noteFieldRead;
    if (!read || read.request !== request || read.page !== pageEpoch || read.session !== sessionEpoch || !noteFieldReadCurrent(read)) {
      if (result && typeof result === 'object') {
        result.text = '';
        if (result.readId && runtime.bridge) runtime.bridge.releaseNoteFieldReadV1(requestId(), pageEpoch, sessionEpoch, result.readId, () => {});
      }
      return;
    }
    read.request = '';
    runtime.pendingNoteFieldRead = '';
    if (errorCode !== 'OK') {
      if (result) result.text = '';
      finishNoteFieldRead(read, false, errorCode);
      return;
    }
    const text = result?.text;
    const count = typeof text === 'string' ? recordFieldCharacterCount(text, 8192) : -1;
    const valid = typeof text === 'string' && count <= 8192 && new TextEncoder().encode(text).length <= 32768 &&
      typeof result.readId === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(result.readId) &&
      (!read.readId || read.readId === result.readId) && Number.isSafeInteger(result.nextOffset) &&
      result.nextOffset === read.offset + count && typeof result.done === 'boolean' &&
      (result.done || result.nextOffset > read.offset);
    if (!valid) {
      if (result) result.text = '';
      finishNoteFieldRead(read, false, 'INTERNAL_FAILURE');
      return;
    }
    read.readId = result.readId;
    read.offset = result.nextOffset;
    read.text += text;
    result.text = '';
    if (result.done) finishNoteFieldRead(read, true);
    else requestNoteFieldChunk(read);
  }

  function currentNoteRequestKey() {
    return JSON.stringify([
      runtime.pageEpoch,
      runtime.sessionEpoch,
      runtime.noteQuery,
      runtime.noteFilter,
      runtime.noteSort,
      runtime.noteCursor,
    ]);
  }

  function resetNotePagePosition() {
    runtime.noteCursor = '';
    runtime.noteNextCursor = '';
    runtime.noteCursorHistory = [];
    runtime.notePageInvalidated = false;
    runtime.notePageTarget = 0;
    clearSelectedNoteDetails();
  }

  function setNoteChipState() {
    projectNoteSort(runtime.noteSort);
    const all = byId('ncount-all'); if (all) all.textContent = String(runtime.noteAllCount);
    const favorite = byId('ncount-fav'); if (favorite) favorite.textContent = String(runtime.noteFavoriteCount);
    document.querySelectorAll('#page-notes .chip[data-nfilter]').forEach(
      (chip) => {
        const active = String(chip.dataset.nfilter || '').toUpperCase() === runtime.noteFilter;
        chip.classList.toggle('active', active);
        chip.setAttribute('aria-pressed', String(active));
      },
    );
  }

  function setProductNoteFilter(value) {
    if (runtime.state !== 'UNLOCKED' || noteWritePending()) return;
    if (noteDraftDirty()) {
      showUnsavedNoteWarning();
      return;
    }
    const normalized = String(value || '').toUpperCase();
    if (
      !['ALL', 'FAVORITE'].includes(normalized) ||
      normalized === runtime.noteFilter
    ) {
      return;
    }
    runtime.noteFilter = normalized;
    state.noteFilter = normalized.toLowerCase();
    resetNotePagePosition();
    queueNoteReload();
    setNoteChipState();
  }

  function acceptNoteAck(ack, pendingField, render) {
    if (ack && ack.accepted === true && ack.errorCode === 'OK') {
      return true;
    }
    runtime[pendingField] = '';
    if (pendingField === 'pendingNoteList') {
      runtime.pendingNoteListKey = '';
    }
    showErrorToast(ack && ack.errorCode);
    render();
    refreshControls();
    return false;
  }

  function noteCardText(value, fallback = '') {
    return escapeHtml(typeof value === 'string' ? value : fallback);
  }

  function noteCardElement(item) {
    const preparingEdit = runtime.noteEditRequestedId === item.noteId && runtime.noteEditReturnToOverview;
    const details = runtime.selectedNoteDetails?.noteId === item.noteId &&
      runtime.selectedNoteRevision === item.revision && !preparingEdit ? runtime.selectedNoteDetails : null;
    const draft = runtime.noteDraft?.noteId === item.noteId ? runtime.noteDraft : null;
    const reading = Boolean(runtime.pendingNoteDetails && runtime.selectedNoteId === item.noteId && !preparingEdit);
    const open = Boolean(details || reading);
    const editing = Boolean(draft);
    const title = draft?.title ?? details?.title ?? item.title;
    const content = draft?.content ?? details?.content ?? item.contentPreview;
    const loadingField = details?.longFields?.[0] || '';
    const card = document.createElement('article');
    card.setAttribute('role', 'group');
    card.className = `note-card${open ? ' is-open' : ''}${editing ? ' is-editing' : ''}`;
    card.dataset.id = String(item.noteId);
    card.dataset.pdmSensitive = 'true';
    card.dataset.previewTruncated = String(item.previewTruncated || item.longFields.length > 0);
    if (editing && runtime.pendingNoteSave) {
      card.tabIndex = -1;
      card.dataset.pdmNativeFocusKey = `note-action:${item.noteId}:pending`;
    }
    if (preparingEdit) card.setAttribute('aria-busy', 'true');
    let body = `
      <div class="note-card-preview" data-pdm-sensitive="true">${noteCardText(item.contentPreview)}</div>
      <div class="note-card-actions"><button type="button" class="btn-link" data-note-card-action="read">${escapeHtml(t('notes.cards.read'))}</button></div>`;
    if (reading) {
      body = `<div class="note-card-body" tabindex="0" aria-busy="true" data-pdm-sensitive="true">${escapeHtml(fixedText('正在读取记事…', 'Loading note…'))}</div>`;
    } else if (details && !editing) {
      body = `
        <div class="note-card-body" tabindex="0" data-pdm-sensitive="true" ${loadingField ? 'aria-busy="true"' : ''}>${noteCardText(loadingField ? fixedText('正在读取完整内容…', 'Loading full content…') : content)}</div>
        <div class="note-card-actions"><button type="button" class="btn-link" data-note-card-action="back" hidden>${escapeHtml(t('notes.cards.back'))}</button></div>`;
    } else if (editing) {
      const dirty = noteDraftDirty();
      const feedbackId = `note-form-feedback-${item.noteId}`;
      body = `
        <div class="note-card-editor">
          <input class="input" value="${noteCardText(title)}" aria-label="${escapeHtml(t('notes.input.title'))}" aria-describedby="${feedbackId}" data-note-card-input="title" data-pdm-sensitive="true">
          <textarea aria-label="${escapeHtml(t('notes.input.content'))}" aria-describedby="${feedbackId}" data-note-card-input="content" data-pdm-sensitive="true">${noteCardText(content)}</textarea>
          <div class="note-form-feedback" id="${feedbackId}" role="status"></div>
        </div>
          <div class="note-card-actions"><button type="button" class="btn btn-danger btn-sm" data-note-card-action="delete">${escapeHtml(t('notes.button.delete'))}</button><span class="note-card-actions-spacer"></span><button type="button" class="btn btn-sm" data-note-card-action="cancel">${escapeHtml(t('dialog.button.cancel'))}</button><button type="button" class="btn btn-primary btn-sm" data-note-card-action="save" ${dirty && !runtime.pendingNoteSave && !runtime.pendingNoteFavorite ? '' : 'disabled'}>${escapeHtml(t('notes.button.save'))}</button></div>`;
    }
    card.innerHTML = `
      <div class="note-card-heading"><h2 class="note-card-title" data-pdm-sensitive="true">${noteCardText(title)}</h2><button type="button" class="note-card-favorite ${item.favorite ? 'active' : ''}" aria-pressed="${String(item.favorite)}" aria-label="${escapeHtml(t('dialog.label.favorite'))}" data-note-card-action="favorite">${svgIcon('star', 18)}</button></div>
      ${body}
      <footer class="note-card-footer"><span data-pdm-sensitive="true">${escapeHtml(t('notes.cards.updated'))} ${noteCardText(item.updatedDate)}</span>${editing || reading ? '' : `<button type="button" class="note-card-edit" data-note-card-action="edit">${svgIcon('pencil', 16)} ${escapeHtml(t('vault.button.edit'))}</button>`}</footer>`;
    const cardTitle = card.querySelector('.note-card-title');
    if (cardTitle) {
      cardTitle.id = `note-card-title-${item.noteId}`;
      card.setAttribute('aria-labelledby', cardTitle.id);
    }
    card.querySelectorAll('button,[tabindex],input,textarea').forEach((element) => {
      const action = element.dataset.noteCardAction || element.dataset.noteCardInput || 'body';
      element.dataset.pdmNativeFocusKey = `note-action:${item.noteId}:${action}`;
    });
    card.querySelectorAll('[data-note-card-input]').forEach((input) => input.addEventListener('input', () => {
      if (!runtime.noteDraft || runtime.noteDraft.noteId !== item.noteId) return;
      runtime.noteDraft[input.dataset.noteCardInput] = input.value;
      const feedback = card.querySelector('.note-form-feedback');
      if (feedback) feedback.textContent = '';
      input.removeAttribute('aria-invalid');
      const save = card.querySelector('[data-note-card-action="save"]');
      if (save) setEnabled(save, noteDraftDirty() && !runtime.pendingNoteSave && !runtime.pendingNoteFavorite);
    }));
    card.querySelectorAll('[data-note-card-action]').forEach((button) => button.addEventListener('click', () => {
      const action = button.dataset.noteCardAction;
      if (action === 'read') activateNote(item);
      else if (action === 'back') closeNoteCard();
      else if (action === 'cancel') cancelNoteEdit();
      else if (action === 'edit') beginNoteEdit(item);
      else if (action === 'save') saveNoteCard();
      else if (action === 'favorite') requestNoteFavorite(item, !item.favorite);
      else if (action === 'delete') openDeleteNoteDialog(item);
    }));
    return card;
  }

  function notePager(container) {
    if (runtime.noteTotal <= 100) return;
    const footer = document.createElement('div');
    footer.className = 'detail-footer';
    footer.innerHTML = `<span class="detail-time">${escapeHtml(fixedText(`共 ${runtime.noteTotal} 条`, `${runtime.noteTotal} notes`))}</span>`;
    const actions = document.createElement('div');
    actions.className = 'detail-buttons';
    for (const [direction, enabled, key, label, handler] of [
      ['previous', Boolean(runtime.noteCursorHistory.length), 'previous', fixedText('上一页', 'Previous'), loadPreviousNotePage],
      ['next', (runtime.noteCursorHistory.length + 1) * 100 < runtime.noteTotal, 'next', fixedText('下一页', 'Next'), loadNextNotePage],
    ]) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'btn btn-sm'; button.textContent = label;
      button.disabled = !enabled || Boolean(runtime.pendingNoteList);
      button.dataset.pdmNotePager = direction;
      button.dataset.pdmNativeFocusKey = `note-page:${key}`;
      button.addEventListener('click', handler);
      actions.append(button);
    }
    footer.append(actions); container.append(footer);
  }

  function patchNoteCard(noteId) {
    setNoteChipState();
    const item = runtime.noteItems.find((value) => value.noteId === noteId);
    const grid = byId('notes-list')?.querySelector('.notes-cards');
    const oldCard = grid?.querySelector(`:scope > .note-card[data-id="${noteId}"]`);
    if (!item || !grid || !oldCard) { renderM4Notes(); return; }
    preserveProductFocus(grid, () => oldCard.replaceWith(noteCardElement(item)));
    const card = grid.querySelector(`:scope > .note-card[data-id="${noteId}"]`);
    if (
      runtime.pendingNoteSave
      && card instanceof HTMLElement
      && card.contains(document.activeElement)
    ) {
      card.focus({preventScroll: true});
    }
    window.requestAnimationFrame(() => window.pdmLayoutNotesCards?.(byId('notes-list')));
    refreshControls();
  }

  function invalidateNotePages() {
    runtime.notePageInvalidated = true;
  }

  function renderM4NotesBody() {
    const wrap = byId('notes-list');
    if (!wrap) return;
    byId('page-notes')?.classList.add('pdm-m4-notes-cards');
    setNoteChipState();
    if (state.currentNav === 'notes') syncGlobalSearchStatus(runtime.noteTotal, runtime.noteQuery);
    wrap.replaceChildren();
    if (runtime.state !== 'UNLOCKED') {
      wrap.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('lock', 40)}</div><div>${escapeHtml(t('startup.empty.notes'))}</div></div>`;
      return;
    }
    if (runtime.pendingNoteList && !runtime.noteItems.length) {
      wrap.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('notebook', 40)}</div><div>${escapeHtml(fixedText('正在读取记事…', 'Loading notes…'))}</div></div>`;
      return;
    }
    if (!runtime.noteItems.length) {
      wrap.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('notebook', 48)}</div><div>${escapeHtml(t('notes.empty'))}</div></div>`;
      return;
    }
    const grid = document.createElement('div');
    grid.className = 'notes-cards'; grid.setAttribute('aria-label', fixedText('记事卡片', 'Note cards'));
    runtime.noteItems.forEach((item) => grid.append(noteCardElement(item)));
    wrap.append(grid); notePager(wrap);
    window.requestAnimationFrame(() => {
      window.pdmLayoutNotesCards?.(wrap);
    });
    refreshControls();
  }

  function renderM4Notes() {
    return preserveProductFocus(byId('page-notes'), renderM4NotesBody);
  }

  function closeNoteCard() {
    if (noteDraftDirty()) { showUnsavedNoteWarning(); return; }
    clearSelectedNoteDetails(); renderM4Notes();
    if (runtime.notePageInvalidated) requestNotePage();
  }

  function beginNoteEdit(item) {
    if (
      !item || runtime.state !== 'UNLOCKED' || !runtime.ready ||
      !runtime.editorLauncher || noteDraftDirty()
    ) {
      if (noteDraftDirty()) showUnsavedNoteWarning();
      return;
    }
    const id = requestId();
    runtime.editorLauncher.openNoteEditorV1(
      id,
      item.noteId,
      item.revision,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          showErrorToast(ack && ack.errorCode); refreshControls(); return;
        }
        if (ack.status === 'FOCUSED_EXISTING') {
          showFixedToast('请先保存或取消当前编辑。', 'Save or cancel the current edit first.', 'info');
          return;
        }
        if (ack.status !== 'OPENING' || typeof ack.instanceId !== 'string' || !ack.instanceId) {
          showErrorToast('INTERNAL_FAILURE'); return;
        }
        runtime.editorIntentId = id;
        runtime.editorInstanceId = ack.instanceId;
        runtime.editorTarget = {
          kind: 'NOTE', recordId: item.noteId, revision: item.revision,
          purpose: 'edit',
        };
        refreshControls();
      },
    );
  }

  function cancelNoteEdit() {
    const draft = runtime.noteDraft;
    if (!draft || runtime.pendingNoteSave || runtime.pendingNoteFavorite) return;
    if (runtime.noteEditReturnToOverview) {
      clearSelectedNoteDetails();
      renderM4Notes();
      if (runtime.notePageInvalidated) requestNotePage();
      return;
    }
    runtime.noteDraft = null;
    patchNoteCard(draft.noteId);
  }

  function noteWritePending() {
    return Boolean(runtime.pendingNoteSave || runtime.pendingNoteFavorite || runtime.pendingNoteCreate ||
      runtime.pendingNoteDeletePrepare || runtime.pendingNoteDeleteCommit);
  }

  function noteWriteFailure(errorCode) {
    const feedback = byId('notes-list')?.querySelector('.note-card.is-editing .note-form-feedback');
    if (errorCode === 'REVISION_CONFLICT') errorCode = fixedText(
      '记事已被修改，当前输入已保留。请先取消编辑、重新打开最新记事，再重试。',
      'This note changed. Your input is preserved. Cancel editing and reopen the latest note before retrying.',
    );
    if (feedback) feedback.textContent = /^[A-Z_]+$/.test(errorCode) ? errorText(errorCode) : errorCode;
    else showErrorToast(errorCode);
  }

  function showUnsavedNoteWarning() {
    showI18nToast('notes.cards.unsaved', 'warning');
    const draft = runtime.noteDraft;
    if (!draft) return;
    noteWriteFailure(t('notes.cards.unsaved'));
    window.pdmFocusVisibility?.restore(
      null,
      [`note-action:${draft.noteId}:title`],
    );
  }

  function saveNoteCard() {
    const draft = runtime.noteDraft;
    if (!draft || runtime.pendingNoteSave || runtime.pendingNoteFavorite || !noteDraftDirty() || !runtime.bridge) return;
    const titleAction = draft.title === draft.originalTitle ? 'KEEP' : 'REPLACE';
    const contentAction = draft.content === draft.originalContent ? 'KEEP' : 'REPLACE';
    const invalidField = !draft.title.trim() ||
      (titleAction === 'REPLACE' && !noteFieldFits('TITLE', draft.title.trim())) ? 'title' :
      (contentAction === 'REPLACE' && !noteFieldFits('CONTENT', draft.content)) ? 'content' : '';
    if (invalidField) {
      noteWriteFailure(fixedText('修改后的标题或内容超出输入限制。', 'Changed title or content exceeds the input limit.'));
      const invalidInput = byId('notes-list')?.querySelector(
        `.note-card.is-editing [data-note-card-input="${invalidField}"]`,
      );
      invalidInput?.setAttribute('aria-invalid', 'true');
      window.pdmFocusVisibility?.restore(
        null,
        [`note-action:${draft.noteId}:${invalidField}`],
      );
      return;
    }
    if (titleAction === 'REPLACE') draft.title = draft.title.trim();
    const id = requestId();
    runtime.pendingNoteSave = id;
    runtime.bridge.updateNoteFieldsV1(id, runtime.pageEpoch, runtime.sessionEpoch, draft.noteId,
      draft.revision, titleAction, titleAction === 'REPLACE' ? draft.title : '', contentAction,
      contentAction === 'REPLACE' ? draft.content : '', runtime.selectedNoteDetails?.favorite === true, (ack) => {
        if (runtime.pendingNoteSave === id && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
          runtime.pendingNoteSave = ''; patchNoteCard(draft.noteId); noteWriteFailure(ack?.errorCode || 'INTERNAL_FAILURE');
          window.pdmFocusVisibility?.restore(
            null,
            [`note-action:${draft.noteId}:title`],
          );
        }
      });
    patchNoteCard(draft.noteId);
  }

  function replaceNoteSummary(item) {
    const index = runtime.noteItems.findIndex((value) => value.noteId === item.noteId);
    if (index < 0) return false;
    const old = runtime.noteItems[index];
    runtime.noteFavoriteCount = Math.max(0, runtime.noteFavoriteCount + Number(item.favorite) - Number(old.favorite));
    old.title = ''; old.contentPreview = '';
    runtime.noteItems[index] = item;
    return true;
  }

  function onNoteUpdated(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingNoteSave || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) { scrubNoteWriteResult(result); return; }
    runtime.pendingNoteSave = '';
    if (errorCode !== 'OK') {
      const noteId = runtime.noteDraft?.noteId || 0;
      scrubNoteWriteResult(result); patchNoteCard(noteId); noteWriteFailure(errorCode);
      window.pdmFocusVisibility?.restore(
        null,
        [`note-action:${noteId}:title`],
      );
      return;
    }
    const write = normalizeNoteWriteResult(result);
    const details = runtime.selectedNoteDetails;
    if (!write || !runtime.noteDraft || !details || write.item.noteId !== runtime.noteDraft.noteId) {
      const noteId = runtime.noteDraft?.noteId || 0;
      scrubNoteWriteResult(result); patchNoteCard(noteId); noteWriteFailure('INTERNAL_FAILURE');
      window.pdmFocusVisibility?.restore(
        null,
        [`note-action:${noteId}:title`],
      );
      return;
    }
    runtime.noteRevision = write.noteRevision;
    invalidateNotePages();
    replaceNoteSummary(write.item);
    details.revision = write.item.revision; details.title = runtime.noteDraft.title; details.content = runtime.noteDraft.content;
    details.favorite = write.item.favorite; details.updatedDate = write.item.updatedDate;
    runtime.selectedNoteRevision = write.item.revision;
    runtime.noteDraft = null;
    runtime.noteEditRequestedId = 0;
    runtime.noteEditReturnToOverview = false;
    scrubNoteWriteResult(result); patchNoteCard(write.item.noteId); showI18nToast('toast.note.saved', 'success');
    window.pdmFocusVisibility?.restore(
      null,
      [
        `note-action:${write.item.noteId}:edit`,
        `note-action:${write.item.noteId}:body`,
        `note-action:${write.item.noteId}:read`,
      ],
    );
  }

  function requestNoteFavorite(item, favorite) {
    if (!item || runtime.pendingNoteFavorite || runtime.pendingNoteSave || !runtime.bridge || runtime.state !== 'UNLOCKED') return;
    const id = requestId(); runtime.pendingNoteFavorite = id; runtime.pendingNoteFavoriteId = item.noteId;
    runtime.bridge.setNoteFavoriteV1(id, runtime.pageEpoch, runtime.sessionEpoch, item.noteId, item.revision, favorite, (ack) => {
      if (runtime.pendingNoteFavorite === id && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
        runtime.pendingNoteFavorite = ''; runtime.pendingNoteFavoriteId = 0; showErrorToast(ack?.errorCode || 'INTERNAL_FAILURE'); patchNoteCard(item.noteId);
      }
    });
    patchNoteCard(item.noteId);
  }

  function onNoteFavoriteSet(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingNoteFavorite || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) { scrubNoteWriteResult(result); return; }
    const favoriteId = runtime.pendingNoteFavoriteId;
    runtime.pendingNoteFavorite = '';
    runtime.pendingNoteFavoriteId = 0;
    if (errorCode !== 'OK') { scrubNoteWriteResult(result); showErrorToast(errorCode); patchNoteCard(favoriteId); return; }
    const write = normalizeNoteWriteResult(result);
    if (!write || !replaceNoteSummary(write.item)) { scrubNoteWriteResult(result); showErrorToast('INTERNAL_FAILURE'); return; }
    runtime.noteRevision = write.noteRevision;
    invalidateNotePages();
    if (runtime.selectedNoteId === write.item.noteId && runtime.selectedNoteDetails) {
      cancelNoteFieldRead();
      runtime.selectedNoteDetails.favorite = write.item.favorite;
      runtime.selectedNoteDetails.revision = write.item.revision;
      runtime.selectedNoteRevision = write.item.revision;
      if (runtime.noteDraft) runtime.noteDraft.revision = write.item.revision;
    }
    scrubNoteWriteResult(result); patchNoteCard(write.item.noteId);
    if (runtime.noteFilter === 'FAVORITE' && !write.item.favorite && !runtime.noteDraft) {
      clearSelectedNoteDetails(); requestNotePage();
    }
  }

  function requestNotePage(targetPage = runtime.noteCursorHistory.length) {
    if (!globalSearchFits(runtime.noteQuery)) return;
    if (runtime.state !== 'UNLOCKED' || state.currentNav !== 'notes' || !runtime.ready || !runtime.bridge || runtime.pendingNoteList || noteDraftDirty() || noteWritePending()) return;
    if (runtime.notePageInvalidated) {
      runtime.notePageTarget = Math.max(0, targetPage);
      runtime.noteCursor = '';
      runtime.noteCursorHistory = [];
      runtime.noteNextCursor = '';
      runtime.notePageInvalidated = false;
    }
    const id = requestId(); runtime.pendingNoteList = id; runtime.pendingNoteListKey = currentNoteRequestKey();
    if (!runtime.noteItems.length) renderM4Notes();
    runtime.bridge.listNoteSummariesV1(id, runtime.pageEpoch, runtime.sessionEpoch, runtime.noteQuery,
      runtime.noteFilter, runtime.noteCursor, 100, runtime.noteSort, (ack) => acceptNoteAck(
        ack,
        'pendingNoteList',
        () => { renderM4Notes(); restoreNoteListFocus(); },
      ));
    refreshControls();
  }

  function restoreNoteListFocus() {
    const keys = Array.isArray(runtime.noteListFocusKeys)
      ? runtime.noteListFocusKeys
      : [];
    const guard = runtime.noteListFocusGuard;
    runtime.noteListFocusKeys = [];
    runtime.noteListFocusGuard = null;
    if (
      !keys.length || state.currentNav !== 'notes' ||
      document.activeElement !== guard
    ) return;
    window.pdmFocusVisibility?.restore(null, keys);
  }

  function queueNoteReload() {
    if (noteDraftDirty()) { showUnsavedNoteWarning(); return; }
    if (runtime.noteSearchTimer) window.clearTimeout(runtime.noteSearchTimer);
    runtime.noteSearchTimer = 0;
    if (!globalSearchFits(runtime.noteQuery)) return;
    runtime.noteSearchTimer = window.setTimeout(() => { runtime.noteSearchTimer = 0; if (runtime.pendingNoteList) { queueNoteReload(); return; } resetNotePagePosition(); requestNotePage(); }, 120);
  }

  function onNotesListed(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingNoteList || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) { scrubNotePageResult(result); return; }
    const key = runtime.pendingNoteListKey; runtime.pendingNoteList = ''; runtime.pendingNoteListKey = '';
    if (key !== currentNoteRequestKey()) { scrubNotePageResult(result); queueNoteReload(); return; }
    if (errorCode !== 'OK') {
      scrubNotePageResult(result);
      if (errorCode === 'INVALID_ARGUMENT' && runtime.noteCursor) {
        resetNotePagePosition(); requestNotePage(); return;
      }
      renderM4Notes();
      if (['SESSION_REQUIRED', 'STALE_SESSION', 'STALE_PAGE'].includes(errorCode)) applyLocked('session_invalidated');
      else { showErrorToast(errorCode); restoreNoteListFocus(); }
      return;
    }
    const page = normalizeNotePage(result);
    if (!page) {
      scrubNotePageResult(result); showErrorToast('INTERNAL_FAILURE'); restoreNoteListFocus(); return;
    }
    if (runtime.noteCursorHistory.length < runtime.notePageTarget && page.nextCursor) {
      runtime.noteCursorHistory.push(runtime.noteCursor);
      runtime.noteCursor = page.nextCursor;
      scrubNotePageResult(result);
      requestNotePage();
      return;
    }
    runtime.notePageTarget = 0;
    clearSelectedNoteDetails();
    runtime.noteItems.forEach((item) => { item.title = ''; item.contentPreview = ''; });
    runtime.noteItems = page.items; runtime.noteTotal = page.total; runtime.noteNextCursor = page.nextCursor; runtime.noteRevision = page.noteRevision; runtime.notePageInvalidated = false;
    runtime.noteAllCount = page.counts.all;
    runtime.noteFavoriteCount = page.counts.favorite;
    renderM4Notes();
    restoreNoteListFocus();
  }

  function loadNextNotePage() {
    if (!globalSearchFits(runtime.noteQuery)) return;
    if (runtime.pendingNoteList || noteDraftDirty()) return;
    if (runtime.notePageInvalidated) { clearSelectedNoteDetails(); requestNotePage(runtime.noteCursorHistory.length + 1); return; }
    if (!runtime.noteNextCursor) return;
    runtime.noteCursorHistory.push(runtime.noteCursor); runtime.noteCursor = runtime.noteNextCursor; runtime.noteNextCursor = ''; clearSelectedNoteDetails(); requestNotePage();
  }

  function loadPreviousNotePage() {
    if (!globalSearchFits(runtime.noteQuery)) return;
    if (runtime.pendingNoteList || noteDraftDirty()) return;
    if (runtime.notePageInvalidated) { clearSelectedNoteDetails(); requestNotePage(Math.max(0, runtime.noteCursorHistory.length - 1)); return; }
    if (!runtime.noteCursorHistory.length) return;
    runtime.noteCursor = runtime.noteCursorHistory.pop(); runtime.noteNextCursor = ''; clearSelectedNoteDetails(); requestNotePage();
  }

  function requestNoteDetails(item) {
    if (runtime.state !== 'UNLOCKED' || !runtime.ready || !runtime.bridge || runtime.pendingNoteDetails) return;
    const id = requestId(); runtime.pendingNoteDetails = id; runtime.selectedNoteId = item.noteId; runtime.selectedNoteRevision = item.revision;
    if (runtime.noteEditRequestedId === item.noteId && runtime.noteEditReturnToOverview) {
      byId('notes-list')?.querySelector(`.note-card[data-id="${item.noteId}"]`)?.setAttribute('aria-busy', 'true');
      refreshControls();
    } else patchNoteCard(item.noteId);
    runtime.bridge.getNoteV1(id, runtime.pageEpoch, runtime.sessionEpoch, item.noteId, item.revision,
      (ack) => {
        if (runtime.pendingNoteDetails === id) acceptNoteAck(ack, 'pendingNoteDetails', () => {
          clearSelectedNoteDetails(); renderM4Notes();
        });
      });
  }

  function activateNote(item) {
    if (noteDraftDirty() || runtime.pendingNoteList || runtime.pendingNoteDetails || runtime.pendingNoteCreate || runtime.pendingLock || runtime.pendingOpen) {
      if (noteDraftDirty()) showUnsavedNoteWarning(); return;
    }
    if (runtime.selectedNoteId === item.noteId) { closeNoteCard(); return; }
    clearSelectedNoteDetails(); requestNoteDetails(item);
  }

  function onNoteDetails(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingNoteDetails || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) { scrubNoteDetailsResult(result); return; }
    runtime.pendingNoteDetails = '';
    if (errorCode !== 'OK') {
      scrubNoteDetailsResult(result); clearSelectedNoteDetails(); renderM4Notes();
      if (['SESSION_REQUIRED', 'STALE_SESSION', 'STALE_PAGE'].includes(errorCode)) applyLocked('session_invalidated');
      else if (['REVISION_CONFLICT', 'NOT_FOUND'].includes(errorCode)) { showErrorToast(errorCode); resetNotePagePosition(); requestNotePage(); }
      else showErrorToast(errorCode);
      return;
    }
    const details = normalizeNoteDetails(result);
    if (!details || details.noteId !== runtime.selectedNoteId || details.revision !== runtime.selectedNoteRevision) { scrubNoteDetailsResult(result); clearSelectedNoteDetails(); showErrorToast('INTERNAL_FAILURE'); renderM4Notes(); return; }
    details.summaryLongFields = [...details.longFields];
    runtime.selectedNoteDetails = details; state.expandedId = details.noteId + 1000;
    if (details.longFields.length) {
      renderM4Notes();
      readNoteField(details, details.longFields[0]);
    }
    else {
      syncNoteSummaryFromDetails(details);
      renderM4Notes();
    }
  }

  function activeNoteDeleteModal() {
    const modal = byId('active-modal');
    return modal?.dataset.pdmM4NoteDelete === 'true' ? modal : null;
  }

  function closeDeleteNoteDialog(force = false) {
    if (!force && (runtime.pendingNoteDeletePrepare || runtime.pendingNoteDeleteCommit)) return;
    runtime.pendingNoteDeletePrepare = '';
    runtime.pendingNoteDeleteCommit = '';
    runtime.noteDelete = null;
    closeDemoModal();
    refreshControls();
  }

  function openDeleteNoteDialog(item) {
    if (!item || noteDraftDirty() || runtime.noteDelete || !runtime.bridge) {
      if (noteDraftDirty()) showUnsavedNoteWarning();
      return;
    }
    const overlay = openDemoModal(`
      <div class="modal-header"><div class="modal-title">${escapeHtml(t('dialog.note.delete.title'))}</div><button type="button" class="modal-close">✕</button></div>
      <div class="modal-body"><div class="delete-confirm-icon">${svgIcon('warning', 32)}</div><div class="delete-confirm-text" id="note-delete-text" data-pdm-sensitive="true">${escapeHtml(t('dialog.note.delete.confirm').replace('{title}', item.title))}</div><div class="delete-confirm-desc" id="note-delete-desc">${escapeHtml(t('dialog.note.delete.desc'))}</div><div class="modal-form-error" id="note-delete-error"></div></div>
      <div class="modal-footer"><div class="modal-footer-right"><button type="button" class="btn btn-sm delete-cancel" data-note-delete-action="cancel">${escapeHtml(t('dialog.button.cancel'))}</button><button type="button" class="btn btn-danger btn-sm" data-note-delete-action="confirm">${escapeHtml(t('dialog.button.delete'))}</button></div></div>`,
      {closeOnBackdrop: false, initialFocusSelector: '.delete-cancel'});
    if (!overlay) { showErrorToast('INTERNAL_FAILURE'); return; }
    overlay.dataset.pdmM4NoteDelete = 'true';
    overlay.querySelector('.modal')?.setAttribute(
      'aria-describedby',
      'note-delete-text note-delete-desc',
    );
    runtime.noteDelete = {noteId: item.noteId, revision: item.revision, title: item.title};
    overlay.querySelector('.modal-close')?.addEventListener('click', () => closeDeleteNoteDialog());
    overlay.querySelector('[data-note-delete-action="cancel"]')?.addEventListener('click', () => closeDeleteNoteDialog());
    overlay.querySelector('[data-note-delete-action="confirm"]')?.addEventListener('click', submitDeleteNote);
    refreshControls();
  }

  function noteDeleteError(code) {
    const target = byId('note-delete-error');
    if (target) {
      target.setAttribute('role', 'status');
      target.setAttribute('aria-live', 'polite');
      target.setAttribute('aria-atomic', 'true');
      target.textContent = errorText(code);
    }
    else showErrorToast(code);
  }

  function submitDeleteNote() {
    const pending = runtime.noteDelete;
    if (!pending || runtime.pendingNoteDeletePrepare || runtime.pendingNoteDeleteCommit || !activeNoteDeleteModal() || !runtime.bridge) return;
    const id = requestId(); runtime.pendingNoteDeletePrepare = id;
    runtime.bridge.prepareDeleteNoteV1(id, runtime.pageEpoch, runtime.sessionEpoch, pending.noteId, pending.revision, (ack) => {
      if (runtime.pendingNoteDeletePrepare === id && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
        runtime.pendingNoteDeletePrepare = ''; noteDeleteError(ack?.errorCode || 'INTERNAL_FAILURE');
      }
    });
  }

  function onNoteDeletePrepared(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingNoteDeletePrepare || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch || !activeNoteDeleteModal()) {
      if (result) result.deleteTicket = '';
      return;
    }
    runtime.pendingNoteDeletePrepare = '';
    if (errorCode !== 'OK') {
      if (['SESSION_REQUIRED', 'STALE_SESSION', 'STALE_PAGE'].includes(errorCode)) { closeDeleteNoteDialog(true); applyLocked('session_invalidated'); }
      else noteDeleteError(errorCode);
      return;
    }
    const ticket = typeof result?.deleteTicket === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(result.deleteTicket) ? result.deleteTicket : '';
    result.deleteTicket = '';
    if (!ticket) { noteDeleteError('INTERNAL_FAILURE'); return; }
    const id = requestId(); runtime.pendingNoteDeleteCommit = id;
    runtime.bridge.deleteNoteV1(id, runtime.pageEpoch, runtime.sessionEpoch, ticket, (ack) => {
      if (runtime.pendingNoteDeleteCommit === id && (!ack || ack.accepted !== true || ack.errorCode !== 'OK')) {
        runtime.pendingNoteDeleteCommit = ''; noteDeleteError(ack?.errorCode || 'INTERNAL_FAILURE');
      }
    });
  }

  function onNoteDeleted(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    const pending = runtime.noteDelete;
    if (request !== runtime.pendingNoteDeleteCommit || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch || !pending) return;
    runtime.pendingNoteDeleteCommit = '';
    if (errorCode !== 'OK') {
      if (['SESSION_REQUIRED', 'STALE_SESSION', 'STALE_PAGE'].includes(errorCode)) { closeDeleteNoteDialog(true); applyLocked('session_invalidated'); }
      else noteDeleteError(errorCode);
      return;
    }
    if (!result || result.deletedId !== pending.noteId || !isRevision(result.noteRevision)) {
      closeDeleteNoteDialog(true); showErrorToast('INTERNAL_FAILURE'); return;
    }
    const focusKeys = noteDeleteFocusKeys(pending.noteId);
    runtime.noteRevision = result.noteRevision;
    invalidateNotePages();
    const index = runtime.noteItems.findIndex((item) => item.noteId === pending.noteId);
    const wasFavorite = index >= 0 && runtime.noteItems[index].favorite;
    if (index >= 0) {
      const [removed] = runtime.noteItems.splice(index, 1);
      removed.title = ''; removed.contentPreview = '';
    }
    runtime.noteTotal = Math.max(0, runtime.noteTotal - 1);
    runtime.noteAllCount = Math.max(0, runtime.noteAllCount - 1);
    if (wasFavorite) runtime.noteFavoriteCount = Math.max(0, runtime.noteFavoriteCount - 1);
    closeDeleteNoteDialog(true); clearSelectedNoteDetails(); renderM4Notes(); showCompositeI18nToast('toast.deleted.prefix', pending.title, '', 'success');
    runtime.noteListFocusKeys = focusKeys;
    runtime.noteListFocusGuard = document.activeElement;
    requestNotePage();
  }

  function activeNoteCreateModal() {
    const modal = byId('active-modal');
    return (
      modal &&
      modal.dataset.pdmM4NoteCreate === 'true'
    ) ? modal : null;
  }

  function clearNoteCreateCooldown() {
    if (runtime.noteCreateCooldownTimer) {
      window.clearTimeout(runtime.noteCreateCooldownTimer);
      runtime.noteCreateCooldownTimer = 0;
    }
    runtime.noteCreateCooldownUntil = 0;
  }

  function beginNoteCreateCooldown(retryAfterMs) {
    clearNoteCreateCooldown();
    if (!Number.isSafeInteger(retryAfterMs) || retryAfterMs < 1) {
      refreshControls();
      return;
    }
    runtime.noteCreateCooldownUntil = Date.now() + retryAfterMs;
    runtime.noteCreateCooldownTimer = window.setTimeout(() => {
      runtime.noteCreateCooldownTimer = 0;
      runtime.noteCreateCooldownUntil = 0;
      refreshControls();
    }, retryAfterMs);
    refreshControls();
  }

  function cancelPendingNoteCreate() {
    const targetRequestId = runtime.pendingNoteCreate;
    runtime.pendingNoteCreate = '';
    if (
      !targetRequestId ||
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0
    ) {
      return;
    }
    runtime.bridge.cancelRequestV1(
      requestId(),
      runtime.pageEpoch,
      targetRequestId,
      () => {},
    );
  }

  function scrubNoteCreateForm() {
    const modal = activeNoteCreateModal();
    clearNoteCreateCooldown();
    if (modal) {
      for (const id of ['nf-title', 'nf-content']) {
        const element = byId(id);
        if (
          element instanceof HTMLInputElement ||
          element instanceof HTMLTextAreaElement
        ) {
          element.value = '';
          element.defaultValue = '';
        }
      }
    }
    runtime.noteCreateReturnFocus = '';
    runtime.noteCreateModalActive = false;
  }

  function closeCreateNoteDialog() {
    cancelPendingNoteCreate();
    scrubNoteCreateForm();
    closeDemoModal();
    refreshControls();
  }

  function showNoteTitleError(
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const error = byId('nf-title-err');
    if (!error) return;
    const visible = setRuntimeText(
      error,
      text,
      fixedZh,
      fixedEn,
      i18nKey,
    );
    error.classList.toggle('show', visible);
    error.setAttribute('aria-hidden', visible ? 'false' : 'true');
    error.setAttribute('role', 'status');
    error.setAttribute('aria-live', 'polite');
    error.setAttribute('aria-atomic', 'true');
    const input = byId('nf-title');
    if (input) {
      input.setAttribute('aria-describedby', 'nf-title-err');
      input.setAttribute('aria-invalid', visible ? 'true' : 'false');
    }
  }

  function showNoteCreateError(
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const error = byId('nf-save-err');
    if (!error) return;
    error.setAttribute('role', 'status');
    error.setAttribute('aria-live', 'polite');
    error.setAttribute('aria-atomic', 'true');
    const visible = setRuntimeText(
      error,
      text,
      fixedZh,
      fixedEn,
      i18nKey,
    );
    error.classList.toggle('show', visible);
    error.setAttribute('aria-hidden', visible ? 'false' : 'true');
  }

  function configureNoteCreateDialog() {
    const modal = activeNoteCreateModal();
    const title = byId('nf-title');
    const content = byId('nf-content');
    const save = modal?.querySelector('.modal-footer .btn-primary');
    if (
      !modal ||
      !(title instanceof HTMLInputElement) ||
      !(content instanceof HTMLTextAreaElement) ||
      !(save instanceof HTMLButtonElement)
    ) {
      return false;
    }
    // maxlength 按 UTF-16 码元截断；这里按 Unicode 字符校验并保留超限输入供修改。
    title.removeAttribute('maxlength');
    content.removeAttribute('maxlength');
    title.dataset.pdmSensitive = 'true';
    content.dataset.pdmSensitive = 'true';
    save.id = 'nf-save';
    const body = modal.querySelector('.modal-body');
    if (body && !byId('nf-save-err')) {
      const error = document.createElement('div');
      error.className = 'modal-form-error';
      error.id = 'nf-save-err';
      error.setAttribute('aria-hidden', 'true');
      body.append(error);
    }
    showNoteTitleError('');
    title.addEventListener('input', () => {
      showNoteTitleError('');
      showNoteCreateError('');
    });
    content.addEventListener('input', () => {
      showNoteCreateError('');
      updateLongTextHint(content, 'nf-content-scroll-hint');
    });
    content.addEventListener('scroll', () => {
      updateLongTextHint(content, 'nf-content-scroll-hint');
    });
    return true;
  }

  function openCreateNoteDialog() {
    if (
      runtime.state !== 'UNLOCKED' ||
      state.currentNav !== 'notes' ||
      !runtime.ready ||
      !runtime.editorLauncher ||
      noteDraftDirty()
    ) {
      if (noteDraftDirty()) showUnsavedNoteWarning();
      return;
    }
    const id = requestId();
    runtime.editorLauncher.openNoteCreatorV1(id, (ack) => {
      if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
        showErrorToast(ack && ack.errorCode); refreshControls(); return;
      }
      if (ack.status === 'FOCUSED_EXISTING') {
        showFixedToast('请先保存或取消当前编辑。', 'Save or cancel the current edit first.', 'info');
        return;
      }
      if (ack.status !== 'OPENING' || typeof ack.instanceId !== 'string' || !ack.instanceId) {
        showErrorToast('INTERNAL_FAILURE'); return;
      }
      runtime.editorIntentId = id;
      runtime.editorInstanceId = ack.instanceId;
      runtime.editorTarget = {kind: 'NOTE', recordId: 0, revision: '', purpose: 'create'};
      refreshControls();
    });
  }

  function submitCreateNote() {
    const modal = activeNoteCreateModal();
    const titleField = byId('nf-title');
    const contentField = byId('nf-content');
    const favorite = byId('nf-favorite');
    if (
      !modal ||
      runtime.pendingNoteCreate ||
      runtime.noteCreateCooldownUntil > Date.now() ||
      !(titleField instanceof HTMLInputElement) ||
      !(contentField instanceof HTMLTextAreaElement)
    ) {
      return;
    }
    let title = titleField.value.trim();
    let content = contentField.value;
    if (!title.trim()) {
      showNoteTitleError(
        '',
        '',
        '',
        'dialog.note.error.titleEmpty',
      );
      titleField.focus({preventScroll: true});
      return;
    }
    if (!noteFieldFits('TITLE', title)) {
      showNoteTitleError(
        '',
        '标题过长，请缩短后重试。',
        'The title is too long. Shorten it and try again.',
      );
      titleField.focus({preventScroll: true});
      title = '';
      content = '';
      return;
    }
    if (!noteFieldFits('CONTENT', content)) {
      showNoteCreateError(
        '',
        '正文过长，请缩短后重试。',
        'The note body is too long. Shorten it and try again.',
      );
      contentField.focus({preventScroll: true});
      title = '';
      content = '';
      return;
    }
    const isFavorite = Boolean(
      favorite && favorite.classList.contains('active'),
    );
    const activeElementId = document.activeElement?.id || '';
    runtime.noteCreateReturnFocus = (
      activeElementId === 'nf-title' ||
      activeElementId === 'nf-content' ||
      activeElementId === 'nf-save'
    ) ? activeElementId : 'nf-content';
    showNoteTitleError('');
    showNoteCreateError('');
    const id = requestId();
    runtime.pendingNoteCreate = id;
    refreshControls();
    runtime.bridge.createNoteV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      title,
      content,
      isFavorite,
      (ack) => {
        if (ack && ack.accepted === true && ack.errorCode === 'OK') {
          return;
        }
        if (runtime.pendingNoteCreate === id) {
          runtime.pendingNoteCreate = '';
          showNoteCreateError(errorText(ack && ack.errorCode));
          refreshControls();
        }
      },
    );
    title = '';
    content = '';
  }

  function normalizeNoteWriteResult(result) {
    if (
      !result ||
      typeof result !== 'object' ||
      !isRevision(result.noteRevision)
    ) {
      return null;
    }
    const item = normalizeNoteSummary(result.item);
    return item ? {item, noteRevision: result.noteRevision} : null;
  }

  function scrubNoteWriteResult(result) {
    if (!result || typeof result !== 'object') return;
    if (result.item && typeof result.item === 'object') {
      result.item.title = '';
      result.item.contentPreview = '';
      result.item.longFields = [];
    }
  }

  function onNoteCreated(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    errorArgumentIndex,
    retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingNoteCreate ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch ||
      !activeNoteCreateModal()
    ) {
      scrubNoteWriteResult(result);
      return;
    }
    runtime.pendingNoteCreate = '';
    if (errorCode !== 'OK') {
      scrubNoteWriteResult(result);
      if (
        errorCode === 'INVALID_ARGUMENT' &&
        errorArgumentIndex === 4
      ) {
        showNoteTitleError(
          '',
          '',
          '',
          'dialog.note.error.titleEmpty',
        );
        byId('nf-title')?.focus({preventScroll: true});
      } else if (
        errorCode === 'SESSION_REQUIRED' ||
        errorCode === 'STALE_SESSION' ||
        errorCode === 'STALE_PAGE'
      ) {
        closeCreateNoteDialog();
        applyLocked('session_invalidated');
        return;
      } else {
        if (errorCode === 'DATABASE_IO_FAILED') {
          showNoteCreateError(
            '',
            '',
            '',
            'dialog.note.error.save_failed',
          );
        } else {
          showNoteCreateError(errorText(errorCode));
        }
      }
      beginNoteCreateCooldown(retryAfterMs);
      const returnFocus = byId(runtime.noteCreateReturnFocus);
      if (
        returnFocus instanceof HTMLElement &&
        !returnFocus.matches(':disabled')
      ) {
        returnFocus.focus({preventScroll: true});
      } else {
        byId('nf-content')?.focus({preventScroll: true});
      }
      return;
    }
    const normalized = normalizeNoteWriteResult(result);
    if (!normalized) {
      scrubNoteWriteResult(result);
      showNoteCreateError(errorText('INTERNAL_FAILURE'));
      refreshControls();
      return;
    }
    runtime.noteRevision = normalized.noteRevision;
    scrubNoteWriteResult(result);
    scrubNoteCreateForm();
    closeDemoModal();
    resetNotePagePosition();
    showI18nToast('toast.note.dialogAdded', 'success');
    requestNotePage();
    refreshControls();
  }

  function clearCreateCooldown() {
    if (runtime.createCooldownTimer) {
      window.clearTimeout(runtime.createCooldownTimer);
      runtime.createCooldownTimer = 0;
    }
    runtime.createCooldownUntil = 0;
  }

  function beginCreateCooldown(retryAfterMs) {
    clearCreateCooldown();
    if (!Number.isSafeInteger(retryAfterMs) || retryAfterMs < 1) {
      refreshControls();
      return;
    }
    runtime.createCooldownUntil = Date.now() + retryAfterMs;
    runtime.createCooldownTimer = window.setTimeout(() => {
      runtime.createCooldownTimer = 0;
      runtime.createCooldownUntil = 0;
      refreshControls();
    }, retryAfterMs);
    refreshControls();
  }

  function clearEditCooldown() {
    if (runtime.editCooldownTimer) {
      window.clearTimeout(runtime.editCooldownTimer);
      runtime.editCooldownTimer = 0;
    }
    runtime.editCooldownUntil = 0;
  }

  function beginEditCooldown(retryAfterMs) {
    clearEditCooldown();
    if (!Number.isSafeInteger(retryAfterMs) || retryAfterMs < 1) {
      refreshControls();
      return;
    }
    runtime.editCooldownUntil = Date.now() + retryAfterMs;
    runtime.editCooldownTimer = window.setTimeout(() => {
      runtime.editCooldownTimer = 0;
      runtime.editCooldownUntil = 0;
      refreshControls();
    }, retryAfterMs);
    refreshControls();
  }

  function suppressBlockedRecordSaveMultiClick(event) {
    const noteModal = activeNoteCreateModal();
    const changeModal = activeChangeKeyModal();
    const modal = (
      activeCreateModal() || activeEditModal() || noteModal || changeModal
    );
    const save = byId(
      changeModal ? 'kf-confirm-btn' : (noteModal ? 'nf-save' : 'mf-save'),
    );
    const editBlocked = Boolean(
      activeEditModal() &&
      (
        runtime.pendingEditSave ||
        runtime.pendingEditOpen ||
        runtime.editCooldownUntil > Date.now() ||
        runtime.editConflict ||
        !runtime.editLeaseId
      )
    );
    const createBlocked = Boolean(
      activeCreateModal() &&
      (
        runtime.pendingCreate ||
        runtime.createCooldownUntil > Date.now()
      )
    );
    const noteCreateBlocked = Boolean(
      noteModal &&
      (
        runtime.pendingNoteCreate ||
        runtime.noteCreateCooldownUntil > Date.now()
      )
    );
    const changeKeyBlocked = Boolean(
      changeModal &&
      (
        runtime.pendingChangeKey ||
        runtime.changeKeyCooldownUntil > Date.now()
      )
    );
    if (
      !modal ||
      !(save instanceof HTMLButtonElement) ||
      !save.disabled ||
      event.detail < 2 ||
      (
        !createBlocked &&
        !editBlocked &&
        !noteCreateBlocked &&
        !changeKeyBlocked
      )
    ) {
      return false;
    }
    const rect = save.getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    ) {
      return false;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    document.getSelection()?.removeAllRanges();
    return true;
  }

  function generatedSlot(slot) {
    return slot === 'tool'
      ? ['toolGeneratedLeaseId', 'toolGeneratedElement']
      : ['formGeneratedLeaseId', 'formGeneratedElement'];
  }

  function releaseGeneratedLease(
    slot,
    reason = 'lease_released',
    preserveElementValue = false,
  ) {
    const [leaseField, elementField] = generatedSlot(slot);
    const leaseId = runtime[leaseField];
    const element = runtime[elementField];
    let preservedValue = '';
    let preservedType = '';
    let preservedSelection = null;
    if (
      preserveElementValue &&
      (
        element instanceof HTMLInputElement ||
        element instanceof HTMLTextAreaElement
      )
    ) {
      preservedValue = element.value;
      if (element instanceof HTMLInputElement) {
        preservedType = element.type;
        preservedSelection = [element.selectionStart, element.selectionEnd, element.selectionDirection];
      }
    }
    runtime[leaseField] = '';
    runtime[elementField] = null;
    if (!leaseId) return;
    if (window.pdmSensitiveDom) {
      window.pdmSensitiveDom.clearLease(leaseId, reason);
    }
    if (
      preserveElementValue &&
      (
        element instanceof HTMLInputElement ||
        element instanceof HTMLTextAreaElement
      ) &&
      element.isConnected
    ) {
      if (
        element instanceof HTMLInputElement &&
        ['password', 'text'].includes(preservedType)
      ) {
        element.type = preservedType;
      }
      element.value = preservedValue;
      if (element instanceof HTMLInputElement && preservedSelection) {
        element.setSelectionRange(...preservedSelection);
      }
    }
    preservedValue = '';
    preservedType = '';
    if (
      runtime.bridge &&
      runtime.ready &&
      runtime.pageEpoch > 0
    ) {
      runtime.bridge.releaseSecretLeaseV1(
        requestId(),
        runtime.pageEpoch,
        leaseId,
        () => {},
      );
    }
  }

  function releaseAllGeneratedLeases(reason) {
    releaseGeneratedLease('tool', reason);
    releaseGeneratedLease('form', reason);
  }

  function releaseNativeSecretLease(leaseId) {
    if (
      typeof leaseId !== 'string' ||
      !leaseId ||
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0
    ) {
      return;
    }
    runtime.bridge.releaseSecretLeaseV1(
      requestId(),
      runtime.pageEpoch,
      leaseId,
      () => {},
    );
  }

  function detachEditorDomLease(
    leaseId,
    reason = 'lease_consumed',
    preservePassword = false,
  ) {
    const password = byId('mf-password');
    let preservedValue = '';
    let preservedType = '';
    let preservedSelection = null;
    if (preservePassword && password instanceof HTMLInputElement) {
      preservedValue = password.value;
      preservedType = password.type;
      preservedSelection = [password.selectionStart, password.selectionEnd, password.selectionDirection];
    }
    if (leaseId && window.pdmSensitiveDom) {
      window.pdmSensitiveDom.clearLease(leaseId, reason);
    }
    if (
      preservePassword &&
      password instanceof HTMLInputElement &&
      password.isConnected
    ) {
      if (['password', 'text'].includes(preservedType)) {
        password.type = preservedType;
      }
      password.value = preservedValue;
      if (preservedSelection) password.setSelectionRange(...preservedSelection);
    }
    preservedValue = '';
    preservedType = '';
  }

  function releaseEditorLease(
    reason = 'lease_released',
    preservePassword = false,
  ) {
    const leaseId = runtime.editLeaseId;
    runtime.editLeaseId = '';
    refreshEditorCopyAuthorization();
    detachEditorDomLease(leaseId, reason, preservePassword);
    releaseNativeSecretLease(leaseId);
  }

  function refreshEditorCopyAuthorization() {
    const password = byId('mf-password');
    if (!(password instanceof HTMLInputElement)) return;
    const fields = runtime.editorFieldMeta?.fields;
    const ready = Boolean(
      activeEditModal() &&
      runtime.editLeaseId &&
      fields &&
      Object.values(fields).every((field) => field.loaded || field.touched),
    );
    if (ready) password.dataset.pdmCopyAuthorized = 'edit';
    else delete password.dataset.pdmCopyAuthorized;
  }

  function cancelPendingCreate() {
    const targetRequestId = runtime.pendingCreate;
    runtime.pendingCreate = '';
    if (
      !targetRequestId ||
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0
    ) {
      return;
    }
    runtime.bridge.cancelRequestV1(
      requestId(),
      runtime.pageEpoch,
      targetRequestId,
      () => {},
    );
  }

  function cancelPendingEditOpen() {
    const targetRequestId = runtime.pendingEditOpen;
    runtime.pendingEditOpen = '';
    runtime.editOpenPurpose = '';
    runtime.editOpenRecordId = 0;
    runtime.editOpenRevision = '';
    runtime.editGenerateAfterOpen = false;
    if (
      !targetRequestId ||
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0
    ) {
      return;
    }
    runtime.bridge.cancelRequestV1(
      requestId(),
      runtime.pageEpoch,
      targetRequestId,
      () => {},
    );
  }

  function scrubEditForm(reason) {
    runtime.healthEditRecordId = 0;
    cancelFieldReads('editor');
    runtime.editorFieldMeta = null;
    runtime.editorPreparing = false;
    const modal = activeEditModal();
    releaseGeneratedLease('form', reason);
    releaseEditorLease(reason);
    if (runtime.editSubmittedLeaseId) {
      detachEditorDomLease(
        runtime.editSubmittedLeaseId,
        reason,
        false,
      );
      releaseNativeSecretLease(runtime.editSubmittedLeaseId);
      runtime.editSubmittedLeaseId = '';
    }
    clearEditCooldown();
    if (modal) {
      for (const id of [
        'mf-platform',
        'mf-account',
        'mf-password',
        'mf-notes',
        'mf-totp',
      ]) {
        const element = byId(id);
        if (
          element instanceof HTMLInputElement ||
          element instanceof HTMLTextAreaElement
        ) {
          element.value = '';
          element.defaultValue = '';
        }
      }
    }
    runtime.pendingEditSave = '';
    runtime.editModalActive = false;
    runtime.editRecordId = 0;
    runtime.editRevision = '';
    runtime.editHasTotp = false;
    runtime.editTotpAction = 'KEEP';
    runtime.editPasswordDirty = false;
    runtime.editConflict = false;
    runtime.editReloadRevision = '';
    runtime.editGenerateAfterOpen = false;
  }

  function closeEditRecordDialog(reason = 'modal_close') {
    if (runtime.pendingEditSave) return;
    const guideTarget = runtime.healthGuideEditTarget;
    cancelPendingEditOpen();
    runtime.pendingGenerate = '';
    runtime.generateTarget = '';
    scrubEditForm(reason);
    closeDemoModal();
    runtime.healthEditRecordId = 0;
    if (guideTarget && runtime.healthGuide && reason !== 'session_invalidated') {
      runtime.healthGuideEditTarget = null;
      pauseHealthGuidance();
    }
    if (reason === 'modal_close' || reason === 'navigation') {
      restoreHealthSingleOrigin();
      runtime.healthSingleOrigin = null;
    }
    refreshControls();
  }

  function scrubCreateForm(reason) {
    const modal = activeCreateModal();
    releaseGeneratedLease('form', reason);
    clearCreateCooldown();
    if (modal) {
      for (const id of [
        'mf-platform',
        'mf-account',
        'mf-password',
        'mf-notes',
        'mf-totp',
      ]) {
        const element = byId(id);
        if (
          element instanceof HTMLInputElement ||
          element instanceof HTMLTextAreaElement
        ) {
          element.value = '';
          element.defaultValue = '';
        }
      }
    }
    runtime.createModalActive = false;
  }

  function closeCreateRecordDialog(reason = 'modal_close') {
    if (
      runtime.pendingCreate &&
      !['manual_lock', 'session_invalidated', 'page_unload'].includes(reason)
    ) {
      return false;
    }
    cancelPendingCreate();
    runtime.pendingGenerate = '';
    runtime.generateTarget = '';
    scrubCreateForm(reason);
    closeDemoModal();
    refreshControls();
    return true;
  }

  function clearChangeKeyCooldown() {
    if (runtime.changeKeyCooldownTimer) {
      window.clearTimeout(runtime.changeKeyCooldownTimer);
      runtime.changeKeyCooldownTimer = 0;
    }
    runtime.changeKeyCooldownUntil = 0;
  }

  function beginChangeKeyCooldown(retryAfterMs) {
    clearChangeKeyCooldown();
    if (!Number.isSafeInteger(retryAfterMs) || retryAfterMs <= 0) {
      refreshControls();
      return;
    }
    const bounded = Math.min(86400000, retryAfterMs);
    runtime.changeKeyCooldownUntil = Date.now() + bounded;
    runtime.changeKeyCooldownTimer = window.setTimeout(() => {
      runtime.changeKeyCooldownTimer = 0;
      runtime.changeKeyCooldownUntil = 0;
      refreshControls();
    }, bounded);
    refreshControls();
  }

  function showChangeKeyCurrentError(
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const error = byId('kf-current-err');
    if (!error) return;
    const visible = setRuntimeText(
      error,
      text,
      fixedZh,
      fixedEn,
      i18nKey,
    );
    error.classList.toggle('show', visible);
    error.setAttribute('aria-hidden', visible ? 'false' : 'true');
    const input = byId('kf-current');
    if (input) {
      input.setAttribute('aria-describedby', 'kf-current-err');
      input.setAttribute('aria-invalid', visible ? 'true' : 'false');
    }
  }

  function showChangeKeyFormError(
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const error = byId('kf-form-error');
    if (!error) return;
    runtime.changeKeyBusyVisible = false;
    error.classList.remove('pending');
    error.setAttribute('role', 'status');
    error.setAttribute('aria-live', 'polite');
    error.setAttribute('aria-atomic', 'true');
    const visible = setRuntimeText(
      error,
      text,
      fixedZh,
      fixedEn,
      i18nKey,
    );
    error.classList.toggle('show', visible);
    error.setAttribute('aria-hidden', visible ? 'false' : 'true');
  }

  function clearChangeKeyBusyPresentation() {
    if (runtime.changeKeyBusyRevealTimer) {
      window.clearTimeout(runtime.changeKeyBusyRevealTimer);
      runtime.changeKeyBusyRevealTimer = 0;
    }
    runtime.changeKeyBusyVisible = false;
    const status = byId('kf-form-error');
    if (!status || !status.classList.contains('pending')) return;
    setRuntimeText(status, '');
    status.classList.remove('show', 'pending');
    status.setAttribute('aria-hidden', 'true');
  }

  function resetChangeKeyProgress() {
    clearChangeKeyBusyPresentation();
    runtime.changeKeyProgressPhase = '';
    const button = byId('kf-confirm-btn');
    if (button) {
      setRuntimeI18nText(button, 'dialog.button.confirm');
      button.removeAttribute('title');
      button.setAttribute('aria-busy', 'false');
    }
  }

  function scrubChangeKeyForm(reason) {
    const modal = activeChangeKeyModal();
    releaseGeneratedLease('form', reason);
    clearChangeKeyCooldown();
    resetChangeKeyProgress();
    if (modal) {
      for (const id of ['kf-current', 'kf-new', 'kf-confirm']) {
        const input = byId(id);
        if (input instanceof HTMLInputElement) {
          input.value = '';
          input.defaultValue = '';
          input.type = 'password';
          input.removeAttribute('data-pdm-sensitive');
        }
      }
      showChangeKeyCurrentError('');
      showChangeKeyFormError('');
    }
    runtime.pendingChangeKey = '';
    runtime.changeKeyModalActive = false;
  }

  function closeChangeKeyDialog(reason = 'modal_close', force = false) {
    if (!force && runtime.pendingChangeKey) return;
    runtime.pendingGenerate = '';
    runtime.generateTarget = '';
    scrubChangeKeyForm(reason);
    closeDemoModal();
    refreshControls();
  }

  function openChangeKeyDialog() {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      runtime.pendingChangeKey ||
      activeChangeKeyModal()
    ) {
      return;
    }
    runtime.changeKeyTerminalReason = '';
    renderDemoChangeKeyDialog();
    const modal = byId('active-modal');
    const current = byId('kf-current');
    const next = byId('kf-new');
    const confirm = byId('kf-confirm');
    if (
      !modal ||
      !(current instanceof HTMLInputElement) ||
      !(next instanceof HTMLInputElement) ||
      !(confirm instanceof HTMLInputElement)
    ) {
      closeDemoModal();
      failClosed();
      return;
    }
    modal.dataset.pdmM4ChangeKey = 'true';
    runtime.changeKeyModalActive = true;
    for (const input of [current, next, confirm]) {
      input.dataset.pdmSensitive = 'true';
    }
    current.addEventListener('input', () => {
      showChangeKeyCurrentError('');
      showChangeKeyFormError('');
    });
    next.addEventListener('input', () => {
      cancelPendingGeneratedPassword('change-key');
      if (
        runtime.formGeneratedLeaseId &&
        runtime.formGeneratedElement === next
      ) {
        releaseGeneratedLease('form', 'lease_released', true);
      }
      showChangeKeyFormError('');
      checkDbPasswordMatch();
      refreshControls();
    });
    confirm.addEventListener('input', () => {
      showChangeKeyFormError('');
      checkDbPasswordMatch();
      refreshControls();
    });
    showChangeKeyCurrentError('');
    showChangeKeyFormError('');
    resetChangeKeyProgress();
    checkDbPasswordMatch();
    refreshControls();
  }

  function submitChangeKey() {
    const modal = activeChangeKeyModal();
    const currentInput = byId('kf-current');
    const newInput = byId('kf-new');
    const confirmInput = byId('kf-confirm');
    if (
      !modal ||
      !runtime.bridge ||
      runtime.state !== 'UNLOCKED' ||
      runtime.sessionEpoch <= 0 ||
      runtime.pendingChangeKey ||
      (runtime.pendingGenerate && runtime.generateTarget === 'change-key') ||
      runtime.changeKeyCooldownUntil > Date.now() ||
      !(currentInput instanceof HTMLInputElement) ||
      !(newInput instanceof HTMLInputElement) ||
      !(confirmInput instanceof HTMLInputElement)
    ) {
      return;
    }
    if (newInput.value !== confirmInput.value) {
      showChangeKeyFormError(
        '',
        '两次输入的新密码不一致。',
        'The new passwords do not match.',
      );
      confirmInput.focus({preventScroll: true});
      return;
    }
    showChangeKeyCurrentError('');
    showChangeKeyFormError('');
    let currentPassword = currentInput.value;
    let newPassword = newInput.value;
    let confirmPassword = confirmInput.value;
    const id = requestId();
    runtime.pendingChangeKey = id;
    runtime.changeKeyProgressPhase = 'QUEUED';
    // The modal stays visually unchanged; the ongoing operation is
    // announced only through the small centered toast.  applyLocked
    // clears runtime toasts exactly at the terminal transition.
    showFixedToast('正在修改…', 'Changing…');
    byId('kf-confirm-btn')?.setAttribute('aria-busy', 'true');
    refreshControls();
    runtime.bridge.changeDatabasePasswordV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      currentPassword,
      newPassword,
      confirmPassword,
      (ack) => {
        if (
          !ack ||
          ack.accepted !== true ||
          ack.errorCode !== 'OK'
        ) {
          if (runtime.pendingChangeKey === id) {
            runtime.pendingChangeKey = '';
            clearRuntimeToasts();
            resetChangeKeyProgress();
            showChangeKeyFormError(errorText(ack && ack.errorCode));
            refreshControls();
          }
        }
      },
    );
    currentPassword = '';
    newPassword = '';
    confirmPassword = '';
  }

  function applyChangeKeyTerminal(reason) {
    if (
      reason === 'CHANGE_KEY_SUCCESS' ||
      reason === 'CHANGE_KEY_RESTORED'
    ) {
      document.documentElement.classList.add(
        'pdm-security-lock-handoff-static',
      );
    }
    if (
      runtime.changeKeyTerminalReason === reason &&
      runtime.sessionEpoch === 0 &&
      ['LOCKED', 'BLOCKED'].includes(runtime.state) &&
      !activeChangeKeyModal()
    ) {
      if (
        reason === 'CHANGE_KEY_SUCCESS' ||
        reason === 'CHANGE_KEY_RESTORED'
      ) {
        restoreChangeKeyConnectionNotice();
        focusLockedDatabasePassword();
      }
      return;
    }
    runtime.changeKeyTerminalReason = reason;
    applyLocked('session_invalidated');
    if (
      reason === 'CHANGE_KEY_SUCCESS' ||
      reason === 'CHANGE_KEY_RESTORED'
    ) {
      restoreChangeKeyConnectionNotice();
    } else if (reason === 'CHANGE_KEY_RECOVERY_FAILED') {
      setFeedback('error', errorText('CHANGE_KEY_RECOVERY_FAILED'));
      runtime.ready = false;
      runtime.state = 'BLOCKED';
      refreshControls();
    }
    if (
      reason === 'CHANGE_KEY_SUCCESS' ||
      reason === 'CHANGE_KEY_RESTORED'
    ) {
      focusLockedDatabasePassword();
    }
  }

  function applyPublicLock(reason) {
    if (
      ![
        'MANUAL_LOCK',
        'AUTO_LOCK',
        'SUSPEND_LOCK',
        'SESSION_INVALIDATED',
        'RENDERER_FAILURE',
      ].includes(reason)
    ) {
      return;
    }
    if (
      runtime.state === 'LOCKED' &&
      runtime.sessionEpoch === 0 &&
      reason !== 'SESSION_INVALIDATED' &&
      (runtime.lastLockReason || runtime.changeKeyTerminalReason)
    ) {
      return;
    }
    document.documentElement.classList.add(
      'pdm-security-lock-handoff-static',
    );
    applyLocked(
      reason === 'MANUAL_LOCK' ? 'manual_lock' : 'session_invalidated',
    );
    runtime.lastLockReason = reason;
    if (reason === 'AUTO_LOCK') {
      rememberLockedNotice('AUTO');
    } else if (reason === 'SUSPEND_LOCK') {
      rememberLockedNotice('SUSPEND');
    }
    document.documentElement.dataset.pdmM4State = 'locked';
  }

  function onChangeKeyCompleted(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingChangeKey ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    runtime.pendingChangeKey = '';
    resetChangeKeyProgress();
    if (errorCode === 'OK') {
      if (
        !result ||
        result.state !== 'LOCKED' ||
        result.sessionEpoch !== 0 ||
        sessionEpoch !== 0
      ) {
        closeChangeKeyDialog('session_invalidated', true);
        failClosed();
        return;
      }
      return;
    }
    if (result !== null && result !== undefined) {
      closeChangeKeyDialog('session_invalidated', true);
      failClosed();
      return;
    }
    if (errorCode === 'AUTH_FAILED') {
      const current = byId('kf-current');
      if (current instanceof HTMLInputElement) {
        current.value = '';
        current.type = 'password';
      }
      showChangeKeyCurrentError(errorText(errorCode));
      beginChangeKeyCooldown(retryAfterMs);
      window.setTimeout(() => {
        if (activeChangeKeyModal()) current?.focus({preventScroll: true});
      }, 0);
      return;
    }
    if (
      errorCode === 'CHANGE_KEY_FAILED_UNCHANGED' ||
      errorCode === 'CANCELLED' ||
      errorCode === 'INVALID_ARGUMENT' ||
      errorCode === 'REQUEST_BUSY'
    ) {
      showChangeKeyFormError(errorText(errorCode));
      beginChangeKeyCooldown(retryAfterMs);
      return;
    }
    if (errorCode === 'CHANGE_KEY_FAILED_RESTORED') {
      if (sessionEpoch !== 0) {
        closeChangeKeyDialog('session_invalidated', true);
        failClosed();
      }
      return;
    }
    if (errorCode === 'CHANGE_KEY_RECOVERY_FAILED') {
      if (sessionEpoch !== 0) {
        closeChangeKeyDialog('session_invalidated', true);
        failClosed();
      }
      return;
    }
    closeChangeKeyDialog('session_invalidated', true);
    failClosed();
  }

  function onSessionStateChanged(
    pageEpoch,
    sessionEpoch,
    appState,
    reason,
    _databaseLabel,
  ) {
    if (
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== 0 ||
      appState !== 'LOCKED'
    ) {
      return;
    }
    if ([
      'MANUAL_LOCK',
      'AUTO_LOCK',
      'SUSPEND_LOCK',
      'SESSION_INVALIDATED',
      'RENDERER_FAILURE',
    ].includes(reason)) {
      applyPublicLock(reason);
      return;
    }
    if (![
      'CHANGE_KEY_SUCCESS',
      'CHANGE_KEY_RESTORED',
      'CHANGE_KEY_RECOVERY_FAILED',
    ].includes(reason)) return;
    applyChangeKeyTerminal(reason);
  }

  function onRequestProgress(
    pageEpoch,
    sessionEpoch,
    request,
    phase,
    completed,
    total,
  ) {
    if (
      request !== runtime.pendingChangeKey ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch ||
      ![
        'QUEUED', 'DERIVING_KEY', 'READING', 'VALIDATING',
        'ENCRYPTING', 'WRITING', 'COMMITTING', 'RESTORING',
        'FINALIZING',
      ].includes(phase) ||
      !Number.isSafeInteger(completed) ||
      !Number.isSafeInteger(total) ||
      completed < 0 ||
      total < 0 ||
      completed > total
    ) {
      return;
    }
    runtime.changeKeyProgressPhase = phase;
    const button = byId('kf-confirm-btn');
    if (button) {
      button.setAttribute('aria-busy', 'true');
    }
  }

  function closeProductModal() {
    if (activeBackupModal()) {
      closeBackupDialog('modal_close');
      return;
    }
    if (runtime.recordTextModal) {
      cancelFieldReads('name');
      const text = byId('full-record-name');
      if (text) text.value = '';
      runtime.recordTextModal = null;
      closeDemoModal();
      refreshControls();
      return;
    }
    if (activeChangeKeyModal()) {
      closeChangeKeyDialog();
      return;
    }
    const healthGuideModal = byId('active-modal');
    if (
      healthGuideModal?.dataset.pdmM4HealthGuide === 'true' ||
      healthGuideModal?.dataset.pdmM4HealthGuideProgress === 'true'
    ) {
      pauseHealthGuidance();
      return;
    }
    if (activeNoteCreateModal()) {
      closeCreateNoteDialog();
      return;
    }
    if (activeNoteDeleteModal()) {
      closeDeleteNoteDialog();
      return;
    }
    if (activeDeleteModal()) {
      closeDeleteRecordDialog('modal_close');
      return;
    }
    if (activeEditModal()) {
      closeEditRecordDialog('modal_close');
      return;
    }
    if (activeCreateModal()) {
      closeCreateRecordDialog('modal_close');
      return;
    }
    closeDemoModal();
    refreshControls();
  }

  function showCreateFieldError(
    id,
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const error = byId(`${id}-err`);
    if (!error) return;
    setRuntimeText(error, text, fixedZh, fixedEn, i18nKey);
    error.classList.add('show');
    error.setAttribute('aria-hidden', 'false');
    const input = byId(id);
    if (input) {
      input.setAttribute('aria-describedby', `${id}-err`);
      input.setAttribute('aria-invalid', 'true');
    }
  }

  function clearCreateFieldError(id) {
    const error = byId(`${id}-err`);
    if (!error) return;
    setRuntimeText(error, '');
    error.classList.remove('show');
    error.setAttribute('aria-hidden', 'true');
    const input = byId(id);
    if (input) {
      input.setAttribute('aria-describedby', `${id}-err`);
      input.setAttribute('aria-invalid', 'false');
    }
  }

  function showCreateFormError(
    text,
    fixedZh = '',
    fixedEn = '',
    i18nKey = '',
  ) {
    const error = byId('mf-save-err');
    if (!error) return;
    error.classList.remove('pending');
    error.style.removeProperty('color');
    error.setAttribute('role', 'status');
    error.setAttribute('aria-live', 'polite');
    error.setAttribute('aria-atomic', 'true');
    const visible = setRuntimeText(
      error,
      text,
      fixedZh,
      fixedEn,
      i18nKey,
    );
    error.classList.toggle('show', visible);
    error.setAttribute('aria-hidden', visible ? 'false' : 'true');
  }

  function showRecordSaveBusy() {
    showCreateFormError(
      '',
      '正在保存，请稍候…',
      'Saving, please wait…',
    );
    const status = byId('mf-save-err');
    if (!status) return;
    status.classList.add('pending');
    status.style.color = 'var(--text-secondary)';
  }

  function configureCreateDialog(presetPassword = '') {
    const modal = activeCreateModal();
    if (!modal) return false;
    const platform = byId('mf-platform');
    const account = byId('mf-account');
    const password = byId('mf-password');
    const notesField = byId('mf-notes');
    const totp = byId('mf-totp');
    const save = modal.querySelector('.modal-footer .btn-primary');
    if (
      !(platform instanceof HTMLInputElement) ||
      !(account instanceof HTMLInputElement) ||
      !(password instanceof HTMLInputElement) ||
      !(notesField instanceof HTMLTextAreaElement) ||
      !(totp instanceof HTMLInputElement) ||
      !(save instanceof HTMLButtonElement)
    ) {
      return false;
    }
    for (const field of [platform, account, password, notesField]) {
      field.removeAttribute('maxlength');
    }
    totp.maxLength = 256;
    account.dataset.pdmSensitive = 'true';
    password.dataset.pdmSensitive = 'true';
    delete password.dataset.pdmCopyAuthorized;
    notesField.dataset.pdmSensitive = 'true';
    totp.dataset.pdmSensitive = 'true';
    save.id = 'mf-save';
    const totpField = totp.closest('.modal-field');
    if (totpField && !byId('mf-totp-err')) {
      const error = document.createElement('div');
      error.className = 'modal-field-error';
      error.id = 'mf-totp-err';
      error.setAttribute('aria-hidden', 'true');
      totpField.append(error);
    }
    const body = modal.querySelector('.modal-body');
    if (body && !byId('mf-save-err')) {
      const error = document.createElement('div');
      error.className = 'modal-form-error';
      error.id = 'mf-save-err';
      error.setAttribute('aria-hidden', 'true');
      body.append(error);
    }
    const platformError = byId('mf-platform-err');
    if (platformError) {
      platformError.setAttribute('aria-hidden', 'true');
    }
    platform.addEventListener('input', () => {
      clearCreateFieldError('mf-platform');
      showCreateFormError('');
    });
    totp.addEventListener('input', () => {
      clearCreateFieldError('mf-totp');
      showCreateFormError('');
    });
    password.addEventListener('input', () => {
      cancelPendingGeneratedPassword('modal');
      if (runtime.formGeneratedElement !== password) return;
      releaseGeneratedLease('form', 'lease_released', true);
    });
    if (presetPassword) {
      password.value = presetPassword;
    }
    presetPassword = '';
    return true;
  }

  function openCreateRecordDialog(sourceLeaseId = '') {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.editorLauncher ||
      runtime.editorInstanceId ||
      typeof sourceLeaseId !== 'string'
    ) {
      return;
    }
    const id = requestId();
    runtime.editorLauncher.openPasswordCreatorV1(
      id,
      sourceLeaseId,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          showErrorToast(ack && ack.errorCode);
          refreshControls();
          return;
        }
        if (ack.status === 'FOCUSED_EXISTING') {
          showFixedToast(
            '请先保存或取消当前编辑。',
            'Save or cancel the current edit first.',
            'info',
          );
          return;
        }
        if (
          ack.status !== 'OPENING' ||
          typeof ack.instanceId !== 'string' ||
          !ack.instanceId
        ) {
          showErrorToast('INTERNAL_FAILURE');
          return;
        }
        runtime.editorIntentId = id;
        runtime.editorInstanceId = ack.instanceId;
        runtime.editorTarget = {
          recordId: 0,
          revision: '',
          purpose: 'create',
        };
        refreshControls();
      },
    );
  }

  function normalizeRecordEditorLease(result) {
    const longFields = normalizedLongFields(result?.longFields);
    if (
      !longFields ||
      !result ||
      Object.prototype.hasOwnProperty.call(result, 'totpSecret') ||
      Object.prototype.hasOwnProperty.call(result, 'totp_secret') ||
      !Number.isSafeInteger(result.recordId) ||
      result.recordId < 1 ||
      !isRevision(result.revision) ||
      typeof result.platform !== 'string' ||
      !result.platform ||
      !recordFieldFits('PLATFORM', result.platform) ||
      typeof result.account !== 'string' ||
      !recordFieldFits('ACCOUNT', result.account) ||
      typeof result.password !== 'string' ||
      !recordFieldFits('PASSWORD', result.password) ||
      typeof result.notes !== 'string' ||
      !recordFieldFits('NOTES', result.notes) ||
      typeof result.hasTotp !== 'boolean' ||
      typeof result.favorite !== 'boolean' ||
      typeof result.editLeaseId !== 'string' ||
      !/^[A-Za-z0-9_-]{16,64}$/.test(result.editLeaseId) ||
      !Number.isSafeInteger(result.expiresInMs) ||
      result.expiresInMs < 1 ||
      result.expiresInMs > 300000
    ) {
      return null;
    }
    return {
      recordId: result.recordId,
      revision: result.revision,
      platform: result.platform,
      account: result.account,
      password: result.password,
      notes: result.notes,
      longFields,
      hasTotp: result.hasTotp,
      favorite: result.favorite,
      editLeaseId: result.editLeaseId,
      expiresInMs: result.expiresInMs,
    };
  }

  function scrubRecordEditorResult(result) {
    if (!result || typeof result !== 'object') return;
    result.account = '';
    result.password = '';
    result.notes = '';
  }

  function releaseReturnedEditorLease(result) {
    const leaseId = result && result.editLeaseId;
    scrubRecordEditorResult(result);
    if (
      typeof leaseId === 'string' &&
      /^[A-Za-z0-9_-]{16,64}$/.test(leaseId)
    ) {
      releaseNativeSecretLease(leaseId);
    }
  }

  function updateEditTotpUi() {
    const hint = byId('mf-totp-hint');
    const remove = byId('mf-totp-remove');
    if (hint) {
      if (runtime.editTotpAction === 'CLEAR') {
        setRuntimeText(
          hint,
          '',
          '保存后将移除现有 TOTP；密钥不会显示在界面中。',
          'Saving will remove the existing TOTP. Its secret is never displayed.',
        );
      } else if (runtime.editHasTotp) {
        setRuntimeText(
          hint,
          '',
          '当前已启用；留空保留，输入新 Base32 密钥则替换。',
          'Currently enabled. Leave empty to keep it, or enter a new Base32 secret to replace it.',
        );
      } else {
        setRuntimeText(
          hint,
          '',
          '当前未启用；输入 Base32 密钥即可启用。',
          'Currently disabled. Enter a Base32 secret to enable it.',
        );
      }
    }
    if (remove instanceof HTMLButtonElement) {
      remove.hidden = !runtime.editHasTotp;
      if (runtime.editTotpAction === 'CLEAR') {
        setRuntimeText(remove, '', '撤销移除', 'Undo removal');
      } else {
        setRuntimeText(
          remove,
          '',
          '移除现有 TOTP',
          'Remove current TOTP',
        );
      }
    }
  }

  function updateEditRecoveryUi() {
    const actions = byId('mf-edit-actions');
    const reload = byId('mf-edit-reload');
    const retry = byId('mf-edit-retry');
    if (!actions) return;
    const canReload = Boolean(
      runtime.editConflict &&
      runtime.editReloadRevision
    );
    const canRetry = Boolean(
      !runtime.editConflict &&
      !runtime.editLeaseId &&
      !runtime.pendingEditOpen &&
      !runtime.pendingEditSave
    );
    actions.hidden = !canReload && !canRetry;
    if (reload instanceof HTMLButtonElement) {
      reload.hidden = !runtime.editConflict;
      reload.disabled = !canReload;
    }
    if (retry instanceof HTMLButtonElement) {
      retry.hidden = !canRetry;
    }
  }

  function setEditConflict() {
    runtime.editConflict = true;
    runtime.editReloadRevision = '';
    showCreateFormError(
      '',
      '记录已在别处发生变化。你的未提交内容仍保留；请加载最新内容后再编辑。',
      'The record changed elsewhere. Your unsaved input is preserved; load the latest version before editing again.',
    );
    updateEditRecoveryUi();
    resetVaultPagePosition();
    requestVaultPage();
  }

  function bindEditorPasswordLease(lease, replacePassword) {
    const password = byId('mf-password');
    if (
      !(password instanceof HTMLInputElement) ||
      !window.pdmSensitiveDom
    ) {
      return false;
    }
    if (runtime.editLeaseId) {
      releaseEditorLease('lease_released', true);
    }
    if (replacePassword) {
      password.value = lease.password;
      password.type = 'password';
    }
    password.dataset.pdmSensitive = 'true';
    try {
      window.pdmSensitiveDom.bindLease(
        lease.editLeaseId,
        'EDITOR',
        lease.expiresInMs,
        [password],
      );
    } catch (_error) {
      if (replacePassword) password.value = '';
      return false;
    }
    runtime.editLeaseId = lease.editLeaseId;
    return true;
  }

  function configureEditDialog(lease) {
    renderDemoAddPasswordDialog('');
    const modal = byId('active-modal');
    if (!modal) return false;
    modal.dataset.pdmM4Create = 'true';
    if (!configureCreateDialog('')) {
      delete modal.dataset.pdmM4Create;
      closeDemoModal();
      return false;
    }
    delete modal.dataset.pdmM4Create;
    modal.dataset.pdmM4Edit = 'true';
    const title = modal.querySelector('.modal-title');
    const save = byId('mf-save');
    const platform = byId('mf-platform');
    const account = byId('mf-account');
    const password = byId('mf-password');
    const notesField = byId('mf-notes');
    const totp = byId('mf-totp');
    const favorite = byId('mf-favorite');
    if (
      !title ||
      !(save instanceof HTMLButtonElement) ||
      !(platform instanceof HTMLInputElement) ||
      !(account instanceof HTMLInputElement) ||
      !(password instanceof HTMLInputElement) ||
      !(notesField instanceof HTMLTextAreaElement) ||
      !(totp instanceof HTMLInputElement)
    ) {
      closeDemoModal();
      return false;
    }
    title.removeAttribute('data-i18n');
    title.innerHTML = (
      `${svgIcon('pencil', 18)} <span data-i18n="dialog.pwd.title.edit">${t('dialog.pwd.title.edit')}</span>`
    );
    save.setAttribute('data-pdm-onclick', 'saveEditPassword()');
    platform.value = lease.platform;
    account.value = lease.account;
    notesField.value = lease.notes;
    totp.value = '';
    totp.placeholder = fixedText(
      '输入新 Base32 密钥以替换',
      'Enter a new Base32 secret to replace it',
    );
    totp.dataset.i18nPlaceholder = 'dialog.pwd.placeholder.totpReplace';
    if (favorite) favorite.classList.toggle('active', lease.favorite);
    const totpField = totp.closest('.modal-field');
    if (totpField) {
      const hint = document.createElement('div');
      hint.className = 'modal-field-hint';
      hint.id = 'mf-totp-hint';
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'modal-inline-action';
      remove.id = 'mf-totp-remove';
      remove.setAttribute('data-pdm-onclick', 'toggleEditTotpRemoval()');
      totpField.append(hint, remove);
    }
    const body = modal.querySelector('.modal-body');
    if (body) {
      const recovery = document.createElement('div');
      recovery.className = 'modal-edit-actions';
      recovery.id = 'mf-edit-actions';
      recovery.hidden = true;
      const reload = document.createElement('button');
      reload.type = 'button';
      reload.className = 'btn btn-sm';
      reload.id = 'mf-edit-reload';
      setRuntimeText(reload, '', '加载最新内容', 'Load latest content');
      reload.setAttribute('data-pdm-onclick', 'reloadLatestEditRecord()');
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'btn btn-sm';
      retry.id = 'mf-edit-retry';
      setRuntimeText(
        retry,
        '',
        '重新取得保存权限',
        'Reauthorize saving',
      );
      retry.setAttribute('data-pdm-onclick', 'retryEditAuthorization()');
      recovery.append(reload, retry);
      body.append(recovery);
    }
    runtime.editModalActive = true;
    runtime.editRecordId = lease.recordId;
    runtime.editRevision = lease.revision;
    runtime.editHasTotp = lease.hasTotp;
    runtime.editTotpAction = 'KEEP';
    runtime.editPasswordDirty = false;
    runtime.editConflict = false;
    runtime.editReloadRevision = '';
    if (!bindEditorPasswordLease(lease, true)) {
      scrubEditForm('modal_close');
      closeDemoModal();
      return false;
    }
    password.addEventListener('input', () => {
      if (!activeEditModal()) return;
      cancelPendingGeneratedPassword('modal');
      if (runtime.formGeneratedElement === password) {
        releaseGeneratedLease('form', 'lease_released', true);
      }
      if (!runtime.editPasswordDirty && runtime.editLeaseId) {
        detachEditorDomLease(
          runtime.editLeaseId,
          'lease_consumed',
          true,
        );
      }
      runtime.editPasswordDirty = true;
      showCreateFormError('');
    });
    totp.addEventListener('input', () => {
      if (!activeEditModal()) return;
      runtime.editTotpAction = totp.value.trim() ? 'REPLACE' : 'KEEP';
      updateEditTotpUi();
      updateEditRecoveryUi();
    });
    for (const [field, definition] of Object.entries(RECORD_FIELDS)) {
      byId(definition.id).addEventListener('input', () => {
        const metadata = runtime.editorFieldMeta?.fields[field];
        if (metadata) metadata.touched = true;
      });
    }
    hydrateEditorFields(lease, true);
    updateEditTotpUi();
    updateEditRecoveryUi();
    return true;
  }

  function applyEditorLeaseToOpenDialog(lease, replaceFields) {
    const modal = activeEditModal();
    const platform = byId('mf-platform');
    const account = byId('mf-account');
    const password = byId('mf-password');
    const notesField = byId('mf-notes');
    const totp = byId('mf-totp');
    const favorite = byId('mf-favorite');
    if (
      !modal ||
      !(platform instanceof HTMLInputElement) ||
      !(account instanceof HTMLInputElement) ||
      !(password instanceof HTMLInputElement) ||
      !(notesField instanceof HTMLTextAreaElement) ||
      !(totp instanceof HTMLInputElement)
    ) {
      return false;
    }
    if (replaceFields) {
      releaseGeneratedLease('form', 'lease_released');
      platform.value = lease.platform;
      account.value = lease.account;
      notesField.value = lease.notes;
      totp.value = '';
      if (favorite) favorite.classList.toggle('active', lease.favorite);
      runtime.editRecordId = lease.recordId;
      runtime.editRevision = lease.revision;
      runtime.editHasTotp = lease.hasTotp;
      runtime.editTotpAction = 'KEEP';
      runtime.editPasswordDirty = false;
      runtime.editConflict = false;
      runtime.editReloadRevision = '';
      clearCreateFieldError('mf-platform');
      clearCreateFieldError('mf-totp');
      showCreateFormError('');
    }
    const preserveEditorView = !replaceFields && !runtime.editPasswordDirty;
    const passwordType = preserveEditorView ? password.type : 'password';
    const selectionStart = preserveEditorView ? password.selectionStart : null;
    const selectionEnd = preserveEditorView ? password.selectionEnd : null;
    const selectionDirection = preserveEditorView ? password.selectionDirection : null;
    const replacePassword = replaceFields || !runtime.editPasswordDirty;
    if (replacePassword) {
      const preserveLongPassword = !replaceFields && lease.longFields.includes('PASSWORD') &&
        runtime.editorFieldMeta?.fields.PASSWORD.loaded;
      if (!bindEditorPasswordLease(lease, !preserveLongPassword)) return false;
      if (preserveEditorView) {
        password.type = passwordType;
        if (selectionStart !== null && selectionEnd !== null) {
          try { password.setSelectionRange(selectionStart, selectionEnd, selectionDirection); } catch (_error) {}
        }
      }
    } else {
      if (runtime.editLeaseId) {
        releaseEditorLease('lease_released', true);
      }
      runtime.editLeaseId = lease.editLeaseId;
    }
    hydrateEditorFields(lease, replaceFields);
    updateEditTotpUi();
    updateEditRecoveryUi();
    return true;
  }

  async function hydrateEditorFields(lease, replaceFields) {
    cancelFieldReads('editor');
    let metadata = runtime.editorFieldMeta;
    if (replaceFields || !metadata || metadata.recordId !== lease.recordId || metadata.revision !== lease.revision) {
      metadata = {recordId: lease.recordId, revision: lease.revision, fields: {}};
      runtime.editorFieldMeta = metadata;
      for (const field of Object.keys(RECORD_FIELDS)) {
        metadata.fields[field] = {long: lease.longFields.includes(field), loaded: false, touched: false, digest: ''};
      }
    }
    runtime.editorPreparing = true;
    refreshControls();
    const jobs = Object.entries(RECORD_FIELDS).map(async ([field, definition]) => {
      const state = metadata.fields[field];
      const target = byId(definition.id);
      if (!target || state.loaded || state.touched) return;
      const remember = async (element) => {
        const digest = await recordFieldDigest(fieldTargetValue(element));
        if (runtime.editorFieldMeta !== metadata || runtime.editRevision !== lease.revision) return;
        state.digest = digest;
        state.loaded = true;
      };
      if (state.long) {
        let hint = byId(`${definition.id}-long-hint`);
        if (!hint) {
          hint = document.createElement('div');
          hint.id = `${definition.id}-long-hint`;
          hint.className = 'modal-field-hint';
          target.closest('.modal-field')?.append(hint);
        }
        setRuntimeText(hint, '', '已有内容超过输入限额；可原样保留，修改后需缩短。',
          'Existing content exceeds the input limit. Keep it unchanged or shorten it before saving.');
        let retry = byId(`${definition.id}-read-retry`);
        if (!retry) {
          retry = document.createElement('button');
          retry.id = `${definition.id}-read-retry`;
          retry.type = 'button';
          retry.className = 'btn btn-sm';
          hint.after(retry);
          retry.addEventListener('click', () => retry._pdmReadOriginal?.());
        }
        setRuntimeText(retry, '', '重新读取原文', 'Reload original');
        retry.hidden = true;
        retry._pdmReadOriginal = async () => {
          if (runtime.editorFieldMeta !== metadata || runtime.editorPreparing) return;
          if (state.touched) {
            showCreateFormError(fixedText('当前字段已有修改；请保留修改，或取消编辑后重新打开原文。',
              'This field has changes. Keep them, or cancel editing before reopening the original.'));
            return;
          }
          runtime.editorPreparing = true;
          refreshControls();
          const loaded = await readRecordField(lease, field, target, 'editor', runtime.editLeaseId, remember);
          retry.hidden = loaded;
          if (runtime.editorFieldMeta === metadata) runtime.editorPreparing = false;
          refreshEditorCopyAuthorization();
          refreshControls();
        };
        const loaded = await readRecordField(lease, field, target, 'editor', lease.editLeaseId, remember);
        if (runtime.editorFieldMeta === metadata) retry.hidden = loaded;
      } else {
        await remember(target);
      }
    });
    try { await Promise.all(jobs); }
    catch (_error) {
      if (runtime.editorFieldMeta === metadata) showCreateFormError(errorText('INTERNAL_FAILURE'));
    } finally {
      if (runtime.editorFieldMeta === metadata) {
        runtime.editorPreparing = false;
        refreshEditorCopyAuthorization();
        refreshControls();
      }
    }
  }

  function handleEditorOpenError(purpose, errorCode) {
    if (
      errorCode === 'SESSION_REQUIRED' ||
      errorCode === 'STALE_SESSION' ||
      errorCode === 'STALE_PAGE'
    ) {
      applyLocked('session_invalidated');
      return;
    }
    if (purpose === 'initial') {
      showErrorToast(errorCode);
      if (runtime.healthGuideEditTarget) {
        runtime.healthGuideEditTarget = null;
        runtime.healthEditRecordId = 0;
        pauseHealthGuidance();
        return;
      }
      if (runtime.healthSingleOrigin) {
        runtime.healthEditRecordId = 0;
        restoreHealthSingleOrigin();
        runtime.healthSingleOrigin = null;
        return;
      }
      if (
        errorCode === 'NOT_FOUND' ||
        errorCode === 'REVISION_CONFLICT'
      ) {
        resetVaultPagePosition();
        requestVaultPage();
      }
      return;
    }
    if (errorCode === 'NOT_FOUND') {
      closeEditRecordDialog('lease_released');
      showFixedToast(
        '记录已不存在，编辑器已关闭。',
        'The record no longer exists. The editor was closed.',
        'error',
      );
      resetVaultPagePosition();
      requestVaultPage();
      return;
    }
    if (errorCode === 'REVISION_CONFLICT') {
      setEditConflict();
      return;
    }
    showCreateFormError(errorText(errorCode));
    updateEditRecoveryUi();
    refreshControls();
  }

  function requestRecordEditor(
    record,
    purpose = 'initial',
    generateAfterOpen = false,
  ) {
    const recordId = Number(record && record.recordId);
    const revision = String(record && record.revision || '');
    const initial = purpose === 'initial';
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.editorLauncher ||
      !Number.isSafeInteger(recordId) ||
      recordId < 1 ||
      !isRevision(revision) ||
      !initial
    ) {
      return;
    }
    const id = requestId();
    runtime.editorLauncher.openPasswordEditorV1(
      id,
      recordId,
      revision,
      Boolean(generateAfterOpen),
      (ack) => {
        if (
          !ack ||
          ack.accepted !== true ||
          ack.errorCode !== 'OK'
        ) {
          handleEditorOpenError(purpose, ack && ack.errorCode);
          refreshControls();
          return;
        }
        if (ack.status === 'FOCUSED_EXISTING') {
          showFixedToast(
            '请先保存或取消当前编辑。',
            'Save or cancel the current edit first.',
            'info',
          );
          return;
        }
        if (
          ack.status !== 'OPENING' ||
          typeof ack.instanceId !== 'string' ||
          !ack.instanceId
        ) {
          handleEditorOpenError(purpose, 'INTERNAL_FAILURE');
          return;
        }
        runtime.editorIntentId = id;
        runtime.editorInstanceId = ack.instanceId;
        runtime.editorTarget = {recordId, revision, purpose};
        refreshControls();
      },
    );
  }

  function clearIndependentEditorState() {
    runtime.editorIntentId = '';
    runtime.editorInstanceId = '';
    runtime.editorTarget = null;
  }

  function onIndependentEditorDataChanged(
    pageEpoch,
    sessionEpoch,
    vaultRevision,
    noteRevision,
    healthRevision,
  ) {
    if (
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch ||
      !isRevision(vaultRevision) ||
      !isRevision(noteRevision) ||
      !isRevision(healthRevision)
    ) {
      return;
    }
    runtime.vaultRevision = vaultRevision;
    runtime.noteRevision = noteRevision;
    runtime.healthRevision = healthRevision;
    runtime.ratingVaultDirty = runtime.ratingHealthDirty = true;
    queueRatingRefresh();
  }

  function onIndependentEditorFinished(
    intentId,
    instanceId,
    outcome,
    recordId,
    revision,
  ) {
    if (
      intentId !== runtime.editorIntentId ||
      instanceId !== runtime.editorInstanceId ||
      !runtime.editorTarget ||
      runtime.editorTarget.recordId !== recordId
    ) {
      return;
    }
    const purpose = runtime.editorTarget.purpose;
    const kind = runtime.editorTarget.kind || 'PASSWORD';
    const guideTarget = runtime.healthGuideEditTarget;
    const healthEdit = runtime.healthEditRecordId === recordId;
    clearIndependentEditorState();
    runtime.healthEditRecordId = 0;
    if (kind === 'NOTE') {
      if (outcome === 'SAVED' && purpose === 'create') {
        resetNotePagePosition(); requestNotePage();
        showI18nToast('toast.note.dialogAdded', 'success');
      } else if (outcome === 'SAVED') {
        const item = runtime.noteItems.find((value) => value.noteId === recordId);
        if (item && isRevision(revision)) {
          item.revision = revision;
          clearSelectedNoteDetails();
          requestNoteDetails(item);
        } else {
          resetNotePagePosition(); requestNotePage();
        }
        showI18nToast('toast.note.saved', 'success');
      } else if (outcome === 'DELETED') {
        resetNotePagePosition(); requestNotePage();
        showI18nToast('toast.note.deleted.generic', 'success');
      }
      refreshControls();
      return;
    }
    if (outcome === 'SAVED') {
      clearSelectedDetailContent();
      if (purpose === 'create') {
        resetVaultPagePosition(true);
        requestVaultPage();
        showI18nToast('toast.pwd.added', 'success');
      } else if (
        guideTarget && runtime.healthGuide &&
        guideTarget.guidanceId === runtime.healthGuide.guidanceId &&
        guideTarget.recordId === recordId &&
        runtime.healthGuide.states[guideTarget.globalIndex] === 0 &&
        runtime.healthGuide.items[
          guideTarget.globalIndex - runtime.healthGuide.pageIndex * 100
        ]?.issueId === guideTarget.issueId
      ) {
        runtime.healthGuide.states[guideTarget.globalIndex] = 1;
        resetVaultPagePosition(true);
        requestVaultPage();
        runtime.healthGuideEditTarget = null;
        const localIndex = (
          guideTarget.globalIndex - runtime.healthGuide.pageIndex * 100
        );
        runtime.healthGuide.itemIndex = localIndex + 1;
        if (runtime.healthGuide.states.every((value) => value !== 0)) {
          finishHealthGuidance();
        } else {
          showHealthGuidanceProgress();
        }
      } else if (healthEdit && runtime.healthSingleOrigin) {
        resetVaultPagePosition(true);
        requestVaultPage();
        requestHealthOverview(runtime.healthSingleOrigin);
      } else {
        resetVaultPagePosition(true);
        requestVaultPage();
      }
      if (purpose !== 'create') {
        showI18nToast('toast.pwd.updated', 'success');
      }
    } else if (outcome === 'DISCARDED' || outcome === 'OPEN_FAILED') {
      if (guideTarget && runtime.healthGuide) {
        runtime.healthGuideEditTarget = null;
        pauseHealthGuidance();
      } else if (runtime.healthSingleOrigin) {
        restoreHealthSingleOrigin();
        runtime.healthSingleOrigin = null;
      }
    }
    refreshControls();
  }

  function onRecordEditorOpened(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingEditOpen ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      releaseReturnedEditorLease(result);
      return;
    }
    const purpose = runtime.editOpenPurpose;
    const expectedRecordId = runtime.editOpenRecordId;
    const expectedRevision = runtime.editOpenRevision;
    const generateAfterOpen = runtime.editGenerateAfterOpen;
    runtime.pendingEditOpen = '';
    runtime.editOpenPurpose = '';
    runtime.editOpenRecordId = 0;
    runtime.editOpenRevision = '';
    runtime.editGenerateAfterOpen = false;
    if (errorCode !== 'OK') {
      releaseReturnedEditorLease(result);
      handleEditorOpenError(purpose, errorCode);
      refreshControls();
      return;
    }
    const lease = normalizeRecordEditorLease(result);
    if (!lease) releaseReturnedEditorLease(result);
    scrubRecordEditorResult(result);
    if (
      !lease ||
      lease.recordId !== expectedRecordId ||
      lease.revision !== expectedRevision
    ) {
      if (lease) releaseNativeSecretLease(lease.editLeaseId);
      if (lease) lease.password = '';
      handleEditorOpenError(purpose, 'INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    let applied = false;
    if (purpose === 'initial') {
      applied = configureEditDialog(lease);
    } else {
      applied = applyEditorLeaseToOpenDialog(
        lease,
        purpose === 'reload',
      );
    }
    if (!applied) {
      releaseNativeSecretLease(lease.editLeaseId);
      showCreateFormError(errorText('INTERNAL_FAILURE'));
    } else if (generateAfterOpen) {
      requestGeneratedPassword('modal');
    }
    lease.password = '';
    lease.account = '';
    lease.notes = '';
    refreshControls();
  }

  function toggleEditTotpRemoval() {
    if (!activeEditModal() || !runtime.editHasTotp) return;
    const totp = byId('mf-totp');
    if (!(totp instanceof HTMLInputElement)) return;
    if (runtime.editTotpAction === 'CLEAR') {
      runtime.editTotpAction = 'KEEP';
    } else {
      totp.value = '';
      runtime.editTotpAction = 'CLEAR';
      clearCreateFieldError('mf-totp');
      showCreateFormError('');
    }
    updateEditTotpUi();
    refreshControls();
  }

  function reloadLatestEditRecord() {
    if (
      !activeEditModal() ||
      !runtime.editConflict ||
      !runtime.editReloadRevision
    ) {
      return;
    }
    requestRecordEditor(
      {
        recordId: runtime.editRecordId,
        revision: runtime.editReloadRevision,
      },
      'reload',
      false,
    );
  }

  function retryEditAuthorization() {
    if (
      !activeEditModal() ||
      runtime.editConflict ||
      runtime.editLeaseId ||
      runtime.pendingEditOpen ||
      runtime.pendingEditSave ||
      runtime.editCooldownUntil > Date.now()
    ) {
      return;
    }
    requestRecordEditor(
      {
        recordId: runtime.editRecordId,
        revision: runtime.editRevision,
      },
      'reauthorize',
      false,
    );
  }

  function looksLikeTotpSecret(value) {
    if (!value || !/^[A-Za-z2-7= \-]+$/.test(value)) return false;
    const compact = value.replace(/[\s-]/g, '').toUpperCase();
    const unpadded = compact.replace(/=+$/, '');
    return Boolean(unpadded) && !unpadded.includes('=');
  }

  function submitCreateRecord() {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.bridge ||
      runtime.pendingCreate ||
      (runtime.pendingGenerate && runtime.generateTarget === 'modal') ||
      runtime.createCooldownUntil > Date.now() ||
      !activeCreateModal()
    ) {
      return;
    }
    const platformInput = byId('mf-platform');
    const accountInput = byId('mf-account');
    const passwordInput = byId('mf-password');
    const notesInput = byId('mf-notes');
    const totpInput = byId('mf-totp');
    const favorite = byId('mf-favorite');
    if (
      !(platformInput instanceof HTMLInputElement) ||
      !(accountInput instanceof HTMLInputElement) ||
      !(passwordInput instanceof HTMLInputElement) ||
      !(notesInput instanceof HTMLTextAreaElement) ||
      !(totpInput instanceof HTMLInputElement)
    ) {
      return;
    }
    let platform = platformInput.value;
    let account = accountInput.value.trim();
    let password = passwordInput.value;
    let recordNotes = notesInput.value.trim();
    let totpSecret = totpInput.value.trim();
    for (const [field, value] of Object.entries({PLATFORM: platform, ACCOUNT: account, PASSWORD: password, NOTES: recordNotes})) {
      if (!recordFieldFits(field, value)) {
        const definition = RECORD_FIELDS[field];
        showCreateFormError(fixedText(`字段超过 ${definition.limit} 字或 ${definition.bytes} 字节的输入限制。`,
          `Field exceeds ${definition.limit} characters or ${definition.bytes} bytes.`));
        byId(definition.id)?.focus({preventScroll: true});
        return;
      }
    }
    if (!platform.trim()) {
      showCreateFieldError(
        'mf-platform',
        '',
        '',
        '',
        'dialog.pwd.error.platformEmpty',
      );
      platformInput.focus({preventScroll: true});
      return;
    }
    if (totpSecret && !looksLikeTotpSecret(totpSecret)) {
      showCreateFieldError(
        'mf-totp',
        '',
        'TOTP 密钥格式无效，请输入 Base32 字符。',
        'The TOTP secret is invalid. Enter a Base32 value.',
      );
      totpInput.focus({preventScroll: true});
      return;
    }
    clearCreateFieldError('mf-platform');
    clearCreateFieldError('mf-totp');
    showCreateFormError('');
    const id = requestId();
    runtime.pendingCreate = id;
    showRecordSaveBusy();
    refreshControls();
    try {
      runtime.bridge.createRecordV1(
        id,
        runtime.pageEpoch,
        runtime.sessionEpoch,
        platform,
        account,
        password,
        recordNotes,
        totpSecret ? 'REPLACE' : 'NONE',
        totpSecret,
        Boolean(favorite && favorite.classList.contains('active')),
        '',
        (ack) => {
          if (
            !ack ||
            ack.accepted !== true ||
            ack.errorCode !== 'OK'
          ) {
            if (runtime.pendingCreate === id) {
              runtime.pendingCreate = '';
              showCreateFormError(errorText(ack && ack.errorCode));
              refreshControls();
            }
          }
        },
      );
    } finally {
      platform = '';
      account = '';
      password = '';
      recordNotes = '';
      totpSecret = '';
    }
  }

  function reauthorizeOpenEditRecord() {
    if (
      !activeEditModal() ||
      runtime.editConflict ||
      runtime.pendingEditOpen ||
      runtime.pendingEditSave
    ) {
      updateEditRecoveryUi();
      return;
    }
    requestRecordEditor(
      {
        recordId: runtime.editRecordId,
        revision: runtime.editRevision,
      },
      'reauthorize',
      false,
    );
  }

  function settleSubmittedEditLease(preservePassword) {
    const leaseId = runtime.editSubmittedLeaseId;
    runtime.editSubmittedLeaseId = '';
    refreshEditorCopyAuthorization();
    detachEditorDomLease(
      leaseId,
      'lease_consumed',
      preservePassword,
    );
  }

  function handleEditWriteFailure(
    errorCode,
    errorArgumentIndex,
    retryAfterMs,
  ) {
    if (
      errorCode === 'SESSION_REQUIRED' ||
      errorCode === 'STALE_SESSION' ||
      errorCode === 'STALE_PAGE'
    ) {
      closeEditRecordDialog('session_invalidated');
      applyLocked('session_invalidated');
      return;
    }
    if (errorCode === 'NOT_FOUND') {
      closeEditRecordDialog('lease_released');
      showFixedToast(
        '记录已不存在，编辑器已关闭。',
        'The record no longer exists. The editor was closed.',
        'error',
      );
      resetVaultPagePosition();
      requestVaultPage();
      return;
    }
    if (errorCode === 'REVISION_CONFLICT') {
      setEditConflict();
      beginEditCooldown(retryAfterMs);
      return;
    }
    if (errorCode === 'PLATFORM_CONFLICT') {
      showCreateFieldError(
        'mf-platform',
        errorText('PLATFORM_CONFLICT'),
      );
      byId('mf-platform')?.focus({preventScroll: true});
    } else if (
      errorCode === 'INVALID_ARGUMENT' &&
      (errorArgumentIndex === 12 || errorArgumentIndex === 13)
    ) {
      showCreateFieldError(
        'mf-totp',
        '',
        'TOTP 密钥格式无效，请检查后重试。',
        'The TOTP secret is invalid. Check it and try again.',
      );
      byId('mf-totp')?.focus({preventScroll: true});
    } else {
      if (errorCode === 'DATABASE_IO_FAILED') {
        showCreateFormError(
          '',
          '',
          '',
          'dialog.pwd.error.save_failed',
        );
      } else {
        showCreateFormError(errorText(errorCode));
      }
    }
    beginEditCooldown(retryAfterMs);
    reauthorizeOpenEditRecord();
  }

  async function submitEditRecord() {
    if (runtime.state !== 'UNLOCKED' || !runtime.bridge || runtime.pendingEditOpen || runtime.pendingEditSave ||
        (runtime.pendingGenerate && runtime.generateTarget === 'modal') ||
        runtime.editorPreparing || runtime.editCooldownUntil > Date.now() || runtime.editConflict ||
        !runtime.editLeaseId || !activeEditModal() || !runtime.editorFieldMeta) return;
    const metadata = runtime.editorFieldMeta;
    const editLeaseId = runtime.editLeaseId;
    const page = runtime.pageEpoch;
    const session = runtime.sessionEpoch;
    const values = {};
    const actions = {};
    const snapshotValues = {};
    const favorite = byId('mf-favorite')?.classList.contains('active') === true;
    let totpSecret = byId('mf-totp')?.value.trim() || '';
    let totpAction = runtime.editTotpAction === 'CLEAR' ? 'CLEAR' : totpSecret ? 'REPLACE' : 'KEEP';
    if (totpAction === 'CLEAR') totpSecret = '';
    if (totpAction === 'REPLACE' && !looksLikeTotpSecret(totpSecret)) {
      showCreateFieldError('mf-totp', '', '动态验证码密钥格式无效。', 'Invalid TOTP secret.');
      byId('mf-totp')?.focus({preventScroll: true});
      return;
    }
    runtime.editorPreparing = true;
    refreshControls();
    try {
      for (const [field, definition] of Object.entries(RECORD_FIELDS)) {
        const target = byId(definition.id);
        if (!target) return;
        snapshotValues[field] = target.value;
        const value = target.value;
        const original = metadata.fields[field];
        const unchanged = original.loaded && original.digest
          ? await recordFieldDigest(value) === original.digest
          : original.long && !original.touched;
        if (runtime.editorFieldMeta !== metadata || runtime.editLeaseId !== editLeaseId ||
            runtime.pageEpoch !== page || runtime.sessionEpoch !== session || !activeEditModal()) return;
        if (unchanged) {
          actions[field] = 'KEEP';
          values[field] = '';
          continue;
        }
        if (!recordFieldFits(field, value) || (field === 'PLATFORM' && !value.trim())) {
          showCreateFormError(fixedText(
            `修改后的字段需满足 ${definition.limit} 字和 ${definition.bytes} 字节以内的输入限制；未修改的旧内容可保留。`,
            `Changed fields must fit ${definition.limit} characters and ${definition.bytes} bytes. Unchanged existing content can be kept.`));
          target.focus({preventScroll: true});
          return;
        }
        actions[field] = 'REPLACE';
        values[field] = value;
      }
      if (Object.entries(RECORD_FIELDS).some(([field, definition]) => byId(definition.id)?.value !== snapshotValues[field])) {
        showCreateFormError(fixedText('输入已变化，请再次保存。', 'Input changed. Please save again.'));
        return;
      }
      if (runtime.formGeneratedLeaseId) {
        releaseGeneratedLease('form', 'lease_consumed', true);
      }
      const id = requestId();
      runtime.editLeaseId = '';
      runtime.editSubmittedLeaseId = editLeaseId;
      refreshEditorCopyAuthorization();
      runtime.pendingEditSave = id;
      runtime.editorPreparing = false;
      showRecordSaveBusy();
      refreshControls();
      const originalArgument = (argument) => ({8: 7, 10: 8, 11: 9, 12: 10, 14: 11, 15: 12, 16: 13, 17: 14}[argument] || argument);
      runtime.bridge.updateRecordFieldsV1(id, page, session, runtime.editRecordId, runtime.editRevision, editLeaseId,
        actions.PLATFORM, values.PLATFORM, actions.ACCOUNT, values.ACCOUNT,
        actions.PASSWORD, values.PASSWORD, actions.NOTES, values.NOTES,
        totpAction, totpSecret, favorite, 'KEEP', '',
        (ack) => {
          if ((!ack || ack.accepted !== true || ack.errorCode !== 'OK') && runtime.pendingEditSave === id) {
            runtime.pendingEditSave = '';
            settleSubmittedEditLease(true);
            releaseNativeSecretLease(editLeaseId);
            handleEditWriteFailure(ack?.errorCode || 'INTERNAL_FAILURE', originalArgument(ack?.errorArgumentIndex || 0), ack?.retryAfterMs || 0);
            refreshControls();
          }
        });
    } catch (_error) {
      if (runtime.editorFieldMeta === metadata && activeEditModal()) showCreateFormError(errorText('INTERNAL_FAILURE'));
    } finally {
      for (const field of Object.keys(values)) values[field] = '';
      for (const field of Object.keys(snapshotValues)) snapshotValues[field] = '';
      totpSecret = '';
      totpAction = '';
      if (runtime.editorFieldMeta === metadata) runtime.editorPreparing = false;
      refreshControls();
    }
  }

  function requestRecordFavorite(record, favorite) {
    record = currentRecordForAction(record);
    if (
      !record ||
      !Number.isSafeInteger(record.recordId) ||
      !isRevision(record.revision) ||
      typeof favorite !== 'boolean' ||
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pendingFavorite
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingFavorite = id;
    runtime.pendingFavoriteRecordId = record.recordId;
    refreshControls();
    runtime.bridge.setRecordFavoriteV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      record.recordId,
      record.revision,
      favorite,
      (ack) => {
        if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
          if (runtime.pendingFavorite === id) {
            runtime.pendingFavorite = '';
            showErrorToast(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function onRecordFavoriteSet(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingFavorite ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      scrubRecordWriteResult(result);
      return;
    }
    const expectedRecordId = runtime.pendingFavoriteRecordId;
    runtime.pendingFavorite = '';
    runtime.pendingFavoriteRecordId = 0;
    if (errorCode !== 'OK') {
      scrubRecordWriteResult(result);
      handleRecordActionError(errorCode);
      refreshControls();
      return;
    }
    const item = normalizeRecordWriteItem(result && result.item);
    if (
      !item || item.recordId !== expectedRecordId ||
      !isRevision(result.vaultRevision) ||
      !isRevision(result.healthRevision)
    ) {
      scrubRecordWriteResult(result);
      showErrorToast('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.vaultRevision = result.vaultRevision;
    if (runtime.selectedRecordId === item.recordId) {
      clearSelectedDetailContent();
      runtime.selectedRevision = item.revision;
      if (runtime.vaultFilter === 'FAVORITE' && !item.favorite) {
        clearSelectedDetails();
      }
      renderM4Vault();
    }
    resetVaultPagePosition(true);
    requestVaultPage();
    showFixedToast(
      item.favorite ? '已收藏' : '已取消收藏',
      item.favorite ? 'Added to favorites' : 'Removed from favorites',
      'success',
    );
    refreshControls();
  }

  function onRecordUpdated(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    errorArgumentIndex,
    retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingEditSave ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch ||
      !activeEditModal()
    ) {
      scrubRecordWriteResult(result);
      settleSubmittedEditLease(false);
      return;
    }
    runtime.pendingEditSave = '';
    settleSubmittedEditLease(true);
    if (errorCode !== 'OK') {
      scrubRecordWriteResult(result);
      handleEditWriteFailure(
        errorCode,
        errorArgumentIndex,
        retryAfterMs,
      );
      refreshControls();
      return;
    }
    const item = normalizeRecordWriteItem(result && result.item);
    if (
      !item ||
      item.recordId !== runtime.editRecordId ||
      !isRevision(result.vaultRevision) ||
      !isRevision(result.healthRevision)
    ) {
      scrubRecordWriteResult(result);
      showCreateFormError(errorText('INTERNAL_FAILURE'));
      updateEditRecoveryUi();
      refreshControls();
      return;
    }
    const healthEdit = runtime.healthEditRecordId === item.recordId;
    const guideTarget = runtime.healthGuideEditTarget;
    const focusKeys = vaultRecordFocusKeys(item.recordId);
    const restoreVaultFocus = state.currentNav === 'vault' && !healthEdit && !guideTarget;
    scrubEditForm('save_complete');
    runtime.healthEditRecordId = 0;
    closeDemoModal();
    clearSelectedDetailContent();
    runtime.selectedRecordId = item.recordId;
    runtime.selectedRevision = item.revision;
    runtime.selectedDetails = null;
    runtime.vaultRevision = result.vaultRevision;
    showI18nToast('toast.pwd.updated', 'success');
    renderM4Vault(restoreVaultFocus ? focusKeys : null);
    if (
      guideTarget && runtime.healthGuide &&
      guideTarget.guidanceId === runtime.healthGuide.guidanceId &&
      guideTarget.recordId === item.recordId &&
      runtime.healthGuide.states[guideTarget.globalIndex] === 0 &&
      runtime.healthGuide.items[guideTarget.globalIndex - runtime.healthGuide.pageIndex * 100]?.issueId === guideTarget.issueId
    ) {
      runtime.healthGuide.states[guideTarget.globalIndex] = 1;
      runtime.healthGuideEditTarget = null;
      const localIndex = guideTarget.globalIndex - runtime.healthGuide.pageIndex * 100;
      runtime.healthGuide.itemIndex = localIndex + 1;
      if (runtime.healthGuide.states.every((value) => value !== 0)) {
        finishHealthGuidance();
      } else {
        showHealthGuidanceProgress();
      }
      refreshControls();
      return;
    }
    if (healthEdit) {
      requestHealthOverview(runtime.healthSingleOrigin);
      refreshControls();
      return;
    }
    resetVaultPagePosition(true);
    requestVaultPage();
    refreshControls();
  }

  function generatorPolicy() {
    const lengthInput = byId('gen-length-num');
    const raw = String(lengthInput?.value || '');
    const parsed = /^[0-9]+$/.test(raw) ? Number(raw) : Number.NaN;
    return {
      length: parsed,
      useLower: Boolean(state.genCharset.lower),
      useUpper: Boolean(state.genCharset.upper),
      useDigits: Boolean(state.genCharset.digit),
      useSymbols: Boolean(state.genCharset.symbol),
      avoidAmbiguous: Boolean(state.genAvoidAmbiguous),
    };
  }

  function generatorPolicyError(policy) {
    if (
      !Number.isSafeInteger(policy.length) ||
      policy.length < 1 ||
      policy.length > 1024
    ) {
      return 'tool.gen.error.length';
    }
    const selected = [
      policy.useLower,
      policy.useUpper,
      policy.useDigits,
      policy.useSymbols,
    ].filter(Boolean).length;
    if (!selected) return 'tool.gen.error.needCharset';
    return policy.length < selected ? 'tool.gen.error.tooShort' : '';
  }

  function showGeneratorConfigError(key) {
    const target = byId('gen-config-error');
    if (!target) return;
    target.hidden = !key;
    target.textContent = key ? t(key) : '';
    if (key) target.dataset.pdmGeneratorError = key;
    else delete target.dataset.pdmGeneratorError;
  }

  function syncGeneratorLength(value) {
    let parsed = Number.parseInt(value, 10);
    if (!Number.isSafeInteger(parsed)) parsed = 20;
    parsed = Math.min(1024, Math.max(1, parsed));
    const slider = byId('gen-length');
    const number = byId('gen-length-num');
    const label = byId('gen-length-val');
    if (slider) slider.value = String(Math.min(128, parsed));
    if (number) number.value = String(parsed);
    if (label) label.textContent = String(parsed);
  }

  function persistGeneratorDraft(generateAfterSave = false) {
    const policy = generatorPolicy();
    const error = generatorPolicyError(policy);
    showGeneratorConfigError(error);
    if (error) return false;
    runtime.generatorLastValidLength = policy.length;
    runtime.generatorDraftDirty = true;
    if (generateAfterSave) {
      runtime.generatorGenerateAfterSaveKey = generatorPolicyKey(policy);
    }
    if (runtime.state === 'UNLOCKED') {
      submitGeneratorDefaults(policy);
    } else if (generateAfterSave) {
      runtime.generatorGenerateAfterSaveKey = '';
      requestGeneratedPassword('tool');
    }
    refreshControls();
    return true;
  }

  function changeGeneratorLength(value) {
    runtime.generatorGenerateAfterSaveKey = '';
    const raw = String(value);
    const parsed = /^[0-9]+$/.test(raw) ? Number(raw) : Number.NaN;
    if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 1024) {
      showGeneratorConfigError('tool.gen.error.length');
      return;
    }
    syncGeneratorLength(parsed);
    persistGeneratorDraft();
  }

  function clampGeneratorLength() {
    const policy = generatorPolicy();
    if (!generatorPolicyError(policy) || (
      Number.isSafeInteger(policy.length) &&
      policy.length >= 1 &&
      policy.length <= 1024
    )) {
      return;
    }
    syncGeneratorLength(runtime.generatorLastValidLength);
    showGeneratorConfigError('tool.gen.error.length');
  }

  function toggleGeneratorCharset(item) {
    runtime.generatorGenerateAfterSaveKey = '';
    const key = String(item?.dataset?.charset || '');
    if (!['lower', 'upper', 'digit', 'symbol'].includes(key)) return;
    state.genCharset[key] = !state.genCharset[key];
    item.classList.toggle('checked', state.genCharset[key]);
    const mark = item.querySelector('.check-box');
    if (mark) mark.textContent = state.genCharset[key] ? '✓' : '';
    persistGeneratorDraft();
  }

  function toggleGeneratorAvoid(checked) {
    runtime.generatorGenerateAfterSaveKey = '';
    state.genAvoidAmbiguous = Boolean(checked);
    const item = byId('gen-avoid-item');
    item?.classList.toggle('checked', state.genAvoidAmbiguous);
    const mark = item?.querySelector('.check-box');
    if (mark) mark.textContent = state.genAvoidAmbiguous ? '✓' : '';
    persistGeneratorDraft();
  }

  function resetGeneratorPolicy() {
    syncGeneratorLength(20);
    for (const key of ['lower', 'upper', 'digit', 'symbol']) {
      state.genCharset[key] = true;
      const item = document.querySelector(
        `.check-item[data-charset="${key}"]`,
      );
      if (!item) continue;
      item.classList.add('checked');
      const mark = item.querySelector('.check-box');
      if (mark) mark.textContent = '✓';
    }
    state.genAvoidAmbiguous = false;
    const avoid = byId('gen-avoid');
    if (avoid instanceof HTMLInputElement) avoid.checked = false;
    const avoidItem = byId('gen-avoid-item');
    avoidItem?.classList.remove('checked');
    const avoidMark = avoidItem?.querySelector('.check-box');
    if (avoidMark) avoidMark.textContent = '';
    persistGeneratorDraft(true);
  }

  function failGeneratorDefaults(errorCode) {
    clearPendingGeneratorDefaults();
    runtime.queuedGeneratorPolicy = null;
    runtime.generatorGenerateAfterSaveKey = '';
    runtime.generatorDraftDirty = false;
    if (runtime.generatorCommittedPolicy) {
      projectGeneratorPolicy(runtime.generatorCommittedPolicy);
    }
    showSettingsFailure(errorCode);
    refreshControls();
  }

  function submitGeneratorDefaults(policy) {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.ready ||
      !runtime.bridge ||
      generatorPolicyError(policy)
    ) {
      return;
    }
    if (runtime.pendingGeneratorDefaults) {
      runtime.queuedGeneratorPolicy = (
        generatorPolicyKey(policy) === generatorPolicyKey(runtime.pendingGeneratorPolicy)
          ? null
          : Object.freeze({...policy})
      );
      return;
    }
    if (
      runtime.generatorCommittedPolicy &&
      generatorPolicyKey(policy) === generatorPolicyKey(runtime.generatorCommittedPolicy)
    ) {
      runtime.generatorDraftDirty = false;
      if (runtime.generatorGenerateAfterSaveKey === generatorPolicyKey(policy)) {
        runtime.generatorGenerateAfterSaveKey = '';
        requestGeneratedPassword('tool');
      }
      return;
    }
    const id = requestId();
    runtime.pendingGeneratorDefaults = id;
    runtime.pendingGeneratorPolicy = Object.freeze({...policy});
    runtime.bridge.setPasswordGeneratorDefaultsV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      policy.length,
      policy.useLower,
      policy.useUpper,
      policy.useDigits,
      policy.useSymbols,
      policy.avoidAmbiguous,
      (ack) => {
        if (
          runtime.pendingGeneratorDefaults === id &&
          (!ack || ack.accepted !== true || ack.errorCode !== 'OK')
        ) {
          failGeneratorDefaults(ack && ack.errorCode);
        }
      },
    );
  }

  function switchProductView(view) {
    const allowedWhileLocked = (
      runtime.state === 'LOCKED' &&
      ['vault', 'tools', 'settings', 'help'].includes(view)
    );
    if (
      (runtime.state !== 'UNLOCKED' && !allowedWhileLocked) ||
      !['vault', 'notes', 'security', 'tools', 'settings', 'help'].includes(view)
    ) {
      return;
    }
    if (runtime.pendingHealthGuidance) cancelHealthGuidanceRequest();
    if (runtime.pendingHealthOverview) cancelPendingHealthOverview();
    if (state.currentNav === view) {
      if (view === 'security') syncHealthRescanPolling(true);
      refreshControls();
      return;
    }
    closeAllSortDropdowns();
    if (state.currentNav === 'notes' && view !== 'notes' && noteDraftDirty()) {
      showUnsavedNoteWarning();
      return;
    }
    if (runtime.recordTextModal) closeProductModal();
    if (state.currentNav === 'vault' && view !== 'vault') {
      cancelHealthLocate();
      clearSelectedDetails();
      renderM4Vault();
    }
    if (runtime.pendingEditOpen) {
      cancelPendingEditOpen();
    }
    if (activeEditModal()) {
      closeEditRecordDialog('navigation');
    }
    if (activeCreateModal()) {
      closeCreateRecordDialog('navigation');
    }
    if (activeNoteCreateModal()) {
      closeCreateNoteDialog();
    }
    if (activeNoteDeleteModal()) {
      closeDeleteNoteDialog(true);
    }
    if (activeChangeKeyModal()) {
      closeChangeKeyDialog('navigation');
    }
    if (state.currentNav === 'notes' && view !== 'notes') {
      clearSelectedNoteDetails();
      renderM4Notes();
    }
    navigateDemoView(view);
    syncHealthRescanPolling(view === 'security');
    setProductTopbarTitle();
    if (view === 'settings') {
      setProductCurrentDatabaseInfo();
    }
    setProductGlobalSearchValue(
      view === 'vault'
        ? runtime.vaultQuery
        : view === 'notes'
          ? runtime.noteQuery
          : '',
    );
    if (view === 'notes') {
      renderM4Notes();
      requestNotePage();
    } else if (view === 'vault') {
      renderM4Vault();
      if (runtime.healthRescanVaultDirty || runtime.ratingVaultDirty) {
        runtime.ratingVaultDirty = false;
        requestVaultPage();
      }
    } else if (view === 'security') {
      renderM4Health();
      requestHealth();
    }
    refreshControls();
  }

  function switchProductTool(tool) {
    if (!['gen', 'check'].includes(tool)) return;
    switchDemoTool(tool);
    if (tool === 'check' && runtime.strengthReport) {
      renderStrengthReport(runtime.strengthReport);
    } else if (tool === 'check' && runtime.pendingStrength) {
      clearStrengthSurface(false, true);
    }
    refreshControls();
  }

  function requestGeneratedPassword(target = 'tool') {
    if (
      !runtime.bridge ||
      !runtime.ready ||
      runtime.pageEpoch <= 0 ||
      runtime.pendingGenerate ||
      (
        (target === 'modal' || target === 'change-key') &&
        (
          runtime.state !== 'UNLOCKED' ||
          !(
            target === 'change-key'
              ? activeChangeKeyModal()
              : (activeCreateModal() || activeEditModal())
          )
        )
      )
    ) {
      return;
    }
    const policy = generatorPolicy();
    const policyError = generatorPolicyError(policy);
    showGeneratorConfigError(policyError);
    if (policyError) {
      showI18nToast(policyError, 'error');
      return;
    }
    const id = requestId();
    runtime.pendingGenerate = id;
    runtime.generateTarget = target;
    refreshControls();
    runtime.bridge.generatePasswordV1(
      id,
      runtime.pageEpoch,
      policy.length,
      policy.useLower,
      policy.useUpper,
      policy.useDigits,
      policy.useSymbols,
      policy.avoidAmbiguous,
      (ack) => {
        if (
          !ack ||
          ack.accepted !== true ||
          ack.errorCode !== 'OK'
        ) {
          if (runtime.pendingGenerate === id) {
            runtime.pendingGenerate = '';
            runtime.generateTarget = '';
            const message = errorText(ack && ack.errorCode);
            if (target === 'change-key') {
              showChangeKeyFormError(message);
            } else if (target === 'modal') showCreateFormError(message);
            else showErrorToast(ack && ack.errorCode);
            refreshControls();
          }
        }
      },
    );
  }

  function cancelPendingGeneratedPassword(target) {
    const pending = runtime.pendingGenerate;
    if (!pending || runtime.generateTarget !== target) return;
    runtime.pendingGenerate = '';
    runtime.generateTarget = '';
    if (runtime.bridge && runtime.pageEpoch > 0) {
      runtime.bridge.cancelRequestV1(requestId(), runtime.pageEpoch, pending, () => {});
    }
    refreshControls();
  }

  function bindGeneratedPassword(lease, target) {
    const slot = target === 'tool' ? 'tool' : 'form';
    const [leaseField, elementField] = generatedSlot(slot);
    let element = null;
    if (target === 'change-key') {
      element = byId('kf-new');
    } else if (target === 'modal') {
      element = byId('mf-password');
    } else {
      element = byId('gen-output');
    }
    if (
      !element ||
      (
        (target === 'modal' || target === 'change-key') &&
        !(
          target === 'change-key'
            ? activeChangeKeyModal()
            : (activeCreateModal() || activeEditModal())
        )
      ) ||
      !window.pdmSensitiveDom
    ) {
      return false;
    }
    const inputType = element instanceof HTMLInputElement ? element.type : '';
    if (target === 'modal' && activeEditModal()) {
      cancelFieldReads('editor');
      const original = runtime.editorFieldMeta?.fields.PASSWORD;
      if (original) original.touched = true;
      if (runtime.editLeaseId) {
        detachEditorDomLease(
          runtime.editLeaseId,
          'lease_consumed',
          false,
        );
      }
      runtime.editPasswordDirty = true;
    }
    releaseGeneratedLease(slot, 'lease_released');
    if (
      element instanceof HTMLInputElement ||
      element instanceof HTMLTextAreaElement
    ) {
      element.value = lease.password;
      if (element instanceof HTMLInputElement) element.type = inputType || 'password';
    } else {
      element.textContent = lease.password;
    }
    element.dataset.pdmSensitive = 'true';
    try {
      window.pdmSensitiveDom.bindLease(
        lease.secretLeaseId,
        'GENERATED',
        lease.expiresInMs,
        [element],
      );
    } catch (_error) {
      if (
        element instanceof HTMLInputElement ||
        element instanceof HTMLTextAreaElement
      ) {
        element.value = '';
      } else {
        element.textContent = '';
      }
      return false;
    }
    runtime[leaseField] = lease.secretLeaseId;
    runtime[elementField] = element;
    if (target === 'modal' || target === 'change-key') {
      const wrap = element.closest('.password-field-wrap');
      const eye = wrap?.querySelector('.pw-action-btn');
      if (eye) eye.innerHTML = svgIcon(element.type === 'text' ? 'eye-closed' : 'eye', 16);
      showI18nToast('toast.gen.generatedNew', 'success');
    } else {
      showI18nToast('toast.gen.generated', 'success');
    }
    return true;
  }

  function moveGeneratedPasswordToCreate() {
    const output = byId('gen-output');
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.toolGeneratedLeaseId ||
      !output ||
      !output.textContent
    ) {
      showI18nToast('toast.gen.needGenFirst', 'error');
      return;
    }
    openCreateRecordDialog(runtime.toolGeneratedLeaseId);
  }

  function copyGeneratedPassword() {
    const output = byId('gen-output');
    if (
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pendingGeneratedCopy ||
      !runtime.toolGeneratedLeaseId ||
      !output?.textContent
    ) {
      if (!runtime.toolGeneratedLeaseId || !output?.textContent) {
        showI18nToast('toast.gen.needGenFirst', 'error');
      }
      return;
    }
    const id = requestId();
    runtime.pendingGeneratedCopy = id;
    refreshControls();
    runtime.bridge.copyGeneratedPasswordV1(
      id,
      runtime.pageEpoch,
      runtime.toolGeneratedLeaseId,
      (ack) => {
        if (
          runtime.pendingGeneratedCopy === id &&
          (!ack || ack.accepted !== true || ack.errorCode !== 'OK')
        ) {
          runtime.pendingGeneratedCopy = '';
          if (ack?.errorCode === 'SECRET_LEASE_EXPIRED') {
            releaseGeneratedLease('tool', 'lease_expired');
            showGeneratedPasswordExpired();
          } else {
            showErrorToast(ack && ack.errorCode);
          }
          refreshControls();
        }
      },
    );
  }

  function onGeneratedPasswordCopied(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingGeneratedCopy ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== 0
    ) {
      return;
    }
    runtime.pendingGeneratedCopy = '';
    if (errorCode !== 'OK') {
      if (errorCode === 'SECRET_LEASE_EXPIRED') {
        releaseGeneratedLease('tool', 'lease_expired');
        showGeneratedPasswordExpired();
      } else {
        showErrorToast(errorCode);
      }
      refreshControls();
      return;
    }
    const clipboard = normalizeClipboardResult(result);
    if (
      !clipboard ||
      !clipboard.owned ||
      clipboard.contentKind !== 'PASSWORD'
    ) {
      showErrorToast('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.clipboardKind = clipboard.contentKind;
    runtime.clipboardMode = clipboard.mode;
    runtime.clipboardRemaining = clipboard.remainingSeconds;
    runtime.clipboardOwned = clipboard.owned;
    renderClipboardState();
    showCompositeI18nToast(
      'vault.detail.password',
      '',
      'toast.copied.suffix',
      'success',
    );
    refreshControls();
  }

  function showGeneratedPasswordExpired() {
    showFixedToast(
      '生成的密码已过期，请重新生成。',
      'The generated password expired. Generate a new one.',
      'warning',
    );
  }

  const STRENGTH_FEEDBACK_CODES = new Set([
    'EMPTY', 'TOO_SHORT', 'ADD_WORDS', 'AVOID_REPEATS',
    'AVOID_SEQUENCES', 'AVOID_RECENT_YEARS', 'AVOID_DATES',
    'AVOID_COMMON_PASSWORD', 'AVOID_COMMON_WORD', 'AVOID_NAMES',
    'AVOID_USER_DATA', 'AVOID_KEYBOARD_PATTERN', 'AVOID_LEET_PATTERN',
    'DICTIONARY_MATCH',
  ]);
  const CRACK_TIME_BUCKETS = new Set([
    'INSTANT', 'SECONDS', 'MINUTES', 'HOURS',
    'DAYS', 'MONTHS', 'YEARS', 'CENTURIES',
  ]);

  function normalizeStrengthReport(result) {
    if (
      !hasExactKeys(result, [
        'crackTimes', 'downgraded', 'feedbackCodes', 'guesses',
        'level', 'score',
      ]) ||
      !['WEAK', 'FAIR', 'STRONG'].includes(result.level) ||
      !Number.isSafeInteger(result.score) ||
      result.score < 0 ||
      result.score > 4 ||
      !Array.isArray(result.feedbackCodes) ||
      result.feedbackCodes.length > 16 ||
      result.feedbackCodes.some((code) => !STRENGTH_FEEDBACK_CODES.has(code)) ||
      typeof result.guesses !== 'string' ||
      result.guesses.length < 1 ||
      result.guesses.length > 1025 ||
      !/^(?:0|[1-9][0-9]*)$/.test(result.guesses) ||
      typeof result.downgraded !== 'boolean' ||
      !hasExactKeys(result.crackTimes, [
        'offlineFast', 'offlineSlow', 'onlineThrottled', 'onlineUnthrottled',
      ]) ||
      Object.values(result.crackTimes).some(
        (bucket) => !CRACK_TIME_BUCKETS.has(bucket),
      )
    ) {
      return null;
    }
    return result;
  }

  function clearStrengthSurface(clearInputs = false, detecting = false) {
    runtime.strengthReport = null;
    if (clearInputs) {
      for (const id of ['check-input', 'check-platform', 'check-account']) {
        const input = byId(id);
        if (input instanceof HTMLInputElement) input.value = '';
      }
      const password = byId('check-input');
      if (password instanceof HTMLInputElement) {
        setStaticPasswordVisibility('check-input', 'check-eye', false);
      }
    }
    const fill = byId('strength-fill');
    const rating = byId('strength-rating');
    const suggestions = byId('suggestions');
    if (fill) {
      fill.style.width = '0';
      fill.style.background = '';
    }
    if (rating) {
      rating.textContent = detecting ? t('tool.check.detecting') : '—';
      rating.className = 'strength-rating';
      rating.style.color = '';
    }
    if (suggestions) suggestions.replaceChildren();
    byId('tool-check')?.setAttribute('aria-busy', detecting ? 'true' : 'false');
  }

  function cancelPendingStrength() {
    if (!runtime.pendingStrength || !runtime.bridge || runtime.pageEpoch <= 0) return;
    runtime.bridge.cancelRequestV1(
      requestId(),
      runtime.pageEpoch,
      runtime.pendingStrength,
      () => {},
    );
  }

  function strengthInputFits(value, chars, bytes) {
    return (
      typeof value === 'string' &&
      !value.includes('\0') &&
      Array.from(value).length <= chars &&
      new TextEncoder().encode(value).length <= bytes
    );
  }

  function currentStrengthInputValid() {
    const password = byId('check-input')?.value || '';
    const platform = byId('check-platform')?.value || '';
    const account = byId('check-account')?.value || '';
    return (
      strengthInputFits(password, 1024, 4096) &&
      strengthInputFits(platform.trim(), 128, 512) &&
      strengthInputFits(account, 512, 2048)
    );
  }

  function requestStrengthCheck(allowHidden = false) {
    if (
      !runtime.ready ||
      !runtime.bridge ||
      runtime.pageEpoch <= 0 ||
      runtime.pendingStrength ||
      runtime.retiredStrengthRequest ||
      (
        !allowHidden &&
        (
          state.currentNav !== 'tools' ||
          !byId('tool-check')?.classList.contains('active')
        )
      )
    ) {
      return;
    }
    let password = byId('check-input')?.value || '';
    let platform = (byId('check-platform')?.value || '').trim();
    let account = byId('check-account')?.value || '';
    if (!password || !currentStrengthInputValid()) return;
    const id = requestId();
    runtime.pendingStrength = id;
    runtime.pendingStrengthVersion = runtime.strengthInputVersion;
    clearStrengthSurface(false, true);
    refreshControls();
    try {
      runtime.bridge.checkPasswordStrengthV1(
        id,
        runtime.pageEpoch,
        password,
        platform,
        account,
        (ack) => {
          if (
            runtime.pendingStrength === id &&
            (!ack || ack.accepted !== true || ack.errorCode !== 'OK')
          ) {
            runtime.pendingStrength = '';
            clearStrengthSurface();
            showErrorToast(ack && ack.errorCode);
            if (runtime.pendingStrengthVersion !== runtime.strengthInputVersion) {
              requestStrengthCheck(true);
            }
            refreshControls();
          }
        },
      );
    } finally {
      password = '';
      platform = '';
      account = '';
    }
  }

  function onStrengthInputChanged() {
    runtime.strengthInputVersion += 1;
    clearStrengthSurface(false, true);
    if (!byId('check-input')?.value) {
      cancelPendingStrength();
      clearStrengthSurface(true);
      return;
    }
    if (!currentStrengthInputValid()) {
      cancelPendingStrength();
      clearStrengthSurface();
      const suggestions = byId('suggestions');
      if (suggestions) suggestions.textContent = t('tool.check.error.limit');
      return;
    }
    if (runtime.pendingStrength) {
      cancelPendingStrength();
      return;
    }
    requestStrengthCheck();
  }

  function renderStrengthReport(report) {
    clearStrengthSurface();
    runtime.strengthReport = report;
    const fill = byId('strength-fill');
    const rating = byId('strength-rating');
    const suggestions = byId('suggestions');
    const level = report.level.toLowerCase();
    if (fill) {
      fill.style.width = `${strengthBarPercent(report.guesses)}%`;
      fill.style.background = `var(--strength-${level})`;
    }
    if (rating) {
      rating.textContent = t(`tool.check.level.${level}`);
      rating.className = 'strength-rating';
      rating.style.color = `var(--strength-${level})`;
    }
    if (!suggestions) return;
    const crackTitle = document.createElement('div');
    crackTitle.className = 'strength-section-title';
    crackTitle.textContent = t('tool.check.crackTime.title');
    suggestions.append(crackTitle);
    for (const [field, labelKey] of [
      ['onlineThrottled', 'tool.check.crackTime.online_throttling'],
      ['onlineUnthrottled', 'tool.check.crackTime.online_no_throttling'],
      ['offlineSlow', 'tool.check.crackTime.offline_slow'],
      ['offlineFast', 'tool.check.crackTime.offline_fast'],
    ]) {
      const row = document.createElement('div');
      row.className = 'suggestion crack-time-row';
      const label = document.createElement('span');
      label.className = 'crack-time-label';
      label.textContent = t(labelKey);
      const value = document.createElement('span');
      value.className = 'crack-time-val';
      value.textContent = t(`tool.check.bucket.${report.crackTimes[field]}`);
      row.append(label, value);
      suggestions.append(row);
    }
    if (report.feedbackCodes.length) {
      const feedbackTitle = document.createElement('div');
      feedbackTitle.className = 'suggestion-sugg-divider';
      feedbackTitle.textContent = t('tool.check.suggestions.title');
      suggestions.append(feedbackTitle);
      for (const code of report.feedbackCodes) {
        const row = document.createElement('div');
        row.className = 'suggestion';
        row.textContent = t(`tool.check.feedback.${code}`);
        suggestions.append(row);
      }
    }
  }

  function onPasswordStrengthChecked(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request === runtime.retiredStrengthRequest &&
      pageEpoch === runtime.pageEpoch
    ) {
      runtime.retiredStrengthRequest = '';
      if (byId('check-input')?.value) requestStrengthCheck(true);
      refreshControls();
      return;
    }
    if (request !== runtime.pendingStrength || pageEpoch !== runtime.pageEpoch) return;
    const requestedVersion = runtime.pendingStrengthVersion;
    runtime.pendingStrength = '';
    if (
      requestedVersion !== runtime.strengthInputVersion
    ) {
      if (byId('check-input')?.value) requestStrengthCheck(true);
      refreshControls();
      return;
    }
    if (errorCode !== 'OK') {
      clearStrengthSurface();
      showErrorToast(errorCode);
      refreshControls();
      return;
    }
    const report = normalizeStrengthReport(result);
    if (!report) {
      clearStrengthSurface();
      showErrorToast('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    renderStrengthReport(report);
    refreshControls();
  }

  function clearStrengthAuthority(discardPending = false) {
    runtime.strengthInputVersion += 1;
    cancelPendingStrength();
    if (discardPending) {
      runtime.retiredStrengthRequest = runtime.pendingStrength;
      runtime.pendingStrength = '';
      runtime.pendingStrengthVersion = 0;
    }
    clearStrengthSurface(true);
  }

  function scrubRecordWriteResult(result) {
    if (result && typeof result === 'object') result.item = null;
  }

  function onRecordCreated(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    errorArgumentIndex,
    retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingCreate ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch ||
      !activeCreateModal()
    ) {
      scrubRecordWriteResult(result);
      return;
    }
    runtime.pendingCreate = '';
    if (errorCode !== 'OK') {
      scrubRecordWriteResult(result);
      if (errorCode === 'PLATFORM_CONFLICT') {
        showCreateFieldError(
          'mf-platform',
          errorText('PLATFORM_CONFLICT'),
        );
        byId('mf-platform')?.focus({preventScroll: true});
      } else if (
        errorCode === 'INVALID_ARGUMENT' &&
        errorArgumentIndex === 9
      ) {
        showCreateFieldError(
          'mf-totp',
          '',
          'TOTP 密钥格式无效，请检查后重试。',
          'The TOTP secret is invalid. Check it and try again.',
        );
        byId('mf-totp')?.focus({preventScroll: true});
      } else if (
        errorCode === 'SESSION_REQUIRED' ||
        errorCode === 'STALE_SESSION' ||
        errorCode === 'STALE_PAGE'
      ) {
        closeCreateRecordDialog('session_invalidated');
        applyLocked('session_invalidated');
        return;
      } else {
        if (errorCode === 'DATABASE_IO_FAILED') {
          showCreateFormError(
            '',
            '',
            '',
            'dialog.pwd.error.save_failed',
          );
        } else {
          showCreateFormError(errorText(errorCode));
        }
      }
      beginCreateCooldown(retryAfterMs);
      return;
    }
    const item = normalizeRecordWriteItem(result && result.item);
    if (
      !item ||
      !isRevision(result.vaultRevision) ||
      !isRevision(result.healthRevision)
    ) {
      scrubRecordWriteResult(result);
      showCreateFormError(errorText('INTERNAL_FAILURE'));
      refreshControls();
      return;
    }
    runtime.selectedRecordId = item.recordId;
    runtime.selectedRevision = item.revision;
    runtime.vaultRevision = result.vaultRevision;
    scrubCreateForm('save_complete');
    closeDemoModal();
    showI18nToast('toast.pwd.added', 'success');
    resetVaultPagePosition();
    requestVaultPage();
    refreshControls();
  }

  function onPasswordGenerated(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingGenerate ||
      pageEpoch !== runtime.pageEpoch
    ) {
      const staleLease = normalizeGeneratedPasswordLease(result);
      if (staleLease) releaseNativeSecretLease(staleLease.secretLeaseId);
      if (result && typeof result === 'object') result.password = '';
      return;
    }
    const target = runtime.generateTarget;
    runtime.pendingGenerate = '';
    runtime.generateTarget = '';
    if (errorCode !== 'OK') {
      if (result && typeof result === 'object') result.password = '';
      const message = errorText(errorCode);
      if (target === 'change-key') {
        showChangeKeyFormError(message);
      } else if (target === 'modal') showCreateFormError(message);
      else showErrorToast(errorCode);
      refreshControls();
      return;
    }
    const lease = normalizeGeneratedPasswordLease(result);
    if (
      !lease ||
      (
        (target === 'modal' || target === 'change-key') &&
        runtime.state !== 'UNLOCKED'
      ) ||
      !bindGeneratedPassword(lease, target)
    ) {
      if (lease && runtime.bridge && runtime.pageEpoch > 0) {
        runtime.bridge.releaseSecretLeaseV1(
          requestId(),
          runtime.pageEpoch,
          lease.secretLeaseId,
          () => {},
        );
      }
      if (result && typeof result === 'object') result.password = '';
      if (target === 'change-key') {
        showChangeKeyFormError(errorText('INTERNAL_FAILURE'));
      } else if (target === 'modal') {
        showCreateFormError(errorText('INTERNAL_FAILURE'));
      } else {
        showErrorToast('INTERNAL_FAILURE');
      }
      refreshControls();
      return;
    }
    lease.password = '';
    if (result && typeof result === 'object') result.password = '';
    refreshControls();
  }

  function resetDemoAuthority() {
    if (activeBackupModal()) {
      closeBackupDialog('session_invalidated', true);
    }
    if (activeNoteCreateModal()) {
      closeCreateNoteDialog();
    }
    if (activeNoteDeleteModal()) {
      closeDeleteNoteDialog(true);
    }
    cancelPendingEditOpen();
    if (activeDeleteModal()) {
      closeDeleteRecordDialog('session_invalidated', true);
    } else {
      clearDeleteRecordState();
    }
    if (activeEditModal()) {
      scrubEditForm('session_invalidated');
      closeDemoModal();
    }
    if (activeCreateModal()) {
      closeCreateRecordDialog('session_invalidated');
    }
    runtime.pendingCreate = '';
    runtime.pendingGenerate = '';
    runtime.pendingGeneratedCopy = '';
    clearStrengthAuthority(true);
    runtime.generateTarget = '';
    releaseAllGeneratedLeases('session_invalidated');
    runtime.toolGeneratedLeaseId = '';
    runtime.toolGeneratedElement = null;
    runtime.formGeneratedLeaseId = '';
    runtime.formGeneratedElement = null;
    clearPendingGeneratorDefaults();
    runtime.queuedGeneratorPolicy = null;
    runtime.generatorGenerateAfterSaveKey = '';
    runtime.createModalActive = false;
    clearCreateCooldown();
    runtime.pendingEditSave = '';
    runtime.editSubmittedLeaseId = '';
    runtime.editModalActive = false;
    runtime.editRecordId = 0;
    runtime.editRevision = '';
    runtime.editLeaseId = '';
    runtime.editHasTotp = false;
    runtime.editTotpAction = 'KEEP';
    runtime.editPasswordDirty = false;
    runtime.editConflict = false;
    runtime.editReloadRevision = '';
    clearEditCooldown();
    clearIndependentEditorState();
    state.genPassword = '';
    const generatedOutput = byId('gen-output');
    if (generatedOutput) {
      generatedOutput.textContent = '';
      generatedOutput.removeAttribute('data-pdm-sensitive');
    }
    passwords.splice(0, passwords.length);
    notes.splice(0, notes.length);
    recents.splice(0, recents.length);
    clearVaultAuthority();
    clearHealthAuthority();
    clearNoteAuthority();
    state.connected = false;
    state.startupMinimized = false;
    state.currentNav = 'vault';
    state.expandedId = null;
    state.splitSelectedId = null;
    state.passwordVisible = {};
    state.autoLock.enabled = false;
    stopIdleCheck();
    if (state.clipboardTimer) {
      window.clearInterval(state.clipboardTimer);
      state.clipboardTimer = null;
    }
    resetClipboardState();
    const path = byId('db-path');
    const password = byId('db-password');
    runtime.targetLocked = false;
    runtime.pendingRecent = '';
    runtime.pendingRecentEntry = null;
    runtime.pendingRemove = '';
    runtime.pendingRemoveIndex = -1;
    runtime.pendingRemoveFocusKey = '';
    runtime.openAfterChoose = false;
    if (path) {
      path.value = '';
      path.readOnly = false;
      path.removeAttribute('aria-readonly');
    }
    if (password) {
      password.value = '';
      setStaticPasswordVisibility('db-password', 'startup-eye', false);
    }
    renderBoundedRecents([]);
  }

  function isTitlebarControl(element) {
    return element.matches('.titlebar-ctrl');
  }

  function setEnabled(element, enabled, softDisabled = false) {
    const disabled = !enabled;
    if (
      element instanceof HTMLButtonElement ||
      element instanceof HTMLInputElement ||
      element instanceof HTMLSelectElement ||
      element instanceof HTMLTextAreaElement
    ) {
      const nativeDisabled = disabled && !softDisabled;
      if (element.disabled !== nativeDisabled) {
        element.disabled = nativeDisabled;
      }
    }
    const stateValue = enabled ? 'false' : 'true';
    if (element.dataset.pdmM4Disabled !== stateValue) {
      element.dataset.pdmM4Disabled = stateValue;
    }
    if (element.getAttribute('aria-disabled') !== stateValue) {
      element.setAttribute('aria-disabled', stateValue);
    }
    if (element.classList?.contains?.('fix-all-btn')) {
      element.classList.toggle('disabled', disabled);
    }
    if (element.hasAttribute('tabindex')) {
      const tabIndex = (enabled || softDisabled) ? 0 : -1;
      if (element.tabIndex !== tabIndex) element.tabIndex = tabIndex;
    }
    if (!enabled && !softDisabled && document.activeElement === element) {
      element.blur();
    }
  }

  function syncProductGlobalSearch() {
    const input = byId('global-search');
    const clear = byId('global-search-clear');
    if (!input || !clear) return;
    clear.hidden = !input.value;
    clear.disabled = input.disabled;
    syncGlobalSearchValidation();
  }

  function setProductGlobalSearchValue(value) {
    const input = byId('global-search');
    if (input) input.value = String(value ?? '');
    syncProductGlobalSearch();
  }

  function handleProductGlobalSearchInput(value) {
    const search = byId('global-search');
    if (search && !search.disabled && state.currentNav === 'settings') {
      handleSearch(String(value ?? search.value));
      return;
    }
    if (!search || runtime.state !== 'UNLOCKED') {
      syncProductGlobalSearch();
      return;
    }
    const rawValue = String(value ?? search.value);
    const nextValue = globalSearchFits(rawValue) ? rawValue.trim() : rawValue;
    if (state.currentNav === 'notes') {
      if (noteDraftDirty()) {
        setProductGlobalSearchValue(runtime.noteQuery);
        showUnsavedNoteWarning();
        return;
      }
      runtime.noteQuery = nextValue;
      state.search = nextValue.toLocaleLowerCase();
      syncProductGlobalSearch();
      queueNoteReload();
    } else if (state.currentNav === 'vault') {
      runtime.vaultQuery = nextValue;
      state.search = nextValue.toLocaleLowerCase();
      syncProductGlobalSearch();
      queueVaultReload();
    } else {
      syncProductGlobalSearch();
    }
  }

  function clearProductGlobalSearch() {
    const input = byId('global-search');
    if (!input || input.disabled) return;
    const blockedByNoteDraft = state.currentNav === 'notes' && noteDraftDirty();
    setProductGlobalSearchValue('');
    handleProductGlobalSearchInput('');
    if (!blockedByNoteDraft) input.focus({preventScroll: true});
  }

  function showDatabasePathTail() {
    const path = byId('db-path');
    // 编辑时保留用户的光标和滚动位置，失焦后优先显示末尾库名。
    if (path && document.activeElement !== path) path.scrollLeft = path.scrollWidth;
  }

  function refreshControls() {
    const focusVisibility = window.pdmFocusVisibility;
    const focusedBeforeRefresh = (
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null
    );
    const focusDescriptor = focusVisibility?.capture() || null;
    const focusFallbacks = focusFallbackKeys(focusedBeforeRefresh);
    const locked = runtime.state === 'LOCKED';
    const unlocked = runtime.state === 'UNLOCKED';
    const editorOccupied = Boolean(runtime.editorInstanceId);
    const connectionBusy = Boolean(
      runtime.pendingChoose ||
      runtime.pendingRecent ||
      runtime.pendingOpen ||
      runtime.pendingRemove ||
      runtime.pendingLock ||
      runtime.pendingChangeKey
    );
    document.documentElement.classList.toggle(
      'pdm-connection-busy',
      connectionBusy,
    );
    const controls = document.querySelectorAll(
      'button,input,select,textarea,[data-pdm-onclick],[data-pdm-note-sort],'
      + '[data-pdm-m4-vault-action],[data-pdm-m4-note-action],'
      + '#quickbar-toggle',
    );
    for (const control of controls) {
      if (control.matches('[data-update-action],[data-update-days]')) continue;
      if (control.matches('#tray-close-segment button,#view-default-segment button,#clip-clear-segment button')) {
        control.disabled = false;
        control.tabIndex = -1;
        control.setAttribute('aria-hidden', 'true');
        delete control.dataset.pdmM4Disabled;
        control.removeAttribute('aria-disabled');
        continue;
      }
      if (control.matches('#lang-segment button')) {
        control.disabled = false;
        control.tabIndex = -1;
        control.setAttribute('aria-hidden', 'true');
        delete control.dataset.pdmM4Disabled;
        control.removeAttribute('aria-disabled');
        continue;
      }
      if (isTitlebarControl(control)) {
        setEnabled(control, true);
        control.tabIndex = -1;
        continue;
      }
      let enabled = false;
      if (control.dataset.pdmStrengthRetry === 'true') {
        const record = control.pdmStrengthRecord;
        enabled = unlocked && runtime.ready && !connectionBusy && !editorOccupied &&
          record?.strength === 'FAILED' && !runtime.pendingStrengthRetries.has(record.recordId);
      } else if (unlocked && runtime.recordTextModal && control.closest('#active-modal')) {
        enabled = true;
      } else if (
        unlocked &&
        control.closest('[data-pdm-m4-health-guide-complete="true"]')
      ) {
        enabled = true;
      } else if (
        unlocked &&
        runtime.healthGuide &&
        (
          control.closest('[data-pdm-m4-health-guide="true"]') ||
          control.closest('[data-pdm-m4-health-guide-progress="true"]')
        )
      ) {
        const current = currentHealthGuideEntry();
        enabled = !connectionBusy && !runtime.pendingHealthGuidance;
        if (control.id === 'health-guide-prev') {
          enabled = enabled && Boolean(current && current.globalIndex > 0);
        } else if (control.id === 'health-guide-edit') {
          enabled = enabled && Boolean(
            current && current.item.available &&
            current.guide.states[current.globalIndex] === 0
          );
        }
      } else if (
        unlocked &&
        runtime.healthGuide &&
        control.closest('#fix-banner')
      ) {
        enabled = !connectionBusy && !runtime.pendingHealthGuidance;
      } else if (
        unlocked && state.currentNav === 'security' &&
        control.matches('#health-rescan-start,#health-rescan-cancel')
      ) {
        enabled = !connectionBusy && runtime.ready;
        if (control.id === 'health-rescan-start') {
          enabled = enabled && !runtime.pendingHealthRescan &&
            (!healthRescanActive() || Boolean(runtime.healthRescanError));
        } else {
          enabled = enabled && healthRescanActive() && !runtime.healthRescanCancelQueued &&
            runtime.pendingHealthRescan?.action !== 'CANCEL' && runtime.healthRescan?.state !== 'CANCELLING';
        }
      } else if (
        unlocked &&
        state.currentNav === 'security' &&
        control.matches('.fix-all-btn')
      ) {
        enabled = !connectionBusy && !runtime.pendingHealthGuidance &&
          !runtime.healthGuide && Boolean(
            runtime.healthSummary &&
            (
              runtime.healthSummary.weakCount ||
              runtime.healthSummary.duplicateGroupCount ||
              runtime.healthSummary.staleCount
            )
          );
      } else if (
        runtime.ready &&
        control.id === 'theme-btn'
      ) {
        enabled = true;
      } else if (
        runtime.ready &&
        control.classList.contains('clear-clip-btn')
      ) {
        enabled = runtime.clipboardOwned && !runtime.pendingClipboardClear;
      } else if (
        runtime.ready &&
        state.currentNav === 'settings' &&
        control.closest('#theme-segment')
      ) {
        enabled = true;
      } else if (
        runtime.ready &&
        state.currentNav === 'settings' &&
        control.closest('#ui-font-scale-segment')
      ) {
        enabled = true;
      } else if (
        runtime.ready &&
        state.currentNav === 'settings' &&
        control.id === 'lang-segment'
      ) {
        enabled = true;
      } else if (
        runtime.ready && state.currentNav === 'settings' &&
        control.id === 'sidebar-text-toggle'
      ) {
        enabled = !connectionBusy && !runtime.pendingSidebarText;
      } else if (
        runtime.ready && unlocked && state.currentNav === 'settings' &&
        control.id === 'autofill-toggle'
      ) {
        enabled = !connectionBusy && !runtime.pendingStartupAutofill;
      } else if (
        runtime.ready && unlocked && state.currentNav === 'settings' &&
        control.id === 'view-default-segment'
      ) {
        enabled = !connectionBusy && !runtime.pendingDefaultView;
      } else if (
        runtime.ready && unlocked && state.currentNav === 'settings' &&
        control.id === 'clip-clear-segment'
      ) {
        enabled = !connectionBusy && !runtime.pendingClipboardPolicy;
      } else if (
        runtime.ready && unlocked && state.currentNav === 'settings' &&
        (control.id === 'clip-slider' || control.id === 'clip-num')
      ) {
        enabled = !connectionBusy && !runtime.pendingClipboardPolicy && runtime.settings?.clipboardMode === 'COUNTDOWN';
      } else if (
        runtime.ready &&
        unlocked &&
        state.currentNav === 'settings' &&
        control.id === 'tray-close-segment'
      ) {
        enabled = !connectionBusy;
      } else if (
        runtime.ready &&
        unlocked &&
        control.id === 'topbar-quickbar-btn'
      ) {
        enabled = (
          !connectionBusy &&
          !runtime.pendingQuickbarOpen &&
          runtime.settings?.quickbarEnabled === true
        );
      } else if (
        runtime.ready &&
        unlocked &&
        state.currentNav === 'settings' &&
        control.id === 'quickbar-toggle'
      ) {
        enabled = (
          !connectionBusy &&
          !runtime.pendingQuickbarEnabled &&
          !runtime.pendingQuickbarHotkey
        );
      } else if (
        runtime.ready &&
        unlocked &&
        state.currentNav === 'settings' &&
        (
          control.id === 'quickbar-hotkey-btn' ||
          control.id === 'quickbar-timeout-slider' ||
          control.id === 'quickbar-timeout-num'
        )
      ) {
        enabled = (
          !connectionBusy &&
          !runtime.pendingQuickbarEnabled &&
          !runtime.pendingQuickbarHotkey
        );
      } else if (
        runtime.ready &&
        unlocked &&
        state.currentNav === 'settings' &&
        (control.id === 'stale-slider' || control.id === 'stale-num')
      ) {
        enabled = !connectionBusy && !runtime.pendingStaleThreshold;
      } else if (
        runtime.ready &&
        unlocked &&
        state.currentNav === 'settings' &&
        (
          control.id === 'autolock-toggle' ||
          control.id === 'autolock-slider' ||
          control.id === 'autolock-num'
        )
      ) {
        enabled = (
          !connectionBusy &&
          !runtime.pendingAutoLock &&
          (
            control.id === 'autolock-toggle' ||
            runtime.settings?.autoLockEnabled === true
          )
        );
      } else if ((unlocked || locked) && control.matches('#page-help button')) {
        enabled = runtime.ready && !connectionBusy;
      } else if (control.id === 'startup-minimized-bar') {
        enabled = runtime.ready && locked && state.startupMinimized && !connectionBusy;
      } else if (control.matches('[data-pdm-recent-action]')) {
        enabled = locked && !connectionBusy;
      } else if (
        locked &&
        (
          control.id === 'db-path' ||
          control.matches('.browse-btn')
        )
      ) {
        enabled = !connectionBusy;
      } else if (
        locked &&
        (
          control.id === 'db-password' ||
          control.matches('.eye-btn')
        )
      ) {
        enabled = !connectionBusy;
      } else if (locked && control.matches('.connect-btn')) {
        const path = byId('db-path');
        enabled = (
          !connectionBusy &&
          Boolean(path && path.value.trim())
        );
      } else if (
        (unlocked || locked) &&
        control.matches(
          locked
            ? '[data-pdm-onclick="navigateTo(\'vault\')"],'
              + '[data-pdm-onclick="navigateTo(\'tools\')"],'
              + '[data-pdm-onclick="navigateTo(\'settings\')"],'
              + '[data-pdm-onclick="navigateTo(\'help\')"]'
            : '[data-pdm-onclick="navigateTo(\'vault\')"],'
              + '[data-pdm-onclick="navigateTo(\'notes\')"],'
              + '[data-pdm-onclick="navigateTo(\'security\')"],'
              + '[data-pdm-onclick="navigateTo(\'tools\')"],'
              + '[data-pdm-onclick="navigateTo(\'settings\')"],'
              + '[data-pdm-onclick="navigateTo(\'help\')"]',
        )
      ) {
        enabled = !connectionBusy;
      } else if (
        (unlocked || locked) &&
        state.currentNav === 'tools' &&
        control.matches('.tool-tab')
      ) {
        enabled = !connectionBusy;
      } else if (
        (unlocked || locked) &&
        state.currentNav === 'tools' &&
        control.matches(
          '#gen-length,#gen-length-num,#gen-avoid,.check-item[data-charset],'
          + '[data-pdm-onclick="resetGenConfig()"]',
        )
      ) {
        enabled = !connectionBusy && !runtime.pendingGenerate;
      } else if (
        unlocked &&
        runtime.changeKeyModalActive &&
        control.closest('#active-modal')
      ) {
        enabled = !runtime.pendingChangeKey;
        if (control.id === 'kf-confirm-btn') {
          const next = byId('kf-new');
          const confirm = byId('kf-confirm');
          enabled = (
            !runtime.pendingChangeKey &&
            !(runtime.pendingGenerate && runtime.generateTarget === 'change-key') &&
            runtime.changeKeyCooldownUntil <= Date.now() &&
            next instanceof HTMLInputElement &&
            confirm instanceof HTMLInputElement &&
            next.value === confirm.value
          );
        } else if (
          control.matches(
            '[data-pdm-onclick="fillModalGeneratedPassword(\'kf-new\')"]',
          )
        ) {
          enabled = !runtime.pendingGenerate;
        }
      } else if (
        unlocked &&
        runtime.noteCreateModalActive &&
        control.closest('#active-modal')
      ) {
        enabled = true;
        if (control.id === 'nf-save') {
          enabled = (
            !runtime.pendingNoteCreate &&
            runtime.noteCreateCooldownUntil <= Date.now()
          );
        }
      } else if (
        unlocked &&
        activeNoteDeleteModal() &&
        control.closest('#active-modal')
      ) {
        enabled = !runtime.pendingNoteDeletePrepare && !runtime.pendingNoteDeleteCommit;
      } else if (
        unlocked &&
        runtime.deleteModalActive &&
        control.closest('#active-modal')
      ) {
        enabled = !(
          runtime.pendingDeletePrepare ||
          runtime.pendingDeleteCommit
        );
      } else if (
        unlocked &&
        runtime.createModalActive &&
        control.closest('#active-modal')
      ) {
        enabled = !runtime.pendingCreate;
        if (control.id === 'mf-save') {
          enabled = (
            !runtime.pendingCreate &&
            !(runtime.pendingGenerate && runtime.generateTarget === 'modal') &&
            runtime.createCooldownUntil <= Date.now()
          );
        } else if (
          control.matches(
            '[data-pdm-onclick="fillModalGeneratedPassword(\'mf-password\')"]',
          )
        ) {
          enabled = !runtime.pendingCreate && !runtime.pendingGenerate;
        }
      } else if (
        unlocked &&
        runtime.editModalActive &&
        control.closest('#active-modal')
      ) {
        enabled = !runtime.pendingEditSave;
        if (control.id === 'mf-save') {
          enabled = (
            !runtime.pendingEditSave &&
            !runtime.pendingEditOpen &&
            !(runtime.pendingGenerate && runtime.generateTarget === 'modal') &&
            Boolean(runtime.editLeaseId) &&
            !runtime.editConflict &&
            runtime.editCooldownUntil <= Date.now()
          );
        } else if (control.id === 'mf-edit-reload') {
          enabled = (
            !runtime.pendingEditSave &&
            !runtime.pendingEditOpen &&
            runtime.editConflict &&
            Boolean(runtime.editReloadRevision)
          );
        } else if (control.id === 'mf-edit-retry') {
          enabled = (
            !runtime.pendingEditSave &&
            !runtime.pendingEditOpen &&
            !runtime.editConflict &&
            !runtime.editLeaseId &&
            runtime.editCooldownUntil <= Date.now()
          );
        } else if (
          control.matches(
            '[data-pdm-onclick="fillModalGeneratedPassword(\'mf-password\')"]',
          )
        ) {
          enabled = (
            !runtime.pendingEditSave &&
            !runtime.pendingEditOpen &&
            !runtime.pendingGenerate &&
            !runtime.editConflict
          );
        }
      } else if (
        unlocked &&
        control.matches(
          '[data-pdm-onclick="openChangeDbPasswordDialog()"]',
        )
      ) {
        enabled = (
          state.currentNav === 'settings' &&
          !connectionBusy &&
          !runtime.changeKeyModalActive &&
          !editorOccupied
        );
      } else if (
        unlocked &&
        control.matches(
          '[data-pdm-onclick="openImportExportDialog(\'export\')"]',
        )
      ) {
        enabled = (
          state.currentNav === 'settings' &&
          !connectionBusy &&
          !runtime.backup
        );
      } else if (unlocked && control.matches('[data-pdm-onclick="openDirectTransferDialog()"]')) {
        enabled = state.currentNav === 'settings' && !connectionBusy && !editorOccupied && !runtime.backup;
      } else if (
        unlocked &&
        control.matches(
          '[data-pdm-onclick="openAddPasswordDialog()"]',
        )
      ) {
        enabled = (
          !connectionBusy &&
          !runtime.pendingCreate &&
          !runtime.pendingEditOpen &&
          !runtime.editModalActive &&
          !runtime.deleteModalActive &&
          !editorOccupied
        );
      } else if (
        unlocked &&
        control.matches(
          '[data-pdm-onclick="openAddNoteDialog()"]',
        )
      ) {
        enabled = (
          state.currentNav === 'notes' &&
          !connectionBusy &&
          !runtime.pendingNoteCreate &&
          !runtime.noteCreateModalActive &&
          !editorOccupied
        );
      } else if (
        (unlocked || locked) &&
        (
          control.matches('[data-pdm-onclick="generatePassword()"]') ||
          control.matches('[data-pdm-onclick="copyGenerated()"]')
        )
      ) {
        enabled = (
          !runtime.pendingGenerate &&
          (
            !control.matches('[data-pdm-onclick="copyGenerated()"]') ||
            (!runtime.pendingGeneratedCopy &&
            Boolean(runtime.toolGeneratedLeaseId)
            )
          )
        );
      } else if (
        unlocked &&
        control.matches('[data-pdm-onclick="saveGenerated()"]')
      ) {
        enabled = !runtime.pendingGenerate && Boolean(runtime.toolGeneratedLeaseId) && !editorOccupied;
      } else if (
        (unlocked || locked) &&
        state.currentNav === 'tools' &&
        control.matches('#tool-check input,.eye-btn')
      ) {
        enabled = !connectionBusy;
      } else if (
        unlocked &&
        control.matches('[data-pdm-onclick="lockApp()"]')
      ) {
        enabled = !connectionBusy;
      } else if (
        unlocked &&
        state.currentNav === 'security' &&
        control.dataset.pdmM4HealthAction === 'true'
      ) {
        enabled = !connectionBusy && !runtime.pendingEditOpen && !runtime.pendingEditSave &&
          !runtime.pendingHealthOverview && !runtime.pendingHealthSummary &&
          !runtime.pendingHealthIssues[control.dataset.pdmM4HealthKind];
        const page = healthPage(control.dataset.pdmM4HealthKind);
        if (control.dataset.pdmM4HealthPager === 'previous') enabled = enabled && page.pageIndex > 0;
        if (control.dataset.pdmM4HealthPager === 'next') enabled = enabled && Boolean(page.nextCursor);
      } else if (
        (locked || unlocked) && state.currentNav === 'settings' &&
        ['global-search', 'global-search-clear'].includes(control.id)
      ) {
        enabled = !connectionBusy;
      } else if (
        unlocked &&
        state.currentNav === 'notes' &&
        (
          control.matches('[data-note-card-action],[data-note-card-input],[data-pdm-note-pager],#note-sort-trigger,[data-pdm-note-sort]')
        )
      ) {
        const action = control.dataset.noteCardAction || '';
        enabled = !connectionBusy && !runtime.pendingNoteList && !runtime.pendingNoteCreate &&
          !runtime.noteCreateModalActive && !runtime.pendingNoteDetails;
        if (action === 'save') {
          enabled = enabled && noteDraftDirty() && !runtime.pendingNoteSave && !runtime.pendingNoteFavorite;
        } else if (action === 'favorite') {
          enabled = enabled && !runtime.pendingNoteSave && !runtime.pendingNoteFavorite && !runtime.pendingNoteFieldRead;
        } else if (action === 'cancel') {
          enabled = !runtime.pendingNoteSave && !runtime.pendingNoteFavorite;
        } else if (action === 'delete') {
          enabled = enabled && !noteDraftDirty() && !runtime.pendingNoteSave && !runtime.pendingNoteFavorite;
        } else if (control.dataset.noteCardInput) {
          enabled = enabled && !runtime.pendingNoteSave && !runtime.pendingNoteFavorite;
        } else if (control.id === 'note-sort-trigger' || control.dataset.pdmNoteSort || control.dataset.pdmNotePager) {
          enabled = enabled && !noteWritePending() && !noteDraftDirty();
          if (control.dataset.pdmNotePager === 'previous') enabled = enabled && runtime.noteCursorHistory.length > 0;
          if (control.dataset.pdmNotePager === 'next') enabled = enabled && (runtime.noteCursorHistory.length + 1) * 100 < runtime.noteTotal;
        }
      } else if (
        unlocked &&
        state.currentNav === 'notes' &&
        (
          control.id === 'global-search' ||
          control.id === 'global-search-clear' ||
          control.closest('#page-notes .filter-chips')
        )
      ) {
        enabled = (
          !connectionBusy &&
          !runtime.pendingNoteCreate &&
          !runtime.noteCreateModalActive
          && !noteWritePending()
        );
      } else if (
        unlocked &&
        state.currentNav === 'vault' &&
        (
          control.id === 'global-search' ||
          control.id === 'global-search-clear' ||
          control.closest('#filter-chips') ||
          control.closest('.view-switcher') ||
          control.id === 'sort-trigger' ||
          control.closest('#sort-menu') ||
          control.dataset.pdmM4VaultAction === 'true'
        )
      ) {
        enabled = (
          !connectionBusy &&
          !runtime.pendingHealthLocate &&
          !runtime.pendingHealthOverview &&
          !runtime.pendingEditOpen &&
          !runtime.pendingEditSave &&
          !runtime.deleteModalActive &&
          !runtime.pendingDeletePrepare &&
          !runtime.pendingDeleteCommit
        );
      }
      const autoLockControl = [
        'autolock-toggle',
        'autolock-slider',
        'autolock-num',
      ].includes(control.id);
      const quickbarPolicyControl = [
        'quickbar-toggle',
        'quickbar-timeout-slider',
        'quickbar-timeout-num',
      ].includes(control.id);
      if ((control.id === 'sort-trigger' || control.closest('#sort-menu')) && runtime.pendingSort) enabled = false;
      const pendingSortTrigger = (
        (control.id === 'sort-trigger' && runtime.pendingSort) ||
        (control.id === 'note-sort-trigger' && runtime.pendingNoteList)
      );
      const pendingGenerateTrigger = Boolean(
        runtime.pendingGenerate &&
        (
          (
            runtime.generateTarget === 'tool' &&
            control.matches('[data-pdm-onclick="generatePassword()"]')
          ) ||
          (
            runtime.generateTarget === 'modal' &&
            control.matches(
              '[data-pdm-onclick="fillModalGeneratedPassword(\'mf-password\')"]',
            )
          ) ||
          (
            runtime.generateTarget === 'change-key' &&
            control.matches(
              '[data-pdm-onclick="fillModalGeneratedPassword(\'kf-new\')"]',
            )
          )
        )
      );
      const softDisabled = Boolean(
        (!enabled &&
          runtime.pendingAutoLock &&
          autoLockControl &&
          (
            control.id === 'autolock-toggle' ||
            runtime.settings?.autoLockEnabled === true
          )) ||
        (
          !enabled &&
          runtime.pendingQuickbarEnabled &&
          quickbarPolicyControl
        ) ||
        (
          !enabled &&
          runtime.pendingChangeKey &&
          runtime.changeKeyModalActive &&
          control.closest('#active-modal')
        ) ||
        (
          !enabled &&
          control.dataset.pdmM4HealthPager &&
          Boolean(runtime.pendingHealthIssues[control.dataset.pdmM4HealthKind])
        ) ||
        (
          !enabled && pendingSortTrigger
        ) ||
        (
          !enabled && pendingGenerateTrigger
        ) || (
          !enabled && control.matches('[data-pdm-recent-action]') &&
          Boolean(runtime.pendingRemove)
        )
      );
      if (control.id === 'mf-save' && runtime.editorPreparing) enabled = false;
      if (control.matches('.fav-star') && (runtime.pendingFavorite || runtime.pendingList)) enabled = false;
      if (
        enabled && editorOccupied &&
        Number(control.dataset.pdmRecordId) === runtime.editorTarget?.recordId &&
        /(?:favorite|delete)$/.test(control.dataset.pdmFocusAction || '')
      ) enabled = false;
      if (
        enabled && editorOccupied && runtime.editorTarget?.kind === 'NOTE' &&
        Number(control.closest('.note-card')?.dataset.id) === runtime.editorTarget.recordId &&
        control.dataset.noteCardAction === 'favorite'
      ) enabled = false;
      if (control.dataset.pdmFieldBusy === 'true') enabled = false;
      setEnabled(control, enabled, softDisabled);
    }
    const themeBusy = runtime.pendingTheme ? 'true' : 'false';
    const languageBusy = runtime.pendingLanguage ? 'true' : 'false';
    const closeBusy = runtime.pendingClose ? 'true' : 'false';
    const autoLockBusy = runtime.pendingAutoLock ? 'true' : 'false';
    const quickbarBusy = (
      runtime.pendingQuickbarEnabled || runtime.pendingQuickbarHotkey
    ) ? 'true' : 'false';
    byId('theme-btn')?.setAttribute('aria-busy', themeBusy);
    document.querySelectorAll('#theme-segment button').forEach((button) => {
      button.setAttribute('aria-busy', themeBusy);
    });
    document.querySelectorAll('#ui-font-scale-segment button').forEach(
      (button) => {
        button.setAttribute(
          'aria-busy',
          runtime.pendingUiFontScale ? 'true' : 'false',
        );
      },
    );
    byId('lang-segment')?.setAttribute('aria-busy', languageBusy);
    byId('autofill-toggle')?.setAttribute('aria-busy', runtime.pendingStartupAutofill ? 'true' : 'false');
    byId('view-default-segment')?.setAttribute('aria-busy', runtime.pendingDefaultView ? 'true' : 'false');
    byId('sidebar-text-toggle')?.setAttribute('aria-busy', runtime.pendingSidebarText ? 'true' : 'false');
    byId('clip-clear-segment')?.setAttribute('aria-busy', runtime.pendingClipboardPolicy ? 'true' : 'false');
    byId('clip-slider')?.setAttribute('aria-busy', runtime.pendingClipboardPolicy ? 'true' : 'false');
    byId('clip-num')?.setAttribute('aria-busy', runtime.pendingClipboardPolicy ? 'true' : 'false');
    byId('tray-close-segment')?.setAttribute('aria-busy', closeBusy);
    byId('autolock-toggle')?.setAttribute('aria-busy', autoLockBusy);
    byId('autolock-slider')?.setAttribute('aria-busy', autoLockBusy);
    byId('autolock-num')?.setAttribute('aria-busy', autoLockBusy);
    byId('quickbar-toggle')?.setAttribute('aria-busy', quickbarBusy);
    byId('quickbar-timeout-slider')?.setAttribute(
      'aria-busy',
      quickbarBusy,
    );
    byId('quickbar-timeout-num')?.setAttribute(
      'aria-busy',
      quickbarBusy,
    );
    byId('quickbar-hotkey-btn')?.setAttribute('aria-busy', quickbarBusy);
    byId('topbar-quickbar-btn')?.setAttribute(
      'aria-busy',
      runtime.pendingQuickbarOpen ? 'true' : 'false',
    );
    syncProductGlobalSearch();
    document.querySelector('.startup-card')?.setAttribute(
      'aria-busy',
      (runtime.pendingOpen || runtime.pendingRemove) ? 'true' : 'false',
    );
    if (focusVisibility) {
      if (
        focusedBeforeRefresh &&
        focusedBeforeRefresh !== document.body &&
        focusedBeforeRefresh.id !== 'main-app' &&
        hardFocusTargetUnavailable(focusedBeforeRefresh)
      ) {
        focusVisibility.restore(focusDescriptor, focusFallbacks);
      } else {
        focusVisibility.refresh();
      }
    }
    showDatabasePathTail();
    renderProductUpdates();
    syncRecentTimeRefresh();
  }

  function applyLocked(reason) {
    state.settingsSearch = '';
    window.pdmFocusVisibility?.clear();
    clearIndependentEditorState();
    const cleanupReason = (
      reason === 'manual_lock' ? 'manual_lock' : 'session_invalidated'
    );
    clearRuntimeToasts();
    closeAllSortDropdowns();
    closeQuickBar();
    if (activeBackupModal()) {
      closeBackupDialog(reason === 'manual_lock' ? 'manual_lock' : 'session_invalidated', true);
    }
    window.__pdmNativeFocusDescriptor = '';
    if (activeNoteCreateModal()) {
      closeCreateNoteDialog();
    }
    if (activeNoteDeleteModal()) {
      closeDeleteNoteDialog(true);
    }
    if (activeChangeKeyModal()) {
      closeChangeKeyDialog(cleanupReason, true);
    } else {
      runtime.pendingChangeKey = '';
      runtime.changeKeyModalActive = false;
      clearChangeKeyCooldown();
      resetChangeKeyProgress();
    }
    if (activeDeleteModal()) {
      closeDeleteRecordDialog(cleanupReason, true);
    } else {
      clearDeleteRecordState();
    }
    cancelPendingEditOpen();
    if (activeEditModal()) {
      scrubEditForm(cleanupReason);
      closeDemoModal();
    } else {
      runtime.pendingEditSave = '';
      runtime.editSubmittedLeaseId = '';
      runtime.editModalActive = false;
      runtime.editRecordId = 0;
      runtime.editRevision = '';
      runtime.editLeaseId = '';
      runtime.editConflict = false;
      runtime.editReloadRevision = '';
      clearEditCooldown();
    }
    if (activeCreateModal()) {
      closeCreateRecordDialog(
        cleanupReason,
      );
    }
    runtime.pendingCreate = '';
    runtime.pendingGenerate = '';
    runtime.pendingGeneratedCopy = '';
    clearStrengthAuthority(true);
    runtime.generateTarget = '';
    clearPendingClose();
    clearPendingAutoLock();
    clearPendingStartupAutofill();
    clearPendingDefaultView();
    clearPendingSidebarText();
    clearPendingClipboardPolicy();
    clearPendingGeneratorDefaults();
    runtime.queuedGeneratorPolicy = null;
    runtime.generatorGenerateAfterSaveKey = '';
    if (runtime.generatorCommittedPolicy) {
      runtime.generatorDraftDirty = false;
      projectGeneratorPolicy(runtime.generatorCommittedPolicy);
    }
    runtime.pendingQuickbarOpen = '';
    clearPendingQuickbarEnabled();
    clearPendingQuickbarHotkey();
    resetHotkeyRecordingVisual();
    releaseAllGeneratedLeases(
      reason === 'manual_lock' ? 'manual_lock' : 'session_invalidated',
    );
    clearCreateCooldown();
    runtime.state = 'LOCKED';
    runtime.sessionEpoch = 0;
    clearContactSupport();
    runtime.pendingOpen = '';
    runtime.pendingLock = '';
    runtime.pendingChoose = '';
    runtime.pendingRecent = '';
    runtime.pendingRecentEntry = null;
    runtime.pendingRemove = '';
    runtime.pendingRemoveIndex = -1;
    runtime.pendingRemoveFocusKey = '';
    runtime.openAfterChoose = false;
    runtime.selectionTicket = '';
    runtime.targetKind = 'NONE';
    runtime.targetLocked = false;
    clearVaultAuthority();
    clearHealthAuthority();
    clearNoteAuthority();
    clearLockedProductSurfaces();
    resetClipboardState();
    runtime.vaultQuery = '';
    runtime.vaultFilter = 'ALL';
    passwords.splice(0, passwords.length);
    notes.splice(0, notes.length);
    state.connected = false;
    state.startupMinimized = false;
    state.currentNav = 'vault';
    state.expandedId = null;
    state.splitSelectedId = null;
    state.passwordVisible = {};
    state.genPassword = '';
    const generatedOutput = byId('gen-output');
    if (generatedOutput) {
      generatedOutput.textContent = '';
      generatedOutput.removeAttribute('data-pdm-sensitive');
    }
    if (window.pdmSensitiveDom && reason) {
      window.pdmSensitiveDom.clearAll(reason);
    }
    const startup = byId('startup-page');
    const bar = byId('startup-minimized-bar');
    if (startup) {
      startup.classList.remove('hidden', 'minimized');
    }
    if (bar) bar.classList.remove('show');
    const password = byId('db-password');
    if (password) {
      password.value = '';
      setStaticPasswordVisibility('db-password', 'startup-eye', false);
    }
    setProductGlobalSearchValue('');
    const card = document.querySelector('.startup-card');
    if (card) card.classList.remove('is-connecting', 'is-locked');
    const connect = document.querySelector('.connect-btn');
    if (connect) {
      connect.dataset.i18n = 'startup.button.connect';
      connect.textContent = t('startup.button.connect');
    }
    setFeedback('', '');
    byId('page-settings')?.classList.remove('connected');
    updateDbDependentUI(false);
    setProductCurrentDatabaseInfo();
    navigateTo('vault');
    const title = byId('topbar-title');
    if (title) {
      title.dataset.i18n = 'topbar.title.connect';
      title.textContent = t('topbar.title.connect');
    }
    setStatusDisconnected();
    refreshControls();
  }

  function applyUnlocked(result) {
    clearDeleteRecordState();
    runtime.changeKeyTerminalReason = '';
    runtime.lockedNotice = '';
    runtime.state = 'UNLOCKED';
    runtime.sessionEpoch = result.sessionEpoch;
    runtime.lastLockReason = '';
    runtime.databaseLabel = result.databaseLabel;
    runtime.upgradeBackupName = result.upgradeBackupName || '';
    runtime.selectionTicket = '';
    runtime.targetKind = 'NONE';
    runtime.targetLocked = false;
    clearVaultAuthority();
    clearNoteAuthority();
    resetClipboardState();
    renderBoundedRecents(result.recentDatabases);
    state.connected = true;
    state.startupMinimized = false;
    state.currentNav = 'vault';
    state.viewMode = runtime.vaultView.toLowerCase();
    state.sortMode = runtime.vaultSort.toLowerCase();
    passwords.splice(0, passwords.length);
    notes.splice(0, notes.length);
    const startup = byId('startup-page');
    const bar = byId('startup-minimized-bar');
    if (startup) {
      startup.classList.add('hidden');
      startup.classList.remove('minimized');
      void startup.offsetWidth;
    }
    document.documentElement.classList.remove(
      'pdm-security-lock-handoff-static',
    );
    if (bar) bar.classList.remove('show');
    const card = document.querySelector('.startup-card');
    if (card) card.classList.remove('is-connecting', 'is-locked');
    const connect = document.querySelector('.connect-btn');
    if (connect) {
      connect.dataset.i18n = 'startup.button.connect';
      connect.textContent = t('startup.button.connect');
    }
    setFeedback('', '');
    byId('page-settings')?.classList.add('connected');
    navigateTo('vault', false);
    setStatusConnected(runtime.databaseLabel);
    setProductCurrentDatabaseInfo();
    refreshControls();
    requestVaultPage();
    window.pdmFocusVisibility?.reset();
    window.pdmFocusVisibility?.focusApplicationRoot();
  }

  function acknowledge(ack, pendingField, expectedRequest) {
    if (runtime[pendingField] !== expectedRequest) return true;
    if (
      !ack ||
      ack.accepted !== true ||
      ack.errorCode !== 'OK'
    ) {
      runtime[pendingField] = '';
      if (pendingField === 'pendingChoose') {
        runtime.openAfterChoose = false;
      }
      if (pendingField === 'pendingList') {
        runtime.pendingListKey = '';
      }
      if (pendingField === 'pendingRecent') {
        runtime.pendingRecentEntry = null;
      }
      if (
        pendingField === 'pendingList' ||
        pendingField === 'pendingDetails'
      ) {
        if (pendingField === 'pendingDetails') {
          clearSelectedDetails();
        }
        showErrorToast(ack && ack.errorCode);
        renderM4Vault();
      } else {
        setFeedback(
          'error',
          errorText(ack && ack.errorCode),
        );
      }
      const card = document.querySelector('.startup-card');
      if (card) card.classList.remove('is-connecting');
      refreshControls();
      return false;
    }
    return true;
  }

  function chooseDatabaseTarget(
    databasePathCandidate = '',
    openAfterChoose = false,
  ) {
    if (
      runtime.state !== 'LOCKED' ||
      !runtime.bridge ||
      runtime.pendingChoose ||
      runtime.pendingRecent ||
      runtime.pendingRemove ||
      runtime.pendingOpen
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingChoose = id;
    runtime.openAfterChoose = openAfterChoose;
    refreshControls();
    runtime.bridge.chooseDatabaseTargetV1(
      id,
      runtime.pageEpoch,
      databasePathCandidate,
      (ack) => acknowledge(ack, 'pendingChoose', id),
    );
  }

  function selectRecentDatabase(entry) {
    if (
      runtime.state !== 'LOCKED' ||
      !runtime.bridge ||
      runtime.pendingChoose ||
      runtime.pendingRecent ||
      runtime.pendingRemove ||
      runtime.pendingOpen ||
      !entry ||
      typeof entry.recentDatabaseId !== 'string' ||
      typeof entry.displayPath !== 'string'
    ) {
      return;
    }
    const id = requestId();
    runtime.openAfterChoose = false;
    runtime.pendingRecent = id;
    runtime.pendingRecentEntry = entry;
    if (!restoreChangeKeyConnectionNotice()) setFeedback('', '');
    refreshControls();
    runtime.bridge.selectRecentDatabaseV1(
      id,
      runtime.pageEpoch,
      entry.recentDatabaseId,
      (ack) => acknowledge(ack, 'pendingRecent', id),
    );
  }

  function removeRecentDatabase(entry, index) {
    if (
      runtime.state !== 'LOCKED' ||
      !runtime.bridge ||
      runtime.pendingChoose ||
      runtime.pendingRecent ||
      runtime.pendingRemove ||
      runtime.pendingOpen ||
      !entry ||
      typeof entry.recentDatabaseId !== 'string'
    ) return;
    const id = requestId();
    runtime.pendingRemove = id;
    runtime.pendingRemoveIndex = index;
    runtime.pendingRemoveFocusKey = `recent-remove:${entry.recentDatabaseId}`;
    refreshControls();
    runtime.bridge.removeRecentDatabaseV1(
      id,
      runtime.pageEpoch,
      entry.recentDatabaseId,
      (ack) => {
        if (
          runtime.pendingRemove === id &&
          (!ack || ack.accepted !== true || ack.errorCode !== 'OK')
        ) {
          const failedFocusKey = runtime.pendingRemoveFocusKey;
          runtime.pendingRemove = '';
          runtime.pendingRemoveIndex = -1;
          runtime.pendingRemoveFocusKey = '';
          setFeedback(
            'error',
            '',
            '移除失败，最近列表未改变，请重试。',
            'Removal failed. The recent list is unchanged. Try again.',
          );
          refreshControls();
          window.pdmFocusVisibility?.restore(
            null, [failedFocusKey],
          );
        }
      },
    );
  }

  function openSelectedDatabase() {
    if (
      runtime.state !== 'LOCKED' ||
      !runtime.bridge ||
      runtime.pendingOpen ||
      runtime.pendingChoose ||
      runtime.pendingRecent ||
      runtime.pendingRemove
    ) {
      return;
    }
    const input = byId('db-password');
    if (runtime.targetLocked) {
      if (input) {
        input.value = '';
        setStaticPasswordVisibility('db-password', 'startup-eye', false);
      }
      setFeedback('error', errorText('LOCKED_OUT'));
      refreshControls();
      if (input) input.focus({preventScroll: true});
      return;
    }
    if (!runtime.selectionTicket) {
      const path = byId('db-path');
      const candidate = path ? path.value.trim() : '';
      if (!candidate) {
        refreshControls();
        return;
      }
      chooseDatabaseTarget(candidate, true);
      return;
    }
    const id = requestId();
    let masterPassword = input ? input.value : '';
    runtime.pendingOpen = id;
    const card = document.querySelector('.startup-card');
    const connect = document.querySelector('.connect-btn');
    if (card) card.classList.add('is-connecting');
    if (connect) {
      connect.dataset.i18n = 'connection.connecting';
      connect.textContent = t('connection.connecting');
    }
    setFeedback('pending', '', '', '', 'connection.connecting');
    refreshControls();
    if (input) input.value = '';
    try {
      runtime.bridge.openDatabaseV1(
        id,
        runtime.pageEpoch,
        runtime.selectionTicket,
        masterPassword,
        (ack) => acknowledge(ack, 'pendingOpen', id),
      );
    } finally {
      masterPassword = '';
      if (input) input.value = '';
    }
  }

  function lockDatabase() {
    if (
      runtime.state !== 'UNLOCKED' ||
      !runtime.bridge ||
      runtime.pendingLock
    ) {
      return;
    }
    const id = requestId();
    runtime.pendingLock = id;
    refreshControls();
    runtime.bridge.lockV1(
      id,
      runtime.pageEpoch,
      runtime.sessionEpoch,
      (ack) => acknowledge(ack, 'pendingLock', id),
    );
  }

  function togglePassword() {
    if (runtime.state !== 'LOCKED') return;
    toggleStaticPasswordVisibility('db-password', 'startup-eye');
  }

  function onQuickbarOpened(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingQuickbarOpen ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    runtime.pendingQuickbarOpen = '';
    if (
      errorCode !== 'OK' ||
      !result ||
      Object.keys(result).length !== 0
    ) {
      showErrorToast(errorCode || 'INTERNAL_FAILURE');
    }
    refreshControls();
  }

  function onQuickbarEnabledSet(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingQuickbarEnabled ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingQuickbarEnabled();
      if (runtime.settings) projectQuickbarSettings(runtime.settings);
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const expected = runtime.pendingQuickbarEnabledValue;
    const expectedIdleSeconds = runtime.pendingQuickbarIdleSeconds;
    const normalized = normalizeSettingsResult(result);
    if (
      !normalized ||
      normalized.settings.quickbarEnabled !== expected ||
      normalized.settings.quickbarIdleSeconds !== expectedIdleSeconds
    ) {
      clearPendingQuickbarEnabled();
      if (runtime.settings) projectQuickbarSettings(runtime.settings);
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingQuickbarEnabledRevision = normalized.settingsRevision;
    runtime.pendingQuickbarEnabledSettings = normalized.settings;
    if (hasProjectedSettingsSignal(normalized.settingsRevision, normalized.settings)) {
      finishPendingQuickbarEnabledProjection();
      return;
    }
    refreshControls();
  }

  function onQuickbarHotkeySet(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingQuickbarHotkey ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingQuickbarHotkey();
      if (runtime.settings) projectQuickbarSettings(runtime.settings);
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const expected = runtime.pendingQuickbarHotkeyValue;
    const normalized = normalizeHotkeySettingsResult(result);
    if (!normalized || normalized.settings.quickbarHotkey !== expected) {
      clearPendingQuickbarHotkey();
      if (runtime.settings) projectQuickbarSettings(runtime.settings);
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingQuickbarHotkeyRevision = normalized.settingsRevision;
    runtime.pendingQuickbarHotkeySettings = normalized.settings;
    runtime.pendingQuickbarHotkeyWarning = normalized.warning;
    if (hasProjectedSettingsSignal(normalized.settingsRevision, normalized.settings)) {
      finishPendingQuickbarHotkeyProjection();
      return;
    }
    refreshControls();
  }

  function onThemeSet(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingTheme ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingTheme();
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const requestedTheme = runtime.pendingThemeValue;
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.theme !== requestedTheme) {
      clearPendingTheme();
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingThemeRevision = normalized.settingsRevision;
    runtime.pendingThemeSettings = normalized.settings;
    if (
      hasProjectedSettingsSignal(
        normalized.settingsRevision,
        normalized.settings,
      )
    ) {
      finishPendingThemeProjection();
      return;
    }
    refreshControls();
  }

  function onLanguageSet(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingLanguage ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingLanguage();
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const requestedLanguage = runtime.pendingLanguageValue;
    const normalized = normalizeSettingsResult(result);
    if (
      !normalized ||
      normalized.settings.language !== requestedLanguage
    ) {
      clearPendingLanguage();
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingLanguageRevision = normalized.settingsRevision;
    runtime.pendingLanguageSettings = normalized.settings;
    if (
      hasProjectedSettingsSignal(
        normalized.settingsRevision,
        normalized.settings,
      )
    ) {
      finishPendingLanguageProjection();
      return;
    }
    refreshControls();
  }

  function onUiFontScaleSet(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingUiFontScale ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingUiFontScale();
      projectUiFontScale(runtime.settings?.uiFontScale || '100');
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const requestedScale = runtime.pendingUiFontScaleValue;
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.uiFontScale !== requestedScale) {
      clearPendingUiFontScale();
      projectUiFontScale(runtime.settings?.uiFontScale || '100');
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingUiFontScaleRevision = normalized.settingsRevision;
    runtime.pendingUiFontScaleSettings = normalized.settings;
    if (
      hasProjectedSettingsSignal(
        normalized.settingsRevision,
        normalized.settings,
      )
    ) {
      finishPendingUiFontScaleProjection();
      return;
    }
    refreshControls();
  }

  function onStartupAutofillSet(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingStartupAutofill || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    if (errorCode !== 'OK') {
      clearPendingStartupAutofill();
      if (runtime.settings) projectStartupAutofill(runtime.settings.startupAutofill);
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.startupAutofill !== runtime.pendingStartupAutofillValue) {
      clearPendingStartupAutofill();
      if (runtime.settings) projectStartupAutofill(runtime.settings.startupAutofill);
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingStartupAutofillRevision = normalized.settingsRevision;
    runtime.pendingStartupAutofillSettings = normalized.settings;
    if (hasProjectedSettingsSignal(normalized.settingsRevision, normalized.settings)) finishPendingStartupAutofillProjection();
    else refreshControls();
  }

  function onDefaultViewSet(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingDefaultView || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    if (errorCode !== 'OK') {
      clearPendingDefaultView();
      if (runtime.settings) projectDefaultView(runtime.settings.defaultView);
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.defaultView !== runtime.pendingDefaultViewValue) {
      clearPendingDefaultView();
      if (runtime.settings) projectDefaultView(runtime.settings.defaultView);
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingDefaultViewRevision = normalized.settingsRevision;
    runtime.pendingDefaultViewSettings = normalized.settings;
    if (hasProjectedSettingsSignal(normalized.settingsRevision, normalized.settings)) finishPendingDefaultViewProjection();
    else refreshControls();
  }

  function onSidebarTextSet(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingSidebarText || pageEpoch !== runtime.pageEpoch || sessionEpoch !== 0) return;
    if (errorCode !== 'OK') {
      clearPendingSidebarText();
      if (runtime.settings) projectSidebarText(runtime.settings.sidebarText);
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.sidebarText !== runtime.pendingSidebarTextValue) {
      clearPendingSidebarText();
      if (runtime.settings) projectSidebarText(runtime.settings.sidebarText);
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingSidebarTextRevision = normalized.settingsRevision;
    runtime.pendingSidebarTextSettings = normalized.settings;
    if (hasProjectedSettingsSignal(normalized.settingsRevision, normalized.settings)) finishPendingSidebarTextProjection();
    else refreshControls();
  }

  function onClipboardPolicySet(request, pageEpoch, sessionEpoch, errorCode, _argument, _retry, result) {
    if (request !== runtime.pendingClipboardPolicy || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
    if (errorCode !== 'OK') {
      clearPendingClipboardPolicy();
      if (runtime.settings) projectClipboardPolicy(runtime.settings.clipboardMode, runtime.settings.clipboardSeconds);
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.clipboardMode !== runtime.pendingClipboardMode || normalized.settings.clipboardSeconds !== runtime.pendingClipboardSeconds) {
      clearPendingClipboardPolicy();
      if (runtime.settings) projectClipboardPolicy(runtime.settings.clipboardMode, runtime.settings.clipboardSeconds);
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingClipboardRevision = normalized.settingsRevision;
    runtime.pendingClipboardSettings = normalized.settings;
    if (hasProjectedSettingsSignal(normalized.settingsRevision, normalized.settings)) finishPendingClipboardPolicyProjection();
    else refreshControls();
  }

  function onSortModeSet(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingSort ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingSort();
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const requestedSort = runtime.pendingSortValue;
    const normalized = normalizeSettingsResult(result);
    if (!normalized || normalized.settings.sortMode !== requestedSort) {
      clearPendingSort();
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingSortRevision = normalized.settingsRevision;
    runtime.pendingSortSettings = normalized.settings;
    if (
      hasProjectedSettingsSignal(
        normalized.settingsRevision,
        normalized.settings,
      )
    ) {
      finishPendingSortProjection();
      return;
    }
    refreshControls();
  }

  function onCloseBehaviorSet(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingClose ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingClose();
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const requestedBehavior = runtime.pendingCloseValue;
    const normalized = normalizeSettingsResult(result);
    if (
      !normalized ||
      normalized.settings.closeBehavior !== requestedBehavior
    ) {
      clearPendingClose();
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingCloseRevision = normalized.settingsRevision;
    runtime.pendingCloseSettings = normalized.settings;
    if (
      hasProjectedSettingsSignal(
        normalized.settingsRevision,
        normalized.settings,
      )
    ) {
      finishPendingCloseProjection();
      return;
    }
    refreshControls();
  }

  function onAutoLockPolicySet(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingAutoLock ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      clearPendingAutoLock();
      if (runtime.settings) {
        projectAutoLockPolicy(
          runtime.settings.autoLockEnabled,
          runtime.settings.autoLockMinutes,
        );
      }
      showSettingsFailure(errorCode);
      refreshControls();
      return;
    }
    const requestedEnabled = runtime.pendingAutoLockEnabled;
    const requestedMinutes = runtime.pendingAutoLockMinutes;
    const normalized = normalizeSettingsResult(result);
    if (
      !normalized ||
      normalized.settings.autoLockEnabled !== requestedEnabled ||
      normalized.settings.autoLockMinutes !== requestedMinutes
    ) {
      clearPendingAutoLock();
      if (runtime.settings) {
        projectAutoLockPolicy(
          runtime.settings.autoLockEnabled,
          runtime.settings.autoLockMinutes,
        );
      }
      showSettingsFailure('INTERNAL_FAILURE');
      refreshControls();
      return;
    }
    runtime.pendingAutoLockRevision = normalized.settingsRevision;
    runtime.pendingAutoLockSettings = normalized.settings;
    if (
      hasProjectedSettingsSignal(
        normalized.settingsRevision,
        normalized.settings,
      )
    ) {
      finishPendingAutoLockProjection();
      return;
    }
    refreshControls();
  }

  function onPasswordGeneratorDefaultsSet(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingGeneratorDefaults ||
      pageEpoch !== runtime.pageEpoch ||
      sessionEpoch !== runtime.sessionEpoch
    ) {
      return;
    }
    if (errorCode !== 'OK') {
      failGeneratorDefaults(errorCode);
      return;
    }
    const normalized = normalizeSettingsResult(result);
    if (
      !normalized ||
      generatorPolicyKey(normalized.settings.generator) !==
        generatorPolicyKey(runtime.pendingGeneratorPolicy)
    ) {
      failGeneratorDefaults('INTERNAL_FAILURE');
      return;
    }
    runtime.pendingGeneratorRevision = normalized.settingsRevision;
    runtime.pendingGeneratorSettings = normalized.settings;
    if (
      hasProjectedSettingsSignal(
        normalized.settingsRevision,
        normalized.settings,
      )
    ) {
      finishPendingGeneratorProjection();
      return;
    }
    refreshControls();
  }

  function onSettingsChanged(pageEpoch, settingsRevision, settingsValue) {
    if (pageEpoch !== runtime.pageEpoch) return;
    const normalized = normalizeSettingsResult({
      settingsRevision,
      settings: settingsValue,
    });
    if (!normalized) {
      showSettingsFailure('INTERNAL_FAILURE');
      return;
    }
    applySettingsProjection(
      normalized.settingsRevision,
      normalized.settings,
      'S02',
    );
    rememberSettingsSignal(
      normalized.settingsRevision,
      normalized.settings,
    );
    settleProjectedSettingsWaiters(
      normalized.settingsRevision,
      normalized.settings,
    );
  }

  function onSystemThemeChanged(pageEpoch, effectiveTheme) {
    if (
      pageEpoch !== runtime.pageEpoch ||
      !runtime.settings ||
      runtime.themePreference !== 'AUTO' ||
      !['LIGHT', 'DARK'].includes(effectiveTheme) ||
      effectiveTheme === runtime.effectiveTheme
    ) {
      return;
    }
    const settings = normalizeSettingsSnapshot({
      ...runtime.settings,
      effectiveTheme,
    });
    if (!settings) return;
    runtime.settings = settings;
    projectProductTheme('AUTO', effectiveTheme);
    runtime.settingsProjectionSource = 'S05';
    runtime.settingsProjectionCount += 1;
    runtime.systemThemeProjectionCount += 1;
    refreshControls();
  }

  function onHandshake(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    retryAfterMs,
    result,
  ) {
    if (request !== runtime.pendingHandshake) return;
    runtime.pendingHandshake = '';
    if (
      errorCode !== 'OK' ||
      !result ||
      result.contractVersion !== CONTRACT_VERSION ||
      result.pageEpoch !== pageEpoch ||
      sessionEpoch !== 0 ||
      result.state !== 'LOCKED'
    ) {
      setFeedback('error', errorText(errorCode));
      return;
    }
    const normalizedSettings = normalizeSettingsResult({
      settingsRevision: result.settingsRevision,
      settings: result.settings,
    });
    if (!normalizedSettings) {
      setFeedback('error', errorText('INTERNAL_FAILURE'));
      return;
    }
    runtime.pageEpoch = pageEpoch;
    applySettingsProjection(
      normalizedSettings.settingsRevision,
      normalizedSettings.settings,
      'BOOTSTRAP',
    );
    renderBoundedRecents(result.recentDatabases);
    runtime.displayPath = (
      typeof result.startupPath === 'string' ? result.startupPath : ''
    );
    const path = byId('db-path');
    if (path) {
      path.value = runtime.displayPath;
      path.readOnly = false;
      path.removeAttribute('aria-readonly');
    }
    applyLocked('');
    runtime.ready = true;
    document.documentElement.dataset.pdmMode = 'product';
    document.documentElement.dataset.pdmM4State = 'locked';
    refreshControls();
    requestProductUpdate('state');
    window.dispatchEvent(
      new CustomEvent('pdm-shared-canvas-ready'),
    );
  }

  function onTargetChosen(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingChoose ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    const openAfterChoose = runtime.openAfterChoose;
    runtime.pendingChoose = '';
    runtime.openAfterChoose = false;
    if (errorCode !== 'OK' || !result) {
      setFeedback('error', connectionTargetErrorText(errorCode));
      refreshControls();
      return;
    }
    if (!result.selected) {
      restoreChangeKeyConnectionNotice();
      refreshControls();
      return;
    }
    applyTargetSelection(result, !openAfterChoose);
    if (openAfterChoose) openSelectedDatabase();
  }

  function applyTargetSelection(result, focusPassword = true) {
    runtime.selectionTicket = result.selectionTicket;
    runtime.targetKind = result.targetKind;
    runtime.targetLocked = false;
    runtime.displayPath = result.displayPath;
    const path = byId('db-path');
    if (path) {
      path.value = result.displayPath;
    }
    const card = document.querySelector('.startup-card');
    if (card) card.classList.remove('is-locked');
    const connect = document.querySelector('.connect-btn');
    if (connect) {
      connect.dataset.i18n = 'startup.button.connect';
      connect.textContent = t('startup.button.connect');
    }
    if (!restoreChangeKeyConnectionNotice()) setFeedback('', '');
    const password = byId('db-password');
    if (password && focusPassword) {
      password.focus({preventScroll: true});
    }
    refreshControls();
  }

  function onRecentSelected(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingRecent ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    const selectedEntry = runtime.pendingRecentEntry;
    runtime.pendingRecent = '';
    runtime.pendingRecentEntry = null;
    if (errorCode !== 'OK' || !result) {
      if (
        errorCode === 'LOCKED_OUT' &&
        retryAfterMs > 0 &&
        selectedEntry
      ) {
        runtime.displayPath = selectedEntry.displayPath;
        runtime.targetKind = 'OPEN_EXISTING';
        const path = byId('db-path');
        if (path) {
          path.value = selectedEntry.displayPath;
        }
        applyCurrentTargetLock();
        return;
      }
      setFeedback('error', errorText(errorCode));
      refreshControls();
      return;
    }
    if (!result.selected) {
      restoreChangeKeyConnectionNotice();
      refreshControls();
      return;
    }
    applyTargetSelection(result);
  }

  function onRecentRemoved(
    request,
    pageEpoch,
    _sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingRemove ||
      pageEpoch !== runtime.pageEpoch
    ) return;
    const removeIndex = runtime.pendingRemoveIndex;
    const failedFocusKey = runtime.pendingRemoveFocusKey;
    runtime.pendingRemove = '';
    runtime.pendingRemoveIndex = -1;
    if (errorCode !== 'OK' || !result || !Array.isArray(result.recentDatabases)) {
      runtime.pendingRemoveFocusKey = '';
      setFeedback(
        'error',
        '',
        '移除失败，最近列表未改变，请重试。',
        'Removal failed. The recent list is unchanged. Try again.',
      );
      refreshControls();
      window.pdmFocusVisibility?.restore(null, [failedFocusKey]);
      return;
    }
    renderBoundedRecents(result.recentDatabases);
    announceOperationText(fixedText(
      '已从最近列表移除。',
      'Removed from the recent list.',
    ));
    runtime.pendingRemoveFocusKey = '';
    refreshControls();
    const removes = Array.from(document.querySelectorAll(
      '[data-pdm-recent-action="remove"]',
    ));
    const next = removes[Math.min(removeIndex, removes.length - 1)];
    window.pdmFocusVisibility?.restore(null, [
      focusKeyForElement(next),
      'db-path',
    ]);
  }

  function applyCurrentTargetLock() {
    runtime.targetLocked = true;
    runtime.selectionTicket = '';
    const password = byId('db-password');
    if (password) {
      password.value = '';
      setStaticPasswordVisibility('db-password', 'startup-eye', false);
    }
    const card = document.querySelector('.startup-card');
    if (card) {
      card.classList.remove('is-connecting');
      card.classList.remove('is-locked');
    }
    const connect = document.querySelector('.connect-btn');
    if (connect) {
      connect.dataset.i18n = 'startup.button.connect';
      connect.textContent = t('startup.button.connect');
    }
    setFeedback('error', errorText('LOCKED_OUT'));
    refreshControls();
  }

  function onDatabaseOpened(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingOpen ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    runtime.pendingOpen = '';
    const card = document.querySelector('.startup-card');
    if (card) card.classList.remove('is-connecting');
    const validSuccess = Boolean(
      errorCode === 'OK' &&
      result &&
      result.state === 'UNLOCKED' &&
      sessionEpoch > 0 &&
      result.sessionEpoch === sessionEpoch &&
      Number.isSafeInteger(result.passwordCount) &&
      Number.isSafeInteger(result.noteCount) &&
      typeof result.upgradeBackupName === 'string' &&
      (!result.upgradeBackupName || isBackupLabel(result.upgradeBackupName)) &&
      Array.isArray(result.recentDatabases)
    );
    if (validSuccess) {
      applyUnlocked(result);
      document.documentElement.dataset.pdmM4State = 'unlocked';
      if (result.upgradeBackupName) {
        showToast(fixedText(
          `升级前的原样加密副本已保存：${result.upgradeBackupName}；详见设置。`,
          `Unchanged encrypted copy saved before upgrade: ${result.upgradeBackupName}. See Settings.`,
        ), 'info');
      }
      return;
    }
    if (errorCode === 'LOCKED_OUT' && retryAfterMs > 0) {
      applyCurrentTargetLock();
      return;
    }
    const preservesTarget = (
      errorCode === 'AUTH_FAILED_RETRY_2' ||
      errorCode === 'AUTH_FAILED_RETRY_1' ||
      errorCode === 'DATABASE_IO_FAILED' ||
      errorCode === 'CANCELLED'
    );
    if (!preservesTarget) runtime.selectionTicket = '';
    setFeedback('error', errorText(errorCode));
    const connect = document.querySelector('.connect-btn');
    if (connect) {
      connect.dataset.i18n = 'startup.button.connect';
      connect.textContent = t('startup.button.connect');
    }
    refreshControls();
    if (
      errorCode === 'AUTH_FAILED_RETRY_2' ||
      errorCode === 'AUTH_FAILED_RETRY_1'
    ) {
      const password = byId('db-password');
      if (password) password.focus({preventScroll: true});
    }
  }

  function onLocked(
    request,
    pageEpoch,
    sessionEpoch,
    errorCode,
    _errorArgumentIndex,
    _retryAfterMs,
    result,
  ) {
    if (
      request !== runtime.pendingLock ||
      pageEpoch !== runtime.pageEpoch
    ) {
      return;
    }
    runtime.pendingLock = '';
    if (
      errorCode === 'OK' &&
      sessionEpoch === 0 &&
      result &&
      result.state === 'LOCKED'
    ) {
      // Native S01 is the single public reason/terminal-state authority.
      return;
    }
    const failure = errorText(errorCode);
    applyLocked('manual_lock');
    document.documentElement.dataset.pdmM4State = 'locked';
    setFeedback('error', failure);
  }

  function assignStaticFocusKeys() {
    const mappings = [
      ['[data-nav="vault"]', 'nav:vault'],
      ['[data-nav="notes"]', 'nav:notes'],
      ['[data-nav="security"]', 'nav:security'],
      ['[data-nav="tools"]', 'nav:tools'],
      ['[data-nav="settings"]', 'nav:settings'],
      ['[data-pdm-onclick="lockApp()"]', 'nav:lock'],
      ['#global-search-clear', 'topbar:search-clear'],
      ['#autofill-toggle', 'settings:autofill'],
      ['#view-default-segment', 'settings:default-view'],
      ['#sidebar-text-toggle', 'settings:sidebar-text'],
      ['#clip-clear-segment', 'settings:clipboard-mode'],
      [
        '[data-pdm-onclick="openAddPasswordDialog()"]',
        'vault:add',
      ],
      ['[data-pdm-onclick="openAddNoteDialog()"]', 'note:add'],
      [
        '[data-pdm-onclick="openChangeDbPasswordDialog()"]',
        'settings:change-key',
      ],
    ];
    for (const [selector, key] of mappings) {
      document.querySelectorAll(selector).forEach((element) => {
        element.dataset.pdmNativeFocusKey = key;
      });
    }
  }

  function bindEvents() {
    assignStaticFocusKeys();
    for (const [id, request] of [
      ['autofill-toggle', requestProductStartupAutofill],
      ['sidebar-text-toggle', requestProductSidebarText],
    ]) {
      const toggle = byId(id);
      if (!toggle) continue;
      toggle.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (toggle.dataset.pdmM4Disabled !== 'true') request();
      });
      toggle.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (toggle.dataset.pdmM4Disabled !== 'true') request();
      });
    }
    const quickbarToggle = document.querySelector(
      '[data-i18n="settings.tray.quickbar.name"]',
    )?.closest('.setting-row')?.querySelector('.toggle');
    if (quickbarToggle) {
      quickbarToggle.id = 'quickbar-toggle';
      quickbarToggle.removeAttribute('data-pdm-onclick');
      quickbarToggle.setAttribute('role', 'switch');
      quickbarToggle.tabIndex = 0;
      quickbarToggle.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (quickbarToggle.dataset.pdmM4Disabled !== 'true') {
          requestQuickbarEnabled();
        }
      });
      quickbarToggle.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (quickbarToggle.dataset.pdmM4Disabled !== 'true') {
          requestQuickbarEnabled();
        }
      });
    }
    const autoLockToggle = byId('autolock-toggle');
    if (autoLockToggle) {
      autoLockToggle.setAttribute('role', 'switch');
      autoLockToggle.tabIndex = 0;
      autoLockToggle.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (autoLockToggle.dataset.pdmM4Disabled !== 'true') {
          requestProductAutoLockToggle();
        }
      });
      autoLockToggle.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (autoLockToggle.dataset.pdmM4Disabled !== 'true') {
          requestProductAutoLockToggle();
        }
      });
    }
    const autoLockSlider = byId('autolock-slider');
    const autoLockNumber = byId('autolock-num');
    [autoLockSlider, autoLockNumber].forEach((control) => {
      if (!control) return;
      control.addEventListener('input', (event) => {
        event.stopImmediatePropagation();
        if (control.dataset.pdmM4Disabled === 'true') {
          if (runtime.settings) {
            projectAutoLockPolicy(
              runtime.settings.autoLockEnabled,
              runtime.settings.autoLockMinutes,
            );
          }
          return;
        }
        requestProductAutoLockMinutes(control.value);
      });
    });
    if (autoLockNumber) {
      autoLockNumber.addEventListener('blur', (event) => {
        event.stopImmediatePropagation();
        if (autoLockNumber.dataset.pdmM4Disabled !== 'true') {
          requestProductAutoLockMinutes(autoLockNumber.value);
        }
      });
    }
    const staleSlider = byId('stale-slider');
    const staleNumber = byId('stale-num');
    [staleSlider, staleNumber].forEach((control) => {
      if (!control) return;
      control.removeAttribute('data-pdm-oninput');
      control.removeAttribute('data-pdm-onblur');
      control.addEventListener('change', (event) => {
        event.stopImmediatePropagation();
        requestStaleThreshold(control.value);
      });
    });
    const quickbarTimeoutSlider = byId('quickbar-timeout-slider');
    const quickbarTimeoutNumber = byId('quickbar-timeout-num');
    [quickbarTimeoutSlider, quickbarTimeoutNumber].forEach((control) => {
      if (!control) return;
      control.removeAttribute('data-pdm-oninput');
      control.addEventListener('change', (event) => {
        event.stopImmediatePropagation();
        if (control.dataset.pdmM4Disabled === 'true') {
          if (runtime.settings) projectQuickbarSettings(runtime.settings);
          return;
        }
        requestQuickbarIdleSeconds(control.value);
      });
    });
    if (quickbarTimeoutNumber) {
      quickbarTimeoutNumber.removeAttribute('data-pdm-onblur');
      quickbarTimeoutNumber.addEventListener('blur', (event) => {
        event.stopImmediatePropagation();
        if (quickbarTimeoutNumber.dataset.pdmM4Disabled !== 'true') {
          requestQuickbarIdleSeconds(quickbarTimeoutNumber.value);
        }
      });
    }
    const clipSlider = byId('clip-slider');
    const clipNumber = byId('clip-num');
    [clipSlider, clipNumber].forEach((control) => {
      if (!control) return;
      control.removeAttribute('data-pdm-oninput');
      control.removeAttribute('data-pdm-onblur');
      control.addEventListener('change', (event) => {
        event.stopImmediatePropagation();
        if (control.dataset.pdmM4Disabled !== 'true') {
          requestProductClipboardPolicy(
            runtime.settings?.clipboardMode || 'COUNTDOWN',
            control.value,
          );
        }
      });
    });
    const databasePath = byId('db-path');
    if (databasePath) {
      databasePath.maxLength = 1024;
      // 浏览器先完成失焦时的原生滚动复位，再在本次绘制前定位末尾。
      databasePath.addEventListener('blur', () => window.queueMicrotask(showDatabasePathTail));
      databasePath.addEventListener('input', () => {
        if (runtime.state !== 'LOCKED') return;
        runtime.selectionTicket = '';
        runtime.targetKind = 'NONE';
        runtime.targetLocked = false;
        runtime.displayPath = databasePath.value;
        const card = document.querySelector('.startup-card');
        if (card) card.classList.remove('is-connecting', 'is-locked');
        if (!restoreChangeKeyConnectionNotice()) setFeedback('', '');
        refreshControls();
      });
    }
    const databasePassword = byId('db-password');
    if (databasePassword) {
      databasePassword.addEventListener('input', () => {
        if (runtime.state !== 'LOCKED') return;
        restoreChangeKeyConnectionNotice();
      });
    }
    const search = byId('global-search');
    if (search) {
      search.removeAttribute('maxlength');
      search.addEventListener('input', (event) => {
        if (event.isComposing) {
          window.clearTimeout(runtime.searchTimer);
          window.clearTimeout(runtime.noteSearchTimer);
          runtime.searchTimer = runtime.noteSearchTimer = 0;
          syncProductGlobalSearch();
          return;
        }
        handleProductGlobalSearchInput(search.value);
      });
      search.addEventListener('compositionend', () => handleProductGlobalSearchInput(search.value));
    }
    document.querySelectorAll('#filter-chips .chip').forEach((chip) => {
      chip.setAttribute('role', 'button');
      chip.tabIndex = 0;
      chip.dataset.pdmNativeFocusKey = (
        `vault-filter:${String(chip.dataset.filter || '').toUpperCase()}`
      );
      const activate = () => {
        if (runtime.state !== 'UNLOCKED') return;
        const value = String(chip.dataset.filter || '').toUpperCase();
        if (
          !['ALL', 'FAVORITE', 'WEAK', 'DUPLICATE', 'SIMILAR'].includes(value) ||
          value === runtime.vaultFilter
        ) {
          return;
        }
        runtime.vaultFilter = value;
        resetVaultPagePosition();
        queueVaultReload();
      };
      chip.addEventListener('click', activate);
      chip.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        activate();
      });
    });
    document.querySelectorAll('#page-notes .chip[data-nfilter]').forEach(
      (chip) => {
        chip.setAttribute('role', 'button');
        chip.tabIndex = 0;
        chip.dataset.pdmNativeFocusKey = (
          `note-filter:${String(chip.dataset.nfilter || '').toUpperCase()}`
        );
        const activate = () => {
          if (
            runtime.state !== 'UNLOCKED' ||
            state.currentNav !== 'notes'
          ) {
            return;
          }
          setProductNoteFilter(chip.dataset.nfilter);
        };
        chip.addEventListener('click', activate);
        chip.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return;
          event.preventDefault();
          activate();
        });
      },
    );
    document.querySelectorAll('.view-switcher [data-view]').forEach(
      (button) => {
        button.dataset.pdmNativeFocusKey = (
          `vault-view:${String(button.dataset.view || '').toUpperCase()}`
        );
        button.addEventListener('click', () => {
          if (runtime.state !== 'UNLOCKED') return;
          const value = String(button.dataset.view || '').toUpperCase();
          if (!['LIST', 'SPLIT'].includes(value)) return;
          runtime.vaultView = value;
          state.viewMode = value.toLowerCase();
          clearSelectedDetails();
          renderM4Vault();
          refreshControls();
        });
      },
    );
    document.addEventListener('mousedown', (event) => {
      suppressBlockedRecordSaveMultiClick(event);
    }, true);
    document.addEventListener('dblclick', (event) => {
      suppressBlockedRecordSaveMultiClick(event);
    }, true);
    const sortTrigger = byId('sort-trigger');
    if (sortTrigger) {
      sortTrigger.addEventListener('click', (event) => {
        if (
          runtime.state !== 'UNLOCKED' || runtime.pendingSort ||
          sortTrigger.dataset.pdmM4Disabled === 'true'
        ) return;
        toggleSortDropdown(event);
      });
    }
    const noteSortTrigger = byId('note-sort-trigger');
    if (noteSortTrigger) {
      noteSortTrigger.addEventListener('click', (event) => {
        if (
          runtime.state === 'UNLOCKED' && !runtime.pendingNoteList &&
          !noteWritePending() && !noteDraftDirty() &&
          noteSortTrigger.dataset.pdmM4Disabled !== 'true'
        ) {
          toggleSortDropdown(event, 'note-sort-dropdown');
        }
      });
    }
    bindSortDropdownKeyboard(
      'sort-dropdown',
      (value) => {
        const sortMode = String(value || '').toUpperCase();
        if (['UPDATED', 'NAME', 'STRENGTH'].includes(sortMode) && sortMode !== runtime.vaultSort) {
          requestProductSort(sortMode);
        }
      },
      () => runtime.state === 'UNLOCKED' && !runtime.pendingSort,
    );
    bindSortDropdownKeyboard(
      'note-sort-dropdown',
      selectNoteSort,
      () => runtime.state === 'UNLOCKED' && !runtime.pendingNoteList && !noteWritePending() && !noteDraftDirty(),
    );
    document.querySelectorAll('#note-sort-menu [data-pdm-note-sort]').forEach(
      (option) => {
        option.addEventListener('click', (event) => {
          if (option.dataset.pdmM4Disabled === 'true') return;
          event.stopPropagation();
          selectNoteSort(option.dataset.pdmNoteSort);
        });
      },
    );
    document.querySelectorAll('#sort-menu .sort-option').forEach(
      (option) => {
        option.addEventListener('click', (event) => {
          if (
            runtime.state !== 'UNLOCKED' || runtime.pendingSort ||
            option.dataset.pdmM4Disabled === 'true'
          ) return;
          event.stopPropagation();
          const value = String(option.dataset.value || '').toUpperCase();
          if (!['UPDATED', 'NAME', 'STRENGTH'].includes(value)) return;
          closeSortDropdown('sort-dropdown', true);
          if (value === runtime.vaultSort) return;
          requestProductSort(value);
        });
      },
    );
    document.addEventListener('click', (event) => {
      const updateAction = event.target?.closest?.('[data-update-action]');
      if (updateAction) {
        event.preventDefault();
        event.stopImmediatePropagation();
        handleProductUpdate(updateAction);
        return;
      }
      const contact = event.target?.closest?.('[data-pdm-contact]');
      if (contact) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.isTrusted) requestContactSupport(contact);
        return;
      }
      const closeSegment = event.target?.closest?.('#tray-close-segment');
      if (closeSegment) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (closeSegment.dataset.pdmM4Disabled !== 'true') {
          requestProductCloseBehavior();
        }
        return;
      }
      const languageSegment = event.target?.closest?.('#lang-segment');
      if (languageSegment) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (languageSegment.dataset.pdmM4Disabled !== 'true') {
          requestProductLanguage();
        }
        return;
      }
      const defaultViewSegment = event.target?.closest?.('#view-default-segment');
      if (defaultViewSegment) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (defaultViewSegment.dataset.pdmM4Disabled !== 'true') requestProductDefaultView();
        return;
      }
      const clipboardSegment = event.target?.closest?.('#clip-clear-segment');
      if (clipboardSegment) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (clipboardSegment.dataset.pdmM4Disabled !== 'true') requestProductClipboardPolicy();
        return;
      }
      const target = event.target?.closest?.(
        'button,[data-pdm-onclick]',
      );
      if (!target) return;
      if (target.dataset.pdmM4Disabled === 'true') {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      if (target.matches('[data-pdm-onclick="openImportExportDialog(\'export\')"]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        openBackupDialog('export');
      } else if (target.matches('[data-pdm-onclick="openDirectTransferDialog()"]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        openDirectTransferDialog();
      } else if (target.dataset.pdmBackupAction) {
        event.preventDefault();
        event.stopImmediatePropagation();
        handleBackupAction(target);
      } else if (target.id === 'startup-minimized-bar') {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (runtime.state === 'LOCKED') expandStartupModal();
        syncRecentTimeRefresh();
      } else if (target.id === 'theme-btn') {
        event.preventDefault();
        event.stopImmediatePropagation();
        requestProductThemeShortcut();
      } else if (target.id === 'global-search-clear') {
        event.preventDefault();
        event.stopImmediatePropagation();
        clearProductGlobalSearch();
      } else if (target.id === 'topbar-quickbar-btn') {
        event.preventDefault();
        event.stopImmediatePropagation();
        requestQuickbarOpen();
      } else if (target.id === 'quickbar-hotkey-btn') {
        event.preventDefault();
        event.stopImmediatePropagation();
        startProductHotkeyRecording();
      } else if (target.matches('#theme-segment button[data-pdm-theme]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        requestProductTheme(target.dataset.pdmTheme);
      } else if (target.matches('#ui-font-scale-segment button[data-pdm-ui-font-scale]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        requestProductUiFontScale(target.dataset.pdmUiFontScale);
      } else if (target.matches('.browse-btn')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        chooseDatabaseTarget('', false);
      } else if (target.matches('.startup-card .eye-btn')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        togglePassword();
      } else if (
        target.matches('[data-pdm-onclick="toggleCheckPassword()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        toggleDemoCheckPassword();
      } else if (target.matches('.connect-btn')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        openSelectedDatabase();
      } else if (
        target.matches(
          '[data-pdm-onclick="navigateTo(\'vault\')"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchProductView('vault');
      } else if (
        target.matches(
          '[data-pdm-onclick="navigateTo(\'notes\')"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchProductView('notes');
      } else if (
        target.matches(
          '[data-pdm-onclick="navigateTo(\'security\')"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchProductView('security');
      } else if (
        target.matches(
          '[data-pdm-onclick="navigateTo(\'tools\')"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchProductView('tools');
      } else if (
        target.matches(
          '[data-pdm-onclick="navigateTo(\'settings\')"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchProductView('settings');
      } else if (target.matches('[data-nav="help"]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchProductView('help');
      } else if (target.matches('.tool-tab[data-tool]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchProductTool(target.dataset.tool);
      } else if (
        target.matches('[data-pdm-onclick="openAddPasswordDialog()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        openCreateRecordDialog();
      } else if (target.matches('.fix-all-btn')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        startHealthGuidance();
      } else if (target.id === 'health-rescan-start' || target.id === 'health-rescan-cancel') {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (target.id === 'health-rescan-start') startHealthRescan();
        else cancelHealthRescan();
      } else if (
        target.matches('[data-pdm-onclick="openAddNoteDialog()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        openCreateNoteDialog();
      } else if (
        target.matches(
          '[data-pdm-onclick="openChangeDbPasswordDialog()"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        openChangeKeyDialog();
      } else if (
        target.matches('[data-pdm-onclick="closeModal()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeProductModal();
      } else if (
        String(target.dataset.pdmOnclick || '').startsWith(
          'confirmDeleteRecord(',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        submitDeleteRecord();
      } else if (
        target.matches('[data-pdm-onclick="confirmChangeDbPassword()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        submitChangeKey();
      } else if (
        target.matches(
          '[data-pdm-onclick="fillModalGeneratedPassword(\'kf-new\')"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        requestGeneratedPassword('change-key');
      } else if (
        target.matches(
          '[data-pdm-onclick="toggleModalPwVisibility(\'kf-new\',this)"],'
          + '[data-pdm-onclick="toggleModalPwVisibility(\'kf-confirm\',this)"]',
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        const inputId = String(target.dataset.pdmOnclick || '').includes(
          "'kf-confirm'",
        ) ? 'kf-confirm' : 'kf-new';
        toggleDemoModalPassword(inputId, target);
      } else if (
        target.matches('[data-pdm-onclick="toggleModalFav(this)"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        toggleDemoModalFavorite(target);
      } else if (
        target.matches('[data-pdm-onclick="generatePassword()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        requestGeneratedPassword('tool');
      } else if (
        target.matches('[data-pdm-onclick="saveGenerated()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        moveGeneratedPasswordToCreate();
      } else if (
        target.matches('[data-pdm-onclick="copyGenerated()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        copyGeneratedPassword();
      } else if (
        target.matches('[data-pdm-onclick="resetGenConfig()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        resetGeneratorPolicy();
      } else if (target.matches('.check-item[data-charset]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        toggleGeneratorCharset(target);
      } else if (
        target.matches('[data-pdm-onclick="lockApp()"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        lockDatabase();
      }
    }, true);
    document.addEventListener('input', (event) => {
      const target = event.target;
      if (
        !['LOCKED', 'UNLOCKED'].includes(runtime.state) ||
        !(target instanceof HTMLInputElement) ||
        target.dataset.pdmM4Disabled === 'true'
      ) {
        return;
      }
      if (['gen-length', 'gen-length-num'].includes(target.id)) {
        event.stopImmediatePropagation();
        changeGeneratorLength(target.value);
      } else if (
        ['check-input', 'check-platform', 'check-account'].includes(target.id)
      ) {
        event.stopImmediatePropagation();
        onStrengthInputChanged();
      }
    }, true);
    document.addEventListener('change', (event) => {
      if (event.target?.matches?.('[data-update-days]')) {
        event.stopImmediatePropagation();
        saveProductUpdateInterval(event.target);
        return;
      }
      if (
        event.target?.id === 'gen-avoid' &&
        event.target.dataset.pdmM4Disabled !== 'true'
      ) {
        event.stopImmediatePropagation();
        toggleGeneratorAvoid(event.target.checked);
      }
    }, true);
    document.addEventListener('blur', (event) => {
      if (event.target?.id === 'gen-length-num') {
        event.stopImmediatePropagation();
        clampGeneratorLength();
      }
    }, true);
    document.addEventListener('beforeinput', (event) => {
      const target = event.target;
      if (
        runtime.pendingChangeKey &&
        target instanceof HTMLElement &&
        target.closest('[data-pdm-m4-change-key="true"]')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }, true);
    document.addEventListener('keydown', (event) => {
      if (event.isComposing || event.keyCode === 229) return;
      if (event.key === 'Enter' && event.target?.matches?.('[data-update-days]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        saveProductUpdateInterval(event.target);
        return;
      }
      if (runtime.hotkeyRecording) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.key === 'Escape') {
          resetHotkeyRecordingVisual();
          refreshControls();
          return;
        }
        if (['Control', 'Alt', 'Shift', 'Meta'].includes(event.key)) {
          return;
        }
        const hotkey = canonicalHotkeyFromEvent(event);
        if (!hotkey) {
          showErrorToast('HOTKEY_INVALID');
          return;
        }
        requestQuickbarHotkey(hotkey);
        return;
      }
      if (
        runtime.state === 'UNLOCKED' &&
        runtime.settings?.quickbarEnabled &&
        runtime.settings.quickbarRegistration === 'REGISTERED' &&
        eventMatchesQuickbarHotkey(event)
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        requestQuickbarOpen();
        return;
      }
      if (
        event.target?.id === 'tray-close-segment' &&
        (event.key === 'Enter' || event.key === ' ')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.target.dataset.pdmM4Disabled !== 'true') {
          requestProductCloseBehavior();
        }
        return;
      }
      if (
        event.target?.id === 'lang-segment' &&
        (event.key === 'Enter' || event.key === ' ')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.target.dataset.pdmM4Disabled !== 'true') {
          requestProductLanguage();
        }
        return;
      }
      if (
        event.target?.id === 'view-default-segment' &&
        (event.key === 'Enter' || event.key === ' ')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.target.dataset.pdmM4Disabled !== 'true') requestProductDefaultView();
        return;
      }
      if (
        event.target?.id === 'clip-clear-segment' &&
        (event.key === 'Enter' || event.key === ' ')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.target.dataset.pdmM4Disabled !== 'true') requestProductClipboardPolicy();
        return;
      }
      if (activeChangeKeyModal()) {
        if (runtime.pendingChangeKey && event.key === 'Escape') {
          event.preventDefault();
          event.stopImmediatePropagation();
          return;
        }
        if (
          event.key === 'Enter' &&
          event.target instanceof HTMLInputElement &&
          ['kf-current', 'kf-new', 'kf-confirm'].includes(event.target.id)
        ) {
          event.preventDefault();
          event.stopImmediatePropagation();
          submitChangeKey();
          return;
        }
      }
      const disabled = event.target?.closest?.(
        '[data-pdm-m4-disabled="true"]',
      );
      if (
        disabled &&
        (event.key === 'Enter' || event.key === ' ')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      if (
        event.key === 'Enter' &&
        event.target &&
        (
          event.target.id === 'db-password' ||
          event.target.id === 'db-path'
        )
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        openSelectedDatabase();
        return;
      }
      const lock = event.target.closest?.(
        '[data-pdm-onclick="lockApp()"]',
      );
      if (
        lock &&
        (event.key === 'Enter' || event.key === ' ')
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
        lockDatabase();
      }
    }, true);
  }

  function failClosed() {
    clearRuntimeToasts();
    clearContactSupport();
    runtime.ready = false;
    runtime.state = 'BLOCKED';
    setFeedback(
      'error',
      '',
      '安全连接不可用，候选界面保持锁定。',
      'The secure connection is unavailable. The candidate remains locked.',
    );
    refreshControls();
  }

  function connectBackupSignals(bridge) {
      bridge.chooseBackupDestinationCompletedV1.connect((request, page, session, error, _argument, _retry, result) => {
        onBackupSelection('choose-export', request, page, session, error, result);
      });
      bridge.chooseBackupSourceCompletedV1.connect((request, page, session, error, _argument, _retry, result) => {
        onBackupSelection('choose-import', request, page, session, error, result);
      });
      bridge.previewEncryptedBackupCompletedV1.connect(onBackupPreviewed);
      bridge.listBackupConflictsCompletedV1.connect(onBackupConflictsListed);
      bridge.setBackupConflictDecisionCompletedV1.connect((request, page, session, error, _argument, _retry, result) => {
        onBackupDecisionChanged('decision', request, page, session, error, result);
      });
      bridge.setAllBackupConflictDecisionsCompletedV1.connect((request, page, session, error, _argument, _retry, result) => {
        onBackupDecisionChanged('all-decision', request, page, session, error, result);
      });
      bridge.readBackupConflictFieldChunkCompletedV1.connect(onBackupFieldChunk);
      bridge.readBackupComparisonFieldChunkCompletedV1.connect(onBackupFieldChunk);
      bridge.exportEncryptedBackupCompletedV1.connect(onBackupExported);
      bridge.executeEncryptedBackupImportCompletedV1.connect(onBackupImported);
  }

  function handleBackupAction(target) {
        const action = target.dataset.pdmBackupAction;
        if (action === 'cancel') closeBackupDialog();
        else if (action === 'mode') projectBackupMode(target.dataset.pdmBackupMode);
        else if (action === 'back-setup') {
          const backup = backupState();
          if (!backup || backup.pending) return;
          if (backup.sourceKind === 'TRANSFER') { closeBackupDialog(); return; }
          closeBackupPreview(backup, 'navigation');
          backup.sourceTicket = ''; backup.pathLabel = '';
          byId('ie-path').value = '';
          backup.draft.clear(); backup.retryIdentity = '';
          clearBackupStatus(backup);
          renderBackupPreview(backup);
          byId('ie-browse-btn')?.focus({preventScroll:true});
        }
        else if (action === 'back-passwords') switchBackupStep('PASSWORD');
        else if (action === 'choose') chooseBackupPath();
        else if (action === 'preview') previewBackupImport();
        else if (action === 'execute') executeBackupOperation();
        else if (action === 'decision') setBackupDecision(target, target.dataset.pdmBackupDecision);
        else if (['select-item', 'select-page', 'clear-selection'].includes(action)) changeBackupSelection(target, action);
        else if (action === 'inspect-item') {
          const backup = backupState();
          if (!backup || backup.pending) return;
          const id = target.closest('[data-pdm-backup-conflict-id]').dataset.pdmBackupConflictId;
          if (backup.activeConflictId === id) return;
          backup.activeConflictId = id;
          renderBackupPreview(backup);
        }
        else if (action === 'filter') changeBackupFilter(target.dataset.pdmBackupFilter, backupState()?.fieldFilter || 'ALL');
        else if (action === 'uncompared') changeBackupFilter(backupState()?.statusFilter || 'ALL', 'ALL');
        else if (action === 'batch-confirm') setAllBackupDecisions(target.dataset.pdmBackupDecision);
        else if (action === 'read-field') readBackupConflictField(target);
        else if (action === 'field-previous' || action === 'field-next') navigateBackupField(target, action === 'field-previous');
        else if (action === 'next') {
          const backup = backupState();
          if (backup?.page?.nextCursor) {
            listBackupConflicts(backup, backup.page.nextCursor, false);
          }
        } else if (action === 'previous') {
          const backup = backupState();
          if (backup?.cursors.length) listBackupConflicts(backup, backup.cursors.at(-1), true);
        } else if (action === 'toggle-password') {
          const input = byId(target.dataset.pdmBackupInput);
          if (input instanceof HTMLInputElement) {
            input.type = input.type === 'password' ? 'text' : 'password';
            syncModalPasswordAccessibility(input, target);
          }
        }
  }

  function projectBackupWindowAppearance(projection) {
    if (!projection || !['DARK', 'LIGHT'].includes(projection.effectiveTheme) ||
        !['ZH', 'EN'].includes(projection.language) || !['90','100','110','125'].includes(projection.uiFontScale)) return;
    if (runtime.backup) clearBackupReads(runtime.backup, 'navigation');
    projectProductLanguage(projection.language);
    projectProductTheme(projection.effectiveTheme, projection.effectiveTheme);
    projectUiFontScale(projection.uiFontScale);
    if (runtime.backup) projectBackupMode(runtime.backup.mode);
  }

  function attachBackupWindow() {
    document.documentElement.classList.add('pdm-backup-window');
    window.closeModal = () => closeBackupDialog();
    new QWebChannel(window.qt.webChannelTransport, (channel) => {
      const bridge = channel.objects.pdmBackupV1;
      if (!bridge) return;
      runtime.bridge = bridge;
      connectBackupSignals(bridge);
      bridge.projectionChangedV1.connect(projectBackupWindowAppearance);
      bridge.closeDeferredV1.connect(() => showBackupStatus(runtime.backup,
        fixedText('正在处理，请稍候。', 'Processing. Please wait.'), '#ie-execute-btn'));
      bridge.initializeV1((initial) => {
        if (!Number.isSafeInteger(initial?.pageEpoch) || initial.pageEpoch <= 0 ||
            !Number.isSafeInteger(initial.sessionEpoch) || initial.sessionEpoch <= 0 ||
            !['import','export'].includes(initial.mode) || !['FILE','TRANSFER'].includes(initial.sourceKind) ||
            !isBackupLabel(initial.displayName)) return;
        const received = initial.sourceKind === 'TRANSFER';
        if (received ? initial.mode !== 'import' || !backupPreview(initial.receivedPreview) : initial.receivedPreview !== null) return;
        runtime.pageEpoch = initial.pageEpoch;
        runtime.sessionEpoch = initial.sessionEpoch;
        runtime.ready = true;
        runtime.state = 'UNLOCKED';
        state.connected = true;
        projectBackupWindowAppearance(initial);
        openBackupDialog(initial.mode, initial);
        if (received) adoptBackupPreview(runtime.backup, initial.receivedPreview);
        bridge.presentReadyV1();
      });
    });
    document.addEventListener('click', (event) => {
      const target = event.target?.closest?.('button');
      if (!target) return;
      if (target.dataset.pdmBackupAction) {
        event.preventDefault(); event.stopImmediatePropagation();
        if (!target.disabled && target.dataset.pdmM4Disabled !== 'true') handleBackupAction(target);
      }
    }, {capture:true});
  }

  function clearContactSupport() {
    if (runtime.pendingContact) {
      runtime.pendingContact.button.disabled = false;
      runtime.pendingContact.status.textContent = '';
    }
    runtime.pendingContact = null;
  }

  function normalizeUpdateState(value) {
    const keys = ['autoNotice', 'available', 'currentVersion', 'enabled', 'error',
      'intervalDays', 'lastAttemptMs', 'publishedAt', 'releaseNotes', 'releaseTag',
      'releaseVersion', 'remindAfterMs', 'reminder', 'resultAtMs', 'revision',
      'settingsReady', 'status'];
    if (!hasExactKeys(value, keys)) return null;
    if (!['settingsReady', 'enabled', 'available', 'autoNotice'].every(key => typeof value[key] === 'boolean') ||
        !['revision', 'lastAttemptMs', 'resultAtMs', 'remindAfterMs'].every(key => Number.isSafeInteger(value[key]) && value[key] >= 0) ||
        !Number.isInteger(value.intervalDays) || value.intervalDays < 1 || value.intervalDays > 2147483647 ||
        !['IDLE', 'CHECKING', 'UPDATE_AVAILABLE', 'UP_TO_DATE', 'NO_RELEASE', 'FAILED'].includes(value.status) ||
        !['NONE', 'SETTINGS_UNAVAILABLE', 'SETTINGS_WRITE_FAILED', 'NETWORK', 'TIMEOUT', 'INCOMPLETE', 'INVALID_RESPONSE', 'RATE_LIMITED', 'CANCELLED'].includes(value.error) ||
        !['NORMAL', 'SNOOZED', 'IGNORED'].includes(value.reminder)) return null;
    for (const [key, limit] of [['currentVersion', 32], ['releaseVersion', 32], ['releaseTag', 48], ['publishedAt', 64], ['releaseNotes', 4096]]) {
      if (typeof value[key] !== 'string' || value[key].includes('\0') || recordFieldCharacterCount(value[key], limit) > limit) return null;
    }
    const version = /^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/;
    if (!version.test(value.currentVersion) || (value.releaseVersion && !version.test(value.releaseVersion))) return null;
    if (value.available && (!value.releaseVersion || !value.resultAtMs ||
        !value.publishedAt || !Number.isFinite(Date.parse(value.publishedAt)) ||
        ![ `windows-v${value.releaseVersion}`, ...(value.releaseVersion === '1.0.0' ? ['v1.0.0'] : []) ].includes(value.releaseTag))) return null;
    if (value.autoNotice && !value.available) return null;
    return Object.freeze({...value});
  }

  function acceptUpdateState(pageEpoch, result) {
    if (!runtime.ready || runtime.pageUnloading || pageEpoch !== runtime.pageEpoch) return false;
    const value = normalizeUpdateState(result);
    if (!value || (runtime.updateState && value.revision < runtime.updateState.revision)) return false;
    runtime.updateState = value;
    renderProductUpdates();
    return true;
  }

  function renderProductUpdates() {
    if (window.pdmBackupWindow) return;
    renderUpdateSurfaces(runtime.updateState, {
      ready: runtime.ready && !runtime.pageUnloading && runtime.pageEpoch > 0,
      pending: new Set(runtime.updatePending.keys()), error: runtime.updateError,
    });
    const update = runtime.updateState;
    if (!runtime.ready || !update?.autoNotice || !update.available || !runtime.hostWindowPresentable ||
        document.visibilityState !== 'visible' || !document.hasFocus() || byId('active-modal')) return;
    const key = `${update.releaseTag}:${update.resultAtMs}`;
    if (runtime.updateNoticeKey === key || runtime.updatePending.has('reminder')) return;
    runtime.updateNoticeKey = key;
    showToast(`${updateLabels().notice} (${update.releaseVersion})`, 'info');
    requestProductUpdate('reminder', [update.releaseTag, 'DISMISS'], true);
  }

  const UPDATE_METHODS = {
    state: 'getUpdateStateV1', check: 'checkUpdatesV1', policy: 'setUpdatePolicyV1',
    reminder: 'setUpdateReminderV1', open: 'openUpdateReleaseV1',
  };

  function requestProductUpdate(action, args = [], silent = false) {
    if (!runtime.ready || !runtime.bridge || runtime.pageUnloading || runtime.pageEpoch <= 0 ||
        runtime.updatePending.has(action) || !UPDATE_METHODS[action]) return;
    const method = runtime.bridge[UPDATE_METHODS[action]];
    if (typeof method !== 'function') return;
    const pending = {id: requestId(), page: runtime.pageEpoch, action, args, silent};
    runtime.updatePending.set(action, pending);
    if (!silent && runtime.updateError !== 'intervalInvalid') runtime.updateError = '';
    renderProductUpdates();
    method(pending.id, pending.page, ...args, ack => {
      if (!ack || ack.accepted !== true || ack.errorCode !== 'OK') {
        finishProductUpdate(action, pending.id, pending.page, ack?.errorCode || 'INTERNAL_FAILURE', null);
      }
    });
  }

  function finishProductUpdate(action, request, pageEpoch, errorCode, result) {
    const pending = runtime.updatePending.get(action);
    if (!pending || pending.id !== request || pending.page !== pageEpoch || pageEpoch !== runtime.pageEpoch || runtime.pageUnloading) return;
    runtime.updatePending.delete(action);
    const queued = action === 'policy' ? runtime.queuedUpdatePolicy : null;
    if (action === 'policy') runtime.queuedUpdatePolicy = null;
    const valid = errorCode === 'OK' && (action === 'open' ? hasExactKeys(result, []) : normalizeUpdateState(result));
    const policySaved = action === 'policy' && valid && result.settingsReady &&
      !['SETTINGS_UNAVAILABLE', 'SETTINGS_WRITE_FAILED'].includes(result.error) &&
      result.enabled === pending.args[0] && result.intervalDays === pending.args[1];
    if (!valid) {
      if (!pending.silent) runtime.updateError = action === 'open' ? 'openFailed' : 'requestFailed';
    } else {
      if (!pending.silent && runtime.updateError !== 'intervalInvalid') runtime.updateError = '';
      if (policySaved) {
        const input = document.querySelector('[data-update-days]');
        if (input && ((!result.enabled && !queued) || updateIntervalValue(input.value) === result.intervalDays)) {
          delete input.dataset.updateDirty;
          if (!result.enabled && !queued) input.value = String(result.intervalDays);
          if (runtime.updateError === 'intervalInvalid') runtime.updateError = '';
        }
      }
      if (action !== 'open') acceptUpdateState(pageEpoch, result);
    }
    if (policySaved && queued) submitUpdatePolicy(...queued);
    renderProductUpdates();
  }

  function updatePolicyIntent() {
    const update = runtime.updateState;
    return runtime.queuedUpdatePolicy || runtime.updatePending.get('policy')?.args || [update.enabled, update.intervalDays];
  }

  function submitUpdatePolicy(enabled, days) {
    if (!runtime.ready || runtime.pageUnloading || !runtime.updateState?.settingsReady) return;
    const pending = runtime.updatePending.get('policy');
    if (pending) {
      // 沿生成器的最新意图队列，避免失焦保存吞掉紧接的开关或二次输入。
      runtime.queuedUpdatePolicy = enabled === pending.args[0] && days === pending.args[1] ? null : [enabled, days];
      return;
    }
    if (enabled === runtime.updateState.enabled && days === runtime.updateState.intervalDays &&
        runtime.updateState.error !== 'SETTINGS_WRITE_FAILED') {
      const input = document.querySelector('[data-update-days]');
      if (input && updateIntervalValue(input.value) === days) delete input.dataset.updateDirty;
      renderProductUpdates();
      return;
    }
    requestProductUpdate('policy', [enabled, days]);
  }

  function saveProductUpdateInterval(input) {
    if (input.disabled || !runtime.ready || !runtime.updateState?.settingsReady || document.hidden) return;
    const days = updateIntervalValue(input.value);
    if (days === null) {
      runtime.updateError = 'intervalInvalid'; renderProductUpdates(); return;
    }
    runtime.updateError = '';
    submitUpdatePolicy(updatePolicyIntent()[0], days);
  }

  function handleProductUpdate(button) {
    if (!runtime.ready || button.disabled || button.dataset.pdmM4Disabled === 'true' || document.hidden) return;
    const action = button.dataset.updateAction, update = runtime.updateState;
    if (action === 'details') {
      switchProductView('help');
      if (state.currentNav === 'help') {
        window.selectHelp?.('about');
        const details = document.querySelector('#page-help .update-release');
        if (details && !details.hidden) { details.open = true; details.scrollIntoView({block: 'nearest'}); }
      }
      return;
    }
    if (action === 'check') return requestProductUpdate('check');
    if (action === 'toggle' && update?.settingsReady) {
      const [enabled, days] = updatePolicyIntent();
      return submitUpdatePolicy(!enabled, days);
    }
    if (!update?.available) return;
    if (action === 'open') return requestProductUpdate('open', [update.releaseTag]);
    if (action === 'snooze' || action === 'ignore') requestProductUpdate('reminder', [update.releaseTag, action === 'snooze' ? 'SNOOZE' : 'IGNORE']);
  }

  function requestContactSupport(button) {
    if (!runtime.ready || !runtime.bridge || runtime.pendingContact ||
        !['LOCKED', 'UNLOCKED'].includes(runtime.state) || state.currentNav !== 'help' ||
        document.visibilityState !== 'visible' || button.disabled) return;
    const status = byId('help-contact-status');
    if (!status) return;
    const pending = {id: requestId(), page: runtime.pageEpoch, session: runtime.sessionEpoch, button, status};
    runtime.pendingContact = pending;
    button.disabled = true;
    status.textContent = '';
    runtime.bridge.contactSupportV1(pending.id, pending.page, (ack) => {
      if (!ack?.accepted) finishContactSupport(pending.id, pending.page, false);
    });
  }

  function finishContactSupport(request, pageEpoch, succeeded) {
    const pending = runtime.pendingContact;
    if (!pending || pending.id !== request || pending.page !== pageEpoch) return;
    runtime.pendingContact = null;
    pending.button.disabled = false;
    if (!runtime.ready || runtime.pageEpoch !== pending.page || runtime.sessionEpoch !== pending.session ||
        state.currentNav !== 'help' || !pending.status.isConnected) return;
    pending.status.textContent = succeeded
      ? fixedText('已请求打开交流群，请入群后联系管理员。', 'Requested opening the group. Join and contact an administrator.')
      : fixedText('未能请求打开交流群，请重试或使用上方群地址。', 'Could not request opening the group. Retry or use the group address above.');
  }

  function attachBridge() {
    if (
      typeof QWebChannel !== 'function' ||
      !window.qt ||
      !window.qt.webChannelTransport
    ) {
      failClosed();
      return;
    }
    new QWebChannel(window.qt.webChannelTransport, (channel) => {
      const bridge = channel.objects.pdmBridgeV1;
      const editorLauncher = channel.objects.pdmEditorLauncherV1;
      if (!bridge || !editorLauncher) {
        failClosed();
        return;
      }
      runtime.bridge = bridge;
      runtime.editorLauncher = editorLauncher;
      runtime.backupLauncher = channel.objects.pdmBackupLauncherV1;
      runtime.transferLauncher = channel.objects.pdmTransferLauncherV1;
      runtime.backupLauncher?.operationCompletedV1.connect((pageEpoch, sessionEpoch, kind, result) => {
        if (runtime.state !== 'UNLOCKED' || pageEpoch !== runtime.pageEpoch || sessionEpoch !== runtime.sessionEpoch) return;
        if (kind === 'IMPORT' && isBackupImportResult(result)) {
          if (!result.changed) {
            showToast(t('toast.ie.no_changes'), 'info');
            return;
          }
          resetVaultPagePosition(); requestVaultPage();
          if (state.currentNav === 'notes') { resetNotePagePosition(); requestNotePage(); }
          if (state.currentNav === 'security') requestHealth();
          showToast(t('toast.ie.imported').replace('{added}', String(result.imported))
            .replace('{updated}', String(result.overwritten)).replace('{skipped}', String(result.skipped)), 'success');
        } else if (kind === 'EXPORT' && isBackupExportResult(result)) {
          showToast(t('toast.ie.exported').replace('{n}', String(result.passwordCount + result.noteCount))
            .replace('{file}', result.backupLabel), 'success');
        }
      });
      editorLauncher.editorFinishedV1.connect(onIndependentEditorFinished);
      bridge.handshakeCompletedV1.connect(onHandshake);
      bridge.contactSupportCompletedV1.connect((request, page, _session, error, _argument, _retry, result) => {
        finishContactSupport(request, page, error === 'OK' && hasExactKeys(result, []));
      });
      for (const [action, method] of Object.entries(UPDATE_METHODS)) {
        bridge[method.replace('V1', 'CompletedV1')].connect((request, page, _session, error, _argument, _retry, result) => {
          finishProductUpdate(action, request, page, error, result);
        });
      }
      bridge.updateStateChangedV1.connect(acceptUpdateState);
      bridge.chooseDatabaseTargetCompletedV1.connect(onTargetChosen);
      bridge.selectRecentDatabaseCompletedV1.connect(onRecentSelected);
      bridge.removeRecentDatabaseCompletedV1.connect(onRecentRemoved);
      bridge.openDatabaseCompletedV1.connect(onDatabaseOpened);
      bridge.lockCompletedV1.connect(onLocked);
      bridge.openQuickbarCompletedV1.connect(onQuickbarOpened);
      bridge.listVaultSummariesCompletedV1.connect(onVaultListed);
      bridge.locateVaultRecordCompletedV1.connect(onHealthLocated);
      bridge.locateVaultAnchorCompletedV1.connect(onRatingVaultLocated);
      bridge.getRecordDetailsCompletedV1.connect(onRecordDetails);
      bridge.updateRecordCompletedV1.connect(onRecordUpdated);
      bridge.updateRecordFieldsCompletedV1.connect((request, page, session, error, argument, retry, result) => {
        const originalArgument = {8: 7, 10: 8, 11: 9, 12: 10, 14: 11, 15: 12, 16: 13, 17: 14}[argument] || argument;
        onRecordUpdated(request, page, session, error, originalArgument, retry, result);
      });
      bridge.readRecordFieldChunkCompletedV1.connect(onRecordFieldChunk);
      bridge.getRecordTotpCodeCompletedV1.connect(onRecordTotpCode);
      bridge.copyRecordTotpCompletedV1.connect(onRecordTotpCopied);
      bridge.revealRecoveryCodeCompletedV1.connect(onRecoveryCodeRevealed);
      bridge.copyRecoveryCodeCompletedV1.connect(onRecoveryCodeCopied);
      bridge.setRecoveryCodeUsedCompletedV1.connect(onRecoveryCodeUsed);
      bridge.setRecordFavoriteCompletedV1.connect(onRecordFavoriteSet);
      bridge.prepareDeleteRecordCompletedV1.connect(onDeletePrepared);
      bridge.deleteRecordCompletedV1.connect(onRecordDeleted);
      bridge.getHealthSummaryCompletedV1.connect(onHealthSummary);
      bridge.getHealthOverviewAtCompletedV1.connect(onHealthOverview);
      bridge.getHealthGuidancePageCompletedV1.connect(onHealthGuidancePage);
      bridge.listHealthIssuesCompletedV1.connect(onHealthIssues);
      bridge.startHealthRescanCompletedV1.connect(onHealthRescan);
      bridge.getHealthRescanStatusCompletedV1.connect(onHealthRescan);
      bridge.cancelHealthRescanCompletedV1.connect(onHealthRescan);
      bridge.generatePasswordCompletedV1.connect(onPasswordGenerated);
      bridge.checkPasswordStrengthCompletedV1.connect(onPasswordStrengthChecked);
      bridge.copyGeneratedPasswordCompletedV1.connect(onGeneratedPasswordCopied);
      bridge.revealRecordPasswordCompletedV1.connect(
        onRecordPasswordRevealed,
      );
      bridge.copyRecordAccountCompletedV1.connect(
        onRecordAccountCopied,
      );
      bridge.copyRecordPasswordCompletedV1.connect(
        onRecordPasswordCopied,
      );
      bridge.clearClipboardCompletedV1.connect(onClipboardCleared);
      bridge.listNoteSummariesCompletedV1.connect(onNotesListed);
      bridge.getNoteCompletedV1.connect(onNoteDetails);
      bridge.readNoteFieldChunkCompletedV1.connect(onNoteFieldChunk);
      bridge.setNoteFavoriteCompletedV1.connect(onNoteFavoriteSet);
      bridge.changeDatabasePasswordCompletedV1.connect(
        onChangeKeyCompleted,
      );
      connectBackupSignals(bridge);
      bridge.setThemeCompletedV1.connect(onThemeSet);
      bridge.setLanguageCompletedV1.connect(onLanguageSet);
      bridge.setUiFontScaleCompletedV1.connect(onUiFontScaleSet);
      bridge.setStartupAutofillCompletedV1.connect(onStartupAutofillSet);
      bridge.setDefaultViewCompletedV1.connect(onDefaultViewSet);
      bridge.setSidebarTextCompletedV1.connect(onSidebarTextSet);
      bridge.setSortModeCompletedV1.connect(onSortModeSet);
      bridge.setClipboardPolicyCompletedV1.connect(onClipboardPolicySet);
      bridge.setCloseBehaviorCompletedV1.connect(onCloseBehaviorSet);
      bridge.setQuickbarEnabledCompletedV1.connect(onQuickbarEnabledSet);
      bridge.setQuickbarHotkeyCompletedV1.connect(onQuickbarHotkeySet);
      bridge.setStaleThresholdCompletedV1.connect(onStaleThresholdSet);
      bridge.setAutoLockPolicyCompletedV1.connect(onAutoLockPolicySet);
      bridge.setPasswordGeneratorDefaultsCompletedV1.connect(
        onPasswordGeneratorDefaultsSet,
      );
      bridge.sessionStateChangedV1.connect(onSessionStateChanged);
      bridge.settingsChangedV1.connect(onSettingsChanged);
      bridge.systemThemeChangedV1.connect(onSystemThemeChanged);
      bridge.dataRevisionChangedV1.connect(
        onIndependentEditorDataChanged,
      );
      bridge.retryRecordStrengthCompletedV1.connect(onStrengthRetried);
      bridge.requestProgressV1.connect(onRequestProgress);
      bridge.clipboardStateChangedV1.connect(onClipboardStateChanged);
      const id = requestId();
      runtime.pendingHandshake = id;
      bridge.handshakeV1(
        id,
        requestId(),
        CONTRACT_VERSION,
        (ack) => acknowledge(ack, 'pendingHandshake', id),
      );
    });
  }

  function normalizeGeneratedPasswordLease(result) {
    if (
      !result ||
      typeof result.secretLeaseId !== 'string' ||
      !/^[A-Za-z0-9_-]{16,64}$/.test(result.secretLeaseId) ||
      typeof result.password !== 'string' ||
      result.password.length < 1 ||
      recordFieldCharacterCount(result.password) > 1024 ||
      !recordFieldFits('PASSWORD', result.password) ||
      !Number.isSafeInteger(result.expiresInMs) ||
      result.expiresInMs < 1 ||
      result.expiresInMs > 300000
    ) {
      return null;
    }
    return {
      secretLeaseId: result.secretLeaseId,
      password: result.password,
      expiresInMs: result.expiresInMs,
    };
  }

  window.addEventListener('focus', (event) => {
    if (event.isTrusted) renderProductUpdates();
  });

  document.addEventListener('visibilitychange', () => {
    syncRecentTimeRefresh();
    if (TOAST_PRESENTATION_AVAILABLE) {
      setToastPresentationVisible(
        runtime.hostWindowPresentable && document.visibilityState === 'visible',
      );
    }
    renderProductUpdates();
    syncHealthRescanPolling(!document.hidden);
    if (!document.hidden) {
      refreshHealthRescanSummary();
      queueRatingRefresh();
      if (runtime.backup) loadBackupComparisonFields(runtime.backup);
    }
    if (document.hidden) {
      if (runtime.backup) clearBackupReads(runtime.backup, 'navigation');
      stopRecordTotp();
    } else if (runtime.state === 'UNLOCKED' && state.currentNav === 'vault' && runtime.selectedDetails?.hasTotp) {
      const value = Array.from(document.querySelectorAll('#page-vault .detail-value.totp'))
        .find((element) => element.getClientRects().length > 0);
      if (value) startRecordTotp(runtime.selectedDetails, value.querySelector('.text'),
        value.querySelector('.totp-ring'), value.querySelector('.btn-sm'));
    }
  });

  window.addEventListener(
    'pagehide',
    () => {
      clearRuntimeToasts();
      runtime.hostWindowPresentable = false;
      runtime.pageUnloading = true;
      stopRecentTimeRefresh();
      if (TOAST_PRESENTATION_AVAILABLE) setToastPresentationVisible(false);
      if (activeBackupModal()) {
        closeBackupDialog('page_unload', true);
      }
      runtime.ready = false;
      runtime.state = 'LOCKED';
      runtime.pageEpoch = 0;
      runtime.sessionEpoch = 0;
      runtime.updateState = null;
      runtime.updatePending.clear();
      runtime.queuedUpdatePolicy = null;
      runtime.updateError = '';
      runtime.updateNoticeKey = '';
      clearContactSupport();
      runtime.lockedNotice = '';
      runtime.selectionTicket = '';
      runtime.pendingChoose = '';
      runtime.openAfterChoose = false;
      runtime.pendingRecent = '';
      runtime.pendingRecentEntry = null;
      runtime.pendingRemove = '';
      runtime.pendingRemoveIndex = -1;
      runtime.pendingRemoveFocusKey = '';
      runtime.pendingDetails = '';
      runtime.pendingDetailsTarget = null;
      runtime.queuedDetailsTarget = null;
      runtime.retiredDetailsRequest = '';
      runtime.pendingAccountCopy = '';
      runtime.pendingPasswordCopy = '';
      runtime.pendingClipboardClear = '';
      runtime.pendingCreate = '';
      runtime.pendingGenerate = '';
      runtime.pendingGeneratedCopy = '';
      runtime.pendingStrength = '';
      runtime.pendingStrengthVersion = 0;
      runtime.generateTarget = '';
      runtime.toolGeneratedLeaseId = '';
      runtime.toolGeneratedElement = null;
      runtime.formGeneratedLeaseId = '';
      runtime.formGeneratedElement = null;
      runtime.createModalActive = false;
      clearCreateCooldown();
      runtime.pendingEditOpen = '';
      runtime.editOpenPurpose = '';
      runtime.editOpenRecordId = 0;
      runtime.editOpenRevision = '';
      runtime.pendingEditSave = '';
      runtime.editSubmittedLeaseId = '';
      runtime.editModalActive = false;
      runtime.editRecordId = 0;
      runtime.editRevision = '';
      runtime.editLeaseId = '';
      runtime.editHasTotp = false;
      runtime.editTotpAction = 'KEEP';
      runtime.editPasswordDirty = false;
      runtime.editConflict = false;
      runtime.editReloadRevision = '';
      runtime.editGenerateAfterOpen = false;
      clearEditCooldown();
      runtime.pendingDeletePrepare = '';
      runtime.pendingDeleteCommit = '';
      runtime.deleteModalActive = false;
      runtime.deleteRecordId = 0;
      runtime.deleteRevision = '';
      runtime.deleteLabel = '';
      runtime.clipboardKind = 'NONE';
      runtime.clipboardRemaining = 0;
      runtime.clipboardOwned = false;
      clearVaultAuthority();
      clearHealthAuthority();
      if (activeNoteCreateModal()) {
        scrubNoteCreateForm();
      }
      runtime.pendingNoteCreate = '';
      runtime.noteCreateModalActive = false;
      clearNoteCreateCooldown();
      clearNoteAuthority();
      if (activeChangeKeyModal()) {
        scrubChangeKeyForm('page_unload');
      }
      runtime.pendingChangeKey = '';
      runtime.changeKeyModalActive = false;
      clearChangeKeyCooldown();
      resetChangeKeyProgress();
      clearPendingTheme();
      clearPendingLanguage();
      clearPendingUiFontScale();
      clearPendingStartupAutofill();
      clearPendingDefaultView();
      clearPendingSidebarText();
      clearPendingClipboardPolicy();
      clearPendingSort();
      cancelFieldReads();
      stopRecordTotp();
      runtime.editorFieldMeta = null;
      clearPendingClose();
      clearPendingAutoLock();
      clearPendingGeneratorDefaults();
      runtime.queuedGeneratorPolicy = null;
      runtime.generatorGenerateAfterSaveKey = '';
      runtime.pendingQuickbarOpen = '';
      clearPendingQuickbarEnabled();
      clearPendingQuickbarHotkey();
      runtime.hotkeyRecording = false;
      runtime.settingsRevision = '';
      runtime.settings = null;
      runtime.projectedSettingsSignals = [];
      if (window.pdmSensitiveDom) {
        window.pdmSensitiveDom.clearAll('page_unload');
      }
    },
    {capture: true},
  );

  window.renderVault = renderM4Vault;
  window.fixAll = startHealthGuidance;
  window.renderNotes = renderM4Notes;
  window.setNoteFilter = setProductNoteFilter;
  window.openAddNoteDialog = openCreateNoteDialog;
  window.saveNewNote = undefined;
  window.openAddPasswordDialog = openCreateRecordDialog;
  window.saveNewPassword = undefined;
  window.openEditPasswordDialog = (recordId) => {
    const record = (
      runtime.selectedDetails?.recordId === recordId
        ? runtime.selectedDetails
        : runtime.vaultItems.find((item) => item.recordId === recordId)
    );
    if (record) requestRecordEditor(record, 'initial', false);
  };
  window.saveEditPassword = undefined;
  window.deleteRecord = (recordId) => {
    const record = (
      runtime.selectedDetails?.recordId === recordId
        ? runtime.selectedDetails
        : runtime.vaultItems.find((item) => item.recordId === recordId)
    );
    if (record) openDeleteRecordDialog(record);
  };
  window.confirmDeleteRecord = submitDeleteRecord;
  window.openChangeDbPasswordDialog = openChangeKeyDialog;
  window.confirmChangeDbPassword = submitChangeKey;
  window.fillModalGeneratedPassword = (inputId) => {
    if (inputId === 'kf-new') requestGeneratedPassword('change-key');
  };
  window.generatePassword = () => {
    requestGeneratedPassword('tool');
  };
  window.switchTool = switchProductTool;
  window.saveGenerated = moveGeneratedPasswordToCreate;
  window.copyGenerated = copyGeneratedPassword;
  window.toggleGeneratorAvoid = toggleGeneratorAvoid;
  window.clampGenLength = clampGeneratorLength;
  window.checkStrength = onStrengthInputChanged;
  window.closeModal = closeProductModal;
  window.setTheme = requestProductTheme;
  window.setUiFontScale = requestProductUiFontScale;
  window.toggleTheme = requestProductThemeShortcut;
  window.setLang = requestProductLanguage;
  window.toggleLang = requestProductLanguage;
  window.toggleAutoLock = requestProductAutoLockToggle;
  window.syncAutoLockTimeout = requestProductAutoLockMinutes;
  window.openImportExportDialog = openBackupDialog;
  window.openDirectTransferDialog = openDirectTransferDialog;
  window.openQuickBar = requestQuickbarOpen;
  window.clearGlobalSearch = clearProductGlobalSearch;
  window.startHotkeyRecording = startProductHotkeyRecording;
  window.renderUpdates = renderProductUpdates;
  resetDemoAuthority();
  if (window.pdmBackupWindow) {
    attachBackupWindow();
    return;
  }
  projectProductLanguage('ZH');
  projectProductTheme('DARK', 'DARK');
  // 首次连接页也在原生加载面后构造静态终态，避免揭幕后继续入场。
  document.documentElement.classList.add('pdm-security-lock-handoff-static');
  applyLocked('');
  bindEvents();
  attachBridge();
})();
