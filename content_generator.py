"""テキストファイルから投稿内容を読み込むモジュール（重複防止付き・API自動補充）"""

import os
import json
import random
import urllib.request

DEFAULT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "post_history.json")
MEIGEN_API_URL = "https://meigen.doodlenote.net/api/json.php?c=10"
AUTO_REFILL_THRESHOLD = 5  # 残りがこの数以下になったら自動補充


class ContentGenerator:
    def __init__(self):
        self.file_path = os.getenv("POSTS_FILE", "posts.txt")
        self.history_file = os.getenv("HISTORY_FILE", DEFAULT_HISTORY_FILE)
        self.posts = self._load_posts()
        self.history = self._load_history()

    def _load_posts(self) -> list:
        """投稿ファイルを読み込む"""
        if not os.path.exists(self.file_path):
            print(f"[ERROR] 投稿ファイルが見つかりません: {self.file_path}")
            return []

        with open(self.file_path, "r", encoding="utf-8") as f:
            posts = [line.strip() for line in f if line.strip()]

        print(f"投稿ファイルから {len(posts)} 件読み込みました")
        return posts

    def _fetch_from_api(self, count=10) -> list:
        """名言APIから新しい名言を取得"""
        try:
            url = f"https://meigen.doodlenote.net/api/json.php?c={count}"
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read().decode("utf-8"))
            quotes = []
            for item in data:
                text = f"「{item['meigen']}」 - {item['auther']}"
                if text not in self.posts and text not in self.history:
                    quotes.append(text)
            print(f"[API] {len(quotes)} 件の新しい名言を取得しました")
            return quotes
        except Exception as e:
            print(f"[WARN] 名言APIの取得に失敗: {e}")
            return []

    def _append_to_file(self, new_posts: list):
        """新しい投稿をposts.txtに追加"""
        with open(self.file_path, "a", encoding="utf-8") as f:
            for post in new_posts:
                f.write(post + "\n")
        self.posts.extend(new_posts)
        print(f"[OK] posts.txt に {len(new_posts)} 件追加しました（合計 {len(self.posts)} 件）")

    def auto_refill(self):
        """残りが少なくなったらAPIから自動補充"""
        remaining = self.get_remaining_count()
        if remaining <= AUTO_REFILL_THRESHOLD:
            print(f"[INFO] 残り {remaining} 件。APIから名言を自動補充します...")
            new_posts = self._fetch_from_api(20)
            if new_posts:
                self._append_to_file(new_posts)
            else:
                print("[WARN] APIから名言を取得できませんでした")

    def _load_history(self) -> list:
        """投稿履歴を読み込む"""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def _save_history(self):
        """投稿履歴を保存"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def generate_post(self) -> str:
        """まだ投稿していない内容をランダムに選択する"""
        if not self.posts:
            return ""

        # 自動補充チェック
        self.auto_refill()

        # 未投稿のものだけ抽出
        available = [p for p in self.posts if p not in self.history]

        if not available:
            print("[WARN] 全ての投稿が使用済みです")
            # 最後の手段: APIから取得して即使う
            new_posts = self._fetch_from_api(10)
            if new_posts:
                self._append_to_file(new_posts)
                available = new_posts
            else:
                return ""

        post = random.choice(available)
        self.history.append(post)
        self._save_history()

        remaining = len(self.posts) - len(self.history)
        print(f"残り未投稿: {remaining} 件")
        return post

    def get_remaining_count(self) -> int:
        """未投稿の数を返す"""
        return len([p for p in self.posts if p not in self.history])


if __name__ == "__main__":
    generator = ContentGenerator()
    print(f"未投稿: {generator.get_remaining_count()} 件")
    post = generator.generate_post()
    if post:
        print(f"選択された投稿:\n{post}")
    else:
        print("投稿できる内容がありません")
