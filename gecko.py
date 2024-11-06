from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager

options = webdriver.FirefoxOptions()
options.add_argument('-headless')  # Добавление опции headless (без GUI)

# Используйте GeckoDriverManager для установки и получения пути к geckodriver
driver_service = webdriver.firefox.service.Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=driver_service, options=options)

# Ваш код здесь

driver.quit()
