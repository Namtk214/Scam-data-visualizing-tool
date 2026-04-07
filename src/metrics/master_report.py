"""
master_report.py — Master Evaluation Report (MER) metric.

Aggregate tất cả 8 metric modules → Release Readiness Decision.
Status: READY FOR RELEASE / NEEDS REVISION / BLOCKED
"""
from typing import Dict, Any, List, Optional

from src.constants import MER_PASS_CONDITIONS
from src.metrics.ambiguity_index import dataset_ai_report
from src.metrics.difficulty_score import dataset_ds_report
from src.metrics.tactic_coverage import compute_tcs
from src.metrics.linguistic_diversity import compute_lds
from src.metrics.phase_completeness import compute_pcs
from src.metrics.victim_state_validity import dataset_vsvs_report
from src.metrics.annotation_quality import compute_aqs
from src.metrics.dataset_balance import compute_dbr


def compute_mer(
    dataset: List[Dict[str, Any]],
    gold_set: Optional[List[Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tính Master Evaluation Report.
    
    Args:
        dataset: normalized dataset
        gold_set: optional gold conversations for AQS
        config: optional threshold overrides
    
    Returns:
        {
          summary: {...},
          module_reports: {...},
          all_errors: list,
          all_warnings: list,
          status: READY FOR RELEASE | NEEDS REVISION | BLOCKED,
          recommendation: str,
        }
    """
    thresholds = {**MER_PASS_CONDITIONS, **(config or {})}
    errors: List[str] = []
    warnings: List[str] = []

    module_reports: Dict[str, Any] = {}

    # ── Run all modules (graceful degradation) ─────────────────────
    def _safe_run(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            errors.append(f"[{fn.__module__}] Failed: {e}")
            return {}

    ai_report = _safe_run(dataset_ai_report, dataset)
    module_reports["AI"] = ai_report
    warnings.extend(ai_report.get("warnings", []))

    ds_report = _safe_run(dataset_ds_report, dataset)
    module_reports["DS"] = ds_report
    warnings.extend(ds_report.get("warnings", []))

    tcs_report = _safe_run(compute_tcs, dataset)
    module_reports["TCS"] = tcs_report
    warnings.extend(tcs_report.get("warnings", []))

    lds_report = _safe_run(compute_lds, dataset)
    module_reports["LDS"] = lds_report
    warnings.extend(lds_report.get("warnings", []))

    pcs_report = _safe_run(compute_pcs, dataset)
    module_reports["PCS"] = pcs_report
    warnings.extend(pcs_report.get("warnings", []))

    vsvs_report = _safe_run(dataset_vsvs_report, dataset)
    module_reports["VSVS"] = vsvs_report
    warnings.extend(vsvs_report.get("warnings", []))

    aqs_report = _safe_run(compute_aqs, dataset, gold_set)
    module_reports["AQS"] = aqs_report
    # AQS errors are critical
    for w in aqs_report.get("warnings", []):
        if w.startswith("ERROR"):
            errors.append(f"[AQS] {w}")
        else:
            warnings.append(w)

    dbr_report = _safe_run(compute_dbr, dataset)
    module_reports["DBR"] = dbr_report
    warnings.extend(dbr_report.get("warnings", []))

    # ── Check PASS conditions ──────────────────────────────────────
    mean_ai = ai_report.get("mean_score")
    if mean_ai is not None:
        if not (thresholds["mean_ambiguity_min"] <= mean_ai <= thresholds["mean_ambiguity_max"]):
            warnings.append(
                f"Mean ambiguity {mean_ai:.3f} outside [{thresholds['mean_ambiguity_min']}, {thresholds['mean_ambiguity_max']}]"
            )

    mean_ds = ds_report.get("mean_score")
    if mean_ds is not None:
        if not (thresholds["mean_difficulty_min"] <= mean_ds <= thresholds["mean_difficulty_max"]):
            warnings.append(
                f"Mean difficulty {mean_ds:.3f} outside [{thresholds['mean_difficulty_min']}, {thresholds['mean_difficulty_max']}]"
            )

    mean_kappa = aqs_report.get("mean_kappa")
    if mean_kappa is not None and mean_kappa < thresholds["mean_iaa_kappa_min"]:
        if mean_kappa < 0.65:
            errors.append(f"Mean IAA kappa {mean_kappa:.3f} < 0.65 (critical)")
        else:
            warnings.append(f"Mean IAA kappa {mean_kappa:.3f} < {thresholds['mean_iaa_kappa_min']}")

    near_dup_ratio = lds_report.get("near_dup_ratio", 0)
    if near_dup_ratio > thresholds["near_duplicate_ratio_max"]:
        errors.append(f"Near-duplicate ratio {near_dup_ratio:.1%} > {thresholds['near_duplicate_ratio_max']:.0%}")

    balance_score = dbr_report.get("mean_balance_score", 0)
    if balance_score < thresholds["balance_score_min"]:
        warnings.append(f"Balance score {balance_score:.3f} < {thresholds['balance_score_min']}")

    p5_ratio = pcs_report.get("p5_ratio", 0)
    if p5_ratio < thresholds["p5_coverage_min"]:
        warnings.append(f"P5 coverage {p5_ratio:.1%} < {thresholds['p5_coverage_min']:.0%}")

    span_comp = aqs_report.get("span_completeness", {}).get("completeness_ratio", 0)
    if span_comp < thresholds["span_completeness_min"]:
        warnings.append(f"Span completeness {span_comp:.1%} < {thresholds['span_completeness_min']:.0%}")

    # ── Determine status ───────────────────────────────────────────
    error_count = len(errors)
    warning_count = len(warnings)
    max_warnings = thresholds["max_warnings_for_ready"]

    if error_count > 0:
        status = "BLOCKED"
        recommendation = "Dừng Release. Sửa lỗi hệ thống hoặc re-calibration toàn đội."
    elif warning_count <= max_warnings:
        status = "READY FOR RELEASE"
        recommendation = "Đóng gói, gán version v1.0 và đẩy lên HuggingFace."
    else:
        status = "NEEDS REVISION"
        recommendation = f"Cần re-annotate hoặc bổ sung mẫu. {warning_count} warnings cần xử lý."

    summary = {
        "total_conversations": len(dataset),
        "passed_quality_gate": status == "READY FOR RELEASE",
        "error_count": error_count,
        "warning_count": warning_count,
        "status": status,
        "recommendation": recommendation,
        "mean_ambiguity": mean_ai,
        "mean_difficulty": mean_ds,
        "mean_kappa": mean_kappa,
        "near_dup_ratio": near_dup_ratio,
        "balance_score": balance_score,
    }

    return {
        "summary": summary,
        "module_reports": module_reports,
        "all_errors": errors,
        "all_warnings": warnings,
        "status": status,
        "recommendation": recommendation,
    }
