"""WebSocket client for real-time Twitch community points notifications."""

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone

import websocket

logger = logging.getLogger("twitch_bot")

HERMES_URL = "wss://hermes.twitch.tv/v1"
CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"


class TwitchWebSocketClient:
    """Connects to Twitch Hermes WebSocket for real-time bonus notifications."""

    def __init__(self, auth_token: str, on_bonus_available: callable):
        self.auth_token = auth_token
        self.on_bonus_available = on_bonus_available
        self._ws = None
        self._thread = None
        self._running = False
        self._subscribed_channels = {}
        self._keepalive_thread = None
        self._last_message_time = time.time()
        self._reconnect_delay = 1

    def start(self, channel_ids: dict[str, str]):
        """Start WebSocket connection. channel_ids = {login: channel_id}."""
        self._subscribed_channels = channel_ids
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop WebSocket connection."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    def _run(self):
        """Main WebSocket loop with automatic reconnection."""
        while self._running:
            try:
                self._connect()
            except Exception as e:
                logger.error("WebSocket ошибка: %s", e)

            if self._running:
                delay = min(self._reconnect_delay, 60)
                logger.info(
                    "Переподключение через %d сек...", delay
                )
                time.sleep(delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    def _connect(self):
        """Establish WebSocket connection."""
        url = f"{HERMES_URL}?clientId={CLIENT_ID}"

        self._ws = websocket.WebSocketApp(
            url,
            header={
                "Authorization": f"OAuth {self.auth_token}",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
                ),
            },
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._ws.run_forever(ping_interval=30, ping_timeout=10)

    def _on_open(self, ws):
        """Called when WebSocket connection is established."""
        logger.info("WebSocket подключен к Hermes")
        self._reconnect_delay = 1
        self._last_message_time = time.time()

        for login, channel_id in self._subscribed_channels.items():
            self._subscribe_to_channel(channel_id, login)

    def _subscribe_to_channel(self, channel_id: str, login: str):
        """Subscribe to community points events for a channel."""
        msg = {
            "type": "subscribe",
            "id": str(uuid.uuid4()),
            "subscribe": {
                "id": str(uuid.uuid4()),
                "type": "pubsub",
                "pubsub": {
                    "topic": f"community-points-channel-v1.{channel_id}",
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self._ws.send(json.dumps(msg))
            logger.info(
                "Подписка на баллы канала: %s (ID: %s)", login, channel_id
            )
        except Exception as e:
            logger.error("Ошибка подписки на %s: %s", login, e)

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        self._last_message_time = time.time()

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "keepalive":
            return

        if msg_type == "subscribeResponse":
            result = data.get("subscribeResponse", {}).get("result", "")
            if result == "ok":
                logger.debug("Подписка подтверждена")
            else:
                logger.warning("Ошибка подписки: %s", result)
            return

        if msg_type == "message" or msg_type == "pubsub":
            self._handle_pubsub_message(data)
            return

        # Try to parse nested message data
        if "data" in data:
            nested = data["data"]
            if isinstance(nested, str):
                try:
                    nested = json.loads(nested)
                except json.JSONDecodeError:
                    return
            self._handle_points_event(nested)

    def _handle_pubsub_message(self, data: dict):
        """Handle a PubSub-style message."""
        msg_data = data.get("data", data.get("message", {}))
        if isinstance(msg_data, str):
            try:
                msg_data = json.loads(msg_data)
            except json.JSONDecodeError:
                return

        # Could be nested in "message" field
        if "message" in msg_data:
            inner = msg_data["message"]
            if isinstance(inner, str):
                try:
                    inner = json.loads(inner)
                except json.JSONDecodeError:
                    return
                msg_data = inner

        self._handle_points_event(msg_data)

    def _handle_points_event(self, data: dict):
        """Handle community points events."""
        event_type = data.get("type", "")

        if event_type == "claim-available":
            claim_data = data.get("data", {}).get("claim", {})
            claim_id = claim_data.get("id")
            channel_id = claim_data.get("channel_id")
            if claim_id and channel_id:
                logger.info(
                    "Бонус доступен! Канал ID: %s, Claim ID: %s",
                    channel_id,
                    claim_id,
                )
                self.on_bonus_available(channel_id, claim_id)
            return

        if event_type == "claim-claimed":
            points = (
                data.get("data", {})
                .get("claim", {})
                .get("point_gain", {})
                .get("total_points", "?")
            )
            logger.info("Бонус забран через WebSocket: +%s", points)
            return

        if event_type in ("points-earned", "balance-updated"):
            balance = data.get("data", {}).get("balance", {})
            if balance:
                channel_id = balance.get("channel_id", "?")
                current = balance.get("balance", "?")
                logger.debug(
                    "Баланс обновлён (канал %s): %s", channel_id, current
                )

    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error("WebSocket ошибка: %s", error)

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.info(
            "WebSocket отключен (код: %s, сообщение: %s)",
            close_status_code,
            close_msg,
        )
