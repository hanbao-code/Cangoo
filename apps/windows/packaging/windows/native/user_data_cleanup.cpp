// SPDX-License-Identifier: MIT
// 许可见本目录 LICENSE。
#include "user_data_cleanup.h"

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
    explicit operator bool() const noexcept { return value_ && value_ != INVALID_HANDLE_VALUE; }
    void reset(HANDLE value = INVALID_HANDLE_VALUE) noexcept {
        if (*this) CloseHandle(value_);
        value_ = value;
    }
private:
    HANDLE value_;
};

struct SessionFree {
    void operator()(wchar_t* value) const noexcept { WTSFreeMemory(value); }
};

struct FolderFree {
    void operator()(wchar_t* value) const noexcept { CoTaskMemFree(value); }
};

bool IdentityMatches(DWORD process_session, DWORD token_session,
                     bool active, bool same_sid) noexcept {
    return process_session != 0 && process_session == token_session && active && same_sid;
}

std::wstring SessionText(DWORD session, WTS_INFO_CLASS kind) {
    wchar_t* raw = nullptr;
    DWORD bytes = 0;
    const BOOL ok = WTSQuerySessionInformationW(WTS_CURRENT_SERVER_HANDLE, session, kind, &raw, &bytes);
    std::unique_ptr<wchar_t, SessionFree> text(raw);
    if (!ok || !raw || bytes < sizeof(wchar_t) || bytes > 2048 || bytes % sizeof(wchar_t)) return {};
    const auto length = wcsnlen(raw, bytes / sizeof(wchar_t));
    return length < bytes / sizeof(wchar_t) ? std::wstring(raw, length) : std::wstring{};
}

bool OpenVerifiedToken(Handle& token) {
    DWORD session = 0, token_session = 0, needed = 0;
    HANDLE raw_token = nullptr;
    if (!ProcessIdToSessionId(GetCurrentProcessId(), &session) || !session ||
        !OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY | TOKEN_IMPERSONATE, &raw_token)) return false;
    token.reset(raw_token);
    if (!GetTokenInformation(token.get(), TokenSessionId, &token_session, sizeof(token_session), &needed) ||
        needed != sizeof(token_session) || token_session != session) return false;

    wchar_t* raw_state = nullptr;
    DWORD bytes = 0;
    const BOOL queried = WTSQuerySessionInformationW(
        WTS_CURRENT_SERVER_HANDLE, session, WTSConnectState, &raw_state, &bytes);
    std::unique_ptr<wchar_t, SessionFree> state(raw_state);
    if (!queried || !raw_state || bytes != sizeof(WTS_CONNECTSTATE_CLASS) ||
        *reinterpret_cast<WTS_CONNECTSTATE_CLASS*>(raw_state) != WTSActive) return false;
    const auto user = SessionText(session, WTSUserName);
    const auto domain = SessionText(session, WTSDomainName);
    if (user.empty() || domain.empty()) return false;

    alignas(SID) BYTE account_sid[SECURITY_MAX_SID_SIZE]{};
    DWORD sid_bytes = sizeof(account_sid), domain_chars = 1024;
    wchar_t resolved_domain[1024]{};
    SID_NAME_USE sid_type{};
    if (!LookupAccountNameW(nullptr, (domain + L"\\" + user).c_str(), account_sid,
                            &sid_bytes, resolved_domain, &domain_chars, &sid_type) || sid_type != SidTypeUser) return false;
    alignas(TOKEN_USER) BYTE user_info[sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE]{};
    if (!GetTokenInformation(token.get(), TokenUser, user_info, sizeof(user_info), &needed)) return false;
    const auto sid = reinterpret_cast<TOKEN_USER*>(user_info)->User.Sid;
    return IsValidSid(sid) && IsValidSid(account_sid) &&
           IdentityMatches(session, token_session, true, EqualSid(sid, account_sid) != FALSE);
}

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
