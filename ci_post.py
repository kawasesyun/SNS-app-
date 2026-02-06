"""GitHub Actions用: 1回だけ投稿して終了するスクリプト"""

import os
import sys
import random
import time

# ランダムな遅延を追加（投稿間隔をばらつかせる）
max_delay_minutes = int(os.getenv("RANDOM_DELAY_MINUTES", 60))
if max_delay_minutes > 0:
    delay = random.randint(0, max_delay_minutes)
    print(f"[INFO] {delay}分間のランダム遅延を開始...")
    time.sleep(delay * 60)
    print(f"[INFO] 遅延完了。投稿を開始します。")

from twitter_client import TwitterClient
from content_generator import ContentGenerator


def main():
    generator = ContentGenerator()

    remaining = generator.get_remaining_count()
    print(f"未投稿の残り: {remaining} 件")

    if remaining == 0:
        print("[WARN] 全投稿が使用済みです。posts.txt に新しい内容を追加してください。")
        sys.exit(0)

    content = generator.generate_post()
    if not content:
        print("[ERROR] 投稿内容を取得できませんでした")
        sys.exit(1)

    print(f"投稿内容: {content}")

    client = TwitterClient()
    result = client.post_tweet(content)

    if result["success"]:
        print("[OK] 投稿完了!")
        sys.exit(0)
    else:
        print(f"[ERROR] 投稿失敗: {result.get('error', 'unknown')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
