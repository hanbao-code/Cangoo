// SPDX-License-Identifier: MIT
#pragma once
#include <windows.h>

extern "C" {
__declspec(dllexport) int WINAPI CangooInnoValidateFolder(const wchar_t* path, const wchar_t* installed, BOOL machine);
__declspec(dllexport) int WINAPI CangooInnoLegacyMsiState();
__declspec(dllexport) BOOL WINAPI CangooInnoCleanupIdentity();
__declspec(dllexport) int WINAPI CangooInnoCleanup(DWORD* deleted_count, DWORD* deleted_mask,
                                                 DWORD* retained_mask, DWORD* error);
}
