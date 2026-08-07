# GPSトラッカー 構造ドキュメント（リファクタリング用）

現状 `index.html` 1ファイル（4853行）に HTML / CSS / JS 全てが同居している状態を、
再構築（ファイル分割・モジュール化）するために現状構造を棚卸ししたもの。

- `<head>`: 1〜21行
- `<style>`: 22〜1237行（CSS、約1200行）
- 強制キャッシュクリア用インラインscript: 1241〜1247行
- `<body>` マークアップ: 1249〜1404行
- メインscript（アプリ本体）: 1406〜4844行（JS、約3400行）
- Service Worker登録script: 4847〜4851行

外部依存（すべてCDN読み込み、ビルドツールなし）:
- Leaflet 1.9.4（地図）
- JSZip 3.10.1（ZIP展開）
- Turf.js 6（GeoJSON空間演算）
- sql.js 1.10.3（ITM形式=SQLiteファイルの読み込み）
- Google Analytics (gtag.js)

データ:
- `boundaries/01.geojson` 〜 `47.geojson`（都道府県別の境界ポリゴン、簡略化済み、GitHub Pagesから逐次fetch）
- `マニュアル.pdf`（操作マニュアル、header内リンクから別タブで開く）

---

## 1. HTML構造（body）

```
<body>
  #hover-tooltip          GPX軌跡ホバー時の簡易ツールチップ（＝吹き出し）
  #loading                初期地図読込中のスピナー
  #progress-bar > #progress-fill   ファイル読込の進捗バー
  #colPickModal           CSV列選択モーダル（配布数列の自動判定に失敗した時）
  #saveLoadModal          セーブ/ロード共通モーダル（一覧・新規保存フォーム）

  #app
    header#header
      .header-row#headerRow1     ロゴ／GPXデータ読込／住所コード読込／航空写真切替／住所検索／位置表示
      .header-row#headerRow2     配布率推定用スライダー3種／ヒートマップ切替／保存／再開／マニュアルリンク

    aside#sidebar
      端末一覧セクション（#deviceControls, #deviceList）
      #city-resizer               境界設定ペインとの上下リサイズハンドル
      #boundarySection            境界設定ペイン（都道府県→市区町村→町丁目の3段階ステッパー）
        #boundaryControls（ステッパー／絞り込み／一括表示切替／塗り濃度スライダー）
        #cityListHeader, #cityList

    #sidebar-resizer             サイドバー全体の左右リサイズハンドル
    #map                         Leaflet地図本体
</body>
```

モーダル・ツールチップ類はすべて自作divで、Leafletのポップアップ機構は使っていない（`showBalloon`/`hideBalloon`で共通管理）。

イベントバインドは基本 `onclick="fn()"` のインラインハンドラ（HTML側）。関数はグローバルスコープ前提。分割時はこの依存に注意（後述）。

---

## 2. CSS構造（22〜1237行）

コメント区切りで以下のセクションに分かれている（ほぼそのままファイル分割の単位にできる）:

| 範囲 | セクション |
|---|---|
| 53〜75 | レイアウト（全体グリッド） |
| 76〜211 | ヘッダー |
| 212〜278 | サイドバー |
| 279〜383 | コントロール共通（ボタン等） |
| 384〜404 | 端末カードリスト |
| 405〜498 | 端末カード |
| 499〜526 | 市区町村ペイン 上下リサイズハンドル |
| 527〜657 | 境界設定 - 市区町村ペイン |
| 658〜686 | 濃度スライダー |
| 687〜696 | ヘッダー下段スライダーの幅調整 |
| 697〜718 | 空状態 |
| 719〜747 | 地図 |
| 748〜781 | ローディング |
| 782〜800 | プログレスバー |
| 801〜893 | CSV列選択モーダル |
| 894〜1038 | セーブ/ロードモーダル |
| 1039〜1066 | 情報吹き出し（自作div・全種類共通） |
| 1067〜1098 | 境界ポリゴンの町字名吹き出し（控えめスタイル） |
| 1099〜1171 | ファイル別展開リスト |
| 1172〜1236 | 住所検索 |

---

## 3. JavaScript構造（1406〜4844行）

### 3.1 定数・状態（1407〜1500行）

- `N_BUCKETS`, `MAX_SPEED` … 速度バケット関連定数
- 軌跡データ状態: `DEVICES`, `GROUPS`, `GPX_DATA`, `GPX_SPEEDS`, `GPX_AVG_SPEED`, `speedPolylines`, `startMarkers`, `endMarkers`, `stayMarkers`, `visibility`, `filterText`, `modelColorMap`, `nextColorIdx`, `nextDeviceSeq`, `loadedKeys`, `groupExpanded`
- 境界ポリゴン状態: `cityGroups`, `cityVisibility`, `citySetai`, `cityCodes`, `cityNames`, `cityPrefCodes`, `cityFilterText`, `loadedPrefCodes`, `autoPrefCodes`, `boundaryFeatureCount`
- 境界設定ペインのステッパー状態: `boundaryLevel`, `prefSelected`, `townStageFromCSV`
- `PREF_NAMES` / `PREF_CODE_BY_NAME`（都道府県コード↔名称）
- CSVレポート状態: `allFeaturesByCode`, `csvTowns`, `townLayers`, `townVisibility`, `townFilterText`, `csvMode`
- 配布率推定状態: `rateHeatmapVisible`, `rateAutoShown`, `clusterRadiusM`, `secPerUnit`, `DISTRIBUTION_ESTIMATE_FACTOR`, `cityKeyByTownCode`, `townSetaiByCode`, `townVisitUnits`, `townDeliveryStats`, `cityDeliveryStats`
- 町丁目空間インデックス: `townFeatureList`, `townSpatialIdx`, `TOWN_BUCKET_*`, `townBucketLatDeg/LonDeg`
- `rateColorLUT`

→ これが実質「アプリの状態ストア」。分割時はここを `state.js` として集約し、他モジュールから参照/変更する形が自然。ただし現状はグローバルletが多数の関数から直接書き換えられており、状態の変更経路が暗黙的（Reduxのような単一更新口はない）。再構築時に整理する価値が高い箇所。

### 3.2 機能ブロック一覧（コメント区切り単位、行範囲付き）

| 行 | ブロック | 主な関数 |
|---|---|---|
| 1501〜1789 | 速度ヘルパー／スライダー連動 | `speedToBucket`, `bucketToOpacity`, `haversineKm`, `calcSpeeds`, `computeStays`, `computeTrajectoryAvgSpeed`, `onSecPerUnitChange/Commit`, `onRestDurationChange/Commit`, `onTransitSpeedChange/Commit`, `computeExclusionFlags`, `isTransitSegment`, `computeVisitClusters` |
| 1727〜1793 | ズーム適応サンプリング | `getSampleRate`, `buildBucketSegments`, `updatePolylines`, `schedulePolylineUpdate` |
| 1793〜1804 | 色生成（黄金角100色） | `deviceColor`, `stripNulSuffix` |
| 1805〜1817 | 座標配列の共通後処理 | `dedupeConsecutiveSameTime` |
| 1818〜1837 | GPXパーサ | `parseGPX` |
| 1834〜1886 | ITM（トレッキングマップ ituser.poi SQLite）パーサ | `getSqlJs`, `itmTicksToMs` |
| 1887〜1908 | JSON（ロガー出力）パーサ | `parseTrackJSON` |
| 1909〜1919 | ファイル名解析 | `parseFilename` |
| 1920〜1941 | グループ構築（端末番号=モデル単位） | `buildGroups` |
| 1941〜1996 | メモリ不足判定／トラック確定処理 | `isOutOfMemoryError`, `finalizeTrackItem` |
| 1997〜2087 | レイヤー管理 | `clearMapLayers`, `mkIcon`, `yieldToUI` |
| 2088〜2132 | 地図初期化／航空写真切替 | `toggleAerial` |
| 2132〜2160 | 表示更新（メインrender） | `render` |
| 2160〜2275 | サイドバー更新 | `isGroupExpandable`, `focusVisibleTracksInGroup`, `makeGroupCard`, `updateSidebar` |
| 2275〜2296 | イベントハンドラ（端末系） | `handleGroupToggle`, `toggleGroupExpand`, `expandAllGroups`, `onFilter`, `bulkVisibility` |
| 2296〜2451 | 配布データCSV読み込み | `decodeBytesAuto`, `parseCSVRows`, `looksLikeDistributionCSV`, `extractDistributionRecords`, `pointsToCoords`, `parseDistributionLabel`, `buildCSVItems` |
| 2451〜2510 | 選択ファイル群→読込ソース一覧への展開 | （無名/内部処理） |
| 2510〜2669 | ファイル読み込み本体（複数ファイル・ZIP内CSV対応・追加読込） | 主処理（巨大） |
| 2669〜2692 | データクリア | `clearTrackData` |
| 2692〜2702 | ファイル入力バインド | |
| 2702〜2828 | 境界データ（GeoJSON、都道府県ごとfetch） | `boundaryGeoJSONUrl` |
| 2828〜2857 | 境界データのアンロード | `unloadPrefectures` |
| 2857〜2919 | 境界設定ペイン：都道府県トグル表示段階 | `renderPrefStage`, `togglePref`, `bulkPrefVisibility`, `cityMatchesFilter` |
| 2919〜2993 | 市区町村リスト更新 | `updateCityList` |
| 2993〜3236 | 境界設定ペイン：3段階ステッパー制御 | `updateBoundaryStepper`, `goBoundaryStage`, `enterPrefStage`, `enterCityStage`, `hideAllCityLayers`, `showCityLayersPerVisibility`, `backToPrefStage`, `teardownTownStage`, `backToCityStageFromTown`, `toggleCity`, `bulkCityVisibility`, `onCityFilter`, `clearCityFilter`, `onFillOpacity` |
| 3236〜3416 | メッシュ読込・配布率推定（配色／空間インデックス） | `buildRateColorLUT`, `buildTownSpatialIndex`, `findTownCodeAt`, `toggleRateHeatmap`, `rateFillColor`, `boundaryStyleFor`, `cityFeatureStyle`, `anyTrackVisible`, `buildCityGeoJSONLayer`, `applyBoundaryColorStyle` |
| 3416〜3532 | 立ち寄りクラスタ検出／集計 | （軽量数値集計、`townVisitUnits`×世帯数から算出） |
| 3532〜3722 | CSVレポート：パース・列自動判定・列選択モーダル | `parseCSVLine`, `matchCode`, `autoDetectDistributionColIdx`, `pickDistributionColumn` |
| 3722〜3806 | CSVレポートクリア | `clearCSVReport` |
| 3806〜3940 | 町丁目リスト更新 | `updateTownList`, `toggleTown`, `townMatchesFilter`, `bulkTownVisibility`, `onTownFilter` |
| 3940〜4027 | 情報吹き出し（自作div・全種類共通） | `fmtTime`, `fmtDuration`, `nearestSpeed`, `fmtSpeed`, `markerScreenPos`, `positionBalloon`, `showBalloon`, `hideBalloon` |
| 4027〜4104 | ホバー検索（GPX軌跡／境界ポリゴンどちらのホバーか判定） | `doHoverSearch`, `extractPrefAndCityFromAddress` |
| 4104〜4138 | クリック位置の住所表示 | |
| 4138〜4200 | 住所検索結果→市区町村key解決 | `resolveCityKeysForQuery` |
| 4200〜4263 | 住所検索（本体） | |
| 4263〜4271 | ヘッダー下段（メッシュ関連ボタン）の表示切替 | |
| 4271〜4275 | 初期描画呼び出し | |
| 4275〜4303 | サイドバー 左右リサイズ | |
| 4303〜4330 | 市区町村ペイン 上下リサイズ | |
| 4330〜4692 | セーブ/ロード機能（IndexedDB） | `getSaveNamespace`, `openSaveDB`, `idbReq`, `hashString`, `slotId`, 保存処理, `resetAllStateForRestore` |
| 4692〜4818 | セーブ/ロードモーダルUI | `fmtSize`, `fmtSavedAt`, `openSaveModal`, `openLoadModal`, `closeSaveLoadModal` |
| 4818〜4844 | 初期表示／ヘッダーツールチップ抑制 | `suppressHeaderTooltips`（IIFE） |

### 3.3 データフロー概要

```
ファイル選択 (folderInput / csvReportInput)
  → 拡張子判定 (zip/gpx/itm/json/csv)
  → 各パーサ (parseGPX / ITMパーサ / parseTrackJSON / 配布CSVパーサ)
  → 座標後処理 (dedupeConsecutiveSameTime, calcSpeeds, computeStays, computeExclusionFlags)
  → finalizeTrackItem → DEVICES[] へ登録
  → buildGroups() → GROUPS[]（端末番号=モデル単位でグルーピング、色割当）
  → render() → updatePolylines() + updateSidebar()
       ├─ updatePolylines: 速度バケットごとのpolyline再構築（ズーム適応サンプリング）
       └─ updateSidebar: 端末カードリスト再描画

境界ポリゴン系（独立した並行フロー）:
  boundaryGeoJSONUrl(prefCode) で boundaries/{code}.geojson を fetch
  → renderPrefStage / updateCityList / updateTownList（都道府県→市区町村→町丁目の3段階ステッパー）
  → buildTownSpatialIndex（配布率推定のポイント・イン・ポリゴン判定を高速化）

配布率推定（GPX + 境界ポリゴンの合流点）:
  computeVisitClusters（GPX滞在クラスタ抽出）
  → findTownCodeAt（クラスタ座標→町丁目コード判定、空間インデックス使用）
  → townVisitUnits 集計 → townDeliveryStats / cityDeliveryStats
  → rateFillColor / buildRateColorLUT でヒートマップ着色

セーブ/ロード:
  IndexedDB (openSaveDB) に「現在の全状態」をシリアライズして保存
  ロード時は resetAllStateForRestore() で状態を初期化してから復元
  （GPX/端末データは再パースなしで復元、境界/住所コードは共有キャッシュから復元）
```

---

## 4. 再構築（ファイル分割）にあたっての注意点

現状の設計上、以下がモジュール分割時の主な障害になる:

1. **グローバル関数へのインラインonclick依存**: HTMLの `onclick="fn()"` が多数あり、`fn` はグローバルスコープに存在する前提。ESモジュール化（`type="module"`）すると自動でグローバルにならないため、①イベントは `addEventListener` に置き換える、②あるいは意図的に `window.fn = fn` で公開する、のどちらかの方針決定が必要。
2. **巨大な共有状態（3.1節）**: 多数の関数が同じletをread/writeしており、依存関係が暗黙的。ファイル分割の単位を機能ブロック（3.2節の表）通りにしても、状態の所有者が曖昧なままだと循環import になりやすい。状態を明示的なストアオブジェクト（例: `state.trackData`, `state.boundary`, `state.distribution`）にまとめてから分割すると安全。
3. **CSVレポート機能が2箇所に分裂**（2296行台と3532行台）: 現状コメントも「CSVレポート」が2回登場しており、機能としては「配布データCSV読込」と「住所コードCSVレポート」で別物。命名を分けて整理する価値がある。
4. **地図インスタンス生成**: `const map = L.map('map', {...})`（2089行）が `// ===== 地図初期化 =====` ブロックの先頭にある（関数化されておらずトップレベルで実行）。他の多数の関数がこの `map` をクロージャ経由で直接参照しているため、分割時は `map` を明示的にエクスポートするモジュール（`map/init.js`）に切り出す必要がある。

## 5. 提案する再構築後のファイル構成（案）

```
index.html                 # マークアップのみ（DOM構造）
css/
  base.css                 # レイアウト・ヘッダー・サイドバー共通
  controls.css             # ボタン・スライダー等コントロール共通
  modals.css                # colPickModal / saveLoadModal
  balloon.css               # 情報吹き出し・ホバーツールチップ
  search.css                 # 住所検索
js/
  main.js                   # エントリポイント（初期化呼び出しのみ）
  state.js                   # 3.1節の状態を集約
  parsers/
    gpx.js / itm.js / json.js / distribution-csv.js
  tracks/
    speed.js                 # 速度ヘルパー・バケット
    groups.js                # buildGroups, deviceColor
    polylines.js             # ズーム適応サンプリング・updatePolylines
  map/
    init.js                   # Leaflet map生成・航空写真切替
    layers.js                 # clearMapLayers, mkIcon
    render.js                  # render(), updateSidebar()
  boundary/
    fetch.js                   # boundaryGeoJSONUrl, 都道府県fetch
    stepper.js                 # 3段階ステッパー制御
    spatial-index.js            # 町丁目空間インデックス
  distribution/
    clusters.js                 # 立ち寄りクラスタ検出
    stats.js                     # townDeliveryStats/cityDeliveryStats集計
    heatmap.js                   # rateColorLUT・着色
    csv-report.js                 # 住所コードCSVレポート機能
  balloon.js                     # 情報吹き出し共通
  search.js                       # 住所検索
  save-load.js                     # IndexedDB セーブ/ロード
  resizers.js                      # サイドバー/市区町村ペインのリサイズ
sw.js
boundaries/*.geojson               # 現状のまま
マニュアル.pdf                       # 現状のまま
```

※ ビルドツール（bundler）を導入しない前提なら `<script type="module">` + 相対import で上記構成をそのまま使える。CDN依存（Leaflet/JSZip/Turf/sql.js）はグローバル変数を提供する旧来型ライブラリのため、`js/main.js` 側で読み込み順を維持する必要がある。
