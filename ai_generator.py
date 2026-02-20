"""Gemini AIを使ってバズる投稿を自動生成するモジュール"""

import os
import json
import random

try:
    import google.generativeai as genai
except ImportError:
    genai = None

SYSTEM_PROMPT = """あなたはX（旧Twitter）で月100万インプレッションを達成したSNSマーケターです。
日本語でバズる投稿を1つ生成してください。

【テーマ（ランダムに1つ選ぶ）】
- お金・投資・資産形成の思考法
- 成功者と普通の人の決定的な違い
- 知らないと一生損する仕事・ビジネスの真実
- メンタルが強い人だけが知っていること
- 20代・30代がやるべき習慣

【必ず使うバズパターン（ランダムに1つ選ぶ）】
A. 衝撃の事実型:「実は○○だった。」「○○の9割が知らないこと。」
B. 禁止・命令型:「○○をやめろ。」「今すぐ○○しろ。」「絶対に○○するな。」
C. 格差対比型:「年収300万の人→○○ / 年収1000万の人→○○」
D. リスト暴露型:「成功者が絶対に言わない5つのこと。①②③④⑤」
E. ストーリー共感型:「3年前の俺は○○だった。でも○○を変えた結果→」
F. 問いかけ型:「あなたは○○できてる？できてない人の末路→」
G. FOMO型:「これを知ってる人は5年後に確実に差がつく。」

【スクロールストッパー技術（冒頭必須）】
- 短い1行で始める（15文字以内）
- 数字を使う（「9割が」「3年で」「月100万」）
- 「。」で終わる断言文
- 読者が「自分のことだ」と思う内容

【文体ルール】
- 280文字以内（厳守）
- 改行は2〜4行ごと（テンポ重視）
- 絵文字・顔文字は使わない
- 「あなた」「自分」「俺」で語りかける
- 最後にハッシュタグを3〜4個（投稿内容に最適なものを選ぶ）
- ハッシュタグ候補: #お金 #投資 #副業 #資産形成 #マインドセット #成功法則 #自己啓発 #仕事術 #人生設計 #節約 #稼ぐ #ビジネス #名言 #モチベーション #成長 #習慣 #努力 #挑戦

【出力形式】
以下のJSON形式のみ出力。他の文章は絶対に不要。
{
  "post_text": "投稿本文（ハッシュタグ含む）",
  "image_quote": "画像に載せるインパクトある一言（25文字以内）",
  "image_author": "名言の著者（オリジナルなら空文字）"
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


THREAD_PROMPT = """あなたはX（旧Twitter）で月100万インプレッションを達成したSNSマーケターです。
お金・成功・マインドセットをテーマに、バズるスレッドを作ってください。

【スレッド構成（5ツイート）】
- ツイート1（Hook）: 衝撃の一言。「これを読んだら人生変わる」と思わせる。15文字以内の短い断言から始める
- ツイート2（Problem）: 読者が抱える悩みや現実を突きつける
- ツイート3〜4（Solution）: 具体的な解決策。数字・対比・ストーリーを使う
- ツイート5（CTA）: 「保存して何度も読み返せ」「フォローして損はない」系

【バズるスレッドのルール】
- 各ツイートは120文字以内（厳守・短い方が読まれる）
- ツイート1は特に短く・インパクト重視
- 絵文字なし
- ハッシュタグは最後のツイートのみ3〜4個
- 続き番号なし（「1/5」「続き↓」不要）
- 読者が「これ自分のことだ」と思う内容
- 具体的な数字を入れる（「年収300万」「3ヶ月で」「月5万」）

【出力形式】
以下のJSON形式のみ出力。他の文章は絶対に不要。
{
  "tweets": [
    "1ツイート目の本文",
    "2ツイート目の本文",
    "3ツイート目の本文",
    "4ツイート目の本文",
    "5ツイート目の本文 #お金 #マインドセット #成功法則"
  ],
  "image_quote": "画像に載せるインパクトある一言（25文字以内）",
  "image_author": "名言の著者（オリジナルなら空文字）"
}
"""


def generate_thread() -> dict:
    """バズるスレッド投稿をAIで生成

    Returns:
        dict: {tweets: [str, ...], image_quote, image_author}
    """
    model = _get_model()

    response = model.generate_content(
        THREAD_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=1.0,
            max_output_tokens=800,
        ),
    )

    result = _parse_response(response.text)

    if "tweets" not in result or not isinstance(result["tweets"], list):
        raise ValueError("tweetsリストがありません")

    # 各ツイートの文字数チェック
    tweets = []
    for tweet in result["tweets"]:
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        tweets.append(tweet)
    result["tweets"] = tweets

    result.setdefault("image_quote", "")
    result.setdefault("image_author", "")

    print(f"[OK] スレッドを生成しました（{len(tweets)}ツイート）")
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
