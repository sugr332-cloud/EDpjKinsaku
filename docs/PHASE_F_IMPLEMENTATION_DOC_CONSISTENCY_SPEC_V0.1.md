# EDpjKinsaku Phase F — 実装・文書整合性検査

Version: 0.1  
Status: Phase Spec（実装前の確定版）  
Date: 2026-09-13  
Target repository: sugr332-cloud/EDpjKinsaku / main  
Supersedes: なし  
Superseded-by: なし

## 0. 目的と非目標

### 目的

文書が主張する数値・成果物と、リポジトリの実体との不一致を、人間の目視ではなく CI で検出できる状態を作る。

### 非目標（F では行わない）

- 不一致そのものの修正（BLOCK 1 / 2 / 6 の責務）
- docs の自動生成・自動書き換え
- 既存 docs / コード本文の変更

F は検査機構を導入するだけで、リポジトリの既存内容を 1 文字も変更しない。 これは §7 の完了条件として構造的に保証する。

## 1. F-1 Consistency Check — 検査対象

コードから実測値を取得し、文書が主張する値と突き合わせる。

| ID | 検査項目 | 実測値の取得元 |
|---|---|---|
| C1 | C-CORE 実装済み genus 数 | `app/bio/c_core.py` 内の `*_RULES: tuple[NormalizedRule, ...]` 定義の個数 |
| C2 | C-CORE 実装済み ruleset 数 | 上記 tuple 群に含まれる `NormalizedRule` インスタンスの総数 |
| C3 | species master 実装済み件数 | `len(app.bio.species_value_master.SPECIES_VALUE_MASTER)` |
| C4 | 登録済み CLI コマンド名 | `app.cli.__main__.app` の Typer グループ登録名を introspect して取得 |
| C5 | 文書が言及するコードパスの実在 | docs / README 内の `app/...py` `scripts/...py` 形式のパス |

C1 / C2 は AST で取得する。import して数える方式は将来ルールを外部データ化した際に壊れるため採らない。C3 は import して `len()` を取る（辞書リテラルのため AST でも可だが、import の方が定義漏れを検出できる）。

C5 は数値比較ではなく存在検査である。今回の `exo_scout.py` はこの項目で検出される。

### CLI サブコマンドの扱い

`harvest-values` のような「文書が機能として宣言しているサブコマンド」は、C4 の実測値（Typer 登録名）と、§2 の baseline ブロックに記載された `cli_commands` を比較して検出する。文書本文からコマンド名を推測抽出することはしない。

## 2. F-1 期待値の取得方法

### 散文からの抽出は行わない

「116 species」のような記述を日本語散文から正規表現で拾う方式は採用しない。表記揺れによる見逃しと、無関係な数値の誤検出が同時に発生し、検査そのものが信用できなくなる。

### baseline ブロック

代わりに、検査対象としたい文書に機械可読ブロックを 1 つ置く。これは第 3 の真実の置き場ではない——その文書自身の主張を、構文を固定して書き直したものである。比較対象はあくまで文書の主張であり、検査スクリプト側に期待値を持たない。

```markdown
<!-- baseline:begin -->
```yaml
c_core:
  implemented_genera: 1
  implemented_rulesets: 5
  target_genera: 20
  target_rulesets: 254
species_value_master:
  implemented_entries: 114
  target_entries: provisional
cli_commands: [journal, state, collector, api, calibration]
```
<!-- baseline:end -->
```

### 規則

1. 文書につき baseline ブロックは 0 個または 1 個。2 個以上は検査エラーとする。
2. `implemented_*` と `cli_commands` のみをコード実測値と突き合わせる。
3. `target_*` は比較しない。キーを分離すること自体が目的で、Target と Implemented を同一キーに混在させられない構造にする。今回の 20 / 116 / 254 問題はこのキー分離で再発しなくなる。
4. `target_*` には `provisional` を値として認める。BLOCK 2 完了まで species inventory が確定しないため。
5. baseline ブロックを持たない文書は F-1 の対象外。

### 段階的な実効化

F 導入時点では baseline ブロックを持つ文書は存在しない（置くのは BLOCK 1 / 2 の作業）。したがって F の時点では F-1 は実質的に C5 のみが動作する。

「baseline ブロックを持つ文書が最低 1 つ存在すること」は F ではなく BLOCK 1 の完了条件とする。 F でこれを必須にすると、F 単体で docs の変更が必要になり、§0 の非目標に反する。

## 3. F-2 Dangling Reference Check — 検出対象

### 走査範囲

- `docs/**/*.md`
- `README.md`
- `app/**/*.py`（docstring・コメント・文字列リテラルを区別せず全文）
- `scripts/**/*.py`
- `tests/**/*.py`

`__pycache__` および `.git` は除外する。

### 抽出パターン

`[A-Za-z0-9_./-]+\.md` にマッチする文字列。ただし以下は除外する。

- `http://` / `https://` で始まる URL の一部として現れるもの
- 拡張子の直前が `*`（`*.md` のようなワイルドカード表記）

### 解決規則

抽出した参照 X について、以下の順で存在を確認し、いずれにも該当しなければ dangling とする。

1. `docs/X`
2. リポジトリルートからの相対パス `X`
3. X が `docs/` で始まる場合はそのままルート相対として `X`

### 想定される初期検出

今回の監査で確認済みの既知 dangling（重複除去後）は以下。

- `SPECIFICATION_V0.4.md`
- `IMPLEMENTATION_SPEC_V0.2.md`
- `PHASE_2_2_CANDIDATE_GENERATION_DESIGN_BASELINE_V0.1.md`
- `PHASE_2_3_HORIZON_VALUE_DESIGN_BASELINE_V0.1.md`
- `CLAUDE_FORMULA_VALIDATION_DIRECTIVE_V0.1.md`
- `ABSOLUTE_FORMULA_VALIDATION_GATE_V0.1.md`
- `SPECIFICATION_TRADE_SCOPE_AMENDMENT_V0.1.md`

これは docs 側からの参照。app/ 側の docstring からはさらに `PHASE_2_4` / `PHASE_2_5*` / `PHASE_2_6*` / `MARKET_PREDICTABILITY_SPEC` 系などが加わる。allowlist の初期内容はスクリプトの初回実行結果で確定させる——本書に列挙した 7 件を手で書き写さない。手で写すと、写し漏れが即座に CI 赤になる。

## 4. allowlist

### ファイル

`.github/known_dangling.txt`

1 行 1 参照。空行と `#` 始まりの行はコメントとして無視。
各エントリに、なぜ許容されているか（どの BLOCK で解消されるか）を `#` コメントで併記する。

### 判定

```text
検出された dangling 参照
    ├─ allowlist に存在する  → 許容
    └─ allowlist に無い      → CI ERROR（新規 dangling）

allowlist のエントリ
    └─ 実際には dangling でなくなっている → CI ERROR（stale entry）
```

stale entry も必ずエラーにする。 これが無いと、BLOCK 6 で文書を復元しても allowlist に古い行が残り続け、「allowlist を空にする」という BLOCK 6 の完了条件が自動検証できなくなる。

## 5. blocking への切り替え条件

段階を分けるのは F-2 の既知分のみで、新規分は F の時点から blocking とする。

| 対象 | F 導入時 | blocking 化の時期 |
|---|---|---|
| F-2 新規 dangling | blocking | 最初から |
| F-2 既知 dangling（allowlist 掲載分） | 許容 | BLOCK 6 完了時に allowlist を空にし、ファイルごと削除 |
| F-2 stale allowlist entry | blocking | 最初から |
| F-1 C5（コードパス実在） | blocking | 最初から |
| F-1 C1〜C4（baseline 比較） | 対象文書ゼロのため実質無効 | BLOCK 1 で最初の baseline ブロックが置かれた時点で自動的に有効化 |

この配分なら、F 導入直後の CI は緑になる。既存の不整合は allowlist で明示的に許容され、新しく増える不整合だけが止まる。

## 6. CI への組み込み

### 既存 workflow の現状

`.github/workflows/bio-c-core.yml` が 1 本存在する。内容は以下で、ci.yml は存在しない。

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
```

同一ジョブ内で pytest と `scripts/real_edsm_aleoida_probe.py`（実 EDSM への live probe）を連続実行している。

### 問題

PR で走らない。  
外部サービスへの live probe と単体テストが同一ジョブなので、EDSM 側の障害・レート制限で main が赤くなる。

### F での変更

新規 workflow `.github/workflows/checks.yml` を追加する。

```text
on: pull_request + push(main)
jobs:
  checks:
    - consistency-check
    - dangling-reference-check
    - pytest
```

ネットワークアクセスを必要としない 3 つだけを置く。

既存 `bio-c-core.yml` は live probe 専用に縮小する。

- pytest ステップを削除（checks.yml に移設済みのため）
- トリガーを schedule + workflow_dispatch に変更

`continue-on-error` は使わない。同一ジョブ内で握り潰すより、workflow を分けて「PR の可否に影響しない場所へ移す」方が、probe が落ちたこと自体は可視のまま残るので望ましい。

## 7. F の完了条件

- [ ] `scripts/check_consistency.py` と `scripts/check_dangling_refs.py` が存在し、ローカルで単独実行できる
- [ ] 両スクリプトが非ゼロ終了コードと、どの参照／どの数値が問題かを示す出力を返す
- [ ] `.github/workflows/checks.yml` が追加され、PR と push(main) の両方で consistency / dangling / pytest が走る
- [ ] `.github/workflows/bio-c-core.yml` から pytest ステップが除かれ、トリガーが schedule + workflow_dispatch になっている
- [ ] `.github/known_dangling.txt` がスクリプトの初回実行結果から生成され、各行に解消予定 BLOCK がコメントされている
- [ ] 存在しない参照を 1 件追加した状態で CI が失敗することを確認した
- [ ] allowlist に実在するファイルを 1 件追加した状態で CI が失敗（stale entry 検出）することを確認した
- [ ] baseline ブロックの構文（§2）が本書で確定している
- [ ] F の差分に `docs/**` および `app/**` の変更が 1 件も含まれていない（§0 の構造的保証）

最後の 1 項目が F の性格を規定する。検査を入れるだけで、直すのは BLOCK 1 / 2 / 6 の仕事とする。

## 8. 後続 BLOCK への引き渡し

| BLOCK | F から引き継ぐ責務 |
|---|---|
| 1 | `ELITEINTEL_INTEGRATION_PLAN` に最初の baseline ブロックを置く。C1〜C4 がここで実効化する |
| 2 | species inventory 確定後、`target_entries: provisional` を確定値へ変更する |
| 6 | 消失した規範文書の回収に伴い `known_dangling.txt` を空にし、ファイルを削除する |
