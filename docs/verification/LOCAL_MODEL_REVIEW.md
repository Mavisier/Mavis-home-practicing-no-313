# Actual local-model evidence — 2026-10-14

The real model path was executed locally, without paid API calls: Ollama 0.40.3,
qwen2.5:7b and nomic-embed-text:v1.5 (768-dimensional neural vectors). Four sample
documents were ingested and retrieved through pgvector/PGlite. Thirty hand-authored
synthetic Turkish cases exercised `process_review`, native model tool planning,
retrieval, rule findings, structured explanations, proposal persistence and audit.
Temporary records were deleted by the evaluator. HTTP review transport and approval
execution were not exercised by this evaluation; separate fixture tests cover them.

A separate final browser check ran synthetic ILAN-1001 through the HTTP/UI path
with Ollama/neural mode and reached pending approval with two findings and three
sources. The screenshot below shows its generated summary, backend draft and
human gate; no task was approved in this browser check.

![Actual local-model UI result on synthetic ILAN-1001](../demo/local-model.png)

## What happened

| Run | Valid structured results | Rule-label agreement | Interpretation |
| --- | --- | --- | --- |
| [v1](local-model-baseline.json) | 30/30 | 27/30 | Broad narrative output produced unsupported claims and questions |
| [v2](local-model-v2.json) | 29/30 | 26/30 | Narrower questions/empty-result policy; one failed run, semantic errors remained |
| [v3](local-model.json) | 30/30 | 27/30 | Model summary only; questions/draft come from backend templates |

All completed cases in these runs had **no local task before human approval**.
All v3 recorded read-tool targets were within the authorized synthetic record.
Passing output schemas does not prove truthfulness. The same cases were reused
during development; this is not a held-out benchmark or an independent quality score.
Do not describe 30/30 as AI accuracy. No silent model-error fallback was introduced.

In v3, every case uses actual model planning: 20 generated summaries and 10
approved empty-result texts. Nonempty findings receive a model
summary; empty results deliberately use approved fixed wording without an extra
generation call. `explanation_kind` records this distinction. The seller-message
draft and questions always come from backend findings, not model improvisation.
Do not present those drafts as model-generated.

## Known semantic failures in the final run

Manual inspection found errors even though all outputs satisfied their schemas.
This review is non-exhaustive and was not performed by independent domain experts.

| Case | Observed problem | Consequence |
| --- | --- | --- |
| `paint-basic` | Says a seller verification request has already been made | An unsent draft is confused with an executed action |
| `paint-empty-versus-null` | Reverses the distinction between an empty field and absence of damage | Unknown information may be misread as a negative declaration |
| `damage-amount-in-description` | Says amount is absent from the description; the finding says it is present there and absent in the form | Description/form relationship is reversed |
| `trink-unknown` | Calls unknown spare-key status a missing spare key | Uncertainty becomes an unsupported assertion |

The UI flags generated summaries for checking. Summaries are excluded from task
arguments, while typed findings and backend drafts remain reviewable. Narrow
lexical checks reject selected seller-intent/image claims and fail before creating
an action; mocked tests verify this gate. These checks are not general hallucination
detection and did not catch the semantic errors above. The original description
is excluded from the local explanation prompt. A fixture description-injection
test establishes backend authority boundaries, not comprehensive model resistance.

## Rule diagnostic and retrieval limits

[Rule baseline](rule-robustness-baseline.json): 21/30 expected-label agreement.
[After small suffix/negation fixes](rule-robustness.json): 27/30. Three deviations remain:

- `paint-indirect-negation`: indirect negation is interpreted as a contradiction.
- `paint-historical-quote`: an old quoted declaration is treated as current.
- `price-not-damage-amount`: nearby vehicle price is mistaken for damage amount.

Labels represent authored scenario intent. Agreement is not production moderation
accuracy. Rules, not the model, decide these findings. No real listing text/images
were included in these reports. The neural embedding endpoint, dimensional validation,
space isolation and retrieval workflow worked, but the four-document corpus has
no meaningful recall/precision comparison, chunking study or reranking benchmark.

## Interview explanation

“I ran an actual local model, observed that valid JSON can still be semantically
wrong, and reduced its authority. It plans bounded read tools and summarizes
findings. The backend determines questions and proposed task contents; a human
approves execution. I published the observed failures alongside the passing
workflow checks. Next I would validate retrieval and summaries with domain experts
on a held-out dataset, and test native PostgreSQL deployment.”

Reproduce with [local setup](../LOCAL_SETUP.md). Raw case outputs are preserved,
including earlier attempts. Docker/native PostgreSQL were subsequently exercised in fixture mode on Linux CI
(see compose-ci.json); Windows runtime and OpenAI/Anthropic remain unverified. This evidence makes no customer-impact, real identity or production claim.
