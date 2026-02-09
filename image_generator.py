"""名言を画像化するモジュール"""

import os
import random
import textwrap
from PIL import Image, ImageDraw, ImageFont

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

# 配色パターン（背景色, テキスト色, アクセント色）
COLOR_SCHEMES = [
    {"bg": "#1a1a2e", "text": "#ffffff", "accent": "#e94560", "sub": "#cccccc"},
    {"bg": "#0f0f0f", "text": "#f5f5f5", "accent": "#f7b731", "sub": "#aaaaaa"},
    {"bg": "#1b1b3a", "text": "#ffffff", "accent": "#6fffe9", "sub": "#bbbbbb"},
    {"bg": "#2d3436", "text": "#ffffff", "accent": "#74b9ff", "sub": "#b2bec3"},
    {"bg": "#0d1b2a", "text": "#e0e1dd", "accent": "#ee6c4d", "sub": "#98c1d9"},
    {"bg": "#1a1a1a", "text": "#ffffff", "accent": "#ff6b6b", "sub": "#999999"},
]


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
    """名言を画像化する"""
    scheme = random.choice(COLOR_SCHEMES)

    img = Image.new("RGB", (WIDTH, HEIGHT), scheme["bg"])
    draw = ImageDraw.Draw(img)

    # フォント設定
    if FONT_PATH:
        font_quote = ImageFont.truetype(FONT_PATH, 36)
        font_author = ImageFont.truetype(FONT_PATH, 24)
    else:
        font_quote = ImageFont.load_default()
        font_author = ImageFont.load_default()

    # アクセントライン（上部）
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=scheme["accent"])

    # 名言テキストを折り返し
    margin = 100
    max_text_width = WIDTH - margin * 2
    lines = _wrap_text(quote, font_quote, max_text_width, draw)

    # テキスト全体の高さを計算
    line_height = 52
    total_text_height = len(lines) * line_height + 60  # +60 for author

    # 中央配置の開始Y座標
    start_y = (HEIGHT - total_text_height) // 2

    # 名言を描画
    y = start_y
    for line in lines:
        if line == "":
            y += line_height // 2
            continue
        bbox = draw.textbbox((0, 0), line, font=font_quote)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        draw.text((x, y), line, fill=scheme["text"], font=font_quote)
        y += line_height

    # 著者名を描画
    y += 20
    author_text = f"― {author}"
    bbox = draw.textbbox((0, 0), author_text, font=font_author)
    author_width = bbox[2] - bbox[0]
    draw.text(((WIDTH - author_width) // 2, y), author_text, fill=scheme["sub"], font=font_author)

    # アクセントライン（下部）
    draw.rectangle([(0, HEIGHT - 4), (WIDTH, HEIGHT)], fill=scheme["accent"])

    # 保存
    img.save(output_path, quality=95)
    return output_path


if __name__ == "__main__":
    path = generate_quote_image(
        "私は失敗していない。うまくいかない方法を1万通り見つけただけだ",
        "トーマス・エジソン"
    )
    print(f"画像を生成しました: {path}")
