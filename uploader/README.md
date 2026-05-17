# Clip Uploader — Загрузка клипов на YouTube и TikTok

Скрипт для автоматической загрузки видеоклипов на YouTube и TikTok.

## Установка

```bash
cd uploader
pip install -r requirements.txt
```

## Подготовка

### 1. Положи клипы в папку `clips/`

```
clips/
  clip1.mp4
  clip2.mp4
  clip3.mp4
  clip4.mp4
  clip5.mp4
```

### 2. Создай `config.json`

Скопируй пример и отредактируй названия:

```bash
cp config.example.json config.json
```

Открой `config.json` и впиши свои названия для каждого клипа:

```json
{
  "clips": [
    { "file": "clip1.mp4", "title": "Мой первый клип", "description": "Описание" },
    { "file": "clip2.mp4", "title": "Второй клип", "description": "Описание" },
    ...
  ]
}
```

### 3. Настрой YouTube (Google API)

1. Перейди в [Google Cloud Console](https://console.cloud.google.com/)
2. Создай проект (или выбери существующий)
3. Включи **YouTube Data API v3** в разделе APIs & Services → Library
4. Создай **OAuth 2.0 Client ID** в разделе APIs & Services → Credentials:
   - Тип: Desktop application
   - Скачай JSON-файл
5. Переименуй скачанный файл в `client_secrets.json` и положи в папку `uploader/`

### 4. Настрой TikTok

Авторизация через куки браузера:

```bash
python upload.py --login tiktok
```

Откроется браузер — войди в свой аккаунт TikTok, затем нажми Enter в консоли.
Куки сохранятся в `tiktok_cookies.json`.

## Использование

### Авторизация

```bash
# Авторизация YouTube (откроется браузер для OAuth)
python upload.py --login youtube

# Авторизация TikTok (откроется браузер для входа)
python upload.py --login tiktok
```

### Загрузка клипов

```bash
# Загрузить на ОБЕ платформы
python upload.py

# Только YouTube
python upload.py --platform youtube

# Только TikTok
python upload.py --platform tiktok

# Свой файл конфига
python upload.py --config my_config.json
```

## Структура файлов

```
uploader/
├── clips/                  # Папка с видеоклипами
│   ├── clip1.mp4
│   ├── clip2.mp4
│   ├── clip3.mp4
│   ├── clip4.mp4
│   └── clip5.mp4
├── config.json             # Конфиг с названиями клипов (создай из примера)
├── config.example.json     # Пример конфига
├── upload.py               # Главный скрипт
├── youtube_upload.py       # Модуль загрузки на YouTube
├── tiktok_upload.py        # Модуль загрузки на TikTok
├── requirements.txt        # Зависимости Python
├── client_secrets.json     # OAuth ключи Google (создай сам)
├── youtube_token.json      # Токен YouTube (создаётся автоматически)
└── tiktok_cookies.json     # Куки TikTok (создаётся автоматически)
```

## Важно

- Файлы `client_secrets.json`, `youtube_token.json`, `tiktok_cookies.json` и `config.json` содержат приватные данные и НЕ коммитятся в git
- YouTube API имеет лимит на количество загрузок в день (обычно ~6 видео)
- TikTok может блокировать автоматические загрузки — если не работает, попробуй обновить куки
