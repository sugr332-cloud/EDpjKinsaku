# EDpjKinsaku / EliteIntel 機能パリティ仕様

## 目的

本仕様の目的は、EDpjKinsaku を C-CORE だけの独立ソフトとして拡張することではない。

**優先するのは、現在の EliteIntel が持つユーザー向け機能・表示・操作を日本語環境へ置き換えること。**

そのうえで、既存の AI/LLM 部分を特定 API に固定せず、**CLI Provider として差し替え可能にし、Antigravity CLI (`agy`) を利用できるようにする**。

EDpjKinsaku C-CORE の Exobiology 判定は Source of Truth として維持するが、既存機能の日本語置換より後回しとする。

## 優先順位

1. 現在の EliteIntel 機能を日本語へ置換
2. 日本語 UI の回帰テストと未翻訳箇所の解消
3. AI Provider の CLI-first 抽象化
4. `agy` CLI Provider の実装
5. 日本語自然言語 Assistant
6. STT / TTS / VOICEVOX
7. Game Action / Ship Control
8. HUD / Overlay / VR
9. Journal / Trade 等の汎用分析
10. EDpjKinsaku C-CORE 統合・全 species / value / ranking
11. Offline / packaging / installer

## 設計原則

1. 現在の機能を先に日本語化し、同等機能を後から作り直す順序にしない。
2. 日本語化は UI の意味・挙動を変更せず、表示言語を置き換える。
3. 既存 localization architecture を優先する。
4. AI は説明・要約・推薦・自然言語対話を担当する。
5. ゲーム状態の事実は Journal / Status / Session 等を Source of Truth とする。
6. AI Provider は交換可能にする。
7. CLI Provider は外部プロセスとして実行できることを共通契約にする。
8. `agy` を第一級の CLI Provider として扱う。
9. AI/LLM の利用に外部 API を必須化しない。
10. C-CORE の species 判定を LLM に委譲しない。
11. C-CORE ruleset を EliteIntel 側へ複製しない。
12. LLM から直接 OS キーボードイベントを発行しない。

---

# A. 現在の EliteIntel 機能の日本語置換

## 対象

- HUD
- メニュー
- 設定
- Journal
- Navigation
- Mission
- Ship status
- Cargo
- Exobiology
- Codex
- Trade
- Assistant / AI 表示
- エラー / 警告 / 状態表示
- 音声関連 UI

## 完了条件

- 現在の主要機能を日本語 UI で利用できる。
- 既存機能を削除・簡略化していない。
- localization key coverage が通る。
- 既存テストが通る。

---

# B. AI Provider / CLI-first

AI を特定サービスの API client に固定しない。

```text
Assistant
   ↓
AIProvider
   ├─ AgyCliProvider
   ├─ GeminiCliProvider
   ├─ ClaudeCliProvider
   └─ OllamaCliProvider
```

Provider の最低契約:

```text
input  = Game Context + user prompt
output = Japanese response
```

共通して扱う状態:

- process unavailable
- non-zero exit
- timeout
- cancellation
- malformed output

---

# C. Antigravity CLI (`agy`) 置換仕様

## 目的

既存の LLM 呼び出し部分を `agy` CLI に差し替えられるようにする。

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

## 必須要件

- `agy` executable path を設定可能
- CLI arguments を設定可能
- Prompt / Game Context を定義された入力方式で渡せる
- stdout と stderr を分離
- exit code を確認
- timeout を設定可能
- process cancellation を扱う
- `agy` 不在時も deterministic command を継続
- 不正な `agy` 出力で UI を壊さない
- Provider 固有仕様を Game Context に持ち込まない

## 禁止

- Game Context を `agy` 専用形式へ固定する
- C-CORE を `agy` の prompt に置き換える
- `agy` の回答をゲーム状態の Source of Truth とする
- AI API を必須依存に戻す

---

# D. 日本語自然言語 Assistant

日本語化された既存機能を自然言語から問い合わせ可能にする。

例:

```text
今どこにいる？
現在の惑星は？
貨物の残量は？
次の目的地まで何ジャンプ？
この惑星で何を採取できる？
```

deterministic command は AI Provider がなくても利用可能とする。

---

# E. 音声

```text
STT
 ↓
Assistant
 ↓
AI Provider
 ↓
Japanese response
 ↓
TTS Provider
 ↓
VOICEVOX local
```

- STT / TTS を Provider として分離する。
- VOICEVOX はローカル実行を前提とする。
- VOICEVOX が使えない場合はテキスト表示へフォールバックする。
- 外部 TTS API を必須依存にしない。

---

# F. Game Action / Ship Control

自然言語から許可済み Action を要求できるようにする。

```text
Natural language
 ↓
Command parser
 ↓
Action Registry
 ↓
Input Adapter
 ↓
Elite Dangerous
```

- Action Registry
- allowlist
- キーバインド設定
- dry-run
- 実行結果 verification

LLM が直接 OS の入力イベントを発行することは禁止する。

---

# G. HUD / Overlay / VR

CLI と HUD / Overlay / VR は同一 Game Context を使用する。

対象:

- Navigation
- Mission
- Exobiology
- Current Body
- Ship
- Cargo
- AI notification

描画責務を CLI / Assistant Core に混在させない。

---

# H. 汎用ゲームデータ分析

同一 Assistant Context から以下を扱えるようにする。

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

# I. C-CORE 統合

日本語化・Assistant・CLI Provider の基盤が成立した後に実施する。

```text
EliteIntel Game Context
        ↓
BodyContext Adapter
        ↓
EDpjKinsaku C-CORE
        ↓
SpeciesEvaluation
        ↓
Assistant / HUD
```

C-CORE は Exobiology 判定の Source of Truth とする。

LLM は C-CORE の判定結果を変更せず、説明・要約・推薦だけを行う。

---

# 機能パリティ目標

| 機能 | 現状 | 目標 |
|---|---:|---:|
| 既存 EliteIntel UI | 既存 | 日本語置換 |
| Text CLI | ○ | ○ |
| C-CORE Exobiology | ○ | ○ |
| 日本語自然言語対話 | × | ○ |
| `agy` CLI | × | ○ |
| Gemini CLI | × | ○ |
| Claude CLI | × | ○ |
| Ollama CLI | × | ○ |
| STT | × | ○ |
| TTS | × | ○ |
| VOICEVOX | × | ○ |
| Ship Control | × | ○ |
| Journal Analysis | △ | ○ |
| Mission Analysis | △ | ○ |
| Navigation | △ | ○ |
| Trade / where-to-sell | × | ○ |
| HUD / Overlay | × | ○ |
| VR | × | ○ |
| Offline Assistant | C-COREのみ | ○ |
| Installer / Update | × | ○ |

---

# 非目標

- LLM に species 判定をさせる。
- LLM をゲーム事実の Source of Truth にする。
- C-CORE ruleset を EliteIntel へコピーする。
- AI Provider を外部 API に固定する。
- LLM から直接キーボードイベントを発生させる。
- 日本語化より先に C-CORE を完成させることを要求する。
- HUD / VR の描画責務を CLI へ混在させる。

---

# 実装順

**最初に現在の EliteIntel の機能を日本語へ置き換える。**

日本語化が一段落した後に、AI Provider 抽象化 → `AgyCliProvider` → 日本語自然言語 Assistant の順で進める。

C-CORE 統合は後段であり、日本語化・既存機能置換のブロッカーにしない。
