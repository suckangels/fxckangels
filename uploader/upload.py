#!/usr/bin/env python3
"""
Clip Uploader — загрузка клипов на YouTube и TikTok.

Использование:
    python upload.py                   — загрузить все клипы из config.json
    python upload.py --platform youtube — только YouTube
    python upload.py --platform tiktok  — только TikTok
    python upload.py --login youtube    — авторизоваться в YouTube
    python upload.py --login tiktok     — авторизоваться в TikTok
"""

import argparse
import json
import os
import sys
from pathlib import Path

from youtube_upload import youtube_upload_clips, get_authenticated_service
from tiktok_upload import tiktok_upload_clips, tiktok_login

CONFIG_FILE = "config.json"


def load_config(path: str) -> dict:
    """Load config from JSON file."""
    if not os.path.exists(path):
        print(f"Ошибка: файл конфигурации '{path}' не найден!")
        print(f"Создай его по примеру config.example.json")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_clip_list(config: dict) -> list:
    """Build list of clips from config."""
    clips_dir = config.get("clips_dir", "clips")
    clips = config.get("clips", [])

    result = []
    for clip in clips:
        file_path = os.path.join(clips_dir, clip["file"])
        if not os.path.exists(file_path):
            print(f"⚠ Файл не найден: {file_path} — пропускаю")
            continue
        result.append({
            "file": file_path,
            "title": clip["title"],
            "description": clip.get("description", ""),
            "tags": clip.get("tags", []),
        })

    if not result:
        print("Нет клипов для загрузки! Проверь config.json и папку clips/")
        sys.exit(1)

    return result


def do_login(platform: str, config: dict):
    """Interactive login for a platform."""
    if platform == "youtube":
        yt_config = config.get("youtube", {})
        secrets_path = yt_config.get("client_secrets", "client_secrets.json")
        token_path = yt_config.get("token_file", "youtube_token.json")
        print("\n=== Авторизация YouTube ===")
        print(f"Используется файл: {secrets_path}")
        get_authenticated_service(secrets_path, token_path)
        print("YouTube авторизация завершена!\n")

    elif platform == "tiktok":
        tt_config = config.get("tiktok", {})
        cookies_path = tt_config.get("cookies_file", "tiktok_cookies.json")
        print("\n=== Авторизация TikTok ===")
        tiktok_login(cookies_path)
        print("TikTok авторизация завершена!\n")

    else:
        print(f"Неизвестная платформа: {platform}")
        print("Доступные: youtube, tiktok")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Загрузка клипов на YouTube и TikTok"
    )
    parser.add_argument(
        "--config", "-c",
        default=CONFIG_FILE,
        help="Путь к файлу конфигурации (по умолчанию: config.json)",
    )
    parser.add_argument(
        "--platform", "-p",
        choices=["youtube", "tiktok"],
        help="Загрузить только на указанную платформу",
    )
    parser.add_argument(
        "--login", "-l",
        metavar="PLATFORM",
        help="Авторизоваться в платформе (youtube / tiktok)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    # Login mode
    if args.login:
        do_login(args.login, config)
        return

    clips = build_clip_list(config)

    print(f"\nНайдено клипов: {len(clips)}")
    print("=" * 50)
    for i, clip in enumerate(clips, 1):
        print(f"  {i}. {clip['title']} ({clip['file']})")
    print("=" * 50)

    platforms = [args.platform] if args.platform else ["youtube", "tiktok"]

    all_results = {}

    # YouTube
    if "youtube" in platforms:
        print("\n>>> YouTube <<<")
        try:
            yt_results = youtube_upload_clips(clips, config)
            all_results["youtube"] = yt_results
        except Exception as e:
            print(f"  [YouTube] Критическая ошибка: {e}")
            all_results["youtube"] = [{"error": str(e), "status": "error"}]

    # TikTok
    if "tiktok" in platforms:
        print("\n>>> TikTok <<<")
        try:
            tt_results = tiktok_upload_clips(clips, config)
            all_results["tiktok"] = tt_results
        except Exception as e:
            print(f"  [TikTok] Критическая ошибка: {e}")
            all_results["tiktok"] = [{"error": str(e), "status": "error"}]

    # Summary
    print("\n" + "=" * 50)
    print("ИТОГИ ЗАГРУЗКИ:")
    print("=" * 50)
    for platform, results in all_results.items():
        print(f"\n  {platform.upper()}:")
        for r in results:
            status = "✓" if r.get("status") == "ok" else "✗"
            title = r.get("title", "—")
            extra = ""
            if r.get("video_id"):
                extra = f" → https://youtu.be/{r['video_id']}"
            if r.get("error"):
                extra = f" → {r['error']}"
            print(f"    {status} {title}{extra}")

    print()


if __name__ == "__main__":
    main()
