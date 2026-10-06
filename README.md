# 古画临摹工艺谱系库

记录故宫古画摹本**从研究成果到正式藏品**全生命周期的领域事件契约与最小实现。摹本的身份会变化，但它成为藏品以前的制作语境——参照版本、勘察、材料批次、阶段影像、试验样张、指导关系、装裱修复、专家意见——必须原样保留，不能因沿用普通复制品台账而丢失。

## 核心规则

1. **只追加、不可覆盖**：事件只能追加。`event_id`、`occurred_at`、`version` 一经接收不得原地改写；同一 `aggregate_id` 内 `version` 从 1 起连续递增。
2. **更正只走后继事件**：新认识（如检测新结论）通过 `links.supersedes_event_id` 追加后继记录，被更正事件保留；检测结论可对旧说明挂"待复核"标记，但不倒改当时采用的认识。
3. **传统诀窍分级可见**：`access.classification=custodian_only` 的记录（如颜料炮制诀窍）只登记保管人（`custodian`）与授权范围（`authorization_scopes`），普通研究者看不到 `payload` 与证据，只见"此处有受限记录及由谁保管"。
4. **失败也留痕**：多人接续或并行时用 `attempt_id` 区分分支，每个人的责任范围（`scope`）、指导关系（`supervised_by_person_id`）和失败试验（`TRIAL_RECORDED/outcome=failed`，必填 `failure_reason`）都进入谱系。
5. **标签与当前身份一致**：巡展标签携带签发瞬间的身份快照（摹本/教学样张、身份状态、保管级别、许可），系统将其与事件流投影出的当前状态核对，不一致即拒绝。

## 聚合与事件

| 聚合 `aggregate_type` | 事件 |
| --- | --- |
| `reference_work` 参照原作 | `REFERENCE_FROZEN`（锁定参照版本状态） |
| `examination` 勘察检测 | `EXAMINATION_RECORDED`、`FINDING_RECORDED`（可挂说明复核标记） |
| `replica_project` 临摹项目 | `PROJECT_OPENED`、`ASSIGNMENT_RECORDED`（分工/指导）、`TRIAL_RECORDED`（试样与失败留痕）、`STAGE_ATTESTED`（阶段影像）、`DETAIL_RECORDED`（细节与代际）、`GENERATION_LINKED`（母本关系） |
| `material_lot` 材料批次 | `MATERIAL_LOT_RECORDED`（纸/绢/颜料批次，诀窍可在此受限）、`MATERIAL_TESTED` |
| `replica_object` 摹本/样张 | `OBJECT_REGISTERED`、`IDENTITY_RECLASSIFIED`（研究成果→藏品等身份变更）、`MOUNTING_RECORDED`、`CONSERVATION_PERFORMED`、`EXPERT_OPINION_RECORDED`、`DESCRIPTION_REVIEW_FLAGGED` |
| `collection_decision` 入藏决定 | `OBJECT_ACCESSIONED`（决定、入藏号、保管级别 L1–L3、许可、入藏依据） |
| `loan_label` 巡展标签 | `LABEL_REVISED`、`LOAN_LABEL_ISSUED` |

对象三分：原作（`reference_work`）、摹本（`object_kind=facsimile`）、教学样张（`teaching_sample`），由投影明确区分，避免台账混列。

> 注：`MATERIAL_TESTED` 属于 `material_lot` 聚合；项目级试样结果用 `TRIAL_RECORDED`。

## 访问分级

| classification | 谁能读内容 |
| --- | --- |
| `open` | 所有调用方 |
| `restricted` | 持有 `research_access` 的研究者 |
| `custodian_only` | 保管人（`is_custodian`）或持有对应授权码（如 `know_how:pigment_preparation`）者；其他人只见保管人与授权范围登记 |

## 三类使用方式

- **研究者**：按稳定的细节编码（如 `peak.cun_texture`）取出同一细节在一代摹（1986，绢本六层积染）与二代教学再摹（2003，纸本四层积染）的处理进行比较；按 `attempt_id` 查看成功与失败的全部试验。
- **藏品管理员**：`classify()` 区分 original / facsimile / teaching_sample；`object_state()` 给出当前身份、入藏号、保管级别与许可，并显示仍待复核的旧说明。
- **巡展借用**：`issue_label_snapshot()` 按当前状态生成标签快照；`label_mismatches()` 核对送审标签，旧身份（"研究成果/普通复制品"）标签会被拦截。

## 目录

- `contracts/domain.schema.json`：跨系统正式契约（JSON Schema 2020-12，含事件—聚合归属与 payload 条件约束）。
- `data/sample.json`：单信封联调样例。
- `data/lineage_sample.json`：32 个事件的完整样例谱系（1985 立项研究临摹 → 失败染绢试验 → 1986 摹本登记为研究成果 → 1990 目验意见 → 2001 修复 → 2019 检测翻案并挂复核 → 2021 凭作者/材料/工艺价值入藏二级 → 2003 二代教学再摹与样张 → 2026 秋巡标签）。
- `src/validator.py`：信封与 payload 基础校验（零依赖）。
- `src/stream.py`：只追加事件流与版本/更正不变量。
- `src/access.py`：访问分级与脱敏视图。
- `src/projection.py`：身份投影、代际细节比较、试验/责任查询、标签一致性核对。
- `tests/`：契约、流不变量、脱敏、投影与正式 schema 校验。

## 本地检查

```bash
pip install -r requirements.txt   # jsonschema 仅用于正式契约校验，核心代码零依赖
python3 -m unittest discover -s tests
```
