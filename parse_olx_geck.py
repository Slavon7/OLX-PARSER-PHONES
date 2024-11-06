from seleniumwire.webdriver import Firefox, FirefoxOptions
import atexit
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import sqlite3
import urllib.request, socket

socket.setdefaulttimeout(180)

PROMPT = "https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/lvov/q-власник/?currency=UAH"

# Створюємо підключення до бази даних SQLite
conn = sqlite3.connect("ads.db")
c = conn.cursor()


def exit_handler():
    driver.quit()

atexit.register(exit_handler)

options = FirefoxOptions()
options.add_argument('-headless')

# # Створюємо таблицю
c.execute("""CREATE TABLE IF NOT EXISTS olx (link TEXT, checked INTEGER)""")
c.execute("""CREATE TABLE IF NOT EXISTS ads (ads_id INTEGER, title TEXT, description TEXT, district TEXT, adlink TEXT, name TEXT, phone TEXT)""")

# Створюємо екземпляр браузера
driver = Firefox(options=options)

# Відкриваємо веб-сторінку
driver.get(PROMPT)

new_ads = 0

# Парсимо сторінку з використанням BeautifulSoup
soup = BeautifulSoup(driver.page_source, "html.parser")

# Знаходимо кількість сторінок з оголошеннями
pages = len(soup.find_all("li", class_="pagination-item"))

# Знаходимо всі оголошення на сторінці
ads = soup.select('[data-cy="l-card"]')

# Парсимо дані з кожного оголошення
for ad in ads:
    link = "https://www.olx.ua" + ad.find("a", class_="css-z3gu2d").get("href")

    c.execute("SELECT * FROM olx WHERE link = ?", (link,))
    data = c.fetchone()

    # Якщо запис не існує, зберігаємо його в базі даних
    if data is None:
        c.execute("INSERT INTO olx (link, checked) VALUES ('%s', '%s')" % (link, 0))
        new_ads += 1

print("Page #1 was scrapped!")
# Зберігаємо (комітимо) зміни
conn.commit()

# Парсимо дані з кожної сторінки
for page in range(2, pages + 1):
    # Відкриваємо веб-сторінку
    driver.get(f"{PROMPT}&page={page}")

    # Парсимо сторінку з використанням BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Знаходимо всі оголошення на сторінці
    ads = soup.select('[data-cy="l-card"]')

    # Парсимо дані з кожного оголошення
    for ad in ads:
        link = "https://www.olx.ua" + ad.find("a", class_="css-z3gu2d").get("href")

        c.execute("SELECT * FROM olx WHERE link = ?", (link,))
        data = c.fetchone()

        # Якщо запис не існує, зберігаємо його в базі даних
        if data is None:
            c.execute("INSERT INTO olx (link, checked) VALUES ('%s', '%s')" % (link, 0))
            new_ads += 1

    print(f"Page #{page} was scrapped!")
    # Зберігаємо (комітимо) зміни

    conn.commit()

print(f"New ads: {new_ads}")
conn.close()
# Закриваємо браузер
driver.quit()
