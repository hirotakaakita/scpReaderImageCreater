"""フォント読み込み・フォールバック・折り返し・自動縮小フィット。

言語別フォント（例: NotoSansThai）にはラテン文字や記号が無いことがあるため、
グリフの有無を見てフォールバックフォント（NotoSans）に切り替えて描画する。
"""
from fontTools.ttLib import TTFont
from PIL import ImageFont

_font_cache = {}
_cov_cache = {}

# 行頭に来てはいけない文字（簡易禁則処理）
_KINSOKU_HEAD = "、。，．！？…‥ー〜）」』】〕｝〉》!?,.;:)]}"


def load_font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def _coverage(path):
    """フォントが持つコードポイント集合（取得失敗時はNone=全部持つ扱い）。"""
    if path not in _cov_cache:
        try:
            tt = TTFont(path, fontNumber=0, lazy=True)
            _cov_cache[path] = set(tt.getBestCmap().keys())
            tt.close()
        except Exception:
            _cov_cache[path] = None
    return _cov_cache[path]


class FontSet:
    """主フォント+フォールバックフォントの組。文字ごとに使い分ける。"""

    def __init__(self, primary_path, size, fallback_path=None):
        self.size = size
        self.primary = load_font(primary_path, size)
        self._pcov = _coverage(primary_path)
        self.fallback = None
        if fallback_path and fallback_path != primary_path:
            self.fallback = load_font(fallback_path, size)

    def _font_for(self, ch):
        if (self.fallback is not None and self._pcov is not None
                and ord(ch) not in self._pcov):
            return self.fallback
        return self.primary

    def runs(self, text):
        """同じフォントで描ける連続文字列に分割する。"""
        out = []
        for ch in text:
            f = self._font_for(ch)
            if out and out[-1][1] is f:
                out[-1][0] += ch
            else:
                out.append([ch, f])
        return [(t, f) for t, f in out]

    def width(self, draw, text):
        return sum(draw.textlength(t, font=f) for t, f in self.runs(text))

    def line_height(self):
        fonts = [self.primary] + ([self.fallback] if self.fallback else [])
        return max(sum(f.getmetrics()) for f in fonts)

    def draw_line(self, draw, x, y, text, fill):
        for t, f in self.runs(text):
            draw.text((x, y), t, font=f, fill=fill)
            x += draw.textlength(t, font=f)


def _break_long_word(draw, word, fs, max_width):
    lines, cur = [], ""
    for ch in word:
        if cur and fs.width(draw, cur + ch) > max_width:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def wrap_text(draw, text, fs, max_width, char_wrap=False):
    """max_widthに収まるよう折り返した行のリストを返す。"""
    lines = []
    for raw in text.split("\n"):
        raw = raw.strip()
        if not raw:
            lines.append("")
            continue
        if char_wrap:
            cur = ""
            for ch in raw:
                if cur and fs.width(draw, cur + ch) > max_width:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            if cur:
                lines.append(cur)
        else:
            cur = ""
            for word in raw.split(" "):
                cand = (cur + " " + word) if cur else word
                if cur and fs.width(draw, cand) > max_width:
                    lines.append(cur)
                    cur = word
                else:
                    cur = cand
                if fs.width(draw, cur) > max_width:
                    parts = _break_long_word(draw, cur, fs, max_width)
                    lines.extend(parts[:-1])
                    cur = parts[-1] if parts else ""
            if cur:
                lines.append(cur)
    # 簡易禁則: 行頭の約物を前の行末に送る
    for i in range(1, len(lines)):
        while lines[i] and lines[i][0] in _KINSOKU_HEAD:
            lines[i - 1] += lines[i][0]
            lines[i] = lines[i][1:]
    return [ln for ln in lines if ln != ""] or [""]


def fit_text(draw, text, font_path, max_width, max_height,
             start_size, min_size, line_spacing, char_wrap=False,
             fallback_path=None):
    """max_width×max_heightに収まる最大フォントで折り返す。

    Returns: (FontSet, lines, block_width, block_height)
    """
    best = None
    for size in range(start_size, min_size - 1, -1):
        fs = FontSet(font_path, size, fallback_path)
        lines = wrap_text(draw, text, fs, max_width, char_wrap)
        lh = fs.line_height()
        block_h = lh * len(lines) + line_spacing * (len(lines) - 1)
        block_w = max(fs.width(draw, ln) for ln in lines)
        best = (fs, lines, block_w, block_h)
        if block_w <= max_width and block_h <= max_height:
            return best
    return best  # 最小サイズでも収まらない場合はそのまま返す（呼び出し側でwarn）


def draw_text_block(draw, lines, fs, center_x, top_y, line_spacing, fill):
    """行リストを中央揃えで描く。"""
    y = top_y
    lh = fs.line_height()
    for ln in lines:
        w = fs.width(draw, ln)
        fs.draw_line(draw, center_x - w / 2, y, ln, fill)
        y += lh + line_spacing
