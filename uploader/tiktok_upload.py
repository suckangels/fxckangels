"""
TikTok upload module.
Uses Selenium to automate TikTok uploads via the web interface.
Requires cookies from a logged-in TikTok session.
"""

import os
import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

COOKIES_FILE = "tiktok_cookies.json"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/upload"


def save_cookies(driver, path: str):
    """Save browser cookies to a JSON file."""
    cookies = driver.get_cookies()
    with open(path, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"  [TikTok] Куки сохранены в {path}")


def load_cookies(driver, path: str):
    """Load cookies from a JSON file into the browser."""
    if not os.path.exists(path):
        return False
    with open(path, "r") as f:
        cookies = json.load(f)
    driver.get("https://www.tiktok.com")
    time.sleep(2)
    for cookie in cookies:
        cookie.pop("sameSite", None)
        cookie.pop("expiry", None)
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass
    return True


def create_driver(headless: bool = False) -> webdriver.Chrome:
    """Create and return a Chrome WebDriver instance."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def tiktok_login(cookies_path: str):
    """
    Interactive TikTok login.
    Opens browser for manual login, then saves cookies.
    """
    print("\n  [TikTok] Открываю браузер для авторизации...")
    print("  [TikTok] Войди в свой аккаунт TikTok в открывшемся окне.")
    print("  [TikTok] После входа нажми Enter в консоли.\n")

    driver = create_driver(headless=False)
    try:
        driver.get("https://www.tiktok.com/login")
        input("  >>> Нажми Enter после входа в TikTok... ")
        save_cookies(driver, cookies_path)
        print("  [TikTok] Авторизация завершена!")
    finally:
        driver.quit()


def upload_single_video(driver, file_path: str, title: str, wait_timeout: int = 60) -> bool:
    """
    Upload a single video to TikTok via the web interface.

    Returns True on success, False on failure.
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        print(f"  [TikTok] Файл не найден: {abs_path}")
        return False

    print(f"  [TikTok] Загрузка: {title}")

    try:
        driver.get(TIKTOK_UPLOAD_URL)
        time.sleep(5)

        # Find the file input and upload
        file_input = WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
        )
        file_input.send_keys(abs_path)
        print("  [TikTok] Файл отправлен, ожидание обработки...")
        time.sleep(10)

        # Clear existing text and type the title
        caption_selectors = [
            '[data-text="true"]',
            '.public-DraftEditor-content',
            '[contenteditable="true"]',
            '.caption-editor',
            '.notranslate',
        ]

        caption_el = None
        for selector in caption_selectors:
            try:
                caption_el = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if caption_el:
                    break
            except TimeoutException:
                continue

        if caption_el:
            caption_el.click()
            time.sleep(0.5)
            # Select all and replace
            from selenium.webdriver.common.keys import Keys
            caption_el.send_keys(Keys.CONTROL, "a")
            time.sleep(0.3)
            caption_el.send_keys(title)
            print(f"  [TikTok] Название установлено: {title}")
        else:
            print("  [TikTok] Не удалось найти поле для названия, загрузка без названия")

        # Wait for video to process
        time.sleep(15)

        # Click the Post button
        post_selectors = [
            'button[data-e2e="post-button"]',
            '//button[contains(text(), "Post")]',
            '//button[contains(text(), "Опубликовать")]',
        ]

        posted = False
        for selector in post_selectors:
            try:
                if selector.startswith("//"):
                    btn = driver.find_element(By.XPATH, selector)
                else:
                    btn = driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                posted = True
                print("  [TikTok] Кнопка 'Опубликовать' нажата")
                break
            except Exception:
                continue

        if not posted:
            # Fallback: try finding any button with "Post" text
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                text = btn.text.strip().lower()
                if text in ("post", "опубликовать", "publish"):
                    btn.click()
                    posted = True
                    print("  [TikTok] Кнопка публикации найдена и нажата")
                    break

        if not posted:
            print("  [TikTok] ВНИМАНИЕ: Не удалось найти кнопку публикации")
            return False

        # Wait for upload to complete
        time.sleep(20)
        print(f"  [TikTok] Готово! Видео '{title}' загружено")
        return True

    except Exception as e:
        print(f"  [TikTok] ОШИБКА: {e}")
        return False


def tiktok_upload_clips(clips: list, config: dict) -> list:
    """
    Upload multiple clips to TikTok.

    clips: list of dicts with keys: file, title
    config: global config dict with tiktok settings

    Returns list of results.
    """
    tt_config = config.get("tiktok", {})
    cookies_path = tt_config.get("cookies_file", COOKIES_FILE)
    headless = tt_config.get("headless", False)

    if not os.path.exists(cookies_path):
        print("\n  [TikTok] Куки не найдены. Нужна авторизация.")
        tiktok_login(cookies_path)

    driver = create_driver(headless=headless)
    results = []

    try:
        loaded = load_cookies(driver, cookies_path)
        if not loaded:
            print("  [TikTok] Не удалось загрузить куки")
            return results

        driver.refresh()
        time.sleep(3)

        for clip in clips:
            success = upload_single_video(driver, clip["file"], clip["title"])
            results.append({
                "file": clip["file"],
                "title": clip["title"],
                "status": "ok" if success else "error",
            })
            time.sleep(5)  # pause between uploads

    finally:
        driver.quit()

    return results
