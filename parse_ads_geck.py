from seleniumwire.webdriver import Firefox, FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import aiosqlite
import asyncio
import time
import re
import socket

socket.setdefaulttimeout(180)

ukr_months = {
    1: "січня",
    2: "лютого",
    3: "березня",
    4: "квітня",
    5: "травня",
    6: "червня",
    7: "липня",
    8: "серпня",
    9: "вересня",
    10: "жовтня",
    11: "листопада",
    12: "грудня",
}
date_format = "%d %m %y р."

proxy_count = 0
request_count = 0
request_limit = 25  # Request count 

# Прочитайте список прокси из файла, если файл существует
try:
    with open("proxies.txt", "r") as proxy_file:
        proxies = proxy_file.read().splitlines()
except FileNotFoundError:
    proxies = []

def get_next_proxy():
    global proxy_count
    if not proxies:
        return None
    if proxy_count >= len(proxies):
        proxy_count = 0
    proxy = proxies[proxy_count]
    proxy_count += 1
    return proxy

def clear_session(driver):
    driver.execute_script('window.localStorage.clear(); window.sessionStorage.clear();')
    driver.delete_all_cookies()

def create_driver(proxy_url=None):
    options = FirefoxOptions()
    options.add_argument('-headless')
    options.add_argument('-safe-mode')
    seleniumwire_options = {}

    if proxy_url:
        seleniumwire_options = {
            'proxy': {
                'http': proxy_url,
                'https': proxy_url,
                'no_proxy': 'localhost,127.0.0.1'
            }
        }
    return Firefox(options=options, seleniumwire_options=seleniumwire_options)

async def main() -> None:
    global request_count

    while True:
        conn = await aiosqlite.connect("ads.db", timeout=10)
        c = await conn.cursor()
        
        initial_proxy = get_next_proxy()
        proxy_url = f"http://{initial_proxy}" if initial_proxy else None

        if proxy_url:
            print(f"Используем прокси: {proxy_url}")
        else:
            print("Используем без прокси")

        driver = create_driver(proxy_url)

        await c.execute("SELECT * FROM olx")
        parsed_links = await c.fetchall()
        await conn.close()

        for lnk in parsed_links:
            if lnk[1]:
                continue

            conn = await aiosqlite.connect("ads.db", timeout=10)
            c = await conn.cursor()
            await c.execute("SELECT * FROM ads WHERE adlink = ?", (lnk[0],))
            data = await c.fetchone()
            if data is not None:
                continue

            print(f"\n{'='*100}")
            print(f"🔎 {lnk[0]}\n")
            driver.get(lnk[0])
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "html")))
            except TimeoutException:
                print("🤬 Сторінка оголошення не зʼявилась протягом 10 секунд")

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Дополнительная обработка ошибок и сетевых проблем
            if soup.find(class_="fc-dialog-overlay") is not None:
                try:
                    accept_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'fc-primary-button')))
                    accept_btn.click()
                except Exception as e:
                    print(f"Could not interact with the fc consent overlay: {e}")
            if soup.select_one('[data-testid="cookies-overlay__container"]') is not None:
                try:
                    cookie_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="dismiss-cookies-banner"]')))
                    cookie_button.click()
                except Exception as e:
                    print(f"Could not interact with the cookie consent overlay: {e}")

            # Проверка на неактивное объявление
            if (soup.select_one('[data-testid="ad-inactive-msg"]') is not None or
                soup.find(class_="c-container") is not None or
                soup.select_one('[data-cy="404-page"]') is not None):
                await c.execute("DELETE FROM olx WHERE link = ?", (lnk[0],))
                await c.execute("DELETE FROM ads WHERE adlink = ?", (lnk[0],))
                await conn.commit()
                print("❌ Неактивне оголошення було видалено")
                continue

            if (soup.select_one('[data-testid="prompt-box"]') is not None or
                soup.find(class_="css-83zqsy") is not None or
                soup.select_one('[data-testid="loader"]') is not None):
                log_box_err = soup.select_one('[data-testid="prompt-box"]') is not None
                infinity_load = soup.select_one('[data-testid="loader"]') is not None
                realtor_ads = soup.find(class_="css-83zqsy") is not None

                print(f"Login Box Error: {'❌' if log_box_err else ''}")
                print(f"Realtor Ads: {'❌' if realtor_ads else ''}")
                print(f"Infinity Loading: {'❌' if infinity_load else ''}")

                if realtor_ads:
                    await c.execute("UPDATE olx SET checked = ? WHERE link = ?", (1, lnk[0]))

                await conn.commit()
                await conn.close()
                clear_session(driver)
                continue

            try:
                button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-cy="ad-contact-phone"]')))
                button.click()
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                if(soup.select_one('[title="reCAPTCHA"]') is not None or
                   soup.select_one('[role="alert"]') is not None or
                   soup.select_one('[data-cy="ad-contact-phone"]') is None):
                    no_btn = soup.select_one('[data-cy="ad-contact-phone"]') is None
                    recapcha = soup.select_one('[title="reCAPTCHA"]') is not None
                    ip_ban = soup.select_one('[role="alert"]') is not None
                    if ip_ban and proxies:
                        next_proxy = get_next_proxy()
                        proxy_host, proxy_port = next_proxy.split(":")[2], next_proxy.split(":")[3]
                        proxy_user, proxy_pass = next_proxy.split(":")[0], next_proxy.split(":")[1]
                        proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
                        driver.quit()
                        driver = create_driver(proxy_url)
                        clear_session(driver)

                    print(f"No Phone Button:: {'❌' if no_btn else ''}")
                    print(f"ReCapcha Box: {'❌' if recapcha else ''}")
                    print(f"IP Ban: {'❌' if ip_ban else ''}")

                    # Удалить запись, если кнопка телефона отсутствует
                    if no_btn:
                        await c.execute("DELETE FROM olx WHERE link = ?", (lnk[0],))
                        print("❌ Запись была удалена из-за отсутствия кнопки телефона")

                    await conn.commit()
                    await conn.close()
                    continue

                if (soup.select_one('[data-cy="ad-contact-phone"]').text.strip() == "Показати телефон"):
                    button.click()
                    time.sleep(5)

                soup = BeautifulSoup(driver.page_source, "html.parser")

                if (soup.select_one('[data-cy="ad-contact-phone"]').text.strip() == "Показати телефон"):
                    continue

                id_ = int(re.sub(r"[^0-9\.]", "", soup.find("span", class_="css-12hdxwj").text.strip()))
                title = soup.find("h4", class_="css-1juynto").text.strip()
                district = soup.find("p", class_="css-1cju8pu").text.strip()
                description = soup.find(class_="css-1t507yq").text.strip()
                adlink = lnk[0]
                name = soup.find("h4", class_="css-1lcz6o7").text.strip()
                phone = soup.select_one('[data-cy="ad-contact-phone"]').text.strip()

                print(title)
                print(district)
                print(name)
                print(phone)

                await c.execute("SELECT * FROM ads WHERE ads_id = ?", (id_,))
                data = await c.fetchone()
                if data is None:
                    await c.execute("INSERT INTO ads VALUES (?,?,?,?,?,?,?)", (id_, title, description, district, adlink, name, phone,))
                    await c.execute("UPDATE olx SET checked = ? WHERE link = ?", (1, adlink))
                    print(f"\n✅ ID:{id_} додано до БД.\n")

                await conn.commit()
                await conn.close()
                clear_session(driver)
            except Exception as e:
                await conn.close()
                clear_session(driver)
                print(f"Could not interact with the phone button: {e}")
            finally:
                clear_session(driver)

            request_count += 1

            # Проверка и смена прокси после определённого количества запросов
            if request_count >= request_limit:
                request_count = 0
                driver.quit()
                break

        driver.quit()

if __name__ == "__main__":
    asyncio.run(main())