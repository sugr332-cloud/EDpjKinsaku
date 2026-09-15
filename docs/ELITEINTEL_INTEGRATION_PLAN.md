# EDpjKinsaku / EliteIntel 実装ロードマップ

## 目的

本プロジェクトの優先順位を見直す。

最優先は、既存 EliteIntel が現在提供している機能を実装対象として整理し、**ユーザー向け表示・操作・仕様を日本語へ置き換えること**である。

その次に、AI/LLM 部分を API 前提にせず **CLI Provider として差し替え可能にし、Antigravity CLI (`agy`) を利用できるようにする**。

Exobiology C-CORE は重要だが、既存 UI/操作体験の日本語化・機能置換を阻害しない。C-CORE の追加統合・拡張は後段へ回す。

## 優先順位

1. **既存機能の日本語化・現状置換**
2. **AI Provider の CLI 化と agy 対応**
3. **既存 EliteIntel 機能の日本語環境での完成度向上**
4. **音声入出力（必要に応じて VOICEVOX）**
5. **ゲーム操作 / 船体制御**
6. **HUD / Overlay / VR**
7. **汎用ゲームデータ・Trade Assistant**
8. **EDpjKinsaku C-CORE の統合・拡張**
9. **Installer / Update / Runtime packaging**

## 基本方針

- 現在存在する EliteIntel の機能を先に日本語化する。
- 日本語化のために既存機能を削除・簡略化しない。
- C-CORE を理由に既存 EliteIntel の UI / Journal / Navigation / Assistant を作り直さない。
- C-CORE の判定 Source of Truth は維持する。
- AI は判定エンジンではなく、説明・要約・推薦・自然言語対話を担当する。
- AI Provider は API に固定せず、**CLI プロセスを第一級の実装方式**として扱う。
- `agy` は交換可能な AI Provider の一実装とする。
- AI Provider の変更で Game Context や C-CORE の内部構造を変更しない。
- 実装前に read-only 調査を行い、既存コード・仕様・テストを確認する。
- 各 Phase は小さく実装し、fixture/test を先に追加する。

---

# Phase 0 — 現状固定 / Read-only baseline

## 目的

現在の EliteIntel / EDpjKinsaku の状態を変更せず、現状を固定する。

## 調査対象

- EliteIntel の現在の UI
- localization resources
- Journal / Session / Navigation
- Assistant / LLM 呼び出し部分
- 音声関連
- HUD / Overlay / VR
- EDpjKinsaku C-CORE
- 既存テスト

## 完了条件

- 既存機能をファイル単位で一覧化できる。
- 現在の日本語化済み範囲と未翻訳範囲を確定する。
- 現在の AI 呼び出し方式を確定する。
- C-CORE の現状 baseline を記録する。
- この Phase では機能変更を行わない。

---

# Phase 1 — 既存 EliteIntel 機能の日本語化 inventory

## 目的

「新機能を作る」のではなく、**現在の EliteIntel の何を日本語へ置き換える必要があるか**を確定する。

## 対象

- HUD 表示
- メニュー
- 設定
- Journal 表示
- Navigation
- Mission
- Ship status
- Cargo
- Exobiology
- Codex
- Trade
- Assistant / AI 表示
- エラー / 警告 / 状態表示
- 音声関連表示

## ルール

- 既存キーを優先して利用する。
- 同じ意味の日本語を複数箇所へ個別実装しない。
- コード内へ日本語文字列を直接大量に埋め込まない。
- 既存の localization architecture を利用する。
- UI の意味を変更せず、表示言語だけを置き換える。

## 完了条件

日本語化対象が「ファイル / localization key / UI 項目」単位で確定していること。

---

# Phase 2 — 既存機能の日本語置換【最優先実装】

## 目的

Phase 1 で確定した現在機能を、日本語 UI として実際に利用可能にする。

## 実装

- 日本語 locale の追加・完成
- HUD 文言の日本語化
- Navigation / Mission / Ship / Cargo の日本語化
- Exobiology / Codex の日本語化
- エラー・警告・状態表示の日本語化
- 設定画面の日本語化
- 既存 Assistant 表示の日本語化
- 既存機能を日本語環境で一通り操作できる状態にする

## 作業効率化ルール

日本語化の完了をキー単位の細切れ作業にしない。**カテゴリ単位でまとめて置換・検証する。**

- 1キーごとの個別コミットは行わない。
- 同一カテゴリの翻訳対象をまとめて処理する。
- 翻訳後はカテゴリ単位でキー欠落・重複・placeholder 不整合を検証する。
- 画面表示確認もカテゴリ単位でまとめて実施する。
- 小さな変更であっても、原則としてカテゴリ単位でコミットする。
- 翻訳対象と無関係なリファクタリングを同時に行わない。
- C-CORE、AI Provider、HUD/Overlay 等の後段設計へ寄り道せず、Phase 2 の日本語置換を完了させる。
- 既存の翻訳済みキーを再調査して同じ作業を繰り返さない。
- 既に検証済みのカテゴリは再検証せず、未完了カテゴリへ進む。
- エラーや曖昧な翻訳が発生した場合のみ、そのキー・カテゴリを個別に追加調査する。

### 推奨サイクル

```text
未翻訳カテゴリを抽出
      ↓
カテゴリ単位で翻訳
      ↓
機械的なキー / placeholder 検証
      ↓
必要な画面だけ表示確認
      ↓
カテゴリ単位でコミット
      ↓
次のカテゴリへ
```

この Phase では、**「翻訳 → 1キー確認 → 1キーコミット」を繰り返さない。**

## 完了条件

- 現在 EliteIntel に存在する主要機能が日本語 UI で利用できる。
- 未翻訳の英語 UI が意図せず残っていない。
- localization test が成功する。
- 既存機能の挙動を変更していない。
- 日本語化対象の全カテゴリについて、翻訳・検証・コミットが完了している。

---

# Phase 3 — AI Provider 抽象化 / CLI-first

## 目的

AI/LLM を特定 API に固定せず、**CLI を実行するだけで Provider を交換できる構造**へ変更する。

## Provider Interface

```text
Assistant Core
      ↓
AIProvider
      ├─ AgyCliProvider
      ├─ GeminiCliProvider
      └─ ClaudeCliProvider
```

## CLI Provider 共通仕様

Provider は以下を共通化する。

- executable path / command
- arguments
- stdin input
- stdout output
- stderr capture
- exit code
- timeout
- process cancellation
- malformed output handling
- provider unavailable handling

AI Provider は API client を直接呼ぶのではなく、CLI Provider では外部プロセスとして実行する。

## 完了条件

- Assistant Core が特定 LLM 実装を直接参照しない。
- CLI Provider を設定だけで切り替えられる。
- Provider の失敗が Assistant Core 全体のクラッシュにならない。

---

# Phase 4 — Antigravity CLI (`agy`) 対応

## 目的

既存 LLM 呼び出しを、**Antigravity CLI (`agy`) へ置換可能**にする。

## 実装

```text
Game Context
     ↓
Assistant Core
     ↓
AgyCliProvider
     ↓
agy process
     ↓
stdout
     ↓
Assistant response
```

## 必須仕様

- `agy` の executable path を設定可能にする。
- 引数を設定可能にする。
- Prompt / Game Context を stdin または CLI 引数の定義された方式で渡せるようにする。
- stdout を AI response として受け取る。
- stderr を診断情報として分離する。
- exit code を検証する。
- timeout を設定可能にする。
- `agy` が存在しない場合に deterministic command を継続利用できる。
- `agy` の出力が不正な場合に UI が壊れない。
- Provider 固有仕様を Game Context / C-CORE に漏らさない。

## API 方針

**AI/LLM の実装方式として外部 API を必須にしない。**

このプロジェクトでは CLI Provider を第一級として扱い、`agy` をその代表実装とする。

## 完了条件

- `agy` を Provider として選択できる。
- 固定 Game Context fixture を `agy` Provider に渡せる。
- stdout の回答を Assistant UI へ表示できる。
- `agy` の失敗時に deterministic command が継続できる。

---

# Phase 5 — 日本語 Assistant / Natural Language

## 目的

日本語化した既存機能を、日本語自然言語で問い合わせられるようにする。

## 例

```text
> 今どこにいる？
> 現在の惑星を教えて
> 貨物の残量は？
> この惑星で採取できる生物は？
> 次の目的地まで何ジャンプ？
```

## 方針

- deterministic command は LLM 不在でも利用可能。
- LLM は Game Context の説明・要約・推薦を担当する。
- ゲームの事実は Journal / Status / Session 等から取得する。
- LLM が事実を捏造して Game Context を上書きすることは禁止する。

---

# Phase 6 — STT / TTS / VOICEVOX

## 目的

日本語 Assistant に音声入出力を追加する。

## 構成

```text
STT
 ↓
Assistant Core
 ↓
AI Provider
 ↓
日本語 response
 ↓
TTS Provider
 ↓
VOICEVOX local
```

## 方針

- STT / TTS は Provider として分離する。
- VOICEVOX はローカル実行を前提とする。
- 外部 TTS API を必須依存にしない。
- VOICEVOX 未起動でもテキスト表示を継続する。

---

# Phase 7 — Game Action / Ship Control

## 目的

自然言語から許可済みのゲーム操作を要求できるようにする。

```text
Natural language
      ↓
AI / Command parser
      ↓
Action Registry
      ↓
Input Adapter
      ↓
Elite Dangerous
```

## 必須仕様

- Action Registry
- Input Adapter
- キーバインド設定
- allowlist
- dry-run
- 実行結果 verification

LLM から直接 OS キーボードイベントを発行することは禁止する。

---

# Phase 8 — HUD / Overlay / VR

## 目的

日本語 Assistant と同じ Game Context を HUD / Overlay / VR へ表示する。

対象:

- Navigation
- Mission
- Exobiology
- Current Body
- Ship
- Cargo
- AI notification

CLI と HUD で別々の状態取得を行わない。

---

# Phase 9 — Generic Game Data / Trade Assistant

## 目的

Exobiology 以外の Elite Dangerous 情報も同じ Assistant から扱う。

対象:

- Journal
- Status
- Cargo
- Mission
- Navigation
- Station
- Commodity
- Trade
- Exobiology
- Codex

最低限:

- commodity 情報
- station 情報
- where-to-sell
- trade route
- cargo
- 利益計算

---

# Phase 10 — EDpjKinsaku C-CORE 統合

## 目的

既存の日本語化・Assistant 機能が成立した後、EDpjKinsaku C-CORE を Exobiology 判定 Source of Truth として統合する。

## 境界

```text
EliteIntel / Game Context
          ↓
BodyContext Adapter
          ↓
EDpjKinsaku C-CORE
          ↓
SpeciesEvaluation
          ↓
Assistant / HUD
```

EliteIntel 側へ C-CORE ruleset をコピーしない。

## 方針

- C-CORE の内部判定を LLM に置き換えない。
- LLM は C-CORE 結果を説明・要約するだけとする。
- Java/Python 接続方式は実コード調査後に確定する。
- 最初から C-CORE を Java へ全面 port しない。

---

# Phase 11 — C-CORE 全 species / Value / Ranking

C-CORE 統合が安定した後に実施する。

- 全 species 利用
- collection state
- expected value
- ranking
- confidence

判定と価値評価を分離する。

---

# Phase 12 — Offline Assistant

## 構成

```text
Ollama CLI / local provider
        ↓
Assistant Core
        ↓
VOICEVOX local
```

ネットワーク接続なしでも、可能な範囲で日本語 Assistant を利用できる構成を完成させる。

---

# Phase 13 — Installer / Update / Runtime packaging

- Windows runtime package
- CLI launcher
- `agy` executable configuration
- AI Provider configuration
- TTS configuration
- optional HUD / VR
- version information
- update mechanism

---

# AI Provider 仕様

## Provider は交換可能であること

```text
AIProvider
 ├─ AgyCliProvider
 ├─ GeminiCliProvider
 ├─ ClaudeCliProvider
 └─ OllamaCliProvider
```

Provider の差し替えで以下を変更してはならない。

- Game Context schema
- C-CORE
- Journal state
- HUD renderer
- Action Registry

## CLI Provider の最低契約

入力:

```text
Game Context + user prompt
```

出力:

```text
Japanese response
```

エラー:

```text
process unavailable
non-zero exit
timeout
malformed output
```

これらを共通エラーとして Assistant Core が処理する。

---

# 実装順の判断基準

**「新しい内部 core を作ること」より「現在使われている機能を日本語で使えること」を常に優先する。**

したがって、C-CORE が未完成でも Phase 2〜9 の UI / Assistant / CLI / 音声 / 操作 / HUD を進めてよい。

C-CORE 統合は、既存機能の日本語化を止めるブロッカーにしない。

---

# テスト方針

## Phase 0–2

- 既存 build/test
- localization key coverage
- 日本語 locale test
- HUD / menu / settings の表示確認
- 既存機能の回帰テスト

## Phase 3–5

- Provider interface test
- CLI process test
- stdin/stdout fixture
- exit code test
- timeout test
- malformed output test
- `agy` unavailable fallback
- 日本語 prompt / response test

## Phase 6

- STT provider test
- TTS provider test
- VOICEVOX unavailable fallback

## Phase 7

- Action allowlist test
- dry-run test
- verification test
- 禁止操作 test

## Phase 8–9

- Game Context consistency
- HUD rendering
- Navigation / Mission / Cargo / Trade fixtures

## Phase 10–12

- BodyContext mapping
- C-CORE fixture
- SpeciesEvaluation preservation
- C-CORE result が AI に改変されないこと
- offline provider test

---

# 非目標

- LLM に Exobiology species 判定をさせない。
- LLM の回答をゲーム事実の Source of Truth にしない。
- C-CORE ruleset を EliteIntel 側へコピーしない。
- LLM から直接 OS キーボードイベントを発行しない。
- 日本語化より先に C-CORE を完成させることを要求しない。
- AI/LLM を特定の外部 API に固定しない。
- HUD / VR の実装を CLI の責務へ混在させない。

---

# 現在の優先作業

**次に実装するのは Phase 0 の read-only inventory → Phase 1 の日本語化対象確定 → Phase 2 の既存機能日本語置換。**

その後、Phase 3–4 で `AgyCliProvider` を追加し、現在の LLM 実装を `agy` CLI に差し替えられる状態を作る。

C-CORE の追加・拡張は、その後でよい。
