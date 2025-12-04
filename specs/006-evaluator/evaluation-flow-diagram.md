# Evaluation Flow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Evaluator Component                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Input: EvaluationRequest                                    │
│  ├─ user_query: str                                          │
│  ├─ submission: str                                         │
│  ├─ team_id: str                                             │
│  └─ config: Optional[EvaluationConfig]                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Load Configuration (from TOML)                     │   │
│  │  ├─ Metric weights                                  │   │
│  │  ├─ LLM models per metric                           │   │
│  │  └─ Evaluation parameters (temp, seed, retries)     │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Sequential Metric Evaluation                       │   │
│  │  ├─ ClarityCoherence (明瞭性/一貫性)                                │   │
│  │  ├─ Coverage (網羅性)                      │   │
│  │  └─ Relevance (関連性)                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Calculate Weighted Overall Score                   │   │
│  │  overall_score = Σ(metric.score × metric.weight)    │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  Output: EvaluationResult                                    │
│  ├─ metrics: List[MetricScore]                               │
│  │   └─ Each with score (0-100) + evaluator_comment          │
│  └─ overall_score: float (0-100)                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Single Metric Evaluation Flow

```
┌────────────────────────────────────────────────────────────────┐
│           Evaluate Single Metric (e.g., ClarityCoherence)               │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  1. Build Prompt                                               │
│     ├─ System: "Impartial evaluator. Avoid verbosity bias."   │
│     └─ User: [Template with query, response, rubric]          │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  2. Call LLM via Pydantic AI                                   │
│     ├─ model: "anthropic:claude-4-5-sonnet"          │
│     ├─ output_type: ClarityCoherenceEvaluation (Pydantic model)        │
│     └─ parameters: {temperature: 0.0, seed: 42}                │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  3. LLM Response (Structured Output)                           │
│     {                                                           │
│       "metric_name": "clarity_coherence",                                │
│       "reasoning": "The response demonstrates excellent...",   │
│       "sub_scores": {                                          │
│         "structure": 22,                                       │
│         "language_simplicity": 23,                             │
│         "sentence_construction": 21,                           │
│         "readability": 24                                      │
│       },                                                       │
│       "score": 90.0                                            │
│     }                                                           │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  4. Pydantic Validation                                        │
│     ├─ score in range [0, 100] ✓                              │
│     ├─ sub_scores sum to score ✓                              │
│     ├─ all required fields present ✓                          │
│     └─ types match schema ✓                                   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  5. Return MetricScore                                         │
│     ├─ metric_name: "clarity_coherence"                                 │
│     ├─ score: 90.0                                             │
│     └─ evaluator_comment: "The response demonstrates..."       │
└────────────────────────────────────────────────────────────────┘
```

## Error Handling and Retry Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    Attempt Evaluation                          │
└────────────────────────────────────────────────────────────────┘
                             ↓
                    ┌────────────────┐
                    │  Call LLM      │
                    └────────────────┘
                             ↓
                    ┌────────────────┐
                    │  Success?      │
                    └────────────────┘
                      ╱            ╲
                    YES            NO
                     ↓              ↓
          ┌──────────────┐   ┌──────────────────────┐
          │ Validate     │   │ Error Type?          │
          │ Response     │   └──────────────────────┘
          └──────────────┘        ↓         ↓         ↓
                 ↓         ValidationError  API Error  Timeout
                 ↓                ↓            ↓         ↓
          ┌──────────────┐   ┌──────────────────────────────┐
          │ Valid?       │   │ Retry Count < Max?           │
          └──────────────┘   └──────────────────────────────┘
            ╱        ╲                ╱              ╲
          YES        NO             YES              NO
           ↓          ↓               ↓                ↓
    ┌──────────┐ ┌─────────────┐ ┌──────────┐ ┌──────────────┐
    │ Return   │ │ ModelRetry  │ │ Retry    │ │ Raise        │
    │ Result   │ │ with        │ │ with     │ │ Evaluation   │
    │          │ │ feedback    │ │ backoff  │ │ Error        │
    └──────────┘ └─────────────┘ └──────────┘ └──────────────┘
                       ↓                ↓
                       └────────────────┘
                              ↓
                    (Back to Call LLM)
```

## Prompt Template Structure

```
┌────────────────────────────────────────────────────────────────┐
│                      Evaluation Prompt                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CONTEXT                                                        │
│  ├─ Role: "You are an impartial evaluator..."                 │
│  ├─ Task: "Evaluate the [METRIC] of the AI response"          │
│  └─ Bias warnings: "Avoid verbosity bias..."                  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────│
│                                                                 │
│  INPUT DATA                                                     │
│  ├─ USER QUERY: {user_query}                                  │
│  └─ AI RESPONSE: {submission}                                │
│                                                                 │
│  ─────────────────────────────────────────────────────────────│
│                                                                 │
│  EVALUATION CRITERIA (Additive Scoring)                        │
│  ├─ Criterion 1: [Description] (X points)                     │
│  ├─ Criterion 2: [Description] (Y points)                     │
│  ├─ Criterion 3: [Description] (Z points)                     │
│  └─ Criterion 4: [Description] (W points)                     │
│     Total: 100 points                                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────│
│                                                                 │
│  SCORING GUIDE (Reference Ranges)                              │
│  ├─ 90-100: [Description of excellent]                        │
│  ├─ 70-89:  [Description of good]                             │
│  ├─ 50-69:  [Description of fair]                             │
│  ├─ 30-49:  [Description of poor]                             │
│  └─ 0-29:   [Description of very poor]                        │
│                                                                 │
│  ─────────────────────────────────────────────────────────────│
│                                                                 │
│  INSTRUCTIONS (Chain-of-Thought)                               │
│  1. Analyze each criterion systematically                      │
│  2. Explain your reasoning for each aspect                     │
│  3. Assign points to each sub-criterion                        │
│  4. Calculate total score (sum of sub-scores)                  │
│  5. Provide actionable feedback                                │
│                                                                 │
│  Provide your evaluation with step-by-step reasoning           │
│  before assigning the final score.                             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Three Metrics Comparison

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       Metric Comparison Table                             │
├──────────────────┬────────────────┬────────────────┬────────────────────┤
│                  │    CLARITY_COHERENCE     │COVERAGE│    RELEVANCE      │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Japanese Name    │   明瞭性/一貫性        │    網羅性       │     関連性         │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Core Question    │ Is it clear?   │ Is it complete? │ Is it relevant?   │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Focus            │ Understandability│ Coverage      │ Addressing query  │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Sub-criteria     │ 4 × 25 pts     │ 2×30 + 2×20 pts│ 1×40 + 2×30 pts   │
│ Breakdown        │ (Equal weight) │ (Varying weight)│ (Query-focused)   │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Key Aspects      │ • Structure    │ • Topic coverage│ • Query alignment │
│                  │ • Language     │ • Detail depth │ • Focus           │
│                  │ • Sentences    │ • Completeness │ • Requirements    │
│                  │ • Readability  │ • Context      │                   │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Common Issues    │ • Jargon       │ • Missing info │ • Off-topic       │
│                  │ • Poor structure│ • Surface-level│ • Wrong question  │
│                  │ • Ambiguity    │ • Incomplete   │ • Tangents        │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Evaluation Time  │ 2-5 seconds    │ 3-6 seconds    │ 2-4 seconds       │
├──────────────────┼────────────────┼────────────────┼────────────────────┤
│ Expected Variance│ 2-4%           │ 3-5%           │ 2-3%              │
└──────────────────┴────────────────┴────────────────┴────────────────────┘
```

## Configuration Flow

```
┌────────────────────────────────────────────────────────────────┐
│              configs/evaluator.toml                            │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  default_model = "anthropic:claude-4-5-sonnet"       │
│                                                                 │
│  [evaluation_settings]                                         │
│  temperature = 0.0                                             │
│  seed = 42                                                     │
│  max_retries = 3                                               │
│                                                                 │
│  [[metric]]                                                    │
│  name = "clarity_coherence"                                              │
│  weight = 0.4                                                  │
│  # Uses default_model                                          │
│                                                                 │
│  [[metric]]                                                    │
│  name = "coverage"                                    │
│  weight = 0.3                                                  │
│  model = "openai:gpt-5"  # Override                           │
│                                                                 │
│  [[metric]]                                                    │
│  name = "relevance"                                            │
│  weight = 0.3                                                  │
│  # Uses default_model                                          │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│              Load and Validate Configuration                   │
├────────────────────────────────────────────────────────────────┤
│  ✓ Check: Σ weights = 1.0                                     │
│  ✓ Check: All weights > 0                                     │
│  ✓ Check: Valid model identifiers                             │
│  ✓ Check: Required environment variables (API keys)           │
│  ✓ Resolve: metric.model → default_model if not specified     │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│              EvaluationConfig (Pydantic Model)                 │
├────────────────────────────────────────────────────────────────┤
│  metric_weights: {"clarity_coherence": 0.4, "coverage": 0.3, ...}│
│  enabled_metrics: ["clarity_coherence", "coverage", "relevance"]│
│  model_per_metric: {"clarity_coherence": "anthropic:...", ...}          │
│  evaluation_params: {temperature: 0.0, seed: 42, ...}         │
└────────────────────────────────────────────────────────────────┘
```

## Consistency Validation Flow

```
┌────────────────────────────────────────────────────────────────┐
│         Consistency Test (for < 5% variance validation)        │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  Test Case: (query, response) pair                            │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  Run evaluation N times (e.g., N=5)                           │
│  ├─ Same model                                                 │
│  ├─ Same temperature (0.0)                                     │
│  ├─ Same seed (42)                                             │
│  └─ Same prompt                                                │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  Collect scores: [85.0, 87.0, 86.0, 85.5, 86.5]              │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  Calculate metrics:                                            │
│  ├─ Mean: 86.0                                                 │
│  ├─ Std Dev: 0.79                                              │
│  ├─ Max Deviation: 1.0                                         │
│  └─ Variance %: (1.0 / 86.0) × 100 = 1.16%                   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  Validate: 1.16% < 5.0% ✓ PASS                                │
└────────────────────────────────────────────────────────────────┘
```

## Data Model Hierarchy

```
EvaluationRequest
├─ user_query: str
├─ submission: str
├─ team_id: str
└─ config: Optional[EvaluationConfig]

EvaluationConfig
├─ metric_weights: Dict[str, float]
├─ enabled_metrics: List[str]
├─ custom_metrics: Optional[Dict]
└─ default_model: Optional[str]

MetricConfig (TOML array element)
├─ name: str
├─ weight: float
└─ model: Optional[str]

MetricScore
├─ metric_name: str
├─ score: float (0-100)
└─ evaluator_comment: str

EvaluationResult
├─ metrics: List[MetricScore]
│   ├─ MetricScore (clarity_coherence)
│   ├─ MetricScore (coverage)
│   └─ MetricScore (relevance)
└─ overall_score: float (0-100)
    = Σ(metric.score × metric.weight)
```

## Legend

```
┌─────────┐
│ Process │  = A processing step or component
└─────────┘

    ↓        = Sequential flow

   ╱ ╲      = Decision point
  YES NO

┌──────────┐
│ Data     │  = Data structure or model
└──────────┘

├─          = List item or nested element
└─          = Last list item
```
