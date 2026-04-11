import requests
from lxml import etree
from datetime import datetime, timedelta
import os
import json
import time

# ======================
# 📩 TELEGRAM
# ======================
def send_telegram(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if not token or not chat_id:
        print("TG не настроен")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": chat_id,
            "text": text
        })
    except Exception as e:
        print("TG ERROR:", e)


# ======================
# 🚀 ОСНОВНОЙ БЛОК
# ======================
try:
    send_telegram(f"🚀 Старт\n{datetime.now()}")

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
        raise Exception("Ошибка авторизации: " + auth_response.text)

    print("✅ Авторизация ок")

    # =========================
    # 📅 ДАТА АКЦИИ
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
        raise Exception("Ошибка загрузки XML")

    root = etree.fromstring(response.content)

    # =========================
    # 📦 ОБНОВЛЕНИЕ ТОВАРОВ
    # =========================
    products = []

    for offer in root.findall('.//offer'):
        try:
            sku = offer.find('vendorCode')
            available = offer.get('available')

            if sku is None or not sku.text:
                continue

            sku = sku.text.strip()
            is_available = str(available).lower() == "true"

            product = {
                "article": sku,
                "presence": "В наявності" if is_available else "Немає в наявності"
            }

            if is_available:
                product["countdown_end_time"] = sale_date_str

            products.append(product)

        except Exception as e:
            print("Ошибка товара:", e)

    print(f"📦 Всего: {len(products)}")

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

        response = requests.post(
            API_URL,
            data=json.dumps(payload, ensure_ascii=False),
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"📤 {i}-{i + len(batch)} | {response.status_code}")

        try:
            print(response.json())
        except:
            print(response.text)

        time.sleep(1)

    # ======================
    # ✅ SUCCESS
    # ======================
    send_telegram(f"✅ Готово\nТоваров: {len(products)}")

except Exception as e:
    # ======================
    # ❌ ERROR
    # ======================
    send_telegram(f"❌ Ошибка:\n{str(e)}")
    raise
