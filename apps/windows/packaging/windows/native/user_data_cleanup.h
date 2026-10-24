// SPDX-License-Identifier: MIT
// 许可见本目录 LICENSE。
#pragma once

#include <windows.h>

namespace cangoo::cleanup {

enum class Status { complete, identity_unknown, failed, partial };

// 位 0–5：默认库、wal、shm、journal、设置、安全状态。
inline constexpr DWORD all_files_mask = 0x3f;

struct Result {
    Status status = Status::failed;
    DWORD deleted_count = 0;
    DWORD deleted_mask = 0;
    // 未删除且尚未证实不存在的类别；身份不明时为全部六类。
    DWORD retained_mask = all_files_mask;
    DWORD error = ERROR_SUCCESS;
};

bool CurrentIdentityMatches() noexcept;

// 仅由已确认且最终成功的交互卸载调用；每次重新核身份，不接收删除路径。
Result DeleteCurrentUserData() noexcept;

}  // namespace cangoo::cleanup
