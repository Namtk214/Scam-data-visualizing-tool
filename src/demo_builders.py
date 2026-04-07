"""
demo_builders.py — Build demo dataset v2 schema đầy đủ.
Tối thiểu 5 conversations:
  1. Authority impersonation (Vietcombank) — FULL_COMPLIANCE — rõ ràng
  2. Commercial fraud (Shopee) — PARTIAL_COMPLIANCE — mờ
  3. Investment fraud (crypto) — REFUSAL — nạn nhân từ chối
  4. Interrupted (interrupted scam)
  5. Non-scam (LEGIT) — legitimate call
"""
from typing import List, Dict, Any
import random


def build_demo_dataset() -> List[Dict[str, Any]]:
    return [
        _conv_vietcombank(),
        _conv_shopee(),
        _conv_crypto(),
        _conv_interrupted(),
        _conv_legit(),
        *_synthetic_variants(),
    ]


def _conv_vietcombank() -> Dict[str, Any]:
    """Authority impersonation — FULL_COMPLIANCE — high manipulation."""
    return {
        "conversation_id": "DEMO_NH_FULL_001",
        "meta": {"dataset_version": "1.0.0", "schema_version": "2.0.0", "language": "vi"},
        "scenario": {
            "id": "NH_VCB",
            "name": "Mạo danh Vietcombank",
            "domain_l1": "AUTHORITY_IMPERSONATION",
            "domain_l2": "Banking",
            "fraud_goal": "otp_extraction",
            "real_world_prevalence": "high",
        },
        "conversation_meta": {
            "length_class": "medium",
            "total_turns": 10,
            "outcome": "FULL_COMPLIANCE",
            "phases_present": ["P1", "P2", "P3", "P4", "P5"],
            "primary_tactics": ["SA_AUTH", "SA_URGENCY", "SA_THREAT"],
            "cialdini_principles": ["authority", "scarcity"],
            "cognitive_mechanisms": ["fear_injection", "cognitive_overload"],
            "ambiguity_score": 0.18,
            "difficulty_score": 0.55,
            "ambiguity_level": "low",
            "difficulty_tier": "hard",
        },
        "personas": {
            "scammer": {"persona_id": "SCM_NH_01", "claimed_identity": "Nhân viên Vietcombank - Phòng Bảo mật",
                        "speaking_register": "formal_professional", "gender_presented": "male"},
            "victim": {"profile_id": "VIC_F45_01", "age_range": "40-55", "gender": "female",
                       "vulnerability_profile": "low_digital_literacy", "prior_scam_knowledge": "none"},
        },
        "turns": [
            {"turn_id": 1, "speaker": "scammer", "phase": "P1", "text": "Xin chào, đây là Ngân hàng Vietcombank, phòng xử lý giao dịch bất thường. Tôi cần xác minh tài khoản số cuối 4523 của chị.",
             "speech_acts": ["SA_AUTH", "SA_VALIDATE"],
             "manipulation_intensity": 2,
             "span_annotations": [{"tag": "FAKE_ORG", "span_text": "Ngân hàng Vietcombank, phòng xử lý giao dịch bất thường"},
                                   {"tag": "FAKE_VALIDATION", "span_text": "tài khoản số cuối 4523"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 2, "speaker": "victim", "phase": "P1", "text": "Vâng, đúng rồi ạ. Có vấn đề gì không?",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_QUESTION", "cognitive_state": "NEUTRAL"},
            {"turn_id": 3, "speaker": "scammer", "phase": "P3", "text": "Tài khoản của chị vừa có 2 giao dịch lạ tổng cộng 47 triệu đồng. Chúng tôi cần đóng băng ngay để bảo vệ chị.",
             "speech_acts": ["SA_THREAT", "SA_URGENCY", "SA_VALIDATE"],
             "manipulation_intensity": 4,
             "span_annotations": [{"tag": "FAKE_VALIDATION", "span_text": "2 giao dịch lạ tổng cộng 47 triệu đồng"},
                                   {"tag": "URGENCY_PHRASE", "span_text": "đóng băng ngay"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 4, "speaker": "victim", "phase": "P3", "text": "Ôi trời, sao lại thế? Tôi không có làm giao dịch gì cả.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_QUESTION", "cognitive_state": "FEARFUL"},
            {"turn_id": 5, "speaker": "scammer", "phase": "P4", "text": "Chính xác, đây là giao dịch bất thường. Để bảo vệ tiền của chị, chúng tôi sẽ chuyển tài khoản vào hệ thống bảo mật. Chị cần cung cấp mã OTP được gửi vào điện thoại ngay bây giờ.",
             "speech_acts": ["SA_REASSURE", "SA_REQUEST"],
             "manipulation_intensity": 4,
             "span_annotations": [{"tag": "REQUEST_INFO", "span_text": "cung cấp mã OTP được gửi vào điện thoại ngay bây giờ"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 6, "speaker": "victim", "phase": "P4", "text": "Nhưng mà... tôi có nên gửi không? Ngân hàng có thực sự cần OTP không?",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_HESITATE", "cognitive_state": "SUSPICIOUS"},
            {"turn_id": 7, "speaker": "scammer", "phase": "P4", "text": "Đây là quy trình bắt buộc của ngân hàng. Nếu chị không xác nhận trong 5 phút, tài khoản sẽ bị khóa vĩnh viễn.",
             "speech_acts": ["SA_VALIDATE", "SA_THREAT", "SA_URGENCY"],
             "manipulation_intensity": 5,
             "span_annotations": [{"tag": "FAKE_VALIDATION", "span_text": "quy trình bắt buộc của ngân hàng"},
                                   {"tag": "THREAT_PHRASE", "span_text": "tài khoản sẽ bị khóa vĩnh viễn"},
                                   {"tag": "URGENCY_PHRASE", "span_text": "trong 5 phút"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 8, "speaker": "victim", "phase": "P4", "text": "Ừ thôi được, mã OTP của tôi là 483726.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_COMPLY", "cognitive_state": "COMPLIANT"},
            {"turn_id": 9, "speaker": "scammer", "phase": "P5", "text": "Cảm ơn chị, tài khoản của chị đã được bảo mật thành công.",
             "speech_acts": ["SA_CLOSE", "SA_REASSURE"],
             "manipulation_intensity": 1,
             "span_annotations": [],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 10, "speaker": "victim", "phase": "P5", "text": "Cảm ơn anh.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_COMPLY", "cognitive_state": "COMPLIANT"},
        ],
        "quality": {
            "writer_id": "W01", "expert_reviewer_id": "EX01",
            "annotation_method": "adversarial_roleplay",
            "iaa_score": 0.89, "expert_authenticity_score": 5, "is_gold": True,
        },
    }


def _conv_shopee() -> Dict[str, Any]:
    """Commercial fraud Shopee — PARTIAL_COMPLIANCE — gray area."""
    return {
        "conversation_id": "DEMO_TMDT_PARTIAL_002",
        "meta": {"dataset_version": "1.0.0", "schema_version": "2.0.0", "language": "vi"},
        "scenario": {
            "id": "TMDT_SHOPEE",
            "name": "Mạo danh Shopee hỗ trợ",
            "domain_l1": "COMMERCIAL_FRAUD",
            "domain_l2": "E-commerce",
            "fraud_goal": "account_takeover",
            "real_world_prevalence": "very_high",
        },
        "conversation_meta": {
            "length_class": "medium",
            "total_turns": 8,
            "outcome": "PARTIAL_COMPLIANCE",
            "phases_present": ["P1", "P2", "P3", "P4"],
            "primary_tactics": ["SA_AUTH", "SA_REASSURE", "SA_DEFLECT"],
            "cialdini_principles": ["authority", "liking"],
            "cognitive_mechanisms": ["false_authority", "manufactured_urgency"],
            "ambiguity_score": 0.52,
            "difficulty_score": 0.62,
            "ambiguity_level": "medium",
            "difficulty_tier": "hard",
        },
        "personas": {
            "scammer": {"persona_id": "SCM_TMDT_02", "claimed_identity": "CSKH Shopee - Bộ phận hoàn tiền",
                        "speaking_register": "semi_formal", "gender_presented": "female"},
            "victim": {"profile_id": "VIC_M30_02", "age_range": "25-35", "gender": "male",
                       "vulnerability_profile": "moderate_digital_literacy", "prior_scam_knowledge": "low"},
        },
        "turns": [
            {"turn_id": 1, "speaker": "scammer", "phase": "P1", "text": "Dạ anh ơi, em là nhân viên hỗ trợ Shopee. Em thấy đơn hàng của anh bị lỗi thanh toán, anh có được thông báo không ạ?",
             "speech_acts": ["SA_AUTH", "SA_BAIT"],
             "manipulation_intensity": 2,
             "span_annotations": [{"tag": "FAKE_ORG", "span_text": "nhân viên hỗ trợ Shopee"},
                                   {"tag": "FAKE_VALIDATION", "span_text": "đơn hàng của anh bị lỗi thanh toán"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 2, "speaker": "victim", "phase": "P1", "text": "Lỗi thanh toán? Mình không thấy thông báo gì lúc mua hàng.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_QUESTION", "cognitive_state": "CURIOUS"},
            {"turn_id": 3, "speaker": "scammer", "phase": "P2", "text": "Đúng vậy anh, hệ thống bị lỗi nên không báo ạ. Bên em kiểm tra thấy anh bị trừ tiền 2 lần rồi. Em muốn giúp anh hoàn tiền.",
             "speech_acts": ["SA_VALIDATE", "SA_REASSURE"],
             "manipulation_intensity": 3,
             "span_annotations": [{"tag": "FAKE_VALIDATION", "span_text": "hệ thống bị lỗi nên không báo"},
                                   {"tag": "SOCIAL_PROOF", "span_text": "anh bị trừ tiền 2 lần rồi"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 4, "speaker": "victim", "phase": "P2", "text": "Ừ mình có đặt hàng, nhưng sao họ lại gọi điện? Shopee thường chat mà.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_QUESTION", "cognitive_state": "SUSPICIOUS"},
            {"turn_id": 5, "speaker": "scammer", "phase": "P3", "text": "Dạ đúng anh ơi, trường hợp hoàn tiền số lớn trên 500k bên em gọi điện trực tiếp để xác nhận ạ. Anh cho em xác nhận tên và số thẻ nhé.",
             "speech_acts": ["SA_DEFLECT", "SA_REQUEST"],
             "manipulation_intensity": 3,
             "span_annotations": [{"tag": "DEFLECT_PHRASE", "span_text": "trường hợp hoàn tiền số lớn trên 500k bên em gọi điện trực tiếp"},
                                   {"tag": "REQUEST_INFO", "span_text": "xác nhận tên và số thẻ"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 6, "speaker": "victim", "phase": "P3", "text": "Số thẻ thì mình không muốn cung cấp... nhưng tên thì được.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_PARTIAL", "cognitive_state": "SUSPICIOUS"},
            {"turn_id": 7, "speaker": "scammer", "phase": "P4", "text": "Anh ơi, không có số thẻ thì hệ thống không thể hoàn tiền được. Anh yên tâm, đây chỉ để xác minh thôi ạ.",
             "speech_acts": ["SA_REASSURE", "SA_ESCALATE"],
             "manipulation_intensity": 4,
             "span_annotations": [{"tag": "DEFLECT_PHRASE", "span_text": "chỉ để xác minh thôi ạ"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 8, "speaker": "victim", "phase": "P4", "text": "Thôi mình không cung cấp số thẻ đâu, Shopee không bao giờ yêu cầu số thẻ đầy đủ.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_REFUSE", "cognitive_state": "RESISTANT"},
        ],
        "quality": {
            "writer_id": "W02", "expert_reviewer_id": "EX01",
            "annotation_method": "adversarial_roleplay",
            "iaa_score": 0.82, "expert_authenticity_score": 4, "is_gold": False,
        },
    }


def _conv_crypto() -> Dict[str, Any]:
    """Investment fraud crypto — REFUSAL — victim sharp."""
    return {
        "conversation_id": "DEMO_INV_REFUSAL_003",
        "meta": {"dataset_version": "1.0.0", "schema_version": "2.0.0", "language": "vi"},
        "scenario": {
            "id": "INV_CRYPTO",
            "name": "Lừa đảo đầu tư crypto",
            "domain_l1": "INVESTMENT_FRAUD",
            "domain_l2": "Cryptocurrency",
            "fraud_goal": "investment_deposit",
            "real_world_prevalence": "high",
        },
        "conversation_meta": {
            "length_class": "short",
            "total_turns": 6,
            "outcome": "REFUSAL",
            "phases_present": ["P1", "P2", "P3"],
            "primary_tactics": ["SA_BAIT", "SA_AUTH", "SA_DEFLECT"],
            "cialdini_principles": ["social_proof", "scarcity"],
            "cognitive_mechanisms": ["fear_then_relief", "false_authority"],
            "ambiguity_score": 0.38,
            "difficulty_score": 0.42,
            "ambiguity_level": "medium",
            "difficulty_tier": "medium",
        },
        "personas": {
            "scammer": {"persona_id": "SCM_INV_03", "claimed_identity": "Chuyên gia đầu tư - CEO VN Capital",
                        "speaking_register": "semi_formal", "gender_presented": "male"},
            "victim": {"profile_id": "VIC_M35_03", "age_range": "30-40", "gender": "male",
                       "vulnerability_profile": "high_digital_literacy", "prior_scam_knowledge": "medium"},
        },
        "turns": [
            {"turn_id": 1, "speaker": "scammer", "phase": "P1", "text": "Anh ơi, em là Minh từ VN Capital. Anh có quan tâm đến cơ hội đầu tư crypto đang cho lợi nhuận 30%/tháng không?",
             "speech_acts": ["SA_AUTH", "SA_BAIT"],
             "manipulation_intensity": 2,
             "span_annotations": [{"tag": "FAKE_ORG", "span_text": "VN Capital"},
                                   {"tag": "SOCIAL_PROOF", "span_text": "lợi nhuận 30%/tháng"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 2, "speaker": "victim", "phase": "P1", "text": "30% một tháng? Nghe phi thực tế quá. Làm sao có mức đó?",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_QUESTION", "cognitive_state": "SUSPICIOUS"},
            {"turn_id": 3, "speaker": "scammer", "phase": "P2", "text": "Đây là hệ thống trading AI thần kỳ mới nhất, bot chạy 24/7. Tháng này nhiều khách đã rút lời mà tôi vẫn đang chờ anh đấy.",
             "speech_acts": ["SA_VALIDATE", "SA_URGENCY", "SA_BAIT"],
             "manipulation_intensity": 3,
             "span_annotations": [{"tag": "FAKE_VALIDATION", "span_text": "hệ thống trading AI thần kỳ mới nhất"},
                                   {"tag": "URGENCY_PHRASE", "span_text": "nhiều khách đã rút lời mà tôi vẫn đang chờ anh"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 4, "speaker": "victim", "phase": "P2", "text": "Không có đầu tư nào đảm bảo lợi nhuận như vậy. Đây là scam rõ ràng.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_EXPOSE", "cognitive_state": "RESISTANT"},
            {"turn_id": 5, "speaker": "scammer", "phase": "P3", "text": "Anh lầm rồi, đây là công nghệ mới, tôi có thể cho anh xem report của 100 nhà đầu tư...",
             "speech_acts": ["SA_DEFLECT", "SA_VALIDATE"],
             "manipulation_intensity": 3,
             "span_annotations": [{"tag": "DEFLECT_PHRASE", "span_text": "Anh lầm rồi"},
                                   {"tag": "SOCIAL_PROOF", "span_text": "report của 100 nhà đầu tư"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 6, "speaker": "victim", "phase": "P3", "text": "Không cần. Tôi không quan tâm. Đừng gọi lại.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_REFUSE", "cognitive_state": "REFUSING"},
        ],
        "quality": {
            "writer_id": "W03", "expert_reviewer_id": "EX02",
            "annotation_method": "expert_written",
            "iaa_score": 0.91, "expert_authenticity_score": 4, "is_gold": True,
        },
    }


def _conv_interrupted() -> Dict[str, Any]:
    """Interrupted conversation — early hang-up."""
    return {
        "conversation_id": "DEMO_INTERRUPTED_004",
        "meta": {"dataset_version": "1.0.0", "schema_version": "2.0.0", "language": "vi"},
        "scenario": {
            "id": "NH_VCB",
            "name": "Mạo danh ngân hàng bị ngắt",
            "domain_l1": "AUTHORITY_IMPERSONATION",
            "domain_l2": "Banking",
            "fraud_goal": "otp_extraction",
            "real_world_prevalence": "high",
        },
        "conversation_meta": {
            "length_class": "short",
            "total_turns": 4,
            "outcome": "INTERRUPTED",
            "phases_present": ["P1", "P3"],
            "primary_tactics": ["SA_AUTH", "SA_URGENCY"],
            "cialdini_principles": ["authority"],
            "cognitive_mechanisms": ["fear_injection"],
            "ambiguity_score": 0.72,
            "difficulty_score": 0.60,
            "ambiguity_level": "high",
            "difficulty_tier": "hard",
        },
        "personas": {
            "scammer": {"persona_id": "SCM_NH_04", "claimed_identity": "Cảnh sát kinh tế",
                        "speaking_register": "authoritative", "gender_presented": "male"},
            "victim": {"profile_id": "VIC_F60_04", "age_range": "55-70", "gender": "female",
                       "vulnerability_profile": "low_digital_literacy", "prior_scam_knowledge": "none"},
        },
        "turns": [
            {"turn_id": 1, "speaker": "scammer", "phase": "P1", "text": "Đây là Cảnh sát kinh tế Hà Nội. Bà có liên quan đến vụ án rửa tiền 2 tỷ đồng đang điều tra.",
             "speech_acts": ["SA_AUTH", "SA_THREAT"],
             "manipulation_intensity": 5,
             "span_annotations": [{"tag": "FAKE_ID", "span_text": "Cảnh sát kinh tế Hà Nội"},
                                   {"tag": "FAKE_VALIDATION", "span_text": "vụ án rửa tiền 2 tỷ đồng"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 2, "speaker": "victim", "phase": "P1", "text": "Sao lại... trời ơi...",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_HESITATE", "cognitive_state": "FEARFUL"},
            {"turn_id": 3, "speaker": "scammer", "phase": "P3", "text": "Bà cần hợp tác ngay bây giờ, chuyển toàn bộ tài sản vào tài khoản an ninh để chúng tôi bảo vệ.",
             "speech_acts": ["SA_URGENCY", "SA_REQUEST"],
             "manipulation_intensity": 5,
             "span_annotations": [{"tag": "URGENCY_PHRASE", "span_text": "ngay bây giờ"},
                                   {"tag": "REQUEST_INFO", "span_text": "chuyển toàn bộ tài sản"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 4, "speaker": "victim", "phase": "P3", "text": "[Cúp máy]",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": None, "cognitive_state": "FEARFUL"},
        ],
        "quality": {
            "writer_id": "W01", "expert_reviewer_id": "EX01",
            "annotation_method": "adversarial_roleplay",
            "iaa_score": 0.85, "expert_authenticity_score": 5, "is_gold": False,
        },
    }


def _conv_legit() -> Dict[str, Any]:
    """Legitimate call — REFUSAL — not a scam."""
    return {
        "conversation_id": "DEMO_LEGIT_005",
        "meta": {"dataset_version": "1.0.0", "schema_version": "2.0.0", "language": "vi"},
        "scenario": {
            "id": "LEGIT_BANK",
            "name": "Cuộc gọi ngân hàng hợp lệ",
            "domain_l1": "AUTHORITY_IMPERSONATION",
            "domain_l2": "Banking",
            "fraud_goal": "none",
            "real_world_prevalence": "high",
        },
        "conversation_meta": {
            "length_class": "short",
            "total_turns": 4,
            "outcome": "REFUSAL",
            "phases_present": ["P1", "P2"],
            "primary_tactics": ["SA_AUTH"],
            "cialdini_principles": [],
            "cognitive_mechanisms": [],
            "ambiguity_score": 0.28,
            "difficulty_score": 0.32,
            "ambiguity_level": "low",
            "difficulty_tier": "medium",
        },
        "personas": {
            "scammer": {"persona_id": "LEGIT_AGENT_05", "claimed_identity": "CSKH Techcombank",
                        "speaking_register": "formal_professional", "gender_presented": "female"},
            "victim": {"profile_id": "VIC_M40_05", "age_range": "35-45", "gender": "male",
                       "vulnerability_profile": "high_digital_literacy", "prior_scam_knowledge": "high"},
        },
        "turns": [
            {"turn_id": 1, "speaker": "scammer", "phase": "P1", "text": "Xin chào anh, đây là Techcombank. Chúng tôi gọi để thông báo thẻ tín dụng của anh sắp hết hạn vào tháng 6.",
             "speech_acts": ["SA_AUTH"],
             "manipulation_intensity": 1,
             "span_annotations": [{"tag": "FAKE_ORG", "span_text": "Techcombank"}],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 2, "speaker": "victim", "phase": "P1", "text": "Vâng, tôi đã biết rồi, ngân hàng đã nhắn tin cho tôi.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_COMPLY", "cognitive_state": "NEUTRAL"},
            {"turn_id": 3, "speaker": "scammer", "phase": "P2", "text": "Anh có muốn làm lại thẻ qua hotline hoặc đến chi nhánh không ạ?",
             "speech_acts": ["SA_REQUEST"],
             "manipulation_intensity": 1,
             "span_annotations": [],
             "response_type": None, "cognitive_state": None},
            {"turn_id": 4, "speaker": "victim", "phase": "P2", "text": "Để tôi tự làm trên app, không cần qua điện thoại.",
             "speech_acts": [], "manipulation_intensity": None,
             "span_annotations": [],
             "response_type": "VR_REFUSE", "cognitive_state": "NEUTRAL"},
        ],
        "quality": {
            "writer_id": "W02", "expert_reviewer_id": "EX02",
            "annotation_method": "expert_written",
            "iaa_score": 0.95, "expert_authenticity_score": 5, "is_gold": True,
        },
    }


def _synthetic_variants() -> List[Dict[str, Any]]:
    """Generate synthetic variants for metric computation."""
    outcomes = ["FULL_COMPLIANCE", "PARTIAL_COMPLIANCE", "REFUSAL", "INTERRUPTED"]
    domains = ["AUTHORITY_IMPERSONATION", "COMMERCIAL_FRAUD", "INVESTMENT_FRAUD", "ROMANCE_FRAUD"]
    ambig_levels = ["low", "medium", "high"]
    diff_tiers = ["easy", "medium", "hard", "expert"]

    samples = []
    for i in range(10):
        n_turns = random.randint(4, 14)
        turns = _gen_synthetic_turns(n_turns)
        outcome = random.choice(outcomes)
        domain = random.choice(domains)
        ambig = random.choice(ambig_levels)
        diff = random.choice(diff_tiers)
        samples.append({
            "conversation_id": f"DEMO_SYN_{i+6:03d}",
            "meta": {"dataset_version": "1.0.0", "schema_version": "2.0.0", "language": "vi"},
            "scenario": {
                "id": f"SYN_{domain[:4]}_{i:02d}",
                "name": f"Synthetic {domain.replace('_',' ')} #{i+1}",
                "domain_l1": domain,
                "domain_l2": "",
                "fraud_goal": "general",
                "real_world_prevalence": "medium",
            },
            "conversation_meta": {
                "length_class": "short" if n_turns < 8 else "medium",
                "total_turns": n_turns,
                "outcome": outcome,
                "phases_present": list(set(t.get("phase") for t in turns if t.get("phase"))),
                "primary_tactics": [],
                "cialdini_principles": [],
                "cognitive_mechanisms": [],
                "ambiguity_score": {"low": 0.2, "medium": 0.5, "high": 0.75}[ambig],
                "difficulty_score": {"easy": 0.2, "medium": 0.45, "hard": 0.63, "expert": 0.82}[diff],
                "ambiguity_level": ambig,
                "difficulty_tier": diff,
            },
            "personas": None,
            "turns": turns,
            "quality": {
                "writer_id": f"W0{(i%3)+1}",
                "expert_reviewer_id": None,
                "annotation_method": "adversarial_roleplay",
                "iaa_score": round(0.75 + random.random() * 0.2, 2),
                "expert_authenticity_score": random.randint(3, 5),
                "is_gold": False,
            },
        })
    return samples


def _gen_synthetic_turns(n: int) -> List[Dict[str, Any]]:
    ssat_pool = ["SA_AUTH", "SA_THREAT", "SA_URGENCY", "SA_REASSURE", "SA_REQUEST",
                 "SA_DEFLECT", "SA_VALIDATE", "SA_ESCALATE", "SA_BAIT", "SA_CLOSE"]
    vcs_pool = ["NEUTRAL", "CURIOUS", "CONCERNED", "FEARFUL", "SUSPICIOUS", "COMPLIANT", "RESISTANT"]
    vrt_pool = ["VR_COMPLY", "VR_PARTIAL", "VR_HESITATE", "VR_QUESTION", "VR_RESIST", "VR_REFUSE"]
    phases = ["P1"] * 2 + ["P2"] * 2 + ["P3"] * 2 + ["P4"] * 2 + ["P5"] * 2 + ["P6"] * 2
    turns = []
    vcs_state = "NEUTRAL"
    vcs_seq = ["NEUTRAL", "CURIOUS", "CONCERNED", "FEARFUL", "COMPLIANT"]
    vcs_i = 0
    for i in range(n):
        speaker = "scammer" if i % 2 == 0 else "victim"
        ph = phases[min(i // 2, len(phases) - 1)]
        if speaker == "scammer":
            n_acts = random.randint(1, 3)
            acts = random.sample(ssat_pool, n_acts)
            turns.append({
                "turn_id": i + 1,
                "speaker": "scammer",
                "phase": ph,
                "text": f"Scammer turn {i+1}: synthetic text mô phỏng hội thoại lừa đảo.",
                "speech_acts": acts,
                "manipulation_intensity": random.randint(1, 5),
                "span_annotations": [],
                "response_type": None,
                "cognitive_state": None,
            })
        else:
            vcs_i = min(vcs_i + random.randint(0, 1), len(vcs_seq) - 1)
            vcs_state = vcs_seq[vcs_i]
            turns.append({
                "turn_id": i + 1,
                "speaker": "victim",
                "phase": ph,
                "text": f"Victim turn {i+1}: phản hồi tự nhiên của nạn nhân.",
                "speech_acts": [],
                "manipulation_intensity": None,
                "span_annotations": [],
                "response_type": random.choice(vrt_pool),
                "cognitive_state": vcs_state,
            })
    return turns
