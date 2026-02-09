"""名言を画像化するモジュール（高品質版）"""

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

# 配色パターン
COLOR_SCHEMES = [
    {"grad1": (15, 15, 35), "grad2": (35, 55, 90), "text": "#ffffff", "sub": "#b0c4de", "accent": "#64b5f6", "glow": (100, 181, 246)},
    {"grad1": (20, 10, 30), "grad2": (60, 25, 50), "text": "#ffffff", "sub": "#d4a0c0", "accent": "#ff79c6", "glow": (255, 121, 198)},
    {"grad1": (10, 20, 25), "grad2": (20, 60, 55), "text": "#e0fff0", "sub": "#80cbc4", "accent": "#4dd0e1", "glow": (77, 208, 225)},
    {"grad1": (25, 15, 10), "grad2": (60, 35, 20), "text": "#fff3e0", "sub": "#ffb74d", "accent": "#ffa726", "glow": (255, 167, 38)},
    {"grad1": (15, 15, 25), "grad2": (45, 30, 60), "text": "#f3e5f5", "sub": "#ce93d8", "accent": "#ab47bc", "glow": (171, 71, 188)},
    {"grad1": (10, 15, 20), "grad2": (30, 45, 55), "text": "#e0f7fa", "sub": "#80deea", "accent": "#26c6da", "glow": (38, 198, 218)},
    {"grad1": (20, 12, 12), "grad2": (55, 25, 30), "text": "#ffebee", "sub": "#ef9a9a", "accent": "#ef5350", "glow": (239, 83, 80)},
    {"grad1": (12, 18, 12), "grad2": (30, 55, 35), "text": "#e8f5e9", "sub": "#a5d6a7", "accent": "#66bb6a", "glow": (102, 187, 106)},
]


def _create_gradient(width, height, color1, color2):
    """滑らかなグラデーション背景"""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            # 対角線グラデーション + 微妙なカーブ
            ratio = (x / width * 0.6 + y / height * 0.4)
            ratio = ratio ** 0.9  # 非線形で自然なグラデーション
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            pixels[x, y] = (r, g, b)
    return img


def _add_vignette(img):
    """ビネット効果（四隅を暗く）"""
    width, height = img.size
    vignette = Image.new("L", (width, height), 0)
    pixels = vignette.load()
    cx, cy = width / 2, height / 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            ratio = dist / max_dist
            # 中央は明るく、端は暗く
            brightness = int(255 * (1.0 - ratio * ratio * 0.6))
            pixels[x, y] = max(0, min(255, brightness))
    # ビネットを適用
    result = Image.new("RGB", (width, height))
    img_pixels = img.load()
    vig_pixels = vignette.load()
    res_pixels = result.load()
    for y in range(height):
        for x in range(width):
            r, g, b = img_pixels[x, y]
            v = vig_pixels[x, y] / 255.0
            res_pixels[x, y] = (int(r * v), int(g * v), int(b * v))
    return result


def _add_light_bokeh(img, glow_color, count=5):
    """光のボケ効果"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img.size
    for _ in range(count):
        x = random.randint(0, width)
        y = random.randint(0, height)
        radius = random.randint(30, 120)
        alpha = random.randint(8, 25)
        r, g, b = glow_color
        # 複数の円を重ねてソフトなボケ感
        for i in range(radius, 0, -3):
            a = int(alpha * (i / radius) ** 0.5)
            draw.ellipse(
                [(x - i, y - i), (x + i, y + i)],
                fill=(r, g, b, a)
            )
    # RGBに変換して合成
    img_rgba = img.convert("RGBA")
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert("RGB")


def _add_noise_texture(img, intensity=8):
    """微細なノイズテクスチャ"""
    width, height = img.size
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            noise = random.randint(-intensity, intensity)
            pixels[x, y] = (
                max(0, min(255, r + noise)),
                max(0, min(255, g + noise)),
                max(0, min(255, b + noise)),
            )
    return img


def _draw_glass_card(img, x1, y1, x2, y2, opacity=40):
    """半透明のガラスカード効果"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # カード本体（半透明の黒）
    draw.rounded_rectangle(
        [(x1, y1), (x2, y2)],
        radius=20,
        fill=(0, 0, 0, opacity),
    )
    # カード上部のハイライトライン
    draw.rounded_rectangle(
        [(x1, y1), (x2, y1 + 2)],
        radius=1,
        fill=(255, 255, 255, 15),
    )
    img_rgba = img.convert("RGBA")
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert("RGB")


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
    """名言を高品質画像化する"""
    scheme = random.choice(COLOR_SCHEMES)

    # 1. グラデーション背景
    img = _create_gradient(WIDTH, HEIGHT, scheme["grad1"], scheme["grad2"])

    # 2. ビネット効果
    img = _add_vignette(img)

    # 3. 光のボケ効果
    img = _add_light_bokeh(img, scheme["glow"], count=random.randint(4, 7))

    # 4. ノイズテクスチャ
    img = _add_noise_texture(img, intensity=6)

    # フォント設定
    if FONT_PATH:
        font_quote = ImageFont.truetype(FONT_PATH, 40)
        font_author = ImageFont.truetype(FONT_PATH, 22)
        font_deco = ImageFont.truetype(FONT_PATH, 140)
    else:
        font_quote = ImageFont.load_default()
        font_author = ImageFont.load_default()
        font_deco = font_quote

    # テキスト折り返し計算（カード内に収める）
    temp_draw = ImageDraw.Draw(img)
    card_margin = 80
    text_margin = 50
    max_text_width = WIDTH - (card_margin + text_margin) * 2
    lines = _wrap_text(quote, font_quote, max_text_width, temp_draw)

    # テキスト高さ計算
    line_height = 58
    quote_height = len(lines) * line_height
    author_height = 50
    deco_height = 30
    total_content_height = quote_height + deco_height + author_height

    # 5. ガラスカード
    card_padding = 45
    card_x1 = card_margin
    card_y1 = (HEIGHT - total_content_height) // 2 - card_padding
    card_x2 = WIDTH - card_margin
    card_y2 = (HEIGHT + total_content_height) // 2 + card_padding
    img = _draw_glass_card(img, card_x1, card_y1, card_x2, card_y2, opacity=50)

    draw = ImageDraw.Draw(img)

    # 6. 装飾的な引用符（カード左上、大きく薄く）
    try:
        # 半透明の引用符をオーバーレイ
        quote_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        qd = ImageDraw.Draw(quote_overlay)
        r, g, b = scheme["glow"]
        qd.text((card_x1 + 15, card_y1 - 30), "\u201C", fill=(r, g, b, 45), font=font_deco)
        img_rgba = img.convert("RGBA")
        img = Image.alpha_composite(img_rgba, quote_overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
    except Exception:
        pass

    # 7. 名言テキスト描画
    start_y = (HEIGHT - total_content_height) // 2
    y = start_y
    for line in lines:
        if line == "":
            y += line_height // 2
            continue
        bbox = draw.textbbox((0, 0), line, font=font_quote)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        # テキストシャドウ（柔らかい影）
        draw.text((x + 1, y + 2), line, fill="#00000060", font=font_quote)
        # メインテキスト
        draw.text((x, y), line, fill=scheme["text"], font=font_quote)
        y += line_height

    # 8. アクセント区切り線
    sep_y = y + 8
    sep_width = 50
    sep_x = (WIDTH - sep_width) // 2
    draw.rounded_rectangle(
        [(sep_x, sep_y), (sep_x + sep_width, sep_y + 3)],
        radius=2,
        fill=scheme["accent"],
    )

    # 9. 著者名
    y = sep_y + 22
    author_text = f"\u2015 {author}"
    bbox = draw.textbbox((0, 0), author_text, font=font_author)
    author_width = bbox[2] - bbox[0]
    draw.text(((WIDTH - author_width) // 2, y), author_text, fill=scheme["sub"], font=font_author)

    # 10. 上下のアクセントライン
    draw.rectangle([(0, 0), (WIDTH, 2)], fill=scheme["accent"])
    draw.rectangle([(0, HEIGHT - 2), (WIDTH, HEIGHT)], fill=scheme["accent"])

    # 保存
    img.save(output_path, quality=95)
    return output_path


if __name__ == "__main__":
    quotes = [
        ("私は失敗していない。うまくいかない方法を1万通り見つけただけだ", "トーマス・エジソン"),
        ("夢を見ることができれば、それは実現できる", "ウォルト・ディズニー"),
        ("人生は自転車に乗るようなもの。倒れないためには走り続けなければならない", "アインシュタイン"),
    ]
    for i, (q, a) in enumerate(quotes):
        path = generate_quote_image(q, a, f"quote_test_{i+1}.png")
        print(f"画像を生成しました: {path}")
