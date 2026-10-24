package app.cangoo.android.data

import android.icu.lang.UCharacter

/** D36记事导入的标题候选键；不代替密码及库名的精确同名规则。 */
fun similarNoteTitleKey(value: String): String {
    return buildString(value.length) {
        var index = 0
        while (index < value.length) {
            val point = value.codePointAt(index)
            if (!windowsWhitespace(point)) {
                // Windows使用Python3.10的Unicode13；更新系统不能额外合并后来新增字母。
                when (point) {
                    // Unicode12/13新增的折叠补给安卓10所用的旧字符表。
                    0xa7ba -> appendCodePoint(0xa7bb)
                    0xa7bc -> appendCodePoint(0xa7bd)
                    0xa7be -> appendCodePoint(0xa7bf)
                    0xa7c2 -> appendCodePoint(0xa7c3)
                    0xa7c4 -> appendCodePoint(0xa794)
                    0xa7c5 -> appendCodePoint(0x0282)
                    0xa7c6 -> appendCodePoint(0x1d8e)
                    0xa7c7 -> appendCodePoint(0xa7c8)
                    0xa7c9 -> appendCodePoint(0xa7ca)
                    0xa7f5 -> appendCodePoint(0xa7f6)
                    else -> if (UCharacter.getAge(point).major > 13) appendCodePoint(point)
                        else append(UCharacter.foldCase(String(Character.toChars(point)), true))
                }
            }
            index += Character.charCount(point)
        }
    }
}

// Python Unicode13的29项空白，来源与完整折叠公开参考见仪器检查资产。
private fun windowsWhitespace(point: Int): Boolean = point in 0x09..0x0d || point in 0x1c..0x20 ||
    point == 0x85 || point == 0xa0 || point == 0x1680 || point in 0x2000..0x200a ||
    point in 0x2028..0x2029 || point == 0x202f || point == 0x205f || point == 0x3000
