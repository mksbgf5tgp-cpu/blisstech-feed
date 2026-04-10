import requests
from lxml import etree
from datetime import datetime, timedelta
import random
import os

# =========================
# 🔐 АВТОРИЗАЦИЯ
# =========================
auth_response = requests.post(
    "https://blisstech.shop/api/auth/",
    json={
        "login": os.getenv("LOGIN"),
        "password": os.getenv("PASSWORD")
    }
)

data = auth_response.json()
token = data.get("response", {}).get("token")

if not token:
    print("❌ Ошибка авторизации")
    print(auth_response.text)
    exit()

print("✅ Авторизация ок")

# =========================
# XML
# =========================
url = "https://opt-drop.com/storage/xml/opt-drop-20.xml"

response = requests.get(url)

if response.status_code != 200:
    print("❌ Ошибка загрузки XML")
    exit()

parser = etree.XMLParser(recover=True)
root = etree.fromstring(response.content, parser)

# =========================
# дата акции
# =========================
now = datetime.now()
sale_date = now.replace(hour=23, minute=59, second=59, microsecond=0)

if now > sale_date:
    sale_date += timedelta(days=1)

sale_date_str = sale_date.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# собираем товары
# =========================
products = []

for offer in root.findall('.//offer'):
    try:
        sku = offer.find('vendorCode')
        available = offer.get('available')

        if sku is None:
            continue

        sku = sku.text.strip()

        # ✅ ПРАВИЛЬНО ДЛЯ ХОРОШОП
        presence = "В наявності" if str(available).lower() == "true" else "Немає в наявності"

        countdown_text = f"Залишилось товарів по акції: {random.randint(8, 20)}"

        products.append({
            "article": sku,
            "presence": presence,
            "countdown_end_time": sale_date_str,
            "countdown_description": countdown_text
        })

    except Exception as e:
        print("Ошибка товара:", e)
        continue

print(f"📦 Собрано товаров: {len(products)}")

# =========================
# 🚀 ОТПРАВКА В ХОРОШОП
# =========================
payload = {
    "token": token,
    "products": products
}

response = requests.post(
    "https://blisstech.shop/api/catalog/import/",
    json=payload
)

print("STATUS:", response.status_code)
print(response.text)
