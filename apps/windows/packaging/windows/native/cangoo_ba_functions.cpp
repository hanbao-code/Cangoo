// SPDX-License-Identifier: MIT
// 许可见本目录 LICENSE；WiX SDK 及其库保留各自的 MS-RL 许可。
#include <windows.h>
#include <commctrl.h>
#include <objbase.h>
#include <msiquery.h>
#include <dutil.h>
#include <BootstrapperApplication.h>
#include <BalBaseBAFunctions.h>
#include <BalBaseBAFunctionsProc.h>

#include <atomic>
#include <new>
#include <string>
#include "user_data_cleanup.h"
#ifdef CANGOO_MSI_UPGRADE_CODE
#include "install_location.h"
#endif

namespace {
constexpr UINT finish_message = WM_APP + 0x251;
constexpr UINT cleanup_message = WM_APP + 0x252;
constexpr WORD clear_control = BAFUNCTIONS_FIRST_ASSIGN_CONTROL_ID + 1;
HMODULE module_handle = nullptr;

class CangooFunctions final : public CBalBaseBAFunctions {
 public:
  explicit CangooFunctions(HMODULE module) : CBalBaseBAFunctions(module) {}

  HRESULT STDMETHODCALLTYPE OnCreate(IBootstrapperEngine* engine, BOOTSTRAPPER_COMMAND* command) override {
    if (!engine || !command) return E_INVALIDARG;
    interactive_ = command->display == BOOTSTRAPPER_DISPLAY_FULL &&
        command->relationType == BOOTSTRAPPER_RELATION_NONE && !command->fPassthrough &&
        (command->resumeType == BOOTSTRAPPER_RESUME_TYPE_NONE || command->resumeType == BOOTSTRAPPER_RESUME_TYPE_ARP);
    const HRESULT result = CBalBaseBAFunctions::OnCreate(engine, command);
    if (FAILED(result)) return result;
    SetResult(L"");
    engine->SetVariableNumeric(L"CangooCleanupPending", 0);
#ifdef CANGOO_MSI_UPGRADE_CODE
    installed_ = cangoo::install::ReadInstalledLocation(CANGOO_MSI_UPGRADE_CODE);
    const bool existing = installed_.state == cangoo::install::InstalledState::unique;
    engine->SetVariableNumeric(L"CangooInstalled", existing ? 1 : 0);
    engine->SetVariableString(L"InstallFolder", existing ? installed_.path.c_str() : DefaultFolder(false).c_str(), FALSE);
#endif
    return result;
  }

  HRESULT STDMETHODCALLTYPE OnThemeControlLoading(LPCWSTR name, BOOL* processed, WORD* id,
                                                 DWORD* automatic_behavior) override {
    if (name && wcscmp(name, L"CangooClearUserData") == 0) {
      *processed = TRUE;
      *id = clear_control;
      // WiX 的 EXCLUDE_ENABLED | EXCLUDE_VALUE；身份与本轮选择由本对象管理。
      *automatic_behavior = 0x1 | 0x8;
    } else if (name && wcscmp(name, L"CangooCleanupInfo") == 0) {
      *processed = TRUE;
      *id = clear_control + 1;
      // 身份说明由本对象固定更新；换页不能恢复成允许清理的默认文案。
      *automatic_behavior = 0x10;
    }
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnThemeLoaded(HWND window) override {
    const HRESULT status = CBalBaseBAFunctions::OnThemeLoaded(window);
    LONGLONG language = 0;
    if (FAILED(status)) return status;
    const HRESULT language_status = m_pEngine->GetVariableNumeric(L"WixStdBALanguageId", &language);
    if (FAILED(language_status) || (language != 1033 && language != 2052)) return E_UNEXPECTED;
    english_ = language == 1033;
    language_ready_ = true;
    const bool available = interactive_ && cangoo::cleanup::CurrentIdentityMatches();
    if (checkbox_) EnableWindow(checkbox_, available);
    if (info_label_ && !available)
      SetWindowTextW(info_label_, Text(L"本次无法确认当前用户身份，卸载时将保留全部用户资料。",
                                      L"Your user identity cannot be confirmed for this session. All user data will be kept."));
    if (logo_) SetWindowTextW(logo_, Text(L"小仓", L"Cangoo"));
#ifdef CANGOO_MSI_UPGRADE_CODE
    if (installed_.state == cangoo::install::InstalledState::unique)
      m_pEngine->SetVariableString(L"WixStdBAScope", installed_.machine ? L"PerMachine" : L"PerUser", FALSE);
#endif
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnThemeControlLoaded(LPCWSTR name, WORD, HWND control, BOOL*) override {
    if (!name) return S_OK;
    if (wcscmp(name, L"CangooClearUserData") == 0) {
      checkbox_ = control;
      // 控件在 OnThemeLoaded 前创建；语言和身份就绪前保持不可选。
      EnableWindow(control, FALSE);
      SendMessageW(control, BM_SETCHECK, BST_UNCHECKED, 0);
    } else if (wcscmp(name, L"CangooCleanupInfo") == 0) info_label_ = control;
    else if (wcscmp(name, L"CangooLogo") == 0) logo_ = control;
    else if (wcscmp(name, L"UninstallButton") == 0) uninstall_button_ = control;
    else if (wcscmp(name, L"CangooCleanupResult") == 0) result_label_ = control;
    else if (wcscmp(name, L"SuccessCloseButton") == 0) close_button_ = control;
    else if (wcscmp(name, L"ProgressCancelButton") == 0) cancel_button_ = control;
#ifdef CANGOO_MSI_UPGRADE_CODE
    else if (wcscmp(name, L"InstallFolder") == 0) install_edit_ = control;
#endif
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnThemeControlWmCommand(WPARAM command, LPCWSTR name, WORD, HWND control,
                                                   BOOL* processed, LRESULT* result) override {
    if (HIWORD(command) == BN_CLICKED && name && wcscmp(name, L"CangooClearUserData") == 0) {
      selected_ = interactive_ && language_ready_ && IsWindowEnabled(control) &&
          SendMessageW(control, BM_GETCHECK, 0, 0) == BST_CHECKED;
      m_pEngine->SetVariableNumeric(L"CangooClearUserData", selected_ ? 1 : 0);
      if (uninstall_button_) SetWindowTextW(uninstall_button_, selected_
          ? Text(L"卸载并清除所选资料", L"Uninstall and clear selected data")
          : Text(L"卸载", L"Uninstall"));
      *processed = TRUE;
      *result = 0;
    } else if (name && wcscmp(name, L"SuccessCloseButton") == 0 && finishing_) {
      *processed = TRUE;
      *result = 0;
    }
#ifdef CANGOO_MSI_UPGRADE_CODE
    else if (HIWORD(command) == BN_CLICKED && name &&
             (wcscmp(name, L"CangooPerUser") == 0 || wcscmp(name, L"CangooPerMachine") == 0)) {
      const bool machine = wcscmp(name, L"CangooPerMachine") == 0;
      std::wstring current = Variable(L"InstallFolder");
      if (install_edit_) {
        wchar_t text[32768]{};
        GetWindowTextW(install_edit_, text, 32768);
        current = text;
      }
      if (current.empty() || _wcsicmp(current.c_str(), DefaultFolder(false).c_str()) == 0 ||
          _wcsicmp(current.c_str(), DefaultFolder(true).c_str()) == 0) {
        const auto next = DefaultFolder(machine);
        m_pEngine->SetVariableString(L"InstallFolder", next.c_str(), FALSE);
        if (install_edit_) SetWindowTextW(install_edit_, next.c_str());
      } else {
        // 标准单选框会刷新当前页；先保存仍在编辑框中的自选路径，避免被旧变量覆盖。
        m_pEngine->SetVariableString(L"InstallFolder", current.c_str(), FALSE);
      }
      // 保留标准主题的 RadioButtons 自动绑定；这里只同步默认路径。
    }
#endif
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnPlanBegin(DWORD, BOOL* cancel) override {
    // PlanBegin 时 WixBundleAction 尚未发布；这里只冻结本轮的用户选择。
    requested_ = !*cancel && interactive_ && selected_;
    armed_ = false;
    package_removing_ = false;
    package_removed_ = false;
    finish_ready_ = false;
    cleanup_ready_ = false;
    result_ready_ = false;
    m_pEngine->SetVariableNumeric(L"CangooCleanupPending", 0);
    m_pEngine->SetVariableString(L"CangooInstallError", L"", FALSE);
    SetResult(L"");
    wchar_t message[112]{};
    swprintf_s(message, L"CANGOO_CLEANUP_PLAN interactive=%d selected=%d requested=%d",
               interactive_, selected_.load(), requested_);
    m_pEngine->Log(BOOTSTRAPPER_LOG_LEVEL_STANDARD, message);
    return S_OK;
  }

#ifdef CANGOO_MSI_UPGRADE_CODE
  HRESULT STDMETHODCALLTYPE OnPlanPackageBegin(LPCWSTR package, BOOTSTRAPPER_PACKAGE_STATE, BOOL,
      BOOTSTRAPPER_PACKAGE_CONDITION_RESULT, BOOTSTRAPPER_PACKAGE_CONDITION_RESULT,
      BOOTSTRAPPER_REQUEST_STATE, BOOTSTRAPPER_CACHE_TYPE,
      BOOTSTRAPPER_REQUEST_STATE* requested, BOOTSTRAPPER_CACHE_TYPE*, BOOL* cancel) override {
    if (!package || wcscmp(package, L"CangooMsi") != 0 || *cancel ||
        (*requested != BOOTSTRAPPER_REQUEST_STATE_PRESENT && *requested != BOOTSTRAPPER_REQUEST_STATE_FORCE_PRESENT &&
         *requested != BOOTSTRAPPER_REQUEST_STATE_REPAIR)) return S_OK;
    using cangoo::install::InstalledState;
    if (installed_.state == InstalledState::failed || installed_.state == InstalledState::conflict)
      return LocationFailure(Text(L"无法确认已有安装位置。请先关闭，再检查已安装应用。",
                                  L"The existing installation could not be identified. Close setup and check Installed Apps."));
    const bool existing = installed_.state == InstalledState::unique;
    const auto target = Variable(L"InstallFolder");
    const auto scope = Variable(L"WixStdBAScope");
    if (scope != L"PerUser" && scope != L"PerMachine")
      return LocationFailure(Text(L"无法确认安装范围，请关闭后重新打开安装程序。",
                                  L"The installation scope is unavailable. Close and reopen setup."));
    if (existing && installed_.machine != (scope == L"PerMachine"))
      return LocationFailure(Text(L"修复或更新将沿用原安装范围。请关闭后重新打开安装程序。",
                                  L"Repair and update must retain the installed scope. Close and reopen setup."));
#ifdef CANGOO_INSTALL_TEST_ROOT
    if (_wcsicmp(target.c_str(), CANGOO_INSTALL_TEST_ROOT) != 0)
      return LocationFailure(L"Acceptance installation directory does not match the fixed build configuration.");
#endif
    const auto check = cangoo::install::ValidateInstallFolder(target, existing ? installed_.path : L"");
    if (check != cangoo::install::FolderStatus::valid)
      return LocationFailure(Text(L"安装位置不可用。请重新打开安装程序，选择新的空文件夹。",
                                  L"The install location is unavailable. Reopen setup and select a new empty folder."));
    return S_OK;
  }
#endif

  HRESULT STDMETHODCALLTYPE OnPlanComplete(HRESULT status) override {
    if (FAILED(status)) { requested_ = false; armed_ = false; }
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnExecutePackageBegin(LPCWSTR package, BOOL execute,
      BOOTSTRAPPER_ACTION_STATE action, INSTALLUILEVEL, BOOL, BOOL* cancel) override {
    if (package && wcscmp(package, L"CangooMsi") == 0) {
      package_removed_ = false;
      package_removing_ = execute && !*cancel && action == BOOTSTRAPPER_ACTION_STATE_UNINSTALL;
      armed_ = requested_ && package_removing_;
      m_pEngine->SetVariableNumeric(L"CangooCleanupPending", armed_ ? 1 : 0);
      SetResult(armed_ ? Text(L"程序卸载后将清理所选资料。", L"Selected data will be cleared after the program is uninstalled.") : L"");
      wchar_t message[112]{};
      swprintf_s(message, L"CANGOO_CLEANUP_EXECUTE execute=%d action=%u armed=%d",
                 execute, static_cast<unsigned>(action), armed_);
      m_pEngine->Log(BOOTSTRAPPER_LOG_LEVEL_STANDARD, message);
    }
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnExecutePackageComplete(LPCWSTR package, HRESULT status,
      BOOTSTRAPPER_APPLY_RESTART restart, BOOTSTRAPPER_EXECUTEPACKAGECOMPLETE_ACTION,
      BOOTSTRAPPER_EXECUTEPACKAGECOMPLETE_ACTION*) override {
    if (package && wcscmp(package, L"CangooMsi") == 0)
      package_removed_ = package_removing_ && SUCCEEDED(status) && restart == BOOTSTRAPPER_APPLY_RESTART_NONE;
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnExecuteComplete(HRESULT status) override {
    if (armed_ && package_removed_ && SUCCEEDED(status) && IsWindow(m_hwndParent)) {
      // MSI 已执行完毕；在标准 BA 排入结果页前收起最后的取消／关闭入口。
      finish_ready_ = true;
      SendMessageW(m_hwndParent, finish_message, 0, 0);
    }
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE OnApplyComplete(HRESULT status, BOOTSTRAPPER_APPLY_RESTART restart,
      BOOTSTRAPPER_APPLYCOMPLETE_ACTION, BOOTSTRAPPER_APPLYCOMPLETE_ACTION*) override {
    const bool run = armed_ && package_removed_ && interactive_ && SUCCEEDED(status) &&
        restart == BOOTSTRAPPER_APPLY_RESTART_NONE && IsWindow(m_hwndParent);
    armed_ = false;
    requested_ = false;
    selected_ = false;
    if (IsWindow(m_hwndParent)) {
      // 消息只是唤醒 UI；执行资格只由本对象的可信回调授予，不能从 wParam 取得。
      cleanup_ready_ = run;
      result_ready_ = true;
      SendMessageW(m_hwndParent, cleanup_message, 0, 0);
    }
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE WndProc(HWND window, UINT message, WPARAM wparam, LPARAM,
                                    BOOL* processed, LRESULT* result) override {
    if (message == finish_message) {
      *processed = TRUE; *result = 0;
      if (!finish_ready_.exchange(false)) return S_OK;
      finishing_ = true;
      SetResult(Text(L"程序已卸载，正在清理所选资料…", L"The program has been uninstalled. Clearing selected data…"));
      EnableMenuItem(GetSystemMenu(window, FALSE), SC_CLOSE, MF_BYCOMMAND | MF_GRAYED);
      if (close_button_) EnableWindow(close_button_, FALSE);
      if (cancel_button_) EnableWindow(cancel_button_, FALSE);
      *processed = TRUE; *result = 0;
    } else if (message == cleanup_message) {
      *processed = TRUE; *result = 0;
      if (!result_ready_.exchange(false)) return S_OK;
      if (cleanup_ready_.exchange(false)) {
        const auto outcome = cangoo::cleanup::DeleteCurrentUserData();
        SetResult(Describe(outcome));
        wchar_t log[128]{};
        swprintf_s(log, L"CANGOO_CLEANUP_RESULT status=%u deleted=%lu kept_mask=%lu error=%lu",
                   static_cast<unsigned>(outcome.status), outcome.deleted_count, outcome.retained_mask, outcome.error);
        m_pEngine->Log(BOOTSTRAPPER_LOG_LEVEL_STANDARD, log);
      } else {
        SetResult(Text(L"用户资料已保留。", L"Your data has been kept."));
      }
      finishing_ = false;
      m_pEngine->SetVariableNumeric(L"CangooCleanupPending", 0);
      EnableMenuItem(GetSystemMenu(window, FALSE), SC_CLOSE, MF_BYCOMMAND | MF_ENABLED);
      if (close_button_) EnableWindow(close_button_, TRUE);
      *processed = TRUE; *result = 0;
    } else if (finishing_ && message == WM_SYSCOMMAND && (wparam & 0xfff0) == SC_CLOSE) {
      *processed = TRUE; *result = 0;
    }
    return S_OK;
  }

 private:
  LPCWSTR Text(LPCWSTR chinese, LPCWSTR english) const { return english_ ? english : chinese; }

#ifdef CANGOO_MSI_UPGRADE_CODE
  std::wstring DefaultFolder(bool machine) const {
#ifdef CANGOO_INSTALL_TEST_ROOT
    (void)machine;
    return CANGOO_INSTALL_TEST_ROOT;
#else
    return cangoo::install::DefaultInstallFolder(machine);
#endif
  }

  std::wstring Variable(LPCWSTR name) const {
    wchar_t text[32768]{};
    SIZE_T length = 32768;
    return SUCCEEDED(m_pEngine->GetVariableString(name, text, &length)) ? std::wstring(text) : std::wstring{};
  }

  HRESULT LocationFailure(LPCWSTR message) {
    m_pEngine->SetVariableString(L"CangooInstallError", message, FALSE);
    return HRESULT_FROM_WIN32(ERROR_BAD_PATHNAME);
  }
  cangoo::install::InstalledLocation installed_;
  HWND install_edit_ = nullptr;
#endif

  void SetResult(const std::wstring& message) {
    if (m_pEngine) m_pEngine->SetVariableString(L"CangooCleanupResult", message.c_str(), FALSE);
    if (result_label_) SetWindowTextW(result_label_, message.c_str());
  }

  std::wstring Describe(const cangoo::cleanup::Result& outcome) const {
    using cangoo::cleanup::Status;
    if (outcome.status == Status::complete)
      return Text(L"所选的默认库、设置和安全状态已清理。其他库与所有备份均保留。",
                  L"The selected default vault, settings and security state have been cleared. Other vaults and all backups are kept.");
    if (outcome.status == Status::identity_unknown)
      return Text(L"无法确认当前用户身份，用户资料均已保留。", L"Your user identity could not be confirmed. Your data has been kept.");
    if (outcome.status == Status::failed)
      return Text(L"所选资料未能清理，均已保留。请检查文件占用、权限或路径。",
                  L"The selected data could not be cleared and has been kept. Check file use, permissions or paths.");
    return std::wstring(Text(L"资料仅部分清理。已清：", L"Data was only partly cleared. Cleared: ")) +
        Labels(outcome.deleted_mask) + Text(L"；保留：", L"; kept: ") + Labels(outcome.retained_mask);
  }

  std::wstring Labels(DWORD mask) const {
    constexpr LPCWSTR names[] = {L"pdm.db", L"pdm.db-wal", L"pdm.db-shm", L"pdm.db-journal", L"settings.json", L"security.st"};
    std::wstring result;
    for (unsigned index = 0; index < 6; ++index) if (mask & (1u << index)) {
      if (!result.empty()) result += L", ";
      result += names[index];
    }
    return result;
  }

  bool interactive_ = false;
  bool english_ = false;
  bool language_ready_ = false;
  bool armed_ = false;
  bool requested_ = false;
  bool package_removing_ = false;
  bool package_removed_ = false;
  std::atomic<bool> selected_{false};
  std::atomic<bool> finishing_{false};
  std::atomic<bool> finish_ready_{false};
  std::atomic<bool> cleanup_ready_{false};
  std::atomic<bool> result_ready_{false};
  HWND checkbox_ = nullptr;
  HWND info_label_ = nullptr;
  HWND logo_ = nullptr;
  HWND uninstall_button_ = nullptr;
  HWND result_label_ = nullptr;
  HWND close_button_ = nullptr;
  HWND cancel_button_ = nullptr;
};

CangooFunctions* instance = nullptr;
}  // namespace

extern "C" BOOL WINAPI DllMain(HMODULE module, DWORD reason, LPVOID) {
  if (reason == DLL_PROCESS_ATTACH) { module_handle = module; DisableThreadLibraryCalls(module); }
  return TRUE;
}

extern "C" __declspec(dllexport) HRESULT WINAPI BAFunctionsCreate(const BA_FUNCTIONS_CREATE_ARGS* args,
                                                                 BA_FUNCTIONS_CREATE_RESULTS* results) {
  if (!args || !results || instance) return E_INVALIDARG;
  instance = new (std::nothrow) CangooFunctions(module_handle);
  if (!instance) return E_OUTOFMEMORY;
  const HRESULT status = instance->OnCreate(args->pEngine, args->pCommand);
  if (FAILED(status)) { instance->Release(); instance = nullptr; return status; }
  results->pfnBAFunctionsProc = BalBaseBAFunctionsProc;
  results->pvBAFunctionsProcContext = instance;
  return S_OK;
}

extern "C" __declspec(dllexport) void WINAPI BAFunctionsDestroy(const BA_FUNCTIONS_DESTROY_ARGS*,
                                                               BA_FUNCTIONS_DESTROY_RESULTS*) {
  if (instance) { instance->Release(); instance = nullptr; }
}
