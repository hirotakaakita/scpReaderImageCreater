"""吹き出し・タイトル・フッターの描画。"""
import math

from . import textutil


def _inflate_box(box, d):
    x0, y0, x1, y1 = box
    return (x0 - d, y0 - d, x1 + d, y1 + d)


def _tail_points(box, direction, length, width):
    """吹き出しのしっぽ（三角形）の頂点を返す。base2点はboxの辺上。"""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d = direction
    if d.startswith("down") or d.startswith("up"):
        down = d.startswith("down")
        edge_y = y1 if down else y0
        sign = 1 if down else -1
        if d.endswith("left"):
            bx = x0 + (x1 - x0) * 0.28
            ax = bx - length * 0.6
        elif d.endswith("right"):
            bx = x0 + (x1 - x0) * 0.72
            ax = bx + length * 0.6
        else:
            bx, ax = cx, cx
        p1 = (bx - width / 2, edge_y)
        p2 = (bx + width / 2, edge_y)
        apex = (ax, edge_y + sign * length)
    elif d in ("left", "right"):
        left = d == "left"
        edge_x = x0 if left else x1
        sign = -1 if left else 1
        p1 = (edge_x, cy - width / 2)
        p2 = (edge_x, cy + width / 2)
        apex = (edge_x + sign * length, cy)
    else:
        raise ValueError(f"unknown tail direction: {direction}")
    return p1, p2, apex


def _inflate_tail(pts, d):
    """しっぽ三角形を外側にd分だけ膨らませる（輪郭パス用）。"""
    p1, p2, apex = pts
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    vx, vy = apex[0] - mid[0], apex[1] - mid[1]
    vlen = math.hypot(vx, vy) or 1.0
    apex_out = (apex[0] + vx / vlen * d * 1.6, apex[1] + vy / vlen * d * 1.6)
    ex, ey = p2[0] - p1[0], p2[1] - p1[1]
    elen = math.hypot(ex, ey) or 1.0
    ex, ey = ex / elen * d * 1.2, ey / elen * d * 1.2
    return (p1[0] - ex, p1[1] - ey), (p2[0] + ex, p2[1] + ey), apex_out


def _draw_shape(draw, box, radius, tail_pts, color):
    if tail_pts:
        draw.polygon([tail_pts[0], tail_pts[1], tail_pts[2]], fill=color)
    draw.rounded_rectangle(box, radius=radius, fill=color)


def draw_bubble(draw, box, bubble_cfg, tail=None):
    """輪郭付き吹き出しを描く。二重描画方式（外側=輪郭色、内側=塗り）で
    しっぽと角丸矩形の継ぎ目を作らない。"""
    ow = bubble_cfg["outline_width"]
    radius = bubble_cfg["corner_radius"]
    tail_pts = None
    if tail:
        tail_pts = _tail_points(box, tail, bubble_cfg["tail_length"], bubble_cfg["tail_width"])
    outer_tail = _inflate_tail(tail_pts, ow) if tail_pts else None
    _draw_shape(draw, _inflate_box(box, ow), radius + ow, outer_tail, bubble_cfg["outline"])
    _draw_shape(draw, box, radius, tail_pts, bubble_cfg["fill"])


def draw_speech(draw, panel_rect, area_norm, text, font_path, bubble_cfg,
                tail=None, char_wrap=False, fallback_path=None):
    """コマ内の正規化領域area_normに吹き出し+テキストを描く。

    吹き出し本体はテキスト量に応じて縮み、領域の中央に置かれる。
    """
    px0, py0, px1, py1 = panel_rect
    pw, ph = px1 - px0, py1 - py0
    ax0 = px0 + area_norm["x"] * pw
    ay0 = py0 + area_norm["y"] * ph
    aw = area_norm["w"] * pw
    ah = area_norm["h"] * ph

    pad = bubble_cfg["padding"]
    font, lines, bw, bh = textutil.fit_text(
        draw, text, font_path,
        max_width=aw - pad * 2,
        max_height=ah - pad * 2,
        start_size=bubble_cfg["font_size"],
        min_size=bubble_cfg["min_font_size"],
        line_spacing=bubble_cfg["line_spacing"],
        char_wrap=char_wrap,
        fallback_path=fallback_path,
    )
    fits = bw <= aw - pad * 2 and bh <= ah - pad * 2
    box_w = min(bw + pad * 2, aw)
    box_h = min(bh + pad * 2, ah)
    bx0 = ax0 + (aw - box_w) / 2
    by0 = ay0 + (ah - box_h) / 2
    box = (bx0, by0, bx0 + box_w, by0 + box_h)

    draw_bubble(draw, box, bubble_cfg, tail=tail)
    textutil.draw_text_block(
        draw, lines, font,
        center_x=(box[0] + box[2]) / 2,
        top_y=by0 + (box_h - bh) / 2,
        line_spacing=bubble_cfg["line_spacing"],
        fill=bubble_cfg["text_color"],
    )
    return fits


def draw_header_text(draw, header_rect, title, font_path, header_cfg,
                     subtitle=None, fallback_path=None):
    """タイトル帯にタイトル（+ 任意でオブジェクトクラスのサブタイトル）を描く。"""
    x0, y0, x1, y1 = header_rect
    full_h = y1 - y0
    title_h = full_h * (0.62 if subtitle else 0.9)
    font, lines, bw, bh = textutil.fit_text(
        draw, title, font_path,
        max_width=(x1 - x0) * 0.94,
        max_height=title_h,
        start_size=header_cfg["font_size"],
        min_size=max(12, header_cfg["font_size"] // 3),
        line_spacing=2,
        char_wrap=False,
        fallback_path=fallback_path,
    )
    if not subtitle:
        textutil.draw_text_block(
            draw, lines, font,
            center_x=(x0 + x1) / 2,
            top_y=y0 + (full_h - bh) / 2,
            line_spacing=2,
            fill=header_cfg["color"],
        )
        return

    sub_h = full_h - title_h
    sub_font, sub_lines, sbw, sbh = textutil.fit_text(
        draw, subtitle, font_path,
        max_width=(x1 - x0) * 0.94,
        max_height=sub_h * 0.9,
        start_size=header_cfg.get("subtitle_font_size", header_cfg["font_size"] // 2),
        min_size=max(10, header_cfg["font_size"] // 4),
        line_spacing=2,
        char_wrap=False,
        fallback_path=fallback_path,
    )
    block_h = bh + sbh
    top_y = y0 + (full_h - block_h) / 2
    textutil.draw_text_block(
        draw, lines, font,
        center_x=(x0 + x1) / 2,
        top_y=top_y,
        line_spacing=2,
        fill=header_cfg["color"],
    )
    textutil.draw_text_block(
        draw, sub_lines, sub_font,
        center_x=(x0 + x1) / 2,
        top_y=top_y + bh,
        line_spacing=2,
        fill=header_cfg["color"],
    )


def draw_caption_frame(draw, rect, caption_cfg):
    """SCP文書調のキャプション枠（白地・黒枠）を描く。文字は別途draw_caption_textで描く。"""
    draw.rectangle(rect, fill=caption_cfg["fill"], outline=caption_cfg["outline"],
                   width=caption_cfg["outline_width"])


def draw_caption(draw, panel_rect, area_norm, anchor, text, font_path, caption_cfg,
                 char_wrap=False, fallback_path=None):
    """コマ内area_norm領域の隅（anchor）に、文字量に合わせて縮む枠+文字を描く。

    draw_speech（吹き出し）と同じ「最大領域を決めてから文字に合わせて箱を縮める」方式。
    幅いっぱいに広がるバナーにならないよう、area_normで最大幅を絞っておく想定。
    """
    px0, py0, px1, py1 = panel_rect
    pw, ph = px1 - px0, py1 - py0
    ax0 = px0 + area_norm["x"] * pw
    ay0 = py0 + area_norm["y"] * ph
    aw = area_norm["w"] * pw
    ah = area_norm["h"] * ph

    pad = caption_cfg["padding"]
    font, lines, bw, bh = textutil.fit_text(
        draw, text, font_path,
        max_width=aw - pad * 2,
        max_height=ah - pad * 2,
        start_size=caption_cfg["font_size"],
        min_size=caption_cfg["min_font_size"],
        line_spacing=caption_cfg["line_spacing"],
        char_wrap=char_wrap,
        fallback_path=fallback_path,
    )
    fits = bw <= aw - pad * 2 and bh <= ah - pad * 2
    box_w = min(bw + pad * 2, aw)
    box_h = min(bh + pad * 2, ah)

    bx0 = ax0 + (aw - box_w) if "right" in anchor else ax0
    by0 = ay0 + (ah - box_h) if "bottom" in anchor else ay0
    box = (bx0, by0, bx0 + box_w, by0 + box_h)

    draw_caption_frame(draw, box, caption_cfg)
    textutil.draw_text_block_left(
        draw, lines, font,
        left_x=bx0 + pad,
        top_y=by0 + (box_h - bh) / 2,
        line_spacing=caption_cfg["line_spacing"],
        fill=caption_cfg["text_color"],
    )
    return fits


def draw_caption_text(draw, rect, text, font_path, caption_cfg,
                      char_wrap=False, fallback_path=None):
    """キャプション枠内に左揃えでテキストを描く。収まったかどうかを返す。"""
    x0, y0, x1, y1 = rect
    pad = caption_cfg["padding"]
    font, lines, bw, bh = textutil.fit_text(
        draw, text, font_path,
        max_width=(x1 - x0) - pad * 2,
        max_height=(y1 - y0) - pad * 2,
        start_size=caption_cfg["font_size"],
        min_size=caption_cfg["min_font_size"],
        line_spacing=caption_cfg["line_spacing"],
        char_wrap=char_wrap,
        fallback_path=fallback_path,
    )
    fits = bw <= (x1 - x0) - pad * 2 and bh <= (y1 - y0) - pad * 2
    textutil.draw_text_block_left(
        draw, lines, font,
        left_x=x0 + pad,
        top_y=y0 + ((y1 - y0) - bh) / 2,
        line_spacing=caption_cfg["line_spacing"],
        fill=caption_cfg["text_color"],
    )
    return fits


def draw_footer_text(draw, footer_rect, lines_of_text, font_path, footer_cfg):
    """ライセンス表記をフッター帯に描く。"""
    x0, y0, x1, y1 = footer_rect
    size = footer_cfg["font_size"]
    spacing = footer_cfg["line_spacing"]
    # 全行が幅に収まるサイズまで縮小
    fs = textutil.FontSet(font_path, size)
    while size > 10:
        fs = textutil.FontSet(font_path, size)
        if all(fs.width(draw, ln) <= (x1 - x0) * 0.96 for ln in lines_of_text):
            break
        size -= 1
    lh = fs.line_height()
    block_h = lh * len(lines_of_text) + spacing * (len(lines_of_text) - 1)
    textutil.draw_text_block(
        draw, lines_of_text, fs,
        center_x=(x0 + x1) / 2,
        top_y=y0 + ((y1 - y0) - block_h) / 2,
        line_spacing=spacing,
        fill=footer_cfg["color"],
    )
