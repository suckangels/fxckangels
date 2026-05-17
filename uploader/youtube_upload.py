"""
YouTube upload module.
Uses YouTube Data API v3 with OAuth2 for authentication.
"""

import os
import json
import time
import httplib2
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "youtube_token.json"
CLIENT_SECRETS_FILE = "client_secrets.json"

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 10


def get_authenticated_service(secrets_path: str, token_path: str) -> object:
    """Authenticate with YouTube API via OAuth2 and return the service object."""
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(secrets_path):
                raise FileNotFoundError(
                    f"Файл {secrets_path} не найден!\n"
                    "Скачай его из Google Cloud Console:\n"
                    "https://console.cloud.google.com/apis/credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=8090, open_browser=True)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    youtube,
    file_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    category_id: str = "22",
    privacy: str = "public",
) -> str:
    """
    Upload a video to YouTube.

    Returns the video ID on success.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Видео не найдено: {file_path}")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        file_path,
        chunksize=10 * 1024 * 1024,  # 10 MB chunks
        resumable=True,
        mimetype="video/*",
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    retries = 0

    print(f"  [YouTube] Загрузка: {title}")

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  [YouTube] Прогресс: {pct}%")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                retries += 1
                if retries > MAX_RETRIES:
                    raise
                wait = 2 ** retries
                print(f"  [YouTube] Ошибка {e.resp.status}, повтор через {wait}с...")
                time.sleep(wait)
            else:
                raise

    video_id = response["id"]
    print(f"  [YouTube] Готово! https://youtu.be/{video_id}")
    return video_id


def youtube_upload_clips(clips: list, config: dict) -> list:
    """
    Upload multiple clips to YouTube.

    clips: list of dicts with keys: file, title, description (optional)
    config: global config dict with youtube settings

    Returns list of video IDs.
    """
    yt_config = config.get("youtube", {})
    secrets_path = yt_config.get("client_secrets", CLIENT_SECRETS_FILE)
    token_path = yt_config.get("token_file", TOKEN_FILE)
    privacy = yt_config.get("privacy", "public")
    category_id = yt_config.get("category_id", "22")
    default_tags = yt_config.get("tags", [])

    youtube = get_authenticated_service(secrets_path, token_path)

    results = []
    for clip in clips:
        try:
            video_id = upload_video(
                youtube,
                file_path=clip["file"],
                title=clip["title"],
                description=clip.get("description", ""),
                tags=clip.get("tags", default_tags),
                category_id=category_id,
                privacy=privacy,
            )
            results.append({"file": clip["file"], "title": clip["title"], "video_id": video_id, "status": "ok"})
        except Exception as e:
            print(f"  [YouTube] ОШИБКА при загрузке {clip['file']}: {e}")
            results.append({"file": clip["file"], "title": clip["title"], "error": str(e), "status": "error"})

    return results
