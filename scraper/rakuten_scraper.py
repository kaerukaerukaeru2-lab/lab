import os
import csv
import time
import datetime
import urllib.request
import urllib.parse
import json

APP_ID = os.environ.get("RAKUTEN_APP_ID", "")
ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "")
print("APP_ID length: " + str(len(APP_ID)))
print("ACCESS_KEY length: " + str(len(ACCESS_KEY)))

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "rakuten_gadgets.csv")

FIELDNAMES = ["取得日時", "カテゴリ", "コンディション", "商品名", "価格", "ショップ名", "商品URL"]

SEARCHES = [
    ("スマホ", "スマートフォン", "新品"),
    ("スマホ", "スマートフォン 中古", "中古"),
    ("スマホ", "スマートフォン ジャンク", "ジャンク"),
    ("スマホアクセサリー", "スマホケース", "新品"),
    ("スマホアクセサリー", "スマホ 保護フィルム", "新品"),
    ("スマホアクセサリー", "スマホ 充電器", "新品"),
    ("GPU", "グラフィックボード", "新品"),
    ("GPU", "グラフィックボード 中古", "中古"),
    ("GPU", "グラフィックボード ジャンク", "ジャンク"),
    ("SSD", "SSD", "新品"),
    ("SSD", "SSD 中古", "中古"),
    ("メモリ", "PCメモリ DDR", "新品"),
    ("メモリ", "PCメモリ 中古", "中古"),
    ("電源", "PC電源ユニット", "新品"),
    ("電源", "電源ユニット 中古", "中古"),
    ("PCケース", "PCケース ATX", "新品"),
    ("PCケース", "PCケース 中古", "中古"),
]

HITS_PER_PAGE = 30
MAX_PAGES = 3


def fetch_items(keyword, page=1):
    params = {
        "applicationId": APP_ID,
        "accessKey": ACCESS_KEY,
        "keyword": keyword,
        "hits": HITS_PER_PAGE,
        "page": page,
        "format": "json",
        "formatVersion": 2,
    }
    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Referer": "https://x.com/fukugyoo_biz",
            "Origin": "https://x.com",
        })
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
        print("[{}] {} ({})".format(category, keyword, condition))
        seen = set()
        for page in range(1, MAX_PAGES + 1):
            items = fetch_items(keyword, page)
            if not items:
                break
            for item in items:
                item_url = item.get("itemUrl", "")
                if item_url in seen:
                    continue
                seen.add(item_url)
                rows.append({
                    "取得日時": now,
                    "カテゴリ": category,
                    "コンディション": condition,
                    "商品名": item.get("itemName", "")[:100],
                    "価格": item.get("itemPrice", 0),
                    "ショップ名": item.get("shopName", ""),
                    "商品URL": item.get("itemUrl", ""),
                })
            time.sleep(1)
        print("  -> {}件取得".format(len(seen)))

    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print("完了: {}件".format(len(rows)))


if __name__ == "__main__":
    scrape()
