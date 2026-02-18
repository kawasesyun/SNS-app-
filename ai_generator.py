"""Gemini AIを使ってバズる投稿を自動生成するモジュール"""

import os
import json
import random

try:
    import google.generativeai as genai
except ImportError:
    genai = None

SYSTEM_PROMPT = """あなたはX（旧Twitter）でバズる投稿を作るプロのSNSマーケターです。
以下のルールに従って、日本語の投稿文を1つ生成してください。

【テーマ】
成功マインドセット、お金を稼ぐ思考、努力・挑戦の大切さ、自己成長、メンタルの強さ

【バズるパターン（いずれかを使う）】
1. 対比型: 「成功する人は○○、失敗する人は○○」
2. リスト型: 「伸びる人の共通点。①○○ ②○○ ③○○」
3. 煽り型: 「知らないと損する○○」「これに気づいた人から人生変わる」
4. ストーリー型: 「昔は○○だった。でも○○して変わった」
5. 断言型: 「○○は絶対にやるな」「○○だけは続けろ」

【ルール】
- 280文字以内（厳守）
- 改行を効果的に使う（読みやすさ重視）
- 冒頭の1行で読者の手を止める（スクロールストッパー）
- 最後にハッシュタグを3個つける
- 絵文字は使わない
- 説教臭くならない、共感を生む文体
- 「あなた」に語りかける
- 具体的な数字やエピソードを入れると効果的

【出力形式】
以下のJSON形式で出力してください。他の文章は一切不要です。
{
  "post_text": "投稿本文（ハッシュタグ含む）",
  "image_quote": "画像に載せる短い名言（30文字以内）",
  "image_author": "名言の著者（なければ空文字）"
}
"""

TREND_PROMPT_TEMPLATE = """あなたはX（旧Twitter）でバズる投稿を作るプロのSNSマーケターです。

以下は今Xでバズっている投稿です。この投稿のスタイル・構造・テンションを参考にして、
完全にオリジナルの新しい投稿を作ってください。パクリではなく、バズる要素を取り入れた新作です。

【参考バズ投稿】
{trend_text}

【テーマ】
成功マインドセット、お金を稼ぐ思考、努力・挑戦の大切さ、自己成長、メンタルの強さ

【ルール】
- 280文字以内（厳守）
- 改行を効果的に使う
- 冒頭の1行で読者の手を止める
- 最後にハッシュタグを3個つける
- 絵文字は使わない
- 参考投稿の内容をそのまま使わない（構造だけ真似る）

【出力形式】
以下のJSON形式で出力してください。他の文章は一切不要です。
{{
  "post_text": "投稿本文（ハッシュタグ含む）",
  "image_quote": "画像に載せる短い名言（30文字以内）",
  "image_author": "名言の著者（なければ空文字）"
}}
"""


def _get_model():
    """Geminiモデルを取得"""
    if genai is None:
        raise ImportError("google-generativeai がインストールされていません")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def _parse_response(text: str) -> dict:
    """AIの応答からJSONを抽出"""
    # ```json ... ``` ブロックを抽出
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    # JSON中の改行文字をエスケープ
    # まずJSONとしてパースを試みる
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # { から } を抽出して再試行
    brace_start = text.find("{")
    brace_end = text.rfind("}") + 1
    if brace_start >= 0 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"JSONのパースに失敗: {text[:200]}")


def generate_viral_post() -> dict:
    """バズる投稿をAIで生成

    Returns:
        dict: {post_text, image_quote, image_author}
    """
    model = _get_model()

    response = model.generate_content(
        SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=1.0,
            max_output_tokens=500,
        ),
    )

    result = _parse_response(response.text)

    # バリデーション
    if "post_text" not in result:
        raise ValueError("post_text がありません")

    # 280文字制限チェック
    post_text = result["post_text"]
    if len(post_text) > 300:
        # ハッシュタグ部分を除いた本文を切り詰め
        lines = post_text.split("\n")
        hashtag_lines = [l for l in lines if l.strip().startswith("#")]
        body_lines = [l for l in lines if not l.strip().startswith("#")]
        body = "\n".join(body_lines)[:250]
        post_text = body + "\n\n" + "\n".join(hashtag_lines)
        result["post_text"] = post_text

    result.setdefault("image_quote", "")
    result.setdefault("image_author", "")

    print(f"[OK] AI投稿を生成しました（{len(result['post_text'])}文字）")
    return result


def generate_trend_post(trend_data: list) -> dict:
    """トレンド情報を参考にバズ投稿を生成

    Args:
        trend_data: スクレイピングしたバズ投稿リスト [{text, likes, author}, ...]

    Returns:
        dict: {post_text, image_quote, image_author, is_trend}
    """
    if not trend_data:
        return generate_viral_post()

    # 上位投稿を参考テキストとして使う
    top_posts = trend_data[:3]
    trend_text = "\n---\n".join(
        f"いいね数: {p.get('likes', 0)}\n{p['text']}" for p in top_posts
    )

    prompt = TREND_PROMPT_TEMPLATE.format(trend_text=trend_text)

    model = _get_model()
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=1.0,
            max_output_tokens=500,
        ),
    )

    result = _parse_response(response.text)

    if "post_text" not in result:
        raise ValueError("post_text がありません")

    result.setdefault("image_quote", "")
    result.setdefault("image_author", "")
    result["is_trend"] = True

    print(f"[OK] AIトレンド投稿を生成しました（{len(result['post_text'])}文字）")
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=== AI投稿生成テスト ===")
    try:
        result = generate_viral_post()
        print(f"\n--- 生成された投稿 ---")
        print(result["post_text"])
        print(f"\n--- 画像用 ---")
        print(f"Quote: {result['image_quote']}")
        print(f"Author: {result['image_author']}")
    except Exception as e:
        print(f"[ERROR] {e}")
