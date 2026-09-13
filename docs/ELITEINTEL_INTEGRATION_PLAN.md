# EliteIntel × EDpjKinsaku C-CORE Integration Plan

## 目的

EliteIntel を Elite Dangerous 側の Journal / Session / HUD / Navigation のホストとして利用し、EDpjKinsaku の Exobiology C-CORE を候補種判定エンジンとして接続する。

116 species の判定ロジックを EliteIntel 側へ移植せず、EDpjKinsaku C-CORE を Exobiology 判定の Source of Truth とする。

## アーキテクチャ

```text
Elite Dangerous
      │ Journal
      ▼
EliteIntel
  ├─ Journal/Event processing
  │   ├─ FSDJump
  │   ├─ FSDTarget
  │   ├─ ScanOrganic
  │   ├─ Codex
  │   └─ Location
  ├─ Session / Body / Navigation
  └─ HUD / Overlay
      │
      │ BodyContext Adapter
      ▼
EDpjKinsaku C-CORE
  ├─ 116 species
  ├─ 254 rulesets
  ├─ MATCH
  ├─ NO_MATCH
  └─ INSUFFICIENT_DATA
      │
      ▼
EliteIntel HUD
```

## Phase 0 — Repo / Build / License baseline

- EliteIntel upstream: `SudoKrondor/EliteIntel`
- EliteIntel 側で build / test / Java / Gradle / license を確認する。
- 既存コードを変更せず baseline を確定する。
- EDpjKinsaku C-CORE は既存の baseline `116 species / 254 rulesets / warnings 0` を維持する。

BLOCK 1（`docs/PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md` §2/§8）: このセクションが `scripts/check_consistency.py`（F-1）の比較対象となる baseline ブロックを持つ最初の文書。`implemented_*` と `cli_commands` のみが実測値と比較され、`target_*` は比較対象外（同spec §2 ルール3）。

<!-- baseline:begin -->
```yaml
c_core:
  implemented_genera: 6
  implemented_rulesets: 65
  target_genera: 19
  target_rulesets: 254
species_value_master:
  implemented_entries: 114
  target_entries: 115
cli_commands: [journal, state, collector, api, calibration, bio]
```
<!-- baseline:end -->

完了条件:

- EliteIntel の既存 build / test が成功
- EDpjKinsaku の既存 C-CORE baseline が成功
- 外部依存と実行方法を確認

## Phase 1 — EliteIntel read-only inventory

以下を変更せず調査する。

### Journal

- `FSDJumpEvent`
- `FSDTargetEvent`
- `ScanOrganicEvent`
- `LocationTrackingSubscriber`
- `JumpCompletedSubscriber`
- `ScanOrganicSubscriber`

### Exobiology

- `BioSampleDto`
- `BioForms`
- `ScanOrganicSubscriber`
- `CodexEntryEventSubscriber`

### HUD

- 既存 Exobiology card
- `ShipRouteCard`
- card factory / registry
- localization

### Session / Navigation

- `SystemSession`
- current system / body state
- navigation target
- route state

完了条件:

`Journal → internal state → exobiology state → HUD` のデータフローをファイル単位で把握する。

## Phase 2 — Japanese localization

EliteIntel の既存 multilingual architecture を利用する。

対象:

- `Language`
- `MultiLingualTextProvider`
- `HudText`
- `SystemSession.getLanguage()`
- localization resources
- `HudCardLocalizationTest`

日本語を既存言語切替へ追加し、HUD の翻訳キーが全言語で空にならないことをテストする。

## Phase 3 — BodyContext Adapter

EliteIntel の Body model を変更せず、薄い Adapter を追加する。

```text
EliteIntel Body
      ↓
BodyContextAdapter
      ↓
EDpjKinsaku BodyContext
```

EDpjKinsaku `BodyContext`:

- `atmosphere`
- `gravity`
- `temperature`
- `pressure`
- `body_type`
- `volcanism`
- `regions`

実際の field mapping は EliteIntel の既存 model を調査したうえで確定する。

## Phase 4 — C-CORE integration boundary

EliteIntel が C-CORE の内部 ruleset を直接参照しない境界を作る。

概念:

```python
class BioScanService:
    def evaluate_body(self, context) -> list[SpeciesEvaluation]:
        ...
```

EliteIntel が認識するのは `SpeciesEvaluation` の結果だけとする。

Java / Python の接続方式は Phase 1 の build / deployment / threading を確認してから決定する。

第一候補:

- local Python service

候補:

- localhost HTTP
- JSON stdin/stdout executable
- Java から Python を直接起動

C-CORE 自体を最初から Java へ port しない。

## Phase 5 — Aleoida vertical slice

最初は Aleoida のみで end-to-end を完成させる。

```text
EliteIntel Body
→ BodyContextAdapter
→ Aleoida C-CORE
→ SpeciesEvaluation
→ existing HUD
```

HUD 例:

```text
🧬 EXOBIOLOGY
Aleoida Arcus       12.9M
MATCH
Aleoida Coronamus    6.3M
NO MATCH
```

完了条件:

実際の ED Journal / Body state から C-CORE を呼び、結果が既存 HUD に表示される。

## Phase 6 — Collection state

C-CORE の候補判定と、実際の採集状態を分離する。

状態:

- `UNKNOWN`
- `LOGGED`
- `SAMPLING`
- `ANALYSED`

表示例:

```text
Aleoida Arcus
MATCH     2/3
```

`MATCH` は「その Body 条件で候補になる」ことを示し、`2/3` は Journal 上の採集状態を示す。

3/3 は単純な event count だけで確定せず、実際の `Analyse` sequence を確認して扱う。

## Phase 7 — All species

Aleoida の vertical slice 完了後、C-CORE が保持する全 species を EliteIntel から利用可能にする。

EliteIntel 側には genus / species ごとの判定ロジックを追加しない。

現在の C-CORE baseline:

- 19 genus entries
- 115 species
- 254 rulesets
- warnings 0

## Phase 8 — Navigation integration

EliteIntel の既存 Journal/navigation state を利用する。

主な入力:

- `FSDTarget`
- `RemainingJumpsInRoute`
- `FSDJump`

Navigation Target と Mission Target は分離する。

Game route の残りジャンプ数と、mission destination の推定ジャンプ数を混同しない。

## Phase 9 — Current Body HUD

C-CORE に渡す BodyContext と同じ情報源を HUD に利用し、表示値と判定値の不一致を避ける。

例:

```text
🪐 CURRENT BODY
Gravity     0.14 G
Temperature 174 K
Atmosphere  CO₂
```

## Phase 10 — Exobiology value / ranking

候補種判定が安定した後に価値情報を追加する。

V1 expected value:

`expected_value_base = biological_signal_count × expected_value_per_signal`

`value_confidence`:

- `HIGH`
- `MEDIUM`
- `DISPUTED`

判定ロジックと価値ランキングを分離する。

## Phase 11 — AI / TTS（VOICEVOX）

候補種判定・Navigation・Current Body の各情報が安定した後、AIによる推奨・説明を音声で提示する層を追加する。

### 目的

ゲームプレイ中に画面を注視できない場面でも、C-COREの判定結果やNavigation情報をAIが要約し、音声で通知できるようにする。

### アーキテクチャ

```text
EliteIntel
   │
   ├─ Game Context
   ├─ C-CORE Result
   └─ Mission / Navigation / Exobiology
          ↓
       AI Provider
       ├─ Gemini CLI
       └─ Claude CLI
          ↓
      日本語テキスト
          ↓
       TTS Provider
          ↓
       VOICEVOX
          ↓
        Speaker
```

4層に分離し、責務を混同しない。

```text
C-CORE      = 判定
EliteIntel  = ゲーム状態・UI
Gemini/Claude = 推奨・説明
VOICEVOX    = 音声化
```

VOICEVOXを「AIそのもの」として扱わない。VOICEVOXはTTS Providerの一実装であり、AIの判断・回答生成には関与しない。

### 設計方針

- AIの判断・回答生成は Gemini CLI / Claude CLI が担う
- 音声合成は VOICEVOX が担う
- VOICEVOX はローカル Windows 上で実行し、**外部 TTS API は使用しない**
- 音声出力は任意機能とする。VOICEVOXが無効・未起動でもテキスト表示のみで動作する
- TTS を抽象化する TTS Provider 層を設け、将来的に別の音声エンジンへ交換可能にする（VOICEVOX を C-CORE / EliteIntel 本体へ直接埋め込まない）
- 音声読み上げ用の AI 回答は短く簡潔にする
- ゲームプレイ中の通知・推奨・警告などを対象に音声化する

### 例

```text
「現在の惑星では、Aleoida Arcusが候補です。採取を続ける価値があります。」
      ↓
   VOICEVOX（例: 青山龍星）
      ↓
    音声出力
```

話者（ボイス）はTTS Provider層の設定として扱い、差し替えてもシステム設計を変更する必要がないようにする。

### ライセンス・クレジット

VOICEVOXおよび各音声ライブラリは無料で利用できるが、音声ライブラリごとに利用規約・クレジット表記の条件が異なる。使用する音声ライブラリの利用規約・クレジット条件を仕様書に明記し、遵守する。

### 完了条件

- C-CORE判定結果を含むAI回答が生成される
- AI回答がVOICEVOX経由で音声出力される
- VOICEVOX未起動時もテキスト表示のみで動作が継続する
- 使用する音声ライブラリの利用規約・クレジット表記が明記されている

## HUD 最終イメージ

```text
┌──────────────────────────────┐
│ 🚀 NAVIGATION                │
│ 現在    HIP 12345            │
│ 目的地  Sol                  │
│ 残り    17 jumps             │
├──────────────────────────────┤
│ 🧬 EXOBIOLOGY                │
│ Aleoida Arcus       12.9M    │
│ MATCH               2/3      │
│ Aleoida Gravis       12.9M   │
│ MATCH               0/3      │
├──────────────────────────────┤
│ 🪐 CURRENT BODY              │
│ Gravity     0.14 G           │
│ Temperature 174 K            │
│ Atmosphere  CO₂              │
└──────────────────────────────┘
```

## Testing

### EDpjKinsaku

- `pytest -q`
- BioScan baseline: `19 / 115 / 254 / 0`
- C-CORE fixture tests
- fixed BodyContext integration tests

### EliteIntel

- existing tests
- Japanese localization tests
- BodyContext Adapter field mapping tests
- C-CORE integration tests
- Journal replay / persistence tests
- real-game test
- AI Provider / TTS Provider abstraction tests（VOICEVOX未起動時にテキスト表示へフォールバックすることを含む）

実ゲームだけをテスト基準にせず、固定 fixture で C-CORE との接続を先に検証する。

## Non-goals

- 116 species の判定ロジックを EliteIntel にコピーしない
- EliteIntel の Journal handling を全面的に書き直さない
- 新しい HUD を別プロジェクトとして作らない
- 初期段階で C-CORE を Java へ全面 port しない
- C-CORE に合わせるため EliteIntel の Session model を無理に変更しない
- 実ゲームテストだけに依存しない
- VOICEVOX（TTS）を AI の判断・回答生成そのものとして扱わない
- 外部 TTS API に依存させない（VOICEVOX はローカル実行を前提とする）

## Commit sequence proposal

1. `chore: fork and verify EliteIntel build`
2. `feat(i18n): add Japanese language support`
3. `refactor(bio): add BodyContext adapter boundary`
4. `feat(bio): integrate Aleoida C-CORE`
5. `feat(bio): display exobiology evaluation in HUD`
6. `feat(bio): integrate collection state`
7. `feat(bio): integrate all C-CORE species`
8. `feat(hud): add navigation and body information`
9. `feat(bio): add exobiology value ranking`
10. `feat(ai): add AI provider and TTS provider abstraction (VOICEVOX)`

## First implementation step

まず Phase 0–1 の read-only inventory と build/test baseline を実施する。

この段階では EliteIntel のコード変更を行わず、既存構造と C-CORE の接続点を確定してから Phase 2 以降へ進む。
