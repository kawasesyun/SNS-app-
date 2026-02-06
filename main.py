"""X投稿自動化システム - メインエントリーポイント"""

import os
import sys
from dotenv import load_dotenv


def main():
    """メイン処理"""
    load_dotenv()

    print("=" * 50)
    print("X投稿自動化システム")
    print("=" * 50)

    from twitter_client import TwitterClient, COOKIE_FILE
    client = TwitterClient()

    # Cookieがなければ初回ログイン
    if not os.path.exists(COOKIE_FILE):
        print("\n初回セットアップ: Xにログインが必要です")
        print("ブラウザが開くので、Xにログインしてください\n")
        client.login_manual()
        print()

    # モード選択
    print("\n実行モードを選択してください:")
    print("1. 定期自動投稿を開始")
    print("2. 今すぐ1回だけ投稿")
    print("3. 投稿内容のテスト生成（投稿しない）")
    print("4. Xに再ログイン（Cookie更新）")
    print("0. 終了")

    choice = input("\n選択 (0-4): ").strip()

    if choice == "1":
        from scheduler import PostScheduler
        scheduler = PostScheduler()
        scheduler.start()

    elif choice == "2":
        from content_generator import ContentGenerator
        generator = ContentGenerator()
        content = generator.generate_post()
        print(f"\n生成された投稿:\n{content}\n")

        confirm = input("この内容で投稿しますか? (y/n): ").strip().lower()
        if confirm == "y":
            result = client.post_tweet(content)
            if result["success"]:
                print("[OK] 投稿が完了しました!")
        else:
            print("投稿をキャンセルしました。")

    elif choice == "3":
        from content_generator import ContentGenerator
        generator = ContentGenerator()
        print("\nテスト生成（5回）:")
        for i in range(5):
            content = generator.generate_post()
            print(f"\n[{i+1}] {content}")

    elif choice == "4":
        client.login_manual()

    else:
        print("終了します。")


if __name__ == "__main__":
    main()
