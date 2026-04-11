import requests
from lxml import etree
from datetime import datetime, timedelta
import os
import json
import time

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
# 📥 СУЩЕСТВУЮЩИЕ ТОВАРЫ
# =========================
existing_articles = set()
page = 1

while True:
    response = requests.get(
        "https://blisstech.shop/api/catalog/export/",
        params={"token": token, "page": page}
    )

    data = response.json()
    items = data.get("response", {}).get("items", [])

    if not items:
        break

    for item in items:
        if item.get("article"):
            existing_articles.add(item["article"])

    page += 1

print(f"📦 Товаров найдено: {len(existing_articles)}")

# =========================
# 📅 ДАТА АКЦИИ (до завтра 02:55)
# =========================
now = datetime.now()
sale_date = (now + timedelta(days=1)).replace(
    hour=2, minute=55, second=0, microsecond=0
)
sale_date_str = sale_date.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# XML
# =========================
url = "https://opt-drop.com/storage/xml/opt-drop-20.xml"
response = requests.get(url, timeout=60)

if response.status_code != 200:
    print("❌ Ошибка загрузки XML")
    exit()

root = etree.fromstring(response.content)

# =========================
# 📦 ОБНОВЛЕНИЕ ТОЛЬКО НАЛИЧИЯ + ДАТЫ АКЦИИ
# =========================
products = []

for offer in root.findall('.//offer'):
    try:
        sku = offer.find('vendorCode')
        available = offer.get('available')

        if sku is None or not sku.text:
            continue

        sku = sku.text.strip()

        # только существующие товары
        if sku not in existing_articles:
            continue

        is_available = str(available).lower() == "true"

        product = {
            "article": sku,
            "presence": "В наявності" if is_available else "Немає в наявності"
        }

        # дата/время акции только для наличия
        if is_available:
            product["countdown_end_time"] = sale_date_str

        products.append(product)

    except Exception as e:
        print("Ошибка товара:", e)

print(f"📦 К обновлению: {len(products)}")

# =========================
# 🚀 ОТПРАВКА
# =========================
API_URL = "https://blisstech.shop/api/catalog/import/"
BATCH_SIZE = 300

for i in range(0, len(products), BATCH_SIZE):
    batch = products[i:i + BATCH_SIZE]

    payload = {
        "token": token,
        "products": batch
    }

    try:
        response = requests.post(
            API_URL,
            data=json.dumps(payload, ensure_ascii=False),
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"📤 {i} - {i + len(batch)} | {response.status_code}")

        try:
            print(response.json())
        except:
            print(response.text)

    except Exception as e:
        print("❌ Ошибка:", e)

    time.sleep(1)

print("✅ Готово")
