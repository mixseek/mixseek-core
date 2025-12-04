# Code Execution Provider Compatibility Analysis

**Date**: 2025-10-21
**Version**: v1.0.0
**Status**: Completed
**Category**: Technical Investigation

## Executive Summary

Comprehensive testing of code execution capabilities across different AI providers revealed that **only Anthropic Claude supports actual code execution** through Pydantic AI's CodeExecutionTool. This finding has significant implications for the MixSeek-Core Member Agent Bundle implementation.

## Investigation Background

### Context
During Phase 6 implementation (T031-T038), we discovered discrepancies in code execution functionality across different AI providers. This led to a systematic investigation to determine which providers actually support real code execution versus simulated responses.

### Research Questions
1. Which AI providers support Pydantic AI's CodeExecutionTool?
2. How can we distinguish between actual code execution and knowledge-based responses?
3. What are the implications for MixSeek-Core architecture?

## Methodology

### Test Design
We developed a progressive testing strategy to verify actual code execution:

1. **Basic Calculation Test**: 10000th prime number calculation
2. **Dynamic Data Test**: Real-time timestamp and random number generation
3. **System Information Test**: Environment details (OS, Python version, directory)
4. **File System Test**: Temporary file creation, read/write, and deletion

### Verification Criteria
- **Actual Execution**: Dynamic data, system specifics, file operations
- **Knowledge Response**: Static information, general answers, no system interaction

## Findings

### Provider Compatibility Matrix

| Provider | Model | Code Execution Support | Status | Evidence |
|----------|-------|----------------------|---------|----------|
| **Anthropic Claude** | `claude-sonnet-4-5-20250929` | ✅ **Full Support** | Working | Real-time data, file ops |
| **Anthropic Claude** | `claude-haiku-4-5` | ✅ **Full Support** | Working | System info, calculations |
| **Google AI** | `gemini-2.5-flash-lite` | ❌ **Not Supported** | Error | 400 INVALID_ARGUMENT |
| **Vertex AI** | `gemini-2.5-flash-lite` | ❌ **Not Supported** | Error | 400 INVALID_ARGUMENT |
| **OpenAI** | `gpt-4o` | ❌ **Not Supported** | Error | UserError: not supported |

### Detailed Test Results

#### ✅ Anthropic Claude (Working)
```bash
# Test Command
mixseek test-member "現在の日時を取得して、ランダムな10桁の数値を生成してください" \
  --config examples/claude_code_execution_agent.toml

# Result
Status: SUCCESS
Response: 現在の日時: 2025-10-21 15:20:45.851550
         ランダムな10桁の数値: 6005416350

# System Information Test
実行環境: posix
現在のディレクトリ: /
Pythonバージョン: 3.11.12 (main, May  9 2025, 23:47:08) [GCC 12.2.0]
```

**Evidence of Actual Execution**:
- Real-time timestamp matching execution time
- Dynamic random number generation
- Actual system environment details
- File system operations confirmed

#### ❌ Google AI/Vertex AI (Not Supported)
```bash
# Error Message
400 INVALID_ARGUMENT. {
  'error': {
    'code': 400,
    'message': 'Unable to submit request because the model does not support code execution.',
    'status': 'INVALID_ARGUMENT'
  }
}
```

#### ❌ OpenAI (Not Supported)
```bash
# Error Message
UserError: `CodeExecutionTool` is not supported by `OpenAIChatModel`.
If it should be, please file an issue.
```

## Technical Implications

### Architecture Impact

1. **Provider Limitation**: Only Anthropic Claude provides actual code execution
2. **Configuration Requirements**:
   - Must use `anthropic:` model prefix
   - Requires `ANTHROPIC_API_KEY` environment variable
   - Need proper model validation updates

3. **Authentication System**: Successfully implemented multi-provider support:
   ```python
   # /app/src/mixseek/core/auth.py
   class AuthProvider(Enum):
       GOOGLE_AI = "google_ai"
       VERTEX_AI = "vertex_ai"
       OPENAI = "openai"
       ANTHROPIC = "anthropic"  # ✅ Added
   ```

### Configuration Updates

Updated model validation to support Anthropic models:
```python
# /app/src/mixseek/models/member_agent.py
@field_validator('model')
def validate_model(cls, v: str) -> str:
    if v.startswith('anthropic:'):  # ✅ Added
        return v
    # ... other providers
```

## Recommendations

### Immediate Actions

1. **Update Documentation**: Clearly specify Claude as the only code execution provider
2. **Configuration Examples**: Provide working Claude configuration templates
3. **Error Handling**: Improve error messages for unsupported providers
4. **Test Coverage**: Add provider-specific test cases

### Configuration Template

```toml
# examples/claude_code_execution_agent.toml
[agent]
name = "claude-code-execution-agent"
type = "code_execution"
model = "anthropic:claude-sonnet-4-5-20250929"  # ✅ Working model
temperature = 0.1
max_tokens = 4096

[agent.instructions]
text = """Anthropic Claudeによる高度なコード生成・実行エージェント..."""
```

### Environment Setup

```bash
# Required environment variable
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Test command
mixseek test-member "10000番目の素数を計算してください" \
  --config examples/claude_code_execution_agent.toml
```

## Future Considerations

### Provider Monitoring
- Monitor Pydantic AI updates for expanded provider support
- Track Google AI and OpenAI roadmaps for code execution features
- Consider alternative code execution frameworks if needed

### Fallback Strategy
For non-Claude providers:
1. Graceful degradation to text-based responses
2. Clear messaging about code execution limitations
3. Alternative computational approaches where applicable

## Validation Methodology

### How to Verify Code Execution

**✅ Signs of Actual Execution**:
- Real-time timestamps matching execution time
- Dynamic data generation (random numbers, UUIDs)
- System-specific information (OS, paths, versions)
- File system operations and persistence
- Calculation results with process details

**❌ Signs of Knowledge-Based Response**:
- Generic or historical information
- Lack of system-specific details
- No dynamic data generation
- Vague process descriptions
- Static or approximate results

### Test Commands for Verification

```bash
# Dynamic Data Test
mixseek test-member "現在の日時とランダムなUUIDを生成してください" --config CONFIG

# System Information Test
mixseek test-member "実行環境とPythonバージョンを教えてください" --config CONFIG

# File System Test
mixseek test-member "一時ファイルを作成して内容を確認してください" --config CONFIG

# Computation Test
mixseek test-member "10000番目の素数を実際に計算してください" --config CONFIG
```

## Related Documents

- [Constitutional Compliance Checklist](../checklists/constitutional-compliance.md)
- [Authentication System Implementation](../implementation/auth-system.md)
- [Provider Configuration Guide](../docs/provider-setup.md)

## Conclusion

**Anthropic Claude is currently the only viable provider for actual code execution** in the MixSeek-Core Member Agent Bundle. This finding necessitates:

1. Documentation updates reflecting this limitation
2. Claude-specific configuration examples and guides
3. Proper error handling for unsupported providers
4. Long-term strategy for provider diversification

This investigation ensures constitutional compliance (Article 9: Data Accuracy Mandate) by providing explicit, tested information about code execution capabilities rather than assumptions or fallback behaviors.

---
**Investigation completed**: 2025-10-21
**Next review**: When Pydantic AI provider support changes
**Status**: Documented and validated