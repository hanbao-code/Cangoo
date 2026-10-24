"""单个可搜索字段的原文与拼音匹配。"""


def field_matches_query(value: str | None, query: str) -> bool:
    """按原文、连续全拼或连续首字母匹配一个字段。"""
    text = value or ""
    needle = query.casefold()
    if needle in text.casefold():
        return True
    if not text or text.isascii():
        return False

    from pypinyin import lazy_pinyin

    full = []
    initials = []
    for part in lazy_pinyin(text, errors=lambda original: ["\0" + original]):
        if part.startswith("\0"):
            token = part[1:].casefold()
            full.append(token)
            initials.append(token)
        else:
            token = part.casefold().replace("ü", "v")
            full.append(token)
            initials.append(token[:1])
    needle = needle.replace("ü", "v")
    return needle in "".join(full) or needle in "".join(initials)
