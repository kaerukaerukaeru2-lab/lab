#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json, re, time, os
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}
BASE = 'https://takarakuji.rakuten.co.jp/backnumber'

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print('取得失敗: %s' % e)
        return None

def prev_ym(ym):
    y, m = int(ym[:4]), int(ym[4:])
    m -= 1
    if m == 0: m = 12; y -= 1
    return '%d%02d' % (y, m)

def clean_amount(text):
    text = re.sub(r'[\*\s]', '', text)
    if not text or text == '該当なし': return text
    n = re.sub(r'[^\d]', '', text)
    if not n: return text
    return '{:,}円'.format(int(n))

def parse_loto_table(table):
    """楽天の1回分テーブルをパース"""
    rows = table.find_all('tr')
    kai = date = None
    numbers = []
    bonus = []
    prizes = []
    sales = ''
    carryover = ''

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(['td','th'])]
        if not cells: continue
        label = cells[0]
        rest = [c for c in cells[1:] if c]

        if '回号' in label:
            m = re.search(r'第0*(\d+)回', ' '.join(cells))
            if m: kai = int(m.group(1))
        elif '抽せん日' in label:
            m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', ' '.join(cells))
            if m: date = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
        elif label == '本数字':
            numbers = [int(c) for c in rest if re.match(r'^\d{1,2}$', c)]
        elif 'ボーナス' in label:
            bonus = [int(re.sub(r'[()]','',c)) for c in rest if re.match(r'^\(?\d{1,2}\)?$', c)]
        elif re.match(r'^\d+等$', label):
            # 楽天: "7口" と "6,861,400円" が別セルで入ってる
            count_str = ''
            amount_str = ''
            for c in rest:
                if re.search(r'\d+口', c): count_str = c
                elif re.search(r'[\d,]+円', c) or c == '該当なし': amount_str = clean_amount(c)
            if not amount_str and rest: amount_str = clean_amount(rest[-1])
            prizes.append({'rank': label, 'count': count_str, 'amount': amount_str})
        elif 'キャリーオーバー' in label:
            for c in rest:
                if re.search(r'[\d,]+円', c):
                    carryover = clean_amount(c)
                    break

    # 販売実績は別テーブルの場合もあるので後で処理
    if kai and date and numbers:
        return {
            'round': kai, 'date': date,
            'numbers': numbers,
            'bonus': bonus[0] if len(bonus)==1 else bonus if len(bonus)>1 else '',
            'prizes': prizes,
            'sales': sales,
            'carryover': carryover
        }
    return None

def scrape_loto(kind):
    now = datetime.now()
    ym = '%d%02d' % (now.year, now.month)
    results = []
    for month in [ym, prev_ym(ym)]:
        url = '%s/%s/%s/' % (BASE, kind, month)
        soup = get_soup(url)
        if not soup:
            time.sleep(2)
            continue
        # 「販売実績」を全体から探す
        sales_map = {}
        for p in soup.find_all(['p','td','div']):
            t = p.get_text(strip=True)
            m = re.search(r'第0*(\d+)回.*?(\d[\d,]+)円', t)
            if m and '販売' in t:
                sales_map[int(m.group(1))] = clean_amount(m.group(2)+'円')

        for table in soup.find_all('table'):
            r = parse_loto_table(table)
            if r:
                if r['round'] in sales_map:
                    r['sales'] = sales_map[r['round']]
                results.append(r)
        time.sleep(2)

    if not results: return None
    # 重複除去
    seen = set()
    unique = []
    for r in results:
        if r['round'] not in seen:
            seen.add(r['round'])
            unique.append(r)
    unique.sort(key=lambda x: x['round'], reverse=True)
    return {'latest': unique[0], 'history': unique[1:6]}

def parse_numbers_table(table, digits):
    rows = table.find_all('tr')
    kai = date = None
    numbers = []
    prizes = []
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(['td','th'])]
        if not cells: continue
        label = cells[0]
        rest = [c for c in cells[1:] if c]
        if '回号' in label:
            m = re.search(r'第0*(\d+)回', ' '.join(cells))
            if m: kai = int(m.group(1))
        elif '抽せん日' in label:
            m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', ' '.join(cells))
            if m: date = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
        elif '当せん番号' in label or '番号' in label:
            for c in rest:
                c2 = re.sub(r'\s','', c)
                if re.match(r'^\d{%d}$' % digits, c2):
                    numbers = [int(d) for d in c2]
                    break
        elif any(x in label for x in ['ストレート','ボックス','セット']):
            amount = clean_amount(rest[-1]) if rest else ''
            prizes.append({'rank': label, 'count': '', 'amount': amount})
    if kai and date and numbers:
        return {'round': kai, 'date': date, 'numbers': numbers, 'prizes': prizes}
    return None

def scrape_numbers(kind, digits):
    now = datetime.now()
    ym = '%d%02d' % (now.year, now.month)
    results = []
    for month in [ym, prev_ym(ym)]:
        url = '%s/%s/%s/' % (BASE, kind, month)
        soup = get_soup(url)
        if not soup:
            time.sleep(2)
            continue
        for table in soup.find_all('table'):
            r = parse_numbers_table(table, digits)
            if r: results.append(r)
        time.sleep(2)
    if not results: return None
    seen = set()
    unique = []
    for r in results:
        if r['round'] not in seen:
            seen.add(r['round'])
            unique.append(r)
    unique.sort(key=lambda x: x['round'], reverse=True)
    return {'latest': unique[0], 'history': unique[1:6]}

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'takarakuji_data.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {'loto6':{},'loto7':{},'mini':{},'n3':{},'n4':{},'scratch':{'current':[],'upcoming':[]}}

    tasks = [
        ('loto7', 'ロト7',    lambda: scrape_loto('loto7')),
        ('loto6', 'ロト6',    lambda: scrape_loto('loto6')),
        ('mini',  'ミニロト',  lambda: scrape_loto('mini')),
        ('n3',    'ナンバーズ3', lambda: scrape_numbers('numbers3', 3)),
        ('n4',    'ナンバーズ4', lambda: scrape_numbers('numbers4', 4)),
    ]
    for key, name, fn in tasks:
        print('%s取得中...' % name)
        r = fn()
        if r:
            data[key] = r
            d = r['latest']
            print('  OK: 第%s回 %s %s prizes:%d' % (d['round'], d['date'], d['numbers'], len(d.get('prizes',[]))))
        else:
            print('  失敗')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('完了')

if __name__ == '__main__':
    main()
