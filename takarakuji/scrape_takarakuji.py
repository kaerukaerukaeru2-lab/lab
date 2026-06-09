#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宝くじ当選番号スクレイピング
取得元: takarakuji-loto.jp / ts4-net.com
出力: takarakuji_data.json
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 Chrome/120.0 Safari/537.36'
}

URLS = {
    'loto7':  'https://takarakuji-loto.jp/loto7_tousenp.html',
    'loto6':  'https://takarakuji-loto.jp/tousenp.html',
    'n3':     'https://www.ts4-net.com/result01.html',
    'n4':     'https://www.ts4-net.com/result02.html',
}

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print('取得失敗: %s -> %s' % (url, e))
        return None

def extract_nums_from_imgs(imgs):
    """画像のファイル名から数字を抽出 lb-09.png -> 9"""
    nums = []
    for img in imgs:
        src = img.get('src', '')
        m = re.search(r'lb-(\d+)', src)
        if m:
            nums.append(int(m.group(1)))
    return nums

def parse_round_date(text):
    """'第６８０回 ロト7 当選番号速報 2026年6月5日 抽選' から回号と日付を取得"""
    kai = ''
    date = ''
    m_kai = re.search(r'第([\d６７８９０１２３４５]+)回', text)
    if m_kai:
        # 全角数字を半角に変換
        kai_str = m_kai.group(1)
        kai_str = kai_str.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        kai = int(kai_str)
    m_date = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    if m_date:
        date = '%s-%02d-%02d' % (m_date.group(1), int(m_date.group(2)), int(m_date.group(3)))
    return kai, date

def scrape_loto(key):
    """ロト7・ロト6共通スクレイパー"""
    soup = get_soup(URLS[key])
    if not soup:
        return None

    results = []
    # h3タグで各回のブロックを特定
    for h3 in soup.find_all('h3'):
        text = h3.get_text()
        kai, date = parse_round_date(text)
        if not kai:
            continue

        # h3の次のテーブル群を取得
        tables = []
        sib = h3.find_next_sibling()
        while sib and sib.name != 'h3':
            if sib.name == 'table':
                tables.append(sib)
            sib = sib.find_next_sibling()

        if len(tables) < 2:
            continue

        # 1つ目のテーブル: 本数字
        nums_imgs = tables[0].find_all('img')
        numbers = extract_nums_from_imgs(nums_imgs)

        # 2つ目のテーブル: ボーナス数字
        bonus_imgs = tables[1].find_all('img')
        bonus = extract_nums_from_imgs(bonus_imgs)

        if not numbers:
            continue

        results.append({
            'round': kai,
            'date': date,
            'numbers': numbers,
            'bonus': bonus
        })

    if not results:
        return None

    latest = results[0]
    history = results[1:] if len(results) > 1 else []

    return {
        'latest': {
            'date': latest['date'],
            'round': latest['round'],
            'numbers': latest['numbers'],
            'bonus': latest['bonus'][0] if latest['bonus'] else ''
        },
        'history': history
    }

def scrape_numbers(key):
    """ナンバーズ3・4スクレイパー"""
    soup = get_soup(URLS[key])
    if not soup:
        return None

    results = []
    # テーブルから当選番号を探す
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(['td','th'])]
            if len(cells) < 3:
                continue
            # 回号らしき数字があるか
            m_kai = re.search(r'(\d{4,5})回?', cells[0])
            if not m_kai:
                continue
            # 日付
            m_date = re.search(r'(\d{4})[./年](\d{1,2})[./月](\d{1,2})', ' '.join(cells))
            if not m_date:
                continue
            date = '%s-%02d-%02d' % (m_date.group(1), int(m_date.group(2)), int(m_date.group(3)))
            kai = int(m_kai.group(1))
            # 数字: 4桁か3桁の数字を探す
            nums_text = ''
            for c in cells[1:]:
                if re.match(r'^\d{3,4}$', c.replace(' ','')):
                    nums_text = c.replace(' ','')
                    break
            if not nums_text:
                continue
            numbers = [int(d) for d in nums_text]
            results.append({'round': kai, 'date': date, 'numbers': numbers})

    if not results:
        return None

    latest = results[0]
    history = results[1:] if len(results) > 1 else []
    return {
        'latest': {
            'date': latest['date'],
            'round': latest['round'],
            'numbers': latest['numbers']
        },
        'history': history
    }

def main():
    print('=== 宝くじ当選番号取得開始 ===')

    # 既存JSONを読み込む（スクラッチ情報を保持するため）
    try:
        with open('takarakuji_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {
            'loto6': {'latest': {}, 'history': []},
            'loto7': {'latest': {}, 'history': []},
            'n3': {'latest': {}, 'history': []},
            'n4': {'latest': {}, 'history': []},
            'scratch': {'current': [], 'upcoming': []}
        }

    # ロト7
    print('ロト7 取得中...')
    r = scrape_loto('loto7')
    if r:
        data['loto7'] = r
        print('  -> 最新: 第%s回 %s %s' % (r['latest']['round'], r['latest']['date'], r['latest']['numbers']))
    else:
        print('  -> 取得失敗')
    time.sleep(3)

    # ロト6
    print('ロト6 取得中...')
    r = scrape_loto('loto6')
    if r:
        data['loto6'] = r
        print('  -> 最新: 第%s回 %s %s' % (r['latest']['round'], r['latest']['date'], r['latest']['numbers']))
    else:
        print('  -> 取得失敗')
    time.sleep(3)

    # ナンバーズ3
    print('ナンバーズ3 取得中...')
    r = scrape_numbers('n3')
    if r:
        data['n3'] = r
        print('  -> 最新: 第%s回 %s %s' % (r['latest']['round'], r['latest']['date'], r['latest']['numbers']))
    else:
        print('  -> 取得失敗（手動確認が必要な可能性あり）')
    time.sleep(3)

    # ナンバーズ4
    print('ナンバーズ4 取得中...')
    r = scrape_numbers('n4')
    if r:
        data['n4'] = r
        print('  -> 最新: 第%s回 %s %s' % (r['latest']['round'], r['latest']['date'], r['latest']['numbers']))
    else:
        print('  -> 取得失敗（手動確認が必要な可能性あり）')

    # JSON保存
    with open('takarakuji_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('\n=== takarakuji_data.json を更新しました ===')

if __name__ == '__main__':
    main()
