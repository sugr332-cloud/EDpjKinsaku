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
