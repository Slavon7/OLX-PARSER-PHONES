import os
import subprocess
import time

proxy_count = 0
request_count = 0
request_limit = 5

with open("proxies.txt", "r") as proxy_file:
    proxies = proxy_file.read().splitlines()

def get_next_proxy():
    global proxy_count
    if proxy_count >= len(proxies):
        proxy_count = 0
    proxy = proxies[proxy_count]
    proxy_count += 1
    return proxy

while True:
    proxy = get_next_proxy()
    os.environ["CURRENT_PROXY"] = f"http://{proxy}"
    print(f"Смена прокси. Новый прокси: {proxy}")

    # Запуск основного скрипта
    process = subprocess.Popen(["python", "parse_ads_geck.py"])

    # Ожидание завершения или завершение после request_limit запросов
    time.sleep(20)  # Ожидание 20 секунд перед перезапуском

    # Завершаем процесс принудительно
    process.terminate()
    process.wait()  # Ожидание завершения процесса

    request_count += 1
    if request_count >= request_limit:
        request_count = 0
        print("Перезапуск с новым прокси...")
