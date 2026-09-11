## Exobiologyモード 実装ノート（2026-09時点）

本節は仕様書の方針を変更するものではなく、
「出力はまず検証用スクリプトから着手」の実施状況を記録する追記である。
ランキングの正本は `docs/EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md` とする。

### 実装状況

- 検証用スクリプト `exo_scout.py` を作成。Journal/Status.jsonを読み、
  現在星系内の生物シグナル保持天体を cr/h でランキングする。
- 判定は3段階（FSS推定→DSS属確定→ScanOrganic種確定）で、
  段階が進むごとに期待値を上書きする方式。
- モードは live（追尾）／replay（既存Journal再生）／
  harvest-values（自分のSellOrganicDataから種価値テーブルを抽出）の3つ。
- スコアは 期待値 ÷（超空間巡航到達 + 降下 + サンプリング + 離陸）の cr/h。
  ファーストフットフォールは Journal に直接出ないため、
  WasDiscovered/WasMapped から確率係数を掛ける期待値方式で近似している。

### 未確定・要較正の項目

- `DEFAULT_GENUS_RULES` の生息条件（大気・重力・温度レンジ）と価値レンジは初期値。
  BioScan/BioInsights のデータおよび harvest-values で得た自分の実績値との
  突き合わせが未実施。
- `DEFAULT_SPECIES_VALUES` も同様に初期値。較正後は `--species-values` で
  外部JSONとして差し替える運用とし、本文の定数は書き換えない。
- 超空間巡航時間・降下/離陸時間・サンプリング移動速度の各定数も仮値。
  実プレイのタイムスタンプ差分との比較調整が必要。

### 探索範囲・UIについて

- 探索範囲は現在星系内（Journalのみで完結）を先行実装とし、
  周辺星系を含めたSpansh併用の候補提示は将来拡張として保留。
- UIは[[evproject]]と同じ2カラム+4層構造・配色を流用した
  モックアップを1点作成済みだが、これは将来像の参考であり、
  「CLIでExobiologyランキングが成立するまでUIは作らない」方針は変更していない。
