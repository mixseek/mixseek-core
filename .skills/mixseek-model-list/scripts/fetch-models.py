#!/usr/bin/env python3
"""
Fetch available LLM models from provider APIs.

Usage:
    fetch-models.py [--provider PROVIDER] [--format FORMAT] [--fallback-only] [--json] [--verbose]

FR-008: model-list skill must fetch model lists from Google Gemini, Anthropic Claude, and OpenAI.
Falls back to docs/data/valid-models.csv when API is unavailable.

Article 9 Compliance:
- API keys are explicitly sourced from environment variables
- Fallback usage is clearly warned
- No implicit defaults or assumed values
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# Constants
API_TIMEOUT_SECONDS = 10
FALLBACK_CSV_PATH = "docs/data/valid-models.csv"

# Provider configurations
PROVIDER_CONFIGS: dict[str, dict[str, str]] = {
    "google": {
        "api_key_env": "GOOGLE_API_KEY",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
        "mixseek_prefix": "google-gla",
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "endpoint": "https://api.openai.com/v1/models",
        "mixseek_prefix": "openai",
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "endpoint": "https://api.anthropic.com/v1/models",
        "mixseek_prefix": "anthropic",
    },
    "grok": {
        "api_key_env": "GROK_API_KEY",
        "endpoint": "https://api.x.ai/v1/models",
        "mixseek_prefix": "grok",
    },
}


@dataclass
class ModelInfo:
    """Model information structure."""

    model_id: str
    provider: str
    name: str
    plain_compatible: bool = True
    code_exec_compatible: bool = False

    def to_mixseek_format(self) -> str:
        """Return model in MixSeek format (provider:model-id)."""
        prefix = PROVIDER_CONFIGS.get(self.provider, {}).get("mixseek_prefix", self.provider)
        return f"{prefix}:{self.model_id}"


def fetch_google_models(api_key: str, verbose: bool = False) -> list[ModelInfo]:
    """Fetch available models from Google Generative AI API."""
    endpoint = f"{PROVIDER_CONFIGS['google']['endpoint']}?key={api_key}"

    if verbose:
        print("[google] Fetching from API...", file=sys.stderr)

    request = urllib.request.Request(endpoint)
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        if verbose:
            print(f"[google] API error: {e}", file=sys.stderr)
        raise

    models: list[ModelInfo] = []
    for model in data.get("models", []):
        model_name: str = model.get("name", "")
        # Format: models/gemini-2.5-pro -> gemini-2.5-pro
        model_id = model_name.replace("models/", "") if model_name.startswith("models/") else model_name

        # Filter to generative models only
        supported_methods = model.get("supportedGenerationMethods", [])
        if "generateContent" not in supported_methods:
            continue

        display_name = model.get("displayName", model_id)
        models.append(
            ModelInfo(
                model_id=model_id,
                provider="google",
                name=display_name,
                plain_compatible=True,
                code_exec_compatible=False,
            )
        )

    if verbose:
        print(f"[google] Found {len(models)} models", file=sys.stderr)

    return models


def fetch_openai_models(api_key: str, verbose: bool = False) -> list[ModelInfo]:
    """Fetch available models from OpenAI API."""
    endpoint = PROVIDER_CONFIGS["openai"]["endpoint"]

    if verbose:
        print("[openai] Fetching from API...", file=sys.stderr)

    request = urllib.request.Request(endpoint)
    request.add_header("Authorization", f"Bearer {api_key}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        if verbose:
            print(f"[openai] API error: {e}", file=sys.stderr)
        raise

    models: list[ModelInfo] = []
    for model in data.get("data", []):
        model_id: str = model.get("id", "")

        # Filter to chat models (gpt-*, o1-*, o3-*, o4-*, chatgpt-*)
        if not any(model_id.startswith(prefix) for prefix in ("gpt-", "o1", "o3", "o4", "chatgpt-")):
            continue

        # Skip non-chat models (embedding, tts, whisper, dall-e, etc.)
        skip_patterns = ("embedding", "tts", "whisper", "dall-e", "davinci", "babbage", "ada", "realtime", "audio")
        if any(pattern in model_id.lower() for pattern in skip_patterns):
            continue

        models.append(
            ModelInfo(
                model_id=model_id,
                provider="openai",
                name=model_id,
                plain_compatible=True,
                code_exec_compatible=False,
            )
        )

    if verbose:
        print(f"[openai] Found {len(models)} models", file=sys.stderr)

    return models


def fetch_anthropic_models(api_key: str, verbose: bool = False) -> list[ModelInfo]:
    """Fetch available models from Anthropic API."""
    endpoint = PROVIDER_CONFIGS["anthropic"]["endpoint"]

    if verbose:
        print("[anthropic] Fetching from API...", file=sys.stderr)

    request = urllib.request.Request(endpoint)
    request.add_header("x-api-key", api_key)
    request.add_header("anthropic-version", "2023-06-01")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        if verbose:
            print(f"[anthropic] API error: {e}", file=sys.stderr)
        raise

    models: list[ModelInfo] = []
    for model in data.get("data", []):
        model_id: str = model.get("id", "")
        display_name: str = model.get("display_name", model_id)

        models.append(
            ModelInfo(
                model_id=model_id,
                provider="anthropic",
                name=display_name,
                plain_compatible=True,
                code_exec_compatible=True,  # All Anthropic models support code execution
            )
        )

    if verbose:
        print(f"[anthropic] Found {len(models)} models", file=sys.stderr)

    return models


def fetch_grok_models(api_key: str, verbose: bool = False) -> list[ModelInfo]:
    """Fetch available models from Grok (xAI) API."""
    endpoint = PROVIDER_CONFIGS["grok"]["endpoint"]

    if verbose:
        print("[grok] Fetching from API...", file=sys.stderr)

    request = urllib.request.Request(endpoint)
    request.add_header("Authorization", f"Bearer {api_key}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        if verbose:
            print(f"[grok] API error: {e}", file=sys.stderr)
        raise

    models: list[ModelInfo] = []
    for model in data.get("data", []):
        model_id: str = model.get("id", "")

        models.append(
            ModelInfo(
                model_id=model_id,
                provider="grok",
                name=model_id,
                plain_compatible=True,
                code_exec_compatible=False,
            )
        )

    if verbose:
        print(f"[grok] Found {len(models)} models", file=sys.stderr)

    return models


def load_fallback_csv(csv_path: str, provider_filter: str | None = None, verbose: bool = False) -> list[ModelInfo]:
    """Load models from fallback CSV file."""
    if verbose:
        print(f"[fallback] Loading from {csv_path}...", file=sys.stderr)

    # Try to find the CSV file relative to project root
    search_paths = [
        Path(csv_path),
        Path(__file__).parent.parent.parent.parent / csv_path,  # From .skills/mixseek-model-list/scripts/
        Path.cwd() / csv_path,
    ]

    csv_file: Path | None = None
    for path in search_paths:
        if path.exists():
            csv_file = path
            break

    if csv_file is None:
        if verbose:
            print(f"[fallback] CSV file not found: {csv_path}", file=sys.stderr)
        return []

    models: list[ModelInfo] = []
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            provider = row.get("provider", "")

            # Apply provider filter if specified
            if provider_filter and provider != provider_filter:
                continue

            model_id = row.get("model_id", "")
            name = row.get("name", model_id)
            plain_compatible = row.get("plain_compatible", "True").lower() == "true"
            code_exec_compatible = row.get("code_exec_compatible", "False").lower() == "true"

            models.append(
                ModelInfo(
                    model_id=model_id,
                    provider=provider,
                    name=name,
                    plain_compatible=plain_compatible,
                    code_exec_compatible=code_exec_compatible,
                )
            )

    if verbose:
        print(f"[fallback] Loaded {len(models)} models", file=sys.stderr)

    return models


def fetch_models_for_provider(
    provider: str,
    fallback_only: bool = False,
    verbose: bool = False,
) -> tuple[list[ModelInfo], bool]:
    """
    Fetch models for a single provider.

    Returns:
        Tuple of (models, used_fallback)
    """
    config = PROVIDER_CONFIGS.get(provider)
    if config is None:
        print(f"Warning: Unknown provider: {provider}", file=sys.stderr)
        return [], True

    api_key_env = config["api_key_env"]
    api_key = os.environ.get(api_key_env, "")

    # Use fallback if requested or if API key is not set
    if fallback_only or not api_key:
        if not api_key and not fallback_only:
            print(f"Warning: {api_key_env} not set, using fallback for {provider}", file=sys.stderr)
        models = load_fallback_csv(FALLBACK_CSV_PATH, provider_filter=provider, verbose=verbose)
        return models, True

    # Try to fetch from API
    fetch_functions = {
        "google": fetch_google_models,
        "openai": fetch_openai_models,
        "anthropic": fetch_anthropic_models,
        "grok": fetch_grok_models,
    }

    fetch_func = fetch_functions.get(provider)
    if fetch_func is None:
        print(f"Warning: No API fetch function for provider: {provider}", file=sys.stderr)
        return load_fallback_csv(FALLBACK_CSV_PATH, provider_filter=provider, verbose=verbose), True

    try:
        models = fetch_func(api_key, verbose=verbose)
        return models, False
    except Exception as e:
        print(f"Warning: API fetch failed for {provider}: {e}, using fallback", file=sys.stderr)
        return load_fallback_csv(FALLBACK_CSV_PATH, provider_filter=provider, verbose=verbose), True


def fetch_all_models(
    providers: Sequence[str],
    fallback_only: bool = False,
    verbose: bool = False,
) -> tuple[list[ModelInfo], dict[str, bool]]:
    """
    Fetch models from all specified providers.

    Returns:
        Tuple of (all_models, fallback_used_by_provider)
    """
    all_models: list[ModelInfo] = []
    fallback_status: dict[str, bool] = {}

    for provider in providers:
        models, used_fallback = fetch_models_for_provider(provider, fallback_only, verbose)
        all_models.extend(models)
        fallback_status[provider] = used_fallback

    return all_models, fallback_status


def format_output(
    models: list[ModelInfo],
    output_format: str,
    fallback_status: dict[str, bool] | None = None,
) -> str:
    """Format models for output."""
    if output_format == "json":
        data: dict[str, list[dict[str, object]] | dict[str, bool]] = {
            "models": [
                {
                    "model_id": m.model_id,
                    "provider": m.provider,
                    "name": m.name,
                    "mixseek_format": m.to_mixseek_format(),
                    "plain_compatible": m.plain_compatible,
                    "code_exec_compatible": m.code_exec_compatible,
                }
                for m in models
            ],
        }
        if fallback_status:
            data["fallback_used"] = fallback_status
        return json.dumps(data, indent=2, ensure_ascii=False)

    elif output_format == "csv":
        csv_lines = ["model_id,provider,name,mixseek_format,plain_compatible,code_exec_compatible"]
        for m in models:
            csv_lines.append(
                f"{m.model_id},{m.provider},{m.name},{m.to_mixseek_format()},{m.plain_compatible},{m.code_exec_compatible}"
            )
        return "\n".join(csv_lines)

    elif output_format == "text":
        text_lines: list[str] = []
        by_provider: dict[str, list[ModelInfo]] = {}
        for m in models:
            by_provider.setdefault(m.provider, []).append(m)

        for provider, provider_models in sorted(by_provider.items()):
            prefix = PROVIDER_CONFIGS.get(provider, {}).get("mixseek_prefix", provider)
            fallback_marker = " (fallback)" if fallback_status and fallback_status.get(provider) else ""
            text_lines.append(f"\n[{provider.upper()}]{fallback_marker}")
            text_lines.append(f"  Prefix: {prefix}")
            text_lines.append("  Models:")
            for m in provider_models:
                code_exec = " [code_exec]" if m.code_exec_compatible else ""
                text_lines.append(f"    - {m.model_id}: {m.name}{code_exec}")

        return "\n".join(text_lines)

    else:  # mixseek format (default)
        return "\n".join(m.to_mixseek_format() for m in models)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch available LLM models from provider APIs (FR-008 compliant)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all models (default MixSeek format)
  %(prog)s

  # Fetch from specific provider
  %(prog)s --provider google

  # Output as JSON
  %(prog)s --json

  # Use fallback CSV only (skip API calls)
  %(prog)s --fallback-only

  # Verbose output with details
  %(prog)s --verbose
""",
    )

    parser.add_argument(
        "--provider",
        choices=["google", "anthropic", "openai", "grok", "all"],
        default="all",
        help="Provider to fetch models from (default: all)",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json", "csv", "mixseek"],
        default="mixseek",
        help="Output format (default: mixseek)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for --format json",
    )

    parser.add_argument(
        "--fallback-only",
        action="store_true",
        help="Skip API calls and use fallback CSV only",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)

    # Determine output format
    output_format = "json" if args.json else args.format

    # Determine providers to fetch
    if args.provider == "all":
        providers = list(PROVIDER_CONFIGS.keys())
    else:
        providers = [args.provider]

    # Fetch models
    models, fallback_status = fetch_all_models(
        providers=providers,
        fallback_only=args.fallback_only,
        verbose=args.verbose,
    )

    if not models:
        print("Error: No models found", file=sys.stderr)
        return 1

    # Output results
    output = format_output(models, output_format, fallback_status if args.verbose else None)
    print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
