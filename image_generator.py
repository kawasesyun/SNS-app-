"""名言を画像化するモジュール（高品質版 + 人物写真付き）"""

import os
import random
import math
import urllib.request
import urllib.parse
import json
import io
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


def _fetch_luxury_background() -> Image.Image | None:
    """Wikimedia Commonsからリッチな背景写真を取得"""
    # 成功・富をイメージさせる検索キーワード
    LUXURY_QUERIES = [
        "Lamborghini Aventador",
        "Ferrari 488",
        "Rolls-Royce Phantom",
        "Porsche 911 GT3",
        "McLaren 720S",
        "Bugatti Chiron",
        "Dubai Marina skyline",
        "Manhattan skyline night",
        "Tokyo skyline night",
        "Singapore Marina Bay",
        "luxury penthouse interior",
        "private jet interior",
        "luxury yacht",
        "Rolex watch",
        "Monaco harbour",
        "Beverly Hills mansion",
        "Swiss watch collection",
        "gold bars",
        "Wall Street",
        "Shanghai skyline",
    ]

    query = random.choice(LUXURY_QUERIES)

    try:
        # Wikimedia Commons APIで画像検索
        encoded = urllib.parse.quote(query)
        api_url = (
            f"https://commons.wikimedia.org/w/api.php?"
            f"action=query&generator=search&gsrsearch={encoded}"
            f"&gsrnamespace=6&gsrlimit=5&prop=imageinfo"
            f"&iiprop=url|size&iiurlwidth=1200&format=json"
        )
        req = urllib.request.Request(api_url, headers={
            "User-Agent": "QuoteBot/1.0 (educational project)"
        })
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        # ランダムに1つ選ぶ
        page_list = list(pages.values())
        random.shuffle(page_list)

        for page in page_list:
            imageinfo = page.get("imageinfo", [{}])[0]
            thumb_url = imageinfo.get("thumburl") or imageinfo.get("url")
            if not thumb_url:
                continue

            try:
                img_req = urllib.request.Request(thumb_url, headers={
                    "User-Agent": "QuoteBot/1.0 (educational project)"
                })
                img_resp = urllib.request.urlopen(img_req, timeout=15)
                img_data = img_resp.read()
                bg_img = Image.open(io.BytesIO(img_data))
                print(f"[OK] 背景画像を取得: {query}")
                return bg_img
            except Exception:
                continue

    except Exception as e:
        print(f"[WARN] 背景画像取得失敗 ({query}): {e}")

    return None


def _prepare_background_photo(bg_img, width, height):
    """背景写真をリサイズしてダーク加工"""
    # アスペクト比を維持してリサイズ＆クロップ
    img_ratio = bg_img.width / bg_img.height
    target_ratio = width / height

    if img_ratio > target_ratio:
        new_height = height
        new_width = int(height * img_ratio)
    else:
        new_width = width
        new_height = int(width / img_ratio)

    bg_img = bg_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 中央クロップ
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    bg_img = bg_img.crop((left, top, left + width, top + height))

    # ダークオーバーレイ（テキストが読みやすいように暗くする）
    bg_img = bg_img.convert("RGB")
    dark_overlay = Image.new("RGB", (width, height), (0, 0, 0))
    bg_img = Image.blend(bg_img, dark_overlay, alpha=0.55)

    return bg_img


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
    """名言を高品質画像化する（リッチ背景写真付き）"""
    scheme = random.choice(COLOR_SCHEMES)

    # 背景写真を取得（スーパーカー、タワマン、豪邸など）
    bg_photo = None
    try:
        bg_photo = _fetch_luxury_background()
    except Exception as e:
        print(f"[WARN] 背景写真取得失敗: {e}")

    # 1. 背景を作成
    if bg_photo:
        # リッチ写真を背景に使用（ダーク加工済み）
        img = _prepare_background_photo(bg_photo, WIDTH, HEIGHT)
        # 写真背景の上にビネットを追加
        img = _add_vignette(img)
        has_photo_bg = True
    else:
        # フォールバック: グラデーション背景
        img = _create_gradient(WIDTH, HEIGHT, scheme["grad1"], scheme["grad2"])
        img = _add_vignette(img)
        img = _add_light_bokeh(img, scheme["glow"], count=random.randint(4, 7))
        has_photo_bg = False

    # 2. ノイズテクスチャ（写真背景は軽め）
    img = _add_noise_texture(img, intensity=4 if has_photo_bg else 6)

    # フォント設定（大きめ・インパクト重視）
    if FONT_PATH:
        font_quote = ImageFont.truetype(FONT_PATH, 46)
        font_author = ImageFont.truetype(FONT_PATH, 26)
        font_deco = ImageFont.truetype(FONT_PATH, 140)
        font_brand = ImageFont.truetype(FONT_PATH, 18)
    else:
        font_quote = ImageFont.load_default()
        font_author = ImageFont.load_default()
        font_deco = font_quote
        font_brand = font_quote

    # テキスト折り返し計算
    temp_draw = ImageDraw.Draw(img)
    card_margin = 70
    text_margin = 55
    max_text_width = WIDTH - (card_margin + text_margin) * 2
    lines = _wrap_text(quote, font_quote, max_text_width, temp_draw)

    # テキスト高さ計算
    line_height = 65
    quote_height = len(lines) * line_height
    author_height = 55
    deco_height = 35
    total_content_height = quote_height + deco_height + author_height

    # 3. ガラスカード（写真背景は濃く・グラデーション感）
    card_padding = 50
    card_x1 = card_margin
    card_y1 = (HEIGHT - total_content_height) // 2 - card_padding
    card_x2 = WIDTH - card_margin
    card_y2 = (HEIGHT + total_content_height) // 2 + card_padding
    card_y1 = max(20, card_y1)
    card_y2 = min(HEIGHT - 20, card_y2)
    card_opacity = 80 if has_photo_bg else 55
    img = _draw_glass_card(img, card_x1, card_y1, card_x2, card_y2, opacity=card_opacity)

    # カード左端にゴールドの縦ライン
    overlay2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d2 = ImageDraw.Draw(overlay2)
    d2.rectangle([(card_x1, card_y1 + 10), (card_x1 + 4, card_y2 - 10)], fill=(212, 175, 55, 180))
    img_rgba = img.convert("RGBA")
    img = Image.alpha_composite(img_rgba, overlay2).convert("RGB")

    draw = ImageDraw.Draw(img)

    # 4. 装飾的な引用符（薄く大きく）
    try:
        quote_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        qd = ImageDraw.Draw(quote_overlay)
        qd.text((card_x1 + 20, card_y1 - 20), "\u201C", fill=(212, 175, 55, 40), font=font_deco)
        img_rgba = img.convert("RGBA")
        img = Image.alpha_composite(img_rgba, quote_overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
    except Exception:
        pass

    # 5. 名言テキスト描画（強いシャドウ + 白テキスト）
    start_y = (HEIGHT - total_content_height) // 2
    y = start_y
    for line in lines:
        if line == "":
            y += line_height // 2
            continue
        bbox = draw.textbbox((0, 0), line, font=font_quote)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        # 多重シャドウでインパクトを出す
        for dx, dy in [(3, 3), (2, 2), (1, 1)]:
            draw.text((x + dx, y + dy), line, fill=(0, 0, 0, 200), font=font_quote)
        draw.text((x, y), line, fill="#ffffff", font=font_quote)
        y += line_height

    # 6. アクセント区切り線（ゴールド・幅広）
    sep_y = y + 12
    sep_width = 80
    sep_x = (WIDTH - sep_width) // 2
    draw.rounded_rectangle(
        [(sep_x, sep_y), (sep_x + sep_width, sep_y + 3)],
        radius=2,
        fill="#d4af37",
    )

    # 7. 著者名（ゴールド）
    y = sep_y + 25
    if author:
        author_text = f"\u2015 {author}"
    else:
        author_text = ""
    if author_text:
        bbox = draw.textbbox((0, 0), author_text, font=font_author)
        author_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - author_width) // 2 + 1, y + 1), author_text, fill="#000000", font=font_author)
        draw.text(((WIDTH - author_width) // 2, y), author_text, fill="#d4af37", font=font_author)

    # 8. 上下のゴールドアクセントライン（太め）
    draw.rectangle([(0, 0), (WIDTH, 4)], fill="#d4af37")
    draw.rectangle([(0, HEIGHT - 4), (WIDTH, HEIGHT)], fill="#d4af37")

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
