"""Mixseek UI - Streamlit application entrypoint."""

import os
from pathlib import Path

import streamlit as st

from mixseek.config.logging import LoggingConfig
from mixseek.observability import setup_logging
from mixseek.ui.utils.workspace import get_workspace_path

# Configure Streamlit page (must be the first Streamlit command)
st.set_page_config(
    page_title="Mixseek UI",
    page_icon=":material/play_arrow:",
    layout="wide",
)

# Set logo (displayed in sidebar)
logo_path = Path(__file__).parent / "assets" / "mixseek700x144_Navy.svg"
if logo_path.exists():
    st.logo(str(logo_path))

# Validate MIXSEEK_WORKSPACE environment variable (Article 9)
try:
    workspace_path = get_workspace_path()
except ValueError as e:
    st.error(str(e))
    st.stop()

# Initialize standard logging (FR-026: 実行ログ表示機能)
# セッション状態でガードし、一度だけ実行
if "logging_initialized" not in st.session_state:
    logging_config = LoggingConfig(
        log_level="info",
        console_enabled=True,
        file_enabled=True,
        logfire_enabled=os.getenv("LOGFIRE_ENABLED") == "1",
    )
    setup_logging(logging_config, workspace=workspace_path)
    st.session_state.logging_initialized = True

# Initialize Logfire if enabled (environment variable check)
# セッション状態でガードし、一度だけ実行
if "logfire_initialized" not in st.session_state:
    st.session_state.logfire_initialized = False

if os.getenv("LOGFIRE_ENABLED") == "1" and not st.session_state.logfire_initialized:
    try:
        from mixseek.config.logfire import LogfireConfig
        from mixseek.observability import setup_logfire

        logfire_config = LogfireConfig.from_env()
        setup_logfire(logfire_config)

        st.session_state.logfire_initialized = True
        st.session_state.logfire_status = f"Logfire enabled ({logfire_config.privacy_mode.value})"
    except ImportError:
        st.session_state.logfire_status = "Logfire not installed (uv sync --extra logfire)"
    except Exception as e:
        st.session_state.logfire_status = f"Logfire initialization failed: {e}"

# サイドバーに観測状態を表示
if "logfire_status" in st.session_state:
    if "enabled" in st.session_state.logfire_status:
        st.sidebar.success(st.session_state.logfire_status)
    elif "not installed" in st.session_state.logfire_status:
        st.sidebar.warning(st.session_state.logfire_status)
    else:
        st.sidebar.error(st.session_state.logfire_status)

# Initialize global session state
if "workspace_path" not in st.session_state:
    st.session_state.workspace_path = workspace_path

# Define pages using st.Page()
execution_page = st.Page(
    "pages/1_execution.py",
    title="実行",
    icon=":material/play_arrow:",
    default=True,
)

results_page = st.Page(
    "pages/2_results.py",
    title="結果",
    icon=":material/leaderboard:",
)

history_page = st.Page(
    "pages/3_history.py",
    title="履歴",
    icon=":material/history:",
)

# Create navigation
pg = st.navigation([execution_page, results_page, history_page])

# Display workspace path in sidebar
with st.sidebar:
    st.markdown("### ワークスペース")
    st.code(str(workspace_path), language="text")

# Run the selected page
pg.run()
