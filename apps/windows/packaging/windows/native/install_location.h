// SPDX-License-Identifier: MIT
// 许可见本目录 LICENSE。
#pragma once

#include <windows.h>
#include <string>

namespace cangoo::install {

enum class InstalledState { none, unique, conflict, failed };
struct InstalledLocation {
    InstalledState state = InstalledState::failed;
    std::wstring path;
    bool machine = false;
    DWORD error = ERROR_SUCCESS;
};

enum class FolderStatus { valid, invalid_path, unsafe_path, occupied, different_location, failed };

std::wstring DefaultInstallFolder(bool machine) noexcept;
InstalledLocation ReadInstalledLocation(const std::wstring& upgrade_guid) noexcept;

// 只读取本次规划时的路径快照，不锁定随后 MSI 写入期间的目录。
FolderStatus ValidateInstallFolder(const std::wstring& path,
                                  const std::wstring& known_installed_path = {}) noexcept;

}
