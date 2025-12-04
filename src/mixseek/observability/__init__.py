"""Observability module for mixseek.

このモジュールは以下の観測機能を提供します:

1. 標準ロギング統合 (Path 1):
   - setup_logging(): Python標準loggingの設定
   - コンソール、ファイル、Logfireへの出力

2. Logfireスパン出力 (Path 2):
   - setup_logfire(): Logfire observabilityの初期化
   - ConsoleOptionsによるローカル出力

3. 複数出力先サポート:
   - TeeWriter: 複数出力先への同時書き込み
"""

from mixseek.observability.logfire import setup_logfire
from mixseek.observability.logging_setup import setup_logging
from mixseek.observability.tee_writer import TeeWriter

__all__ = ["setup_logfire", "setup_logging", "TeeWriter"]
