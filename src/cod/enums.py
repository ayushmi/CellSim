from enum import Enum


class InterventionType(str, Enum):
    genetic = "genetic"
    chemical = "chemical"
    ligand = "ligand"
    environmental = "environmental"
    mechanical = "mechanical"
    infectious = "infectious"
    combinatorial = "combinatorial"
    none = "none"


class InterventionDirection(str, Enum):
    knockout = "knockout"
    knockdown = "knockdown"
    overexpression = "overexpression"
    inhibition = "inhibition"
    activation = "activation"
    exposure = "exposure"
    withdrawal = "withdrawal"
    none = "none"


class TimeAnchorType(str, Enum):
    baseline = "baseline"
    post_perturbation = "post_perturbation"
    diagnosis = "diagnosis"
    treatment_cycle = "treatment_cycle"
    developmental_stage = "developmental_stage"
    inferred = "inferred"


class ActionAssignmentMethod(str, Enum):
    direct = "direct"
    curated = "curated"
    inferred = "inferred"
    weak_supervision = "weak_supervision"
    model_assisted = "model_assisted"


class ActionDirectionality(str, Enum):
    activate = "activate"
    suppress = "suppress"
    switch = "switch"
    maintain = "maintain"
    exit = "exit"
    enter = "enter"


class CausalEvidenceTier(int, Enum):
    descriptive_observation = 0
    association = 1
    quasi_causal = 2
    perturbational_causal = 3
    replicated_perturbational = 4
    mechanistically_supported = 5


class StateRepresentationType(str, Enum):
    raw_measured = "raw_measured"
    normalized_measured = "normalized_measured"
    harmonized = "harmonized"
    inferred = "inferred"


class PairingStatus(str, Enum):
    exact_cell = "exact_cell"
    exact_sample = "exact_sample"
    probabilistic_context = "probabilistic_context"
    pseudo_cell = "pseudo_cell"
    unpaired = "unpaired"


class SupportDomainTag(str, Enum):
    in_domain = "in_domain"
    near_domain = "near_domain"
    out_of_domain = "out_of_domain"
