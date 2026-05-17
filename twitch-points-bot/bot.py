#!/usr/bin/env python3
"""
Twitch Channel Points Auto-Claim Bot

Автоматически собирает бесплатные баллы канала (Channel Points) на Twitch.
Подключается к стримам, отслеживает появление бонусов и забирает их.
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from twitch_api import TwitchAPI
from websocket_client import TwitchWebSocketClient

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging."""
    logger = logging.getLogger("twitch_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(console_handler)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / f"bot_{datetime.now():%Y%m%d}.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)

    return logger


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from file or environment variables."""
    config = {
        "auth_token": "",
        "streamers": [],
        "check_interval_seconds": 60,
        "claim_bonus": True,
        "follow_raids": True,
        "watch_streak": True,
        "log_level": "INFO",
    }

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            file_config = json.load(f)
            config.update(file_config)

    env_token = os.environ.get("TWITCH_AUTH_TOKEN")
    if env_token:
        config["auth_token"] = env_token

    env_streamers = os.environ.get("TWITCH_STREAMERS")
    if env_streamers:
        config["streamers"] = [s.strip() for s in env_streamers.split(",")]

    env_interval = os.environ.get("TWITCH_CHECK_INTERVAL")
    if env_interval:
        config["check_interval_seconds"] = int(env_interval)

    return config


class TwitchPointsBot:
    """Main bot class that orchestrates channel points collection."""

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger("twitch_bot")
        self.api = TwitchAPI(config["auth_token"])
        self.ws_client = None
        self.running = False
        self.channel_ids: dict[str, str] = {}  # login -> channel_id
        self.balances: dict[str, int] = {}  # login -> balance
        self.stream_info: dict[str, dict] = {}  # login -> stream info
        self.last_watch_event: dict[str, float] = {}  # login -> timestamp
        self.claims_total = 0
        self.points_earned = 0
        self.start_time = None

    def start(self):
        """Start the bot."""
        self.running = True
        self.start_time = datetime.now()

        self.logger.info("=" * 50)
        self.logger.info("  Twitch Channel Points Bot")
        self.logger.info("=" * 50)

        # Validate token
        if not self.api.validate_token():
            self.logger.error(
                "Не удалось авторизоваться. Проверьте auth_token в config.json"
            )
            sys.exit(1)

        # Resolve channel IDs
        streamers = self.config["streamers"]
        if not streamers:
            self.logger.error(
                "Список стримеров пуст! Добавьте стримеров в config.json"
            )
            sys.exit(1)

        self.logger.info("Стримеры для отслеживания: %s", ", ".join(streamers))

        for login in streamers:
            login = login.lower().strip()
            channel_id = self.api.get_channel_id(login)
            if channel_id:
                self.channel_ids[login] = channel_id
                self.logger.info("  ✓ %s (ID: %s)", login, channel_id)
            else:
                self.logger.warning("  ✗ %s — не найден", login)

        if not self.channel_ids:
            self.logger.error("Ни один стример не найден!")
            sys.exit(1)

        # Start WebSocket for real-time notifications
        self._start_websocket()

        # Main polling loop
        self._main_loop()

    def _start_websocket(self):
        """Start WebSocket client for real-time bonus detection."""
        try:
            self.ws_client = TwitchWebSocketClient(
                self.config["auth_token"],
                on_bonus_available=self._on_bonus_from_ws,
            )
            self.ws_client.start(self.channel_ids)
            self.logger.info("WebSocket клиент запущен")
        except Exception as e:
            self.logger.warning(
                "Не удалось запустить WebSocket: %s. "
                "Будет использоваться только GQL polling.",
                e,
            )

    def _on_bonus_from_ws(self, channel_id: str, claim_id: str):
        """Handle bonus detected via WebSocket."""
        login = None
        for l, cid in self.channel_ids.items():
            if cid == channel_id:
                login = l
                break

        if login:
            self.logger.info(
                "⚡ Бонус обнаружен через WebSocket: %s", login
            )
        else:
            self.logger.info(
                "⚡ Бонус обнаружен через WebSocket: канал ID %s", channel_id
            )

        if self.config.get("claim_bonus", True):
            success = self.api.claim_bonus(channel_id, claim_id)
            if success:
                self.claims_total += 1
                self.points_earned += 50

    def _main_loop(self):
        """Main polling loop."""
        interval = self.config.get("check_interval_seconds", 60)
        self.logger.info(
            "Запуск основного цикла (интервал: %d сек)", interval
        )

        while self.running:
            try:
                self._check_all_channels()
                self._send_watch_events()
                self._print_status()
                time.sleep(interval)
            except KeyboardInterrupt:
                self.logger.info("Остановка по Ctrl+C...")
                self.stop()
                break
            except Exception as e:
                self.logger.error("Ошибка в основном цикле: %s", e)
                time.sleep(10)

    def _check_all_channels(self):
        """Check all channels for available bonuses."""
        for login, channel_id in self.channel_ids.items():
            try:
                # Check if stream is live
                info = self.api.get_stream_info(login)
                if info:
                    if login not in self.stream_info:
                        self.logger.info(
                            "🟢 %s в эфире! Игра: %s",
                            login,
                            info.get("game", "?"),
                        )
                    self.stream_info[login] = info
                else:
                    if login in self.stream_info:
                        self.logger.info("🔴 %s оффлайн", login)
                        del self.stream_info[login]
                    continue

                # Check for bonus
                claim_id, balance = self.api.check_bonus_available(login)
                self.balances[login] = balance

                if claim_id and self.config.get("claim_bonus", True):
                    self.logger.info(
                        "🎁 Бонус найден на канале %s! Забираем...", login
                    )
                    success = self.api.claim_bonus(channel_id, claim_id)
                    if success:
                        self.claims_total += 1
                        self.points_earned += 50

            except Exception as e:
                self.logger.error(
                    "Ошибка при проверке %s: %s", login, e
                )

    def _send_watch_events(self):
        """Send minute-watched events for live streams."""
        now = time.time()
        for login, info in self.stream_info.items():
            last_sent = self.last_watch_event.get(login, 0)
            if now - last_sent >= 60:
                broadcast_id = info.get("broadcast_id", "")
                if broadcast_id:
                    success = self.api.send_watch_event(login, broadcast_id)
                    if success:
                        self.last_watch_event[login] = now
                        self.logger.debug("Минута просмотра отправлена: %s", login)

    def _print_status(self):
        """Print current status summary."""
        live = [l for l in self.channel_ids if l in self.stream_info]
        offline = [l for l in self.channel_ids if l not in self.stream_info]

        uptime = datetime.now() - self.start_time if self.start_time else None
        uptime_str = str(uptime).split(".")[0] if uptime else "?"

        self.logger.info(
            "📊 Статус | Время работы: %s | Бонусов забрано: %d | "
            "~Баллов: %d | Онлайн: %d | Оффлайн: %d",
            uptime_str,
            self.claims_total,
            self.points_earned,
            len(live),
            len(offline),
        )

        if live:
            for login in live:
                balance = self.balances.get(login, "?")
                game = self.stream_info.get(login, {}).get("game", "?")
                self.logger.info(
                    "  🟢 %s — %s баллов — %s", login, balance, game
                )

    def stop(self):
        """Stop the bot gracefully."""
        self.running = False
        if self.ws_client:
            self.ws_client.stop()
        self.logger.info(
            "Бот остановлен. Всего бонусов забрано: %d, ~Баллов заработано: %d",
            self.claims_total,
            self.points_earned,
        )


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    config = load_config(config_path)
    logger = setup_logging(config.get("log_level", "INFO"))

    bot = TwitchPointsBot(config)

    def signal_handler(sig, frame):
        logger.info("Получен сигнал остановки")
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bot.start()


if __name__ == "__main__":
    main()
