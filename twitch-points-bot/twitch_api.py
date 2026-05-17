"""Twitch GQL API wrapper for channel points operations."""

import logging
from secrets import token_hex

import requests

logger = logging.getLogger("twitch_bot")

CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
GQL_URL = "https://gql.twitch.tv/gql"
SPADE_URL = "https://spade.twitch.tv/track"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class TwitchAPI:
    """Handles all Twitch GQL API interactions."""

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.session = requests.Session()
        self.session.headers.update({
            "Client-Id": CLIENT_ID,
            "Authorization": f"OAuth {auth_token}",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        })
        self.device_id = token_hex(16)
        self.user_id = None
        self.user_login = None

    def _gql_request(self, data: dict | list) -> dict | list:
        """Send a GQL request and return the response JSON."""
        try:
            resp = self.session.post(GQL_URL, json=data, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("GQL request failed: %s", e)
            raise

    def validate_token(self) -> bool:
        """Validate the auth token and get user info."""
        try:
            resp = self.session.get(
                "https://id.twitch.tv/oauth2/validate",
                headers={"Authorization": f"OAuth {self.auth_token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.user_id = data.get("user_id")
                self.user_login = data.get("login")
                logger.info(
                    "Токен валиден. Пользователь: %s (ID: %s)",
                    self.user_login,
                    self.user_id,
                )
                return True
            logger.error("Токен невалиден! Статус: %s", resp.status_code)
            return False
        except requests.RequestException as e:
            logger.error("Ошибка валидации токена: %s", e)
            return False

    def get_user_id(self) -> str | None:
        """Get the authenticated user's ID."""
        if self.user_id:
            return self.user_id
        self.validate_token()
        return self.user_id

    def get_channel_id(self, streamer_login: str) -> str | None:
        """Get the channel ID for a streamer by login name."""
        data = {
            "operationName": "ReportMenuItem",
            "variables": {"channelLogin": streamer_login},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "8f3628981255345ca5e5453dfd844efffb01d6b4f84b7631571a2a4f2a636a1e",
                }
            },
        }
        try:
            resp = self._gql_request(data)
            user = resp.get("data", {}).get("user")
            if user:
                return user["id"]
            logger.warning("Стример %s не найден", streamer_login)
            return None
        except Exception:
            return None

    def get_channel_points_context(self, streamer_login: str) -> dict | None:
        """Get channel points context including available claims."""
        data = {
            "operationName": "ChannelPointsContext",
            "variables": {"channelLogin": streamer_login},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9988086babc615a918a1e9a722ff41d98847acac822645209ac7379eecb27152",
                }
            },
        }
        try:
            resp = self._gql_request(data)
            community = resp.get("data", {}).get("community")
            if community is None:
                logger.warning("Канал %s не найден", streamer_login)
                return None
            return community
        except Exception:
            return None

    def check_bonus_available(self, streamer_login: str) -> tuple[str | None, int]:
        """Check if a bonus claim is available. Returns (claim_id, balance)."""
        context = self.get_channel_points_context(streamer_login)
        if context is None:
            return None, 0

        channel = context.get("channel", {})
        self_data = channel.get("self", {})
        cp = self_data.get("communityPoints", {})

        balance = cp.get("balance", 0)
        available_claim = cp.get("availableClaim")

        claim_id = None
        if available_claim is not None:
            claim_id = available_claim.get("id")

        return claim_id, balance

    def claim_bonus(self, channel_id: str, claim_id: str) -> bool:
        """Claim a channel points bonus."""
        data = {
            "operationName": "ClaimCommunityPoints",
            "variables": {
                "input": {
                    "channelID": channel_id,
                    "claimID": claim_id,
                }
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "46aaeebe02c99afdf4fc97c7c0cba964124bf6b0af229395f1f6d1feed05b3d0",
                }
            },
        }
        try:
            resp = self._gql_request(data)
            if "errors" in resp:
                logger.error("Ошибка при клейме бонуса: %s", resp["errors"])
                return False
            claim_data = (
                resp.get("data", {})
                .get("claimCommunityPoints", {})
                .get("claim", {})
            )
            points = claim_data.get("pointsEarnedTotal", "?")
            logger.info("Бонус получен! +%s баллов", points)
            return True
        except Exception as e:
            logger.error("Ошибка при клейме бонуса: %s", e)
            return False

    def is_stream_live(self, streamer_login: str) -> bool:
        """Check if a streamer is currently live."""
        data = {
            "operationName": "WithIsStreamLiveQuery",
            "variables": {"id": streamer_login},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "04e46329a6786ff3a81c01c50bfa5d725902507a0deb83b0edbf7abe7a3716ea",
                }
            },
        }
        try:
            resp = self._gql_request(data)
            user = resp.get("data", {}).get("user")
            if user is None:
                return False
            stream = user.get("stream")
            return stream is not None
        except Exception:
            return False

    def get_stream_info(self, streamer_login: str) -> dict | None:
        """Get stream info (broadcast_id, game, etc.)."""
        data = {
            "operationName": "VideoPlayerStreamInfoOverlayChannel",
            "variables": {"channel": streamer_login},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "a5f2e34d626a9f4f5c0204f910bab2194948a9502089be558bb6e779a9e1b3d2",
                }
            },
        }
        try:
            resp = self._gql_request(data)
            user = resp.get("data", {}).get("user")
            if user and user.get("stream"):
                stream = user["stream"]
                return {
                    "broadcast_id": stream.get("id"),
                    "game": stream.get("game", {}).get("name", "Unknown"),
                    "title": user.get("lastBroadcast", {}).get("title", ""),
                }
            return None
        except Exception:
            return None

    def send_watch_event(self, streamer_login: str, broadcast_id: str) -> bool:
        """Send a minute-watched event to earn passive points."""
        payload = [
            {
                "event": "minute-watched",
                "properties": {
                    "channel_id": self.get_channel_id(streamer_login),
                    "broadcast_id": broadcast_id,
                    "player": "site",
                    "user_id": self.user_id or "",
                },
            }
        ]
        try:
            resp = self.session.post(
                SPADE_URL,
                json=payload,
                timeout=10,
            )
            return resp.status_code == 204 or resp.status_code == 200
        except Exception:
            return False

    def get_followed_streamers(self) -> list[str]:
        """Get the list of followed streamers."""
        if not self.user_id:
            self.validate_token()
        if not self.user_id:
            return []

        data = {
            "operationName": "FollowingLive_CurrentUser",
            "variables": {"limit": 30},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "41bfa15d37b2a14495a655fca4f20d610346bf7e7e1d8c5db4e618a0b2c3b4e4",
                }
            },
        }
        try:
            resp = self._gql_request(data)
            edges = (
                resp.get("data", {})
                .get("currentUser", {})
                .get("followedLiveUsers", {})
                .get("edges", [])
            )
            return [
                edge.get("node", {}).get("login", "")
                for edge in edges
                if edge.get("node", {}).get("login")
            ]
        except Exception:
            return []
