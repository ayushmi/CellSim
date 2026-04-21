# External Prediction Contract

COD 3.0 evaluates external model predictions without altering them.

## Required fields

- `cod_event_id`
- `proposed_action`

## Optional fields

- `candidate_actions`
- `confidence`
- `proposed_output_type`

Accepted file formats:

- `.jsonl`
- `.json`
- `.csv`
- `.parquet`

## Minimal example

```json
{"cod_event_id":"COD_CTE_00001","proposed_action":"activate_interferon_program","confidence":0.82}
```

## Richer example

```json
{
  "cod_event_id": "COD_CTE_00001",
  "proposed_action": "activate_interferon_program",
  "candidate_actions": ["activate_interferon_program", "activate_inflammatory_cytokine_program"],
  "confidence": 0.82,
  "proposed_output_type": "transcriptomic_response"
}
```

## Evaluator command

```bash
python -m cod.cli evaluate-predictions \
  --input-dir data/materialized_cod3_public \
  --predictions examples/predictions/cod3_sample_external_predictions.jsonl \
  --output-dir benchmarks/cod3_public/evaluation_latest
```

## Main evaluator outputs

- `evaluation_report.json`
- `evaluation_rows.jsonl`
- `evaluation_rows.csv`

## Metrics reported

- action exact agreement
- candidate-label agreement
- output-type agreement
- plausibility penalty rate
- confidence calibration
- held-out robustness
- failure taxonomy

## Failure taxonomy

- `unsupported_action`
- `low_evidence_action`
- `source_specific_shortcut`
- `output_mismatch`
- `off_distribution_state`
- `low_confidence_disagreement`
- `agreement_or_unclassified`
