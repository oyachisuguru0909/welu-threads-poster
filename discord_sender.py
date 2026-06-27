#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discord Webhook へメッセージを送信する。2000字制限に合わせて自動分割。"""
import time
import requests

DISCORD_LIMIT = 1900  # 余裕をもって1900で分割


def _chunk(text, limit=DISCORD_LIMIT):
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def send_to_discord(webhook_url, content):
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")
    for chunk in _chunk(content):
        resp = requests.post(webhook_url, json={"content": chunk}, timeout=30)
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"Discord webhook failed: {resp.status_code} {resp.text}"
            )
        time.sleep(1)  # レート制限よけ
