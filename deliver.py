#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Welu / 放課後等デイサービス特化 Threads 配信スクリプト
Claude APIで投稿文を生成 → Discord Webhookへ配信（届いたらコピペしてThreadsへ手動投稿）。
バズの型はNIGUN準拠（データ×比較×具体数字×断言×1行詰め）。重複防止はhistory.jsonで管理。
"""
import os
import sys
import anthropic
from discord_sender import send_to_discord
from history import (
    load_history, save_history, pick_theme, recent_texts, record_post,
)

# モデルはここで固定（過去に MODEL 環境変数が空文字でAPIエラーになった事故を回避）
MODEL = (os.environ.get("MODEL") or "").strip() or "claude-sonnet-4-6"
DRY_RUN = (os.environ.get("DRY_RUN", "false").strip().lower() == "true")
POST_TYPE = (os.environ.get("POST_TYPE") or "").strip().lower()

# ============================================================
# 共通ボイス（Welu：放課後等デイ特化・働きたい人/働く人向け・女性比率高め）
# NIGUNの「数字主軸・1行詰め・断言・短文」をWeluのやさしさと両立させる。
# ============================================================
VOICE = """あなたは「Welu（ウェルー）」のSNS発信者です。
Weluは放課後等デイサービス（放デイ）専門の転職・キャリア相談サービスで、自社でも障害福祉事業所を運営しています。
Threadsで、放デイで働く人・これから放デイで働きたい人（保育士・児童指導員・教員免許保有者・未経験など。女性が多い）に向けて投稿します。

# 絶対に守る（MUST）
- 数字・具体・比較で勝負する。1投稿に必ず具体的な数字を1つ以上入れる。抽象的な精神論は書かない。
- 列挙は改行せず1行に詰める（例：医療法人系350-420万 大手FC系280-330万 個人運営200-450万）。
- 120〜180字を目安、最長200字。前置きを削り、いきなり本題から入る。
- 断言する。言いっぱなしでよい。ただし読者（あなた）を見下さない。"放デイの現場を分かってる人"の距離感で。
- 一人称（私・俺・僕）は使わない。Welu（会社）の話のときだけ「私たち」は可。

# 絶対に書かない（NG）
- 感動ポルノ・やりがい搾取・根性論・説教（「頑張れ」「天職」を安易に使わない）。
- 「いかがでしたか」等のブログ的な締め／命令調CTA／ハッシュタグの羅列。
- 嘘の数字・デマ。相場や傾向は「〜なことが多い」等で表現する。

# 世界観（コアメッセージ）
- 燃え尽きは、才能が枯れたからじゃない。職場とのミスマッチ。
- 「辞めたい」「転職したい」は甘えじゃない。前向きな戦略。
- せっかくの資格・経験を、合わない放デイですり減らすのはもったいない。
- やりがいも、ちゃんとした待遇も、両方あきらめなくていい。
- Weluは自社でも障害福祉事業所を運営している。だから放デイ現場のリアルを本音で語れる。"""

# ============================================================
# 投稿タイプ（NIGUN準拠の5型を放デイ版に）＋ 切り口プール（重複防止）
# ============================================================
POST_TYPES = {
    # ── 最強のバイラル：データ系・比較 ──
    "viral": {
        "label": "🔥 データ・比較（最強バイラル）",
        "instruction": (
            "最もバズる型。放デイの『運営母体別・地域別・タイプ別』などの差を具体数字で示す。"
            "できれば数倍級の差を見せ、列挙は1行に詰め、最後は『どこも同じは思い込み』『知らないと損』等の強い断言で締める。"
            "120〜160字。いきなり本題から。"
        ),
        "themes": [
            "放デイの年収、運営母体別の差（医療法人系/社福系/大手FC系/個人運営）",
            "放デイの時給、地域別の差",
            "加算体制の違いで変わる給料",
            "児発管の有無で変わる年収",
            "送迎ありなしで変わる負担と離職率",
            "放デイと保育園、給料・休日数の比較",
            "個別支援計画の作成有無で変わる残業時間",
            "放デイの賞与、運営形態別の差",
            "児童指導員と保育士、放デイでの待遇差",
            "未経験から入れて伸びる障害児支援の職種比較",
        ],
    },
    # ── 保存される：まとめ・見抜き方 ──
    "ranking": {
        "label": "📊 まとめ・見抜き方",
        "instruction": (
            "数字つきのまとめ/ランキング（◯選・特徴・見抜き方）。保存・引用される型。"
            "見出し→中身は1行で列挙→最後はオープンループ（続きが気になる締め）。必ず具体を入れる。"
        ),
        "themes": [
            "消耗する放デイの特徴◯選",
            "子どもとちゃんと向き合えるいい放デイの見抜き方",
            "放デイの面接で必ず聞くべきこと",
            "求人票で見抜く『危ない放デイ』のサイン",
            "長く続く放デイ職員の共通点",
            "放デイの離職理由ランキング",
            "放デイ未経験が入る前に確認すべき条件",
        ],
    },
    # ── 本音・内部告発 ──
    "insider": {
        "label": "💢 内部・タブー",
        "instruction": (
            "放デイ業界の内部・タブーを本音で暴く。給料が上がらない理由、送迎の負担、加算の仕組み、"
            "大量開設による質のばらつき等。必ず具体（数字・事実）を入れる。読者を責めず、構造を責める。"
        ),
        "themes": [
            "放デイが急増した理由と、質のばらつき",
            "給料が上がらないのは加算と運営の問題",
            "送迎が職員の消耗の最大要因になっている",
            "個別支援計画・記録の事務負担の重さ",
            "児発管が不足している構造",
            "『療育』と名ばかりの預かりの差",
            "処遇改善加算が現場に回らない事業所がある",
        ],
    },
    # ── 逆張り・キャリア（背中押し）──
    "career": {
        "label": "🚀 キャリア・逆張り",
        "instruction": (
            "前向きに背中を押す逆張り。転職は前向き／児発管というキャリア／事業所を変えれば変わる／"
            "『向いてない』ではなく『合ってない』だけ。具体や数字を1つ入れる。"
        ),
        "themes": [
            "放デイを辞めたいは、甘えじゃない",
            "児発管になると年収もキャリアも変わる",
            "事業所を変えるだけで消耗度が変わる",
            "『子ども相手は向いてない』ではなく『職場が合ってない』",
            "保育士資格は放デイで強い武器になる",
            "転職は回数より『選び方』で評価される",
            "合わない放デイで我慢し続ける時間がもったいない",
        ],
    },
    # ── 共感・エピソード（ファン化）──
    "episode": {
        "label": "🤝 共感・エピソード",
        "instruction": (
            "現場のリアルな共感エピソード/あるある（ファン化用）。子どもの成長、保護者対応、送迎、記録など。"
            "このタイプは数字なしでもよい。やさしく、でも本音で。最後は『分かる人いる？』的な共感で締める。"
        ),
        "themes": [
            "子どもの小さな成長に立ち会えた瞬間",
            "保護者対応の気疲れ",
            "送迎中の責任とヒヤリ",
            "記録が終わらなくて残業する夜",
            "『先生』と呼ばれる嬉しさと、その重さ",
            "利用児は好き、でも職場がしんどい矛盾",
            "連休明けの憂うつ",
        ],
    },
}
ORDER = ["viral", "ranking", "insider", "career", "episode"]


def generate(client, key, theme, avoid_texts):
    spec = POST_TYPES[key]
    avoid_block = ""
    if avoid_texts:
        joined = "\n".join(f"- {t}" for t in avoid_texts)
        avoid_block = f"\n# 直近の投稿（切り口・言い回し・数字の見せ方が被らないように）\n{joined}\n"

    prompt = f"""{VOICE}

# 今回の投稿タイプ
{spec['label']}

# このタイプの作り方
{spec['instruction']}

# 今回の切り口（これを軸に書く）
{theme}
{avoid_block}
# 出力ルール
- Threadsにそのまま貼れる投稿本文だけを出力する（前置き・解説・補足は一切不要）。
- 上の「直近の投稿」とは切り口・言い回し・数字の見せ方を被らせない。
- 「絶対に守る（MUST）」を厳守する。

投稿本文："""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY が未設定です", file=sys.stderr)
        sys.exit(1)
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook and not DRY_RUN:
        print("ERROR: DISCORD_WEBHOOK_URL が未設定です", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    history = load_history()

    if POST_TYPE in ("", "all"):
        keys = ORDER
    elif POST_TYPE in POST_TYPES:
        keys = [POST_TYPE]
    else:
        print(f"ERROR: 不明な POST_TYPE: {POST_TYPE}", file=sys.stderr)
        sys.exit(1)

    changed = False
    for key in keys:
        label = POST_TYPES[key]["label"]
        theme = pick_theme(history, key, POST_TYPES[key]["themes"])
        avoid = recent_texts(history, n=8)
        try:
            text = generate(client, key, theme, avoid)
        except Exception as e:
            print(f"生成失敗 [{label}]: {e}", file=sys.stderr)
            continue

        message = f"**{label}**　｜　コピーしてThreadsへ\n────────────\n{text}"
        if DRY_RUN:
            print(f"\n===== [DRY_RUN] {label} / 切り口: {theme} =====\n{text}\n")
        else:
            send_to_discord(webhook, message)
            record_post(history, key, theme, text)
            changed = True
            print(f"sent: {label}（切り口: {theme}）")

    if changed and not DRY_RUN:
        save_history(history)


if __name__ == "__main__":
    main()
