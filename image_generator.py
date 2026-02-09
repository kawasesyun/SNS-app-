"""名言を画像化するモジュール（グラデーション背景 + 装飾付き）"""

import os
import random
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# 画像サイズ（X推奨: 16:9）
WIDTH = 1200
HEIGHT = 675

# フォントパス（Windows / Linux CI 両対応）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/NotoSansJP-VF.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]
FONT_PATH = next((f for f in _FONT_CANDIDATES if os.path.exists(f)), None)

# グラデーション配色パターン（始点色, 終点色, テキスト色, サブ色, アクセント色）
COLOR_SCHEMES = [
    {"grad1": (26, 26, 46), "grad2": (22, 33, 62), "text": "#ffffff", "sub": "#cccccc", "accent": "#e94560"},
    {"grad1": (15, 15, 15), "grad2": (40, 20, 60), "text": "#f5f5f5", "sub": "#aaaaaa", "accent": "#f7b731"},
    {"grad1": (27, 27, 58), "grad2": (10, 50, 60), "text": "#ffffff", "sub": "#bbbbbb", "accent": "#6fffe9"},
    {"grad1": (13, 27, 42), "grad2": (44, 62, 80), "text": "#e0e1dd", "sub": "#98c1d9", "accent": "#ee6c4d"},
    {"grad1": (20, 20, 30), "grad2": (60, 20, 40), "text": "#ffffff", "sub": "#cccccc", "accent": "#ff6b6b"},
    {"grad1": (10, 10, 30), "grad2": (30, 60, 90), "text": "#ffffff", "sub": "#b0c4de", "accent": "#74b9ff"},
    {"grad1": (30, 15, 40), "grad2": (80, 40, 60), "text": "#ffffff", "sub": "#ddaacc", "accent": "#ff79c6"},
    {"grad1": (5, 25, 20), "grad2": (20, 60, 50), "text": "#e0fff0", "sub": "#88ccaa", "accent": "#50fa7b"},
]


def _create_gradient(width, height, color1, color2, direction="diagonal"):
    """グラデーション背景を生成"""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            if direction == "diagonal":
                ratio = (x + y) / (width + height)
            elif direction == "radial":
                cx, cy = width / 2, height / 2
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                max_dist = math.sqrt(cx ** 2 + cy ** 2)
                ratio = dist / max_dist
            else:
                ratio = y / height
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            pixels[x, y] = (r, g, b)
    return img


def _draw_decorative_quotes(draw, x, y, size, color, alpha=60):
    """装飾的な引用符を描画"""
    if FONT_PATH:
        try:
            font_deco = ImageFont.truetype(FONT_PATH, size)
            draw.text((x, y), "\u201C", fill=color, font=font_deco)
            return
        except Exception:
            pass
    draw.text((x, y), '"', fill=color)


def _draw_accent_elements(draw, scheme, width, height):
    """装飾要素を描画"""
    accent = scheme["accent"]

    # 上部アクセントライン
    draw.rectangle([(0, 0), (width, 3)], fill=accent)
    # 下部アクセントライン
    draw.rectangle([(0, height - 3), (width, height)], fill=accent)

    # 左側の縦アクセントバー
    bar_x = 60
    bar_top = height // 4
    bar_bottom = height * 3 // 4
    draw.rectangle([(bar_x, bar_top), (bar_x + 3, bar_bottom)], fill=accent)


def _wrap_text(text, font, max_width, draw):
    """テキストを指定幅で折り返す"""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current_line = ""
        for char in paragraph:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > max_width:
                lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
    return lines


def generate_quote_image(quote: str, author: str, output_path: str = "quote_image.png") -> str:
    """名言を画像化する（グラデーション + 装飾付き）"""
    scheme = random.choice(COLOR_SCHEMES)

    # グラデーション方向をランダムに選択
    direction = random.choice(["diagonal", "vertical", "radial"])
    img = _create_gradient(WIDTH, HEIGHT, scheme["grad1"], scheme["grad2"], direction)
    draw = ImageDraw.Draw(img)

    # フォント設定
    if FONT_PATH:
        font_quote = ImageFont.truetype(FONT_PATH, 36)
        font_author = ImageFont.truetype(FONT_PATH, 24)
    else:
        font_quote = ImageFont.load_default()
        font_author = ImageFont.load_default()

    # 装飾要素を描画
    _draw_accent_elements(draw, scheme, WIDTH, HEIGHT)

    # 大きな引用符マーク（装飾）
    quote_mark_color = scheme["accent"] + "30"  # 半透明
    _draw_decorative_quotes(draw, 80, 50, 120, scheme["accent"])

    # 名言テキストを折り返し
    margin = 120
    max_text_width = WIDTH - margin * 2
    lines = _wrap_text(quote, font_quote, max_text_width, draw)

    # テキスト全体の高さを計算
    line_height = 52
    total_text_height = len(lines) * line_height + 70  # +70 for author

    # 中央配置の開始Y座標
    start_y = (HEIGHT - total_text_height) // 2

    # 名言を描画（影付き）
    y = start_y
    for line in lines:
        if line == "":
            y += line_height // 2
            continue
        bbox = draw.textbbox((0, 0), line, font=font_quote)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        # テキストシャドウ
        draw.text((x + 2, y + 2), line, fill="#00000080", font=font_quote)
        # メインテキスト
        draw.text((x, y), line, fill=scheme["text"], font=font_quote)
        y += line_height

    # 区切り線
    sep_y = y + 10
    sep_width = 60
    sep_x = (WIDTH - sep_width) // 2
    draw.rectangle([(sep_x, sep_y), (sep_x + sep_width, sep_y + 2)], fill=scheme["accent"])

    # 著者名を描画
    y = sep_y + 18
    author_text = f"\u2015 {author}"
    bbox = draw.textbbox((0, 0), author_text, font=font_author)
    author_width = bbox[2] - bbox[0]
    draw.text(((WIDTH - author_width) // 2, y), author_text, fill=scheme["sub"], font=font_author)

    # 保存
    img.save(output_path, quality=95)
    return output_path


if __name__ == "__main__":
    # テスト: 3枚生成して確認
    quotes = [
        ("私は失敗していない。うまくいかない方法を1万通り見つけただけだ", "トーマス・エジソン"),
        ("夢を見ることができれば、それは実現できる", "ウォルト・ディズニー"),
        ("人生は自転車に乗るようなもの。倒れないためには走り続けなければならない", "アインシュタイン"),
    ]
    for i, (q, a) in enumerate(quotes):
        path = generate_quote_image(q, a, f"quote_test_{i+1}.png")
        print(f"画像を生成しました: {path}")
