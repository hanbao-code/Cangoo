"""从选定原稿确定性导出两端统一品牌资源，保留主体原色与比例。"""

from collections import deque
import hashlib
from pathlib import Path
import struct

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader, QPainter


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs/product/brand_assets/cangoo_c0_d1_o3_original.png"
SOURCE_SHA256 = "edef19bc2fb8aeb54304a0d39cb3fdc5a8d1e1d6ecba8e64d8cbda926cdc1c2a"
OUTPUT = ROOT / "apps/windows/resources/icons/cangoo"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def connected(candidates: bytearray, seeds: list[int], width: int, height: int) -> bytearray:
    """取得指定种子所在的相连像素区域。"""
    found = bytearray(width * height)
    queue: deque[int] = deque()

    def visit(index: int) -> None:
        if candidates[index] and not found[index]:
            found[index] = 1
            queue.append(index)

    for index in seeds:
        visit(index)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        if x: visit(index - 1)
        if x + 1 < width: visit(index + 1)
        if y: visit(index - width)
        if y + 1 < height: visit(index + width)
    return found


def cutout(source: QImage, *, animal_only: bool = False) -> QImage:
    """只移除外沿底色，前景另去除不与主体相连的底板边缘。"""
    width, height = source.width(), source.height()
    pixels = bytearray(source.constBits())
    candidates = bytearray(width * height)
    for index in range(width * height):
        red, green, blue = pixels[index * 4:index * 4 + 3]
        if animal_only:
            gray = blue >= red - 6 and abs(red - green) <= 12 and abs(green - blue) <= 12 and min(red, green, blue) >= 160
        else:
            gray = max(red, green, blue) - min(red, green, blue) <= 64 and min(red, green, blue) >= 140
        orange = red > 200 and red - green > 35 and green - blue > 25
        candidates[index] = gray or (animal_only and orange)
    edges = list(range(width)) + list(range((height - 1) * width, height * width))
    edges += [y * width + x for y in range(height) for x in (0, width - 1)]
    background = connected(candidates, edges, width, height)
    keep = bytearray(not value for value in background)
    if animal_only:
        # 已锁定原稿的中央深蓝主体，排除底板圆角留下的独立细边。
        keep = connected(keep, [600 * width + 600], width, height)
    for index, opaque in enumerate(keep):
        if not opaque:
            pixels[index * 4 + 3] = 0
    result = QImage(bytes(pixels), width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
    assert result.pixelColor(0, 0).alpha() == 0
    for x, y in ((600, 600), (600, 1000), (450, 400)):
        assert result.pixelColor(x, y) == source.pixelColor(x, y), (x, y)
    assert result.pixelColor(600, 100).alpha() == (0 if animal_only else 255)
    return result


def opaque_bounds(image: QImage) -> tuple[int, int, int, int]:
    width, height = image.width(), image.height()
    alpha = bytes(image.constBits())[3::4]
    left, top, right, bottom = width, height, -1, -1
    for y in range(height):
        row = alpha[y * width:(y + 1) * width]
        first = row.find(b"\xff")
        if first >= 0:
            left, right = min(left, first), max(right, row.rfind(b"\xff"))
            top, bottom = min(top, y), y
    assert right >= left and bottom >= top
    return left, top, right - left + 1, bottom - top + 1


def square(image: QImage, size: int, content_size: int | None = None) -> QImage:
    image = image.scaled(content_size or size, content_size or size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    canvas = QImage(size, size, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.drawImage((size - image.width()) // 2, (size - image.height()) // 2, image)
    painter.end()
    return canvas


def save(image: QImage, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG"), path
    loaded = QImage(str(path))
    assert loaded == image and loaded.hasAlphaChannel(), path
    assert loaded.width() == loaded.height() and loaded.pixelColor(0, 0).alpha() == 0, path


def main() -> None:
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256, "选定原稿已变化"
    source = QImage(str(SOURCE)).convertToFormat(QImage.Format.Format_RGBA8888)
    assert source.width() == 1214 and source.height() == 1295 and source.bytesPerLine() == source.width() * 4
    master = square(cutout(source), max(source.width(), source.height()))
    save(master, OUTPUT / "app_master.png")
    entries, payloads = [], []
    offset = 6 + 16 * len(SIZES)
    for size in (*SIZES, 512):
        path = OUTPUT / f"app_{size}.png"
        save(square(master, size), path)
        if size <= 256:
            data = path.read_bytes()
            entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
            payloads.append(data)
            offset += len(data)
    icon = OUTPUT / "app.ico"
    icon.write_bytes(struct.pack("<HHH", 0, 1, len(SIZES)) + b"".join(entries) + b"".join(payloads))
    reader = QImageReader(str(icon))
    assert reader.imageCount() == len(SIZES)
    for index, size in enumerate(SIZES):
        assert reader.jumpToImage(index)
        image = reader.read()
        assert not image.isNull() and image.width() == image.height() == size
        assert image.hasAlphaChannel() and image.pixelColor(0, 0).alpha() == 0
    for relative, size in (
        ("apps/windows/desktop/frontend/assets/brand/cangoo.png", 128),
        ("apps/android/app/src/main/res/drawable-nodpi/app_icon.png", 512),
        ("apps/android/prototypes/mobile_b/public/app_icon.png", 512),
    ):
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((OUTPUT / f"app_{size}.png").read_bytes())
    animal = cutout(source, animal_only=True)
    animal = animal.copy(*opaque_bounds(animal))
    # 108单位画布中主体占58单位，并核对直径66单位的圆形安全区。
    foreground = square(animal, 432, 232)
    rgba = foreground.convertToFormat(QImage.Format.Format_RGBA8888)
    alpha = bytes(rgba.constBits())[3::4]
    assert all((index % 432 - 215.5) ** 2 + (index // 432 - 215.5) ** 2 <= 132 ** 2
               for index, value in enumerate(alpha) if value), "安卓前景超出圆形安全区"
    save(foreground, ROOT / "apps/android/app/src/main/res/drawable-nodpi/app_icon_foreground.png")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    print("统一图标：原稿摘要、主体原值、透明边缘、10档PNG、9帧ICO及两端同源资源检查通过")


if __name__ == "__main__":
    main()
