import requests
from lxml import etree
from datetime import datetime, timedelta
import os
import json
import time

# ======================
# 📁 ФАЙЛ СО СТАРЫМИ ЦЕНАМИ
# ======================
PRICE_FILE = "prices.json"

# загружаем старые цены
if os.path.exists(PRICE_FILE):
    with open(PRICE_FILE, "r", encoding="utf-8") as f:
        saved_prices = json.load(f)
else:
    saved_prices = {}


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
        hour=2,
        minute=55,
        second=0,
        microsecond=0
    )

    sale_date_str = sale_date.strftime("%Y-%m-%d %H:%M:%S")

    # =========================
    # XML
    # =========================
    url = "https://opt-drop.com/storage/xml/opt-drop-24.xml"

    response = requests.get(url, timeout=60)

    if response.status_code != 200:
        raise Exception("Ошибка загрузки XML")

    root = etree.fromstring(response.content)

    # =========================
    # 📦 ОБНОВЛЕНИЕ ТОВАРОВ
    # =========================
    products = []

    updated_prices = 0
    skipped_prices = 0

    for offer in root.findall('.//offer'):

        try:
            sku = offer.find('vendorCode')
            price = offer.find('price')

            available = offer.get('available')

            if sku is None or not sku.text:
                continue

            if price is None or not price.text:
                continue

            sku = sku.text.strip()

            # =====================
            # 💰 ЦЕНА
            # =====================

            original_price = float(price.text)

            # Наценка по диапазонам
            if original_price <= 107:
                final_price = original_price * 1.347

            elif 107 < original_price <= 166:
                final_price = original_price * 1.263

            elif 166 < original_price <= 261:
                final_price = original_price * 1.179

            elif 261 < original_price <= 356:
                final_price = original_price * 1.094

            else:
                # выше 356 грн — без наценки
                final_price = original_price

            # округление
            final_price = round(final_price)

            # =====================
            # ПРОВЕРКА ИЗМЕНЕНИЯ ЦЕНЫ
            # =====================

            old_price = saved_prices.get(sku)

            is_available = str(available).lower() == "true"

            product = {
                "article": sku,
                "presence": "В наявності" if is_available else "Немає в наявності"
            }

            # обновляем цену только если изменилась
            if old_price != final_price:

                product["price"] = final_price

                saved_prices[sku] = final_price

                updated_prices += 1

            else:
                skipped_prices += 1

            if is_available:
                product["countdown_end_time"] = sale_date_str

            products.append(product)

        except Exception as e:
            print("Ошибка товара:", e)

    print(f"📦 Всего товаров: {len(products)}")
    print(f"💰 Обновлено цен: {updated_prices}")
    print(f"⏭ Пропущено цен: {skipped_prices}")

    # =========================
    # 💾 СОХРАНЯЕМ ЦЕНЫ
    # =========================
    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(saved_prices, f, ensure_ascii=False, indent=2)

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
            headers={
                "Content-Type": "application/json"
            },
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
    send_telegram(
        f"✅ Готово\n"
        f"Товаров: {len(products)}\n"
        f"Обновлено цен: {updated_prices}\n"
        f"Пропущено: {skipped_prices}"
    )

except Exception as e:

    # ======================
    # ❌ ERROR
    # ======================
    send_telegram(f"❌ Ошибка:\n{str(e)}")
    raise
