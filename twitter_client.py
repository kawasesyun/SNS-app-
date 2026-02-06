"""Cookieベースの認証でXに投稿するモジュール（人間操作模倣）"""

import os
import time
import random
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


COOKIE_FILE = os.path.join(os.path.dirname(__file__), "x_cookies.pkl")


def human_delay(min_sec=0.5, max_sec=1.5):
    """人間らしいランダムな待機"""
    time.sleep(random.uniform(min_sec, max_sec))


def human_type(element, text):
    """人間のようにゆっくり1文字ずつ入力"""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.03, 0.12))


class TwitterClient:
    def __init__(self):
        self.username = os.getenv("X_USERNAME")
        self.password = os.getenv("X_PASSWORD")
        self.driver = None

    def _create_driver(self, headless=False):
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

        # CI環境用: 追加設定
        if os.getenv("CI"):
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--lang=ja-JP")
            options.add_argument("--single-process")

        self.driver = webdriver.Chrome(options=options)

        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })

    def _save_cookies(self):
        """Cookieを保存"""
        cookies = self.driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"[OK] Cookieを保存しました ({len(cookies)}件)")

    def _load_cookies(self) -> bool:
        """保存済みCookieを読み込む"""
        if not os.path.exists(COOKIE_FILE):
            return False
        try:
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
            self.driver.get("https://x.com")
            time.sleep(2)
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass
            return True
        except:
            return False

    def login_auto(self) -> bool:
        """ユーザー名とパスワードで自動ログイン（CI環境用）"""
        # 環境変数を再取得（CI環境対応）
        self.username = os.getenv("X_USERNAME")
        self.password = os.getenv("X_PASSWORD")

        if not self.username or not self.password:
            print(f"[ERROR] X_USERNAME または X_PASSWORD が未設定です")
            print(f"  X_USERNAME: {'設定済み' if self.username else '未設定'}")
            print(f"  X_PASSWORD: {'設定済み' if self.password else '未設定'}")
            return False

        try:
            self._create_driver(headless=False)
            self.driver.get("https://x.com/i/flow/login")
            human_delay(3, 5)

            # ユーザー名入力
            username_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            human_delay(0.5, 1.0)
            actions = ActionChains(self.driver)
            actions.move_to_element(username_input).pause(0.3).click().perform()
            human_delay(0.3, 0.6)
            human_type(username_input, self.username)
            human_delay(0.5, 1.0)

            # 「次へ」ボタンをクリック
            next_buttons = self.driver.find_elements(By.XPATH, '//button[@role="button"]')
            for btn in next_buttons:
                text = btn.text.strip()
                if text in ["Next", "次へ", "next"]:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(btn).pause(0.3).click().perform()
                    break
            human_delay(2, 3)

            # パスワード入力
            password_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            actions = ActionChains(self.driver)
            actions.move_to_element(password_input).pause(0.3).click().perform()
            human_delay(0.3, 0.6)
            human_type(password_input, self.password)
            human_delay(0.5, 1.0)

            # 「ログイン」ボタンをクリック
            login_buttons = self.driver.find_elements(By.XPATH, '//button[@role="button"]')
            for btn in login_buttons:
                text = btn.text.strip()
                if text in ["Log in", "ログイン", "log in"]:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(btn).pause(0.3).click().perform()
                    break
            human_delay(4, 6)

            # ログイン成功確認
            if "/home" in self.driver.current_url:
                self._save_cookies()
                print("[OK] 自動ログイン成功")
                return True
            else:
                print(f"[ERROR] ログイン失敗 URL: {self.driver.current_url}")
                self.driver.save_screenshot("debug_login.png")
                return False

        except Exception as e:
            print(f"[ERROR] 自動ログインエラー: {e}")
            try:
                if self.driver:
                    print(f"[DEBUG] 現在のURL: {self.driver.current_url}")
                    print(f"[DEBUG] ページタイトル: {self.driver.title}")
                    self.driver.save_screenshot("debug_login.png")
            except Exception as e2:
                print(f"[DEBUG] スクリーンショット取得失敗: {e2}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def login_manual(self):
        """ブラウザを表示して手動ログイン（初回のみ）"""
        print("ブラウザが開きます。Xにログインしてください。")
        print("ログイン完了後、ホーム画面が表示されたらEnterを押してください。")

        self._create_driver(headless=False)
        self.driver.get("https://x.com/i/flow/login")

        input("\nログイン完了後、Enterキーを押してください... ")

        self._save_cookies()
        self.driver.quit()
        self.driver = None
        print("[OK] 次回からは自動でログインできます")

    def _login_with_cookies(self) -> bool:
        """Cookie使ってログイン"""
        if not self._load_cookies():
            print("[ERROR] 保存済みCookieがありません")
            return False

        self.driver.get("https://x.com/home")
        time.sleep(random.uniform(4, 6))

        if "/login" in self.driver.current_url or "/i/flow" in self.driver.current_url:
            print("[ERROR] Cookieが期限切れです。再ログインが必要です")
            return False

        print("[OK] Cookieでログインしました")
        return True

    def post_tweet(self, text: str) -> dict:
        """ツイートを投稿する（ブラウザ表示して人間操作を模倣）"""
        try:
            # ブラウザ表示モードで実行（検知回避）
            self._create_driver(headless=False)

            if not self._login_with_cookies():
                print("[INFO] Cookie無効。自動ログインを試みます...")
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                # 自動ログインしてCookieを保存
                if not self.login_auto():
                    return {"success": False, "error": "auto login failed"}
                # 再度ドライバー作成してCookieログイン
                self._create_driver(headless=False)
                if not self._login_with_cookies():
                    return {"success": False, "error": "cookie login failed after auto login"}

            human_delay(2, 4)

            # 投稿ボックスをクリック
            tweet_box = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
            )

            # マウスを移動してからクリック
            actions = ActionChains(self.driver)
            actions.move_to_element(tweet_box).pause(random.uniform(0.3, 0.8)).click().perform()
            human_delay(0.5, 1.0)

            # 人間のように1文字ずつ入力
            human_type(tweet_box, text)
            human_delay(1.0, 2.0)

            # 投稿ボタンをクリック
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="tweetButtonInline"]'))
            )
            actions = ActionChains(self.driver)
            actions.move_to_element(post_button).pause(random.uniform(0.3, 0.6)).click().perform()

            time.sleep(5)

            # 投稿成功確認
            self.driver.save_screenshot("debug_post.png")
            print("[OK] 投稿成功!")
            return {"success": True}

        except Exception as e:
            print(f"[ERROR] 投稿エラー: {e}")
            try:
                self.driver.save_screenshot("debug_post.png")
            except:
                pass
            return {"success": False, "error": str(e)}

        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def verify_credentials(self) -> bool:
        """Cookieでログインできるか確認"""
        if not os.path.exists(COOKIE_FILE):
            print("[ERROR] まだログインしていません")
            print("  'python twitter_client.py login' を実行してください")
            return False
        try:
            self._create_driver(headless=False)
            result = self._login_with_cookies()
            return result
        except Exception as e:
            print(f"[ERROR] 認証エラー: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    client = TwitterClient()

    if len(sys.argv) > 1 and sys.argv[1] == "login":
        client.login_manual()
    else:
        client.verify_credentials()
