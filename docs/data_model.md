# COD Data Model Notes

## Unit of record

Each row in `cod_event` is a **Cell Transition Event**:

`cell state + inputs/interventions + constraints -> actions + short-horizon outputs + long-horizon outcomes + reward context`

## State representation

The schema preserves the distinction requested in the manual:

- `latent biological state`: not directly stored as observed truth
- `measured state`: raw assay-linked profiles
- `harmonized state`: normalized references used for integration
- `model-inferred state`: latent model references marked with `state_representation_type=inferred`

## Missingness and pairing

Missing modalities are explicit through `has_*` flags and nullable profile refs.

Pairing is explicit through:

- `measurement_pairing_status`
- `temporal_completeness_flag`
- `intervention_completeness_flag`

## Action layer

Actions are not collapsed into raw molecular deltas.

Each event stores:

- hierarchical action family fields
- `action_label_set_ref`
- `action_assignment_method`
- `action_confidence_score`
- `action_label_provenance_ref`

## Outcome and reward layer

Short-horizon outputs and long-horizon outcomes remain separate fields. Reward context is represented independently through reward labels and proxy scores, which keeps policy/value work possible without conflating it with descriptive endpoints.
