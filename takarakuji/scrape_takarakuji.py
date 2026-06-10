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
        print('  取得失敗: %s -> %s' % (url, e))
        return None

def prev_ym(ym):
    y, m = int(ym[:4]), int(ym[4:])
    m -= 1
    if m == 0: m = 12; y -= 1
    return '%d%02d' % (y, m)

def clean_amount(text):
    text = re.sub(r'[\*\s]', '', text.strip())
    if not text or text == '該当なし': return text
    n = re.sub(r'[^\d]', '', text)
    if not n: return text
    return '{:,}円'.format(int(n))

def parse_one_round(table):
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
        rest = [c for c in cells[1:] if c.strip()]

        if '回号' in label or '開催回' in label:
            m = re.search(r'第0*(\d+)回', ' '.join(cells))
            if m: kai = int(m.group(1))
        elif '抽せん日' in label:
            m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', ' '.join(cells))
            if m: date = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
        elif '本数字' in label:
            # ミニロト: 「本数字 (　)はボーナス数字」のラベルで同一行にボーナスも含む
            for c in rest:
                c2 = re.sub(r'\s', '', c)
                if re.match(r'^\(\d{1,2}\)$', c2):
                    bonus = [int(re.sub(r'[()]', '', c2))]
                elif re.match(r'^\d{1,2}$', c2):
                    numbers.append(int(c2))
        elif 'ボーナス' in label:
            bonus = [int(re.sub(r'[()]','',c)) for c in rest if re.match(r'^\(?\d{1,2}\)?$', c)]
        elif re.match(r'^\d+等$', label):
            count_str = ''
            amount_str = ''
            for c in rest:
                if re.search(r'\d+口', c): count_str = c
                elif '円' in c or c == '該当なし': amount_str = clean_amount(c)
            if not amount_str and rest: amount_str = clean_amount(rest[-1])
            prizes.append({'rank': label, 'count': count_str, 'amount': amount_str})
        elif 'キャリーオーバー' in label:
            for c in rest:
                if re.search(r'\d', c): carryover = clean_amount(c); break
        elif '販売実績' in label:
            for c in rest:
                if re.search(r'\d', c): sales = clean_amount(c); break

    if kai and date and numbers:
        b_val = bonus[0] if len(bonus)==1 else (bonus if len(bonus)>1 else '')
        return {'round':kai,'date':date,'numbers':numbers,'bonus':b_val,
                'prizes':prizes,'sales':sales,'carryover':carryover}
    return None

def scrape_month(kind, ym):
    """指定月のデータを全回取得"""
    url = '%s/%s/%s/' % (BASE, kind, ym)
    soup = get_soup(url)
    # 月別URLでテーブルが取れない場合、月なしURL（今月分）を試す
    if not soup or not soup.find('table'):
        url = '%s/%s/' % (BASE, kind)
        soup = get_soup(url)
    if not soup: return []
    results = []
    seen = set()
    for table in soup.find_all('table'):
        r = parse_one_round(table)
        if r and r['round'] not in seen:
            seen.add(r['round'])
            results.append(r)
    results.sort(key=lambda x: x['round'], reverse=True)
    return results

def get_past_month_list(kind):
    """過去月リストを取得"""
    url = '%s/%s_past/' % (BASE, kind)
    soup = get_soup(url)
    if not soup: return []
    months = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        m = re.search(r'/backnumber/%s/(\d{6})' % kind, href)
        if m:
            ym = m.group(1)
            if ym not in seen:
                seen.add(ym)
                y, mo = int(ym[:4]), int(ym[4:])
                label = '%d年%d月分' % (y, mo)
                text = a.get_text(strip=True)
                months.append({'ym': ym, 'label': label, 'range': text})
    return months

def parse_numbers_round(table, digits):
    rows = table.find_all('tr')
    kai = date = None
    numbers = []
    prizes = []
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(['td','th'])]
        if not cells: continue
        label = cells[0]
        rest = [c for c in cells[1:] if c.strip()]
        if '回号' in label or '開催回' in label:
            m = re.search(r'第0*(\d+)回', ' '.join(cells))
            if m: kai = int(m.group(1))
        elif '抽せん日' in label:
            m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', ' '.join(cells))
            if m: date = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
        elif '当せん番号' in label or '番号' in label:
            for c in rest:
                c2 = re.sub(r'\s','',c)
                if re.match(r'^\d{%d}$' % digits, c2):
                    numbers = [int(d) for d in c2]; break
        elif any(x in label for x in ['ストレート','ボックス','セット']):
            amount = clean_amount(rest[-1]) if rest else ''
            prizes.append({'rank': label, 'count': '', 'amount': amount})
    if kai and date and numbers:
        return {'round':kai,'date':date,'numbers':numbers,'prizes':prizes}
    return None

def scrape_numbers_month(kind, ym, digits):
    url = '%s/%s/%s/' % (BASE, kind, ym)
    soup = get_soup(url)
    if not soup: return []
    results = []
    seen = set()
    for table in soup.find_all('table'):
        r = parse_numbers_round(table, digits)
        if r and r['round'] not in seen:
            seen.add(r['round'])
            results.append(r)
    results.sort(key=lambda x: x['round'], reverse=True)
    return results

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'takarakuji_data.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}

    now = datetime.now()
    cur_ym = '%d%02d' % (now.year, now.month)

    loto_tasks = [
        ('loto7', 'ロト7',   'loto7'),
        ('loto6', 'ロト6',   'loto6'),
        ('mini',  'ミニロト', 'mini'),
    ]
    numbers_tasks = [
        ('n3', 'ナンバーズ3', 'numbers3', 3),
        ('n4', 'ナンバーズ4', 'numbers4', 4),
    ]

    for key, name, kind in loto_tasks:
        print('%s取得中...' % name)
        if key not in data: data[key] = {}

        # 今月分（全回）
        cur = scrape_month(kind, cur_ym)
        data[key]['current'] = cur
        print('  今月: %d回分' % len(cur))
        time.sleep(2)

        # 過去月リスト
        months = get_past_month_list(kind)
        data[key]['past_months'] = months
        print('  過去月リスト: %d件' % len(months))
        time.sleep(2)

        # 過去月データ（直近12ヶ月取得）
        if 'past_data' not in data[key]: data[key]['past_data'] = {}
        for m in months[:12]:
            ym = m['ym']
            if ym not in data[key]['past_data']:
                print('  %s取得中...' % m['label'])
                past = scrape_month(kind, ym)
                data[key]['past_data'][ym] = past
                time.sleep(2)

    for key, name, kind, digits in numbers_tasks:
        print('%s取得中...' % name)
        if key not in data: data[key] = {}

        cur = scrape_numbers_month(kind, cur_ym, digits)
        data[key]['current'] = cur
        print('  今月: %d回分' % len(cur))
        time.sleep(2)

        # ナンバーズの過去月リスト
        months = get_past_month_list(kind)
        data[key]['past_months'] = months
        if 'past_data' not in data[key]: data[key]['past_data'] = {}
        for m in months[:12]:
            ym = m['ym']
            if ym not in data[key]['past_data']:
                past = scrape_numbers_month(kind, ym, digits)
                data[key]['past_data'][ym] = past
                time.sleep(2)

    # スクラッチは手動管理
    if 'scratch' not in data:
        data['scratch'] = {'current':[],'upcoming':[]}

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('完了: %s' % json_path)

if __name__ == '__main__':
    main()
