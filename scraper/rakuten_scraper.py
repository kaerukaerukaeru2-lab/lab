import os
import csv
import time
import datetime
import urllib.request
import urllib.parse
import json

APP_ID = os.environ["RAKUTEN_APP_ID"]

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "rakuten_gadgets.csv")

FIELDNAMES = ["取得日時", "カテゴリ", "コンディション", "商品名", "価格", "ショップ名", "商品URL"]

# 検索キーワード定義
# (カテゴリ名, キーワード, コンディション)
SEARCHES = [
    # スマホ
    ("スマホ", "スマートフォン", "新品"),
    ("スマホ", "スマートフォン 中古", "中古"),
    ("スマホ", "スマートフォン ジャンク", "ジャンク"),
    # スマホアクセサリー
    ("スマホアクセサリー", "スマホケース", "新品"),
    ("スマホアクセサリー", "スマホ 保護フィルム", "新品"),
    ("スマホアクセサリー", "スマホ 充電器", "新品"),
    # GPU
    ("GPU", "グラフィックボード", "新品"),
    ("GPU", "グラフィックボード 中古", "中古"),
    ("GPU", "グラフィックボード ジャンク", "ジャンク"),
    # SSD
    ("SSD", "SSD", "新品"),
    ("SSD", "SSD 中古", "中古"),
    # メモリ
    ("メモリ", "PCメモリ DDR", "新品"),
    ("メモリ", "PCメモリ 中古", "中古"),
    # 電源ユニット
    ("電源", "PC電源ユニット", "新品"),
    ("電源", "電源ユニット 中古", "中古"),
    # PCケース
    ("PCケース", "PCケース ATX", "新品"),
    ("PCケース", "PCケース 中古", "中古"),
]

HITS_PER_PAGE = 30  # 1回のAPIコールで取得する件数（最大30）
MAX_PAGES = 3       # 1キーワードあたり最大ページ数 → 最大90件/キーワード


def fetch_items(keyword, page=1):
    """楽天商品検索APIを呼び出してアイテムリストを返す"""
    params = {
        "applicationId": APP_ID,
        "keyword": keyword,
        "hits": HITS_PER_PAGE,
        "page": page,
        "sort": "-reviewCount",   # レビュー数順（人気順の代替）
        "availability": 1,        # 在庫あり
        "formatVersion": 2,
    }
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
        return data.get("Items", [])
    except Exception as e:
        print(f"  [ERROR] {keyword} page={page}: {e}")
        return []


def scrape():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for category, keyword, condition in SEARCHES:
        print(f"[{category}] {keyword} ({condition})")
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
                    "取得日時":   now,
                    "カテゴリ":   category,
                    "コンディション": condition,
                    "商品名":     item.get("itemName", "")[:100],  # 長すぎる場合は切る
                    "価格":       item.get("itemPrice", 0),
                    "ショップ名": item.get("shopName", ""),
                    "商品URL":    item_url,
                })
            time.sleep(1)  # APIレートリミット対策（1秒待機）
        print(f"  → {len(seen)}件取得")

    # CSV書き込み（追記モード：初回は新規作成）
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\n完了: {len(rows)}件 → {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape()

