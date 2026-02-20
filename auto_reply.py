"""人気投稿にAIで自動リプライするモジュール（フォロワー増加施策）"""

import os
import re
import json
import time
import random
import pickle
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    import google.generativeai as genai
except ImportError:
    genai = None

COOKIE_FILE = os.path.join(os.path.dirname(__file__), "x_cookies.pkl")
REPLY_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "reply_history.json")

# リプライ対象の検索クエリ（人気投稿を探す）
REPLY_QUERIES = [
    "名言 min_faves:100",
    "成功 マインド min_faves:50",
    "モチベーション min_faves:100",
    "お金持ち 思考 min_faves:50",
    "自己啓発 min_faves:100",
    "努力 min_faves:200",
    "挑戦 min_faves:100",
]

REPLY_PROMPT = """あなたはXで影響力のある名言・成功系アカウントのコメント担当です。
以下の投稿に対して、自然で価値のある短いリプライを生成してください。

【元の投稿】
{post_text}

【ルール】
- 30〜80文字以内
- 共感・同意・補足のどれか1つのスタイルで書く
- 自分の意見や経験を少し加える
- 会話が続くような終わり方にする（質問形式も可）
- ハッシュタグなし・絵文字なし
- 宣伝や誘導は絶対NG
- 自然な日本語で、人間が書いたように見せる

リプライ文のみ出力してください。他の文章は不要です。
"""


def _create_driver(headless=True):
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


def _load_reply_history() -> set:
    """今日リプライ済みの投稿URLセットを返す"""
    if not os.path.exists(REPLY_HISTORY_FILE):
        return set()
    try:
        with open(REPLY_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        today = datetime.date.today().isoformat()
        return set(data.get(today, []))
    except Exception:
        return set()


def _save_reply_history(urls: list):
    """リプライ済みURLを記録"""
    today = datetime.date.today().isoformat()
    data = {}
    if os.path.exists(REPLY_HISTORY_FILE):
        try:
            with open(REPLY_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    existing = set(data.get(today, []))
    existing.update(urls)
    data[today] = list(existing)
    # 3日以上前のデータを削除
    cutoff = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    data = {k: v for k, v in data.items() if k >= cutoff}
    with open(REPLY_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _generate_reply(post_text: str) -> str:
    """Gemini AIでリプライを生成"""
    if genai is None:
        raise ImportError("google-generativeai がインストールされていません")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = REPLY_PROMPT.format(post_text=post_text[:200])
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=1.0, max_output_tokens=150),
    )
    reply = response.text.strip()
    # ハッシュタグを念のため除去
    reply = re.sub(r"#\S+", "", reply).strip()
    return reply[:100]


def scrape_target_posts(driver, query: str, max_posts=10) -> list:
    """リプライ対象の人気投稿を取得"""
    import urllib.parse
    encoded = urllib.parse.quote(query)
    url = f"https://x.com/search?q={encoded}&src=typed_query&f=top"
    driver.get(url)
    time.sleep(random.uniform(5, 8))

    if "/login" in driver.current_url or "/i/flow" in driver.current_url:
        print("[WARN] ログインが必要です")
        return []

    already_replied = _load_reply_history()
    posts = []
    scroll_count = 0

    while len(posts) < max_posts and scroll_count < 4:
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
        for tweet_el in tweet_elements:
            try:
                # テキスト取得
                text_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                text = text_el.text.strip()
                if not text or len(text) < 20:
                    continue

                # ツイートURL取得（重複チェック用）
                tweet_url = ""
                try:
                    time_el = tweet_el.find_element(By.CSS_SELECTOR, "time")
                    link_el = time_el.find_element(By.XPATH, "..")
                    tweet_url = link_el.get_attribute("href") or ""
                except Exception:
                    pass

                if tweet_url in already_replied:
                    continue
                if any(p["url"] == tweet_url for p in posts):
                    continue

                posts.append({"text": text, "url": tweet_url, "element": tweet_el})

                if len(posts) >= max_posts:
                    break

            except Exception:
                continue

        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(random.uniform(2, 4))
        scroll_count += 1

    print(f"[INFO] リプライ対象を {len(posts)} 件取得")
    return posts


def post_reply(driver, tweet_url: str, reply_text: str) -> bool:
    """指定ツイートにリプライを投稿"""
    try:
        driver.get(tweet_url)
        time.sleep(random.uniform(4, 6))

        # リプライボックスをクリック
        reply_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(reply_box).pause(random.uniform(0.3, 0.8)).click().perform()
        time.sleep(random.uniform(0.5, 1.0))

        # テキストをJavaScriptで入力
        reply_box = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
        driver.execute_script("""
            var el = arguments[0];
            el.focus();
            var text = arguments[1];
            var dt = new DataTransfer();
            dt.setData('text/plain', text);
            var event = new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true});
            el.dispatchEvent(event);
        """, reply_box, reply_text)
        time.sleep(random.uniform(1.5, 2.5))

        # Ctrl+Enterで投稿
        reply_box = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
        reply_box.send_keys(Keys.CONTROL, Keys.ENTER)
        time.sleep(4)

        print(f"[OK] リプライ投稿成功: {tweet_url[:60]}")
        return True

    except Exception as e:
        # ボタンクリックで再試行
        try:
            btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetButtonInline"]')
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(4)
            print(f"[OK] リプライ投稿成功（ボタン）: {tweet_url[:60]}")
            return True
        except Exception:
            pass
        print(f"[ERROR] リプライ失敗: {e}")
        return False


def run_auto_reply(replies_per_run=3):
    """メイン処理: 人気投稿を探してAIリプライを投稿"""
    driver = None
    replied_urls = []

    try:
        is_ci = bool(os.getenv("CI"))
        driver = _create_driver(headless=is_ci or True)

        if not _load_cookies(driver):
            print("[ERROR] Cookie読み込み失敗")
            return

        driver.get("https://x.com/home")
        time.sleep(3)
        if "/login" in driver.current_url or "/i/flow" in driver.current_url:
            print("[ERROR] ログインが必要です（Cookieが無効）")
            return

        print("[OK] ログイン確認")

        # ランダムなクエリで投稿を取得
        query = random.choice(REPLY_QUERIES)
        print(f"[INFO] 検索クエリ: {query}")
        target_posts = scrape_target_posts(driver, query, max_posts=10)

        if not target_posts:
            print("[WARN] リプライ対象が見つかりませんでした")
            return

        # ランダムに選択
        selected = random.sample(target_posts, min(replies_per_run, len(target_posts)))

        for post in selected:
            try:
                # AIでリプライを生成
                reply_text = _generate_reply(post["text"])
                print(f"[INFO] 生成リプライ: {reply_text}")

                if post["url"]:
                    success = post_reply(driver, post["url"], reply_text)
                    if success:
                        replied_urls.append(post["url"])
                        # 人間らしい間隔
                        time.sleep(random.uniform(30, 60))

            except Exception as e:
                print(f"[WARN] リプライ処理エラー: {e}")
                continue

        print(f"[OK] {len(replied_urls)} 件のリプライが完了しました")

    except Exception as e:
        print(f"[ERROR] 自動リプライエラー: {e}")
    finally:
        if driver:
            driver.quit()
        if replied_urls:
            _save_reply_history(replied_urls)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_auto_reply()
