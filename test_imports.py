import sys
sys.path.insert(0, '.')
errors = []

# Test schema
try:
    from src.schema import VALID_TRANSITIONS, VCS_LEGACY_MAP_DEFAULT, VALID_DOMAIN_L1
    print('schema OK')
except Exception as e:
    errors.append('schema: ' + str(e))

# Test constants
try:
    from src.constants import MER_PASS_CONDITIONS, classify_length
    print('constants OK')
except Exception as e:
    errors.append('constants: ' + str(e))

# Test normalize
try:
    from src.normalize.normalize_input import normalize_conversation, normalize_dataset
    from src.normalize.legacy_adapter import adapt_legacy, is_legacy_schema
    print('normalize OK')
except Exception as e:
    errors.append('normalize: ' + str(e))

# Test validators
try:
    from src.validators import validate_dataset, validate_basic_schema
    print('validators OK')
except Exception as e:
    errors.append('validators: ' + str(e))

# Test metrics
try:
    from src.metrics.ambiguity_index import compute_ai, dataset_ai_report
    from src.metrics.difficulty_score import compute_ds, dataset_ds_report
    from src.metrics.tactic_coverage import compute_tcs
    from src.metrics.linguistic_diversity import compute_lds
    from src.metrics.phase_completeness import compute_pcs
    from src.metrics.victim_state_validity import compute_vsvs, dataset_vsvs_report
    from src.metrics.annotation_quality import compute_aqs
    from src.metrics.dataset_balance import compute_dbr
    from src.metrics.master_report import compute_mer
    print('metrics OK')
except Exception as e:
    errors.append('metrics: ' + str(e))

# Test demo builders
try:
    from src.demo_builders import build_demo_dataset
    dataset = build_demo_dataset()
    print('demo_builders OK (' + str(len(dataset)) + ' conversations)')
except Exception as e:
    errors.append('demo_builders: ' + str(e))

# Test full pipeline
try:
    dataset_norm = normalize_dataset(dataset)
    val_result = validate_dataset(dataset_norm)
    print('pipeline OK - valid: ' + str(val_result['n_valid']) + ', errors: ' + str(val_result['n_errors']))
except Exception as e:
    errors.append('pipeline: ' + str(e))

# Test MER
try:
    mer = compute_mer(dataset_norm)
    print('MER OK - status: ' + str(mer['status']))
except Exception as e:
    errors.append('MER: ' + str(e))

if errors:
    print('ERRORS:')
    for e in errors:
        print('  - ' + e)
else:
    print('ALL CHECKS PASSED!')
