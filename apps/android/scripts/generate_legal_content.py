"""从共同协议与安卓固定许可清单生成 legal_content.json；生成物不手改。"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile


ANDROID_ROOT = Path(__file__).resolve().parents[1]
ASSETS = ANDROID_ROOT / "app/src/main/assets"
TERMS_SOURCE = ANDROID_ROOT.parent / "windows/desktop/frontend/assets/help/content.json"
OUTPUT = ASSETS / "legal_content.json"


def nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 必须是非空字符串")
    return value


def build_content(terms_source=TERMS_SOURCE, assets=ASSETS):
    source = json.loads(terms_source.read_text(encoding="utf-8"))
    version = nonempty_string(source["terms_version"], "terms_version")
    author = nonempty_string(source["author"], "author")
    terms = {
        language: nonempty_string(source["terms"][language], f"terms.{language}")
        .replace("{terms_version}", version)
        for language in ("zh", "en")
    }
    documents = source["license_documents"]
    if set(documents) != {"agpl", "openssl"}:
        raise ValueError("本地许可文档必须为agpl和openssl")
    for identifier, document in documents.items():
        nonempty_string(document["text"], f"{identifier}.text")
        for field in ("title", "intro"):
            for language in ("zh", "en"):
                nonempty_string(document[field][language], f"{identifier}.{field}.{language}")
    introduction = {language: nonempty_string(source["licenseIntro"][language], f"licenseIntro.{language}")
                    for language in ("zh", "en")}
    catalog = json.loads((assets / "third_party/catalog.json").read_text(encoding="utf-8"))
    entries = catalog["licenses"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("许可清单必须是非空列表")
    licenses = []
    seen = set()
    for entry in entries:
        identifier = nonempty_string(entry["id"], "许可 id")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", identifier) or identifier in seen:
            raise ValueError(f"许可 id 无效或重复：{identifier}")
        seen.add(identifier)
        relative = nonempty_string(entry["path"], f"{identifier}.path")
        path = (assets / relative).resolve()
        if "\\" in relative or Path(relative).is_absolute() or not path.is_relative_to(assets.resolve()):
            raise ValueError(f"许可路径必须位于 assets 内：{identifier}")
        nonempty_string(entry["origin"], f"{identifier}.origin")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"许可来源摘要不符：{identifier}")
        text = nonempty_string(raw.decode("utf-8"), f"{identifier}.text")
        if entry["format"] not in ("text", "html"):
            raise ValueError(f"许可格式无效：{identifier}")
        licenses.append({
            "id": identifier,
            "title": nonempty_string(entry["title"], f"{identifier}.title"),
            "version": nonempty_string(entry["version"], f"{identifier}.version"),
            "text": text,
            "format": entry["format"],
        })
    return {"terms_version": version, "author": author, "terms": terms, "licenses": licenses,
            "license_documents": documents, "licenseIntro": introduction}


def self_test():
    with tempfile.TemporaryDirectory(prefix="cangoo_legal_") as temporary:
        root = Path(temporary)
        assets = root / "assets"
        (assets / "third_party").mkdir(parents=True)
        source = root / "content.json"
        terms = {"terms_version": "3", "author": "author", "terms": {"zh": "版本 {terms_version}", "en": "Version {terms_version}"}}
        terms["license_documents"] = {identifier: {"title": {"zh": "标题", "en": "Title"},
            "intro": {"zh": "简介", "en": "Intro"}, "text": "Original public text\n"}
            for identifier in ("agpl", "openssl")}
        terms["licenseIntro"] = {"zh": "第三方声明", "en": "Third-party notices"}
        source.write_text(json.dumps(terms), encoding="utf-8")
        license_path = assets / "license.txt"
        license_path.write_bytes(b"Original license\n")
        entry = {"id": "sample", "title": "Sample", "version": "1", "path": "license.txt", "origin": "https://example.org/LICENSE", "sha256": hashlib.sha256(license_path.read_bytes()).hexdigest(), "format": "text"}
        catalog_path = assets / "third_party/catalog.json"

        def write_catalog(entries):
            catalog_path.write_text(json.dumps({"licenses": entries}), encoding="utf-8")

        def must_reject():
            try:
                build_content(source, assets)
            except ValueError:
                return
            raise AssertionError("无效来源未被拒绝")

        write_catalog([entry])
        content = build_content(source, assets)
        assert content["terms"]["zh"] == "版本 3"
        assert content["licenses"][0]["text"] == "Original license\n"
        assert content["license_documents"]["agpl"]["text"] == "Original public text\n"
        for invalid in (
            [entry, entry],
            [{**entry, "path": "../content.json"}],
            [{**entry, "sha256": "0" * 64}],
            [{**entry, "format": "markdown"}],
        ):
            write_catalog(invalid)
            must_reject()
        license_path.write_bytes(b"")
        write_catalog([{**entry, "sha256": hashlib.sha256(b"").hexdigest()}])
        must_reject()
        terms["terms_version"] = 3
        source.write_text(json.dumps(terms), encoding="utf-8")
        must_reject()
    print("法律资源生成器自检通过")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只检查生成物与来源一致")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="生成物路径")
    parser.add_argument("--self-test", action="store_true", help="检查正常生成与无效来源拒绝")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    try:
        content = (json.dumps(build_content(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if args.check:
            if not args.output.is_file() or args.output.read_bytes() != content:
                raise ValueError("法律资源已过期或缺失，请运行 apps/android/scripts/generate_legal_content.py")
            print("法律资源与来源一致")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(content)
            print(f"已生成 {args.output}")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"法律资源生成失败：{error}\n")


if __name__ == "__main__":
    main()
