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
std::wstring InstallFolderFromParent(const std::wstring& parent) noexcept;
InstalledLocation ReadInstalledLocation(const std::wstring& upgrade_guid) noexcept;

// 只读取本次规划时的路径快照，不锁定随后 MSI 写入期间的目录。
FolderStatus ValidateInstallFolder(const std::wstring& path,
                                  const std::wstring& known_installed_path = {}) noexcept;

// 所有用户安装只接受系统程序目录及受保护的现有文件；不更改权限或迁移旧安装。
FolderStatus ValidateMachineInstallFolder(const std::wstring& path,
                                         const std::wstring& known_installed_path = {}) noexcept;

// 检查路径、占用、重解析点与实际创建权限；不修改目录权限。
FolderStatus ValidateUserInstallFolder(const std::wstring& path,
                                        const std::wstring& known_installed_path = {}) noexcept;

}
