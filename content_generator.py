"""テキストファイルから投稿内容を読み込むモジュール（重複防止付き）"""

import os
import json
import random

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "post_history.json")


class ContentGenerator:
    def __init__(self):
        self.file_path = os.getenv("POSTS_FILE", "posts.txt")
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

    def _load_history(self) -> list:
        """投稿履歴を読み込む"""
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def _save_history(self):
        """投稿履歴を保存"""
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def generate_post(self) -> str:
        """まだ投稿していない内容をランダムに選択する"""
        if not self.posts:
            return ""

        # 未投稿のものだけ抽出
        available = [p for p in self.posts if p not in self.history]

        if not available:
            print("[WARN] 全ての投稿が使用済みです。posts.txt に新しい内容を追加してください")
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
