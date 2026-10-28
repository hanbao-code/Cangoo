// SPDX-License-Identifier: MIT
// 许可见本目录 LICENSE。
#include "user_data_cleanup.h"
#include "user_identity.h"
#include <exception>

#include <shlobj.h>
#include <wtsapi32.h>

#include <array>
#include <memory>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#if defined(CANGOO_CLEANUP_PRODUCTION) && \
    (defined(CANGOO_CLEANUP_ACCEPTANCE) || defined(CANGOO_CLEANUP_TEST_ROOT))
#error Production cleanup must not contain acceptance roots.
#endif
#if defined(CANGOO_CLEANUP_ACCEPTANCE) != defined(CANGOO_CLEANUP_TEST_ROOT)
#error Acceptance cleanup requires both the explicit flag and a fixed test root.
#endif

namespace cangoo::cleanup {
namespace {

class Handle {
public:
    explicit Handle(HANDLE value = INVALID_HANDLE_VALUE) noexcept : value_(value) {}
    ~Handle() { reset(); }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
    Handle(Handle&& other) noexcept : value_(std::exchange(other.value_, INVALID_HANDLE_VALUE)) {}
    HANDLE get() const noexcept { return value_; }
    HANDLE release() noexcept { return std::exchange(value_, INVALID_HANDLE_VALUE); }
    explicit operator bool() const noexcept { return value_ && value_ != INVALID_HANDLE_VALUE; }
    void reset(HANDLE value = INVALID_HANDLE_VALUE) noexcept {
        if (*this) CloseHandle(value_);
        value_ = value;
    }
private:
    HANDLE value_;
};

struct FolderFree {
    void operator()(wchar_t* value) const noexcept { CoTaskMemFree(value); }
};

bool IdentityMatches(DWORD process_session, DWORD token_session,
                     bool active, bool same_sid) noexcept {
    return process_session != 0 && process_session == token_session && active && same_sid;
}

bool SameUserLogon(HANDLE first, HANDLE second) {
    alignas(TOKEN_USER) BYTE left[sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE]{};
    alignas(TOKEN_USER) BYTE right[sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE]{};
    DWORD needed = 0, first_session = 0, second_session = 0;
    TOKEN_STATISTICS first_stats{}, second_stats{};
    if (!GetTokenInformation(first, TokenUser, left, sizeof(left), &needed) ||
        !GetTokenInformation(second, TokenUser, right, sizeof(right), &needed) ||
        !GetTokenInformation(first, TokenSessionId, &first_session, sizeof(first_session), &needed) ||
        !GetTokenInformation(second, TokenSessionId, &second_session, sizeof(second_session), &needed) ||
        !GetTokenInformation(first, TokenStatistics, &first_stats, sizeof(first_stats), &needed) ||
        !GetTokenInformation(second, TokenStatistics, &second_stats, sizeof(second_stats), &needed)) return false;
    const auto first_sid = reinterpret_cast<TOKEN_USER*>(left)->User.Sid;
    const auto second_sid = reinterpret_cast<TOKEN_USER*>(right)->User.Sid;
    return IsValidSid(first_sid) && IsValidSid(second_sid) && EqualSid(first_sid, second_sid) &&
        first_session == second_session &&
        first_stats.AuthenticationId.LowPart == second_stats.AuthenticationId.LowPart &&
        first_stats.AuthenticationId.HighPart == second_stats.AuthenticationId.HighPart;
}

bool OrdinaryToken(HANDLE token, bool limited) {
    bool elevated = false;
    DWORD needed = 0;
    TOKEN_ELEVATION_TYPE elevation_type{};
    if (!cangoo::identity::TokenMatchesSession(token) ||
        !cangoo::identity::IsElevated(token, elevated) || elevated ||
        !GetTokenInformation(token, TokenElevationType, &elevation_type, sizeof(elevation_type), &needed) ||
        (limited && elevation_type != TokenElevationTypeLimited)) return false;
    alignas(TOKEN_MANDATORY_LABEL) BYTE integrity[sizeof(TOKEN_MANDATORY_LABEL) + SECURITY_MAX_SID_SIZE]{};
    if (!GetTokenInformation(token, TokenIntegrityLevel, integrity, sizeof(integrity), &needed)) return false;
    const auto sid = reinterpret_cast<TOKEN_MANDATORY_LABEL*>(integrity)->Label.Sid;
    return IsValidSid(sid) && *GetSidSubAuthorityCount(sid) &&
        *GetSidSubAuthority(sid, *GetSidSubAuthorityCount(sid) - 1) == SECURITY_MANDATORY_MEDIUM_RID;
}

bool CanImpersonate(HANDLE token) {
    TOKEN_TYPE type{};
    SECURITY_IMPERSONATION_LEVEL level = SecurityAnonymous;
    DWORD needed = 0;
    return GetTokenInformation(token, TokenType, &type, sizeof(type), &needed) &&
        (type == TokenPrimary || (type == TokenImpersonation &&
         GetTokenInformation(token, TokenImpersonationLevel, &level, sizeof(level), &needed) &&
         level >= SecurityImpersonation));
}

bool OpenVerifiedToken(Handle& token) {
    DWORD session = 0, token_session = 0, needed = 0;
    HANDLE raw_token = nullptr;
    if (!ProcessIdToSessionId(GetCurrentProcessId(), &session) || !session ||
        !OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY | TOKEN_DUPLICATE | TOKEN_IMPERSONATE, &raw_token)) return false;
    token.reset(raw_token);
    if (!cangoo::identity::TokenMatchesSession(token.get())) return false;
    bool elevated = false;
    if (!cangoo::identity::IsElevated(token.get(), elevated)) return false;
    const bool linked_user = elevated;
    if (elevated) {
        TOKEN_LINKED_TOKEN linked{};
        if (!GetTokenInformation(token.get(), TokenLinkedToken, &linked, sizeof(linked), &needed)) return false;
        token.reset(linked.LinkedToken);
    }
    if (!token || !OrdinaryToken(token.get(), linked_user) ||
        !GetTokenInformation(token.get(), TokenSessionId, &token_session, sizeof(token_session), &needed) ||
        !IdentityMatches(session, token_session, true, true)) return false;
    Handle shell_token;
    HANDLE source = token.get();
    TOKEN_TYPE source_type{};
    SECURITY_IMPERSONATION_LEVEL source_level = SecurityAnonymous;
    if (!GetTokenInformation(source, TokenType, &source_type, sizeof(source_type), &needed) ||
        (source_type != TokenPrimary && source_type != TokenImpersonation)) return false;
    if (source_type == TokenImpersonation &&
        !GetTokenInformation(source, TokenImpersonationLevel, &source_level, sizeof(source_level), &needed)) return false;
    if (source_type == TokenImpersonation && source_level < SecurityImpersonation) {
        if (!linked_user || source_level != SecurityIdentification) return false;
        // 关联令牌可能仅能识别；只接受当前桌面 shell 中同一普通登录的主令牌。
        DWORD process_id = 0;
        const HWND shell = GetShellWindow();
        if (!shell || !GetWindowThreadProcessId(shell, &process_id) || !process_id) return false;
        Handle process(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, process_id));
        HANDLE raw_shell = nullptr;
        if (!process || !OpenProcessToken(process.get(), TOKEN_QUERY | TOKEN_DUPLICATE, &raw_shell)) return false;
        shell_token.reset(raw_shell);
        TOKEN_TYPE type{};
        if (!GetTokenInformation(shell_token.get(), TokenType, &type, sizeof(type), &needed) || type != TokenPrimary ||
            !SameUserLogon(token.get(), shell_token.get()) || !OrdinaryToken(shell_token.get(), true)) return false;
        source = shell_token.get();
    }
    HANDLE raw_ordinary = nullptr;
    if (!DuplicateTokenEx(source, TOKEN_QUERY | TOKEN_IMPERSONATE | TOKEN_DUPLICATE, nullptr,
                          SecurityImpersonation, TokenImpersonation, &raw_ordinary)) return false;
    Handle ordinary(raw_ordinary);
    TOKEN_TYPE type{};
    if (!GetTokenInformation(ordinary.get(), TokenType, &type, sizeof(type), &needed) || type != TokenImpersonation ||
        !CanImpersonate(ordinary.get()) || !SameUserLogon(token.get(), ordinary.get()) ||
        !OrdinaryToken(ordinary.get(), linked_user)) return false;
    token.reset(ordinary.release());
    return true;
}

class OrdinaryUserScope {
public:
    explicit OrdinaryUserScope(HANDLE token) {
        HANDLE previous = nullptr;
        if (OpenThreadToken(GetCurrentThread(), TOKEN_QUERY | TOKEN_IMPERSONATE, TRUE, &previous))
            previous_.reset(previous);
        else if (GetLastError() != ERROR_NO_TOKEN) return;
        active_ = ImpersonateLoggedOnUser(token) != FALSE;
    }
    ~OrdinaryUserScope() {
        if (active_ && !(previous_ ? SetThreadToken(nullptr, previous_.get()) : RevertToSelf())) {
            // 身份恢复失败后不能让安装器继续处理任何操作。
            TerminateProcess(GetCurrentProcess(), ERROR_ACCESS_DENIED);
            std::terminate();
        }
    }
    explicit operator bool() const noexcept { return active_; }
private:
    Handle previous_;
    bool active_ = false;
};

#ifdef CANGOO_CLEANUP_ACCEPTANCE
constexpr std::wstring_view acceptance_root = CANGOO_CLEANUP_TEST_ROOT;
constexpr std::wstring_view work_prefix = L"D:\\pycharm\\Password_manager_work\\";
static_assert(acceptance_root.substr(0, work_prefix.size()) == work_prefix &&
              acceptance_root.size() > work_prefix.size(), "Acceptance cleanup must use an owned D-drive work root.");
#pragma message("Cangoo cleanup: ACCEPTANCE ONLY, fixed D-drive roots")
#endif

bool UserFolder(REFKNOWNFOLDERID id, HANDLE token, std::wstring& path, DWORD& error) {
#ifdef CANGOO_CLEANUP_ACCEPTANCE
    (void)token;
    path = std::wstring(acceptance_root) + (IsEqualGUID(id, FOLDERID_RoamingAppData) ? L"\\roaming" : L"\\local");
    (void)error;
    return true;
#else
    wchar_t* raw = nullptr;
    const HRESULT hr = SHGetKnownFolderPath(id, 0, token, &raw);
    std::unique_ptr<wchar_t, FolderFree> folder(raw);
    if (FAILED(hr) || !raw || !*raw) {
        error = HRESULT_FACILITY(hr) == FACILITY_WIN32 ? HRESULT_CODE(hr) : ERROR_PATH_NOT_FOUND;
        return false;
    }
    path = raw;
    return true;
#endif
}

bool LocalPath(const std::wstring& path) {
    if (path.size() < 4 || path.size() >= 32768 || path[1] != L':' || path[2] != L'\\' ||
        !((path[0] >= L'A' && path[0] <= L'Z') || (path[0] >= L'a' && path[0] <= L'z')) ||
        path.find_first_of(L"/*?\0", 0, 4) != std::wstring::npos || path.find(L':', 2) != std::wstring::npos) return false;
    for (size_t start = 3; start < path.size();) {
        const auto separator = path.find(L'\\', start);
        const auto end = separator == std::wstring::npos ? path.size() : separator;
        const auto part = std::wstring_view(path).substr(start, end - start);
        if (part.empty() || part == L"." || part == L".." || part.back() == L'.' || part.back() == L' ') return false;
        start = end + 1;
    }
    if (path.back() == L'\\') return false;
    const auto drive = GetDriveTypeW(path.substr(0, 3).c_str());
    return drive == DRIVE_FIXED || drive == DRIVE_REMOVABLE;
}

struct Prepared {
    std::vector<Handle> parents;
    std::array<Handle, 6> files;
    DWORD present_mask = 0;
};

bool PinFolder(const std::wstring& path, Prepared& prepared, bool& missing, DWORD& error) {
    missing = false;
    if (!LocalPath(path)) { error = ERROR_BAD_PATHNAME; return false; }
    for (size_t end = 3;;) {
        // 同时拒绝写入和删除，防止目录置换或原地设置联接改变后续目标。
        Handle handle(CreateFileW(path.substr(0, end).c_str(), FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ, nullptr, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!handle) {
            error = GetLastError();
            missing = error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND;
            return missing;
        }
        FILE_ATTRIBUTE_TAG_INFO info{};
        if (!GetFileInformationByHandleEx(handle.get(), FileAttributeTagInfo, &info, sizeof(info))) {
            error = GetLastError(); return false;
        }
        if ((info.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) || !(info.FileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
            error = ERROR_BAD_PATHNAME; return false;
        }
        prepared.parents.push_back(std::move(handle));
        if (end == path.size()) return true;
        const auto next = path.find(L'\\', end + 1);
        end = next == std::wstring::npos ? path.size() : next;
    }
}

bool Prepare(const std::wstring& roaming, const std::wstring& local, Prepared& prepared, Result& result) {
    constexpr const wchar_t* names[] = { L"pdm.db", L"pdm.db-wal", L"pdm.db-shm", L"pdm.db-journal",
                                       L"settings.json", L"security.st" };
    const std::array<std::wstring, 2> roots{roaming + L"\\cangoo", local + L"\\cangoo\\State"};
    for (size_t group = 0; group < roots.size(); ++group) {
        bool missing = false;
        if (!PinFolder(roots[group], prepared, missing, result.error)) return false;
        if (missing) { result.retained_mask &= ~(group == 0 ? 0x1ful : 0x20ul); continue; }
        for (size_t i = group == 0 ? 0 : 5; i < (group == 0 ? 5 : 6); ++i) {
            const DWORD bit = 1ul << i;
            prepared.files[i].reset(CreateFileW((roots[group] + L"\\" + names[i]).c_str(),
                DELETE | FILE_READ_ATTRIBUTES, 0, nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
            if (!prepared.files[i]) {
                result.error = GetLastError();
                if (result.error != ERROR_FILE_NOT_FOUND) return false;
                result.retained_mask &= ~bit;
                continue;
            }
            prepared.present_mask |= bit;
            FILE_ATTRIBUTE_TAG_INFO info{};
            if (!GetFileInformationByHandleEx(prepared.files[i].get(), FileAttributeTagInfo, &info, sizeof(info))) {
                result.error = GetLastError(); return false;
            }
            if ((info.FileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_READONLY)) ||
                GetFileType(prepared.files[i].get()) != FILE_TYPE_DISK) {
                result.error = ERROR_ACCESS_DENIED; return false;
            }
        }
    }
    return true;
}

void DeletePrepared(Prepared& prepared, Result& result) noexcept {
    FILE_DISPOSITION_INFO disposition{TRUE};
    for (size_t i = 0; i < prepared.files.size(); ++i) {
        const DWORD bit = 1ul << i;
        if (!(prepared.present_mask & bit)) continue;
        if (!SetFileInformationByHandle(prepared.files[i].get(), FileDispositionInfo, &disposition, sizeof(disposition))) {
            result.error = GetLastError();
            result.status = result.deleted_count ? Status::partial : Status::failed;
            return;
        }
        prepared.files[i].reset();
        result.deleted_mask |= bit;
        result.retained_mask &= ~bit;
        ++result.deleted_count;
    }
    result.status = Status::complete;
    result.error = ERROR_SUCCESS;
}

void DeleteOwnedFiles(const std::wstring& roaming, const std::wstring& local, Result& result) {
    Prepared prepared;
    if (Prepare(roaming, local, prepared, result)) DeletePrepared(prepared, result);
}

}  // namespace

bool CurrentIdentityMatches() noexcept {
    try { Handle token; return OpenVerifiedToken(token); }
    catch (...) { return false; }
}

Result DeleteCurrentUserData() noexcept {
    Result result;
    try {
        Handle token;
        if (!OpenVerifiedToken(token)) {
            result.status = Status::identity_unknown;
            result.error = ERROR_NO_SUCH_LOGON_SESSION;
            return result;
        }
        OrdinaryUserScope ordinary(token.get());
        if (!ordinary) {
            result.status = Status::identity_unknown;
            result.error = GetLastError();
            return result;
        }
        std::wstring roaming, local;
        if (!UserFolder(FOLDERID_RoamingAppData, token.get(), roaming, result.error) ||
            !UserFolder(FOLDERID_LocalAppData, token.get(), local, result.error)) return result;
        DeleteOwnedFiles(roaming, local, result);
    } catch (...) {
        result.error = ERROR_NOT_ENOUGH_MEMORY;
        result.status = result.deleted_count ? Status::partial : Status::failed;
    }
    return result;
}

}  // namespace cangoo::cleanup
