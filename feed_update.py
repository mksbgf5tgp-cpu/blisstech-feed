import requests
from lxml import etree
from datetime import datetime, timedelta
import random
import os
import time
import json
import re

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

response = requests.get(url, timeout=60)

if response.status_code != 200:
    print("❌ Ошибка загрузки XML")
    exit()

parser = etree.XMLParser()
root = etree.fromstring(response.content, parser)

# =========================
# 📂 категории
# =========================
category_map = {}

for cat in root.findall('.//category'):
    if cat.get('id') and cat.text:
        category_map[cat.get('id')] = cat.text.strip()

# =========================
# 📅 дата акции
# =========================
now = datetime.now()
sale_date = (now + timedelta(days=1)).replace(hour=2, minute=55, second=0, microsecond=0)
sale_date_str = sale_date.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# 💰 НАЦЕНКА
# =========================
def apply_markup(price):
    if price <= 107:
        return price * 1.347
    elif price <= 166:
        return price * 1.263
    elif price <= 261:
        return price * 1.179
    elif price <= 356:
        return price * 1.094
    else:
        return price

# =========================
# 🧠 ЧИСТКА HTML (ГЛАВНОЕ)
# =========================
def clean_html(node):
    if node is None:
        return ""

    html = node.text or "".join(node.itertext())
    html = html.strip()

    # убираем CDATA мусор
    html = html.replace("<![CDATA[", "").replace("]]>", "")

    # убираем font/span/style мусор
    html = re.sub(r'<span[^>]*>', '', html)
    html = re.sub(r'</span>', '', html)
    html = re.sub(r'<font[^>]*>', '', html)
    html = re.sub(r'</font>', '', html)
    html = re.sub(r'style="[^"]*"', '', html)

    # фикс изображений
    html = html.replace(
        "<img",
        '<img style="max-width:100%;height:auto;display:block;"'
    )

    return html

# =========================
# 📦 ТОВАРЫ
# =========================
products = []

for offer in root.findall('.//offer'):
    try:
        sku = offer.find('vendorCode')
        name = offer.find('name')

        if sku is None or not sku.text:
            continue
        if name is None or not name.text:
            continue

        sku = sku.text.strip()

        price = offer.find('price')
        description = offer.find('description')
        brand = offer.find('vendor')
        image = offer.find('picture')
        category_id = offer.find('categoryId')
        available = offer.get('available')

        is_available = str(available).lower() == "true"
        presence = "В наявності" if is_available else "Немає в наявності"

        parent_category = category_map.get(category_id.text, "Без категорії") if category_id is not None else "Без категорії"

        base_price = 0
        try:
            if price is not None and price.text:
                base_price = float(price.text.replace(",", "."))
        except:
            base_price = 0

        final_price = apply_markup(base_price)
        final_price = int(final_price) + 0.99
        old_price = final_price * random.uniform(1.3, 1.6)

        product = {
            "article": sku,
            "presence": presence,
            "price": round(final_price, 2),
            "price_old": round(old_price, 2),
        }

        if is_available:
            product["countdown_end_time"] = sale_date_str

        # =========================
        # ОБНОВЛЕНИЕ / НОВЫЙ ТОВАР
        # =========================
        if sku not in existing_articles:

            product.update({
                "title": {
                    "ua": name.text.strip(),
                    "ru": name.text.strip()
                },
                "description": {
                    "ua": clean_html(description),
                    "ru": clean_html(description)
                },
                "brand": brand.text if brand is not None and brand.text else "",
                "currency": "UAH",
                "parent": parent_category,
                "images": {
                    "links": [image.text.strip()] if image is not None and image.text else []
                }
            })
        else:
            # 🔥 существующий товар → только апдейт статуса
            product.update({
                "countdown_end_time": sale_date_str
            })

        products.append(product)

    except Exception as e:
        print("Ошибка товара:", e)
        continue

print(f"📦 Всего товаров: {len(products)}")

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