// SPDX-License-Identifier: MIT
#pragma once

#include <windows.h>
#include <wtsapi32.h>
#include <memory>
#include <string>

namespace cangoo::identity {

struct SessionFree { void operator()(wchar_t* value) const noexcept { WTSFreeMemory(value); } };

inline std::wstring SessionText(DWORD session, WTS_INFO_CLASS kind) {
    wchar_t* raw = nullptr;
    DWORD bytes = 0;
    const BOOL ok = WTSQuerySessionInformationW(WTS_CURRENT_SERVER_HANDLE, session, kind, &raw, &bytes);
    std::unique_ptr<wchar_t, SessionFree> text(raw);
    if (!ok || !raw || bytes < sizeof(wchar_t) || bytes > 2048 || bytes % sizeof(wchar_t)) return {};
    const auto length = wcsnlen(raw, bytes / sizeof(wchar_t));
    return length < bytes / sizeof(wchar_t) ? std::wstring(raw, length) : std::wstring{};
}

inline bool TokenMatchesSession(HANDLE token) {
    DWORD session = 0, needed = 0;
    if (!GetTokenInformation(token, TokenSessionId, &session, sizeof(session), &needed) ||
        needed != sizeof(session) || !session) return false;
    wchar_t* raw = nullptr;
    DWORD bytes = 0;
    const BOOL ok = WTSQuerySessionInformationW(WTS_CURRENT_SERVER_HANDLE, session, WTSConnectState, &raw, &bytes);
    std::unique_ptr<wchar_t, SessionFree> state(raw);
    if (!ok || !raw || bytes != sizeof(WTS_CONNECTSTATE_CLASS) ||
        *reinterpret_cast<WTS_CONNECTSTATE_CLASS*>(raw) != WTSActive) return false;
    const auto user = SessionText(session, WTSUserName), domain = SessionText(session, WTSDomainName);
    if (user.empty() || domain.empty()) return false;
    alignas(SID) BYTE account[SECURITY_MAX_SID_SIZE]{};
    DWORD sid_bytes = sizeof(account), domain_chars = 1024;
    wchar_t resolved_domain[1024]{};
    SID_NAME_USE kind{};
    if (!LookupAccountNameW(nullptr, (domain + L"\\" + user).c_str(), account, &sid_bytes,
                           resolved_domain, &domain_chars, &kind) || kind != SidTypeUser) return false;
    alignas(TOKEN_USER) BYTE info[sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE]{};
    if (!GetTokenInformation(token, TokenUser, info, sizeof(info), &needed)) return false;
    const auto sid = reinterpret_cast<TOKEN_USER*>(info)->User.Sid;
    return IsValidSid(sid) && IsValidSid(account) && EqualSid(sid, account);
}

inline bool IsElevated(HANDLE token, bool& elevated) {
    TOKEN_ELEVATION value{};
    DWORD needed = 0;
    if (!GetTokenInformation(token, TokenElevation, &value, sizeof(value), &needed) || needed != sizeof(value)) return false;
    elevated = value.TokenIsElevated != 0;
    return true;
}

}  // namespace cangoo::identity
