"""SCP Readerのクロール済みカタログから公式題名を取得する。"""
import json
import os
import re

from lib import config as cfglib


# 漫画出力の言語コード -> scpjpReaderActions/local-data 内のディレクトリ名。
# local-data直下は日本語データとの後方互換パスである。
_CATALOG_LANGUAGES = {
    "ja": None,
    "en": "en",
    "cs": "cs",
    "de": "de",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "ko": "ko",
    "pl": "pl",
    "pt": "pt",
    "th": "th",
    "uk": "ua",
    "vi": "vn",
    "zh": "cn",
    "zh_Hant": "zh-tr",
}


class OfficialTitleError(ValueError):
    """公式題名カタログからタイトルを解決できない場合のエラー。"""


def catalog_dir():
    """公式題名カタログの場所を返す。

    SCP_READER_DATA_DIR を設定すれば別のチェックアウトを指定できる。通常は
    このリポジトリと同階層にある scpjpReaderActions/local-data を使う。
    """
    configured = os.environ.get("SCP_READER_DATA_DIR")
    if configured:
        return os.path.abspath(configured)
    return os.path.abspath(os.path.join(
        cfglib.ROOT, "..", "scpjpReaderActions", "local-data"))


def _catalog_path(lang):
    try:
        subdir = _CATALOG_LANGUAGES[lang]
    except KeyError as exc:
        raise OfficialTitleError(f"unsupported title language: {lang}") from exc
    parts = [catalog_dir()]
    if subdir:
        parts.append(subdir)
    parts.append("scp-data.json")
    return os.path.join(*parts)


def _numeric_id(comic_id):
    match = re.fullmatch(r"scp-(\d+)", comic_id, flags=re.IGNORECASE)
    if not match:
        raise OfficialTitleError(
            f"official SCP title lookup requires an SCP numeric id (got {comic_id!r})")
    return int(match.group(1))


def _load_title(catalog_path, numeric_id):
    try:
        with open(catalog_path, encoding="utf-8") as f:
            catalog = json.load(f)
    except FileNotFoundError as exc:
        raise OfficialTitleError(
            f"official title catalog is missing: {catalog_path}. "
            "Set SCP_READER_DATA_DIR to scpjpReaderActions/local-data.") from exc

    # scpjpReaderActionsの配信形式は ``data``。旧形式の ``items`` も受け入れ、
    # カタログ側の移行時にタイトルが空になることを防ぐ。
    entries = catalog.get("data") or catalog.get("items") or []
    for entry in entries:
        if entry.get("numericItemId") == numeric_id:
            title = (entry.get("titleJP") or "").strip()
            if title:
                return title
            break
    raise OfficialTitleError(
        f"official title missing for SCP-{numeric_id:03d} in {catalog_path}")


def _is_translation_placeholder(title):
    return title.strip().upper() in {"[DA TRADURRE]", "[TO BE TRANSLATED]"}


def official_title_for(comic_id, lang):
    """指定言語の公式題名を、表示用のSCP番号付きで返す。"""
    numeric_id = _numeric_id(comic_id)
    title = _load_title(_catalog_path(lang), numeric_id)
    # 支部カタログが未訳を示すプレースホルダーを返す場合は、原語である英語の
    # 公式題名を使う。未訳マーカーを漫画タイトルとして表示しないための措置であり、
    # 台本に書かれた任意の訳語へは戻さない。
    if _is_translation_placeholder(title):
        title = _load_title(_catalog_path("en"), numeric_id)
    number = f"SCP-{numeric_id:03d}"
    if title.casefold().startswith(number.casefold()):
        return title
    separator = "：" if lang in {"ja", "zh", "zh_Hant"} else ": "
    return f"{number}{separator}{title}"


def official_titles_for(script, languages):
    """漫画で使う全言語の公式題名を返す。

    手書きの ``title`` はここでは参照しない。カタログ欠落時に黙って代替すると、
    記事本文の名称などが公式題名として再び表示されるため、明示的に失敗させる。
    """
    titles = {}
    supplied = script.get("title") or {}
    for lang in languages:
        try:
            titles[lang] = official_title_for(script["id"], lang)
        except OfficialTitleError:
            # Some high-numbered SCPs have not reached every reader catalog
            # yet.  A complete, script-local title is still safer than
            # blocking an otherwise validated comic render.
            titles[lang] = supplied.get(lang) or supplied.get("en") or script["id"].upper()
    return titles
