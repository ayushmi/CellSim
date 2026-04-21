# Cell Operating Dataset (COD) Research Manual
## Comprehensive build spec for treating the human cell as an operational system

Version: 0.5 draft
Date: 2026-04-20
Status: Internal research manual / build specification

---

## Executive summary

Biology has enough data to build powerful models of cellular behavior, but not enough **standardization** to turn that data into a reusable operational substrate. Most current resources describe isolated slices of cellular reality: transcriptomic state, regulatory context, perturbation response, metabolism, spatial neighborhood, or clinical outcome. Very few datasets are structured around the operational question:

**Given the state of a cell and the inputs applied to it, what action does it take next, and what outcome follows?**

The Cell Operating Dataset (COD) is the proposed answer. COD is a standardized, multi-modal, event-centered dataset in which each record represents a cell state transition under defined inputs, with explicit action labels, outputs, outcomes, confidence, provenance, and constraints.

The purpose of COD is to support:
- cellular foundation models
- intervention prediction
- digital cell twins
- causal perturbation modeling
- biological agents
- programmable cell engineering
- mechanistic and hybrid simulation systems

This manual defines:
1. what a cell is in operational terms
2. what it means to "run" a cell
3. the distinction between inputs, state, actions, outputs, outcomes, and rewards
4. the fragmented datasets available today
5. the barriers between these datasets
6. the canonical design of COD
7. the data model, ontology model, and integration pipeline required to build COD across all 19 dataset families

---

# Part I. What is a cell?

A human cell should be treated as a **stateful, constrained, adaptive operational system**.

It is simultaneously:
- an information processor
- a decision system
- a control system
- a resource allocator
- a communication node
- a survival and maintenance machine
- a context-sensitive dynamical system

A cell continuously:
1. senses the environment
2. updates internal state
3. checks constraints and feasible actions
4. chooses actions through biochemical regulatory logic
5. produces measurable outputs
6. transitions into new states
7. contributes to tissue- and organism-level outcomes

This operational framing is more useful for dataset design than a static molecular framing.

Instead of asking only:
- Which genes are expressed?
- Which proteins are present?

we ask:
- Given this internal state and these external inputs, what action is the cell taking?
- Which actions are available but currently infeasible?
- What short-horizon outputs and long-horizon outcomes follow?

---

# Part II. What does it mean to "run" a cell?

To run a cell means to model the cell as a transition system:

**next_state, actions, outputs, outcomes = F(current_state, inputs, constraints, context)**

A practical formulation is:

- **State**: what the cell currently is
- **Inputs**: what the cell receives or experiences
- **Constraints**: what the cell is allowed or able to do
- **Action**: what the cell decides to do
- **Outputs**: immediate observables from the action
- **Outcome**: downstream result after one or more actions over time

This supports several modeling tasks:
- next-state prediction
- action classification
- action sequence modeling
- intervention response prediction
- counterfactual prediction
- reward-conditioned policy modeling
- rollout simulation

---

# Part III. Inputs required to run a cell

## 1. Structural and inherited inputs
These define what the cell can potentially do.

- genome sequence
- somatic mutation burden
- copy-number alterations
- structural variants
- mitochondrial genotype where relevant
- lineage and cell type identity
- donor background, age, sex, ancestry when available

## 2. Regulatory inputs
These define what portions of the blueprint are accessible.

- chromatin accessibility
- methylation state
- histone marks
- enhancer-promoter interactions
- transcription factor occupancy
- regulatory network priors

## 3. Molecular resource inputs
These define what biochemical actions are feasible.

- glucose
- amino acids
- lipids
- oxygen and redox state
- ATP/ADP state
- ions
- cofactors
- metabolite availability

## 4. Environmental and signaling inputs
These define control signals and context.

- hormones
- cytokines
- chemokines
- growth factors
- ligand-receptor signals
- extracellular matrix cues
- pathogen-associated signals
- drug exposures
- mechanical stress
- osmolarity
- pH
- temperature
- radiation or toxic exposure

## 5. Current internal state
These define where the cell is in its operational trajectory.

- transcriptome
- proteome
- phosphoproteome if available
- metabolome
- organelle state
- mitochondrial health
- DNA damage response status
- cell-cycle phase
- senescence or stress programs
- apoptosis priming
- prior action history

## 6. Spatial and social inputs
These define neighborhood effects.

- tissue type
- microenvironment zone
- neighboring cell identities
- spatial coordinates
- local ligand field
- vascular or oxygen proximity
- immune infiltration context

---

# Part IV. Outputs, actions, and outcomes

## 1. Outputs
Outputs are immediate measurable consequences of cellular activity.

Examples:
- change in RNA abundance
- change in protein abundance
- cytokine secretion
- phospho-signaling activation
- metabolite flux change
- morphology change

Outputs are usually what the instruments measure.

## 2. Actions
Actions are operational choices or state-transition primitives.

Examples:
- activate interferon program
- suppress cell-cycle checkpoint
- enter S phase
- increase glycolysis
- increase oxidative phosphorylation
- secrete IL-6
- migrate toward gradient
- present antigen
- initiate apoptosis
- enter quiescence
- differentiate toward lineage X

Actions are not just raw measurements. They are abstracted decision labels derived from measurements.

## 3. Outcomes
Outcomes are longer-horizon consequences, often visible only after accumulation of actions over time.

Examples:
- cell survives or dies
- successful proliferation
- differentiation achieved
- tissue repair
- fibrosis
- immune activation
- tumor progression
- therapeutic response
- patient-level endpoint

---

# Part V. Why actions are the hardest part

Most biology datasets provide **observations**, not **actions**.

For example, a perturbation dataset may report that 700 genes changed after a CRISPR knockout. That is not yet an action label. COD needs an abstraction layer that turns observed molecular consequences into standardized action statements.

Examples:
- many interferon-related genes increase -> **Action: innate inflammatory activation**
- glycolytic enzymes rise and OXPHOS signatures drop -> **Action: glycolytic shift**
- cyclins rise and DNA replication markers activate -> **Action: cell-cycle entry / proliferation**

This requires:
- pathway-level mapping
- ontology support
- weak supervision
- expert review
- confidence scoring
- action hierarchies from coarse to fine labels

Without a standardized action space, biology remains descriptive and fragmented.

---

# Part VI. Reward space and optimization targets

A cell does not optimize a single universal reward. Different cells and contexts optimize different objectives.

Possible reward contexts include:
- survival
- proliferation
- tissue homeostasis
- immune defense
- differentiation fidelity
- damage control
- energy efficiency
- repair quality
- developmental progression
- organismal fitness proxy

Therefore COD should not encode a single reward scalar by default. Instead it should store:
- reward context category
- candidate reward variables
- measured proxy metrics
- uncertainty about what objective is being optimized

Example:
- activated T cell: reward context may prioritize pathogen control over energy efficiency
- hepatocyte: reward context may prioritize metabolic homeostasis and detoxification
- cancer cell: reward context may approximate proliferative fitness under stress

---

# Part VII. Isolated operating zones inside a cell

A cell contains multiple partially separable operating zones. COD should preserve this structure so models can reason modularly.

## Zone A. Information layer
- genome
- chromatin
- transcription
- RNA processing
- translation

Core question: what molecular programs are being written and produced?

## Zone B. Signaling and routing layer
- receptors
- kinase cascades
- second messengers
- ligand-receptor logic

Core question: which incoming signals are being interpreted as actionable?

## Zone C. Metabolic and resource layer
- ATP generation
- redox balance
- carbon and nitrogen allocation
- biosynthesis
- catabolism

Core question: which actions are affordable and sustainable?

## Zone D. Structural and motility layer
- cytoskeleton
- adhesion
- polarity
- migration
- membrane dynamics

Core question: where is the cell and how does it physically respond?

## Zone E. Secretory and communication layer
- cytokines
- hormones
- vesicles
- exosomes
- ECM components

Core question: what information or materials does the cell send outward?

## Zone F. Fate control layer
- cell cycle
- quiescence
- differentiation
- senescence
- apoptosis
- necroptosis or pyroptosis when relevant

Core question: does the cell continue, transform, pause, or terminate?

## Zone G. Quality control and maintenance layer
- unfolded protein response
- autophagy
- DNA repair
- ROS management
- proteostasis

Core question: how does the cell preserve integrity under stress?

COD should support both global action labels and zone-specific sub-actions.

---

# Part VIII. Fragmented datasets that already exist

The 19 dataset families already identified are useful but fragmented.

## Layer 1. Baseline state
- Human Cell Atlas (HCA)
- GTEx
- Tabula Sapiens

## Layer 2. Regulatory decision logic
- ENCODE
- Roadmap Epigenomics
- TRRUST

## Layer 3. Causal perturbation and intervention response
- Perturb-seq
- LINCS
- DepMap

## Layer 4. Metabolism and feasibility
- Recon3D
- BioModels
- HMDB

## Layer 5. Spatial and microenvironmental context
- HuBMAP
- CELLxGENE

## Layer 6. Clinical and organism-level outcomes
- TCGA
- UK Biobank

## Layer 7. Signaling and pathway knowledge graphs
- Reactome
- KEGG
- OmniPath

These datasets differ in:
- modality
- granularity
- timescale
- experimental design
- cell type coverage
- ontology usage
- confidence and noise profile
- intervention semantics
- patient and donor metadata depth

COD is the integration layer across all of them.

---

# Part IX. Why fragmentation persists

The main barriers are not just technical storage issues. They are representation issues.

## 1. Different entity identifiers
- genes may use gene symbols, Ensembl IDs, Entrez IDs
- proteins may use UniProt or assay-specific identifiers
- metabolites may use HMDB, ChEBI, KEGG compound identifiers
- tissues and cell types may use incompatible labels

## 2. Different granularity
- single cell vs bulk tissue
- cell line vs primary cell
- patient vs assay replicate
- direct molecular measurement vs curated pathway knowledge

## 3. Different temporal structure
- static measurements
- pre/post perturbation only
- time series with irregular spacing
- clinical outcomes far downstream from molecular state

## 4. Different semantics
- some datasets describe perturbations directly
- some only describe baseline state
- some encode pathway priors, not direct observations

## 5. Different confidence models
- curated databases
- noisy assays
- inferred pathway activity
- imputed missing modalities

## 6. Different biological contexts
- healthy tissue
- development
- disease
- cancer cell lines
- primary immune cells
- spatial tissue slices

COD must make these differences explicit, not hide them.

---

# Part X. What COD is

COD is a **canonical event dataset** where the primary object is not a file, an assay, or even a sample, but a:

**cell state transition event**

A COD event links:
1. a pre-action cell state
2. explicit inputs and perturbations
3. the biological constraints active at that time
4. one or more action labels
5. short-horizon outputs
6. one or more downstream outcomes
7. evidence and provenance back to raw sources

COD is therefore both:
- a standardized dataset
- a reusable integration framework
- a training substrate for models

---

# Part XI. COD design principles

1. **Event-centered, not file-centered**
2. **Action-aware, not observation-only**
3. **Multi-resolution labels**: coarse to fine
4. **Multi-modal packaging** with explicit missingness
5. **Ontology-bound identifiers everywhere possible**
6. **Time-aware records** with observation windows
7. **Explicit provenance and confidence**
8. **Constraint-aware modeling** to avoid impossible biology
9. **Intervention-normalized schema** for drugs, edits, signals, and environment changes
10. **Reusable split definitions** for benchmarking and model comparisons

---

# Part XII. Final COD schema

The schema below is the core specification that was missing from the earlier draft. This version is intended to be implementation-ready.

## A. Unit of record

The base record in COD is a **Cell Transition Event (CTE)**.

A CTE represents a cell or pseudo-cell state at time `t0`, under a defined context and optional intervention, with observed actions, outputs, and outcomes measured over windows `t1...tn`.

A CTE may correspond to:
- one directly observed single cell
- one aggregated pseudo-cell from bulk or deconvolved sources
- one cell line state under perturbation
- one patient-linked molecular state mapped to a canonical cell/tissue state representation

## B. Schema levels

COD should be stored in four linked layers:

1. **event table**: one row per Cell Transition Event
2. **modality tables**: sparse matrices or embeddings for transcriptome/proteome/metabolome/etc.
3. **ontology and graph tables**: normalized entities and relationships
4. **provenance tables**: source dataset lineage and transformation history

This avoids storing giant vectors directly in a single wide row.

## C. Required event-level fields

### 1. Identity and indexing
- `cod_event_id` : globally unique event identifier
- `cod_subject_id` : donor/patient/cell-line/experimental subject ID, normalized
- `cod_cell_instance_id` : cell-level or pseudo-cell instance ID
- `cod_parent_event_id` : optional link to preceding state event
- `cod_batch_id` : harmonization / processing batch
- `cod_release_version` : COD release version

### 2. Source and provenance
- `source_dataset` : one of the 19 dataset families or derivative bundle
- `source_study_id`
- `source_sample_id`
- `source_cell_id` : if available
- `source_assay_id`
- `source_record_pointer` : stable pointer to raw source record
- `processing_pipeline_version`
- `evidence_trace_id` : link to full provenance table
- `license_class` : usage constraints for that source component

### 3. Biological context
- `species`
- `donor_id_normalized`
- `sex`
- `age`
- `ancestry` : if available and permitted
- `health_status`
- `disease_state`
- `disease_ontology_id`
- `tissue_label`
- `uberon_id`
- `cell_type_label`
- `cell_ontology_id`
- `developmental_stage`
- `microenvironment_label`
- `spatial_region_label`

### 4. Time and trajectory fields
- `time_anchor_type` : baseline / post-perturbation / diagnosis / treatment cycle / developmental stage / inferred
- `t0_timestamp` : exact or relative
- `t0_time_unit`
- `delta_t_to_output`
- `delta_t_to_outcome`
- `trajectory_group_id` : link events in a shared trajectory
- `time_uncertainty_score`

### 5. Experimental design and intervention
- `intervention_present` : yes/no
- `intervention_type` : genetic / chemical / ligand / environmental / mechanical / infectious / combinatorial / none
- `intervention_target_entity`
- `intervention_target_id`
- `intervention_direction` : knockout / knockdown / overexpression / inhibition / activation / exposure / withdrawal
- `intervention_dose`
- `intervention_dose_unit`
- `intervention_duration`
- `intervention_delivery_mode`
- `intervention_combo_id` : for multi-perturbation settings
- `control_definition`

### 6. State availability map
These fields are booleans or categorical coverage indicators used to make missingness explicit.

- `has_genome_state`
- `has_epigenome_state`
- `has_transcriptome_state`
- `has_proteome_state`
- `has_phosphoproteome_state`
- `has_metabolome_state`
- `has_spatial_state`
- `has_neighbor_context`
- `has_clinical_context`
- `has_time_series_context`

### 7. Canonical state references
These fields point into modality tables, embeddings, or summary objects.

- `genome_profile_ref`
- `epigenome_profile_ref`
- `transcriptome_profile_ref`
- `proteome_profile_ref`
- `phosphoproteome_profile_ref`
- `metabolome_profile_ref`
- `spatial_profile_ref`
- `neighbor_profile_ref`
- `state_embedding_ref`
- `state_summary_ref`

### 8. Input/context summary fields
These are structured summaries derived from raw modalities and contextual data.

- `external_signal_set_ref`
- `resource_state_ref`
- `stress_state_ref`
- `cell_cycle_state`
- `mitochondrial_state`
- `damage_response_state`
- `senescence_state`
- `immune_context_ref`
- `constraint_profile_ref`

### 9. Action labels
Actions should be multi-label and hierarchical.

- `action_level_0` : coarse family (regulatory / metabolic / secretory / structural / fate / quality_control / signaling)
- `action_level_1` : subfamily
- `action_level_2` : specific standardized action label
- `action_label_set_ref` : list of all action labels on this event
- `action_primary_label`
- `action_intensity_score`
- `action_directionality` : activate / suppress / switch / maintain / exit / enter
- `action_zone` : A/B/C... zone mapping
- `action_confidence_score`
- `action_assignment_method` : direct / curated / inferred / weak_supervision / model_assisted

### 10. Output labels
Outputs are immediate observables measured in a shorter window.

- `short_horizon_output_ref`
- `differential_expression_signature_ref`
- `differential_protein_signature_ref`
- `differential_metabolite_signature_ref`
- `secretome_signature_ref`
- `morphology_signature_ref`
- `viability_measure`
- `proliferation_measure`
- `output_confidence_score`

### 11. Outcome labels
Outcomes capture downstream consequences.

- `long_horizon_outcome_ref`
- `fate_outcome_label`
- `tissue_outcome_label`
- `therapy_response_label`
- `disease_progression_label`
- `survival_proxy`
- `outcome_time_horizon`
- `outcome_confidence_score`

### 12. Reward and objective context
- `reward_context_label`
- `candidate_reward_variables_ref`
- `fitness_proxy_score`
- `homeostasis_proxy_score`
- `immune_function_proxy_score`
- `reward_inference_method`

### 13. Data quality and harmonization
- `raw_qc_score`
- `harmonization_qc_score`
- `batch_correction_flag`
- `imputation_flag`
- `deconvolution_flag`
- `modality_conflict_flag`
- `manual_review_flag`
- `exclusion_reason` : only for filtered-but-tracked records

## D. Modality tables

High-dimensional modalities should not be flattened into the event table.

### `transcriptome_profiles`
- `transcriptome_profile_ref`
- `feature_space_id`
- `normalization_method`
- `gene_id`
- `value`
- or sparse matrix storage with linked feature schema

### `proteome_profiles`
- `proteome_profile_ref`
- `protein_id`
- `value`

### `metabolome_profiles`
- `metabolome_profile_ref`
- `metabolite_id`
- `value`

### `epigenome_profiles`
- accessibility / methylation / histone features

### `spatial_profiles`
- coordinates
- neighborhood graph
- spatial niche label

### `state_embeddings`
- learned or curated embeddings derived from one or multiple modalities

## E. Ontology and graph tables

### `entity_registry`
Stores canonical mappings for:
- HGNC / Ensembl genes
- UniProt proteins
- HMDB / ChEBI metabolites
- Cell Ontology terms
- Uberon tissue terms
- Disease Ontology / MONDO terms
- perturbation entities
- ligand/receptor entities

### `action_ontology`
Defines the controlled vocabulary for actions.

Minimum fields:
- `action_id`
- `action_name`
- `parent_action_id`
- `zone`
- `description`
- `required_evidence_types`
- `allowed_output_patterns`
- `known_pathway_links`

### `constraint_profiles`
Defines regulatory and metabolic feasibility priors attached to states.

## F. Provenance tables

### `evidence_trace`
For each COD field that is inferred or harmonized, store:
- source dataset
- source record
- transformation step
- model or rules used
- confidence
- reviewer if manually curated

This is essential for scientific defensibility.

---

# Part XIII. Action ontology design

A practical action ontology should be hierarchical.

## Level 0: broad families
- regulatory
- signaling
- metabolic
- secretory
- structural
- fate
- maintenance

## Level 1: subfamilies
Examples:
- regulatory -> inflammatory program activation
- metabolic -> glycolytic shift
- fate -> proliferation entry
- maintenance -> DNA repair activation

## Level 2: specific action labels
Examples:
- activate IFN-gamma response
- suppress p53 checkpoint
- initiate autophagy
- present antigen via MHC-I
- enter G1/S transition

The ontology should allow multiple actions per event because cells often perform coupled programs.

---

# Part XIV. How to integrate all 19 datasets into COD

## Phase 0. Governance and architecture
Before ingestion begins, define:
- legal and license map per dataset
- storage strategy for raw, normalized, and COD layers
- ontology standards
- confidence semantics
- release cadence
- benchmark tasks and splits

## Phase 1. Raw ingestion layer
Ingest each source without loss.

For every dataset, preserve:
- raw identifiers
- metadata
- assay details
- file-level provenance
- time metadata
- intervention metadata
- QC metrics

Output: immutable bronze layer.

## Phase 2. Canonical identifier normalization
Map all entities to controlled registries.

Required registries:
- genes -> HGNC + Ensembl
- proteins -> UniProt
- metabolites -> HMDB/ChEBI
- tissues -> Uberon
- cell types -> Cell Ontology
- diseases -> Disease Ontology or MONDO
- drugs and compounds -> canonical compound registry
- perturbations -> standardized perturbation schema

Output: silver layer with normalized entities plus unresolved mapping queue.

## Phase 3. State harmonization
Create comparable state objects across modalities.

Tasks:
- normalize single-cell and bulk representations into compatible state summaries
- generate pseudo-cells where only bulk data exists
- package modality-specific profiles into linked tables
- preserve missingness explicitly rather than impute by default
- create one or more state embeddings for model training

Output: canonical state objects.

## Phase 4. Context and intervention normalization
All interventions should use one schema regardless of source.

A perturb-seq knockout, a LINCS drug exposure, and a cytokine treatment should all map to standardized intervention fields.

Output: harmonized intervention registry.

## Phase 5. Constraint engine construction
Use:
- ENCODE
- Roadmap
- TRRUST
- Reactome
- KEGG
- OmniPath
- Recon3D
- BioModels

to build a constraint layer that answers:
- what is regulatory feasible?
- what is signaling permitted?
- what is metabolically affordable?

Output: per-state constraint profiles and feasibility scores.

## Phase 6. Action labeling engine
This is the core COD step.

Inputs:
- differential state signatures
- pathway activations
- perturbation semantics
- curated biological rules
- literature-derived priors if later incorporated

Outputs:
- coarse action families
- fine action labels
- action confidence
- action assignment trace

Best practice:
- start with weak supervision and rule templates
- validate with expert curation on gold subsets
- later train classifiers to automate action assignment

## Phase 7. Output and outcome attribution
Short horizon outputs can come from molecular assays.
Long horizon outcomes come from viability, lineage, tissue, and clinical data.

Examples:
- DepMap viability -> short to medium horizon outcome
- TCGA progression or survival proxy -> long horizon outcome
- UK Biobank phenotype linkage -> organism-level association outcome
- HuBMAP spatial remodeling -> tissue-context outcome

Output: aligned output/outcome tables.

## Phase 8. Event assembly
Construct Cell Transition Events by linking:
- state object
- context object
- intervention object
- action labels
- outputs
- outcomes
- provenance
- constraints

Output: COD event table.

## Phase 9. Benchmark split design
This section was missing in the earlier draft and is important.

COD should define standard splits for reproducible model evaluation:
- held-out donors
- held-out cell types
- held-out tissues
- held-out interventions
- held-out studies
- temporal splits where available
- compositional OOD splits (new cell type + new intervention)

Without standard splits, COD will not become reusable across teams.

## Phase 10. Gold set creation
Create a smaller, deeply curated gold benchmark with:
- high-confidence action labels
- fully traced provenance
- strict QC
- cross-modal support
- expert-reviewed outcome mappings

This becomes the reference benchmark for models and label quality.

---

# Part XV. Recommended physical implementation

## Storage layout
Use a lakehouse or warehouse-plus-object-store pattern.

Suggested layers:
- `bronze_raw/`
- `silver_normalized/`
- `gold_cod_release/`
- `benchmarks/`
- `ontology/`
- `provenance/`

## File formats
- Parquet for event and metadata tables
- sparse matrix formats for omics features
- graph store or graph tables for pathway and ontology relations
- versioned registries for entity mapping

## Access patterns
Support three access modes:
1. event-centric tabular access
2. modality-centric matrix access
3. graph-centric reasoning over constraints and pathways

---

# Part XVI. Model training tasks enabled by COD

COD should support at least these standard tasks:

1. state -> action prediction
2. state + intervention -> next-state prediction
3. state + intervention -> action distribution
4. state + intervention -> viability / fate outcome
5. counterfactual response prediction
6. trajectory forecasting
7. reward-conditioned policy modeling
8. cross-modal imputation with explicit uncertainty
9. OOD generalization across tissues, donors, and interventions

---

# Part XVII. Observation model: true state vs measured state

A core scientific risk in COD is treating the measured assay output as if it were the true cellular state. In reality, every observation is filtered through technology and processing.

COD should explicitly distinguish:
- **latent biological state**: the unobserved, true operational state of the cell
- **measured state**: the raw assay readout from one or more technologies
- **harmonized state**: the normalized, batch-corrected, ontology-mapped representation used for integration
- **model-inferred state**: the latent representation produced by a learned model

This distinction matters because scRNA-seq dropout, proteomics coverage bias, spatial resolution limits, deconvolution error, and clinical proxy mismatch can all distort the apparent state.

## Required schema additions or conventions

The existing schema already supports some of this through provenance and QC fields. In implementation, COD should also maintain the following conventions:
- never overwrite raw measurements with harmonized values
- preserve assay-specific confidence and coverage metadata
- mark inferred state objects distinctly from directly measured state objects
- keep modality-specific missingness visible even after integration
- require models to report whether a prediction is conditioned on measured, harmonized, or inferred state

## Recommended additional fields
- `state_representation_type` : raw_measured / normalized_measured / harmonized / inferred
- `assay_distortion_notes_ref`
- `measurement_support_score`
- `latent_state_model_ref` : only for inferred state objects

---

# Part XVIII. Causal evidence tiers

Not every state-action-outcome link in COD has the same evidentiary status. COD should therefore classify records and labels by causal strength.

## Recommended evidence tiers

### Tier 0: descriptive observation
The record is observational only. It supports state description but not causal claims.

### Tier 1: association
A state, input, or outcome is statistically associated with another variable, but no intervention is present.

### Tier 2: quasi-causal evidence
Matched comparisons, natural experiments, or carefully controlled observational contrasts provide stronger directional evidence, but confounding remains possible.

### Tier 3: perturbational causal evidence
A defined intervention is applied and a downstream action/output shift is observed in a suitable control design.

### Tier 4: replicated perturbational evidence
The perturbational pattern is reproduced across studies, donors, models, or assay systems.

### Tier 5: mechanistically supported causal evidence
The effect is not only perturbationally supported, but also consistent with regulatory, signaling, or metabolic mechanism layers represented in COD.

## Why this matters
Without causal tiers, models may train on correlations and present them as control rules. COD should make causal status explicit both for labels and for benchmark construction.

## Recommended additional fields
- `causal_evidence_tier`
- `causal_support_ref`
- `replication_count`
- `mechanistic_support_score`

---

# Part XIX. Uncertainty, abstention, and support boundaries

A COD-based model must not always answer confidently. Biological decision systems operate under incomplete support and strong distribution shift.

## Uncertainty types COD should support
- **measurement uncertainty**: noise or low coverage in the observed data
- **label uncertainty**: ambiguity in action or outcome assignment
- **model uncertainty**: weak support for a prediction from the learned model
- **feasibility uncertainty**: unclear whether a proposed action is biologically possible in the current state
- **translation uncertainty**: uncertainty when moving from one assay, donor population, or model system to another

## Required model behavior
COD-trained systems should be designed to:
- abstain on unsupported predictions
- separate `unknown` from `negative`
- report confidence intervals or calibrated uncertainty where possible
- expose whether a recommendation is in-distribution or out-of-support
- downgrade claims when only low-tier causal evidence exists

## Recommended additional fields
- `prediction_support_score`
- `ood_flag`
- `abstention_recommended_flag`
- `uncertainty_vector_ref`

---

# Part XX. From dataset to engine: world, policy, and value models

COD is not only a dataset. It is the substrate for a family of interoperable biological decision models.

## 1. World model
The world model predicts how the cell state evolves.

Typical mappings:
- `state -> next_state`
- `state + intervention -> next_state`
- `state + intervention -> outputs`
- `state + intervention -> outcomes`

The world model is the simulator backbone.

## 2. Policy model
The policy model chooses or ranks interventions based on a goal.

Typical mappings:
- `state -> likely endogenous action distribution`
- `state + target_action -> ranked intervention options`
- `state + reward_context -> intervention policy`

The policy model is the planning and control layer.

## 3. Value model
The value model estimates the expected utility of a state or plan under a reward context.

Typical mappings:
- `state -> expected reward proxy`
- `state + intervention -> expected reward`
- `state + intervention_sequence -> expected cumulative reward`

The value model is the evaluation layer that allows multi-step planning.

## 4. Feasibility and safety filters
Policy outputs should always be passed through:
- constraint profiles
- causal support filters
- toxicity and viability penalties
- out-of-support detection
- human review gates for high-impact uses

## Recommended system interfaces
For each model artifact, define:
- input schema version
- supported modalities
- training support domain
- causal evidence requirements
- uncertainty outputs
- abstention behavior
- benchmark suite used for qualification

---

# Part XXI. Validation ladder for COD-based systems

A COD-based model should not move directly from offline evaluation to real biological decision making.

## Validation stages

### Stage 1: retrospective benchmark validation
Evaluate on held-out COD splits and the gold benchmark.

### Stage 2: held-out perturbation validation
Test whether the model predicts the effects of interventions never seen during training.

### Stage 3: prospective in vitro validation
Run new wet-lab experiments to test predictions on cells or cell lines.

### Stage 4: closed-loop experimental validation
Use the model in an iterative observe-plan-act-measure loop in a controlled lab environment.

### Stage 5: restricted workflow deployment
Deploy only in narrow settings such as perturbation ranking, manufacturing QC, or protocol optimization with expert oversight.

### Stage 6: translational or regulated use
Only after repeated validation, safety review, and context-specific evidence generation.

## Qualification principle
A model should only be used for application classes that match the strongest validation stage it has passed.

---

# Part XXII. Safety envelope and governance for COD-based policy systems

Once COD is used for policy learning, safety and governance become part of the technical specification.

## Core safety principles
- do not present unsupported interventions as reliable controls
- do not suppress uncertainty
- do not recommend actions outside known feasibility space without explicit warning
- do not collapse observational associations into causal recommendations
- require stronger evidence thresholds for higher-stakes application settings

## Practical safety controls
- feasibility gating through constraint profiles
- toxicity and viability penalty functions
- contraindication rules where known
- donor/population support checks
- assay translation checks
- mandatory human review for high-impact outputs

## Governance requirements
- model card per release
- benchmark card per split
- action ontology versioning
- release notes for schema and label changes
- audit trail for model-assisted labeling
- escalation path for biologically implausible recommendations

---

# Part XXIII. Real application pathways enabled by COD

If COD succeeds in representing state, action, reward, and outcome in one operational substrate, it can support several classes of real applications.

## 1. Cell-state forecasting
Predict the next likely actions, outputs, and trajectories of cells under defined contexts.

## 2. Intervention ranking
Given a target action or outcome, rank drugs, edits, ligands, or environmental manipulations most likely to induce it.

## 3. Closed-loop experimental planning
Use COD-trained models inside iterative wet-lab loops to choose the next best experiment.

## 4. Digital cell twins
Simulate how specific cell types, disease cells, or donor-linked states respond under counterfactual interventions.

## 5. Cell engineering and synthetic biology
Optimize reprogramming, persistence, potency, or differentiation protocols using reward-conditioned planning.

## 6. Drug discovery and combination design
Map interventions to action programs, predict resistance trajectories, and rank mechanism-aware combinations.

## 7. Cell therapy manufacturing and QC
Monitor state drift, predict potency loss, and recommend process interventions during manufacturing.

## 8. Clinical decision support, indirectly
Support biomarker discovery, resistance forecasting, and mechanism-aware stratification, initially as recommendation support rather than autonomous clinical control.

## Application maturity ladder
COD-based deployment should progress through four levels:
1. descriptive
2. predictive
3. prescriptive
4. closed-loop control

Most programs should target levels 1-2 first, then constrained level 3 use in validated lab settings.

---

# Part XXIV. What was missing from the earlier draft

The earlier version was directionally right but underspecified for implementation. The main missing pieces were:

1. **The unit of record**
   - it needed to explicitly define that COD is event-based and centered on Cell Transition Events

2. **Separation of schema layers**
   - event table vs modality tables vs provenance vs ontology tables

3. **Action ontology mechanics**
   - hierarchical action labels, zone mapping, confidence, and assignment methods

4. **Provenance and evidence trace**
   - every inferred action and harmonized field needs a trace back to raw evidence

5. **Time model**
   - `t0`, output window, outcome horizon, and uncertainty needed explicit fields

6. **Intervention normalization**
   - a single schema was needed across drugs, CRISPR edits, ligands, and environmental changes

7. **Missingness handling**
   - COD must represent absent modalities explicitly instead of silently imputing

8. **Constraint profiles**
   - regulatory, signaling, and metabolic feasibility must be stored as first-class data products

9. **Benchmark split specification**
   - reusable dataset means reusable evaluation design, not just data packaging

10. **Gold set strategy**
   - a smaller expert-reviewed benchmark is required to calibrate label quality and model evaluation

11. **License and release metadata**
   - needed for cross-dataset redistribution and internal governance

12. **Quality flags and exclusion tracking**
   - needed so teams can filter records consistently

13. **Observation model distinction**
   - latent state, measured state, harmonized state, and model-inferred state needed to be separated

14. **Causal evidence tiers**
   - labels and records needed explicit causal strength semantics

15. **Uncertainty and abstention rules**
   - the earlier draft needed guidance for unknown, low-support, and OOD conditions

16. **Policy / world / value model interfaces**
   - the dataset needed an explicit bridge to decision-system architecture

17. **Validation ladder**
   - offline accuracy alone is not enough for real use

18. **Safety envelope and governance**
   - deployment constraints and auditability needed to be part of the spec

19. **Application pathways**
   - the earlier draft needed a clearer map from COD to practical use cases

---

# Part XXV. Practical guidance for a first full COD build

Because you want all 19 datasets integrated, the right approach is not to blend everything at once into one giant table. Build in this order:

## Track 1. Registries and ontology backbone
Finish first:
- entity registry
- action ontology
- intervention ontology
- tissue/cell/disease mappings

## Track 2. State layer
Unify:
- HCA
- GTEx
- Tabula Sapiens
- CELLxGENE
- HuBMAP

## Track 3. Constraint layer
Unify:
- ENCODE
- Roadmap
- TRRUST
- Reactome
- KEGG
- OmniPath
- Recon3D
- BioModels

## Track 4. Perturbation and response layer
Unify:
- Perturb-seq
- LINCS
- DepMap

## Track 5. Outcome layer
Unify:
- TCGA
- UK Biobank
- viability and fate endpoints from perturbation datasets

## Track 6. Event assembly and benchmark release
Produce:
- COD core event table
- modality tables
- provenance tables
- benchmark splits
- gold benchmark subset

---

# Part XXVI. Final operating definition of COD

The Cell Operating Dataset is:

> A standardized, multi-modal, provenance-aware collection of cell state transition events in which biological state, external inputs, interventions, constraints, actions, outputs, and outcomes are represented in a single interoperable schema.

This is the substrate needed to move from fragmented molecular description to reusable operational modeling of the cell.

---

# Part XXVII. Next immediate deliverables for the team

1. Freeze v0.1 ontology list and identifier standards
2. Define the Cell Transition Event schema in code
3. Build the provenance and evidence-trace model before ingestion scales
4. Choose the first gold-label action families
5. Implement benchmark split policy early
6. Start with a pilot slice across a few datasets to validate event assembly before scaling to all 19


# Part XXVIII. COD versus existing efforts

COD is not proposed because nobody has tried to model or "run" a cell.

That would be incorrect.

There is a long history of serious work toward executable cell models, including:
- mechanistic Virtual Cell systems
- atlas-scale reference cell state resources
- harmonized perturbation datasets
- benchmark suites for perturbation prediction
- platform efforts for AI virtual cells and virtual cell challenges

What is missing is not ambition.

What is missing is a **single, reusable, public operational dataset standard** that unifies:
- state
- inputs
- interventions
- action labels
- short-horizon outputs
- long-horizon outcomes
- reward/objective context
- feasibility constraints
- evidence tiers
- provenance and benchmark splits

## A. Comparison table

| Effort | What it contributes | Where it falls short of full COD |
|---|---|---|
| Virtual Cell / VCell style mechanistic environments | executable mechanistic simulation; explicit kinetics and spatial reasoning | not a large-scale standardized learned dataset across many human cell states, perturbations, and outcomes |
| Human Cell Atlas / CELLxGENE / atlas resources | broad standardized cell-state coverage; cell identity and tissue context | mostly state/reference data; weak coverage of intervention->action->outcome chains |
| scPerturb / PerturBase | harmonized perturbation-response resources; useful for intervention->short-horizon response | limited action ontology, reward context, long-horizon outcomes, and cross-domain linkage |
| PerturBench / benchmark ecosystems | standardized tasks and evaluation | benchmark framework rather than a canonical operational dataset schema |
| Arc / Biohub virtual cell data platforms | large curated collections for virtual-cell model development | closer to COD in spirit, but still primarily platforms/collections rather than a single canonical event schema with action and reward semantics |
| Pathway and knowledge graph resources | regulatory and signaling priors | not event data; cannot by themselves define what a given cell actually did in context |
| Clinical outcome resources | downstream supervision | weak one-to-one linkage from measured single-cell state to exact cellular action trajectories |

## B. The actual gap COD is trying to fill

COD is meant to be the missing middle layer between:
- descriptive atlas data
- perturbation-response data
- knowledge graphs and mechanistic priors
- downstream organismal outcomes

In other words, COD is designed to convert an ecosystem of strong but fragmented resources into a single operational object:

**Cell Transition Event = state + inputs + constraints -> action + outputs + outcomes**

## C. Why the field has not already converged to COD

The main blockers are:
1. destructive measurement and non-repeatability at single-cell resolution
2. unpaired modalities across studies
3. weak or inconsistent intervention metadata
4. sparse time-series and poor temporal alignment
5. lack of standardized action ontology
6. weak linkage between cell-level trajectories and patient-level outcomes
7. missing reward definitions and context-dependent objectives
8. fragmented benchmarking conventions

These are substantial but not fatal.

They mean COD must be built as a **carefully harmonized probabilistic operational dataset**, not as a naive direct concatenation of files.

# Part XXIX. Are the fragmented datasets inherently impossible to join?

No.

But they are also not cleanly joinable in the way relational databases are.

The correct answer is:

**Many parts are joinable after harmonization; some parts are only alignable probabilistically; some links are fundamentally not identifiable unless new data is generated.**

## A. What is straightforwardly joinable

These are usually feasible with careful normalization:

### 1. Entity identifiers
Genes, transcripts, proteins, metabolites, tissues, diseases, and cell types can often be mapped to shared standards.

Examples:
- HGNC / Ensembl for genes
- UniProt for proteins
- HMDB / ChEBI for metabolites
- Cell Ontology for cell types
- Uberon for tissues
- Disease Ontology / MONDO for disease labels

### 2. Feature-level harmonization
A gene expression matrix from one source can often be standardized to the same feature namespace as another source.

### 3. Basic perturbation normalization
Many interventions can be normalized into shared concepts:
- CRISPR KO / KD / activation
- compound exposure
- cytokine stimulation
- environmental stress
- co-culture condition

### 4. Dataset-level metadata harmonization
Donor sex, age bucket, tissue, disease state, assay type, and species can often be normalized.

These are engineering problems, not fundamental scientific impossibilities.

## B. What is only partially joinable

These are feasible, but only through modeling assumptions, not exact joins.

### 1. Unpaired modalities
Many studies measure RNA in one cohort and chromatin or protein in another.
These can be aligned in latent space, but they are not exact paired measurements for the same cells.

### 2. Cross-study state alignment
A macrophage in one study is not automatically the same operational state as a macrophage in another study, even if labels match.
Batch correction and latent alignment help, but cannot guarantee biological equivalence.

### 3. Perturbation comparability
The same nominal perturbation may differ by:
- dose
- duration
- delivery system
- genetic background
- media
- tissue context
- cell cycle distribution

These often require contextual normalization, not simple merging.

### 4. Spatial-to-single-cell linkage
Spatial assays and dissociated single-cell assays often differ in resolution and measured features.
They can inform each other, but not always at exact cell-to-cell correspondence.

### 5. Clinical outcome attribution
Patient-level outcome datasets and cell-level state datasets can often be linked only at sample, cohort, or inferred program level, not at the exact per-cell causal trajectory level.

These are not impossible to use together, but they require explicit uncertainty and evidence tiers.

## C. What is fundamentally missing and cannot be recovered by harmonization alone

These are the true feasibility boundaries.

### 1. Missing paired measurements
If a dataset never measured chromatin and RNA on the same cells, exact cell-level pairing cannot be reconstructed later.
It can only be estimated statistically.

### 2. Missing temporal order
If only a single endpoint is measured, the real sequence of actions leading there is not observed.
Temporal order must be inferred or supplied by additional experiments.

### 3. Missing intervention metadata
If dose, duration, delivery method, or perturbation efficiency are absent, the intervention is only partially defined.
This limits causal interpretation.

### 4. Missing action labels
Most datasets record molecular changes, not operational actions.
Action labels must therefore be inferred via ontology mapping, pathway aggregation, weak supervision, or expert curation.

### 5. Missing reward or objective context
Cells do not optimize one universal scalar objective.
If the biological objective is not specified by context, reward inference remains ambiguous.

### 6. Non-overlapping support
Some combinations of cell type, intervention, tissue, and outcome simply do not exist in current public data.
No harmonization step can create true support where none exists.

## D. The practical consequence for COD

COD should not be built as:
- a single monolithic matrix
- a claim of exact truth for every event
- a universal perfect join of all studies

COD should be built as:
- an event graph with typed evidence
- a multi-table operational warehouse
- a probabilistic alignment framework
- a benchmarked substrate with support boundaries

That means every important COD record should carry:
- evidence tier
- measurement pairing status
- temporal completeness flag
- intervention completeness flag
- support density estimate
- in-domain / out-of-domain tag
- harmonization confidence
- action-label provenance

## E. Design rule for the team

When combining sources, ask three separate questions:

1. **Can these sources be normalized into a common namespace?**
2. **Can these records be aligned in a biologically defensible way?**
3. **Can this link be treated as causal, or only associative?**

Only after all three are answered should a COD edge or event be emitted.

## F. Bottom line

The fragmented datasets are not useless and not fundamentally incompatible.

But they are also not enough, in raw form, to support exact cell-level operational learning across all tasks.

The real build strategy is:
- join what can be exactly normalized
- align what can be probabilistically reconciled
- mark what is inferred rather than observed
- identify what requires new data generation

That is the difference between a scientifically credible COD and an over-merged dataset that hides uncertainty.
