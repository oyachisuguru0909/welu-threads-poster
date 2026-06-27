#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""投稿の重複防止：テーマのローテーション管理＋直近投稿の記録（history.json）。"""
import os
import json
import random
import datetime

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
RECENT_KEEP = 40  # 直近何件を保持するか（被り回避の参照にも使う）


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                h = json.load(f)
                h.setdefault("used_themes", {})
                h.setdefault("recent_posts", [])
                return h
        except Exception:
            pass
    return {"used_themes": {}, "recent_posts": []}


def save_history(h):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)


def pick_theme(h, post_type, pool):
    """まだ使っていない切り口から1つ選ぶ。全部使い切ったら一周リセット。"""
    used = h["used_themes"].get(post_type, [])
    remaining = [t for t in pool if t not in used]
    if not remaining:                 # 一周したのでリセット
        used = []
        remaining = list(pool)
    theme = random.choice(remaining)
    used.append(theme)
    h["used_themes"][post_type] = used
    return theme


def recent_texts(h, n=8):
    """直近n件の投稿本文（被り回避のためAIに渡す）。"""
    return [p.get("text", "") for p in h["recent_posts"][-n:] if p.get("text")]


def record_post(h, post_type, theme, text):
    h["recent_posts"].append({
        "type": post_type,
        "theme": theme,
        "text": text,
        "ts": datetime.datetime.utcnow().isoformat(timespec="seconds"),
    })
    h["recent_posts"] = h["recent_posts"][-RECENT_KEEP:]
