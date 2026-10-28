// SPDX-License-Identifier: MIT
// Inno 仅做 ABI 适配，目录与删除权限仍由共用原生实现判断。
#include "inno_support.h"
#include "install_location.h"
#include "user_data_cleanup.h"
#include <string>

#if defined(CANGOO_INNO_TEST_ROOT) && !defined(CANGOO_CLEANUP_ACCEPTANCE)
#error Inno acceptance requires isolated cleanup as well.
#endif
#if defined(CANGOO_INNO_TEST_LEGACY_MSI_UPGRADE_CODE) && !defined(CANGOO_INNO_TEST_ROOT)
#error An isolated legacy MSI identity requires an acceptance build.
#endif

int WINAPI CangooInnoValidateFolder(const wchar_t* path, const wchar_t* installed, BOOL machine) {
    using namespace cangoo::install;
    if (!path) return static_cast<int>(FolderStatus::invalid_path);
    // Pascal 的空字符串可经 ABI 传为 null，表示尚无已登记目录。
    if (!installed) installed = L"";
    try {
#ifdef CANGOO_INNO_TEST_ROOT
        if (!machine) {
            const std::wstring prefix = std::wstring(CANGOO_INNO_TEST_ROOT) + L"\\";
            if (wcslen(path) <= prefix.size() ||
                CompareStringOrdinal(path, static_cast<int>(prefix.size()), prefix.c_str(),
                                     static_cast<int>(prefix.size()), TRUE) != CSTR_EQUAL)
                return static_cast<int>(FolderStatus::unsafe_path);
        }
#endif
        return static_cast<int>(machine ? ValidateMachineInstallFolder(path, installed) :
                                          ValidateUserInstallFolder(path, installed));
    } catch (...) { return static_cast<int>(FolderStatus::failed); }
}

int WINAPI CangooInnoLegacyMsiState() {
    constexpr auto production = L"{91633B47-721D-5FB4-85E9-3B45F90CB0D3}";
#ifdef CANGOO_INNO_TEST_ROOT
#ifdef CANGOO_INNO_TEST_LEGACY_MSI_UPGRADE_CODE
    constexpr auto isolated = CANGOO_INNO_TEST_LEGACY_MSI_UPGRADE_CODE;
    // 迁移验收复用真实查询，只允许独立身份，不能触及正式安装。
    if (wcslen(isolated) != 38 || CompareStringOrdinal(isolated, -1, production, -1, TRUE) == CSTR_EQUAL)
        return static_cast<int>(cangoo::install::InstalledState::failed);
    return static_cast<int>(cangoo::install::ReadInstalledLocation(isolated).state);
#else
    (void)production;
    return 0;
#endif
#else
    return static_cast<int>(cangoo::install::ReadInstalledLocation(production).state);
#endif
}

BOOL WINAPI CangooInnoCleanupIdentity() { return cangoo::cleanup::CurrentIdentityMatches(); }

int WINAPI CangooInnoCleanup(DWORD* count, DWORD* deleted, DWORD* retained, DWORD* error) {
    if (!count || !deleted || !retained || !error) return static_cast<int>(cangoo::cleanup::Status::failed);
    const auto result = cangoo::cleanup::DeleteCurrentUserData();
    *count = result.deleted_count;
    *deleted = result.deleted_mask;
    *retained = result.retained_mask;
    *error = result.error;
    return static_cast<int>(result.status);
}
