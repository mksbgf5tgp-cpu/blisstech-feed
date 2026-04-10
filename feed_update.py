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

        # акция
        random_qty = random.randint(8, 20)

        countdown_html = f"""
<div style="max-width:320px;margin:10px auto 0;padding:10px 14px;font-family:'Rubik',Arial,sans-serif;background:rgba(254,155,54,0.08);border-radius:10px;display:inline-block;">
<span style="font-size:14px;color:#444;">🔥 Залишилось товарів по акції:</span>
<span style="font-size:20px;font-weight:700;color:#FE9B36;margin-left:6px;"> {random_qty} шт.</span>
</div>
"""

        product = {
            "article": sku,
            "presence": presence,
            "countdown_end_time": sale_date_str
        }

        # акция только для наличия
        if is_available:
            product["countdown_description"] = {
                "ua": countdown_html,
                "ru": countdown_html
            }

        # =========================
        # 🆕 НОВЫЕ ТОВАРЫ
        # =========================
        if is_new:
            base_price = float(price.text) if price is not None else 0

            # 🔥 старая цена +30–60%
            old_price = base_price * random.uniform(1.3, 1.6)

            product.update({
                "title": {
                    "ua": name.text.strip(),
                    "ru": name.text.strip()
                },
                "description": {
                    "ua": description.text if description is not None else "",
                    "ru": description.text if description is not None else ""
                },
                "price": round(base_price, 2),
                "price_old": round(old_price, 2),
                "brand": brand.text if brand is not None else "",
                "currency": "UAH",
                "parent": parent_category,
                "images": {
                    "links": [image.text] if image is not None else []
                }
            })

        products.append(product)

    except Exception as e:
        print("Ошибка товара:", e)
        continue

print(f"📦 Всего на отправку: {len(products)}")

# =========================
# 🚀 ОТПРАВКА
# =========================
if products:
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
else:
    print("✅ Нет товаров для обновления")
