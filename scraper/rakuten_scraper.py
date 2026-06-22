import os
import csv
import time
import datetime
import urllib.request
import urllib.parse
import json

APP_ID = os.environ.get("RAKUTEN_APP_ID", "")
ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "")
AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "")
print("APP_ID length: " + str(len(APP_ID)))
print("ACCESS_KEY length: " + str(len(ACCESS_KEY)))
print("AFFILIATE_ID length: " + str(len(AFFILIATE_ID)))

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "rakuten_gadgets.csv")

FIELDNAMES = ["取得日時", "カテゴリ", "コンディション", "商品名", "価格", "ショップ名", "商品URL"]

# ノイズ除外キーワード（商品名に含まれたらスキップ）
EXCLUDE_KEYWORDS = [
    "ふるさと納税", "返礼品", "タブレット", "iPad", "Fire HD",
    "キーボード", "マウス", "モニター", "ディスプレイ",
    "ルーター", "Wi-Fi", "プリンター", "スキャナー",
    "ゲーム機", "Nintendo", "PlayStation", "Xbox",
    "イヤホン", "ヘッドホン", "スピーカー",
]

SEARCHES = [
    # ── iPhone ──────────────────────────────
    ("iPhone", "iPhone 16 Pro",        "新品"),
    ("iPhone", "iPhone 16 Pro 中古",   "中古"),
    ("iPhone", "iPhone 16",            "新品"),
    ("iPhone", "iPhone 16 中古",       "中古"),
    ("iPhone", "iPhone 15 Pro",        "新品"),
    ("iPhone", "iPhone 15 Pro 中古",   "中古"),
    ("iPhone", "iPhone 15",            "新品"),
    ("iPhone", "iPhone 15 中古",       "中古"),
    ("iPhone", "iPhone 14",            "新品"),
    ("iPhone", "iPhone 14 中古",       "中古"),
    ("iPhone", "iPhone ジャンク",      "ジャンク"),

    # ── Android 有名機種 ─────────────────────
    ("Android_Xperia",  "Xperia 1 VI",              "新品"),
    ("Android_Xperia",  "Xperia 1 VI 中古",         "中古"),
    ("Android_Xperia",  "Xperia 5 VI",              "新品"),
    ("Android_Xperia",  "Xperia 10 VI",             "新品"),
    ("Android_Galaxy",  "Galaxy S24 Ultra",          "新品"),
    ("Android_Galaxy",  "Galaxy S24",                "新品"),
    ("Android_Galaxy",  "Galaxy S24 中古",           "中古"),
    ("Android_Galaxy",  "Galaxy S23 中古",           "中古"),
    ("Android_Pixel",   "Google Pixel 9 Pro",        "新品"),
    ("Android_Pixel",   "Google Pixel 9",            "新品"),
    ("Android_Pixel",   "Google Pixel 8 中古",       "中古"),
    ("Android_AQUOS",   "AQUOS sense8",              "新品"),
    ("Android_AQUOS",   "AQUOS R8",                  "新品"),
    ("Android_AQUOS",   "AQUOS 中古",                "中古"),
    ("Android_Arrow",   "arrows We2",                "新品"),
    ("Android_その他",  "Android スマートフォン 新品", "新品"),
    ("Android_その他",  "Android スマートフォン 中古", "中古"),
    ("Android_その他",  "スマートフォン ジャンク",    "ジャンク"),

    # ── アクセサリー ─────────────────────────
    ("アクセサリー_ケース",    "スマホケース iPhone",   "新品"),
    ("アクセサリー_ケース",    "スマホケース Android",  "新品"),
    ("アクセサリー_フィルム",  "スマホ 保護フィルム",   "新品"),
    ("アクセサリー_充電器",    "スマホ 充電器 急速",    "新品"),
    ("アクセサリー_充電器",    "MagSafe 充電器",        "新品"),
]

HITS_PER_PAGE = 30
MAX_PAGES = 10


def is_noise(item_name):
    name = item_name.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in name:
            return True
    return False


def fetch_items(keyword, page=1):
    params = {
        "applicationId": APP_ID,
        "accessKey": ACCESS_KEY,
        "affiliateId": AFFILIATE_ID,
        "keyword": keyword,
        "hits": HITS_PER_PAGE,
        "page": page,
        "format": "json",
        "formatVersion": 2,
        "sort": "-itemPrice",
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
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  [429] レート制限 リトライ待機中...")
            time.sleep(5)
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    data = json.loads(res.read().decode("utf-8"))
                return data.get("Items", [])
            except Exception as e2:
                print("  [ERROR] リトライ失敗: {}".format(e2))
                return []
        print("  [ERROR] {}: {}".format(keyword, e))
        return []
    except Exception as e:
        print("  [ERROR] {}: {}".format(keyword, e))
        return []


def scrape():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    seen_global = set()  # URL重複を全体でも排除

    for category, keyword, condition in SEARCHES:
        print("[{}] {} ({})".format(category, keyword, condition))
        seen_local = set()
        fetched = 0
        noise_count = 0

        for page in range(1, MAX_PAGES + 1):
            items = fetch_items(keyword, page)
            if not items:
                break
            for item in items:
                item_url = item.get("affiliateUrl") or item.get("itemUrl", "")
                item_name = item.get("itemName", "")

                # URL重複チェック（ローカル＋グローバル）
                if item_url in seen_local or item_url in seen_global:
                    continue

                # ノイズフィルタ
                if is_noise(item_name):
                    noise_count += 1
                    continue

                seen_local.add(item_url)
                seen_global.add(item_url)
                fetched += 1
                rows.append({
                    "取得日時": now,
                    "カテゴリ": category,
                    "コンディション": condition,
                    "商品名": item_name[:100],
                    "価格": item.get("itemPrice", 0),
                    "ショップ名": item.get("shopName", ""),
                    "商品URL": item_url,
                })
            time.sleep(2)

        print("  -> {}件取得 (ノイズ除外: {}件)".format(fetched, noise_count))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print("完了: {}件".format(len(rows)))


if __name__ == "__main__":
    scrape()
