#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json, re, time, os

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print('取得失敗: %s' % e)
        return None

def nums_from_imgs(tag):
    nums = []
    for img in tag.find_all('img'):
        src = img.get('src', '')
        m = re.search(r'lb-0*(\d+)', src)
        if m:
            nums.append(int(m.group(1)))
    return nums

def parse_kai_date(text):
    kai, date = '', ''
    t = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    m = re.search(r'第(\d+)回', t)
    if m: kai = int(m.group(1))
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', t)
    if m: date = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    return kai, date

def scrape_loto(url):
    soup = get_soup(url)
    if not soup: return None
    results = []
    # h3, h2, div問わず回号テキストを含む要素を探す
    for tag in soup.find_all(['h2','h3','h4','p','div']):
        text = tag.get_text()
        kai, date = parse_kai_date(text)
        if not kai or not date: continue
        # 同じブロック内か直後のテーブルから画像を取得
        tables = []
        node = tag.find_next_sibling()
        count = 0
        while node and count < 10:
            if node.name == 'table':
                tables.append(node)
                if len(tables) >= 2: break
            node = node.find_next_sibling()
            count += 1
        if len(tables) < 1: continue
        numbers = nums_from_imgs(tables[0])
        bonus = nums_from_imgs(tables[1]) if len(tables) > 1 else []
        if not numbers: continue
        results.append({'round': kai, 'date': date, 'numbers': numbers, 'bonus': bonus})
        if len(results) >= 5: break
    if not results: return None
    latest = results[0]
    return {
        'latest': {
            'date': latest['date'],
            'round': latest['round'],
            'numbers': latest['numbers'],
            'bonus': latest['bonus'][0] if latest['bonus'] else ''
        },
        'history': results[1:]
    }

def scrape_numbers(url, digits):
    soup = get_soup(url)
    if not soup: return None
    results = []
    for tr in soup.find_all('tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all(['td','th'])]
        if len(cells) < 2: continue
        row_text = ' '.join(cells)
        t = row_text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        m_kai = re.search(r'第(\d{4,5})回', t)
        m_date = re.search(r'(\d{4})[./年](\d{1,2})[./月](\d{1,2})', t)
        if not m_kai or not m_date: continue
        kai = int(m_kai.group(1))
        date = '%s-%02d-%02d' % (m_date.group(1), int(m_date.group(2)), int(m_date.group(3)))
        for c in cells:
            c2 = re.sub(r'\s','', c)
            if re.match(r'^\d{%d}$' % digits, c2):
                numbers = [int(d) for d in c2]
                results.append({'round': kai, 'date': date, 'numbers': numbers})
                break
        if len(results) >= 5: break
    if not results: return None
    return {'latest': results[0], 'history': results[1:]}

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'takarakuji_data.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {'loto6':{},'loto7':{},'n3':{},'n4':{},'scratch':{'current':[],'upcoming':[]}}

    print('ロト7取得中...')
    r = scrape_loto('https://takarakuji-loto.jp/loto7_tousenp.html')
    if r:
        data['loto7'] = r
        print('  OK: 第%s回 %s %s' % (r['latest']['round'], r['latest']['date'], r['latest']['numbers']))
    else:
        print('  失敗')
    time.sleep(3)

    print('ロト6取得中...')
    r = scrape_loto('https://takarakuji-loto.jp/tousenp.html')
    if r:
        data['loto6'] = r
        print('  OK: 第%s回 %s %s' % (r['latest']['round'], r['latest']['date'], r['latest']['numbers']))
    else:
        print('  失敗')
    time.sleep(3)

    print('ナンバーズ3取得中...')
    r = scrape_numbers('https://www.ts4-net.com/result01.html', 3)
    if r:
        data['n3'] = r
        print('  OK: %s' % r['latest'])
    else:
        print('  失敗')
    time.sleep(3)

    print('ナンバーズ4取得中...')
    r = scrape_numbers('https://www.ts4-net.com/result02.html', 4)
    if r:
        data['n4'] = r
        print('  OK: %s' % r['latest'])
    else:
        print('  失敗')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('完了: %s' % json_path)

if __name__ == '__main__':
    main()
