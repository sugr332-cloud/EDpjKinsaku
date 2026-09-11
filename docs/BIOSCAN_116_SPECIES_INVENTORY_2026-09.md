# BioScan 116 Species 棚卸し結果

**Date:** 2026-09-11  
**BioScan baseline:** `5f0d2e445a95681bf2e85223f883d5c552a7726b`  
**Repository:** `Silarn/EDMC-BioScan`  
**Scope:** baseline時点のBioScan species/ruleset と `value_estimate()` の評価器挙動、およびEDpj側のSpeciesValueMaster/C側実装との突合。

## 1. 結論

棚卸しの結果、現時点で明確に確認できた不整合は次の3系統に分かれる。

1. **BioScan ruleset → `value_estimate()` の評価器不整合:** 1件
   - Brain Tree の `region` / `regions` キー不一致。
2. **EDpj SpeciesValueMaster とBioScanの固定価値差:** 9件
   - Anemone Croceum
   - Bacterium Nebulus
   - Bacterium Scopulum
   - Brain Tree 5色
   - Tussock Ventusa
   - これらは既存の複数ソース照合調査で「判断保留」の値差として既に記録されており、今回の棚卸しではC側の値を自動変更しない。
3. **BioScan側に存在し、現行SpeciesValueMasterに存在しないcatalog entry:** 3件
   - Bark Mound
   - Amphora Plant
   - Radicoida Unicus
   - ただし本棚卸しの「116 Species」母集団にこれら3件をどこまで含めるかは、speciesとしてのスコープ定義と照合して最終確定する必要がある。

したがって、**C-COREの正規化ロジックへ直ちに反映すべき新規仕様変更は確認されていない**。まず `BUD-001` を基準とする評価器差異を維持し、固定価値9件は既存の外部データ照合結果として扱う。

## 2. Baseline確認

`5f0d2e445a95681bf2e85223f883d5c552a7726b` はBioScanの実在commitであり、2026-07-11のcommit `Dont set the ship location when docking the Nomad`。このcommitのtreeにはBioScanのspecies catalog/ruleset一式が含まれている。

BioScan `species.py` は以下のruleset catalogを統合している。

- Aleoida
- Anemone
- Bacterium
- Brain Tree
- Cactoida
- Clypeus
- Concha
- Electricae
- Fonticulua
- Frutexa
- Fumerola
- Fungoida
- Osseus
- Recepta
- Shard
- Stratum
- Tubers
- Tubus
- Tussock
- 追加のMound / Amphora / Radicoida catalog

## 3. Ruleset → value_estimate() 棚卸し

### BUD-001: Brain Tree region key

BioScanのBrain Tree rulesetには `region` という単数キーが存在する一方、`value_estimate()` の評価器側には `regions` のcaseが存在する。

結果として、rulesetに書かれたBrain Treeのregion条件と評価器の参照キーが一致しない。

これは既存台帳 `BUD-001` と一致するため、**新規BUDは発行しない**。

**判定:**

- 判断状態: `OPEN`
- 実装状態: `NOT_IMPLEMENTED`
- C側の扱い: ruleset側の正規化仕様を基準とする

## 4. 固定価値の突合

EDpjの `SpeciesValueMaster` は、BioScanから直接転記したものではなく、Fandom wiki等との独立照合を経て構築されている。既存調査では以下の9件が値不一致として残っている。

| Species | EDpj現行値 | BioScan baseline値 | 備考 |
|---|---:|---:|---|
| Anemone Croceum | 3,399,800 | 1,499,900 | disputed |
| Bacterium Nebulus | 9,116,600 | 5,289,900 | disputed |
| Bacterium Scopulum | 8,633,800 | 4,934,500 | disputed |
| Gypseeum Brain Tree | 3,565,100 | 1,593,700 | disputed |
| Ostrinum Brain Tree | 3,565,100 | 1,593,700 | disputed |
| Aureum Brain Tree | 3,565,100 | 1,593,700 | disputed |
| Puniceum Brain Tree | 3,565,100 | 1,593,700 | disputed |
| Lindigoticum Brain Tree | 3,565,100 | 1,593,700 | disputed |
| Tussock Ventusa | 3,277,700 | 3,227,700 | disputed |

これらは「BioScanの値が正しい」とはまだ判断しない。EDpj側では既に `confidence="disputed"` として扱っているため、今回の棚卸しではC側の値を変更しない。

なお、Fonticulua FluctusとConcha Biconcavisについては、既存調査で第三ソースによる補正を行い、EDpj側はBioScan baselineと一致する値になっているため、今回の差分には含めない。

## 5. SpeciesValueMaster未収載のcatalog entry

BioScan baselineには以下のcatalog entryが存在するが、現行EDpj `SpeciesValueMaster` には対応エントリが確認できない。

- Bark Mound
- Amphora Plant
- Radicoida Unicus

ただし、この3件を「116 Species」棚卸しの母集団へ含めるかは、単純なcatalog entry数ではなく、今回の棚卸しで定義したSpeciesスコープと一致させてから確定する。

特にRadicoida UnicusはHIP 87621の固有条件を持つ特殊なcatalog entryであり、通常の種条件と同じ扱いにしない。

## 6. C側実装について

現行EDpjではBioScanのrulesetをそのまま実行するC-CORE/正規化エンジンはまだ存在せず、`app/bio/species_prediction.py` はBaseline 0/1のバックテストモデル、`app/bio/species_value_master.py` は固定種価値テーブルとして実装されている。

したがって今回の棚卸しで、既存コードへ推測による正規化条件を追加することは行わない。

## 7. 次工程への判断

棚卸し結果から、C-CORE実装時に確定させるべき事項は次の順序とする。

1. `BUD-001` の `region` / `regions` 差異を正規化ルールとして明示する。
2. BioScan evaluatorの挙動をC-CORE仕様へ直接コピーせず、ruleset条件を一次入力として正規化する。
3. 固定価値9件は現時点では値変更せず、外部データ差異として保持する。
4. Bark Mound / Amphora Plant / Radicoida Unicusの116 Speciesスコープ上の扱いを確定する。
5. その後、C-COREの正規化仕様を実装する。
