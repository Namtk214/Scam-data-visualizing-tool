# Scam Dataset Visualization Tool

Tool Python + Streamlit để nạp, duyệt, thống kê và trực quan hóa dataset hội thoại scam nhiều tầng annotation.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Cách chạy

```bash
streamlit run app.py
```

Truy cập `http://localhost:8501` trên browser.

## Format input JSON

Mỗi conversation là một JSON object:

```json
{
  "conversation_id": "conv_0001",
  "title": "Tên case",
  "summary": "Mô tả ngắn",
  "context": "Bối cảnh cuộc gọi",
  "conversation_labels": {
    "outcome": "SCAM",
    "scenario_group": "A",
    "scenario_name": "Mạo danh Công an",
    "phase_sequence": ["P1", "P3", "P5"],
    "ambiguity_level": "L1"
  },
  "turns": [
    {
      "turn_id": 1,
      "speaker": "scammer",
      "text": "Nội dung turn...",
      "turn_labels": {
        "ssat": ["SA_AUTH"],
        "vrt": null,
        "vcs": null,
        "phase": "P1"
      },
      "spans": [
        {"label": "FAKE_ID", "start": 15, "end": 39, "text": "Nguyễn Văn Hùng"}
      ]
    }
  ],
  "notes": "Ghi chú..."
}
```

Input hỗ trợ:

- một JSON array `[{...}, {...}]`
- hoặc file JSONL, mỗi dòng là một object

## Labels hỗ trợ

| Field | Values |
|-------|--------|
| outcome | SCAM, AMBIGUOUS, LEGIT |
| scenario_group | A, B, C, D |
| ambiguity_level | L1, L2, L3, L4 |
| phase | P1-P6 |
| ssat | SA_AUTH, SA_THREAT, SA_URGENCY, SA_REASSURE, SA_REQUEST, SA_DEFLECT, SA_VALIDATE, SA_ESCALATE, SA_BAIT, SA_CLOSE |
| vrt | VR_COMPLY, VR_PARTIAL, VR_HESITATE, VR_QUESTION, VR_RESIST, VR_REFUSE, VR_EXPOSE |
| vcs | NEUTRAL, CONFUSED, ANXIOUS, FEARFUL, SUSPICIOUS, RESISTANT |
| span labels | FAKE_ID, FAKE_ORG, URGENCY_PHRASE, THREAT_PHRASE, FAKE_VALIDATION, REQUEST_INFO, DEFLECT_PHRASE, SOCIAL_PROOF |

## Các tabs trong app

1. **Data Input** - Upload/paste JSON, normalize schema, validate và nạp dataset
2. **Data Browser** - Duyệt conversation, xem turn-level detail, spans, filter/search
3. **Dataset Overview** - Mô tả phân bố dataset ở mức conversation, turn, span, persona, quality metadata
4. **Quality Metrics** - 9 metric modules và 25 benchmark visualizations để đánh giá chất lượng dataset
5. **Benchmark Readiness** - Tóm tắt mức độ sẵn sàng cho benchmark tasks
6. **Export** - Export CSV/JSON/markdown summary

## Dataset Overview

Tab **Dataset Overview** là lớp mô tả dataset, không phải tab chấm điểm chất lượng chuẩn hóa. Mục tiêu của nó là trả lời nhanh: dataset đang gồm những gì, phân bố ra sao, cấu trúc hội thoại thế nào, annotation có những loại nào, persona có đa dạng không, và metadata chất lượng đang trông như thế nào.

Luồng dữ liệu của tab này:

- `session.get_filtered()` lấy danh sách conversations sau khi filter
- `compute_stats(...)` tính KPI tổng quát
- `build_conversation_df(...)` tạo bảng conversation-level
- `flatten_to_turn_df(...)` tạo bảng turn-level
- `flatten_to_span_df(...)` tạo bảng span-level

### 1. KPI đầu trang

Các KPI đầu trang cho snapshot tổng quan:

- **Conversations**: tổng số hội thoại
- **Total Turns**: tổng số turns
- **Avg Turns/Conv**: số turn trung bình mỗi conversation
- **Total Spans**: tổng số span annotations
- **Gold Samples**: số conversation có `quality.is_gold = True`
- **Avg AI Score**: trung bình `conversation_meta.ambiguity_score`
- **Avg IAA**: trung bình `quality.iaa_score`
- **Scammer Turns**: tổng số turn của scammer
- **Victim Turns**: tổng số turn của victim
- **Avg DS Score**: trung bình `conversation_meta.difficulty_score`
- **Unique Scenarios**: số `scenario.id` khác nhau
- **Avg Tokens/Turn**: số token trung bình mỗi turn

Đây là lớp summary đầu tiên để biết dataset lớn đến đâu, annotation dày hay mỏng, có bao nhiêu gold samples, và metadata chất lượng hiện tại ra sao.

### 2. Dataset Composition

Nhóm này trả lời câu hỏi: dataset gồm những loại case nào và đang lệch về đâu.

- **Outcome Distribution**: pie chart phân bố `conversation_meta.outcome`
- **Domain L1 Distribution**: bar chart phân bố `scenario.domain_l1`
- **Ambiguity Level**: donut chart phân bố `conversation_meta.ambiguity_level`
- **Difficulty Tier**: bar chart phân bố `conversation_meta.difficulty_tier`

Ý nghĩa:

- Outcome cho biết đầu ra hội thoại thiên về `FULL_COMPLIANCE`, `PARTIAL_COMPLIANCE`, hay `REFUSAL`
- Domain L1 cho biết coverage theo nhóm scam domain
- Ambiguity level cho biết dataset đang nghiêng về case rõ ràng hay nhập nhằng
- Difficulty tier cho biết dataset đang nghiêng về easy/medium/hard/expert

### 3. Scenario Analysis

Nhóm này zoom vào nội dung và bối cảnh kịch bản.

- **Scenario Distribution**: bar chart theo `scenario.name`
- **Fraud Goal Distribution**: bar chart theo `scenario.fraud_goal`
- **Real-World Prevalence**: bar chart theo `scenario.real_world_prevalence`
- **Domain × Outcome**: stacked bar theo `domain_l1 × outcome`

Ý nghĩa:

- Xem dataset có đang lặp lại một vài scenario cụ thể hay không
- Xem fraud goal nào đang chiếm ưu thế
- Xem mức độ bám sát các scam phổ biến ngoài đời
- Xem trong mỗi domain, outcome có bị lệch mạnh không

### 4. Conversation Properties

Nhóm này mô tả tính chất của từng hội thoại ở mức macro.

- **Ambiguity Score vs Difficulty Score**: scatter từ `conversation_meta.ambiguity_score` và `conversation_meta.difficulty_score`
- **Cialdini Principles Used**: bar multi-label từ `conversation_meta.cialdini_principles`
- **Cognitive Mechanisms Used**: bar multi-label từ `conversation_meta.cognitive_mechanisms`
- **Phase Coverage (% of conversations)**: bar chart tỷ lệ conversation có từng phase trong `phases_present`

Ý nghĩa:

- Scatter AI/DS giúp xem conversation nằm trong vùng "sweet spot" hay quá dễ/quá khó
- Cialdini principles cho biết dataset đã phủ bao nhiêu nguyên lý thuyết phục
- Cognitive mechanisms cho biết mức đa dạng cơ chế thao túng/tác động nhận thức
- Phase coverage cho biết mỗi phase có được đại diện đủ rộng trong dataset không

### 5. Annotation Analysis

Nhóm này nhìn dataset ở mức annotation inventory.

- **Scammer Speech Act (SSAT) Frequency**: bar chart tần suất `speech_acts` của scammer
- **Victim Cognitive State (VCS) Distribution**: bar chart phân bố `cognitive_state`
- **Manipulation Intensity Distribution**: histogram `manipulation_intensity`
- **Span Label Distribution**: bar chart phân bố `span_label`

Ý nghĩa:

- Kiểm tra nhãn nào đang nhiều hoặc thiếu
- Quan sát độ đa dạng label ở cả scammer, victim và span level
- Đánh giá phân bố mức độ thao túng của các turn scammer

### 6. Turn Structure Analysis

Nhóm này nhìn cấu trúc hội thoại theo chuỗi turn.

- **Conversation Length Distribution (# Turns)**: histogram số turn mỗi conversation
- **Victim Response Type Distribution**: bar chart phân bố `response_type`
- **Tactic × Phase Heatmap (SSAT)**: heatmap tactic nào hay xuất hiện ở phase nào
- **Phase Transition Matrix**: ma trận chuyển phase giữa các turn liên tiếp
- **Victim State Transition Heatmap (VCS)**: ma trận chuyển trạng thái tâm lý victim

Ý nghĩa:

- Conversation length cho biết dataset thiên về hội thoại ngắn hay dài
- Response type cho biết victim thường phản ứng theo kiểu gì
- Tactic × Phase giúp kiểm tra tính logic giữa tactic và phase
- Hai transition heatmap giúp nhìn flow hội thoại và flow tâm lý của victim

### 7. Persona Analysis

Nhóm này dùng trường `personas` để kiểm tra realism và diversity.

- **Victim Age Range**: bar chart phân bố độ tuổi nạn nhân
- **Victim Vulnerability Profile**: bar chart phân bố profile dễ tổn thương
- **Scammer Speaking Register**: pie chart phân bố phong cách nói của scammer
- **Victim Prior Scam Knowledge**: bar chart mức hiểu biết trước đó của victim

Ý nghĩa:

- Kiểm tra dataset có bị bias theo một nhóm persona nào không
- Kiểm tra scammer persona có đủ đa dạng phong cách không
- Kiểm tra victim có đủ các mức đề kháng khác nhau hay không

### 8. Quality Signals

Nhóm này nhìn metadata chất lượng annotation, chưa phải metric recompute.

- **IAA Score Distribution**: histogram `quality.iaa_score`
- **Expert Authenticity Score (1-5)**: bar chart `quality.expert_authenticity_score`
- **Gold vs Non-Gold Samples**: pie chart tỉ lệ `is_gold`
- **Annotation Method**: bar chart phân bố `quality.annotation_method`

Ý nghĩa:

- IAA phản ánh độ đồng thuận annotator
- Expert authenticity score phản ánh mức độ giống thực tế
- Gold ratio cho biết khả năng dùng dataset để hiệu chuẩn/kiểm thử
- Annotation method cho biết dữ liệu được tạo theo quy trình nào

### 9. Raw Tables

Cuối tab có:

- **Conversation Table**: bảng từ `build_conversation_df(...)`, có nút export CSV
- **Turn Table**: bảng từ `flatten_to_turn_df(...)`

Mục tiêu là cho phép kiểm tra lại dữ liệu gốc sau khi xem biểu đồ, đặc biệt khi cần debug một pattern bất thường.

## Quality Metrics

Tab **Quality Metrics** là lớp đánh giá chuẩn hóa chất lượng dataset. Ở đây hệ thống recompute 9 metric modules và render thành 25 benchmark visualizations.

Luồng dữ liệu:

- mỗi module trong `src/metrics/*.py` tính report/score
- `src/viz/charts_quality.py` biến report thành Plotly figure
- `src/ui/page_quality.py` render vào 9 subtabs

### 1. Ambiguity Index (AI)

AI đo độ tinh vi/nhập nhằng của scam script. Điểm AI được tính từ 6 factor:

- không có `SA_REQUEST`
- `manipulation_intensity` thấp
- register trang trọng nhưng không threat
- victim bị rối
- scammer hay deflect
- outcome là `PARTIAL_COMPLIANCE`

Biểu đồ:

- **#1 AI Score Badge**: gauge tổng `mean_score`, kiểm tra có nằm trong target `0.30-0.55` không
- **#2 Manipulation Intensity Flow**: line chart theo turn, vẽ `manipulation_intensity` của scammer cho một conversation hoặc trung bình toàn dataset
- **#3 Register Mix**: donut phân bố `speaking_register` của scammer
- **#4 Confusion Density Bubble**: bubble theo conversation, trục Y là mật độ victim confusion, kích thước bong bóng là `ambiguity_score`
- **#5 Attack -> Deflect Flow Map**: Sankey từ `SA_THREAT` / `SA_URGENCY` sang `SA_DEFLECT`
- **#6 Outcome × Ambiguity Weight Pie**: pie theo outcome, nhưng diện tích là tổng AI score tích lũy của các conversation thuộc outcome đó

Ý nghĩa:

- Nhóm này cho biết dataset có đủ các case tinh vi, khó nhận diện hay không
- Không chỉ nhìn score tổng mà còn chỉ ra AI đến từ tactic nào, register nào và outcome nào

### 2. Difficulty Score (DS)

DS đo độ khó của conversation đối với mô hình NLP. Điểm DS là tổ hợp 6 thành phần:

- AI contribution
- tactic density
- phase complexity
- linguistic complexity (TTR)
- victim confusion
- scammer adaptability

Biểu đồ:

- **#7 AI vs DS Scatter**: scatter mỗi điểm là 1 conversation, X = AI, Y = DS, màu theo tier khó
- **#8 Tactic Distribution per Conversation**: grouped bar của tactic count trên top 15 conversation giàu tactic nhất
- **#9 Phase Completion Progress**: horizontal progress bar dùng phase coverage từ PCS
- **#10 TTR Distribution**: histogram TTR của scammer text theo conversation
- **#11 VCS State Transition Sankey**: Sankey transition của victim state
- **#12 Adaptability Timeline**: timeline đánh dấu các turn scammer đổi bộ tactic

Ý nghĩa:

- DS không chỉ là "khó hay dễ" mà là khó vì nhiều tactics, nhiều phase, ngôn ngữ phong phú hay vì victim state biến động
- Các chart này giúp bóc tách nguồn gốc của độ khó

### 3. Tactic Coverage Score (TCS)

TCS kiểm tra coverage và imbalance của tactic trong dataset:

- đếm `tactic_counts`
- tactic dưới ngưỡng tối thiểu 50 examples sẽ bị cảnh báo
- tính `gini_coefficient` để đo lệch phân bố

Biểu đồ:

- **#13 Tactic Frequency Bar**: bar ngang số lần xuất hiện từng tactic, có vạch ngưỡng 50 examples
- **#14 Lorenz Curve**: đường Lorenz so với equality line để nhìn mức độ bất bình đẳng phân bố tactic

Ý nghĩa:

- Nếu một số tactic quá ít hoặc phân bố quá lệch, model sẽ khó học tốt trên toàn bộ tactical space

### 4. Linguistic Diversity Score (LDS)

LDS đánh giá độ đa dạng ngôn ngữ của scammer text bằng:

- TTR
- mean pairwise cosine similarity
- near-duplicate ratio
- bigram reuse ratio
- diversity score tổng hợp

Biểu đồ:

- **Summary Cards**: hiển thị `TTR`, `Mean Cosine Similarity`, `Near-Duplicate Pairs`, `Diversity Score`
- **#15 Scammer Vocabulary**: bar ngang top 30 từ phổ biến nhất, đóng vai trò word-cloud dạng bar
- **#16 Similarity Heatmap**: heatmap cosine similarity giữa tối đa 20 conversations

Ý nghĩa:

- Nhóm này kiểm tra dataset có đang lặp wording/pattern quá nhiều hay không
- Similarity heatmap đặc biệt hữu ích để phát hiện near-duplicate conversations

### 5. Phase Completeness Score (PCS)

PCS đo:

- phase coverage ratio cho `P1..P6`
- tính hợp lệ của phase sequence
- đặc biệt theo dõi `P5` vì đây là phase quan trọng cho compliance-related tasks

Biểu đồ:

- **#17 Phase Distribution Stacked Area**: rolling cumulative ratio conversation có từng phase trên toàn dataset
- **#18 Phase Transition Sankey**: luồng chuyển tiếp giữa các phase

Ý nghĩa:

- Cho biết dataset có đầy đủ lifecycle của scam conversation hay không
- Cho biết phase flow có hợp logic hay đang bị thiếu/bị nhảy lùi

### 6. Victim State Validity Score (VSVS)

VSVS kiểm tra chuỗi `cognitive_state` của victim có hợp lệ theo `VALID_TRANSITIONS` hay không.

Biểu đồ:

- **#19 Transition Matrix Heatmap**: heatmap xác suất chuyển trạng thái, hàng là state trước, cột là state sau

Ý nghĩa:

- Ô sáng ở vị trí không mong đợi là dấu hiệu annotation bất hợp lý hoặc victim-state flow không thực tế

### 7. Annotation Quality Score (AQS)

AQS đánh giá chất lượng annotation qua 3 chiều:

- Cohen's Kappa so với gold set
- entropy theo annotator để phát hiện lazy annotation
- span completeness cho các tactic cần span

Biểu đồ:

- **#20 Kappa Heatmap**: heatmap 1 hàng, mỗi cột là một label với giá trị Cohen's Kappa
- **#21 Annotator Entropy Radar**: radar entropy mỗi annotator, kèm team mean và lazy threshold
- **#22 Span Coverage Heatmap**: heatmap `annotator × tactic`, mỗi ô là `% turns có span / turns cần span`

Ý nghĩa:

- Nhóm này dùng để đánh giá trực tiếp độ tin cậy của annotation
- Đây là phần quan trọng nhất nếu dataset được dùng làm benchmark chuẩn

### 8. Dataset Balance Report (DBR)

DBR đo normalized entropy trên 8 chiều:

- `scenario`
- `outcome`
- `length_class`
- `speech_acts`
- `victim_state`
- `domain_l1`
- `difficulty_tier`
- `ambiguity_level`

Biểu đồ:

- **#23 DBR Radar**: radar 8 trục entropy, có ngưỡng target `>= 0.65` và warning `< 0.50`
- **#24 Scenario Representativeness**: stacked bar theo `domain_l1 × outcome`

Ý nghĩa:

- Cho biết dataset có cân bằng trên nhiều chiều phân loại hay không
- Nếu radar méo mạnh hoặc co nhỏ, dataset đang bị bias đáng kể

### 9. Master Evaluation Report (MER)

MER không tạo metric mới mà tổng hợp 8 modules trên thành quyết định release readiness:

- `READY FOR RELEASE`
- `NEEDS REVISION`
- `BLOCKED`

Biểu đồ:

- **#25 MER Dashboard**: indicator grid 5 điều kiện release chính: ambiguity, difficulty, kappa, near-duplicate, balance

Ý nghĩa:

- Đây là bảng tổng hợp cuối cùng để quyết định dataset đã đủ chuẩn benchmark/release hay chưa
- Nhìn nhanh PASS/FAIL của các điều kiện cốt lõi mà không cần đọc từng module riêng lẻ

## Cách add data mới

1. Chuẩn bị file JSON/JSONL theo schema trên
2. Vào tab **Data Input** để upload file
3. Click **Add valid samples to dataset**

## Mở rộng schema

- Thêm label mới: sửa `src/schema.py`
- Thêm visualization overview-level: thêm hàm vào `src/visualize.py`
- Thêm quality chart: thêm hàm vào `src/viz/charts_quality.py`
- Thêm thống kê dạng DataFrame: thêm hàm vào `src/stats.py`
- Thêm metric module: thêm hàm vào `src/metrics/*.py` và render ở `src/ui/page_quality.py`
