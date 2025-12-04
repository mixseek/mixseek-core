# Future Enhancements: Multiple Round Support

## Overview

初期実装は1ラウンドのみだが、将来的に複数ラウンド対応を行う際の設計指針。

## RoundController拡張

- `should_continue_round()`: ラウンド継続判定
- `load_previous_round()`: 前ラウンド結果読み込み
- `update_round_state()`: ラウンド状態更新

## Orchestrator拡張

- ラウンド進行状況の監視
- ラウンド間のフィードバック統合

## 実装時の考慮事項

- FR-003: ラウンドコントローラへの委譲
- FR-004: 終了条件判定
