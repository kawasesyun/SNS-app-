"""Xのトレンド・バズ投稿をスクレイピングして参考にするモジュール"""

import os
import re
import time
import random
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


COOKIE_FILE = os.path.join(os.path.dirname(__file__), "x_cookies.pkl")


def _create_driver(headless=True):
    """Chromeドライバーを作成"""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if os.getenv("CI"):
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        options.add_argument("--disable-extensions")
        options.add_argument("--lang=ja-JP")

    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })
    except Exception:
        pass
    return driver


def _load_cookies(driver) -> bool:
    """Cookieを読み込む"""
    if not os.path.exists(COOKIE_FILE):
        return False
    try:
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
        driver.get("https://x.com")
        time.sleep(2)
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        return True
    except Exception:
        return False


def scrape_trending_posts(search_query="名言 min_faves:100", max_posts=10):
    """Xでバズっている投稿をスクレイピング

    Args:
        search_query: 検索クエリ（min_faves でいいね数フィルタ）
        max_posts: 取得する最大投稿数

    Returns:
        list[dict]: バズ投稿のリスト [{text, likes, author}, ...]
    """
    driver = None
    try:
        is_ci = bool(os.getenv("CI"))
        driver = _create_driver(headless=is_ci or True)

        # Cookieでログイン
        if not _load_cookies(driver):
            print("[WARN] トレンドスクレイピング: Cookie読み込み失敗")
            return []

        # 検索ページにアクセス（人気順）
        import urllib.parse
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=top"
        driver.get(url)
        time.sleep(random.uniform(5, 8))

        # ログイン確認
        if "/login" in driver.current_url or "/i/flow" in driver.current_url:
            print("[WARN] トレンドスクレイピング: ログインが必要です")
            return []

        print(f"[INFO] 検索ページにアクセス: {search_query}")

        # 投稿を取得
        posts = []
        scroll_count = 0
        max_scrolls = 3

        while len(posts) < max_posts and scroll_count < max_scrolls:
            # ツイート要素を取得
            tweet_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')

            for tweet_el in tweet_elements:
                try:
                    # テキスト取得
                    text_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                    text = text_el.text.strip()

                    if not text or len(text) < 20:
                        continue

                    # 重複チェック
                    if any(p["text"] == text for p in posts):
                        continue

                    # ユーザー名取得
                    author = ""
                    try:
                        user_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]')
                        author = user_el.text.split("\n")[0] if user_el.text else ""
                    except Exception:
                        pass

                    # いいね数取得
                    likes = 0
                    try:
                        like_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="like"] span')
                        like_text = like_el.text.strip()
                        if like_text:
                            like_text = like_text.replace(",", "").replace(".", "")
                            if "万" in like_text:
                                likes = int(float(like_text.replace("万", "")) * 10000)
                            elif "K" in like_text.upper():
                                likes = int(float(like_text.upper().replace("K", "")) * 1000)
                            else:
                                likes = int(like_text) if like_text.isdigit() else 0
                    except Exception:
                        pass

                    posts.append({
                        "text": text,
                        "author": author,
                        "likes": likes,
                    })

                    if len(posts) >= max_posts:
                        break

                except Exception:
                    continue

            # スクロール
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(random.uniform(2, 4))
            scroll_count += 1

        # いいね数でソート
        posts.sort(key=lambda x: x["likes"], reverse=True)
        print(f"[OK] バズ投稿を {len(posts)} 件取得しました")
        return posts

    except Exception as e:
        print(f"[WARN] トレンドスクレイピング失敗: {e}")
        return []
    finally:
        if driver:
            driver.quit()


# 検索クエリのバリエーション（ランダムに選ぶ）
TREND_QUERIES = [
    "名言 min_faves:100",
    "格言 min_faves:100",
    "人生 大切 min_faves:200",
    "心に刺さる min_faves:100",
    "モチベーション min_faves:100",
    "努力 報われる min_faves:50",
    "成功 秘訣 min_faves:50",
    "自分を変える min_faves:50",
    "挑戦 min_faves:100",
    "名言 偉人 min_faves:50",
]


def get_buzz_post_for_reference():
    """バズ投稿を1件取得して参考用テキストを返す

    Returns:
        dict or None: {original_text, formatted_post, image_quote, image_author}
    """
    query = random.choice(TREND_QUERIES)
    posts = scrape_trending_posts(search_query=query, max_posts=5)

    if not posts:
        print("[WARN] バズ投稿を取得できませんでした")
        return None

    # ランダムに1件選ぶ（上位から）
    post = random.choice(posts[:3]) if len(posts) >= 3 else posts[0]
    original = post["text"]
    print(f"[INFO] 参考バズ投稿（いいね{post['likes']}）: {original[:50]}...")

    # バズ投稿のスタイルを真似た投稿を生成
    formatted = _remix_buzz_post(original)
    if not formatted:
        return None

    return formatted


def _remix_buzz_post(original_text: str):
    """バズ投稿のスタイルを参考にして、オリジナルの投稿を生成する

    パクリではなく、構造・スタイルを真似て新しい内容を作る
    """
    # 投稿の構造を分析
    lines = [l.strip() for l in original_text.split("\n") if l.strip()]

    # ハッシュタグを抽出
    hashtags = re.findall(r"#\S+", original_text)
    # 本文からハッシュタグを除去
    clean_text = re.sub(r"#\S+", "", original_text).strip()
    clean_lines = [l.strip() for l in clean_text.split("\n") if l.strip()]

    if not clean_lines:
        return None

    # パターン分析してリミックス
    result = _create_inspired_post(clean_lines, hashtags)
    return result


# リミックス用の名言・教訓テンプレート
REMIX_TEMPLATES = [
    # パターン1: 対比型
    [
        "{hook}",
        "",
        "{point1}",
        "でも{point2}",
        "",
        "{conclusion}",
    ],
    # パターン2: リスト型
    [
        "{hook}",
        "",
        "①{point1}",
        "②{point2}",
        "③{point3}",
        "",
        "{conclusion}",
    ],
    # パターン3: ストーリー型
    [
        "{hook}",
        "",
        "{point1}",
        "",
        "{point2}",
        "",
        "{conclusion}",
    ],
    # パターン4: シンプル強調型
    [
        "{hook}",
        "",
        "{point1}",
        "",
        "{conclusion}",
    ],
]

# リミックス用の素材
REMIX_HOOKS = [
    "成功する人と失敗する人の違い。",
    "これに気づいた人から人生変わる。",
    "30歳になって分かったこと。",
    "誰も教えてくれなかった真実。",
    "伸びる人の共通点。",
    "結果を出す人の考え方。",
    "人生で大切なことは3つだけ。",
    "今すぐやめるべき習慣。",
    "トップ1%がやっていること。",
    "知らないと損する考え方。",
    "メンタルが強い人の特徴。",
    "幸せな人がやっていること。",
]

REMIX_POINTS = [
    ("努力の方向を間違えない", "量より質が大事", "正しい方向に進めば必ず結果が出る"),
    ("行動しない人は永遠に変わらない", "小さな一歩でもいいから踏み出す", "続けた人だけが見える景色がある"),
    ("他人と比べない", "昨日の自分と比べる", "その小さな成長が未来を変える"),
    ("失敗を恐れない", "失敗は最高の学び", "何もしないことが一番の失敗"),
    ("環境を変える勇気を持つ", "付き合う人で人生が変わる", "居心地の悪い場所にこそ成長がある"),
    ("完璧を求めすぎない", "まず60点でいいから出す", "走りながら修正すればいい"),
    ("インプットよりアウトプット", "知識は使わないと意味がない", "行動こそが最大の学び"),
    ("睡眠を削らない", "健康が全ての土台", "体が資本。これだけは忘れちゃいけない"),
    ("感謝を忘れない", "当たり前は当たり前じゃない", "感謝できる人の周りに人が集まる"),
    ("素直に聞く力", "プライドが成長を止める", "教えてもらえるうちが花"),
    ("時間は有限", "今この瞬間が一番若い", "いつかやるは一生やらない"),
    ("継続こそ最強のスキル", "才能より続ける力", "毎日1%の成長で1年後には37倍"),
]

REMIX_CONCLUSIONS = [
    "これを知ってるだけで人生の質が変わる。",
    "気づいた今日から変わればいい。",
    "シンプルだけど、これが全て。",
    "今日から意識してみてほしい。",
    "この事実を忘れないでいたい。",
    "あなたはもう気づいてるはず。",
    "過去は変えられない。でも未来は変えられる。",
    "やるかやらないか。それだけ。",
]

REMIX_HASHTAGS = [
    "#人生", "#成長", "#モチベーション", "#自己啓発",
    "#努力", "#挑戦", "#名言", "#マインドセット",
    "#習慣", "#行動", "#成功", "#考え方",
]


def _create_inspired_post(reference_lines, reference_hashtags):
    """参考投稿のスタイルに触発されたオリジナル投稿を生成"""
    # テンプレートを選択
    template = random.choice(REMIX_TEMPLATES)

    # 素材を選択
    hook = random.choice(REMIX_HOOKS)
    points = random.choice(REMIX_POINTS)
    conclusion = random.choice(REMIX_CONCLUSIONS)

    # ハッシュタグ（参考投稿のものも一部使う）
    all_tags = list(set(reference_hashtags + REMIX_HASHTAGS))
    tags = random.sample(all_tags, min(3, len(all_tags)))
    tag_line = " ".join(tags)

    # テンプレートを埋める
    post_lines = []
    for line in template:
        filled = line.format(
            hook=hook,
            point1=points[0],
            point2=points[1],
            point3=points[2] if len(points) > 2 else points[1],
            conclusion=conclusion,
        )
        post_lines.append(filled)

    post_lines.append("")
    post_lines.append(tag_line)

    post_text = "\n".join(post_lines)

    # 画像用の情報も返す
    return {
        "post_text": post_text,
        "image_quote": points[0] + "。" + points[1] + "。",
        "image_author": "",  # オリジナルなので著者なし
        "is_trend": True,
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=== バズ投稿スクレイピングテスト ===")
    result = get_buzz_post_for_reference()
    if result:
        print(f"\n--- 生成された投稿 ---")
        print(result["post_text"])
        print(f"\n--- 画像用テキスト ---")
        print(f"Quote: {result['image_quote']}")
    else:
        print("バズ投稿の取得に失敗しました")
