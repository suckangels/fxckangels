# Twitch Channel Points Bot

Бот для автоматического сбора бесплатных баллов канала (Channel Points) на Twitch.

## Что делает бот

- **Автоматически забирает бонусные баллы** — ту самую зелёную кнопку "+50", которая появляется при просмотре стрима
- **Эмулирует просмотр стрима** — отправляет события "minute-watched" для пассивного заработка баллов
- **Отслеживает несколько стримеров** — можно добавить любое количество каналов
- **Работает в фоне** — запустил и забыл
- **Два режима обнаружения бонусов**:
  - Через WebSocket (Hermes API) — мгновенное обнаружение
  - Через GQL polling — резервный способ, проверяет каждые N секунд

## Установка

### 1. Установить Python 3.10+

```bash
python3 --version  # Проверить версию
```

### 2. Установить зависимости

```bash
cd twitch-points-bot
pip install -r requirements.txt
```

### 3. Получить auth token

Для работы бота нужен ваш auth token от Twitch. Как его получить:

1. Откройте [twitch.tv](https://twitch.tv) в браузере
2. Залогиньтесь в свой аккаунт
3. Откройте DevTools (F12) → Application → Cookies → `https://www.twitch.tv`
4. Найдите cookie с именем `auth-token`
5. Скопируйте его значение

> ⚠️ **Важно:** Никому не передавайте свой auth token! Он даёт полный доступ к вашему аккаунту.

### 4. Настроить конфиг

Отредактируйте файл `config.json`:

```json
{
    "auth_token": "ваш_токен_сюда",
    "streamers": [
        "streamer1",
        "streamer2",
        "streamer3"
    ],
    "check_interval_seconds": 60,
    "claim_bonus": true,
    "follow_raids": true,
    "watch_streak": true
}
```

**Параметры:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `auth_token` | Ваш auth token от Twitch | — |
| `streamers` | Список логинов стримеров для отслеживания | `[]` |
| `check_interval_seconds` | Интервал проверки бонусов (в секундах) | `60` |
| `claim_bonus` | Забирать бонусные баллы | `true` |
| `follow_raids` | Следовать за рейдами | `true` |
| `watch_streak` | Отслеживать серии просмотров | `true` |
| `log_level` | Уровень логирования (DEBUG, INFO, WARNING) | `INFO` |

### 5. Запуск

```bash
python3 bot.py
```

Или с кастомным конфигом:

```bash
python3 bot.py /путь/к/config.json
```

## Переменные окружения

Вместо конфига можно использовать переменные окружения:

```bash
export TWITCH_AUTH_TOKEN="ваш_токен"
export TWITCH_STREAMERS="streamer1,streamer2,streamer3"
export TWITCH_CHECK_INTERVAL="60"

python3 bot.py
```

> Переменные окружения имеют приоритет над значениями из config.json.

## Как это работает

```
┌─────────────────────────────────────────────────┐
│                  Twitch Bot                      │
│                                                  │
│  ┌──────────────┐     ┌──────────────────────┐  │
│  │  WebSocket    │     │    GQL Polling        │  │
│  │  (Hermes)     │     │    (каждые N сек)     │  │
│  │              │     │                       │  │
│  │  Мгновенное  │     │  Резервная проверка   │  │
│  │  обнаружение │     │  бонусов              │  │
│  └──────┬───────┘     └──────────┬────────────┘  │
│         │                        │               │
│         └────────┬───────────────┘               │
│                  ▼                                │
│         ┌────────────────┐                       │
│         │ ClaimBonus     │                       │
│         │ (GQL Mutation) │                       │
│         └────────────────┘                       │
│                                                  │
│  + Эмуляция просмотра (minute-watched events)   │
└─────────────────────────────────────────────────┘
```

1. **WebSocket (Hermes)** — подключается к Twitch WebSocket и подписывается на события `community-points-channel-v1` для каждого стримера. Когда бонус становится доступен, мгновенно его забирает.

2. **GQL Polling** — каждые N секунд проверяет через GraphQL API, есть ли доступный бонус. Это резервный механизм на случай, если WebSocket пропустит событие.

3. **Minute-watched** — каждую минуту отправляет событие просмотра для онлайн-стримов, чтобы пассивно зарабатывать баллы.

## Логи

Логи записываются в папку `logs/` и выводятся в консоль. Пример:

```
2024-01-15 12:00:00 [INFO] Токен валиден. Пользователь: myuser (ID: 123456)
2024-01-15 12:00:01 [INFO]   ✓ streamer1 (ID: 789012)
2024-01-15 12:00:01 [INFO]   ✓ streamer2 (ID: 345678)
2024-01-15 12:00:02 [INFO] 🟢 streamer1 в эфире! Игра: Just Chatting
2024-01-15 12:00:02 [INFO] 🎁 Бонус найден на канале streamer1! Забираем...
2024-01-15 12:00:02 [INFO] Бонус получен! +50 баллов
2024-01-15 12:00:02 [INFO] 📊 Статус | Время работы: 0:05:00 | Бонусов забрано: 3 | ~Баллов: 150
```

## Запуск в фоне (Linux)

### С помощью screen:

```bash
screen -S twitch-bot
python3 bot.py
# Ctrl+A, D — отсоединиться
# screen -r twitch-bot — подключиться обратно
```

### С помощью systemd:

Создайте файл `/etc/systemd/system/twitch-bot.service`:

```ini
[Unit]
Description=Twitch Channel Points Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/twitch-points-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable twitch-bot
sudo systemctl start twitch-bot
sudo systemctl status twitch-bot
```

## FAQ

**Q: Это безопасно?**
A: Бот использует те же API, что и веб-клиент Twitch. Риск бана минимален, но используйте на свой страх и риск.

**Q: Токен перестал работать?**
A: Токены Twitch истекают. Получите новый токен через DevTools браузера.

**Q: Можно ли запустить несколько экземпляров?**
A: Да, но лучше использовать один экземпляр с несколькими стримерами в конфиге.
