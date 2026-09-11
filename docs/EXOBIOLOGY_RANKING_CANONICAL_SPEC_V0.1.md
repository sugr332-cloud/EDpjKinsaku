# Exobiology ランキング正本 v0.1

**Status:** Normative / Canonical
**Date:** 2026-09-11

本書は、Exobiologyランキングにおける「本番で何を正本モデルとして使うか」を定義する。Phase文書・実装ノート・backtest資料に矛盾がある場合、本書を優先する。

## 1. 採用モデルの宣言

本番ランキングの基準モデルは **V1** とする。

```text
expected_value_base
= biological_signal_count × expected_value_per_signal
```

`expected_value_per_signal` は species / genus の固定単価ではない。本人の `SellOrganicData` / `ScanOrganic` 履歴から算出する、履歴ベースの生体分析1件あたり平均収益率である。

species prediction（`P(species | body_conditions, ...)`）は研究トラックとして並行開発するが、下記の昇格基準をすべて満たすまでは本番の `cr/h` 計算には使用しない。

## 2. species prediction の昇格基準

species prediction の評価は、以下の3指標を分離して扱う。

### 2.1 Prediction Accuracy

- Top-1 accuracy
- Top-k hit rate
- Coverage
- Insufficient rate

現行の **60% gate は Top-1 accuracy に対する基準**であり、これだけで本番採用とはしない。

### 2.2 Value Error

予測した species 分布から算出した価値と、実際に観測・売却された価値との差を評価する。

少なくとも MAE / MAPE 等の誤差指標を定義し、評価対象とする。

### 2.3 Ranking Quality

予測モデルで算出した候補順位と、実測データから算出した価値・`cr/h` 順位の一致度を評価する。

**Accuracy 単体での本番昇格は禁止する。**

本番昇格には Prediction Accuracy / Value Error / Ranking Quality の各基準を別々に定義し、全条件を満たすことを要求する。

## 3. V1 から species prediction への昇格経路

現在の本番系統は次の通り固定する。

```text
                     ┌─ species prediction ─┐
                     │                       │
本番 V1 ─────────────┤                       ├─ 昇格判定
                     │                       │
                     └───────────────────────┘
                              │
                    Accuracy / Value Error /
                      Ranking Quality
                              │
                         全条件 PASS
                              ↓
                  species-based value model
```

species prediction のbacktest結果が改善しただけでは、本番計算式を自動変更しない。

## 4. First Footfall の扱い

`WasDiscovered` / `WasMapped` から導出するFirst Footfall係数は、現時点では**未較正の推定値**として扱う。

- 絶対的な確率・確定期待値として扱わない。
- FD補正を含む値は、確定値と同列の値として扱わない。
- 出力上は `[推定]` 等の明示的な注記を付ける。
- V1の基準価値とFD upsideを概念上分離する。

## 5. value_confidence の伝播

SpeciesValueMaster の `confidence` はランキング結果まで保持する。

```text
HIGH / MEDIUM / DISPUTED
```

`DISPUTED` の値を使用した候補は、確定値と区別できる状態で表示する。

特に `DISPUTED` 由来の価値だけを根拠として上位順位になった場合は、順位に注記するか、確定値のランキングと分離して表示する。

未カバー species は 0 や推測値で補完しない。価値データ不足として扱う。

## 6. 時間モデル

初期実装では固定時間モデルを使用する。

対象時間は少なくとも、超空間巡航到達・降下・サンプリング・離陸を明示的に区別する。

実プレイでは Journal のタイムスタンプ差分を用いて固定値を較正する。

地形・実移動時間等を詳細にモデル化することは将来Phaseとし、未較正の固定値を実測値として扱わない。

## 7. 探索範囲

現在星系内ランキングを先行実装とする。

周辺星系を含む探索およびSpansh併用は削除せず、将来Phaseとして保持する。

現在星系内ランキングが成立したことをもって、周辺星系探索まで成立したとはみなさない。

## 8. 旧仕様との関係

本プロジェクトの現在スコープは Exobiology のみである。

Mining / Trade / Market の旧仕様を現在のランキング設計の依存関係として扱わない。旧仕様書を参照する新規実装・新規仕様は作成しない。

## 9. 文書の優先順位

1. 本書 `EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md`
2. `BIO_EXTERNAL_DATA_VALIDATION_SPEC_V0.1.md` 等のNormative / binding文書
3. Phase設計書
4. Backtest / Investigation / Implementation Note

Phase文書や実装ノートに本書と異なる暫定式・旧方針が残っている場合、それは履歴または実装記録として扱い、本番仕様の正本とはしない。

## 10. Journal による Exobiology 採集状態の取得

### 10.1 基本方針

Exobiologyの「採集状況」は、Cargo容量・Cargo内容量から推定しない。

ゲーム内Journalに記録される `ScanOrganic` イベントを一次入力とし、アプリケーション側で対象Speciesの採集状態を管理する。

```text
Elite Dangerous Journal
        ↓
    ScanOrganic
        ↓
Collection State
        ↓
現在の System / Body / Species
        ↓
UI表示
```

C-COREのSpecies判定と採集状態は別の責務として扱う。

- **C-CORE:** この天体で成立する可能性のあるSpeciesを判定する
- **Collection State:** プレイヤーがそのSpeciesをどこまで採集・分析したかを管理する

### 10.2 ScanOrganic

`ScanOrganic` はOrganic Sampling Toolによる生物スキャンをJournalへ記録するイベントとして扱う。

主な入力項目として以下を利用する。

- `ScanType`
- `Genus`
- `Genus_Localised`
- `Species`
- `Species_Localised`
- `Variant`
- `Variant_Localised`
- `SystemAddress`
- `Body`
- `timestamp`

`ScanOrganic` の `ScanType` は、少なくとも `Log` / `Sample` / `Analyse` を区別できるものとして扱う。

### 10.3 採集状態モデル

Journalにはアプリケーション向けの `2/3` 等の完成済みカウンタが直接記録されるとは限らないため、Journalイベントからアプリケーション側で状態を再構成する。

基本状態は以下とする。

```text
UNKNOWN
LOGGED
SAMPLING
ANALYSED
```

`SAMPLING` の内部状態では、取得済みSample数を別フィールドとして保持する。

```text
sample_count = 0
sample_count = 1
sample_count = 2
sample_count = 3
```

UI上では必要に応じて以下のように表示する。

```text
採集状況 0/3
採集状況 1/3
採集状況 2/3
採集状況 3/3
```

ただし、`3/3` を単純に3件のJournalイベント数だけで確定しない。`ScanType=Analyse` を含む実際のイベント系列を基準として完了状態を確定する。

### 10.4 状態の識別単位

採集状態は最低限、以下の組み合わせで対象を識別する。

```text
SystemAddress + Body + Species
```

必要に応じて `Variant` を保持するが、Variantの違いだけでSpeciesの採集状態を別Speciesとして扱わない。

### 10.5 重複イベント

Journal再読込・アプリ再起動・同一イベントの再処理によって採集数を二重計上してはならない。

イベントには `timestamp` 等を利用した重複排除キーを設け、同一Journalイベントを複数回適用してもCollection Stateが変化しない冪等な処理とする。

### 10.6 星系・天体との紐付け

採集状態はSpecies名だけで保持せず、必ず対象天体に紐付ける。

```text
SystemAddress
  └─ Body
      └─ Species
          └─ Collection State
```

これにより、別の星系・別の天体に同一Speciesが存在しても採集済み状態を混同しない。

### 10.7 Journal再生と永続化

アプリ起動時に既存Journalを再生して現在のCollection Stateを復元できる設計とする。

実装時は、以下を満たすことを要求する。

- 最新Journalを監視できる
- 過去Journalをreplayできる
- 同一イベントの再処理が冪等である
- アプリ再起動後も必要な状態を復元できる
- 星系・天体移動後に前天体の採集状態と混同しない

### 10.8 UI表示

採集状況はC-COREの判定結果と同じカード内に表示できるが、意味を混同させない。

```text
🧬 Aleoida Arcus

判定: MATCH
価値: 12.9M

採集状況
██████░░░░ 2/3
✓ Sample
✓ Sample
○ Sample
```

候補Speciesについて、C-COREが `MATCH` でも採集状況が `0/3` なら未採集として表示する。逆に採集済みでも、現在天体に対するC-CORE判定が成立しない場合は、過去の採集記録として扱い、現在の候補とは混同しない。

### 10.9 Cargoとの責務分離

Cargo表示とExobiology採集状態は別モデルとする。

```text
Cargo State
  └─ Cargo容量 / 現在搭載量

Collection State
  └─ System / Body / Species / Sample / Analyse
```

「Cargoに入っているから採集済み」と推定する仕様は採用しない。

### 10.10 現時点の実装範囲

本節は仕様定義であり、`ScanOrganic` のJournal parserおよびCollection State実装が完了したことを意味しない。

実装前に実ゲームのJournalログを用いて以下を確認する。

1. 実際の`ScanOrganic`イベント系列
2. `Log` / `Sample` / `Analyse` の遷移
3. 同一Species・同一Bodyでの再処理時の挙動
4. 中断・失敗・再開時のイベント系列
5. `Variant` の扱い

確認結果と本仕様に差異がある場合は、実ログを一次資料として仕様を更新する。
