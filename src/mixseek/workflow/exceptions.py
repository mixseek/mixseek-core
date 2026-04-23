"""Workflow mode の例外定義。"""


class WorkflowStepFailedError(Exception):
    """Workflow ステップ継続不能な失敗時に raise される例外。

    主に function executor の ERROR（D4）や `build_executable` の
    動的 import 失敗時に `WorkflowEngine._execute_step` が昇格させる。
    後続ステップは実行されない。

    Attributes:
        step_id: 失敗したステップの ID
        executor_name: 失敗原因となった executor 名
        error_message: エラーメッセージ（executor 由来 or build 時の理由）
    """

    def __init__(
        self,
        *,
        step_id: str,
        executor_name: str,
        error_message: str | None,
    ) -> None:
        self.step_id = step_id
        self.executor_name = executor_name
        self.error_message = error_message
        super().__init__(f"Workflow step '{step_id}' failed at executor '{executor_name}': {error_message}")
