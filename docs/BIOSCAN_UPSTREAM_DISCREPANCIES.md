# BioScan Upstream Discrepancy Ledger

**Status:** Operational ledger  
**Scope:** BioScan ruleset と `value_estimate()` / C 正規化ルールの不整合記録  
**Purpose:** upstream の表現変更・typo・仕様差異を C の内部構造へ直接持ち込まず、発見時点の判断根拠を後から追跡可能にする。

**baseline_commit:** `5f0d2e445a95681bf2e85223f883d5c552a7726b`  
**baseline_scope:** 116 Species 集計は上記 BioScan コミット時点を基準とする。以後の upstream 更新は、基準との差分として扱う。

## 1. 運用原則

依存関係は以下の一方向を維持する。

```text
一次資料 → BioScan ruleset → C の正規化ルール
```

- Canonn 等の upstream 表現を C の内部構造へ直接反映しない。
- ruleset と `value_estimate()` の食い違いを発見した場合、この台帳へ記録する。
- 明確な typo と断定できないものは、判断が確定するまで保留として記録する。
- 台帳は「C 側の例外実装一覧」ではなく、upstream と実装の差異を追跡するための監査記録とする。
- upstream が将来修正された場合は、修正前後の挙動と C 側の変更要否をこの台帳から追跡できる状態にする。
- 判断状態と実装状態は別軸で管理する。判断が確定したことと、C 側へ反映済みであることを同一視しない。

## 2. 記録項目

| ID | 対象 | ruleset上の条件 | `value_estimate()`での扱い | Cでの扱い | 判断根拠 | 状態 | 実装状態 |
|---|---|---|---|---|---|---|---|
| BUD-001 | Brain Tree (`region`) | ruleset側では `regions` を正規化上の条件として扱う | `region` を参照しているため ruleset と不一致 | ruleset の `regions` を正として扱う | `region` / `regions` の単複不一致。Brain Tree の条件記述における明確な表記差異として記録 | OPEN | NOT_IMPLEMENTED |
| BUD-002 | Stratum (`$Codex_Ent_Stratum_04_Name;`、`stratum.py`) | `catalog`直下（genus階層の外）に、`$Codex_Ent_Stratum_04_Name;`を種コードとする孤立エントリが存在する。`name: 'Stratum Aranaemus'`、`rulesets: []`（0件）。一方、正規のgenus階層(`$Codex_Ent_Stratum_Genus_Name;`)内にも同一種コード`$Codex_Ent_Stratum_04_Name;`で`name: 'Stratum Araneamus'`、`rulesets`1件のエントリが別途存在する（綴りが"Aranaemus"と"Araneamus"で異なる） | 未調査（`app/bio/value.py`等の現行`value_estimate()`がStratum genusをどう扱っているか未確認） | 現時点でC-CORE(`app/bio/c_core.py`)はAleoida属のみ実装済みで、Stratum genusは未変換のため影響なし | `scripts/count_bioscan_rulesets.py`のAnnAssign対応修正後、baseline commit `5f0d2e445a95681bf2e85223f883d5c552a7726b`に対して19ファイル全走査した際に発見。genus_entries合計が19ファイルに対し20となる原因はこの孤立エントリ。typo(綴り違い)か仕様上の別種かは未確定のため判断を保留する | OPEN | NOT_IMPLEMENTED |

## 3. 状態定義

### 3.1 判断状態

- `OPEN`: 不整合を確認済み。upstream の修正・仕様確定を待つ、または継続監視する。
- `CONFIRMED_TYPO`: typo / 表記ミスと判断済み。
- `CONFIRMED_SPEC`: 意図的な仕様差異と判断済み。
- `RESOLVED_UPSTREAM`: upstream 側の変更を確認し、その変更内容に対する C 側の再確認が完了。
- `RESOLVED_LOCAL`: upstream を待たず、C 側の正規化上の判断を確定し、差異を意図的に維持することを確認済み。

### 3.2 実装状態

- `NOT_IMPLEMENTED`: 判断結果が C 側へまだ反映されていない、または upstream 変更後の再同期が必要な状態。
- `IMPLEMENTED`: 現在の判断結果が C 側へ反映済みで、対象データ・正規化ルールとの整合確認も完了している状態。

実装状態は判断状態とは独立して記録する。したがって、例えば `CONFIRMED_TYPO + NOT_IMPLEMENTED` は「typo と判断済みだが C 未反映」を意味する。

## 4. 状態遷移と Upstream 修正時の分岐

判断状態の基本遷移は以下とする。

```text
OPEN
 ├─→ CONFIRMED_TYPO
 ├─→ CONFIRMED_SPEC
 ├─→ RESOLVED_UPSTREAM
 └─→ RESOLVED_LOCAL
```

実装状態は以下の独立軸で管理する。

```text
NOT_IMPLEMENTED → IMPLEMENTED
```

特に `RESOLVED_UPSTREAM` へ遷移する場合、upstream の修正内容を次の2種類に分ける。

1. **評価器のバグ修正**
   - 既存 ruleset の記述どおりに動くよう `value_estimate()` 側だけが修正されたケース。
   - BioScan の評価器が C の既存ルールへ追いつく修正であり、C 側の変更は不要。
   - この場合、C が基準どおりであることを再確認したうえで、実装状態は変更しない。

2. **ruleset / 価値データそのものの変更**
   - Frontier の仕様変更、価値の再計算、条件の更新などにより、C が参照している基準自体が変更されたケース。
   - C 側の参照値・正規化ルールが古くなるため、`IMPLEMENTED` のまま維持してはならない。
   - この場合、`RESOLVED_UPSTREAM` への遷移と同時に実装状態を強制的に `NOT_IMPLEMENTED` へ戻し、再同期・再検証を要求する。

つまり、`RESOLVED_UPSTREAM` は「C 側も対応済み」を意味しない。upstream の変更種別と実装状態を必ず別々に確認する。

## 5. 116 Species 棚卸し時の運用

116 Species の棚卸し中に新しい不整合を発見した場合、集計結果とは別に本ファイルへ 1 件ずつ追加する。

特に以下を同一視しない。

1. ruleset の記述ミス
2. `value_estimate()` の実装バグ
3. C の正規化仕様との差異
4. upstream の意図的な仕様変更
5. upstream 修正による評価器側の追随
6. upstream による ruleset / 価値データ自体の更新

判断できない場合は無理に確定せず、`OPEN` として判断根拠だけを残す。

## 6. Upstream 修正時の確認手順

upstream 側で記述またはデータが修正された場合は、少なくとも以下を確認する。

1. 修正前の台帳エントリを参照する。
2. 現行 ruleset と `value_estimate()` の差異を再確認する。
3. upstream の変更が「評価器のバグ修正」か「ruleset / 価値データの変更」かを分類する。
4. 「評価器のバグ修正」の場合、C の変更は不要であることを確認する。
5. 「ruleset / 価値データの変更」の場合、実装状態を `NOT_IMPLEMENTED` に戻し、C 側の再同期対象として扱う。
6. 必要な場合のみ C 側を変更する。
7. 再検証後、判断状態と実装状態をそれぞれ更新する。

## 7. Baseline 更新時の扱い

BioScan が更新された場合、既存台帳を無条件に現在版へ上書きしない。

- `baseline_commit` は、当該 116 Species 棚卸しを再現するための監査基準として保持する。
- 新しい upstream commit を監査対象とする場合は、旧 baseline との差分を確認したうえで新しい baseline を明示する。
- baseline を更新した場合、Change History に旧 commit、新 commit、更新理由を記録する。
- 既存エントリの判断状態・実装状態は、baseline 更新だけを理由に自動変更しない。変更内容を確認した結果に応じて個別に更新する。

## 8. Change History

- 2026-09-11: 初版。116 Species の集計開始前に、不整合を会話履歴ではなくリポジトリ上で継続管理する運用を追加。
- 2026-09-11: 判断状態と実装状態を分離。`RESOLVED_UPSTREAM` を評価器バグ修正と ruleset / 価値データ変更に分岐させ、後者では `NOT_IMPLEMENTED` へ戻す運用を追加。BioScan baseline commit `5f0d2e445a95681bf2e85223f883d5c552a7726b` を明記。
- 2026-09-11: `scripts/count_bioscan_rulesets.py`の`ast.AnnAssign`対応修正後、baseline全19ファイルの走査でStratum genusの構造異常(`$Codex_Ent_Stratum_04_Name;`の孤立エントリ、Aranaemus/Araneamusの綴り違い)を発見し、BUD-002として追加。
