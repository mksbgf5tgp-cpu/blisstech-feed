!pip install gspread pandas requests lxml

import requests
from lxml import etree
import pandas as pd
import numpy as np

# =========================
# 🔗 XML
# =========================

url = "https://blisstech.shop/marketplace-integration/facebook/d16015b3b40dacd474ec02f91ae07c63?langId=3"

response = requests.get(url, timeout=60)

parser = etree.XMLParser(recover=True, huge_tree=True, strip_cdata=False)
root = etree.fromstring(response.content, parser=parser)

ns = {'g': 'http://base.google.com/ns/1.0'}

# =========================
# 📦 ПАРСИНГ
# =========================

data = []

for item in root.xpath('//item'):

    def get(xpath):
        try:
            res = item.xpath(xpath, namespaces=ns)
            return res[0] if res else ''
        except:
            return ''

    row = {
        'id': get('g:id/text()'),
        'old_title': get('g:title/text()'),  # 👈 переименовали
        'description': get('g:description/text()'),
        'link': get('g:link/text()'),
        'image_link': get('g:image_link/text()'),
        'availability': get('g:availability/text()'),
        'price': get('g:price/text()'),
        'sale_price': get('g:sale_price/text()'),
        'brand': get('g:brand/text()'),
        'product_type': get('g:product_type/text()'),
        'condition': get('g:condition/text()'),  # 👈 новое поле
    }

    additional_images = item.xpath('g:additional_image_link/text()', namespaces=ns)
    row['additional_images'] = ", ".join(additional_images) if additional_images else ''

    data.append(row)

df = pd.DataFrame(data)

# =========================
# 🔥 ЧИСТКА
# =========================

df = df.replace([np.inf, -np.inf], "")
df = df.fillna("")
df = df.astype(str)

# =========================
# 📊 ПОРЯДОК КОЛОНОК (A–L)
# =========================

# =========================
# 📊 ПОРЯДОК КОЛОНОК (A–L)
# =========================

columns_order = [
    'id',                 # A
    'old_title',          # B
    'description',        # C
    'link',               # D
    'image_link',         # E
    'availability',       # F
    'price',              # G
    'sale_price',         # H
    'brand',              # I
    'product_type',       # J
    'additional_images',  # K
    'condition'           # L ✅
]

df = df[columns_order]

# =========================
# 🔐 АВТОРИЗАЦИЯ
# =========================



import os
import json
import gspread
from google.oauth2.service_account import Credentials

creds_json = json.loads(os.environ['GOOGLE_CREDENTIALS'])

creds = Credentials.from_service_account_info(
    creds_json,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

gc = gspread.authorize(creds)

# =========================
# 📄 ТАБЛИЦА
# =========================

SHEET_ID = "12DIBP22X7FhNfMUrjL7U5x_Z4nAYpeah2_OwpRlmDPE"

spreadsheet = gc.open_by_key(SHEET_ID)
sheet = spreadsheet.worksheet("Feed")

# =========================
# 📤 ЗАЛИВКА (ТОЛЬКО A–L)
# =========================

sheet.batch_clear(["A:L"])  # 👈 чистим только нужный диапазон

sheet.update(
    f"A1:L{len(df)+1}",  # 👈 ограничиваем диапазон
    [df.columns.values.tolist()] + df.values.tolist(),
    value_input_option='RAW'
)

print("✅ Готово, загружено:", len(df))
