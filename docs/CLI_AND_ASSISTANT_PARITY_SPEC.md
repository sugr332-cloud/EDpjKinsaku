# EDpjKinsaku / EliteIntel 機能拡張仕様

## 目的

既存の「Exobiology C-CORE に特化した CLI」という位置づけを拡張し、EliteIntel の LLM アシスタントで利用できる主要機能を、EDpjKinsaku 側でも段階的に利用可能にする。

本仕様では、CLI を単なる C-CORE 検証コマンドとして終了させず、**ゲーム状態取得・自然言語対話・ゲーム操作・HUD/VR・汎用ゲームデータ解析・音声入出力**を分離した拡張可能なアシスタント基盤として定義する。

ただし、C-CORE の判定ロジックを LLM に移すことは禁止する。

## 設計原則

1. C-CORE は Exobiology の判定 Source of Truth とする。
2. LLM は推奨・説明・自然言語対話を担当し、ゲーム状態の事実を勝手に生成しない。
3. ゲーム操作は明示的な Command / Action 層を介して実行する。
4. CLI、GUI/HUD、VR、音声は表示・入出力層として分離する。
5. 外部 TTS API は使用せず、ローカル TTS Provider を利用可能にする。
6. Gemini CLI / Claude CLI / Ollama は AI Provider として交換可能にする。
7. CLI 単体でも主要な情報取得・分析・自然言語対話を完結できるようにする。
8. ゲームへの直接操作を追加する場合は、操作可能なコマンドを明示的な allowlist として管理する。
9. 既存 C-CORE の ruleset を EliteIntel 側へ複製しない。
10. 実装は各 Phase ごとに fixture/test を追加し、実ゲーム依存を最小化する。

## 機能目標

### A. 音声入出力

- STT Provider 層を追加する。
- 音声入力を CLI / Assistant Command に変換する。
- TTS Provider 層を追加する。
- VOICEVOX をローカル TTS Provider として利用する。
- STT/TTS を無効にしてもテキスト CLI は動作する。
- 将来、別 STT/TTS エンジンへ交換可能にする。

### B. 自然言語対話

AI Provider 層を追加し、以下を交換可能にする。

- Gemini CLI
- Claude CLI
- Ollama

AI Provider に渡す情報は Game Context として構造化する。

```text
Game Context
 ├─ System
 ├─ Body
 ├─ Ship
 ├─ Cargo
 ├─ Mission
 ├─ Navigation
 ├─ Exobiology
 └─ Journal events
       ↓
    AI Provider
       ↓
 Japanese response
```

LLM に渡してよい事実と、C-CORE が確定した結果を区別する。

### C. ゲーム状態の汎用取得

Journal / Status / 補助データを統合し、少なくとも以下を CLI から問い合わせ可能にする。

- 現在星系
- 現在惑星 / Body
- 船情報
- Cargo / Cargo 残量
- Mission
- Navigation Target
- Remaining Jumps
- Trade 情報
- Station 情報
- Exobiology
- Codex

例:

```text
> status
> where am i
> current body
> cargo
> mission
> route
> exobiology
```

### D. 交易・売却先分析

Exobiology 専用 CLI から汎用ゲーム分析 CLI へ拡張する。

最低限:

- commodity 情報取得
- station 情報取得
- where-to-sell 相当の検索
- trade route 情報
- cargo 状態
- 利益計算

分析結果は構造化 JSON と人間向けテキストの両方を提供する。

### E. ゲーム操作

CLI からゲーム操作を要求できる Action 層を追加する。

例:

```text
> deploy landing gear
> retract landing gear
> deploy cargo scoop
> engage supercruise
> engage fsd
```

操作は LLM が直接キーコードを発行するのではなく、必ず Action Registry を経由する。

```text
Natural language
      ↓
AI / Command parser
      ↓
Action Registry
      ↓
Validated game action
      ↓
Input adapter
      ↓
Elite Dangerous
```

危険操作・戦闘操作等は安全ポリシーによって別途制限する。

### F. HUD / Overlay

CLI だけでなく、同一 Game Context を利用する表示層を追加する。

```text
Game Context
 ├─ CLI renderer
 ├─ HUD renderer
 └─ VR renderer
```

既存 EliteIntel の HUD に相当する以下を表示可能にする。

- Navigation
- Exobiology
- Current Body
- Mission
- Ship status
- Cargo
- AI notification

CLI と HUD で別々のゲーム状態を取得しない。

### G. VR

VR 表示は CLI プロセスへ直接実装せず、Overlay / VR renderer として分離する。

CLI は表示データを提供し、VR renderer が SteamVR 等の描画を担当する。

### H. オフライン AI

Ollama を AI Provider の候補として実装する。

```text
AI Provider
 ├─ Gemini CLI
 ├─ Claude CLI
 └─ Ollama
```

Provider 選択は設定で変更可能とし、特定 Provider の API 仕様を C-CORE や Game Context に直接持ち込まない。

## Phase 12 — Assistant Core / CLI conversation

### 目的

C-CORE 検証 CLI を、継続対話可能な Assistant CLI に拡張する。

### 実装

- REPL を追加する。
- `status` / `where` / `body` / `cargo` / `mission` / `route` / `exobiology` を統一 Command Interface にする。
- Game Context を JSON で取得可能にする。
- AI Provider Interface を追加する。
- Gemini CLI / Claude CLI / Ollama の Provider 境界を定義する。
- LLM の出力を事実データとして保存しない。

### 完了条件

- CLI から継続的に質問できる。
- Game Context を取得できる。
- Provider を切り替えられる。
- LLM 未起動時も deterministic command が利用できる。

## Phase 13 — STT / TTS / VOICEVOX

### 目的

CLI Assistant に音声入出力を追加する。

### 実装

- STT Provider Interface
- TTS Provider Interface
- 音声入力 → Command/Prompt
- AI response → TTS
- VOICEVOX local provider
- 未起動時のテキスト fallback

### 完了条件

- 音声で質問できる。
- 音声で Command を要求できる。
- AI 回答を VOICEVOX で読み上げられる。
- VOICEVOX が利用できなくても CLI は継続動作する。

## Phase 14 — Game Action / Ship Control

### 目的

EliteIntel の船体制御に相当する機能を追加する。

### 実装

- Action Registry
- Input Adapter
- キーバインド設定
- 操作 allowlist
- dry-run mode
- 実行結果の verification

LLM が直接 OS のキーボード入力を操作することは禁止する。

### 完了条件

- 定型マクロ名を知らなくても自然言語から許可済み Action を実行できる。
- 操作前後の状態を検証できる。
- dry-run で実行内容を確認できる。

## Phase 15 — Generic Game Data / Trade Assistant

### 目的

Exobiology 専用分析から Elite Dangerous 全般のゲーム情報分析へ拡張する。

### 対象

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

### 完了条件

- where-to-sell 相当の問い合わせが CLI から可能。
- 交易情報を取得・計算できる。
- Mission / Navigation / Cargo / Exobiology を同一 Assistant Context から問い合わせられる。

## Phase 16 — HUD / Overlay / VR renderer

### 目的

CLI と同一の Game Context を HUD / VR に表示する。

### 実装

- Renderer Interface
- HUD renderer
- Overlay renderer
- VR renderer boundary
- AI notification display

### 完了条件

- CLI と HUD が同じ Game Context を使用する。
- Navigation / Exobiology / Current Body / Mission が表示される。
- AI の通知を表示できる。
- VR renderer を独立した表示層として交換できる。

## Phase 17 — Integrated Assistant / Offline mode

### 目的

全機能を一つの Assistant として統合する。

```text
Elite Dangerous
      ↓
Journal / Status
      ↓
Game Context
      ├──────────────┐
      ↓              ↓
C-CORE           Assistant Core
      ↓              │
Exobiology          ├─ Command
      │              ├─ AI Provider
      │              ├─ STT Provider
      │              └─ TTS Provider
      │                    ↓
      └──────────────→ HUD / VR / CLI
```

### AI Provider

- Gemini CLI
- Claude CLI
- Ollama

### TTS Provider

- VOICEVOX local

### 完了条件

- オフライン構成では Ollama + VOICEVOX を利用できる。
- クラウド AI を選択した場合も Game Context / C-CORE 境界は同一である。
- CLI、HUD、VR、音声が同一 Assistant Core を利用する。
- C-CORE の判定結果が LLM によって改変されない。

## Phase 18 — Installer / Update / Runtime packaging

### 目的

独自 CLI / Assistant を実運用可能なアプリケーションとして配布する。

### 実装

- Windows runtime package
- CLI launcher
- configuration management
- AI Provider configuration
- TTS configuration
- optional HUD/VR components
- version information
- update mechanism

GUI installer は必須依存ではなく、CLI launcher 単体でも起動可能とする。

### 完了条件

- クリーン環境へ導入できる。
- CLI 単体で起動できる。
- Provider 設定を変更できる。
- 各コンポーネントを個別に無効化できる。

## 機能パリティ目標

| 機能 | 現在のCLI | 拡張後 |
|---|---:|---:|
| テキストCLI | ○ | ○ |
| C-CORE Exobiology | ○ | ○ |
| 自然言語対話 | × | ○ |
| Gemini CLI | × | ○ |
| Claude CLI | × | ○ |
| Ollama | × | ○ |
| STT | × | ○ |
| TTS | × | ○ |
| VOICEVOX | × | ○ |
| 船体操作 | × | ○ |
| Journal分析 | △ | ○ |
| Trade分析 | × | ○ |
| where-to-sell | × | ○ |
| Mission分析 | △ | ○ |
| Navigation | △ | ○ |
| HUD | × | ○ |
| Overlay | × | ○ |
| VR | × | ○ |
| オフライン運用 | C-COREのみ | ○ |
| インストーラー | × | ○ |
| 自動更新 | × | ○ |

## 非目標

- LLM に Exobiology の species 判定をさせる。
- LLM の回答を Source of Truth とする。
- C-CORE ruleset を EliteIntel 側へコピーする。
- LLM から直接キーボードイベントを発生させる。
- HUD / VR のために CLI の責務へ描画コードを混在させる。
- 外部 TTS API を必須依存にする。

## テスト方針

各 Phase で fixture test を先に実施する。

### CLI

- REPL command tests
- JSON output tests
- Game Context tests
- Provider selection tests

### AI

- deterministic context fixture
- provider failure fallback
- malformed response handling
- C-CORE result preservation

### Game Action

- allowlist tests
- dry-run tests
- action verification tests

### Audio

- STT provider tests
- TTS provider tests
- VOICEVOX unavailable fallback

### HUD / VR

- renderer contract tests
- Game Context consistency tests
- AI notification rendering tests

## フェーズ実装順

既存 Phase 0–11 の完了後、以下を順番に実施する。

12. Assistant Core / CLI conversation
13. STT / TTS / VOICEVOX
14. Game Action / Ship Control
15. Generic Game Data / Trade Assistant
16. HUD / Overlay / VR renderer
17. Integrated Assistant / Offline mode
18. Installer / Update / Runtime packaging

**Phase 12–18 は、Phase 11 の AI/TTS 仕様を置き換えるものではなく、CLI・音声・操作・表示・配布まで含めた機能拡張として追加する。**
