// SPDX-License-Identifier: MIT
// 许可见本目录 LICENSE。
#include "install_location.h"

#include <msi.h>
#include <msiquery.h>
#include <aclapi.h>
#include <sddl.h>
#include <shlobj.h>

#include <algorithm>
#include <memory>
#include <string_view>
#include <vector>

#ifndef CANGOO_INSTALL_MACHINE_LEAF
#define CANGOO_INSTALL_MACHINE_LEAF L"Cangoo"
#endif

namespace cangoo::install {
namespace {

struct FolderFree {
    void operator()(wchar_t* value) const noexcept { CoTaskMemFree(value); }
};

struct LocalFreeDeleter {
    void operator()(void* value) const noexcept { LocalFree(value); }
};

struct HandleCloser {
    void operator()(void* value) const noexcept { CloseHandle(value); }
};
using Handle = std::unique_ptr<void, HandleCloser>;

bool NormalizePath(std::wstring& path) {
    if (path.size() < 4 || path.size() >= 32768) return false;
    std::replace(path.begin(), path.end(), L'/', L'\\');
    while (path.size() > 3 && path.back() == L'\\') path.pop_back();
    if (path.size() < 4 || path[1] != L':' || path[2] != L'\\' ||
        !((path[0] >= L'A' && path[0] <= L'Z') || (path[0] >= L'a' && path[0] <= L'z')) ||
        path.find(L':', 2) != std::wstring::npos || path.find_first_of(L"<>\"|?*") != std::wstring::npos ||
        std::any_of(path.begin(), path.end(), [](wchar_t ch) { return ch < 32; })) return false;
    for (size_t begin = 3; begin < path.size();) {
        const auto separator = path.find(L'\\', begin);
        const auto end = separator == std::wstring::npos ? path.size() : separator;
        const auto part = std::wstring_view(path).substr(begin, end - begin);
        if (part.empty() || part == L"." || part == L".." || part.back() == L' ' || part.back() == L'.') return false;
        std::wstring stem(part.substr(0, part.find(L'.')));
        CharUpperBuffW(stem.data(), static_cast<DWORD>(stem.size()));
        if (stem == L"CON" || stem == L"PRN" || stem == L"AUX" || stem == L"NUL" ||
            (stem.size() == 4 && (stem.substr(0, 3) == L"COM" || stem.substr(0, 3) == L"LPT") &&
             std::wstring_view(L"123456789\u00b9\u00b2\u00b3").find(stem[3]) != std::wstring_view::npos)) return false;
        begin = end + 1;
    }
    const auto drive = GetDriveTypeW(path.substr(0, 3).c_str());
    return drive == DRIVE_FIXED || drive == DRIVE_REMOVABLE;
}

#ifdef CANGOO_INSTALL_TEST_ROOT
bool MatchesAcceptanceFolder(const std::wstring& path) {
    auto candidate = path;
    std::wstring expected = CANGOO_INSTALL_TEST_ROOT;
    return NormalizePath(candidate) && NormalizePath(expected) &&
        CompareStringOrdinal(candidate.c_str(), -1, expected.c_str(), -1, TRUE) == CSTR_EQUAL;
}
#endif

UINT ProductProperty(LPCWSTR product, MSIINSTALLCONTEXT context, LPCWSTR name, std::wstring& value) {
    DWORD length = 0;
    UINT error = MsiGetProductInfoExW(product, nullptr, context, name, nullptr, &length);
    if (error != ERROR_SUCCESS && error != ERROR_MORE_DATA) return error;
    if (length >= 32768) return ERROR_BAD_CONFIGURATION;
    std::vector<wchar_t> buffer(length + 1);
    ++length;
    error = MsiGetProductInfoExW(product, nullptr, context, name, buffer.data(), &length);
    if (error == ERROR_SUCCESS) value.assign(buffer.data(), length);
    return error;
}

FolderStatus EmptyFolder(const std::wstring& path) {
    WIN32_FIND_DATAW data{};
    const HANDLE handle = FindFirstFileW((path + L"\\*").c_str(), &data);
    if (handle == INVALID_HANDLE_VALUE)
        return GetLastError() == ERROR_FILE_NOT_FOUND ? FolderStatus::valid : FolderStatus::failed;
    FolderStatus result = FolderStatus::valid;
    do {
        if (wcscmp(data.cFileName, L".") && wcscmp(data.cFileName, L"..")) {
            result = FolderStatus::occupied;
            break;
        }
    } while (FindNextFileW(handle, &data));
    if (result == FolderStatus::valid && GetLastError() != ERROR_NO_MORE_FILES) result = FolderStatus::failed;
    FindClose(handle);
    return result;
}

bool TrustedSid(PSID sid, PSID installer) {
    return sid && IsValidSid(sid) && (IsWellKnownSid(sid, WinLocalSystemSid) ||
        IsWellKnownSid(sid, WinBuiltinAdministratorsSid) || EqualSid(sid, installer));
}

FolderStatus ProtectedPermissions(HANDLE handle, PSID installer, bool ancestor, bool directory) {
    PSID owner = nullptr;
    PACL acl = nullptr;
    PSECURITY_DESCRIPTOR raw = nullptr;
    const DWORD error = GetSecurityInfo(handle, SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
                                        &owner, nullptr, &acl, nullptr, &raw);
    const std::unique_ptr<void, LocalFreeDeleter> descriptor(raw);
    if (error != ERROR_SUCCESS) return FolderStatus::failed;
    if (!TrustedSid(owner, installer) || !acl || !IsValidAcl(acl)) return FolderStatus::unsafe_path;
    const DWORD changes = WRITE_DAC | WRITE_OWNER | DELETE | FILE_WRITE_DATA | FILE_WRITE_EA |
                          FILE_WRITE_ATTRIBUTES | FILE_DELETE_CHILD | (ancestor ? 0 : FILE_APPEND_DATA);
    for (DWORD index = 0; index < acl->AceCount; ++index) {
        void* raw_ace = nullptr;
        if (!GetAce(acl, index, &raw_ace)) return FolderStatus::failed;
        const auto* header = static_cast<ACE_HEADER*>(raw_ace);
        if (header->AceType == ACCESS_DENIED_ACE_TYPE) continue;
        if (header->AceType != ACCESS_ALLOWED_ACE_TYPE) return FolderStatus::unsafe_path;
        const auto* ace = static_cast<ACCESS_ALLOWED_ACE*>(raw_ace);
        const bool inherit_only = (header->AceFlags & INHERIT_ONLY_ACE) != 0;
        // 卷根可允许创建兄弟目录；程序目录还须保证新文件继承的权限安全。
        if (inherit_only && (ancestor || !directory)) continue;
        const auto sid = const_cast<DWORD*>(&ace->SidStart);
        if (TrustedSid(sid, installer) || (inherit_only && IsWellKnownSid(sid, WinCreatorOwnerSid))) continue;
        DWORD mask = ace->Mask;
        GENERIC_MAPPING mapping{FILE_GENERIC_READ, FILE_GENERIC_WRITE, FILE_GENERIC_EXECUTE, FILE_ALL_ACCESS};
        MapGenericMask(&mask, &mapping);
        if (mask & changes) return FolderStatus::unsafe_path;
    }
    return FolderStatus::valid;
}

FolderStatus PinProtectedObject(const std::wstring& path, PSID installer, bool ancestor, bool require_directory,
                               std::vector<Handle>& handles, bool& directory, bool& missing) {
    missing = false;
    const HANDLE raw = CreateFileW(path.c_str(), FILE_READ_DATA | FILE_READ_ATTRIBUTES | READ_CONTROL, FILE_SHARE_READ, nullptr,
                                  OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (raw == INVALID_HANDLE_VALUE) {
        const DWORD error = GetLastError();
        missing = error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND;
        return missing ? FolderStatus::valid : error == ERROR_SHARING_VIOLATION ? FolderStatus::occupied : FolderStatus::failed;
    }
    Handle handle(raw);
    FILE_ATTRIBUTE_TAG_INFO info{};
    if (!GetFileInformationByHandleEx(raw, FileAttributeTagInfo, &info, sizeof(info))) return FolderStatus::failed;
    directory = (info.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
    if ((info.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) || (require_directory && !directory) ||
        GetFileType(raw) != FILE_TYPE_DISK) return FolderStatus::unsafe_path;
    if (!directory) {
        FILE_STANDARD_INFO standard{};
        if (!GetFileInformationByHandleEx(raw, FileStandardInfo, &standard, sizeof(standard))) return FolderStatus::failed;
        if (standard.NumberOfLinks != 1) return FolderStatus::unsafe_path;
    }
    const auto status = ProtectedPermissions(raw, installer, ancestor, directory);
    if (status == FolderStatus::valid) handles.push_back(std::move(handle));
    return status;
}

}

std::wstring DefaultInstallFolder(bool machine) noexcept {
    try {
        wchar_t* raw = nullptr;
        const HRESULT status = SHGetKnownFolderPath(machine ? FOLDERID_ProgramFilesX64 : FOLDERID_LocalAppData,
                                                   0, nullptr, &raw);
        std::unique_ptr<wchar_t, FolderFree> folder(raw);
        if (FAILED(status) || !raw || !*raw) return {};
        std::wstring result = std::wstring(raw) + (machine ? L"\\" CANGOO_INSTALL_MACHINE_LEAF : L"\\Programs\\Cangoo");
        return NormalizePath(result) ? result : std::wstring{};
    } catch (...) { return {}; }
}

std::wstring InstallFolderFromParent(const std::wstring& parent) noexcept {
    try {
        if (parent.empty()) return {};
        auto result = parent;
        std::replace(result.begin(), result.end(), L'/', L'\\');
        while (result.size() > 3 && result.back() == L'\\') result.pop_back();
        if (result.back() != L'\\') result += L'\\';
        result += L"Cangoo";
        return NormalizePath(result) ? result : std::wstring{};
    } catch (...) { return {}; }
}

InstalledLocation ReadInstalledLocation(const std::wstring& upgrade_guid) noexcept {
    InstalledLocation result;
    try {
        std::wstring input = upgrade_guid.size() == 36 ? L"{" + upgrade_guid + L"}" : upgrade_guid;
        GUID guid{};
        wchar_t canonical[39]{};
        if (input.size() != 38 || FAILED(IIDFromString(input.c_str(), &guid)) ||
            StringFromGUID2(guid, canonical, 39) != 39) {
            result.error = ERROR_INVALID_PARAMETER; return result;
        }
        result.state = InstalledState::none;
        constexpr MSIINSTALLCONTEXT contexts[] = {MSIINSTALLCONTEXT_USERUNMANAGED,
                                                  MSIINSTALLCONTEXT_USERMANAGED, MSIINSTALLCONTEXT_MACHINE};
        for (DWORD index = 0;; ++index) {
            wchar_t product[39]{};
            const UINT enumerated = MsiEnumRelatedProductsW(canonical, 0, index, product);
            if (enumerated == ERROR_NO_MORE_ITEMS) return result;
            result.error = enumerated;
            if (enumerated != ERROR_SUCCESS) { result.state = InstalledState::failed; return result; }
            bool found = false;
            for (const auto context : contexts) {
                std::wstring state;
                UINT error = ProductProperty(product, context, INSTALLPROPERTY_PRODUCTSTATE, state);
                if (error == ERROR_UNKNOWN_PRODUCT) continue;
                if (error != ERROR_SUCCESS || state != L"5") {
                    result.state = InstalledState::failed;
                    result.error = error == ERROR_SUCCESS ? ERROR_BAD_CONFIGURATION : error;
                    return result;
                }
                found = true;
                std::wstring path;
                error = ProductProperty(product, context, INSTALLPROPERTY_INSTALLLOCATION, path);
                if (error != ERROR_SUCCESS || !NormalizePath(path)) {
                    result.state = InstalledState::failed;
                    result.error = error == ERROR_SUCCESS ? ERROR_BAD_PATHNAME : error;
                    return result;
                }
                if (result.state == InstalledState::unique) {
                    result.state = InstalledState::conflict; result.path.clear(); return result;
                }
                result.state = InstalledState::unique;
                result.path = std::move(path);
                result.machine = context == MSIINSTALLCONTEXT_MACHINE;
            }
            // 有登记但查不到当前用户或本机的完整实例，不能降级为“全新安装”。
            if (!found) { result.state = InstalledState::failed; result.error = ERROR_UNKNOWN_PRODUCT; return result; }
        }
    } catch (...) {
        result.state = InstalledState::failed; result.error = ERROR_NOT_ENOUGH_MEMORY; return result;
    }
}

FolderStatus ValidateInstallFolder(const std::wstring& path, const std::wstring& known_installed_path) noexcept {
    try {
        std::wstring candidate = path;
        if (!NormalizePath(candidate)) return FolderStatus::invalid_path;
        if (!known_installed_path.empty()) {
            std::wstring known = known_installed_path;
            if (!NormalizePath(known)) return FolderStatus::failed;
            if (CompareStringOrdinal(candidate.c_str(), -1, known.c_str(), -1, TRUE) != CSTR_EQUAL)
                return FolderStatus::different_location;
        }
        for (size_t end = 3;;) {
            const DWORD attributes = GetFileAttributesW(candidate.substr(0, end).c_str());
            if (attributes == INVALID_FILE_ATTRIBUTES) {
                const DWORD error = GetLastError();
                if (error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND) return FolderStatus::valid;
                return error == ERROR_SHARING_VIOLATION ? FolderStatus::occupied : FolderStatus::failed;
            }
            if (attributes & FILE_ATTRIBUTE_REPARSE_POINT) return FolderStatus::unsafe_path;
            if (!(attributes & FILE_ATTRIBUTE_DIRECTORY)) return FolderStatus::occupied;
            if (end == candidate.size()) break;
            const auto next = candidate.find(L'\\', end + 1);
            end = next == std::wstring::npos ? candidate.size() : next;
        }
        return known_installed_path.empty() ? EmptyFolder(candidate) : FolderStatus::valid;
    } catch (...) { return FolderStatus::failed; }
}

FolderStatus ValidateMachineInstallFolder(const std::wstring& path, const std::wstring& known_installed_path) noexcept {
    try {
        const auto base = ValidateInstallFolder(path, known_installed_path);
        if (base != FolderStatus::valid) return base;
        std::wstring candidate = path;
        if (!NormalizePath(candidate)) return FolderStatus::invalid_path;
        const auto expected = DefaultInstallFolder(true);
        if (expected.empty()) return FolderStatus::failed;
        if (CompareStringOrdinal(candidate.c_str(), -1, expected.c_str(), -1, TRUE) != CSTR_EQUAL)
            return FolderStatus::unsafe_path;
        PSID raw_installer = nullptr;
        if (!ConvertStringSidToSidW(L"S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464", &raw_installer))
            return FolderStatus::failed;
        const std::unique_ptr<void, LocalFreeDeleter> installer(raw_installer);
        std::vector<Handle> handles;
        const auto programs_end = candidate.rfind(L'\\');
        for (size_t end = 3;;) {
            bool directory = false, missing = false;
            const auto status = PinProtectedObject(candidate.substr(0, end), raw_installer, end < programs_end,
                                                    true, handles, directory, missing);
            if (status != FolderStatus::valid) return status;
            if (missing) return end == candidate.size() ? FolderStatus::valid : FolderStatus::failed;
            if (end == candidate.size()) break;
            const auto next = candidate.find(L'\\', end + 1);
            end = next == std::wstring::npos ? candidate.size() : next;
        }
        std::vector<std::wstring> pending{candidate};
        while (!pending.empty()) {
            const auto parent = std::move(pending.back());
            pending.pop_back();
            WIN32_FIND_DATAW data{};
            const HANDLE search = FindFirstFileW((parent + L"\\*").c_str(), &data);
            if (search == INVALID_HANDLE_VALUE) {
                if (GetLastError() == ERROR_FILE_NOT_FOUND) continue;
                return FolderStatus::failed;
            }
            FolderStatus status = FolderStatus::valid;
            do {
                if (!wcscmp(data.cFileName, L".") || !wcscmp(data.cFileName, L"..")) continue;
                const auto child = parent + L"\\" + data.cFileName;
                bool directory = false, missing = false;
                status = PinProtectedObject(child, raw_installer, false, false, handles, directory, missing);
                if (status != FolderStatus::valid || missing) { if (missing) status = FolderStatus::failed; break; }
                if (directory) pending.push_back(child);
            } while (FindNextFileW(search, &data));
            if (status == FolderStatus::valid && GetLastError() != ERROR_NO_MORE_FILES) status = FolderStatus::failed;
            FindClose(search);
            if (status != FolderStatus::valid) return status;
        }
        // 检查时拒绝已有写入/删除句柄；随后只有受信任管理员能改变目录链和程序文件。
        return FolderStatus::valid;
    } catch (...) { return FolderStatus::failed; }
}

FolderStatus ValidateUserInstallFolder(const std::wstring& path, const std::wstring& known_installed_path) noexcept {
    try {
        const auto status = ValidateInstallFolder(path, known_installed_path);
        if (status != FolderStatus::valid) return status;
        std::wstring candidate = path;
        if (!NormalizePath(candidate)) return FolderStatus::invalid_path;
        std::vector<std::wstring> ancestors;
        bool missing = false;
        for (size_t end = 3;;) {
            const auto current = candidate.substr(0, end);
            const DWORD attributes = GetFileAttributesW(current.c_str());
            if (attributes == INVALID_FILE_ATTRIBUTES) {
                const DWORD error = GetLastError();
                if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND) return FolderStatus::failed;
                missing = true; break;
            }
            if ((attributes & FILE_ATTRIBUTE_REPARSE_POINT) || !(attributes & FILE_ATTRIBUTE_DIRECTORY))
                return FolderStatus::unsafe_path;
            ancestors.push_back(current);
            if (end == candidate.size()) break;
            const auto next = candidate.find(L'\\', end + 1);
            end = next == std::wstring::npos ? candidate.size() : next;
        }
        if (ancestors.empty()) return FolderStatus::failed;
        // 由系统以当前调用身份检查实际创建权限；此处不创建文件或修改 ACL。
        Handle writable(CreateFileW(ancestors.back().c_str(), missing ? FILE_ADD_SUBDIRECTORY : FILE_ADD_FILE,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (writable.get() == INVALID_HANDLE_VALUE) { writable.release(); return FolderStatus::failed; }
        if (!missing) {
            std::vector<std::wstring> pending{candidate};
            while (!pending.empty()) {
                const auto parent = std::move(pending.back()); pending.pop_back();
                WIN32_FIND_DATAW data{};
                const HANDLE search = FindFirstFileW((parent + L"\\*").c_str(), &data);
                if (search == INVALID_HANDLE_VALUE) {
                    if (GetLastError() == ERROR_FILE_NOT_FOUND) continue;
                    return FolderStatus::failed;
                }
                do {
                    if (!wcscmp(data.cFileName, L".") || !wcscmp(data.cFileName, L"..")) continue;
                    if (data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) {
                        FindClose(search); return FolderStatus::unsafe_path;
                    }
                    const auto child = parent + L"\\" + data.cFileName;
                    const bool directory = (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
                    if (directory) pending.push_back(child);
                } while (FindNextFileW(search, &data));
                const auto error = GetLastError();
                FindClose(search);
                if (error != ERROR_NO_MORE_FILES) return FolderStatus::failed;
            }
        }
        return FolderStatus::valid;
    } catch (...) { return FolderStatus::failed; }
}

}

#ifdef CANGOO_MSI_UPGRADE_CODE
namespace {
UINT InitializeSessionFolder(MSIHANDLE session) {
    using namespace cangoo::install;
    wchar_t folder[32768]{};
    DWORD length = static_cast<DWORD>(std::size(folder));
    if (MsiGetPropertyW(session, L"INSTALLFOLDER", folder, &length) != ERROR_SUCCESS) return ERROR_INSTALL_FAILURE;
    if (length) return ERROR_SUCCESS;
    const auto installed = ReadInstalledLocation(CANGOO_MSI_UPGRADE_CODE);
    if (installed.state == InstalledState::unique) return MsiSetPropertyW(session, L"INSTALLFOLDER", installed.path.c_str());
    // 登记异常留给实际写入守卫处理，不能阻止原有卸载入口。
    if (installed.state != InstalledState::none) return ERROR_SUCCESS;
#ifdef CANGOO_INSTALL_TEST_ROOT
    const std::wstring target = CANGOO_INSTALL_TEST_ROOT;
    return MatchesAcceptanceFolder(target) ? MsiSetPropertyW(session, L"INSTALLFOLDER", target.c_str()) : ERROR_INSTALL_FAILURE;
#else
    wchar_t all_users[2]{}, per_user[2]{};
    DWORD all_size = 2, user_size = 2;
    if (MsiGetPropertyW(session, L"ALLUSERS", all_users, &all_size) != ERROR_SUCCESS ||
        MsiGetPropertyW(session, L"MSIINSTALLPERUSER", per_user, &user_size) != ERROR_SUCCESS) return ERROR_INSTALL_FAILURE;
    const bool machine = all_users[0] == L'1' || (all_users[0] == L'2' && per_user[0] != L'1');
    const auto target = DefaultInstallFolder(machine);
    return target.empty() ? ERROR_INSTALL_FAILURE : MsiSetPropertyW(session, L"INSTALLFOLDER", target.c_str());
#endif
}

bool HasComponentWrites(MSIHANDLE session, bool& writes) {
    PMSIHANDLE database = MsiGetActiveDatabase(session);
    PMSIHANDLE view;
    if (!database || MsiDatabaseOpenViewW(database, L"SELECT `Component` FROM `Component`", &view) != ERROR_SUCCESS ||
        MsiViewExecute(view, 0) != ERROR_SUCCESS) return false;
    writes = false;
    for (;;) {
        PMSIHANDLE record;
        const UINT next = MsiViewFetch(view, &record);
        if (next == ERROR_NO_MORE_ITEMS) return true;
        if (next != ERROR_SUCCESS) return false;
        wchar_t component[73]{};
        DWORD length = static_cast<DWORD>(std::size(component));
        INSTALLSTATE installed = INSTALLSTATE_UNKNOWN, action = INSTALLSTATE_UNKNOWN;
        if (MsiRecordGetStringW(record, 1, component, &length) != ERROR_SUCCESS || !length ||
            MsiGetComponentStateW(session, component, &installed, &action) != ERROR_SUCCESS) return false;
        if (action == INSTALLSTATE_LOCAL || action == INSTALLSTATE_SOURCE || action == INSTALLSTATE_DEFAULT) {
            writes = true; return true;
        }
        // REMOVED 与特性 ADVERTISED 共用数值；这里查询组件，按移除处理。
        if (action != INSTALLSTATE_ABSENT && action != INSTALLSTATE_REMOVED && action != INSTALLSTATE_UNKNOWN) return false;
    }
}

UINT CheckMachineSession(MSIHANDLE session, bool deferred) {
    using namespace cangoo::install;
    if ((MsiGetMode(session, MSIRUNMODE_SCHEDULED) != FALSE) != deferred) return ERROR_INSTALL_FAILURE;
    if (!deferred) {
        bool writes = false;
        // REMOVE 等命令行属性能相互覆盖，只有 CostFinalize 后的实际组件动作能授予卸载豁免。
        if (!HasComponentWrites(session, writes)) return ERROR_INSTALL_FAILURE;
        if (!writes) return MsiSetPropertyW(session, L"CangooValidateMachineInstall", L"");
    }
    wchar_t target[32768]{};
    DWORD length = static_cast<DWORD>(std::size(target));
    const UINT read = deferred ? MsiGetPropertyW(session, L"CustomActionData", target, &length)
                               : MsiGetTargetPathW(session, L"INSTALLFOLDER", target, &length);
    if (deferred && read == ERROR_SUCCESS && !length) return ERROR_SUCCESS;
#ifdef CANGOO_INSTALL_TEST_ROOT
    if (read != ERROR_SUCCESS || !length || length >= std::size(target) || wcsnlen(target, std::size(target)) != length ||
        !MatchesAcceptanceFolder(target)) return ERROR_INSTALL_FAILURE;
#endif
    const auto installed = ReadInstalledLocation(CANGOO_MSI_UPGRADE_CODE);
    if (read == ERROR_SUCCESS && length && length < std::size(target) && wcsnlen(target, std::size(target)) == length &&
        (installed.state == InstalledState::none || (installed.state == InstalledState::unique && installed.machine)) &&
        // 预检已确认首装空目录或原安装；升级卸旧后仍须核验实际目录的权限与全部剩余文件。
        ValidateMachineInstallFolder(target, installed.state == InstalledState::unique ? installed.path :
            deferred ? target : L"") == FolderStatus::valid) {
        return deferred ? ERROR_SUCCESS : MsiSetPropertyW(session, L"CangooValidateMachineInstall", target);
    }
    const MSIHANDLE message = MsiCreateRecord(0);
    if (message) {
        MsiRecordSetStringW(message, 0,
            L"所有用户安装只允许使用受保护的系统程序目录。已有安装不符合要求时，请保留资料卸载后重新安装。 "
            L"All-users installation requires the protected system program directory. Uninstall an incompatible installation while keeping your data, then reinstall.");
        MsiProcessMessage(session, INSTALLMESSAGE_ERROR, message);
        MsiCloseHandle(message);
    }
    return ERROR_INSTALL_FAILURE;
}

UINT CheckUserSession(MSIHANDLE session, bool deferred) {
    using namespace cangoo::install;
    if ((MsiGetMode(session, MSIRUNMODE_SCHEDULED) != FALSE) != deferred) return ERROR_INSTALL_FAILURE;
    if (!deferred) {
        bool writes = false;
        if (!HasComponentWrites(session, writes)) return ERROR_INSTALL_FAILURE;
        if (!writes) return MsiSetPropertyW(session, L"CangooValidateUserInstall", L"");
    }
    wchar_t buffer[32768]{};
    DWORD length = static_cast<DWORD>(std::size(buffer));
    const UINT read = deferred ? MsiGetPropertyW(session, L"CustomActionData", buffer, &length)
                               : MsiGetTargetPathW(session, L"INSTALLFOLDER", buffer, &length);
    if (deferred && read == ERROR_SUCCESS && !length) return ERROR_SUCCESS;
    if (read != ERROR_SUCCESS || !length || length >= std::size(buffer) || wcsnlen(buffer, std::size(buffer)) != length)
        return ERROR_INSTALL_FAILURE;
    bool maintenance = false;
    std::wstring target = buffer;
    if (deferred) {
        if (length < 3 || buffer[1] != L'|' || (buffer[0] != L'0' && buffer[0] != L'1')) return ERROR_INSTALL_FAILURE;
        maintenance = buffer[0] == L'1'; target.erase(0, 2);
    }
#ifdef CANGOO_INSTALL_TEST_ROOT
    if (!MatchesAcceptanceFolder(target)) return ERROR_INSTALL_FAILURE;
#endif
    const auto installed = ReadInstalledLocation(CANGOO_MSI_UPGRADE_CODE);
    if (!deferred) maintenance = installed.state == InstalledState::unique && !installed.machine;
    if (installed.state == InstalledState::none ||
        (installed.state == InstalledState::unique && !installed.machine && maintenance)) {
        const auto check = ValidateUserInstallFolder(target, installed.state == InstalledState::unique ? installed.path :
            deferred && maintenance ? target : L"");
        if (check == FolderStatus::valid) {
            const auto data = std::wstring(maintenance ? L"1|" : L"0|") + target;
            return deferred ? ERROR_SUCCESS : MsiSetPropertyW(session, L"CangooValidateUserInstall", data.c_str());
        }
    }
    PMSIHANDLE message = MsiCreateRecord(0);
    if (message) {
        MsiRecordSetStringW(message, 0,
            L"安装目录不可用。请选择可写的本地目录，并确认没有其他文件或路径重定向。 "
            L"The installation directory is unavailable. Choose a writable local folder without unrelated files or redirected paths.");
        MsiProcessMessage(session, INSTALLMESSAGE_ERROR, message);
    }
    return ERROR_INSTALL_FAILURE;
}
}

extern "C" __declspec(dllexport) UINT WINAPI CangooInitializeInstallFolder(MSIHANDLE session) {
    try { return InitializeSessionFolder(session); }
    catch (...) { return ERROR_INSTALL_FAILURE; }
}

extern "C" __declspec(dllexport) UINT WINAPI CangooPrepareMachineInstall(MSIHANDLE session) {
    try { return CheckMachineSession(session, false); }
    catch (...) { return ERROR_INSTALL_FAILURE; }
}

extern "C" __declspec(dllexport) UINT WINAPI CangooValidateMachineInstall(MSIHANDLE session) {
    try { return CheckMachineSession(session, true); }
    catch (...) { return ERROR_INSTALL_FAILURE; }
}

extern "C" __declspec(dllexport) UINT WINAPI CangooPrepareUserInstall(MSIHANDLE session) {
    try { return CheckUserSession(session, false); }
    catch (...) { return ERROR_INSTALL_FAILURE; }
}

extern "C" __declspec(dllexport) UINT WINAPI CangooValidateUserInstall(MSIHANDLE session) {
    try { return CheckUserSession(session, true); }
    catch (...) { return ERROR_INSTALL_FAILURE; }
}
#endif
