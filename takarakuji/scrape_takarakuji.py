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

def parse_loto_tables(soup):
    results = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        kai = date = None
        numbers = []
        bonus = []
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(['td','th'])]
            if not cells: continue
            label = cells[0]
            if '回号' in label or ('回' in label and len(cells) > 1):
                m = re.search(r'第0*(\d+)回', ' '.join(cells))
                if m: kai = int(m.group(1))
            elif '抽せん日' in label or '抽選日' in label:
                m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', ' '.join(cells))
                if m: date = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
            elif '本数字' in label:
                numbers = [int(c) for c in cells[1:] if re.match(r'^\d{1,2}$', c)]
            elif 'ボーナス' in label:
                bonus = [int(re.sub(r'[()]','',c)) for c in cells[1:] if re.match(r'^\(?\d{1,2}\)?$', c)]
        if kai and date and numbers:
            results.append({'round': kai, 'date': date, 'numbers': numbers, 'bonus': bonus})
    return results

def parse_numbers_tables(soup, digits):
    results = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        kai = date = None
        numbers = []
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(['td','th'])]
            if not cells: continue
            label = cells[0]
            if '回号' in label or ('回' in label and len(cells) > 1):
                m = re.search(r'第0*(\d+)回', ' '.join(cells))
                if m: kai = int(m.group(1))
            elif '抽せん日' in label or '抽選日' in label:
                m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', ' '.join(cells))
                if m: date = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
            elif '当せん番号' in label or '番号' in label:
                for c in cells[1:]:
                    c2 = re.sub(r'\s','', c)
                    if re.match(r'^\d{%d}$' % digits, c2):
                        numbers = [int(d) for d in c2]
                        break
        if kai and date and numbers:
            results.append({'round': kai, 'date': date, 'numbers': numbers})
    return results

def scrape_loto(kind):
    now = datetime.now()
    ym = '%d%02d' % (now.year, now.month)
    results = []
    for month in [ym, prev_ym(ym)]:
        url = '%s/%s/%s/' % (BASE, kind, month)
        soup = get_soup(url)
        if soup:
            results += parse_loto_tables(soup)
        time.sleep(2)
    if not results: return None
    results.sort(key=lambda x: x['round'], reverse=True)
    latest = results[0]
    return {
        'latest': {
            'date': latest['date'],
            'round': latest['round'],
            'numbers': latest['numbers'],
            'bonus': latest['bonus'][0] if latest['bonus'] else ''
        },
        'history': results[1:6]
    }

def scrape_numbers(kind, digits):
    now = datetime.now()
    ym = '%d%02d' % (now.year, now.month)
    results = []
    for month in [ym, prev_ym(ym)]:
        url = '%s/%s/%s/' % (BASE, kind, month)
        soup = get_soup(url)
        if soup:
            results += parse_numbers_tables(soup, digits)
        time.sleep(2)
    if not results: return None
    results.sort(key=lambda x: x['round'], reverse=True)
    return {'latest': results[0], 'history': results[1:6]}

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'takarakuji_data.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {'loto6':{},'loto7':{},'n3':{},'n4':{},'scratch':{'current':[],'upcoming':[]}}

    tasks = [
        ('loto7', 'ロト7',    lambda: scrape_loto('loto7')),
        ('loto6', 'ロト6',    lambda: scrape_loto('loto6')),
        ('n3',    'ナンバーズ3', lambda: scrape_numbers('numbers3', 3)),
        ('n4',    'ナンバーズ4', lambda: scrape_numbers('numbers4', 4)),
    ]
    for key, name, fn in tasks:
        print('%s取得中...' % name)
        r = fn()
        if r:
            data[key] = r
            print('  OK: 第%s回 %s %s' % (r['latest']['round'], r['latest']['date'], r['latest']['numbers']))
        else:
            print('  失敗')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('完了: %s' % json_path)

if __name__ == '__main__':
    main()
