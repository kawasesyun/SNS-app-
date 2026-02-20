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
        if char == '\n':
            element.send_keys(Keys.SHIFT, Keys.ENTER)
        else:
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
            options.add_argument("--lang=ja-JP")

        self.driver = webdriver.Chrome(options=options)

        # navigator.webdriverを隠す（CSPでブロックされる場合はスキップ）
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            })
        except Exception:
            pass

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
        """ユーザー名とパスワードで自動ログイン（CI環境用 - ヘッドレス）"""
        # 環境変数を再取得（CI環境対応）
        self.username = os.getenv("X_USERNAME")
        self.password = os.getenv("X_PASSWORD")

        if not self.username or not self.password:
            print(f"[ERROR] X_USERNAME または X_PASSWORD が未設定です")
            print(f"  X_USERNAME: {'設定済み' if self.username else '未設定'}")
            print(f"  X_PASSWORD: {'設定済み' if self.password else '未設定'}")
            return False

        try:
            self._create_driver(headless=True)
            print("[INFO] ヘッドレスモードでログイン開始...")
            self.driver.get("https://x.com/i/flow/login")
            time.sleep(5)
            print(f"[DEBUG] ページタイトル: {self.driver.title}")

            # ユーザー名入力
            username_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            print("[INFO] ユーザー名入力欄を発見")
            username_input.click()
            time.sleep(0.5)
            username_input.send_keys(self.username)
            time.sleep(1)

            # 「次へ」ボタンをクリック
            next_buttons = self.driver.find_elements(By.XPATH, '//button[@role="button"]')
            for btn in next_buttons:
                text = btn.text.strip()
                if text in ["Next", "次へ", "next"]:
                    btn.click()
                    print(f"[INFO] 「{text}」ボタンをクリック")
                    break
            time.sleep(3)

            # パスワード入力
            password_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            print("[INFO] パスワード入力欄を発見")
            password_input.click()
            time.sleep(0.5)
            password_input.send_keys(self.password)
            time.sleep(1)

            # 「ログイン」ボタンをクリック
            login_buttons = self.driver.find_elements(By.XPATH, '//button[@role="button"]')
            for btn in login_buttons:
                text = btn.text.strip()
                if text in ["Log in", "ログイン", "log in"]:
                    btn.click()
                    print(f"[INFO] 「{text}」ボタンをクリック")
                    break
            time.sleep(6)

            # ログイン成功確認
            print(f"[DEBUG] ログイン後URL: {self.driver.current_url}")
            if "/home" in self.driver.current_url:
                self._save_cookies()
                print("[OK] 自動ログイン成功")
                return True
            else:
                print(f"[ERROR] ログイン失敗 URL: {self.driver.current_url}")
                return False

        except Exception as e:
            print(f"[ERROR] 自動ログインエラー: {e}")
            try:
                if self.driver:
                    print(f"[DEBUG] 現在のURL: {self.driver.current_url}")
                    print(f"[DEBUG] ページタイトル: {self.driver.title}")
            except Exception as e2:
                print(f"[DEBUG] デバッグ情報取得失敗: {e2}")
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

    def post_tweet(self, text: str, image_path: str = None) -> dict:
        """ツイートを投稿する（ブラウザ表示して人間操作を模倣）"""
        try:
            # CI環境はヘッドレス、ローカルはブラウザ表示
            is_ci = bool(os.getenv("CI"))
            self._create_driver(headless=is_ci)

            if not self._login_with_cookies():
                print("[INFO] Cookie無効。自動ログインを試みます...")
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                # 自動ログインしてCookieを保存
                if not self.login_auto():
                    return {"success": False, "error": "auto login failed"}
                # 再度ドライバー作成してCookieログイン
                self._create_driver(headless=is_ci)
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

            # クリック後に要素を再取得（stale element対策）
            tweet_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
            )

            # 画像を添付
            if image_path and os.path.exists(image_path):
                try:
                    file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[data-testid="fileInput"]')
                    file_input.send_keys(os.path.abspath(image_path))
                    print(f"[INFO] 画像を添付: {image_path}")
                    time.sleep(3)
                except Exception as e:
                    print(f"[WARN] 画像添付失敗: {e}")

            # JavaScriptでテキストを入力（BMP外の絵文字対応）
            self.driver.execute_script("""
                var el = arguments[0];
                el.focus();
                var text = arguments[1];
                var dt = new DataTransfer();
                dt.setData('text/plain', text);
                var event = new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true});
                el.dispatchEvent(event);
            """, tweet_box, text)
            human_delay(2.0, 3.0)

            # スクリーンショット（投稿前）
            self.driver.save_screenshot("debug_before_post.png")

            # 投稿方法1: Ctrl+Enterで送信（最も確実）
            posted = False
            try:
                tweet_box_active = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
                tweet_box_active.send_keys(Keys.CONTROL, Keys.ENTER)
                print("[INFO] Ctrl+Enterで投稿を送信")
                time.sleep(5)
                posted = True
            except Exception as e1:
                print(f"[WARN] Ctrl+Enter失敗: {e1}")

            # 投稿方法2: ボタンクリック（複数セレクタを試す）
            if not posted:
                button_selectors = [
                    '[data-testid="tweetButtonInline"]',
                    '[data-testid="tweetButton"]',
                ]
                for selector in button_selectors:
                    try:
                        btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        self.driver.execute_script("arguments[0].click();", btn)
                        print(f"[INFO] ボタンクリック成功: {selector}")
                        time.sleep(5)
                        posted = True
                        break
                    except Exception:
                        continue

            self.driver.save_screenshot("debug_post.png")

            self._save_cookies()
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

    def post_thread(self, tweets: list, image_path: str = None) -> dict:
        """スレッド投稿（複数ツイートを連続リプライ形式で投稿）

        Args:
            tweets: ツイートテキストのリスト（最初が親ツイート）
            image_path: 最初のツイートに添付する画像（任意）

        Returns:
            dict: {success, posted_count}
        """
        if not tweets:
            return {"success": False, "error": "tweets is empty"}

        try:
            is_ci = bool(os.getenv("CI"))
            self._create_driver(headless=is_ci)

            if not self._login_with_cookies():
                print("[INFO] Cookie無効。自動ログインを試みます...")
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                if not self.login_auto():
                    return {"success": False, "error": "auto login failed"}
                self._create_driver(headless=is_ci)
                if not self._login_with_cookies():
                    return {"success": False, "error": "cookie login failed after auto login"}

            posted_count = 0

            for i, tweet_text in enumerate(tweets):
                human_delay(2, 4)

                if i == 0:
                    # 最初のツイート: ホームから投稿
                    tweet_box = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
                    )
                else:
                    # 2ツイート目以降: 前のツイートへのリプライ
                    # 「返信する」ボタンを探す
                    time.sleep(3)
                    try:
                        reply_btn = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="reply"]'))
                        )
                        self.driver.execute_script("arguments[0].click();", reply_btn)
                        time.sleep(2)
                        tweet_box = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
                        )
                    except Exception as e:
                        print(f"[WARN] リプライボックスが見つかりません: {e}")
                        break

                actions = ActionChains(self.driver)
                actions.move_to_element(tweet_box).pause(random.uniform(0.3, 0.8)).click().perform()
                human_delay(0.5, 1.0)

                # 最初のツイートに画像を添付
                if i == 0 and image_path and os.path.exists(image_path):
                    try:
                        file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[data-testid="fileInput"]')
                        file_input.send_keys(os.path.abspath(image_path))
                        print(f"[INFO] 画像を添付: {image_path}")
                        time.sleep(3)
                    except Exception as e:
                        print(f"[WARN] 画像添付失敗: {e}")

                # テキスト入力
                tweet_box = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
                self.driver.execute_script("""
                    var el = arguments[0];
                    el.focus();
                    var text = arguments[1];
                    var dt = new DataTransfer();
                    dt.setData('text/plain', text);
                    var event = new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true});
                    el.dispatchEvent(event);
                """, tweet_box, tweet_text)
                human_delay(1.5, 2.5)

                # Ctrl+Enterで投稿
                tweet_box = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
                tweet_box.send_keys(Keys.CONTROL, Keys.ENTER)
                time.sleep(5)
                posted_count += 1
                print(f"[OK] スレッド {i+1}/{len(tweets)} 投稿完了")

            self._save_cookies()
            print(f"[OK] スレッド投稿完了（{posted_count}件）")
            return {"success": posted_count > 0, "posted_count": posted_count}

        except Exception as e:
            print(f"[ERROR] スレッド投稿エラー: {e}")
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
