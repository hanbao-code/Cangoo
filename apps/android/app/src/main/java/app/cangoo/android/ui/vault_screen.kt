package app.cangoo.android.ui

import android.hardware.biometrics.BiometricManager
import android.icu.text.BreakIterator

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.gestures.LocalBringIntoViewSpec
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.contextmenu.provider.LocalTextContextMenuDropdownProvider
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import app.cangoo.android.R
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.semantics.disabled
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.PointerEventType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.platform.LocalClipboard
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalAccessibilityManager
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.ParagraphStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.input.TransformedText
import androidx.compose.ui.text.input.OffsetMapping
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.SecureFlagPolicy
import app.cangoo.android.data.PasswordRecord
import app.cangoo.android.data.NoteRecord
import app.cangoo.android.data.VaultInfo
import app.cangoo.android.data.BackupProtocol
import kotlinx.coroutines.launch

private val Paper: Color
    @Composable get() = LocalBThemeColors.current.paper
private val Card: Color
    @Composable get() = LocalBThemeColors.current.surface
private val Ink: Color
    @Composable get() = LocalBThemeColors.current.ink
private val Muted: Color
    @Composable get() = LocalBThemeColors.current.muted
private val Line: Color
    @Composable get() = LocalBThemeColors.current.line
private val Soft: Color
    @Composable get() = LocalBThemeColors.current.soft
private val Accent: Color
    @Composable get() = LocalBThemeColors.current.accentInk
private val Error: Color
    @Composable get() = LocalBThemeColors.current.error
private val ProtectedDialog = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn)

@Composable
@OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)
internal fun CangooApp(model: VaultModel, contentVisible: Boolean, onLeave: () -> Unit, onSystemAppearance: (Boolean, Int) -> Unit = { _, _ -> },
                       onOpenSystemSettings: (SystemSettingsDestination) -> Boolean = { true },
                       onOpenContact: () -> Boolean = { false },
                       onOpenRelease: () -> Boolean = { false },
                        onStartTransfer: () -> Unit = {},
                        onTransferSettings: (DirectTransferSettings) -> Unit = {},
                       onChooseBackupFile: (BackupDocumentKind, Long) -> Unit) {
    LocalizedContent(model.uiPreferences.language) {
        CangooContent(model, contentVisible, onLeave, onSystemAppearance, onOpenSystemSettings, onOpenContact, onOpenRelease,
            onStartTransfer, onTransferSettings, onChooseBackupFile)
    }
}

@Composable
@OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)
private fun CangooContent(model: VaultModel, contentVisible: Boolean, onLeave: () -> Unit, onSystemAppearance: (Boolean, Int) -> Unit,
                          onOpenSystemSettings: (SystemSettingsDestination) -> Boolean,
                          onOpenContact: () -> Boolean,
                          onOpenRelease: () -> Boolean,
                           onStartTransfer: () -> Unit,
                           onTransferSettings: (DirectTransferSettings) -> Unit,
                          onChooseBackupFile: (BackupDocumentKind, Long) -> Unit) {
    val texts = LocalResources.current
    val guide = model.systemGuideVisible
    val state = if (guide) model.state.copy(page = Page.SYSTEM_ACCESS) else model.state
    LaunchedEffect(guide, model.state.busy) { if (guide && !model.state.busy) model.refreshSystemAccess() }
    val presentationPage = if (state.page == Page.NOTE_EDIT) Page.NOTE_DETAIL else state.page
    val uiPreferences = model.uiPreferences
    var helpSection by remember(state.page == Page.HELP) { mutableStateOf("menu") }
    var helpLicense by remember(state.page == Page.HELP) { mutableStateOf<String?>(null) }
    val helpScrollStates = remember(state.page == Page.HELP) { mutableMapOf<String, ScrollState>() }
    val editGeneration = model.editGeneration
    val clipboard = LocalClipboard.current
    val publishingClipboard = remember(model, clipboard, state.page, state.vault?.id, editGeneration) {
        PublishingClipboard(clipboard, model.frameworkClipboard(state.page, state.vault?.id, editGeneration))
    }
    SideEffect { model.observeContentVisible(contentVisible) }
    DisposableEffect(model) { onDispose { model.observeContentVisible(false) } }
    val focus = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val imeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0
    val root = state.page in listOf(Page.HOME, Page.PASSWORDS, Page.TOOLS, Page.SETTINGS)
    val listStates = remember(state.vault?.id, state.unlocked) { mutableMapOf<Page, LazyListState>() }
    val listState = listStates.getOrPut(state.page) { LazyListState() }
    val queryFocus = remember(state.vault?.id, state.unlocked) { FocusRequester() }
    var focusedSearchOpening by remember(state.vault?.id, state.unlocked) { mutableLongStateOf(-1L) }
    val formScrollStates = remember(state.vault?.id, state.unlocked) { mutableMapOf<Page, ScrollState>() }
    // 返回列表会清记录，重新选择从顶开始；编辑往返和短暂离开保本次阅读。
    val recordScrollStates = remember(state.vault?.id, state.unlocked, state.record?.id, state.note?.id) {
        mutableMapOf<Page, ScrollState>()
    }
    val formScrollState = when (state.page) {
        Page.HELP -> helpScrollStates.getOrPut("$helpSection/${helpLicense.orEmpty()}") { ScrollState(0) }
        Page.DETAIL, Page.EDIT, Page.NOTE_DETAIL, Page.NOTE_EDIT -> recordScrollStates.getOrPut(presentationPage) { ScrollState(0) }
        // 新表单随本次页面存在；同页草稿、弹层和短暂离开保持位置。
        Page.CREATE, Page.RENAME, Page.MASTER, Page.BIOMETRIC, Page.ADD, Page.NOTE_ADD ->
            remember(state.vault?.id, state.unlocked, state.page) { ScrollState(0) }
        else -> formScrollStates.getOrPut(state.page) { ScrollState(0) }
    }
    val noteCursor = remember(state.vault?.id, state.note?.id, state.unlocked) { NoteCursorVisibility() }
    val originalBringSpec = LocalBringIntoViewSpec.current
    val noteBringSpec = remember(noteCursor, originalBringSpec) { noteCursor.resizeSpec(originalBringSpec) }
    val notePage = state.page == Page.NOTE_DETAIL || state.page == Page.NOTE_EDIT
    val accessibility = LocalAccessibilityManager.current
    fun back() {
        focus.clearFocus()
        if (guide) { model.finishSystemGuide(); return }
        if (state.page == Page.HELP && helpLicense != null) { helpLicense = null; return }
        if (state.page == Page.HELP && helpSection != "menu") {
            helpSection = when (helpSection) { "licenses" -> "about"; "agpl", "openssl", "terms_licenses" -> "terms"; else -> "menu" }
            return
        }
        val timeout = accessibility?.calculateRecommendedTimeoutMillis(2000L, containsText = true, containsControls = true) ?: 2000L
        if (model.back(timeout.coerceAtLeast(2000L))) onLeave()
    }
    BackHandler(enabled = contentVisible && !imeVisible) { back() }
    LaunchedEffect(formScrollState.isScrollInProgress) {
        if (formScrollState.isScrollInProgress) model.exitConfirmation.cancel()
    }
    LaunchedEffect(presentationPage, state.unlocked, state.showVaults) {
        focus.clearFocus()
        // 结束编辑焦点不保证输入法收起，锁定落点须同时结束键盘呈现。
        if (presentationPage == Page.LOCKED || presentationPage == Page.VAULTS) keyboard?.hide()
    }
    LaunchedEffect(state.page) { if (state.page == Page.NOTE_DETAIL) focus.clearFocus() }
    LaunchedEffect(state.vault?.id, state.unlocked) { listState.scrollToItem(0) }
    LaunchedEffect(state.browseRun) { listState.scrollToItem(0) }
    CompositionLocalProvider(LocalClipboard provides publishingClipboard) {
    CangooTheme(uiPreferences) {
        val dark = uiPreferences.isDark(isSystemInDarkTheme())
        val systemPaper = Paper.toArgb()
        SideEffect { onSystemAppearance(dark, systemPaper) }
        if (!contentVisible) {
            Box(Modifier.fillMaxSize().background(Paper))
            return@CangooTheme
        }
        Column(Modifier.fillMaxSize().background(Paper).safeDrawingPadding().imePadding()) {
            if (state.page == Page.SEARCH) SearchToolbar(state, model, queryFocus, onBack = { back() }) {
                if (focusedSearchOpening != state.searchOpening && model.state.page == Page.SEARCH && model.editGeneration == editGeneration) {
                    focusedSearchOpening = state.searchOpening
                    queryFocus.requestFocus()
                }
            }
            else if (state.page == Page.HOME || state.page == Page.PASSWORDS) BLookupToolbar(state.busy, model::startSearch, model::showAdd) { model.lock() }
            else if (state.page != Page.LOCKED) Header(state, onBack = { back() }, onAdd = model::showAdd,
                titleOverride = if (state.page == Page.HELP) texts.getString(when (helpSection) {
                    "manual" -> R.string.help_manual; "terms" -> R.string.help_terms; "about" -> R.string.help_about
                    "licenses" -> R.string.third_party_licenses; "terms_licenses" -> R.string.terms_third_party_notices
                    "agpl" -> R.string.terms_full_license; "openssl" -> R.string.terms_openssl_permission; else -> R.string.help
                }) else null,
                onLock = { model.lock() }, onSettings = model::openSecuritySettings, onEdit = {
                    state.record?.let { model.startSecretEdit(state.vault?.id.orEmpty(), it.id, it.revision, editGeneration) }
                }, onDeleteNote = {
                    state.note?.let { model.requestNoteDelete(state.vault?.id, it.id, it.revision, editGeneration) }
                })
            if (state.page != Page.SECURITY && model.securitySettingsError.isNotEmpty()) {
                Text(model.securitySettingsError, Modifier.padding(horizontal = 24.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = Error, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp))
            }
            Box(Modifier.weight(1f).fillMaxWidth()) {
                if (state.page == Page.HOME) {
                    val entries = state.passwords.map { HomeEntry(it.id, it.title, it.account, false, it.favorite) } + state.notes.map { HomeEntry(it.id, it.title, it.preview, true, it.favorite) }
                    val favorites = entries.filter { it.favorite }
                    BHomeContent(favorites, state.recentKeys.mapNotNull { key -> entries.firstOrNull { it.id == key.first && it.isNote == key.second } },
                        state.checks.warningIds.size, if (state.checksAvailable) state.checks.checkedCount else -1, state.busy,
                        onRecord = { id, note -> if (note) model.openNote(id) else model.openRecord(id) },
                        onFavorites = model::showFavorites, onLibrary = { model.selectRoot(Page.PASSWORDS) }, onWarnings = model::showChecks,
                        scrollState = formScrollState, contextPresent = state.vaults.size > 1, pendingCount = state.checks.pendingEpochs.size, topContent = {
                            if (state.vaults.size > 1) BVaultContext(state.vault?.name.orEmpty(), state.busy, model::showVaults)
                            Feedback(state)
                        })
                } else if (state.page == Page.TRANSFER) {
                    model.directTransfer?.let { controller ->
                        BDirectTransferPage(controller, onStartTransfer, model::closeDirectTransfer, onTransferSettings,
                            Modifier.fillMaxSize(), model::copyTransferPairingCode)
                    }
                } else if (state.page == Page.CHECKS) {
                    ChecksPage(state, listState, model)
                } else if (state.page == Page.PASSWORDS || state.page == Page.SEARCH) {
                    PasswordList(state, listState, model)
                } else if (state.page == Page.GENERATOR) {
                    BGeneratorPage(state.generatorOptions, state.generated, state.busy || model.uiPreferencesSaving,
                        onOptions = { model.updateGeneratorOptions(it, editGeneration) }, onGenerate = model::generate,
                        onUse = { model.useGenerated(it, editGeneration) }, error = state.error.ifEmpty { state.notice }.localized(), expanded = state.generatedExpanded,
                        onExpanded = { model.expandGenerated(it, editGeneration) }, scrollState = formScrollState,
                        fontScale = uiPreferences.fontScale, onCopy = { model.copyGenerated(editGeneration) })
                } else key(presentationPage, state.vault?.id) {
                    CompositionLocalProvider(LocalBringIntoViewSpec provides if (notePage) noteBringSpec else originalBringSpec) {
                        Column(
                            Modifier.fillMaxSize()
                                .then(if (notePage) Modifier.onGloballyPositioned { noteCursor.viewportCoordinates = it } else Modifier)
                                .verticalScroll(formScrollState).padding(horizontal = 24.dp, vertical = 8.dp),
                            verticalArrangement = Arrangement.spacedBy(20.dp),
                        ) {
                            CompositionLocalProvider(LocalBringIntoViewSpec provides originalBringSpec) {
                                when (state.page) {
                                    Page.VAULTS, Page.VAULT_MANAGEMENT -> VaultList(state, model)
                                    Page.CREATE -> CreateVault(state, model)
                                    Page.RENAME -> RenameVault(state, model)
                                    Page.MASTER, Page.BIOMETRIC -> Column {
                                        if (state.vaults.size > 1) BVaultNameContext(model, state.page, editGeneration)
                                        Column(verticalArrangement = Arrangement.spacedBy(20.dp)) {
                                            if (state.page == Page.MASTER) MasterPasswordPage(state, model)
                                            else BiometricSettingsPage(state, model)
                                        }
                                    }
                                    Page.VAULT_DELETE -> model.deletionState.target?.let { target ->
                                        val deletion = model.deletionState
                                        BVaultDeletionPage(deletion.preview?.name ?: target.name, target.hasMasterPassword, deletion.preview, state.busy,
                                            inputSlot = { FormField(texts.getString(R.string.vault_master), deletion.master, { model.updateDeletionMaster(it, editGeneration) },
                                                required = model.deletionState.target?.hasMasterPassword == true, enabled = !state.busy, secret = true, placeholder = if (target.hasMasterPassword) texts.getString(R.string.vault_master_hint) else texts.getString(R.string.empty_to_verify)) })
                                    }
                                    Page.LOCKED -> UnlockVault(state, model)
                                    Page.ADD, Page.EDIT -> AddPassword(state, model)
                                    Page.DETAIL, Page.NOTE_DETAIL, Page.NOTE_EDIT -> Column {
                                        if (state.vaults.size > 1) BVaultNameContext(model, state.page, editGeneration)
                                        if (state.page == Page.DETAIL) state.record?.let { RecordDetail(it, state.passwordShown, model) }
                                        else state.note?.let { NoteDetail(it, model, noteCursor) }
                                    }
                                    Page.NOTE_ADD -> EditNote(state, model)
                                    Page.SECURITY -> SettingsPage(model, onOpenRelease)
                                    Page.BACKUP -> BBackupPage(model, onChooseBackupFile)
                                    Page.HELP -> BHelpPage(helpSection, helpLicense, { helpSection = it }, { helpLicense = it },
                                        uiPreferences.language, model.uiPreferencesSaving, model.uiPreferencesError,
                                        onLanguage = { model.updateUiPreferences(uiPreferences.copy(language = it), uiPreferences, Page.HELP, editGeneration) },
                                        onContact = { model.onUserInteraction() && onOpenContact() }, updates = model.updates,
                                        onOpenRelease = { model.onUserInteraction() && onOpenRelease() },
                                        updateDialogModifier = Modifier.recordDialogInteraction(model))
                                    Page.SYSTEM_ACCESS -> SystemAccessPage(model.systemAccessSnapshot, guide) {
                                        if (model.prepareSystemSettings()) onOpenSystemSettings(it) else true
                                    }
                                    Page.STRENGTH -> BPasswordStrengthPage(
                                        shown = state.passwordShown, hasInput = state.strengthInput.isNotEmpty(), overLimit = state.strengthInput.codePointCount(0, state.strengthInput.length) > 1024,
                                        result = state.strengthResult, pending = state.strengthPending, error = state.error.localized(),
                                        onReveal = { model.togglePassword(editGeneration, Page.STRENGTH, state.record?.id) },
                                        onClear = { model.updateStrengthInput("", editGeneration) }, onCancel = { model.cancelStrength(editGeneration) },
                                        onRetry = { model.updateStrengthInput(state.strengthInput, editGeneration) },
                                        inputSlot = { FormField(texts.getString(R.string.password_to_check), state.strengthInput, { model.updateStrengthInput(it, editGeneration) }, !state.busy,
                                            placeholder = texts.getString(R.string.password_input_hint), secret = true, reveal = state.passwordShown) },
                                    )
                                    Page.APPEARANCE -> BAppearancePage(uiPreferences, model.uiPreferencesSaving,
                                        model.uiPreferencesError.takeIf { model.uiPreferencesErrorSource in listOf(UiPreferenceErrorSource.GENERAL, UiPreferenceErrorSource.DISPLAY) }.orEmpty()) {
                                        model.updateUiPreferences(it, uiPreferences, Page.APPEARANCE, editGeneration)
                                    }
                                    Page.TOOLS -> ToolsPage(model)
                                    Page.SETTINGS -> SettingsPage(model, onOpenRelease)
                                    Page.HOME, Page.PASSWORDS, Page.SEARCH, Page.CHECKS, Page.GENERATOR, Page.TRANSFER -> Unit
                                }
                                if (state.page !in listOf(Page.CREATE, Page.RENAME, Page.ADD, Page.EDIT, Page.NOTE_ADD, Page.LOCKED, Page.STRENGTH, Page.VAULT_DELETE, Page.BACKUP, Page.MASTER, Page.BIOMETRIC) &&
                                    !(state.page == Page.NOTE_EDIT && model.noteTextChanged)) Feedback(state)
                                if (state.page == Page.VAULTS && state.error.isNotEmpty()) {
                                    TextButton(onClick = model::refreshVaults, enabled = !state.busy) { Text(texts.getString(R.string.reload_vaults)) }
                                }
                                Spacer(Modifier.height(4.dp))
                            }
                        }
                    }
                }
                if (state.page == Page.LOCKED) IconButton(
                    onClick = model::openSecuritySettings, enabled = !state.busy,
                    modifier = Modifier.align(Alignment.TopEnd).padding(end = 16.dp),
                ) { Icon(bIcon("settings"), texts.getString(R.string.settings), tint = Ink) }
                if (notePage) NotePositionBar(formScrollState, model::onUserInteraction, Modifier.align(Alignment.CenterEnd))
                if (state.page == Page.VAULTS) ExitConfirmationFeedback(model.exitConfirmation, Modifier.align(Alignment.TopCenter))
                if (state.unlocked || state.page in listOf(Page.CREATE, Page.RENAME, Page.SECURITY)) {
                    ClipboardFeedback(model, Modifier.align(Alignment.TopCenter))
                }
                UpdateAvailableFeedback(model.updates, { model.onUserInteraction() && onOpenRelease() },
                    Modifier.align(Alignment.BottomCenter), Modifier.recordDialogInteraction(model))
            }
            if (state.unlocked && root && !imeVisible) BBottomNavigation(when (state.page) {
                Page.PASSWORDS -> "library"
                Page.TOOLS -> "tools"
                Page.SETTINGS -> "settings"
                else -> "home"
            }) { id -> model.selectRoot(when (id) { "library" -> Page.PASSWORDS; "tools" -> Page.TOOLS; "settings" -> Page.SETTINGS; else -> Page.HOME }) }
            if (state.page in listOf(Page.MASTER, Page.BIOMETRIC)) {
                HorizontalDivider(color = Line)
                Column(Modifier.padding(horizontal = 24.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    VaultSecurityActions(state, model,
                        enabled = state.page == Page.MASTER || state.vault?.biometricEnabled == true ||
                            state.vault?.hasMasterPassword == true && state.master.isNotEmpty() && model.biometricCapability == BiometricManager.BIOMETRIC_SUCCESS,
                        label = if (state.page == Page.MASTER) texts.getString(R.string.change_and_lock) else if (state.vault?.biometricEnabled == true) texts.getString(R.string.disable_quick_unlock) else texts.getString(R.string.enable_quick_unlock))
                }
            }
            if (guide) {
                HorizontalDivider(color = Line)
                Column(Modifier.padding(horizontal = 24.dp, vertical = 10.dp)) {
                    PrimaryButton(texts.getString(R.string.get_started), false, onClick = model::finishSystemGuide)
                }
            }
            if (state.page in listOf(Page.CREATE, Page.RENAME, Page.ADD, Page.EDIT, Page.NOTE_ADD) || model.noteTextChanged) {
                HorizontalDivider(color = Line)
                Column(Modifier.padding(horizontal = 24.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Feedback(state)
                    PrimaryButton(when (state.page) {
                        Page.CREATE -> texts.getString(R.string.create_vault)
                        Page.RENAME -> texts.getString(R.string.save_vault_name)
                        Page.NOTE_ADD -> texts.getString(R.string.save_note)
                        Page.NOTE_EDIT -> texts.getString(R.string.save)
                        else -> texts.getString(R.string.save_password)
                    }, state.busy, enabled = state.page !in listOf(Page.ADD, Page.EDIT) || !state.secretView.stale) {
                        when (state.page) {
                            Page.CREATE -> model.create()
                            Page.RENAME -> model.rename()
                            Page.NOTE_ADD, Page.NOTE_EDIT -> model.saveNote()
                            else -> model.save(editGeneration, state.page, state.record?.id, state.record?.revision)
                        }
                    }
                }
            }
            if (state.page == Page.BACKUP) {
                Column(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(horizontal = 24.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Feedback(state)
                    }
                    BBackupFooter(model, onChooseBackupFile)
                }
            }
            if (state.page == Page.VAULT_DELETE) {
                HorizontalDivider(color = Line)
                Column(Modifier.padding(horizontal = 24.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Feedback(state)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        TextButton(onClick = { back() }, enabled = !state.busy, modifier = Modifier.weight(1f).heightIn(min = 48.dp)) { Text(texts.getString(R.string.cancel)) }
                        val verified = model.deletionState.preview != null
                        Button(onClick = { if (verified) model.confirmDeletion(editGeneration) else model.authenticateDeletion(editGeneration) },
                            enabled = !state.busy, modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = if (verified) Error else LocalBThemeColors.current.accentFill,
                                contentColor = if (verified) Color.White else LocalBThemeColors.current.onAccent)) {
                            Text(if (state.busy) texts.getString(R.string.processing) else if (verified) texts.getString(R.string.confirm_delete) else texts.getString(R.string.verify_review))
                        }
                    }
                }
            }
        }
        model.draftGenerator?.let { panel ->
            val initialFocus = remember(panel.token) { FocusRequester() }
            AlertDialog(
                modifier = Modifier.imePadding().recordDialogInteraction(model),
                onDismissRequest = { model.dismissDraftGenerator(panel.token) },
                title = { Text(texts.getString(R.string.generator_parameters)) },
                text = {
                    Column(Modifier.heightIn(max = 480.dp)) {
                        Column(Modifier.weight(1f, fill = false).verticalScroll(remember(panel.token) { ScrollState(0) })) {
                            BGeneratorParameters(panel.options, !state.busy && !model.uiPreferencesSaving) { model.updateDraftGenerator(panel.token, it) }
                        }
                        if (panel.error.isNotEmpty()) Text(panel.error.localized(), color = Error, fontSize = businessSp(13.sp),
                            lineHeight = 1.5.em, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Assertive })
                    }
                },
                confirmButton = { TextButton(onClick = { model.saveDraftGenerator(panel.token) }, enabled = !state.busy && !model.uiPreferencesSaving) { Text(texts.getString(R.string.save_parameters)) } },
                dismissButton = {
                    TextButton(onClick = { model.dismissDraftGenerator(panel.token) }, modifier = Modifier.focusRequester(initialFocus), enabled = !model.uiPreferencesSaving) { Text(texts.getString(R.string.cancel)) }
                    // 初始焦点属于非输入操作，避免对话框自动选中长度框并唤起键盘。
                    LaunchedEffect(panel.token) { initialFocus.requestFocus() }
                },
                containerColor = Card, properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn, decorFitsSystemWindows = false),
            )
        }
        state.secretDraft.confirmation?.let { change ->
            val label = if (change.field == RecordSecretField.TOTP) texts.getString(R.string.setup_key) else texts.getString(R.string.recovery_group)
            AlertDialog(
                modifier = Modifier.recordDialogInteraction(model),
                onDismissRequest = { model.cancelSecretChange(editGeneration, state.page, state.record?.id, state.record?.revision) },
                title = { Text(texts.getString(if (change.intent == RecordSecretIntent.REPLACE) R.string.replace_secret_question else R.string.remove_secret_question, label)) },
                text = { Text(if (change.intent == RecordSecretIntent.REMOVE) texts.getString(R.string.remove_secret_on_save, label)
                    else if (change.field == RecordSecretField.RECOVERY_CODES) texts.getString(R.string.replace_recovery_hint)
                    else texts.getString(R.string.replace_key_hint)) },
                confirmButton = { TextButton(onClick = { model.confirmSecretChange(change, editGeneration, state.page, state.record?.id, state.record?.revision) }, enabled = !state.busy) { Text(texts.getString(R.string.continue_action)) } },
                dismissButton = { TextButton(onClick = { model.cancelSecretChange(editGeneration, state.page, state.record?.id, state.record?.revision) }, enabled = !state.busy) { Text(texts.getString(R.string.cancel)) } },
                containerColor = Card, properties = ProtectedDialog,
            )
        }
        if (state.secretDraft.reloadLatest) state.record?.let { record ->
            AlertDialog(
                modifier = Modifier.recordDialogInteraction(model),
                onDismissRequest = { model.cancelSecretChange(editGeneration, state.page, record.id, record.revision) },
                title = { Text(texts.getString(R.string.reload_latest_question)) },
                text = { Text(texts.getString(R.string.reload_draft_warning)) },
                confirmButton = { TextButton(onClick = { model.loadLatestRecord(editGeneration, record.id, record.revision) }, enabled = !state.busy) { Text(texts.getString(R.string.reload)) } },
                dismissButton = { TextButton(onClick = { model.cancelSecretChange(editGeneration, state.page, record.id, record.revision) }, enabled = !state.busy) { Text(texts.getString(R.string.keep_draft)) } },
                containerColor = Card, properties = ProtectedDialog,
            )
        }
        if (state.discard) {
            AlertDialog(
                modifier = Modifier.recordDialogInteraction(model),
                onDismissRequest = model::keepDraft,
                title = { Text(texts.getString(R.string.discard_question)) },
                text = { Text(texts.getString(R.string.discard_warning)) },
                confirmButton = { TextButton(onClick = model::discardDraft) { Text(texts.getString(R.string.discard)) } },
                dismissButton = { TextButton(onClick = model::keepDraft) { Text(texts.getString(R.string.continue_editing)) } },
                containerColor = Card,
                properties = ProtectedDialog,
            )
        }
        if (state.showAdd) AlertDialog(
            modifier = Modifier.recordDialogInteraction(model),
            onDismissRequest = model::dismissAdd,
            title = { Text(texts.getString(R.string.add_item)) },
            text = { Column {
                TextButton(onClick = model::startAdd, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text(texts.getString(R.string.add_password)) }
                TextButton(onClick = model::startNote, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text(texts.getString(R.string.add_note)) }
            } },
            confirmButton = { TextButton(onClick = model::dismissAdd) { Text(texts.getString(R.string.cancel)) } },
            containerColor = Card, properties = ProtectedDialog,
        )
        if (state.deleteConfirm) AlertDialog(
            modifier = Modifier.recordDialogInteraction(model),
            onDismissRequest = model::dismissDelete,
            title = { Text(if (state.page in listOf(Page.NOTE_DETAIL, Page.NOTE_EDIT)) texts.getString(R.string.delete_note_question) else texts.getString(R.string.delete_password_question)) },
            text = { Column { Text(texts.getString(R.string.delete_item_warning, state.record?.title ?: state.note?.title.orEmpty()), Modifier.verticalScroll(rememberScrollState())); Feedback(state) } },
            confirmButton = { TextButton(onClick = model::deleteRecord, enabled = !state.busy) { Text(texts.getString(R.string.delete), color = Error) } },
            dismissButton = { TextButton(onClick = model::dismissDelete, enabled = !state.busy) { Text(texts.getString(R.string.cancel)) } },
            containerColor = Card, properties = ProtectedDialog,
        )
        if (state.showVaults) {
            AlertDialog(
                modifier = Modifier.recordDialogInteraction(model),
                onDismissRequest = model::dismissVaults,
                title = { Text(texts.getString(R.string.select_vault)) },
                text = {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(state.vaults, key = { it.id }) { vault ->
                            VaultRow(vault, state.unlocked && state.vault?.id == vault.id, !state.busy, lineHeight = 20) { model.selectVault(vault) }
                        }
                    }
                },
                confirmButton = { TextButton(onClick = model::startCreate) { Text(texts.getString(R.string.new_vault)) } },
                dismissButton = { TextButton(onClick = model::dismissVaults) { Text(texts.getString(R.string.cancel)) } },
                containerColor = Card,
                properties = ProtectedDialog,
            )
        }
    }
    }
}

// 自有对话框属于独立窗口，其滚动和按键不会经过活动的输入分发。
internal fun Modifier.recordDialogInteraction(model: VaultModel): Modifier = composed {
    val view = LocalView.current
    var parent: android.view.View? = view
    var window: android.view.Window? = null
    while (parent != null && window == null) {
        window = (parent as? androidx.compose.ui.window.DialogWindowProvider)?.window
        parent = parent.parent as? android.view.View
    }
    DisposableEffect(window, model) {
        val target = window
        val previous = target?.callback
        if (target == null || previous == null) onDispose { }
        else {
            val dispatcher = app.cangoo.android.ProtectedTouchDispatcher()
            val protected = object : android.view.Window.Callback by previous {
                override fun dispatchTouchEvent(event: android.view.MotionEvent): Boolean = dispatcher.dispatch(event,
                    allowed = { model.onUserInteraction() }, forward = previous::dispatchTouchEvent)
            }
            target.callback = protected
            if (android.os.Build.VERSION.SDK_INT >= 31) target.setHideOverlayWindows(true)
            onDispose { if (target.callback === protected) target.callback = previous }
        }
    }
    onPreviewKeyEvent { !model.onUserInteraction() }.pointerInput(model) {
        awaitPointerEventScope {
            while (true) {
                val event = awaitPointerEvent(PointerEventPass.Initial)
                if (event.type == PointerEventType.Scroll || event.changes.any { it.pressed || it.previousPressed }) {
                    if (!model.onUserInteraction()) event.changes.forEach { it.consume() }
                }
            }
        }
    }
}

@Composable
private fun Header(state: VaultUiState, onBack: () -> Unit, onAdd: () -> Unit, onLock: () -> Unit, onSettings: () -> Unit,
                   onEdit: () -> Unit, onDeleteNote: () -> Unit, titleOverride: String? = null) {
    val texts = LocalResources.current
    Row(Modifier.fillMaxWidth().heightIn(min = 64.dp).padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
        val root = state.page in listOf(Page.HOME, Page.PASSWORDS, Page.TOOLS, Page.SETTINGS)
        if (!root) {
            if (state.page != Page.VAULTS) IconButton(onClick = onBack, enabled = !state.busy) {
                Icon(bIcon("chevron_left"), texts.getString(R.string.back), tint = Ink)
            } else Spacer(Modifier.size(48.dp))
        }
        Text(
            titleOverride ?: when (state.page) {
                Page.VAULTS -> texts.getString(R.string.my_vaults)
                Page.VAULT_MANAGEMENT -> texts.getString(R.string.manage_vaults)
                Page.VAULT_DELETE -> texts.getString(R.string.delete_vault)
                Page.CREATE -> texts.getString(R.string.new_vault)
                Page.RENAME -> texts.getString(R.string.rename_vault)
                Page.MASTER -> texts.getString(R.string.change_master)
                Page.BIOMETRIC -> texts.getString(R.string.quick_unlock)
                Page.LOCKED -> "小仓"
                Page.PASSWORDS -> texts.getString(R.string.scope_all)
                Page.HOME -> texts.getString(R.string.home)
                Page.SEARCH -> texts.getString(R.string.search_items)
                Page.CHECKS -> texts.getString(R.string.password_checks)
                Page.TOOLS -> texts.getString(R.string.tools)
                Page.SETTINGS -> stringResource(R.string.settings)
                Page.APPEARANCE -> stringResource(R.string.appearance)
                Page.GENERATOR -> texts.getString(R.string.generate_password)
                Page.STRENGTH -> texts.getString(R.string.analyze_strength)
                Page.ADD -> texts.getString(R.string.add_password)
                Page.EDIT -> texts.getString(R.string.edit_password)
                Page.DETAIL -> texts.getString(R.string.password_details)
                Page.NOTE_ADD -> texts.getString(R.string.add_note)
                Page.NOTE_DETAIL, Page.NOTE_EDIT -> texts.getString(R.string.note)
                Page.SECURITY -> stringResource(R.string.settings)
                Page.BACKUP -> texts.getString(R.string.backup_restore)
                Page.TRANSFER -> texts.getString(R.string.transfer_title)
                Page.HELP -> stringResource(R.string.help)
                Page.SYSTEM_ACCESS -> stringResource(R.string.system_access)
            },
            modifier = Modifier.weight(1f).padding(start = if (root) 8.dp else 0.dp).semantics { heading() },
            fontSize = businessSp(if (root) 29.sp else 18.sp),
            style = TextStyle(lineHeight = if (root) 1.3.em else 1.4.em, letterSpacing = if (root) (-0.7).sp else (-0.3).sp,
                lineHeightStyle = BLineHeightStyle),
            fontWeight = FontWeight.Bold,
            color = Ink,
            textAlign = if (root) TextAlign.Start else TextAlign.Center,
        )
        if (state.page == Page.VAULTS) {
            IconButton(onClick = onSettings, enabled = !state.busy) { Icon(bIcon("settings"), texts.getString(R.string.settings), tint = Ink) }
        }
        if (state.page == Page.PASSWORDS) {
            Surface(onClick = onAdd, enabled = !state.busy, shape = RoundedCornerShape(15.dp), color = LocalBThemeColors.current.accentFill) {
                Box(Modifier.size(48.dp), contentAlignment = Alignment.Center) {
                    Icon(bIcon("add"), texts.getString(R.string.add_item), tint = LocalBThemeColors.current.onAccent)
                }
            }
        }
        if (state.page == Page.DETAIL) {
            TextButton(onClick = onEdit, enabled = !state.busy && !state.secretView.stale,
                modifier = Modifier.widthIn(min = 56.dp).heightIn(min = 48.dp), contentPadding = PaddingValues(horizontal = 6.dp)) {
                Icon(bIcon("edit"), null, Modifier.size(18.dp))
                Spacer(Modifier.width(7.dp))
                Text(texts.getString(R.string.edit), fontSize = businessSp(14.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
            }
        }
        if (state.page in listOf(Page.NOTE_DETAIL, Page.NOTE_EDIT)) {
            TextButton(onClick = onDeleteNote, enabled = !state.busy,
                modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = texts.getString(R.string.delete_note) }) {
                Text(texts.getString(R.string.delete), color = Error, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            }
        }
        if (state.unlocked) IconButton(onClick = onLock) { Icon(bIcon("lock"), texts.getString(R.string.lock_vault), tint = Ink) }
        else if (!root) Spacer(Modifier.size(48.dp))
    }
}

@Composable
private fun ToolsPage(model: VaultModel) {
    val texts = LocalResources.current
    val state = model.state
    val colors = LocalBThemeColors.current
    val message = when {
        !state.checksAvailable -> texts.getString(R.string.checks_unavailable)
        state.checks.checkedCount == 0 -> texts.getString(R.string.checks_empty)
        state.checks.warningIds.isNotEmpty() -> texts.getQuantityString(R.plurals.warning_count, state.checks.warningIds.size, state.checks.warningIds.size)
        state.checks.pendingEpochs.isNotEmpty() -> texts.getQuantityString(R.plurals.pending_count, state.checks.pendingEpochs.size, state.checks.pendingEpochs.size)
        else -> texts.getString(R.string.checks_clear)
    }
    Column(Modifier.fillMaxWidth()) {
        Surface(onClick = model::startGenerator, enabled = !state.busy && !model.uiPreferencesSaving, shape = RoundedCornerShape(22.dp),
            color = colors.accentFill, modifier = Modifier.padding(top = 9.dp, bottom = 30.dp)) {
            Column(Modifier.fillMaxWidth().padding(25.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Icon(bIcon("lock"), null, Modifier.size(30.dp), tint = colors.onAccent)
                    Icon(bIcon("chevron_right"), null, Modifier.size(24.dp), tint = colors.onAccent)
                }
                Text(texts.getString(R.string.generate_password), Modifier.padding(top = 28.dp), color = colors.onAccent, fontSize = businessSp(28.sp), lineHeight = 1.4.em,
                    letterSpacing = (-0.3).sp, fontWeight = FontWeight.Medium)
                Text(texts.getString(R.string.generator_description), Modifier.padding(top = 7.dp), color = colors.onAccentMuted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
            }
        }
        Text(texts.getString(R.string.data_management), Modifier.padding(bottom = 10.dp).semantics { heading() }, color = Ink, fontSize = businessSp(20.sp),
            lineHeight = 1.4.em, fontWeight = FontWeight.Bold)
        SettingsGroup {
            SettingsAction(texts.getString(R.string.analyze_strength), texts.getString(R.string.offline_analysis_hint), !state.busy, "mixer", model::startStrength)
            HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
            SettingsAction(texts.getString(R.string.password_checks), message, !state.busy, if (state.checks.warningIds.isEmpty()) "info" else "warning", model::showChecks)
            HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
            SettingsAction(texts.getString(R.string.backup_restore), texts.getString(R.string.backup_description), !state.busy, "tools", model::openBackup)
        }
    }
}

@Composable
private fun SettingsPage(model: VaultModel, onOpenRelease: () -> Boolean) {
    val state = model.state
    val generation = model.editGeneration
    var viewingName by remember(state.vault?.id, generation) { mutableStateOf(false) }
    Column(Modifier.fillMaxWidth()) {
        if (!state.unlocked) Surface(shape = RoundedCornerShape(20.dp), color = Card, modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
            Text(stringResource(R.string.locked), Modifier.padding(24.dp), color = Ink, fontSize = businessSp(22.sp), lineHeight = 1.4.em)
        } else Surface(shape = RoundedCornerShape(20.dp), color = Card, modifier = Modifier.padding(top = 8.dp)) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 25.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.size(48.dp).background(Soft, RoundedCornerShape(13.dp)), contentAlignment = Alignment.Center) {
                    Icon(bIcon("lock"), null, Modifier.size(22.dp), tint = Accent)
                }
                TextButton(onClick = {
                    if (generation == model.editGeneration && model.state.page == Page.SETTINGS && model.onUserInteraction()) viewingName = true
                }, enabled = !state.busy, contentPadding = PaddingValues(0.dp), modifier = Modifier.padding(top = 13.dp).heightIn(min = 48.dp)) {
                    Text(state.vault?.name.orEmpty(), color = Ink, fontSize = businessSp(22.sp), lineHeight = 1.4.em,
                        fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center,
                        modifier = Modifier.weight(1f, fill = false).semantics { heading() })
                    Icon(bIcon("info"), stringResource(R.string.view_full_name), Modifier.padding(start = 8.dp).size(18.dp), tint = Muted)
                }
                Text(stringResource(R.string.appearance_summary, pluralStringResource(R.plurals.password_count, state.passwords.size, state.passwords.size), pluralStringResource(R.plurals.note_count, state.notes.size, state.notes.size)), Modifier.padding(top = 9.dp, bottom = 18.dp), color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
                Button(onClick = { model.lock() }, shape = RoundedCornerShape(11.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Soft, contentColor = Ink), modifier = Modifier.heightIn(min = 48.dp)) {
                    Text(stringResource(R.string.lock_now), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
                }
            }
        }
        SettingsHeading(stringResource(R.string.vault_group))
        SettingsGroup {
            SettingsAction(stringResource(R.string.manage_vaults), pluralStringResource(R.plurals.vault_count, state.vaults.size, state.vaults.size), !state.busy, "lock", model::manageVaults)
            HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
            SettingsAction(stringResource(R.string.backup_restore), if (state.unlocked) state.localBackupRecordLabel?.localized() ?: stringResource(R.string.backup_loading) else stringResource(R.string.unlock_required), state.unlocked && !state.busy, "tools", model::openBackup)
            HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
            SettingsAction(stringResource(R.string.transfer_title), stringResource(if (state.unlocked) R.string.transfer_description else R.string.unlock_required),
                state.unlocked && !state.busy, "reload", model::openDirectTransfer)
            HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
            SettingsAction(stringResource(R.string.change_master), if (state.unlocked) stringResource(R.string.change_master_hint) else stringResource(R.string.unlock_required), state.unlocked && !state.busy, "lock", model::openMasterChange)
            HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
            SettingsAction(stringResource(R.string.quick_unlock), if (!state.unlocked) stringResource(R.string.unlock_required) else if (state.vault?.biometricEnabled == true) stringResource(R.string.vault_enabled, (model.biometricText.settingName ?: stringResource(R.string.biometric_setting_fallback))) else (model.biometricText.settingName ?: stringResource(R.string.biometric_setting_fallback)),
                state.unlocked && !state.busy, "lock", model::openBiometricSettings)
        }
        UiSettingsPage(model)
        UpdateCheckCard(model.updates, { model.onUserInteraction() && onOpenRelease() }, Modifier.padding(top = 22.dp),
            Modifier.recordDialogInteraction(model))
        Surface(color = Card, shape = RoundedCornerShape(17.dp), modifier = Modifier.padding(top = 22.dp)) {
            SettingsAction(stringResource(R.string.system_access), stringResource(R.string.system_access_hint), !state.busy, "settings", model::openSystemAccess)
        }
        Surface(color = Card, shape = RoundedCornerShape(17.dp), modifier = Modifier.padding(top = 22.dp)) {
            SettingsAction(stringResource(R.string.help), stringResource(R.string.help_hint), !state.busy, "info") { model.openHelp(generation) }
        }
    }
    if (viewingName) BVaultNameSheet(state.vault?.name.orEmpty(), model) { viewingName = false }
}

@Composable
private fun SettingsHeading(title: String) {
    Text(title, Modifier.padding(top = 28.dp, bottom = 10.dp).semantics { heading() }, color = Muted,
        fontSize = businessSp(13.sp), lineHeight = 1.4.em, fontWeight = FontWeight.Bold)
}

@Composable
internal fun SettingsGroup(content: @Composable () -> Unit) {
    Surface(shape = RoundedCornerShape(17.dp), color = Card) { Column { content() } }
}

@Composable
internal fun SettingsChoice(title: String, value: String, enabled: Boolean, horizontalPadding: androidx.compose.ui.unit.Dp = 14.dp, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick).heightIn(min = 65.dp).padding(horizontal = horizontalPadding, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, Modifier.weight(1f), color = Ink, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
        Text(value, color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
        Icon(bIcon("chevron_down"), null, Modifier.size(18.dp), tint = Muted)
    }
}

@Composable
private fun UiSettingsPage(model: VaultModel) {
    val prefs = model.uiPreferences
    val generation = model.editGeneration
    val saving = model.uiPreferencesSaving
    val preferencePage = model.state.page
    var chooseLanguage by remember { mutableStateOf(false) }
    var chooseFont by remember { mutableStateOf(false) }
    var chooseCopyTime by remember { mutableStateOf(false) }
    var chooseGeneratorTime by remember { mutableStateOf(false) }
    @Composable fun PreferenceErrorFor(source: UiPreferenceErrorSource) {
        if (model.uiPreferencesErrorSource == source && model.uiPreferencesError.isNotEmpty()) Text(model.uiPreferencesError,
            Modifier.padding(horizontal = 14.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Assertive },
            color = Error, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp))
    }
    PreferenceErrorFor(UiPreferenceErrorSource.GENERAL)
    SettingsHeading(stringResource(R.string.lock_group))
    SettingsGroup { SecuritySettingsPage(model, embedded = true) }
    SettingsHeading(stringResource(R.string.cleanup_group))
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SettingsGroup {
            Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp)) {
                GeneratorToggle(stringResource(R.string.generator_auto_clear), prefs.generatorAutoClear, !saving,
                    note = stringResource(R.string.generator_auto_hint)) {
                    model.updateUiPreferences(prefs.copy(generatorAutoClear = it), prefs, preferencePage, generation)
                }
            }
            AnimatedVisibility(visible = prefs.generatorAutoClear,
                enter = expandVertically(animationSpec = tween(150), expandFrom = Alignment.Top),
                exit = shrinkVertically(animationSpec = tween(150), shrinkTowards = Alignment.Top)) {
                Column(Modifier.padding(start = 16.dp)) {
                    HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
                    SettingsChoice(stringResource(R.string.retention), when (prefs.generatorSeconds) { 30 -> stringResource(R.string.seconds_thirty); 60 -> stringResource(R.string.minute_one); else -> stringResource(R.string.minutes_five) },
                        !saving && prefs.generatorAutoClear) { chooseGeneratorTime = true }
                }
            }
            PreferenceErrorFor(UiPreferenceErrorSource.GENERATOR)
        }
        SettingsGroup {
            SettingsChoice(stringResource(R.string.copy_retention), pluralStringResource(R.plurals.seconds_count, prefs.clipboardSeconds, prefs.clipboardSeconds), !saving) { chooseCopyTime = true }
            HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
            TextButton(onClick = model::clearClipboard, enabled = model.clipboardDuty != null && !model.state.busy,
                modifier = Modifier.fillMaxWidth().heightIn(min = 65.dp), shape = RoundedCornerShape(0.dp),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 14.dp),
                colors = ButtonDefaults.textButtonColors(contentColor = Accent)) {
                Text(stringResource(R.string.clear_clipboard), Modifier.fillMaxWidth(), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            }
            PreferenceErrorFor(UiPreferenceErrorSource.CLIPBOARD)
        }
    }
    SettingsHeading(stringResource(R.string.display_group))
    SettingsGroup {
        SettingsChoice(stringResource(R.string.language_title), prefs.language.label, !saving) { chooseLanguage = true }
        HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
        SettingsChoice(stringResource(R.string.font_size), if (prefs.fontScale == 1f) stringResource(R.string.standard) else "${(prefs.fontScale * 100).toInt()}%", !saving) { chooseFont = true }
        HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
        SettingsAction(stringResource(R.string.appearance), stringResource(R.string.appearance_summary, paletteLabel(prefs.palette), themeLabel(prefs.theme)), !saving, "settings", model::openAppearance)
        if (!chooseLanguage) PreferenceErrorFor(UiPreferenceErrorSource.DISPLAY)
    }
    if (chooseLanguage) AlertDialog(
        modifier = Modifier.recordDialogInteraction(model), properties = ProtectedDialog,
        onDismissRequest = { if (!saving) chooseLanguage = false }, title = { Text(stringResource(R.string.language_title)) },
        text = { Column(Modifier.verticalScroll(rememberScrollState())) {
            UiLanguage.entries.forEach { language ->
                TextButton(onClick = {
                    model.updateUiPreferences(prefs.copy(language = language), prefs, preferencePage, generation) { chooseLanguage = false }
                }, enabled = !saving, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Text(language.label, Modifier.weight(1f), color = Ink)
                    if (prefs.language == language) Icon(bIcon("check"), null, tint = Accent)
                }
            }
            PreferenceErrorFor(UiPreferenceErrorSource.DISPLAY)
        } }, confirmButton = { TextButton(onClick = { chooseLanguage = false }, enabled = !saving) { Text(stringResource(R.string.cancel)) } },
    )
    if (chooseGeneratorTime) AlertDialog(
        modifier = Modifier.recordDialogInteraction(model), properties = ProtectedDialog,
        onDismissRequest = { chooseGeneratorTime = false }, title = { Text(stringResource(R.string.generator_retention)) },
        text = { Column {
            listOf(30 to stringResource(R.string.seconds_thirty), 60 to stringResource(R.string.minute_one), 300 to stringResource(R.string.minutes_five)).forEach { (seconds, label) ->
                TextButton(onClick = {
                    chooseGeneratorTime = false
                    model.updateUiPreferences(prefs.copy(generatorSeconds = seconds), prefs, preferencePage, generation)
                }, enabled = !saving, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Text(label, Modifier.weight(1f), color = Ink)
                    if (prefs.generatorSeconds == seconds) Icon(bIcon("check"), null, tint = Accent)
                }
            }
        } }, confirmButton = { TextButton(onClick = { chooseGeneratorTime = false }) { Text(stringResource(R.string.cancel)) } },
    )
    if (chooseCopyTime) AlertDialog(
        modifier = Modifier.recordDialogInteraction(model), properties = ProtectedDialog,
        onDismissRequest = { chooseCopyTime = false }, title = { Text(stringResource(R.string.copy_retention)) },
        text = { Column {
            listOf(5, 30, 60).forEach { seconds ->
                TextButton(onClick = {
                    chooseCopyTime = false
                    model.updateUiPreferences(prefs.copy(clipboardSeconds = seconds), prefs, preferencePage, generation)
                }, enabled = !saving, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Text(pluralStringResource(R.plurals.seconds_count, seconds, seconds), Modifier.weight(1f), color = Ink)
                    if (prefs.clipboardSeconds == seconds) Icon(bIcon("check"), null, tint = Accent)
                }
            }
        } }, confirmButton = { TextButton(onClick = { chooseCopyTime = false }) { Text(stringResource(R.string.cancel)) } },
    )
    if (chooseFont) AlertDialog(
        modifier = Modifier.recordDialogInteraction(model),
        onDismissRequest = { chooseFont = false }, properties = ProtectedDialog,
        title = { Text(stringResource(R.string.font_size)) }, text = {
            Column {
                BFontOptions.forEach { (scale, label) ->
                    TextButton(onClick = {
                        chooseFont = false
                        model.updateUiPreferences(prefs.copy(fontScale = scale), prefs, preferencePage, generation)
                    }, enabled = !saving, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                        Text(if (scale == 1f) stringResource(R.string.standard) else label, Modifier.weight(1f), color = Ink)
                        if (prefs.fontScale == scale) Icon(bIcon("check"), null, tint = Accent)
                    }
                }
            }
        }, confirmButton = { TextButton(onClick = { chooseFont = false }) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
internal fun SettingsAction(title: String, subtitle: String, enabled: Boolean, icon: String, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().then(if (enabled) Modifier.clickable(onClick = onClick) else Modifier.semantics { disabled() }).heightIn(min = 85.dp).padding(horizontal = 14.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        Box(Modifier.size(40.dp).background(Soft, RoundedCornerShape(13.dp)), contentAlignment = Alignment.Center) {
            Icon(bIcon(icon), null, Modifier.size(22.dp), tint = if (enabled) Accent else Muted)
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(title, color = if (enabled) Ink else Muted, fontSize = businessSp(15.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
            if (subtitle.isNotEmpty()) Text(subtitle, color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
        }
        if (enabled) Icon(bIcon("chevron_right"), null, Modifier.size(16.dp), tint = Muted)
        else Spacer(Modifier.size(16.dp))
    }
}

@Composable
private fun SecuritySettingsPage(model: VaultModel, embedded: Boolean = false) {
    val texts = LocalResources.current
    val settings = model.securitySettings
    val saving = model.securitySettingsSaving
    var chooseIdle by remember { mutableStateOf(false) }
    @Composable fun idleLabel(minutes: Int) = if (minutes == 0) stringResource(R.string.off) else pluralStringResource(R.plurals.minute_count, minutes, minutes)
    if (!embedded) Text(stringResource(R.string.lock_group), Modifier.padding(top = 14.dp), color = Muted, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp), fontWeight = FontWeight.SemiBold)
    Surface(shape = RoundedCornerShape(17.dp), color = if (embedded) Color.Transparent else Card) {
        Column {
            Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp)) {
                GeneratorToggle(stringResource(R.string.lock_on_leave), settings.lockOnLeave, !saving, divider = true,
                    note = stringResource(R.string.lock_on_leave_hint)) { model.updateSecuritySettings(settings.copy(lockOnLeave = it)) }
            }
            SettingsChoice(stringResource(R.string.idle_lock), idleLabel(settings.idleMinutes), !saving) { chooseIdle = true }
        }
    }
    if (!embedded) Notice(stringResource(R.string.lock_info))
    if (!embedded) Surface(color = Card, shape = RoundedCornerShape(17.dp)) {
        SettingsAction(stringResource(R.string.system_access), texts.getString(R.string.status_without_unlock), !model.state.busy, "settings", model::openSystemAccess)
    }
    if (model.securitySettingsError.isNotEmpty()) Text(model.securitySettingsError,
        Modifier.semantics { liveRegion = LiveRegionMode.Polite }, color = Error, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp))
    if (chooseIdle) AlertDialog(
        modifier = Modifier.recordDialogInteraction(model),
        onDismissRequest = { if (model.onUserInteraction()) chooseIdle = false },
        title = { Text(stringResource(R.string.idle_lock)) },
        text = {
            Column {
                listOf(1, 5, 15, 0).forEach { minutes ->
                    TextButton(onClick = {
                        model.updateSecuritySettings(settings.copy(idleMinutes = minutes))
                        chooseIdle = false
                    }, enabled = !saving, modifier = Modifier.fillMaxWidth()) {
                        Text(idleLabel(minutes), Modifier.weight(1f), textAlign = TextAlign.Start)
                        if (minutes == settings.idleMinutes) Text(stringResource(R.string.current))
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = { if (model.onUserInteraction()) chooseIdle = false }) { Text(stringResource(R.string.cancel)) } },
        containerColor = Card, properties = ProtectedDialog,
    )
}

@Composable
private fun VaultList(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    if (state.vaults.isEmpty() && !state.busy && state.error.isEmpty()) {
        EmptyState(texts.getString(R.string.no_vaults), texts.getString(R.string.create_first_vault))
    } else if (state.vaults.isNotEmpty()) {
        val input = model.editGeneration
        state.vaults.forEach { vault ->
            val current = state.unlocked && state.vault?.id == vault.id
            Surface(shape = RoundedCornerShape(17.dp), color = Card) {
                Column {
                    VaultRow(vault, current, !state.busy) { model.selectVault(vault) }
                    HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
                    if (state.page == Page.VAULT_MANAGEMENT && current) {
                        TextButton(onClick = model::startRename, enabled = !state.busy,
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(texts.getString(R.string.rename)) }
                    }
                    TextButton(onClick = { model.openVaultDeletion(vault.id, input, state.page) }, enabled = !state.busy,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(texts.getString(R.string.delete_vault), color = Error) }
                }
            }
        }
    }
    PrimaryButton(texts.getString(R.string.new_vault), state.busy, onClick = model::startCreate)
}

@Composable
private fun VaultRow(vault: VaultInfo, current: Boolean, enabled: Boolean, lineHeight: Int = 24, onClick: () -> Unit) {
    val texts = LocalResources.current
    Surface(onClick = onClick, enabled = enabled, shape = RoundedCornerShape(17.dp), color = Card) {
        Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            LockMark(44)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(vault.name, color = Ink, lineHeight = (lineHeight / 16f).em, fontSize = businessSp(16.sp), fontWeight = FontWeight.SemiBold)
                Text(
                    if (!vault.available) texts.getString(R.string.vault_unavailable) else if (current) texts.getString(R.string.vault_unlocked) else if (vault.hasMasterPassword) texts.getString(R.string.master_needed) else texts.getString(R.string.no_master),
                    color = Muted, lineHeight = (lineHeight / 13f).em, fontSize = businessSp(13.sp),
                )
            }
            Icon(bIcon("chevron_right"), null, tint = Muted)
        }
    }
}

@Composable
private fun CreateVault(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val editGeneration = model.editGeneration
    FormField(texts.getString(R.string.vault_name), state.vaultName, { model.updateVaultName(it, editGeneration) }, required = true, enabled = !state.busy, placeholder = texts.getString(R.string.name_hint))
    FormField(texts.getString(R.string.new_vault_master), state.master, { model.updateMaster(it, Page.CREATE, editGeneration) }, secret = true, enabled = !state.busy, placeholder = texts.getString(R.string.may_be_empty))
    FormField(texts.getString(R.string.confirm_new_vault_master), state.confirmation, { model.updateConfirmation(it, editGeneration) }, secret = true, required = state.master.isNotEmpty(), enabled = !state.busy)
    Notice(if (state.master.isEmpty()) texts.getString(R.string.empty_master_warning) else texts.getString(R.string.independent_master_hint))
}

@Composable
private fun RenameVault(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val generation = model.editGeneration
    FormField(texts.getString(R.string.new_vault_name), state.vaultName, { model.updateVaultName(it, generation, Page.RENAME) }, placeholder = texts.getString(R.string.name_hint), required = true, enabled = !state.busy)
    if (state.vault?.hasMasterPassword == true) {
        FormField(texts.getString(R.string.current_vault_master), state.master, { model.updateMaster(it, Page.RENAME, generation) }, secret = true, required = state.vault?.hasMasterPassword == true && state.vaultName.trim() != state.vault?.name, enabled = !state.busy)
    }
}

@Composable
private fun UnlockVault(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val vault = state.vault ?: return
    val editGeneration = model.editGeneration
    Column(Modifier.fillMaxWidth().padding(top = 70.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Image(painterResource(R.drawable.app_icon), null, Modifier.size(84.dp))
        Spacer(Modifier.height(30.dp))
        Text(texts.getString(R.string.app_locked), color = Ink, fontSize = businessSp(29.sp), lineHeight = (38f / 29).em, fontWeight = FontWeight.Bold, modifier = Modifier.semantics { heading() })
        Spacer(Modifier.height(8.dp))
        TextButton(onClick = model::showVaults, enabled = !state.busy) {
            Text(vault.name, textAlign = TextAlign.Center, lineHeight = (20f / 16).em, fontSize = businessSp(16.sp), color = Muted)
        }
        TextButton(onClick = model::manageVaults, enabled = !state.busy) { Text(texts.getString(R.string.manage_vaults), lineHeight = (20f / 14).em, fontSize = businessSp(14.sp)) }
        if (vault.biometricEnabled) {
            TextButton(onClick = model::unlockWithBiometric,
                enabled = !state.busy && model.biometricCapability == BiometricManager.BIOMETRIC_SUCCESS) {
                Text(model.biometricText.buttonLabel ?: stringResource(R.string.quick_unlock), lineHeight = 1.5.em, fontSize = businessSp(16.sp))
            }
            if (model.biometricCapability != BiometricManager.BIOMETRIC_SUCCESS) {
                Text(biometricCapabilityMessage(model.biometricCapability), color = Muted, textAlign = TextAlign.Center,
                    lineHeight = 1.5.em, fontSize = businessSp(13.sp))
            }
        }
        Spacer(Modifier.height(43.dp))
        if (!vault.hasMasterPassword && vault.available) {
            Notice(texts.getString(R.string.empty_master_open))
            Spacer(Modifier.height(20.dp))
        }
        FormField(texts.getString(R.string.master_password), state.master, { model.updateMaster(it, Page.LOCKED, editGeneration) }, secret = true, required = vault.hasMasterPassword, enabled = !state.busy, placeholder = texts.getString(R.string.master_hint), onDone = model::unlock)
        Feedback(state)
        Spacer(Modifier.height(18.dp))
        PrimaryButton(texts.getString(R.string.unlock), state.busy, onClick = model::unlock)
    }
}

@Composable
private fun MasterPasswordPage(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val input = model.editGeneration
    FormField(texts.getString(R.string.current_master), state.master, { model.updateMaster(it, Page.MASTER, input) }, secret = true, required = state.vault?.hasMasterPassword == true, enabled = !state.busy,
        placeholder = if (state.vault?.hasMasterPassword == true) texts.getString(R.string.current_master_hint) else texts.getString(R.string.empty_current_master))
    FormField(texts.getString(R.string.new_master), state.newMaster, { model.updateNewMaster(it, input) }, secret = true, enabled = !state.busy, placeholder = texts.getString(R.string.may_be_empty))
    FormField(texts.getString(R.string.confirm_new_master), state.confirmation, { model.updateNewMasterConfirmation(it, input) }, secret = true, required = state.newMaster.isNotEmpty(), enabled = !state.busy,
        onDone = model::submitVaultSecurity)
    Notice(if (state.newMaster.isEmpty()) texts.getString(R.string.remove_master_warning)
        else texts.getString(R.string.master_unrecoverable))
}

@Composable
private fun BiometricSettingsPage(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val vault = state.vault ?: return
    val input = model.editGeneration
    Surface(color = Card, shape = RoundedCornerShape(17.dp)) {
        Column(Modifier.fillMaxWidth().padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(if (vault.biometricEnabled) texts.getString(R.string.enabled) else texts.getString(R.string.not_enabled), color = Ink, fontSize = businessSp(22.sp), fontWeight = FontWeight.Bold, lineHeight = 1.4.em)
            Text(texts.getString(R.string.device_support), color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
            Text((model.biometricText.settingName ?: stringResource(R.string.biometric_setting_fallback)), color = Ink, fontSize = businessSp(16.sp), lineHeight = 1.5.em)
        }
    }
    Text(texts.getString(R.string.system_method_hint), color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
    if (vault.biometricEnabled) Notice(texts.getString(R.string.disable_biometric_hint))
    else if (!vault.hasMasterPassword) Notice(texts.getString(R.string.empty_master_biometric))
    else if (model.biometricCapability == BiometricManager.BIOMETRIC_SUCCESS) {
        Notice(texts.getString(R.string.enable_biometric_hint))
        FormField(texts.getString(R.string.vault_master), state.master, { model.updateMaster(it, Page.BIOMETRIC, input) },
            secret = true, required = true, enabled = !state.busy, placeholder = texts.getString(R.string.current_master_hint), onDone = model::submitVaultSecurity)
    }
    if (model.biometricCapability != BiometricManager.BIOMETRIC_SUCCESS) {
        Text(biometricCapabilityMessage(model.biometricCapability), color = Muted, lineHeight = 1.5.em, fontSize = businessSp(13.sp))
    }
}

@Composable
private fun VaultSecurityActions(state: VaultUiState, model: VaultModel, enabled: Boolean, label: String) {
    val texts = LocalResources.current
    Feedback(state)
    if (state.securityStage.isNotEmpty()) Text(state.securityStage.localized(), color = Muted,
        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
    if (state.page == Page.BIOMETRIC && state.vault?.biometricEnabled == true) {
        OutlinedButton(onClick = model::submitVaultSecurity, enabled = !state.busy && enabled,
            modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, Line)) {
            Text(if (state.busy) texts.getString(R.string.processing) else label, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
        }
    } else PrimaryButton(label, state.busy, enabled, model::submitVaultSecurity)
    if (state.busy) TextButton(onClick = model::cancelVaultSecurity, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
        Text(texts.getString(R.string.cancel), lineHeight = 1.5.em, fontSize = businessSp(14.sp))
    }
}

@Composable
private fun biometricCapabilityMessage(code: Int): String = when (code) {
    BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> LocalResources.current.getString(R.string.biometric_not_enrolled)
    BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> LocalResources.current.getString(R.string.biometric_no_hardware)
    else -> LocalResources.current.getString(R.string.biometric_unavailable)
}

@Composable
private fun SearchToolbar(state: VaultUiState, model: VaultModel, requester: FocusRequester, onBack: () -> Unit, onReady: () -> Unit) {
    val texts = LocalResources.current
    val input = model.editGeneration
    Row(Modifier.fillMaxWidth().heightIn(min = 64.dp).background(Paper).padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = onBack, enabled = !state.busy) { Icon(bIcon("chevron_left"), texts.getString(R.string.back), tint = Ink) }
        Box(Modifier.weight(1f)) {
            FormField(texts.getString(R.string.search_password_notes), state.query, { model.updateQuery(it, input) }, !state.busy, placeholder = texts.getString(R.string.search_hint), focusRequester = requester,
                search = true, onClear = { model.updateQuery("", input) })
        }
        IconButton(onClick = { model.lock() }) { Icon(bIcon("lock"), texts.getString(R.string.lock_vault), tint = Ink) }
    }
    LaunchedEffect(state.searchOpening) { onReady() }
}

@Composable
private fun BrowseControls(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val input = model.editGeneration
    val colors = LocalBThemeColors.current
    var chooser by remember { mutableStateOf("") }
    val filters = listOf(BrowseFilter.ALL to texts.getString(R.string.all), BrowseFilter.FAVORITE to texts.getString(R.string.favorites)) +
        if (state.browseKind == BrowseKind.NOTE) emptyList() else listOf(BrowseFilter.WEAK to texts.getString(R.string.weak_passwords), BrowseFilter.REPEATED to texts.getString(R.string.repeated_passwords))
    Row(Modifier.fillMaxWidth().padding(top = 14.dp, bottom = 12.dp).background(Soft, RoundedCornerShape(12.dp)).padding(4.dp)) {
        listOf(BrowseKind.ALL to texts.getString(R.string.all), BrowseKind.PASSWORD to texts.getString(R.string.record_type_passwords), BrowseKind.NOTE to texts.getString(R.string.record_type_notes)).forEach { (kind, label) ->
            TextButton(onClick = { model.changeBrowse(kind = kind, filter = BrowseFilter.ALL, expectedGeneration = input, expectedPage = state.page) }, enabled = !state.busy,
                modifier = Modifier.weight(1f).heightIn(min = 48.dp).semantics { selected = kind == state.browseKind },
                shape = RoundedCornerShape(9.dp), colors = ButtonDefaults.textButtonColors(containerColor = if (kind == state.browseKind) Card else Color.Transparent, contentColor = Ink)) { Text(label, lineHeight = (20f / 16).em, fontSize = businessSp(16.sp)) }
        }
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        TextButton(onClick = { if (model.onUserInteraction()) chooser = "filter" }, enabled = !state.busy, colors = ButtonDefaults.textButtonColors(contentColor = Accent)) {
            Text(texts.getString(R.string.filter_value, filters.firstOrNull { it.first == state.browseFilter }?.second ?: texts.getString(R.string.all)), fontSize = businessSp(14.sp), fontWeight = FontWeight.SemiBold, lineHeight = 1.5.em)
            Icon(bIcon("chevron_down"), null, Modifier.padding(start = 8.dp).size(18.dp))
        }
        TextButton(onClick = { if (model.onUserInteraction()) chooser = "sort" }, enabled = !state.busy, colors = ButtonDefaults.textButtonColors(contentColor = Accent)) {
            Icon(bIcon("mixer"), null, Modifier.padding(end = 8.dp).size(17.dp))
            Text(if (state.browseSort == BrowseSort.RECENT) texts.getString(R.string.sort_recent) else texts.getString(R.string.sort_name), fontSize = businessSp(14.sp), fontWeight = FontWeight.SemiBold, lineHeight = 1.5.em)
        }
    }
    if (chooser.isNotEmpty()) AlertDialog(modifier = Modifier.recordDialogInteraction(model), onDismissRequest = { chooser = "" }, properties = ProtectedDialog,
        title = { Text(if (chooser == "sort") texts.getString(R.string.sort_order) else texts.getString(R.string.filter_items)) }, text = {
            Column {
                if (chooser == "sort") listOf(BrowseSort.RECENT to texts.getString(R.string.sort_recent), BrowseSort.NAME to texts.getString(R.string.sort_name)).forEach { (sort, label) ->
                    TextButton(onClick = { chooser = ""; model.changeBrowse(sort = sort, expectedGeneration = input, expectedPage = state.page) }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                        Text(label, Modifier.weight(1f), color = Ink)
                        if (state.browseSort == sort) Icon(bIcon("check"), null, tint = colors.accentInk)
                    }
                } else filters.forEach { (filter, label) ->
                    TextButton(onClick = { chooser = ""; model.changeBrowse(filter = filter, expectedGeneration = input, expectedPage = state.page) }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                        Text(label, Modifier.weight(1f), color = Ink)
                        if (state.browseFilter == filter) Icon(bIcon("check"), null, tint = colors.accentInk)
                    }
                }
            }
        }, confirmButton = { TextButton(onClick = { chooser = "" }) { Text(texts.getString(R.string.cancel)) } })
}

@Composable
private fun PasswordList(state: VaultUiState, listState: LazyListState, model: VaultModel) {
    val texts = LocalResources.current
    val generation = model.editGeneration
    val passwordMatches = if (state.page == Page.SEARCH) state.searchPasswords.map { it.id }.toSet() else state.passwords.map { it.id }.toSet()
    val passwords = state.passwords.filter { it.id in passwordMatches && state.browseKind != BrowseKind.NOTE && when (state.browseFilter) {
            BrowseFilter.ALL -> true
            BrowseFilter.FAVORITE -> it.favorite
            BrowseFilter.WEAK -> it.id in state.checks.weakIds
            BrowseFilter.REPEATED -> it.id in state.checks.repeatedIds
        } }
    val noteMatches = if (state.page == Page.SEARCH) state.searchNotes.map { it.id }.toSet() else state.notes.map { it.id }.toSet()
    val notes = state.notes.filter { it.id in noteMatches && state.browseKind != BrowseKind.PASSWORD &&
        (state.browseFilter == BrowseFilter.ALL || state.browseFilter == BrowseFilter.FAVORITE && it.favorite) }
    val byKey = (passwords.map { HomeEntry(it.id, it.title, it.account, false, it.favorite) } + notes.map { HomeEntry(it.id, it.title, it.preview, true, it.favorite) }).associateBy { it.id to it.isNote }
    val orderedKeys = state.orderKeys.toHashSet()
    val entries = (state.orderKeys + byKey.keys.filter { it !in orderedKeys }).mapNotNull(byKey::get)
    LazyColumn(state = listState, contentPadding = PaddingValues(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 24.dp)) {
        item {
            if (state.vaults.size > 1) {
                BVaultContext(state.vault?.name.orEmpty(), state.busy, model::showVaults)
            }
            if (state.vault?.hasMasterPassword == false) Text(texts.getString(R.string.no_master), color = Muted, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp))
            BrowseControls(state, model)
            if (state.orderPending || !state.orderAvailable) Text(if (state.orderPending) texts.getString(R.string.order_updating) else texts.getString(R.string.order_not_updated), color = Muted, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp))
            val resultStatus = if (state.page == Page.SEARCH && state.searchPending) texts.getString(R.string.searching)
                else if (state.browseFilter == BrowseFilter.WEAK && state.checks.pendingEpochs.isNotEmpty()) texts.getString(R.string.appearance_summary, texts.getQuantityString(R.plurals.weak_count, entries.size, entries.size), texts.getQuantityString(R.plurals.pending_count, state.checks.pendingEpochs.size, state.checks.pendingEpochs.size))
                else texts.getQuantityString(if (state.page == Page.SEARCH && state.effectiveQuery.isNotEmpty()) R.plurals.search_result_count else R.plurals.item_count, entries.size, entries.size)
            Text(resultStatus, color = Muted, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp),
                minLines = 1, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.semantics { if (state.page == Page.SEARCH) liveRegion = LiveRegionMode.Polite })
            Spacer(Modifier.height(12.dp))
            Feedback(state)
        }
        itemsIndexed(entries, key = { _, item -> "${if (item.isNote) "note" else "password"}:${item.id}" }) { index, item ->
            val top = if (index == 0) 17.dp else 0.dp
            val bottom = if (index == entries.lastIndex) 17.dp else 0.dp
            Surface(onClick = { if (item.isNote) model.openNote(item.id) else model.openRecord(item.id) }, enabled = !state.busy, color = Card, shape = RoundedCornerShape(topStart = top, topEnd = top, bottomStart = bottom, bottomEnd = bottom)) {
                Column {
                    Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        BRecordMark(item.isNote)
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(item.title, lineHeight = 1.5.em, fontSize = businessSp(16.sp), color = Ink, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text(item.subtitle.ifEmpty { if (item.isNote) texts.getString(R.string.view_note) else texts.getString(R.string.account_empty) }, lineHeight = 1.5.em, fontSize = businessSp(13.sp), color = Muted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        if (item.favorite) Icon(bIcon("star_filled"), null, Modifier.size(13.dp), tint = Color(0xffbf9538))
                        Icon(bIcon("chevron_right"), null, tint = Muted)
                    }
                    if (index < entries.lastIndex) HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = Line)
                }
            }
        }
        if (entries.isEmpty()) item {
            val pending = state.checks.pendingEpochs.size
            val awaitingChecks = state.browseFilter == BrowseFilter.WEAK && pending > 0
            val failed = model.failedCheckCount
            val hasQuery = state.page == Page.SEARCH && state.effectiveQuery.isNotEmpty()
            val filtered = state.browseKind != BrowseKind.ALL || state.browseFilter != BrowseFilter.ALL
            val hasConditions = state.query.isNotEmpty() || filtered
            val textStyle = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle, letterSpacing = 0.sp)
            Column(Modifier.fillMaxWidth().padding(vertical = 35.dp, horizontal = 10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(bIcon("search"), null, tint = Muted.copy(alpha = 0.6f), modifier = Modifier.size(34.dp))
                Spacer(Modifier.height(21.dp))
                Text(when {
                    awaitingChecks && model.checksPaused -> texts.getString(R.string.checks_paused)
                    awaitingChecks && model.checksRunning -> texts.getString(R.string.checks_running)
                    awaitingChecks && failed > 0 -> texts.getString(R.string.checks_incomplete)
                    awaitingChecks -> texts.getString(R.string.checks_pending)
                    hasQuery -> texts.getString(R.string.search_empty)
                    filtered -> texts.getString(R.string.filter_empty)
                    else -> texts.getString(R.string.items_empty)
                }, color = Ink, fontWeight = FontWeight.Bold, fontSize = businessSp(16.sp), lineHeight = 1.5.em, textAlign = TextAlign.Center, style = textStyle)
                Spacer(Modifier.height(8.dp))
                Text(when {
                    awaitingChecks && !model.checksPaused && !model.checksRunning && failed > 0 -> texts.getQuantityString(R.plurals.failed_checks_retry, failed, failed)
                    awaitingChecks -> texts.getQuantityString(R.plurals.pending_checks_hint, pending, pending)
                    state.query.isNotEmpty() -> texts.getString(R.string.search_empty_hint)
                    filtered -> texts.getString(R.string.filter_empty_hint)
                    else -> texts.getString(R.string.items_empty_hint)
                }, color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.8.em, textAlign = TextAlign.Center, style = textStyle)
                if (awaitingChecks && (model.checksPaused || (!model.checksRunning && failed > 0))) {
                    TextButton(onClick = { if (model.checksPaused) model.continueChecks() else model.retryChecks() }, enabled = !state.busy) {
                        Text(if (model.checksPaused) texts.getString(R.string.continue_checks) else texts.getString(R.string.retry), fontWeight = FontWeight.SemiBold, fontSize = businessSp(14.sp), lineHeight = 1.5.em, style = textStyle)
                    }
                }
                TextButton(onClick = { if (hasConditions) model.clearBrowse(generation, state.page) else model.showAdd() }, enabled = !state.busy, colors = ButtonDefaults.textButtonColors(contentColor = if (awaitingChecks) Muted else Accent)) {
                    Text(if (hasConditions) texts.getString(R.string.clear_filters) else texts.getString(R.string.add_item), fontWeight = FontWeight.SemiBold, fontSize = businessSp(14.sp), lineHeight = 1.5.em, style = textStyle)
                }
            }
        }
    }
}

@Composable
private fun ChecksPage(state: VaultUiState, listState: LazyListState, model: VaultModel) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    val textStyle = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle, letterSpacing = 0.sp)
    val byId = state.passwords.filter { state.checksAvailable && it.id in state.checks.warningIds }.associateBy { it.id }
    val records = (state.orderKeys.filter { !it.second }.map { it.first } + byId.keys).distinct().mapNotNull(byId::get)
    val failedIds = model.failedCheckIds
    val unfinishedById = state.passwords.filter { state.checksAvailable && it.id in failedIds && it.id !in byId }.associateBy { it.id }
    val unfinished = (state.orderKeys.filter { !it.second }.map { it.first } + unfinishedById.keys).distinct().mapNotNull(unfinishedById::get)
    val checked = state.checks.checkedCount
    val input = model.editGeneration
    LazyColumn(state = listState, contentPadding = PaddingValues(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 24.dp)) {
        item {
            if (state.vaults.size > 1) BVaultNameContext(model, Page.CHECKS, input)
            Feedback(state)
            Column(Modifier.padding(top = 20.dp, bottom = 24.dp)) {
                Box(Modifier.size(40.dp).background(if (records.isNotEmpty()) colors.warningSurface else Soft, RoundedCornerShape(13.dp)), contentAlignment = Alignment.Center) {
                    Icon(bIcon(if (records.isNotEmpty()) "warning" else "info"), null, Modifier.size(20.dp), tint = if (records.isNotEmpty()) colors.warningInk else Muted)
                }
                Spacer(Modifier.height(17.dp))
                val pending = state.checks.pendingEpochs.size
                val headline = when {
                    !state.checksAvailable -> texts.getString(R.string.checks_cannot_run)
                    checked == 0 -> texts.getString(R.string.checks_empty)
                    records.isNotEmpty() -> texts.getQuantityString(R.plurals.warning_count, records.size, records.size)
                    pending > 0 -> texts.getString(R.string.no_issues_yet)
                    else -> texts.getString(R.string.checks_clear)
                }
                Box(Modifier.fillMaxWidth().heightIn(min = 65.dp)) {
                    if (records.isNotEmpty()) Row(verticalAlignment = Alignment.Bottom) {
                        Text(records.size.toString(), Modifier.alignByBaseline(), color = Ink, fontSize = businessSp(50.sp),
                            fontWeight = FontWeight.Medium, style = textStyle.copy(letterSpacing = (-0.7).sp), lineHeight = 1.3.em)
                        Text(texts.getQuantityString(R.plurals.attention_suffix, records.size), Modifier.weight(1f).alignByBaseline(), color = Ink, fontSize = businessSp(20.sp),
                            style = textStyle.copy(letterSpacing = (-0.7).sp), lineHeight = 1.3.em)
                    } else Text(headline, Modifier.semantics { heading() }, color = Ink, fontSize = businessSp(25.sp),
                        minLines = 2, fontWeight = FontWeight.Medium, style = textStyle.copy(letterSpacing = (-0.3).sp), lineHeight = 1.3.em)
                }
                val status = if (model.checksPaused && pending > 0) texts.getString(R.string.checks_paused) else if (checked > 0) { if (model.checksRunning) texts.getString(R.string.checked_progress, state.checks.ratedCount, checked) else texts.getQuantityString(R.plurals.checked_count, state.checks.ratedCount, state.checks.ratedCount) } else ""
                val detail = when {
                    model.failedCheckCount > 0 -> texts.getQuantityString(R.plurals.failed_checks, model.failedCheckCount, model.failedCheckCount) + if (pending > model.failedCheckCount) " · " + texts.getQuantityString(R.plurals.pending_count, pending - model.failedCheckCount, pending - model.failedCheckCount) else ""
                    pending > 0 -> texts.getQuantityString(R.plurals.pending_count, pending, pending)
                    else -> ""
                }
                Row(Modifier.fillMaxWidth().padding(top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(status + if (detail.isNotEmpty()) "\n$detail" else "", Modifier.weight(1f), color = Muted,
                        minLines = 2, fontSize = businessSp(13.sp), style = textStyle, lineHeight = 1.9.em)
                    Box(Modifier.width(96.dp).heightIn(min = 48.dp), contentAlignment = Alignment.CenterEnd) {
                        when {
                            !state.checksAvailable -> TextButton(onClick = model::showChecks, enabled = !state.busy) { Text(texts.getString(R.string.check_again)) }
                            model.checksPaused && pending > 0 -> TextButton(onClick = model::continueChecks, enabled = !state.busy) { Text(texts.getString(R.string.continue_checks)) }
                            model.checksRunning -> TextButton(onClick = model::cancelChecks, enabled = !state.busy) { Text(texts.getString(R.string.cancel_checks)) }
                            model.failedCheckCount > 0 -> TextButton(onClick = model::retryChecks, enabled = !state.busy) { Text(texts.getString(R.string.retry)) }
                        }
                    }
                }
            }
            if (state.checksAvailable && checked > 0) {
                Surface(color = Card, shape = RoundedCornerShape(14.dp)) {
                    Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min).padding(vertical = 17.dp)) {
                        listOf(texts.getString(R.string.weak_passwords) to state.checks.weakIds.size, texts.getString(R.string.repeated_passwords) to state.checks.repeatedIds.size).forEachIndexed { index, (label, count) ->
                            if (index > 0) Box(Modifier.width(1.dp).fillMaxHeight().background(Line))
                            Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(count.toString(), color = Ink, fontSize = businessSp(23.sp), fontWeight = FontWeight.Medium, style = textStyle, lineHeight = 1.5.em)
                                Text(label, color = Muted, fontSize = businessSp(13.sp), style = textStyle, lineHeight = (24f / 13).em)
                            }
                        }
                    }
                }
                Spacer(Modifier.height(24.dp))
            }
            if (records.isNotEmpty()) Text(texts.getString(R.string.items_with_warnings), Modifier.padding(top = 22.dp, bottom = 12.dp).heightIn(min = 32.dp).semantics { heading() },
                color = Ink, fontSize = businessSp(20.sp), fontWeight = FontWeight.Bold, style = textStyle.copy(letterSpacing = (-0.3).sp), lineHeight = 1.5.em)
        }
        items(records + unfinished, key = { it.id }) { record ->
            if (record.id == unfinished.firstOrNull()?.id) Text(texts.getString(R.string.checks_unfinished), Modifier.padding(top = 22.dp, bottom = 12.dp).semantics { heading() },
                color = Ink, fontSize = businessSp(20.sp), fontWeight = FontWeight.Bold, style = textStyle, lineHeight = 1.5.em)
            Surface(color = Card, shape = RoundedCornerShape(15.dp), modifier = Modifier.padding(bottom = 12.dp)) {
                Column(Modifier.padding(start = 15.dp, end = 15.dp, bottom = 15.dp)) {
                    Row(Modifier.fillMaxWidth().heightIn(min = 73.dp).padding(vertical = 13.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        BRecordMark(false)
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(record.title, color = Ink, fontSize = businessSp(16.sp), fontWeight = FontWeight.Bold, style = textStyle, lineHeight = 1.5.em, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text(listOfNotNull(texts.getString(R.string.password_warning_weak).takeIf { record.id in state.checks.weakIds }, texts.getString(R.string.password_warning_repeated).takeIf { record.id in state.checks.repeatedIds }, texts.getString(R.string.check_failed).takeIf { record.id in failedIds }).joinToString(" · "),
                                color = Muted, fontSize = businessSp(13.sp), style = textStyle, lineHeight = 1.5.em)
                        }
                    }
                    TextButton(onClick = { model.editCheckedRecord(state.vault?.id.orEmpty(), record.id, input) }, enabled = !state.busy,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(11.dp),
                        colors = ButtonDefaults.textButtonColors(containerColor = Soft, contentColor = Ink), contentPadding = PaddingValues(horizontal = 16.dp, vertical = 9.dp)) {
                        Text(texts.getString(R.string.review_edit), Modifier.weight(1f), fontSize = businessSp(13.sp), style = textStyle, lineHeight = 1.5.em, textAlign = TextAlign.Start)
                        Icon(bIcon("chevron_right"), null, Modifier.size(18.dp))
                    }
                }
            }
        }
        item {
            if (!state.checksAvailable) TextButton(onClick = model::showChecks, enabled = !state.busy) { Text(texts.getString(R.string.check_again), style = textStyle) }
            else if (records.isEmpty() && unfinished.isEmpty()) Column(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 35.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                if (checked == 0) Text(texts.getString(R.string.enter_password_to_check), color = Muted, fontSize = businessSp(13.sp), style = textStyle, lineHeight = 1.8.em)
                TextButton(onClick = { model.selectRoot(Page.PASSWORDS); model.changeBrowse(kind = BrowseKind.PASSWORD, filter = BrowseFilter.ALL, expectedGeneration = model.editGeneration, expectedPage = Page.PASSWORDS) }, enabled = !state.busy) {
                    Text(texts.getString(R.string.view_password_items), fontSize = businessSp(14.sp), style = textStyle, lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
                }
            } else Text(texts.getString(R.string.change_at_service_hint), Modifier.padding(vertical = 20.dp), color = Muted, fontSize = businessSp(13.sp), style = textStyle, lineHeight = 1.8.em)
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun AddPassword(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val draft = state.draft
    val editGeneration = model.editGeneration
    val page = state.page
    if (state.secretView.stale && page == Page.EDIT) {
        Notice(texts.getString(R.string.stale_draft_hint))
        state.record?.let { record -> TextButton(onClick = { model.requestLatestRecord(editGeneration, record.id, record.revision) }, enabled = !state.busy) { Text(texts.getString(R.string.reload_latest)) } }
    }
    FormField(texts.getString(R.string.name), draft.title, { value -> model.changeDraft(editGeneration, page) { copy(title = value) } }, required = true, enabled = !state.busy, placeholder = texts.getString(R.string.name_hint))
    FormField(texts.getString(R.string.account), draft.account, { value -> model.changeDraft(editGeneration, page) { copy(account = value) } }, enabled = !state.busy, placeholder = texts.getString(R.string.account_hint))
    val secrets = state.secretDraft
    val id = state.record?.id
    val revision = state.record?.revision
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        FormField(texts.getString(R.string.password), draft.password, { value -> model.changeDraft(editGeneration, page) { copy(password = value) } }, secret = true, enabled = !state.busy,
            reveal = state.passwordShown, onReveal = { model.togglePassword(editGeneration, page, id) })
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = { focus.clearFocus(); model.generateDraftPassword(editGeneration, page, id, revision) },
                enabled = !state.busy && !model.uiPreferencesSaving && !state.secretView.stale,
                shape = RoundedCornerShape(11.dp), contentPadding = PaddingValues(horizontal = 3.dp, vertical = 8.dp),
                modifier = Modifier.heightIn(min = 48.dp), colors = ButtonDefaults.textButtonColors(contentColor = Accent)) {
                Icon(bIcon("reload"), null, Modifier.size(17.dp)); Spacer(Modifier.width(7.dp))
                Text(texts.getString(R.string.generate_password), fontSize = businessSp(14.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
            }
            OutlinedButton(onClick = { focus.clearFocus(); model.openDraftGenerator(editGeneration, page, id, revision) },
                enabled = !state.busy && !model.uiPreferencesSaving && !state.secretView.stale,
                shape = RoundedCornerShape(11.dp), border = BorderStroke(1.dp, Line), modifier = Modifier.heightIn(min = 48.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Muted), contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp)) {
                Icon(bIcon("mixer"), null, Modifier.size(17.dp)); Spacer(Modifier.width(7.dp))
                Text(texts.getString(R.string.parameters), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            }
        }
    }
    val totpField: @Composable () -> Unit = {
        FormField(texts.getString(R.string.authenticator_setup_key), secrets.totpInput, { model.changeSecretInput(RecordSecretField.TOTP, it, editGeneration, page, id, revision) },
            required = !state.secretView.hasTotp, enabled = !state.busy, secret = true, placeholder = if (state.secretView.hasTotp) texts.getString(R.string.keep_key_hint) else texts.getString(R.string.setup_key_hint),
            reveal = secrets.totpShown, onReveal = { model.toggleSecretInput(RecordSecretField.TOTP, editGeneration, page, id, revision) })
    }
    if (state.secretView.hasTotp) BSecretEditSection(texts.getString(R.string.one_time_code), texts.getString(R.string.enabled), true, secrets.totpIntent, !state.busy,
        onReplace = { model.requestSecretChange(RecordSecretChange(RecordSecretField.TOTP, RecordSecretIntent.REPLACE), editGeneration, page, id, revision) },
        onRemove = { model.requestSecretChange(RecordSecretChange(RecordSecretField.TOTP, RecordSecretIntent.REMOVE), editGeneration, page, id, revision) },
        onKeep = { model.keepSecret(RecordSecretField.TOTP, editGeneration, page, id, revision) }, input = totpField)
    else {
        val enabled = secrets.totpIntent == RecordSecretIntent.REPLACE
        Row(Modifier.fillMaxWidth().toggleable(enabled, enabled = !state.busy, role = Role.Switch,
            onValueChange = { model.enableNewTotp(it, editGeneration, page, id, revision) }).semantics { contentDescription = texts.getString(R.string.one_time_code) }
            .heightIn(min = 65.dp).padding(vertical = 14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(texts.getString(R.string.one_time_code), color = Ink, lineHeight = (24f / 14).em, fontSize = businessSp(14.sp), fontWeight = FontWeight.Medium)
                Text(if (enabled) texts.getString(R.string.code_after_save) else texts.getString(R.string.service_key_hint), color = Muted, fontSize = businessSp(13.sp), lineHeight = (21f / 13).em)
            }
            BNewTotpSwitchMark(enabled)
        }
        if (enabled) totpField()
    }
    BSecretEditSection(texts.getString(R.string.recovery_codes), texts.getQuantityString(R.plurals.existing_recovery_codes, state.secretView.recoveryUsed.size, state.secretView.recoveryUsed.size), state.secretView.recoveryUsed.isNotEmpty(), secrets.recoveryIntent, !state.busy,
        onReplace = { model.requestSecretChange(RecordSecretChange(RecordSecretField.RECOVERY_CODES, RecordSecretIntent.REPLACE), editGeneration, page, id, revision) },
        onRemove = { model.requestSecretChange(RecordSecretChange(RecordSecretField.RECOVERY_CODES, RecordSecretIntent.REMOVE), editGeneration, page, id, revision) },
        onKeep = { model.keepSecret(RecordSecretField.RECOVERY_CODES, editGeneration, page, id, revision) }) {
        FormField(texts.getString(R.string.recovery_codes), secrets.recoveryInput, { model.changeSecretInput(RecordSecretField.RECOVERY_CODES, it, editGeneration, page, id, revision) },
            enabled = !state.busy, secret = true, multiline = true, placeholder = if (state.secretView.recoveryUsed.isNotEmpty()) texts.getString(R.string.keep_codes_hint) else texts.getString(R.string.optional),
            reveal = secrets.recoveryShown, onReveal = { model.toggleSecretInput(RecordSecretField.RECOVERY_CODES, editGeneration, page, id, revision) })
        Text(texts.getString(R.string.one_per_line), color = Muted, fontSize = businessSp(12.sp), lineHeight = 1.75.em)
    }
    FormField(texts.getString(R.string.notes_field), draft.notes, { value -> model.changeDraft(editGeneration, page) { copy(notes = value) } }, enabled = !state.busy, multiline = true, placeholder = texts.getString(R.string.notes_hint))
    GeneratorToggle(texts.getString(R.string.add_favorite), draft.favorite, !state.busy, divider = page == Page.EDIT) { value ->
        focus.clearFocus()
        model.changeDraft(editGeneration, page) { copy(favorite = value) }
    }
    if (model.editingFromChecks) Notice(texts.getString(R.string.change_password_hint))
    if (page == Page.EDIT) TextButton(onClick = model::requestDelete, enabled = !state.busy) { Text(texts.getString(R.string.delete_item), color = Error) }
}

@Composable
private fun EditNote(state: VaultUiState, model: VaultModel) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val draft = state.noteDraft
    val editGeneration = model.editGeneration
    val page = state.page
    FormField(texts.getString(R.string.title), draft.title, { value -> model.changeNoteDraft(editGeneration, page) { copy(title = value) } }, required = true, enabled = !state.busy, placeholder = texts.getString(R.string.title_hint))
    FormField(texts.getString(R.string.note_body), draft.content, { value -> model.changeNoteDraft(editGeneration, page) { copy(content = value) } }, enabled = !state.busy, multiline = true, placeholder = texts.getString(R.string.note_body_hint))
    GeneratorToggle(texts.getString(R.string.add_favorite), draft.favorite, !state.busy, divider = page == Page.NOTE_EDIT) { value ->
        focus.clearFocus()
        model.changeNoteDraft(editGeneration, page) { copy(favorite = value) }
    }
    if (page == Page.NOTE_EDIT) TextButton(onClick = model::requestDelete, enabled = !state.busy) { Text(texts.getString(R.string.delete_item), color = Error) }
}

@Composable
private fun NoteDetail(note: NoteRecord, model: VaultModel, cursorVisibility: NoteCursorVisibility) {
    val texts = LocalResources.current
    val editGeneration = model.editGeneration
    val bodyFocus = remember(note.id) { FocusRequester() }
    RecordIdentity(note.title, true, note.favorite, !model.state.busy, titleContent = { NoteReadingField(note, model, true, bodyFocus, cursorVisibility) }) {
        model.toggleFavorite(note.id, true, note.revision, editGeneration)
    }
    Surface(color = Card, shape = RoundedCornerShape(17.dp)) {
        NoteReadingField(note, model, false, bodyFocus, cursorVisibility)
    }
    Text(texts.getString(R.string.item_updated_at, recordDate(note.updatedAt)), Modifier.padding(vertical = 20.dp), color = Muted,
        fontSize = businessSp(13.sp), lineHeight = 1.8.em)
}

@Composable
@OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)
private fun NoteReadingField(note: NoteRecord, model: VaultModel, title: Boolean, bodyFocus: FocusRequester, cursorVisibility: NoteCursorVisibility) {
    val texts = LocalResources.current
    val state = model.state
    val input = model.editGeneration
    val reading = state.page == Page.NOTE_DETAIL
    val value = if (reading) { if (title) note.title else note.content }
        else { if (title) state.noteDraft.title else state.noteDraft.content }
    var editingValue by remember { mutableStateOf(TextFieldValue(value)) }
    val fieldValue = editingValue.copy(text = value)
    val inputVisibility = remember(note.id) { BringIntoViewRequester() }
    val visibilityScope = rememberCoroutineScope()
    val focus = LocalFocusManager.current
    val clipboard = LocalClipboard.current
    val copyAllowed by rememberUpdatedState(!state.busy)
    val guardedClipboard = remember(clipboard) { GuardedClipboard(clipboard) { copyAllowed } }
    val nativeMenu = remember { NativeTextMenuRelay() }
    val display = remember { VisualTransformation(::noteDisplayText) }
    SideEffect { editingValue = fieldValue }
    if (!title) {
        SideEffect { cursorVisibility.value = { editingValue } }
        DisposableEffect(cursorVisibility) { onDispose { cursorVisibility.clear() } }
    }
    CompositionLocalProvider(LocalClipboard provides guardedClipboard, LocalTextContextMenuDropdownProvider provides nativeMenu) {
        BasicTextField(value = fieldValue, onValueChange = { next ->
            if (!title && next.text != editingValue.text) cursorVisibility.contentChanged(next.text)
            editingValue = next
            if (next.text != value) model.changeNoteDraft(input, state.page) {
                if (title) copy(title = next.text) else copy(content = next.text)
            }
        }, enabled = !state.busy, readOnly = reading,
            onTextLayout = {
                if (!title) {
                    cursorVisibility.layout = it
                    if (cursorVisibility.consumeInputReveal()) visibilityScope.launch {
                        if (cursorVisibility.cursor() != null) cursorVisibility.track { inputVisibility.bringIntoView() }
                    }
                }
            },
            visualTransformation = if (title) VisualTransformation.None else display,
            modifier = Modifier.fillMaxWidth()
                .then(if (title) Modifier else Modifier.focusRequester(bodyFocus))
                .then(if (title) Modifier.semantics { heading() } else Modifier.heightIn(min = 240.dp).padding(20.dp))
                .then(if (title) Modifier else Modifier.then(NoteCursorVisibilityElement(cursorVisibility)).bringIntoViewRequester(inputVisibility))
                .onFocusChanged {
                    if (!title) cursorVisibility.focusChanged(it.isFocused)
                    if (it.isFocused) model.startNoteEdit(state.vault?.id, note.id, note.revision, input)
                }
                .semantics { contentDescription = if (title) texts.getString(R.string.title_required_label) else texts.getString(R.string.note_body) }
                .basicEditMenu(fieldValue) { editingValue = it; focus.clearFocus() },
            textStyle = TextStyle(color = Ink, fontSize = businessSp(if (title) 25.sp else 16.sp),
                fontWeight = if (title) FontWeight.Bold else FontWeight.Normal, lineHeight = if (title) 1.3.em else 1.9.em,
                lineHeightStyle = BLineHeightStyle), cursorBrush = SolidColor(Accent),
            keyboardOptions = KeyboardOptions(autoCorrectEnabled = false, keyboardType = KeyboardType.Text,
                imeAction = if (title) ImeAction.Next else ImeAction.Default),
            keyboardActions = KeyboardActions(onNext = { bodyFocus.requestFocus() }),
            decorationBox = { field ->
                BindNativeTextMenu(nativeMenu)
                Box(if (title) Modifier else Modifier.onGloballyPositioned { cursorVisibility.textCoordinates = it }) {
                    if (title && value.isEmpty()) Text(texts.getString(R.string.title_hint), color = Muted, fontSize = businessSp(25.sp),
                        lineHeight = 1.3.em, fontWeight = FontWeight.Bold)
                    if (!title && value.isEmpty()) Text(texts.getString(R.string.note_body_empty), color = Muted, fontSize = businessSp(16.sp), lineHeight = 1.9.em)
                    field()
                }
            })
    }
}

internal fun noteDisplayText(original: AnnotatedString): TransformedText {
    val text = original.text
    val cuts = mutableListOf<Int>()
    var paragraphStart = 0
    var boundaries: BreakIterator? = null
    var lineBoundaries: BreakIterator? = null
    while (paragraphStart < text.length) {
        val paragraphEnd = text.indexOf('\n', paragraphStart).let { if (it < 0) text.length else it }
        if (paragraphEnd - paragraphStart > 4096) {
            var directional = false
            var index = paragraphStart
            while (index < paragraphEnd) {
                val point = text.codePointAt(index)
                val direction = Character.getDirectionality(point)
                if (direction == Character.DIRECTIONALITY_RIGHT_TO_LEFT || direction == Character.DIRECTIONALITY_RIGHT_TO_LEFT_ARABIC ||
                    (direction >= Character.DIRECTIONALITY_LEFT_TO_RIGHT_EMBEDDING && direction <= Character.DIRECTIONALITY_POP_DIRECTIONAL_ISOLATE) || point == 0x200e) directional = true
                index += Character.charCount(point)
            }
            // 双向上下文保持原段落；其他长段只添加展示样式，不添加换行字符。
            if (!directional) {
                val iterator = boundaries ?: BreakIterator.getCharacterInstance(java.util.Locale.ROOT).apply {
                    setText(text); boundaries = this
                }
                val lines = lineBoundaries ?: BreakIterator.getLineInstance(java.util.Locale.ROOT).apply {
                    setText(text); lineBoundaries = this
                }
                var start = paragraphStart
                while (paragraphEnd - start > 512) {
                    val target = text.offsetByCodePoints(start, 256)
                    val wordEnd = lines.preceding(target + 1)
                    val end = if (wordEnd > start && wordEnd >= target - 64 && iterator.isBoundary(wordEnd)) wordEnd
                        else iterator.following(target - 1)
                    if (end == BreakIterator.DONE || end >= paragraphEnd) break
                    cuts += end
                    start = end
                }
            }
        }
        paragraphStart = paragraphEnd + 1
    }
    val shown = if (cuts.isEmpty()) original else AnnotatedString.Builder(original).apply {
        var start = 0
        for (end in cuts + text.length) {
            addStyle(ParagraphStyle(), start, end)
            start = end
        }
    }.toAnnotatedString()
    return TransformedText(shown, OffsetMapping.Identity)
}

@Composable
private fun RecordDetail(record: PasswordRecord, shown: Boolean, model: VaultModel) {
    val texts = LocalResources.current
    val editGeneration = model.editGeneration
    val vaultId = model.state.vault?.id.orEmpty()
    val enabled = !model.state.busy && !model.state.secretView.stale
    val edit = { model.startSecretEdit(vaultId, record.id, record.revision, editGeneration) }
    RecordIdentity(record.title, false, record.favorite, enabled) {
        model.toggleFavorite(record.id, false, record.revision, editGeneration)
    }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SecretCard(texts.getString(R.string.account), record.account) {
            RecordAction(texts.getString(R.string.copy_account), "copy", enabled && record.account.isNotEmpty(), true) {
                model.copyRecordField(vaultId, record.id, record.revision, editGeneration, ClipboardField.ACCOUNT)
            }
        }
        SecretCard(texts.getString(R.string.password), if (shown || record.password.isEmpty()) record.password else "••••••••••••", secret = record.password.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                RecordAction(if (shown) texts.getString(R.string.hide) else texts.getString(R.string.show), if (shown) "eye_closed" else "eye_open", enabled && record.password.isNotEmpty(), false) {
                    model.togglePassword(editGeneration, Page.DETAIL, record.id)
                }
                RecordAction(texts.getString(R.string.copy_password), "copy", enabled && record.password.isNotEmpty(), true) {
                    model.copyRecordField(vaultId, record.id, record.revision, editGeneration, ClipboardField.PASSWORD)
                }
            }
        }
    }
    val secrets = model.state.secretView
    if (secrets.hasTotp) Column(Modifier.padding(top = 20.dp)) {
        BTotpDetails(secrets, !model.state.busy && !secrets.stale,
            onCopy = { model.copyRecordField(vaultId, record.id, record.revision, editGeneration, ClipboardField.TOTP) },
            onEdit = { model.startSecretEdit(vaultId, record.id, record.revision, editGeneration) },
            onReload = { model.reloadSecretRecord(vaultId, record.id, record.revision, editGeneration) })
    }
    if (secrets.recoveryUsed.isNotEmpty()) key(vaultId, record.id) {
        Column(Modifier.padding(top = 20.dp)) {
            BRecoveryCodeDetails(secrets, !model.state.busy && !secrets.stale,
                onCopy = { model.copyRecordField(vaultId, record.id, record.revision, editGeneration, ClipboardField.RECOVERY, it) },
                onToggle = { model.toggleRecoveryCode(vaultId, record.id, record.revision, it, editGeneration) },
                onUsed = { index, used -> model.setRecoveryUsed(vaultId, record.id, record.revision, index, used, editGeneration) },
                onReload = { model.reloadSecretRecord(vaultId, record.id, record.revision, editGeneration) })
        }
    }
    if (model.state.error.isNotEmpty()) TextButton(onClick = { model.reloadSecretRecord(vaultId, record.id, record.revision, editGeneration) }, enabled = !model.state.busy) { Text(texts.getString(R.string.reload_record)) }
    if (record.notes.isNotEmpty()) {
        Column(Modifier.padding(top = 22.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(texts.getString(R.string.notes_field), color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em, fontWeight = FontWeight.Bold)
            Text(record.notes, color = Ink, fontSize = businessSp(16.sp), lineHeight = 1.9.em)
        }
    }
    val labels = if (model.state.checksAvailable) listOfNotNull(
        texts.getString(R.string.password_warning_weak).takeIf { record.id in model.state.checks.weakIds }, texts.getString(R.string.password_warning_repeated).takeIf { record.id in model.state.checks.repeatedIds }) else emptyList()
    if (labels.isNotEmpty()) Surface(color = Soft, shape = RoundedCornerShape(12.dp), modifier = Modifier.padding(top = 20.dp)) {
        Row(Modifier.padding(14.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Icon(bIcon("warning"), null, Modifier.padding(top = 3.dp).size(18.dp), tint = Muted)
            Column(Modifier.weight(1f)) {
                Text(labels.joinToString(" · "), color = Ink, fontSize = businessSp(13.sp), lineHeight = 1.8.em)
                TextButton(onClick = edit, enabled = enabled, contentPadding = PaddingValues(0.dp)) {
                    Text(texts.getString(R.string.review_edit), fontSize = businessSp(14.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
    Text(texts.getString(R.string.password_dates, recordDate(record.passwordChangedAt), recordDate(record.updatedAt)),
        Modifier.padding(vertical = 20.dp), color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.8.em)
}

@Composable
private fun recordDate(value: String?): String {
    val texts = LocalResources.current
    return runCatching {
        val date = BackupProtocol.displayDate(value.orEmpty())
        val locale = texts.configuration.locales[0]
        val format = if (locale.language == "zh") java.time.format.DateTimeFormatter.ofPattern("uuuu/M/d", locale)
            else java.time.format.DateTimeFormatter.ofLocalizedDate(java.time.format.FormatStyle.MEDIUM).withLocale(locale)
        format.format(date)
    }.getOrDefault(texts.getString(R.string.unrecorded))
}

@Composable
private fun RecordIdentity(title: String, note: Boolean, favorite: Boolean, enabled: Boolean,
                           titleContent: (@Composable () -> Unit)? = null, onFavorite: () -> Unit) {
    val texts = LocalResources.current
    Row(Modifier.fillMaxWidth().padding(top = 10.dp, bottom = 24.dp), verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        BRecordMark(note, size = 44)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(fieldLabel(if (note) texts.getString(R.string.title) else texts.getString(R.string.password_record), note), color = Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em,
                modifier = Modifier.semantics { if (note) contentDescription = texts.getString(R.string.title_required_label) })
            if (titleContent != null) titleContent()
            else Text(title, color = Ink, fontSize = businessSp(25.sp), lineHeight = 1.3.em, fontWeight = FontWeight.Bold,
                modifier = Modifier.semantics { heading() })
        }
        TextButton(onClick = onFavorite, enabled = enabled, shape = RoundedCornerShape(12.dp), contentPadding = PaddingValues(6.dp),
            modifier = Modifier.widthIn(min = 56.dp).heightIn(min = 56.dp).semantics { selected = favorite }) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Icon(bIcon(if (favorite) "star_filled" else "star"), null, Modifier.size(18.dp), tint = if (favorite) Accent else Muted)
                Text(if (favorite) texts.getString(R.string.favorited) else texts.getString(R.string.favorites), color = if (favorite) Accent else Muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
            }
        }
    }
}

@Composable
private fun RecordAction(text: String, icon: String, enabled: Boolean, highlighted: Boolean, onClick: () -> Unit) {
    TextButton(onClick = onClick, enabled = enabled, shape = RoundedCornerShape(11.dp), contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp),
        modifier = Modifier.heightIn(min = 48.dp), colors = ButtonDefaults.textButtonColors(
            containerColor = if (highlighted) Soft else Color.Transparent, contentColor = if (highlighted) Accent else Muted)) {
        Icon(bIcon(icon), null, Modifier.size(18.dp))
        Spacer(Modifier.width(7.dp))
        Text(text, fontSize = businessSp(14.sp), lineHeight = 1.5.em, fontWeight = if (highlighted) FontWeight.SemiBold else FontWeight.Normal)
    }
}

@Composable
private fun SecretCard(label: String, value: String, secret: Boolean = false, action: @Composable () -> Unit = {}) {
    val texts = LocalResources.current
    Surface(shape = RoundedCornerShape(18.dp), color = Card, border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(top = 8.dp, bottom = 20.dp)) {
            Row(Modifier.fillMaxWidth().heightIn(min = 48.dp).padding(bottom = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(label, Modifier.weight(1f), color = Muted, lineHeight = (24f / 14).em, fontSize = businessSp(14.sp))
                action()
            }
            Text(value.ifEmpty { texts.getString(R.string.not_entered) }, color = if (value.isEmpty()) Muted else Ink, fontSize = businessSp(19.sp), lineHeight = 1.65.em,
                letterSpacing = if (secret) 0.8.sp else 0.sp, fontFamily = if (secret) FontFamily.Monospace else FontFamily.Default)
        }
    }
}

@Composable
internal fun fieldLabel(label: String, required: Boolean): AnnotatedString {
    val requiredStyle = SpanStyle(color = Error, fontWeight = FontWeight.SemiBold)
    return buildAnnotatedString {
        append(label)
        if (required) withStyle(requiredStyle) { append(" *") }
    }
}

@Composable
internal fun FormField(
    label: String, value: String, onChange: (String) -> Unit, enabled: Boolean,
    placeholder: String = "", secret: Boolean = false, multiline: Boolean = false,
    reveal: Boolean = false, onReveal: (() -> Unit)? = null, onDone: (() -> Unit)? = null,
    focusRequester: FocusRequester? = null,
    search: Boolean = false, onClear: (() -> Unit)? = null,
    required: Boolean = false,
    keyboardType: KeyboardType = if (secret) KeyboardType.Password else KeyboardType.Text,
) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    var editingValue by remember { mutableStateOf(TextFieldValue(value)) }
    val fieldValue = editingValue.copy(text = value)
    var lastText by remember(value) { mutableStateOf(value) }
    val clipboard = LocalClipboard.current
    val copyAllowed by rememberUpdatedState(enabled && (!secret || reveal))
    val guardedClipboard = remember(clipboard) { GuardedClipboard(clipboard) { copyAllowed } }
    val nativeMenu = remember { NativeTextMenuRelay() }
    SideEffect { editingValue = fieldValue }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (!search) Text(fieldLabel(label, required), color = if (focused) Accent else Ink, fontSize = businessSp(13.sp),
            lineHeight = (20f / 13).em, fontWeight = FontWeight.SemiBold,
            modifier = Modifier.semantics { if (required) contentDescription = texts.getString(R.string.required_label, label) })
        CompositionLocalProvider(LocalClipboard provides guardedClipboard, LocalTextContextMenuDropdownProvider provides nativeMenu) {
        BasicTextField(
            value = fieldValue,
            onValueChange = { next ->
                editingValue = next
                if (next.text != lastText) {
                    lastText = next.text
                    onChange(next.text)
                }
            },
            enabled = enabled,
            modifier = Modifier.fillMaxWidth().then(if (focusRequester == null) Modifier else Modifier.focusRequester(focusRequester)).semantics { contentDescription = if (required) texts.getString(R.string.required_label, label) else label }
                .basicEditMenu(fieldValue) {
                    editingValue = it
                    focus.clearFocus()
                },
            singleLine = !multiline, minLines = if (multiline) 6 else 1, maxLines = if (multiline) 6 else 1,
            textStyle = TextStyle(color = if (enabled) Ink else Muted, fontSize = businessSp(16.sp), lineHeight = 1.6.em,
                lineHeightStyle = BLineHeightStyle),
            cursorBrush = SolidColor(Accent), interactionSource = interaction,
            visualTransformation = if (secret && !reveal) PasswordVisualTransformation() else VisualTransformation.None,
            keyboardOptions = KeyboardOptions(
                autoCorrectEnabled = false,
                keyboardType = keyboardType,
                imeAction = if (onDone != null) ImeAction.Done else if (multiline) ImeAction.Default else ImeAction.Next,
            ),
            keyboardActions = KeyboardActions(onDone = { focus.clearFocus(); onDone?.invoke() }),
            decorationBox = { input ->
                BindNativeTextMenu(nativeMenu)
                Row(
                    Modifier.fillMaxWidth().heightIn(min = if (multiline) 150.dp else if (search) 48.dp else 50.dp)
                        .background(if (search) LocalBThemeColors.current.searchBackground else Card, RoundedCornerShape(13.dp))
                        .border(1.dp, if (focused) Accent else if (search) Color.Transparent else Line, RoundedCornerShape(13.dp))
                        .padding(start = 14.dp, end = if (onReveal == null && onClear == null) 14.dp else 4.dp),
                    verticalAlignment = if (multiline) Alignment.Top else Alignment.CenterVertically,
                ) {
                    Box(Modifier.weight(1f).padding(vertical = 13.dp)) {
                        if (value.isEmpty()) Text(placeholder, lineHeight = 1.6.em, fontSize = businessSp(14.sp), color = Muted)
                        input()
                    }
                    if (onReveal != null) TextButton(onClick = onReveal, enabled = enabled) { Text(if (reveal) texts.getString(R.string.hide) else texts.getString(R.string.show), lineHeight = (20f / 13).em, fontSize = businessSp(13.sp)) }
                    if (onClear != null) {
                        if (value.isNotEmpty()) IconButton(onClick = onClear, enabled = enabled) { Icon(bIcon("cross"), texts.getString(R.string.clear_search), Modifier.size(18.dp), tint = Muted) }
                        else Spacer(Modifier.size(48.dp))
                    }
                }
            },
        )
    }
    }
}

@Composable
internal fun PrimaryButton(label: String, busy: Boolean, enabled: Boolean = true, onClick: () -> Unit) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val colors = LocalBThemeColors.current
    Button(onClick = { focus.clearFocus(); onClick() }, enabled = !busy && enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp).semantics {
        if (busy) { stateDescription = texts.getString(R.string.processing_accessibility); liveRegion = LiveRegionMode.Polite }
    }, colors = ButtonDefaults.buttonColors(containerColor = colors.accentFill, contentColor = colors.onAccent), shape = RoundedCornerShape(14.dp), contentPadding = PaddingValues(14.dp)) {
        Box(Modifier.size(20.dp)) {
            if (busy) CircularProgressIndicator(Modifier.fillMaxSize(), color = colors.onAccent, strokeWidth = 2.dp)
        }
        Text(label, Modifier.weight(1f), lineHeight = (20f / 16).em, fontSize = businessSp(16.sp), fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
        Spacer(Modifier.size(20.dp))
    }
}

@Composable
private fun LockMark(size: Int) {
    Box(Modifier.size(size.dp).background(if (size >= 80) Soft else Color(0xffe2f1e7), RoundedCornerShape((size * 0.32f).dp)), contentAlignment = Alignment.Center) {
        Icon(bIcon("lock"), null, tint = if (size >= 80) Ink else Color(0xff318257), modifier = Modifier.size((size * 0.5f).dp))
    }
}

@Composable
private fun EmptyState(title: String, description: String) {
    Column(Modifier.fillMaxWidth().padding(vertical = 35.dp, horizontal = 10.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Icon(bIcon("lock"), null, tint = Muted, modifier = Modifier.size(34.dp))
        Text(title, color = Ink, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
        Text(description, color = Muted, fontSize = businessSp(13.sp), textAlign = TextAlign.Center, lineHeight = (23f / 13).em)
    }
}

@Composable
private fun Notice(text: String) {
    Surface(color = Soft, shape = RoundedCornerShape(12.dp)) { Text(text, Modifier.padding(14.dp), color = Ink, fontSize = businessSp(13.sp), lineHeight = (23f / 13).em) }
}

@Composable
private fun Feedback(state: VaultUiState) {
    if (state.error.isNotEmpty()) Text(state.error.localized(), Modifier.fillMaxWidth().padding(vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Assertive }, color = Error, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
    if (state.notice.isNotEmpty()) Text(state.notice.localized(), Modifier.padding(vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = Accent, lineHeight = 1.5.em, fontSize = businessSp(14.sp))
}
