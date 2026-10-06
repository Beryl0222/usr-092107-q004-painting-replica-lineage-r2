# 古画临摹工艺谱系库

本仓库记录该项目已确认的领域对象、事件名称和基础校验方式，便于不同系统交换一致的数据。

## 资料范围

- `contracts/domain.schema.json`：领域事件信封、聚合类型与事件名称，以及各事件的必备字段。
- `data/sample.json`：一条用于本地联调的中文样例。
- `data/lineage_example.json`：一条完整的接续谱系样例，演示从参照冻结到巡展标签的各节点。
- `src/`：事件信封的最小校验代码，与契约中的规则保持一致。
- `tests/`：验证样例符合基础约定，并覆盖主要领域规则的正反例。

## 聚合类型

| 聚合 | 含义 |
| --- | --- |
| `reference_work` | 参照原作及其版本、勘察资料 |
| `replica_project` | 临摹项目，承接责任分工、指导关系、阶段影像、装裱与专家意见 |
| `material_lot` | 纸、绢、颜料等材料批次 |
| `trial_sample` | 试验样张，成功与失败均留档 |
| `secret` | 传统诀窍，只登记保管人与授权范围 |
| `detection` | 检测结论及其引发的复核标记 |
| `collection_decision` | 入藏决定、身份变化与标签输出 |

## 事件目录

| 事件 | 挂靠聚合 | 必备字段 | 含义 |
| --- | --- | --- | --- |
| `REFERENCE_FROZEN` | reference_work | — | 冻结参照原作版本 |
| `SURVEY_RECORDED` | reference_work | — | 勘察资料归档 |
| `MATERIAL_LOT_REGISTERED` | material_lot | — | 材料批次登记 |
| `MATERIAL_TESTED` | material_lot | — | 材料试验结论，含不合格批次 |
| `TRIAL_SAMPLE_RECORDED` | trial_sample | `outcome`（success/failure/partial） | 试验样张登记，失败试验同样保留 |
| `STAGE_ATTESTED` | replica_project | — | 阶段影像与阶段确认 |
| `RESPONSIBILITY_ASSIGNED` | replica_project | `assignee`、`scope` | 多人接续或并行时的责任范围 |
| `MENTORSHIP_RECORDED` | replica_project | — | 指导关系登记 |
| `MOUNTING_RECORDED` | reference_work / replica_project | — | 装裱修复记录 |
| `EXPERT_OPINION_RECORDED` | replica_project / collection_decision | — | 专家意见 |
| `SECRET_REGISTERED` | secret | `custodian`、`authorization_scope` | 诀窍登记，内容不入库 |
| `DETECTION_RECORDED` | detection | — | 新检测结论 |
| `REVIEW_FLAGGED` | detection | `targets`（非空） | 标记需复核的既往说明 |
| `OBJECT_ACCESSIONED` | collection_decision | — | 入藏决定 |
| `IDENTITY_RECLASSIFIED` | collection_decision | `from_identity`、`to_identity` | 身份变化（如研究成果转为正式藏品后的重新认定） |
| `LABEL_ISSUED` | collection_decision | `identity`、`custody_level`、`permission` | 巡展借用等场景的标签输出 |
| `LABEL_REVISED` | collection_decision | — | 标签更正（以新记录接续） |

对象身份取值：`original`（原作）、`replica`（摹本）、`teaching_sample`（教学样张）。

## 约定

- 记录一经接收，标识、发生时间与版本不得原地改写；更正使用新的后继记录，同一聚合内版本单调递增。
- 多人接续或并行尝试不同材料时，各自的责任范围（`RESPONSIBILITY_ASSIGNED`）与失败试验（`TRIAL_SAMPLE_RECORDED`，`outcome=failure`）都必须留档。
- 诀窍事件只登记保管人和授权范围，不得包含诀窍内容字段（`content`、`technique_detail`）；普通研究者不能读取诀窍内容。
- 新检测结论通过 `REVIEW_FLAGGED` 指出需要复核的既往说明，但不倒改过去采用的认识，原记录保持不变。
- 标签（`LABEL_ISSUED`）必须与对象当前身份、保管级别和许可一致；身份变化以 `IDENTITY_RECLASSIFIED` 接续记录。
- 个人、机构及商业敏感信息仅向履行职责所需的调用方开放。

## 本地检查

```bash
python3 -m unittest discover -s tests
```
