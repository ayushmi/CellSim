# Source Support Matrix

| Source | Family | Access | Automated fetch | State depth | Intervention depth | Outcome depth | Action usefulness | Status | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Human Cell Atlas | baseline_state | public | true | metadata_first | none | none | low_to_moderate | partially implemented | full expression ingestion requires per-project file resolution and heavier downstream processing |
| GTEx | baseline_state | mixed | true | bulk_state_potential | none | low | low | public-subset deeply implemented | current open path is bulk tissue reference rather than single-cell state |
| Tabula Sapiens | baseline_state | public | false | high | none | none | moderate | partially implemented | default repo path uses manual/local h5ad adapter rather than automated public fetch |
| ENCODE | regulatory_logic | public | true | regulatory_metadata_first | none | none | moderate | partially implemented | real signal summarization from bigWig/peak files is not yet in place |
| Roadmap Epigenomics | regulatory_logic | public | false | high | none | none | moderate | partially implemented | current implementation is local/manual metadata adapter rather than default automated fetch |
| TRRUST | regulatory_logic | public | true | graph_only | none | none | moderate | knowledge/ontology fully integrated | current path is edge-level knowledge integration, not state-bearing observation |
| Perturb-seq | perturbation_response | public | true | medium | high | low_to_moderate | high | public-subset deeply implemented | generalized multi-study matrix parsing and differential pipeline are still limited |
| LINCS | perturbation_response | public | true | medium | high | low | high | public-subset deeply implemented | public path uses a small Level2 landmark-gene subset rather than full compendium signatures |
| DepMap | perturbation_response | public | true | medium | high | medium | high | public-subset deeply implemented | current path uses public pediatric subset rather than the full portal release |
| Recon3D | metabolism_feasibility | public | false | graph_only | none | none | moderate | partially implemented | current implementation is a local SBML/manual adapter rather than automated fetch |
| BioModels | metabolism_feasibility | public | true | simulated_model | variable | simulated | moderate | knowledge/ontology fully integrated | current integration uses model metadata and download refs, not simulation execution |
| HMDB | metabolism_feasibility | mixed | false | registry_only | none | none | low_to_moderate | partially implemented | anti-bot/licensing boundaries mean the default repo path relies on a local download adapter |
| HuBMAP | spatial_context | mixed | true | metadata_first | none | none | moderate | partially implemented | full spatial payload transfer and neighborhood reconstruction are not yet automated |
| CELLxGENE | spatial_context | public | true | high | low | low | moderate | public-subset deeply implemented | only a small public subset is ingested and only marker-gene slices are extracted |
| TCGA | clinical_outcomes | mixed | true | metadata_first_public | low | medium | low_to_moderate | controlled-data adapter implemented | deep molecular state requires controlled or larger public file handling |
| UK Biobank | clinical_outcomes | controlled | false | high_potential | observational | high | low_to_moderate | controlled-data adapter implemented | cohort access remains controlled and cannot be automated in the public-open repo |
| Reactome | signaling_graph | public | true | graph_only | none | none | high | knowledge/ontology fully integrated | current path is pathway/knowledge support rather than direct cellular measurement |
| KEGG | signaling_graph | mixed | false | graph_only | none | none | high | controlled-data adapter implemented | licensing/reuse boundaries still prevent a default automated public-open fetch path |
| OmniPath | signaling_graph | public | true | graph_only | none | none | high | knowledge/ontology fully integrated | event-context grounding still depends on other state-bearing sources |
