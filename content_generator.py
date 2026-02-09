"""テキストファイルから投稿内容を読み込むモジュール（重複防止付き・API自動補充）"""

import os
import json
import random
import urllib.request

DEFAULT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "post_history.json")
MEIGEN_API_URL = "https://meigen.doodlenote.net/api/json.php?c=10"
AUTO_REFILL_THRESHOLD = 5  # 残りがこの数以下になったら自動補充

# 共感フック（冒頭に付ける一言）
HOOKS = [
    "何度でも言いたい。",
    "これ、マジで大事。",
    "心に刺さった言葉。",
    "迷った時に読み返したい。",
    "全人類に届けたい言葉。",
    "これを知ってから人生変わった。",
    "何回読んでも鳥肌が立つ。",
    "20代のうちに知りたかった。",
    "落ち込んだ時はこれを読む。",
    "保存して何度も読み返してほしい。",
    "この言葉に何度救われたか。",
    "成功する人は皆これを知っている。",
    "これが真理だと思う。",
    "忘れちゃいけない言葉。",
    "壁にぶつかった時に思い出す言葉。",
]

# 一言コメント（名言の後に付ける感想）
COMMENTS = [
    "行動した人だけが見える景色がある。",
    "結局、やるかやらないか。それだけ。",
    "完璧じゃなくていい。まず一歩。",
    "過去は変えられない。でも未来は選べる。",
    "今日が人生で一番若い日。",
    "失敗を恐れるより、何もしないことを恐れよう。",
    "努力は裏切らない。ただし正しい方向に。",
    "自分を信じた人だけが道を切り拓ける。",
    "小さな積み重ねが、やがて大きな差になる。",
    "諦めた瞬間が、本当の失敗。",
    "昨日の自分を超えればいい。それだけでいい。",
    "環境のせいにした瞬間、成長は止まる。",
    "辛い時こそ、自分の底力が試される。",
    "夢は逃げない。逃げるのはいつも自分。",
    "後悔するのは、やらなかったこと。",
]

# リプライ誘導（エンゲージメント促進）
ENGAGEMENTS = [
    "共感したら♥",
    "保存していつでも読み返そう📌",
    "あなたの座右の銘は何ですか？",
    "グッときたらRT🔁",
    "誰かに届けたいと思ったらRT",
    "この言葉、誰に届けたい？",
    "",  # 空文字 = 問いかけなし（毎回入れるとしつこいので）
    "",
]

# ハッシュタグセット（ランダムに3〜4個選ぶ）
HASHTAGS = [
    "#名言", "#格言", "#人生", "#モチベーション",
    "#自己啓発", "#成長", "#挑戦", "#努力",
    "#言葉の力", "#心に響く言葉", "#今日の名言",
]


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

        # フォーマット整形 + ハッシュタグ追加
        formatted = self._format_post(post)
        return formatted

    def _format_post(self, post: str) -> str:
        """バズる投稿フォーマットに整形"""
        # 共感フック（冒頭の一言）
        hook = random.choice(HOOKS)

        # 「名言」 - 人物 の形式を分割
        if " - " in post:
            quote_part, author_part = post.rsplit(" - ", 1)
            quote_block = f"{quote_part}\n\n― {author_part}"
        else:
            quote_block = post

        # 一言コメント（感想・教訓）
        comment = random.choice(COMMENTS)

        # ハッシュタグ（3〜4個）
        tags = random.sample(HASHTAGS, random.randint(3, 4))
        tag_line = " ".join(tags)

        # リプライ誘導（ランダムに付ける）
        engagement = random.choice(ENGAGEMENTS)

        # フォーマット: フック → 名言 → コメント → 誘導 → ハッシュタグ
        parts = [hook, quote_block, comment]
        if engagement:
            parts.append(engagement)
        parts.append(tag_line)
        result = "\n\n".join(parts)
        return result

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
