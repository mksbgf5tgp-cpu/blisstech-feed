import requests
from lxml import etree
from datetime import datetime, timedelta
import random
import os
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

print(f"📦 Уже есть товаров: {len(existing_articles)}")

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
# 📂 категории из XML
# =========================
category_map = {}

for cat in root.findall('.//category'):
    cat_id = cat.get('id')
    cat_name = cat.text

    if cat_id and cat_name:
        category_map[cat_id] = cat_name.strip()

# =========================
# дата акции
# =========================
now = datetime.now()
sale_date = now.replace(hour=23, minute=59, second=59, microsecond=0)

if now > sale_date:
    sale_date += timedelta(days=1)

sale_date_str = sale_date.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# товары
# =========================
products = []

for offer in root.findall('.//offer'):
    try:
        sku = offer.find('vendorCode')
        name = offer.find('name')
        description = offer.find('description')
        price = offer.find('price')
        brand = offer.find('vendor')
        image = offer.find('picture')
        category_id = offer.find('categoryId')
        available = offer.get('available')

        if sku is None or name is None:
            continue

        sku = sku.text.strip()
        is_new = sku not in existing_articles

        is_available = str(available).lower() == "true"
        presence = "В наявності" if is_available else "Немає в наявності"

        # категория
        if category_id is not None:
            parent_category = category_map.get(category_id.text, "Без категорії")
        else:
            parent_category = "Без категорії"

        product = {
            "article": sku,
            "presence": presence
        }

        # дата акции только для товаров в наличии
        if is_available:
            product["countdown_end_time"] = sale_date_str

        # 🆕 новые товары
        if is_new:
            base_price = float(price.text) if price is not None and price.text else 0
            old_price = base_price * random.uniform(1.3, 1.6)

            image_url = image.text if image is not None else ""
            desc_text = description.text if description is not None else ""

            product.update({
                "title": {
                    "ua": name.text.strip(),
                    "ru": name.text.strip()
                },
                "description": {
                    "ua": desc_text,
                    "ru": desc_text
                },
                "price": round(base_price, 2),
                "price_old": round(old_price, 2),
                "brand": brand.text if brand is not None else "",
                "currency": "UAH",
                "parent": parent_category,
                "images": {
                    "links": [image_url] if image_url else []
                }
            })

        products.append(product)

    except Exception as e:
        print("Ошибка товара:", e)
        continue

print(f"📦 Всего на отправку: {len(products)}")

# =========================
# 🚀 ОТПРАВКА БАТЧАМИ
# =========================
API_URL = "https://blisstech.shop/api/catalog/import/"
BATCH_SIZE = 100

for i in range(0, len(products), BATCH_SIZE):
    batch = products[i:i + BATCH_SIZE]

    payload = {
        "token": token,
        "products": batch
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=30)

        print(f"📤 Отправка {i} - {i + len(batch)}")
        print("STATUS:", response.status_code)

        try:
            print(response.json())
        except:
            print(response.text)

    except Exception as e:
        print("❌ Ошибка отправки:", e)

    time.sleep(1)

print("✅ Готово")
