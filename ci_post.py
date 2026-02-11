"""GitHub Actions用: 1回だけ投稿して終了するスクリプト"""

import os
import sys
import random
import time
import json
from dotenv import load_dotenv

load_dotenv()

# ランダムな遅延を追加（投稿間隔をばらつかせる）
max_delay_minutes = int(os.getenv("RANDOM_DELAY_MINUTES", 60))
if max_delay_minutes > 0:
    delay = random.randint(0, max_delay_minutes)
    print(f"[INFO] {delay}分間のランダム遅延を開始...")
    time.sleep(delay * 60)
    print(f"[INFO] 遅延完了。投稿を開始します。")

from twitter_client import TwitterClient
from content_generator import ContentGenerator
from image_generator import generate_quote_image
from trend_scraper import get_buzz_post_for_reference

# 投稿タイプのローテーション記録ファイル
ROTATION_FILE = os.path.join(os.path.dirname(__file__), "post_rotation.json")


def _load_rotation() -> dict:
    """ローテーション状態を読み込む"""
    if os.path.exists(ROTATION_FILE):
        try:
            with open(ROTATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_type": "trend"}  # 初回は名言から始まるように


def _save_rotation(data: dict):
    """ローテーション状態を保存"""
    with open(ROTATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _should_use_trend() -> bool:
    """今回トレンド投稿を使うかどうか（2回に1回）"""
    rotation = _load_rotation()
    last_type = rotation.get("last_type", "trend")
    # 前回がtrend → 今回はquote、前回がquote → 今回はtrend
    return last_type == "quote"


def main():
    use_trend = _should_use_trend()
    print(f"[INFO] 今回の投稿タイプ: {'トレンド参考' if use_trend else '名言'}")

    content = None
    image_path = None

    if use_trend:
        # === トレンド投稿モード ===
        print("[INFO] バズ投稿を参考にした投稿を生成中...")
        try:
            trend_result = get_buzz_post_for_reference()
            if trend_result:
                content = trend_result["post_text"]
                # 画像生成
                try:
                    image_path = generate_quote_image(
                        trend_result["image_quote"],
                        trend_result.get("image_author", ""),
                    )
                    print(f"[OK] トレンド画像を生成: {image_path}")
                except Exception as e:
                    print(f"[WARN] トレンド画像生成失敗: {e}")
            else:
                print("[WARN] トレンド投稿の取得に失敗。名言投稿にフォールバック。")
        except Exception as e:
            print(f"[WARN] トレンド処理エラー: {e}。名言投稿にフォールバック。")

    if not content:
        # === 名言投稿モード（通常 or フォールバック） ===
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

        # 名言画像を生成
        try:
            raw_post = generator.history[-1] if generator.history else ""
            if " - " in raw_post:
                quote_part, author_part = raw_post.rsplit(" - ", 1)
                quote_text = quote_part.replace("「", "").replace("」", "")
                image_path = generate_quote_image(quote_text, author_part)
                print(f"[OK] 名言画像を生成: {image_path}")
            else:
                print("[INFO] 画像生成スキップ（著者情報なし）")
        except Exception as e:
            print(f"[WARN] 画像生成失敗: {e}")

        # フォールバックの場合はトレンドとして記録しない
        if use_trend:
            use_trend = False

    print(f"投稿内容: {content}")

    client = TwitterClient()
    result = client.post_tweet(content, image_path=image_path)

    if result["success"]:
        # ローテーション記録を更新
        _save_rotation({"last_type": "trend" if use_trend else "quote"})
        print("[OK] 投稿完了!")
        sys.exit(0)
    else:
        print(f"[ERROR] 投稿失敗: {result.get('error', 'unknown')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
