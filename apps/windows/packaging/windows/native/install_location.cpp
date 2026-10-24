// SPDX-License-Identifier: MIT
// 许可见本目录 LICENSE。
#include "install_location.h"

#include <msi.h>
#include <shlobj.h>

#include <algorithm>
#include <memory>
#include <string_view>
#include <vector>

namespace cangoo::install {
namespace {

struct FolderFree {
    void operator()(wchar_t* value) const noexcept { CoTaskMemFree(value); }
};

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

UINT ProductProperty(LPCWSTR product, MSIINSTALLCONTEXT context, LPCWSTR name, std::wstring& value) {
    DWORD length = 0;
    UINT error = MsiGetProductInfoExW(product, nullptr, context, name, nullptr, &length);
    if (error != ERROR_SUCCESS) return error;
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

}

std::wstring DefaultInstallFolder(bool machine) noexcept {
    try {
        wchar_t* raw = nullptr;
        const HRESULT status = SHGetKnownFolderPath(machine ? FOLDERID_ProgramFilesX64 : FOLDERID_LocalAppData,
                                                   0, nullptr, &raw);
        std::unique_ptr<wchar_t, FolderFree> folder(raw);
        if (FAILED(status) || !raw || !*raw) return {};
        std::wstring result = std::wstring(raw) + (machine ? L"\\Cangoo" : L"\\Programs\\Cangoo");
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

}
