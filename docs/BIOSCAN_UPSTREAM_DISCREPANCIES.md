# BioScan Upstream Discrepancy Ledger

**Status:** Operational ledger  
**Scope:** BioScan ruleset と `value_estimate()` / C 正規化ルールの不整合記録  
**Purpose:** upstream の表現変更・typo・仕様差異を C の内部構造へ直接持ち込まず、発見時点の判断根拠を後から追跡可能にする。

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

## 2. 記録項目

| ID | 対象 | ruleset上の条件 | `value_estimate()`での扱い | Cでの扱い | 判断根拠 | 状態 |
|---|---|---|---|---|---|---|
| BUD-001 | Brain Tree (`region`) | ruleset側では `regions` を正規化上の条件として扱う | `region` を参照しているため ruleset と不一致 | ruleset の `regions` を正として扱う | `region` / `regions` の単複不一致。Brain Tree の条件記述における明確な表記差異として記録 | OPEN |

## 3. 状態定義

- `OPEN`: 不整合を確認済み。upstream の修正・仕様確定を待つ、または継続監視する。
- `CONFIRMED_TYPO`: typo / 表記ミスと判断済み。
- `CONFIRMED_SPEC`: 意図的な仕様差異と判断済み。
- `RESOLVED_UPSTREAM`: upstream が修正され、C 側との再確認が完了。
- `RESOLVED_LOCAL`: C 側の対応が完了し、upstream との差異を意図的に維持することを確認済み。

## 4. 更新ルール

116 Species の棚卸し中に新しい不整合を発見した場合、集計結果とは別に本ファイルへ 1 件ずつ追加する。

特に以下を同一視しない。

1. ruleset の記述ミス
2. `value_estimate()` の実装バグ
3. C の正規化仕様との差異
4. upstream の意図的な仕様変更

判断できない場合は無理に確定せず、`OPEN` として判断根拠だけを残す。

## 5. Upstream 修正時の確認手順

upstream 側で記述が修正された場合は、少なくとも以下を確認する。

1. 修正前の台帳エントリを参照する。
2. 現行 ruleset と `value_estimate()` の差異を再確認する。
3. C の正規化ルールに変更が必要か確認する。
4. 必要な場合のみ C 側を変更する。
5. 再検証後、該当エントリの状態を `RESOLVED_UPSTREAM` または `RESOLVED_LOCAL` に更新する。

## 6. Change History

- 2026-09-11: 初版。116 Species の集計開始前に、不整合を会話履歴ではなくリポジトリ上で継続管理する運用を追加。
