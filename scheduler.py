"""ランダム間隔で投稿するスケジュール管理モジュール"""

import os
import random
import time
from datetime import datetime

from twitter_client import TwitterClient
from content_generator import ContentGenerator


class PostScheduler:
    def __init__(self):
        self.twitter_client = TwitterClient()
        self.content_generator = ContentGenerator()
        self.min_hours = int(os.getenv("POST_MIN_HOURS", 2))
        self.max_hours = int(os.getenv("POST_MAX_HOURS", 5))

    def post_job(self):
        """投稿ジョブ: 内容選択 → 投稿"""
        print(f"\n{'='*50}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 投稿ジョブ開始")

        content = self.content_generator.generate_post()
        if not content:
            print("[WARN] 投稿する内容がありません。posts.txt に追加してください")
            return False

        print(f"投稿内容: {content}")
        print("Xに投稿中...")
        result = self.twitter_client.post_tweet(content)

        if result["success"]:
            print("[OK] 投稿完了")
        print(f"{'='*50}\n")
        return result["success"]

    def start(self):
        """ランダム間隔で投稿を繰り返す"""
        remaining = self.content_generator.get_remaining_count()
        print(f"X自動投稿スケジューラーを開始します")
        print(f"投稿間隔: {self.min_hours}〜{self.max_hours}時間（ランダム）")
        print(f"未投稿の残り: {remaining} 件")
        print("-" * 50)

        # 起動時に1回投稿
        self.post_job()

        try:
            while True:
                # ランダムな間隔を決定
                wait_hours = random.uniform(self.min_hours, self.max_hours)
                wait_minutes = int(wait_hours * 60)
                next_time = datetime.now().strftime('%H:%M')
                print(f"次回投稿: {wait_hours:.1f}時間後（約{wait_minutes}分後）")

                # 待機
                time.sleep(wait_hours * 3600)

                # 残り確認
                if self.content_generator.get_remaining_count() == 0:
                    print("[WARN] 全投稿が使用済みです。停止します")
                    print("posts.txt に新しい内容を追加してから再起動してください")
                    break

                self.post_job()

        except KeyboardInterrupt:
            print("\nスケジューラーを停止しました")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    scheduler = PostScheduler()
    scheduler.start()
