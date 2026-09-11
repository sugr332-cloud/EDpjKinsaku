# EDpjKinsaku

Elite Dangerous の **Exobiology（生物学）** 支援を目的としたプロジェクトです。

現在の仕様上の対象は Exobiology のみです。Mining、Trade、Market 等の旧仕様は対象外として整理し、関連する仕様書を削除しました。

## Exobiology

現在の実装・検証方針は、まず CLI / 検証用スクリプトから成立性を確認することです。

- Journal / Status.json を利用した現在星系の生物候補抽出
- 生物シグナル保持天体の候補評価
- FSS 推定 → DSS 属確定 → ScanOrganic 種確定の段階的更新
- Exobiology の期待価値・探索効率の評価
- `harvest-values` による自分の実績値の収集・較正
- 周辺星系・Spansh 連携は将来拡張
- UI は検証用CLIが成立した後に実装する

## ランキング正本

Exobiologyランキングの本番モデル・species predictionの昇格条件・First Footfall推定・confidence伝播・時間モデル・探索範囲の扱いは、以下を正本とします。

- `docs/EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md`

Phase文書や実装ノートに暫定的な記述が残る場合も、本番仕様については正本を優先します。

## 主要ドキュメント

Exobiology 関連の仕様・検証資料は `docs/` を参照してください。

- `docs/EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md`
- `docs/EXOBIOLOGY_IMPLEMENTATION_NOTE_2026-09.md`
- `docs/PHASE_3_BIO_VALUE_MODEL_V1_DESIGN_BASELINE_V0.1.md`
- `docs/PHASE_BIO_SPECIES_PREDICTION_BACKTEST_DESIGN_BASELINE_V0.1.md`
- `docs/BIO_EXTERNAL_DATA_VALIDATION_SPEC_V0.1.md`
- `docs/BIO_SPECIES_PREDICTION_BACKTEST_RESULT_V0.1.md`
- `docs/BIO_SPECIES_VALUE_MASTER_CROSS_REFERENCE_INVESTIGATION_V0.1.md`
- `docs/BIO_VALUE_FORMULA_BACKTEST_RESULT_V0.1.md`

## 開発方針

- 実装前に検証可能な単位へ分割する
- 未較正の定数・推定値を確定値として扱わない
- 実プレイデータと `harvest-values` による較正を優先する
- UIより先にCLIでランキング・候補評価の成立性を確認する
