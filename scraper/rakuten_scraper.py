import os
import csv
import time
import datetime
import urllib.request
import urllib.parse
import json

APP_ID = os.environ.get("RAKUTEN_APP_ID", "")
print("APP_ID length: " + str(len(APP_ID)))

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "rakuten_gadgets.csv")

FIELDNAMES = ["取得日時", "カテゴリ", "コンディション", "商品名", "価格", "ショップ名", "商品URL"]

SEARCHES = [
    ("スマホ", "スマートフォン", "新品"),
    ("GPU", "グラフィックボード", "新品"),
    ("SSD", "SSD", "新品"),
]

def fetch_items(keyword, page=1):
    params = {
        "applicationId": APP_ID,
        "keyword": keyword,
        "hits": 10,
        "page": page,
        "formatVersion": 2,
    }
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601?" + urllib.parse.urlencode(params)
    print("REQUEST: " + url[:120])
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode("utf-8"))
        return data.get("Items", [])
    except Exception as e:
        print("  [ERROR] {}: {}".format(keyword, e))
        return []

def scrape():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for category, keyword, condition in SEARCHES:
        print("[{}] {}".format(category, keyword))
        items = fetch_items(keyword)
        for item in items:
            rows.append({
                "取得日時": now,
                "カテゴリ": category,
                "コンディション": condition,
                "商品名": item.get("itemName", "")[:100],
                "価格": item.get("itemPrice", 0),
                "ショップ名": item.get("shopName", ""),
                "商品URL": item.get("itemUrl", ""),
            })
        print("  -> {}件".format(len(items)))
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    print("完了: {}件".format(len(rows)))

if __name__ == "__main__":
    scrape()
