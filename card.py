import PyPDF2
import re
import pandas as pd

# Путь к вашему PDF файлу
pdf_path = 'Binder1.pdf'

# Открываем PDF файл
with open(pdf_path, 'rb') as file:
    reader = PyPDF2.PdfReader(file)
    
    # Объединяем текст всех страниц
    text = ''
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text()

# Шаблон для поиска номеров заказов
order_number_pattern = r'39[0-5]\s?\d{3}\s?\d{3}'
# Шаблон для поиска товаров и количества
item_pattern = r'(4YOU.*?)(?=\s*\d{3}\s?\d{3}|\n|$)'
quantity_pattern = r'(\d+)\s*шт\.'

# Находим все вхождения номеров заказов
order_sections = re.split(order_number_pattern, text)[1:]  # Разделяем текст на части по номерам заказов
order_numbers = re.findall(order_number_pattern, text)  # Находим все номера заказов

# Проверяем, чтобы у нас было столько же секций, сколько и номеров заказов
if len(order_sections) != len(order_numbers):
    print("Ошибка: количество секций и номеров заказов не совпадает!")
else:
    # Создаем пустой список для хранения данных
    data = []

    # Заполняем список данных
    for order_number, section in zip(order_numbers, order_sections):
        # Находим все товары в секции
        items = re.findall(item_pattern, section, re.DOTALL)
        for item in items:
            # Очистка текста товара
            item_cleaned = re.sub(r'\s*\.\.\.\.\s*', ' ', item).strip()  # Убираем многоточия
            item_cleaned = re.sub(r'\d+\s*шт\.', '', item_cleaned).strip()  # Убираем количество и единицу измерения
            # Извлекаем количество товаров
            quantity_match = re.search(quantity_pattern, item)
            quantity = quantity_match.group(1) if quantity_match else 'N/A'
            # Фильтруем и добавляем только нужные строки
            if len(item_cleaned) > 0:
                data.append({'Order Number': order_number, 'Item': item_cleaned, 'Quantity': quantity})

    # Создаем DataFrame из списка данных
    df = pd.DataFrame(data)

    # Убираем дубликаты
    df = df.drop_duplicates()

    # Сохраняем DataFrame в Excel файл
    df.to_excel('orders_items.xlsx', index=False, engine='openpyxl')

    print('Данные сохранены в файл orders_items.xlsx')