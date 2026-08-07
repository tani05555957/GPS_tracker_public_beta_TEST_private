#!/usr/bin/env python3
"""
boundaries/<都道府県コード>.geojson（県まるごと1ファイル）を、
  boundaries/<都道府県コード>/index.json              … その県の市区町村一覧（コード・名称・世帯数のみ、ジオメトリなし）
  boundaries/<都道府県コード>/<市区町村コード>.geojson … 個々の市区町村のポリゴン
へ分割する。

市区町村keyの計算は index.html 側（loadBoundaryIndex/ensureCityGeometry が前提とする形）と
完全に一致させる必要がある。ロジックは元々 index.html 内の loadBoundaryFromGeoJSONText に
あったものと同一（PREF+CITYからkeyを作り、無ければKEY_CODEの先頭5桁にフォールバック）。

実行後、分割元の boundaries/<NN>.geojson は使われなくなる（index.html は
boundaries/<NN>/index.json と boundaries/<NN>/<city>.geojson だけを参照する）。
"""
import json
import glob
import os

BOUNDARIES_DIR = os.path.join(os.path.dirname(__file__), '..', 'boundaries')


def city_key_and_code(props, pref_code_fallback):
    pref = props.get('PREF')
    city_num = props.get('CITY')
    key_code = str(props.get('KEY_CODE') or props.get('KEYCODE') or '').strip()
    pref_code = str(pref).zfill(2) if pref is not None else key_code[:2]
    if pref is not None and city_num is not None:
        city_code = pref_code + str(city_num).zfill(3)
    else:
        city_code = key_code[:5]
    city_name = props.get('CITY_NAME') or props.get('name') or '不明'
    key = city_code or f"{pref_code or '??'}_{city_name}"
    code = city_code or key
    return key, code, pref_code or pref_code_fallback, city_name


def split_one(src_path):
    pref_code = os.path.splitext(os.path.basename(src_path))[0]
    with open(src_path, encoding='utf-8') as f:
        data = json.load(f)

    cities = {}  # key -> {code, prefCode, name, setai, features: []}
    fallback_count = 0
    for feat in data['features']:
        props = feat.get('properties') or {}
        key, code, p_code, city_name = city_key_and_code(props, pref_code)
        if key != code:
            fallback_count += 1
        entry = cities.setdefault(key, {
            'key': key, 'code': code, 'prefCode': p_code, 'name': city_name, 'setai': 0, 'features': [],
        })
        entry['features'].append(feat)
        try:
            entry['setai'] += int(props.get('SETAI') or 0)
        except (TypeError, ValueError):
            pass

    out_dir = os.path.join(BOUNDARIES_DIR, pref_code)
    os.makedirs(out_dir, exist_ok=True)

    index_entries = []
    for key, entry in cities.items():
        index_entries.append({
            'key': entry['key'], 'code': entry['code'], 'prefCode': entry['prefCode'],
            'name': entry['name'], 'setai': entry['setai'],
        })
        city_geojson = {'type': 'FeatureCollection', 'features': entry['features']}
        out_path = os.path.join(out_dir, f"{entry['code']}.geojson")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(city_geojson, f, ensure_ascii=False, separators=(',', ':'))

    index_entries.sort(key=lambda c: c['code'])
    with open(os.path.join(out_dir, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index_entries, f, ensure_ascii=False, separators=(',', ':'))

    return {
        'prefCode': pref_code,
        'cities': len(cities),
        'features': len(data['features']),
        'fallbackKeys': fallback_count,
    }


def main():
    src_files = sorted(glob.glob(os.path.join(BOUNDARIES_DIR, '[0-9][0-9].geojson')))
    if not src_files:
        print('分割対象の boundaries/<NN>.geojson が見つかりません')
        return

    total_cities = 0
    total_features = 0
    total_fallback = 0
    for src in src_files:
        stats = split_one(src)
        total_cities += stats['cities']
        total_features += stats['features']
        total_fallback += stats['fallbackKeys']
        print(f"{stats['prefCode']}: {stats['cities']:4d}市区町村 / {stats['features']:6d}フィーチャ"
              + (f"  ※フォールバックkey {stats['fallbackKeys']}件" if stats['fallbackKeys'] else ''))

    print('---')
    print(f"合計: {len(src_files)}都道府県 / {total_cities}市区町村 / {total_features}フィーチャ"
          + (f" / フォールバックkey {total_fallback}件" if total_fallback else ''))


if __name__ == '__main__':
    main()
