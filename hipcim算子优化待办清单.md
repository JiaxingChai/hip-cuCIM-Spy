# hipcim 算子优化待办清单

> - **文档名称**：hipcim 算子优化待办清单
> - **生成来源**：cuCIM PR 集合（rapidsai/cucim，`archive/2026-11-07/cucim_prs.json`，`hipCIM_prs.json` 为空）
> - **业务场景**：空天算力｜DCU GPU 算子优化｜大 2D/3D 遥感图像｜海量分割目标｜极端各向异性尺寸
> - **状态枚举**：`[ ] 待办`｜`[🚧] 进行中`｜`[✅] 已完成`｜`[⚠️] 阻塞`
> - **使用说明**：
>   1. 人工维护：直接修改任务复选框状态（`[ ]` / `[🚧]` / `[✅]` / `[⚠️]`），并在每条任务的【备注】栏填写测试结果、benchmark 数据、遇到的问题、阻塞原因。
>   2. Agent 读取本文件时的行为规则：
>      - 解析全部任务状态，区分 待办 / 进行中 / 已完成 / 阻塞；
>      - 汇总：已完成的算子优化、当前阻塞任务及阻塞原因、剩余待办任务；
>      - 若存在阻塞任务，优先分析阻塞点并给出解决建议；
>      - 按剩余任务的依赖关系与复杂度自动生成下一阶段工作计划，**堆叠 PR 严格按依赖顺序排期**（本文件中以 `阶段 A/B/C` 标注依赖链）；
>      - 只输出**新的 markdown 片段**供追加，禁止覆盖原文档中已人工填写的备注与测试数据。
>   3. 任务编号前缀（H/M/L）与 PR 编号一一绑定，可跨版本追溯。
> - **文档版本**：v1（基线：cuCIM main @ 2026-11-07，含 #1199 前全部已合并 PR）

---

## 1. 【候选PR概览】

### 1.1 保留 PR（进入待办）

| PR | 标题 | 一句话核心内核改动 |
|---|---|---|
| #1087 | add large image support to `measure.label`（64-bit indexing） | connected-component label 内核索引/计数由 32 位改为按需 64 位，支持 >2^32 像素图像 |
| #843 | Region Properties Overhaul Part 1 | 单一 kernel 一次遍历全图批量计算所有 label 的 bbox / 像素数 / 边界像素数，替代 per-region 循环 |
| #844 | Region Properties Overhaul Part 2 | 批量 intensity 统计内核（mean/std/min/max），label 直方图归约替代逐区域裁剪 |
| #845 | Region Properties Overhaul Part 3 | 依赖 convex hull 的属性（area_convex/solidity/feret）GPU 预处理 + 凸包内像素判定内核 |
| #846 | Region Properties Overhaul Part 4 | 批量矩内核（moments / weighted moments / inertia tensor）单趟累加 |
| #847 | Region Properties Overhaul Part 5 | perimeter / crofton perimeter / euler_number 的批量内核与紧邻区域隔离策略 |
| #848 | Region Properties Overhaul Part 6 | `regionprops_table` 默认走批量内核路径（dispatch + extra_properties 兼容） |
| #849 | regionprops 非 CuPy 输入统一报错 | 显存/主机混合输入的显式校验，避免隐式 host 回退 |
| #1088 | `regionprops_table` 输出列顺序与格式 | 批量路径的列排布/dtype 与 scikit-image 对齐 |
| #1115 | Add `filters.rank` module | N-D rank filter：滑窗直方图（uint8 2D 快路）+ 逐元素归约通用路 |
| #1061 | morphology `h_maxima`/`local_maxima`，改进 `reconstruct` | `maximum_filter + ndi.label + 校验` 替代串行 flood-fill；`reconstruct` 改为 GPU 迭代重建 |
| #1060 | batch/multi-channel interpolation 优化 | `batch_axes` 检测 + last-axis 批量循环，避免对 channel 维做 4×4×4/8 邻域插值 |
| #1055 | vendored interpolation kernels 精度修复 | 修复应走 float32 却落入 float64 代码路径的问题（ND 插值核） |
| #1040 | `restoration.rolling_ball` | 灰度形态学背景估计 + 球/椭圆结构元素生成内核，附 downsample 降复杂度 |
| #839 | `label2rgb` 性能优化 | 自定义逐元素内核替代多次 map/索引 kernel，含 mode=avg 的 label 归约 |
| #809 | color distance kernel fusion | deltaE 系列多 kernel 融合为单趟 elementwise kernel |
| #782 | `peak_local_max` 性能修复 | min_distance=1 时跳过 `ensure_spacing`（CPU 回退），避免整图坐标回传 |
| #828 | `convex_hull_image` / `convex_hull_object` | GPU 预处理（边界点/去重/偏移）+ QHull + 凸包内像素填充内核 |
| #838 | 内存高效的最大成对距离（Feret） | 分块 pairwise distance，块内 GPU 归约，避免 O(N²) 显存 |
| #516 | transform 裁剪（clip）低效修复 | 复用已算得 (min,max)，避免重复整图归约 kernel |
| #485 | rank filter 去掉不必要的 footprint kernel | footprint 全 1 时跳过权重数组分配与读取 |
| #517 | 二值形态学省略 weights 数组 | 支持 shape tuple 结构元素，省一次整图向量加载 |
| #521 | 修复非均匀 footprint 的中值滤波 | rank 内核中非均匀 footprint 的取值/排序索引修正（#485 回归） |
| #540 | 2D 距离变换越界防护 | `_pba_2d`/`kernelColor` 负坐标访问修正，避免非法显存访问 |
| #482 | vendored `pad` 逐元素内核 | edge/symmetric/reflect/wrap 单 kernel 完成全轴 padding，去掉多 kernel 串行 |
| #813 | vendored ndimage 支持 `axes` | 过滤/形态学内核支持子集轴运算，避免整图 N-D 迭代 |
| #836 | 更新 vendored 二值形态学 | 上游修复（二值腐蚀/膨胀快路）合入 |
| #842 | 更新 vendored `binary_fill_holes` | 用户自定义 structure 也走快路 + dtype 输出处理 |
| #770 | Windows 关闭自定义 2D 可分离卷积核 | 说明该组自定义 separable kernel 的自动派发存在平台相关缺陷（DCU 侧需自检） |
| #967 | `reconstruction` 无符号输入崩溃修复 | 重建设内核前的 dtype 提升，避免 uint 溢出导致环 |
| #764 | chan_vese 常量改为 device scalar | fused kernel 参数化，避免 host 端 dtype 推断问题 |
| #856 | chan_vese fused kernel dtype 修复 | 融合核内 float scalar 精度一致化，保证输出 dtype |
| #1038 | 对齐 scikit-image 0.26 | 几何变换大重构 + `intensity_median`（缺批量内核，可补） |
| #1142 | stain 协方差中心化（CuPy CUB） | 均值归约前逐行平移，保持 float32 归约精度 |
| #1077 | heap overflow 修复 | C++/解码路径的边界与分配修复（涉及大图 ROI 安全性） |
| #488 | colocalization 度量 | manders / pearson 归约 kernel（含 fused kernel） |
| #577 | kernel fusion 失败回退路径验证 | 融合归约核不可用时的正确性兜底测试 |
| #727 | scikit-image 0.23 同步（part 1） | `intensity_std`、`expand_labels` spacing 等 |
| #728 | scikit-image 0.23 同步（part 2：morphology） | 边界 mode/cval、偶数尺寸 footprint 修复、footprint tuple 优化 |
| #1007 | nvImageCodec 批量 ROI 解码 | 单次 `DecoderDecode` 批量 ROI，摊薄 kernel launch 与分配开销（I/O 层） |
| #1028 | 异步 CUDA stream 批量解码 | 调度/等待分离 + 自定义 stream 透传，流水线化解码（I/O 层） |
| #1145 | cuslide2 GPU 常驻 tile cache | 双缓存（host/device），恢复 direct-to-device 解码路径（I/O 层） |
| #1034 | cuslide2 tile 级缓存 | ROI 拆 tile + 缓存查找/回填，命中即免解码（I/O 层） |

### 1.2 被过滤 PR 说明（分类汇总）

| 过滤原因 | 数量 | 说明 |
|---|---|---|
| CI / 构建流水线（runner、workflow、zizmor、sccache、telemetry） | 197 | 无算子代码改动 |
| Forward-merge（分支同步） | 135 | 纯合并提交 |
| conda / wheel / 依赖 / 版本 / CMake / CUDA 版本升级 | 93 | 打包与工具链 |
| 文档 / 品牌 / SECURITY / SPDX / 版权 | 84 | 仅文档与许可证 |
| Python 版本兼容（3.11~3.14 增删） | 10 | 夹具与元数据 |
| nanobind / pybind11 绑定迁移 | 3 | 绑定层，不含 kernel |
| CI 测试跳过 / 网络 429 / xfail | 2 | 测试稳定性 |
| 其他：无 GPU kernel 改动或单行低复杂度修复 | 342 | 纯 Python 胶水、单点 bug、测试夹具 |
| **合计过滤** | **866** | 全库 909 个 PR，保留 43 项 |

> 全量编号清单见【附录 A】，供回溯核对；如需重新筛选可执行 `tools/filtered.py`。

---

## 2. 【高优先级｜下周重点】

> 3 项，均为 kernel 级改动；堆叠 PR（#843–#848）已拆为阶段交付，禁止一次性整体移植。

### H1 大图连通域标记内核 64 位化（突破 2^32 像素上限）

- [ ] **H1 label 内核 64-bit 索引与计数改造** `关联PR: #1087`
  - **任务简述**：
    - 阶段 A：改造 `measure/_label_kernels.py` 的局部标记（shared-memory union-find）+ 全局等价合并（merge/relabel）两个 kernel，索引与临时计数改为“按需 64 位”（图像总像素 > 2^31 或 max_label 溢出风险时启用 64 位模板实例化，覆盖 cuCIM 上游“necessary 时启用”的策略）。
    - 阶段 B：`measure.label` 的 grayscale 模式（邻接仅当灰度值相等才连通）同步支持 64 位，`background`/`connectivity` 参数与 scikit-image 语义对齐。
    - 阶段 C：输出 dtype 自动选择（`int32` 不溢出则保持 `int32`，否则 `int64`），并在 `regionprops`/`label2rgb` 下游保证不再假设 `int32`。
  - **核心算法 & GPU 算子难点**：
    - 局部标记用 LDS 内 union-find + `atomicMin` 传播根标签，64 位化后每次 LDS 访问字节数翻倍，bank 冲突与 LDS 容量压力显著上升；
    - 全局 merge 需对等价对做排序/去重（可用 hipCUB `DeviceRadixSort` 或自写桶排），再跑 pointer-jumping 压缩；
    - 大图必须分块（tile）处理并保留 halo，halo 处跨块连通性通过全局等价表合并，块内计数用 64 位原子累加。
  - **空天算力场景收益**：
    - 遥感大幅面镶嵌图（如 100000×100000 = 10^10 像素）此前直接 int32 溢出/显存越界，是“超大 2D 图像”场景的硬门禁；
    - 海量分割目标（10^6~10^7 个连通域）时 label 值是后续 regionprops/label2rgb 的索引基座，64 位化打通整条批处理链路。
  - **交付 & 验证指标**：
    - 正确性：2D/3D、4/8 连通、grayscale 模式，与 scikit-image `label` 逐像素比对；构造 >2^31 像素的合成图（分块写入）验证无溢出、label 计数一致；与 cuCIM 上游同 PR 输出对齐。
    - 性能：`(100000, 100000) uint8`（稀疏前景/密集前景两档）、`(8192, 8192, 8192)` 3D 小规模代表、极端各向异性 `(1, 4096, 2000000)`；对比 hipcim 现实现（int32 版）与 cuCIM 32 位路径，记录 kernel 时间、显存峰值、relabel 迭代次数。
  - **HIP/DCU 移植风险**：
    - wavefront 64（CUDA warpSize=32 假设）导致 ballot mask 语义差异：`__ballot` 返回 64 位掩码，`__match_any_sync` 在部分 gfx 上不可用或性能差，需准备 LDS 哈希分组回退；
    - `uint64` 原子操作：`atomicAdd(unsigned long long*)`、`atomicMin/atomicMax` 对 64 位支持依架构而异，必要时用 CAS 循环实现，注意 CAS 重试风暴；
    - LDS bank：AMD LDS 32 bank×4B，64 位 union-find 数组易触发 2-way/4-way 冲突，建议 32 位 pair 拆分存储；
    - 大图分块尺寸与 grid 维度上限（HIP grid 维度限制同样为 2^31-1 量级，需用 1D/2D 展平 + 64 位线性索引）。
  - **备注**：`【待填写：进度、测试数据、问题】`
    - 初始核查（2026-11-08）：`hipcim/python/cucim/src/cucim/skimage/measure/_label_kernels.py` 未出现 64 位索引/计数代码，视为未迁移。

### H2 Region Properties 批量内核栈（#843–#848，六阶段顺序交付）

- [ ] **H2-A 批量基础属性内核** `关联PR: #843`
  - **任务简述**：把 `_regionprops.py` 的“逐区域裁剪 + 逐区域计算”改为单 kernel 全图扫描：一次遍历同时产出 `bbox`、`num_pixels`、`num_pixels_filled`（洞填充）、`num_perimeter_pixels`、`num_boundary_pixels`；导出派生属性（area/area_bbox/extent/等价直径等）。对应 hipcim 已有 `_regionprops_gpu_basic_kernels.py` 的复核与补齐。
  - **核心算法 & GPU 算子难点**：`(max_label, 2*ndim)` 归约表用 `atomicMin/atomicMax` 维护 bbox（可把 2D 坐标打包进 64 位整数单次原子）；`num_pixels` 用直方图原子累加；洞填充需 2D 泛洪（`binary_fill_holes` 快路）+ 二次统计；要避免 `atomicAdd` 热点造成的 label 局部冲突（可用共享内存直方图 + 冲突时全局原子回退）。
  - **空天算力场景收益**：海量目标（10^5~10^6 个）时性能与区域数量近似无关，解决旧实现随区域数线性劣化的问题。
  - **交付 & 验证指标**：正确性对齐 scikit-image `regionprops_table`（含 bool/uint8/int32 label、2D/3D、含洞环形目标）；性能基准 `(7680,4320)` 区域数 4→16384、`(384,384,384)` 3D 区域数 8→1728，记录加速比。
  - **HIP/DCU移植风险**：`atomicMin/Max` 64 位打包坐标在部分架构缺失；共享内存直方图 bank 冲突（label 连续递增时可按 `(label & (NBINKS-1))` 重排）；`max_label` 巨大而实际区域稀疏时需稠密→稀疏索引映射。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **H2-B 批量强度统计内核** `关联PR: #844`
  - **任务简述**：`intensity_mean/std/min/max` 批量内核：以 label 为桶做 sum / sum² / min / max 归约，再在 host/小 kernel 上折算 std。
  - **核心算法 & GPU 算子难点**：float32 累加精度（大图 sum² 抵消）——分块内先做 wave 级规约再原子累加，或 float64 累加 + 量化误差评估；min/max 需处理 label=0 背景剔除；多属性一次遍历（multi-intensity）。
  - **空天算力场景收益**：遥感反演常需对每类地物做统计，热点图（大图、类别数中等）收益最大。
  - **交付 & 验证指标**：与 scikit-image 比对 mean/std（rtol 1e-5 量级，需记录 dtype 差异）、min/max 严格相等；基准 `(7680,4320)` 与 `(8192,8192)`。
  - **HIP/DCU移植风险**：`cupy.mean` 在启用 CUB 时数值路径变化（见 #1142 同类问题），归约顺序不同会放大 float32 误差；wave64 下 `__shfl_down` 需 6 级而非 5 级。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **H2-C 凸包相关属性内核** `关联PR: #845, #828, #838`
  - **任务简述**：先落地 `convex_hull_image`（GPU 预处理 + QHull + 凸包内像素判定内核）与分块最大成对距离（Feret），再实现 `area_convex`/`solidity`/`feret_diameter_max` 批量接口；明确“区域数多时退化为 per-region 调用”的策略与阈值。
  - **核心算法 & GPU 算子难点**：边界点提取（邻域差 + 掩码压缩）、点集去重与偏移、凸包内判定（凸多边形逐边半平面测试向量化，或按扫描线并行填充）；QHull 为 host 串行，需 GPU/CPU 重叠（异步拷贝 + 多流）。
  - **空天算力场景收益**：遥感目标（舰船、飞机、地块）形状因子统计；大而少的目标收益最高，避免 CPU 端 QHull 前的 O(N log N) 与后处理像素扫描。
  - **交付 & 验证指标**：与 scikit-image `convex_hull_image`/`area_convex`/`solidity`/`feret_diameter_max` 比对（含高度凹形目标、`offset_coords` 两档）；性能基准 `(64..8192)²`、`(384)³`，记录 GPU32/GPU64 两档与 CPU 对比。
  - **HIP/DCU移植风险**：host 回退比例高导致 GPU 空转；`hipCUB` 无 cuVS/pylibraft 等价库，pairwise 距离需自写分块 kernel；`atomicMax` 于 float 需 CAS 位模式技巧。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **H2-D 批量矩内核** `关联PR: #846`
  - **任务简述**：`moments` / `moments_weighted` 单趟累加内核（最高阶按需），派生 centroid、central/normalized/Hu moments、inertia tensor 及特征值/特征向量、`axis_lengths`。
  - **核心算法 & GPU 算子难点**：高阶矩（p+q ≤ 3 及以上）需 `(label, p, q)` 多维累加表，显存与原子压力大 → 用 LDS 分块累加 + 每块刷回；weighted 版同时读 intensity 图，双图访问的合并访存与 L2 复用是关键；特征分解在 host/小批 kernel 完成。
  - **空天算力场景收益**：目标方向性/长宽比分析（机场跑道、桥梁、舰船）依赖二阶矩；批量实现使 10^5 目标统计可行。
  - **交付 & 验证指标**：与 scikit-image 各矩属性比对（含 3D、weighted）；基准 multi-moment 组合在 `(8192,8192)`/`(512)³` 的耗时。
  - **HIP/DCU移植风险**：float64 原子在消费级/部分 DCU 上性能极差，需 float32+LDS 顺序累加；寄存器压力（高阶矩展开）导致 occupancy 骤降，需 `__launch_bounds__` 调参。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **H2-E 周长与欧拉数内核** `关联PR: #847`
  - **任务简述**：`perimeter`、`perimeter_crofton`、`euler_number` 批量内核；实现 `robust_perimeter=True` 时对紧邻区域做隔离计算的回退路径与开关。
  - **核心算法 & GPU 算子难点**：Crofton 周长需对多个方向做计数（方向数×像素），可用“每线程多方向”减少访存；euler number 需 2×2×2 局部位模式查表 + 全局累加；紧邻区域隔离意味着必须能从 label 图局部重建单区域掩码，cache 友好性差。
  - **空天算力场景收益**：地物边界复杂度、矢量化简前的周长估计；紧邻目标（密集建筑、细胞）场景下缺此回退会得到错误周长。
  - **交付 & 验证指标**：与 scikit-image 比对（含紧邻区域、单像素目标、含洞目标、3D）；性能基准同 H2-A，并单列 `robust_perimeter=True/False` 两档。
  - **HIP/DCU移植风险**：Crofton 常量表与方向实现需与 scikit-image 完全一致（否则真值比对失败）；查表用 constant memory 在 HIP 上退化为 global 读取，需评估。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **H2-F `regionprops_table` 派发与兼容** `关联PR: #848, #1088, #849`
  - **任务简述**：`regionprops_table`/`regionprops_dict` 默认走批量路径，保留 `batch_processing=False` 旧路；支持 `extra_properties` 回调（按区域循环）；输出列顺序/格式与 scikit-image 0.26 对齐。
  - **核心算法 & GPU 算子难点**：无新内核，重点在属性依赖图（避免重复计算）与显存预算（稠密归约表 vs 区域数）；`intensity_median`（#1038 新增）需要补批量内核或按区域回退。
  - **空天算力场景收益**：业务侧零改动即获得数量级加速；避免上层 Python 循环。
  - **交付 & 验证指标**：全属性组合回归（2D/3D、含/不含 intensity_image），列名与 dtype 与 scikit-image 一致；`extra_properties` 行为一致。
  - **HIP/DCU移植风险**：无 kernel 风险；注意属性缓存导致显存峰值叠加，需提供按属性分组的显存上限保护。
  - **备注**：`【待填写：进度、测试数据、问题】`

### H3 批维/多通道插值内核优化（#1055 → #1060 顺序）

- [ ] **H3 插值内核 batch_axes 检测与多通道向量化** `关联PR: #1055, #1060`
  - **任务简述**：
    - 阶段 A（#1055）：修正 vendored ndimage 插值的 dtype 派发，确保 float32 输入不再落入 float64 代码路径；
    - 阶段 B（#1060）：在 `affine_transform` / `rotate` / `shift` / `zoom` / `map_coordinates` 中引入 `batch_axes` 检测，只对真正需要插值的轴构建邻域模板；spline 预滤波仅沿被滤波轴进行；
    - 阶段 C：`loop_batch_axis` —— 当最后一维属于 batch 轴时，让单线程循环处理 N 个 batch/channel 元素（RGB/RGBA 常见场景）；
    - 阶段 D：`transform.warp` 将 `axes`/batch 推导与内核对齐，保证遥感 (H,W,C) 与 (N,H,W) 堆栈同 kernel 完成。
  - **核心算法 & GPU 算子难点**：
    - 通用 N-D 插值核的循环边界（axes 组合、order 0–5、mode 集合）导致模板实例爆炸，需模板化 + 编译期裁减；
    - 邻域模板大小从 4^d 降为 4^(d-|batch|)，寄存器/LDS 使用量与合并访存策略随之改变；
    - spline 预滤波是递推（IIR），只沿滤波轴做可大幅降耗，但需处理轴顺序与 stride 非连续；
    - `loop_batch_axis` 会改变每线程工作量，需重新平衡 block 尺寸（避免明显的 load imbalance）。
  - **空天算力场景收益**：
    - 多光谱/高光谱遥感 (H,W,bands) 与多时相堆栈 (T,H,W) 的几何配准/重采样是主流程；此前把通道维当空间维插值，白做 (order+1)^C 倍计算；
    - 大 2D 遥感图旋转/重采样（如 40000×40000×4 uint8）时，带宽与计算双降；
    - 极端各向异性尺寸（如 1×10^6×3 条带图）下 batch 轴识别收益最大。
  - **交付 & 验证指标**：
    - 正确性：对 `order ∈ {0,1,2,3,5}` × `mode ∈ {constant,nearest,reflect,wrap,mirror}` 全组合，与 `scipy.ndimage`/`cupyx.scipy.ndimage` 逐元素比对；float32 路径断言输出 dtype；RGB/RGBA 单 kernel 结果与逐通道循环完全一致（bitwise 或 1e-6）。
    - 性能：`(4096,4096,3) uint8 rotate`、`(32,2048,2048) float32 rotate`、`(20000,20000,4) uint8 warp`、`(1,1000000,3)`；对比 hipcim 现路径与 cuCIM 优化后路径，记录 kernel 时间与有效带宽。
  - **HIP/DCU移植风险**：
    - 模板实例数量爆炸导致编译时间/host 端 code object 体积膨胀，需控制实例化组合（用运行时 order 分支 + 有限模板）；
    - AMD 无 texture 单元，`linear` 插值需自算权重，合并访存（相邻线程访问邻近像素）在 stride 非 1 的 batch 轴上易失配；
    - LDS 在 64 线程 wave 下 bank 冲突更明显，尤其 `loop_batch_axis` 使同一 wave 内线程访问同一像素多通道；
    - `hipCUB` 不参与此路径，但 `cp.ascontiguousarray` 的隐式拷贝会吞掉收益，需在 Python 层做 layout 预检。
  - **备注**：`【待填写：进度、测试数据、问题】`
    - 初始核查（2026-11-08）：`hipcim/python/cucim/src/cucim/skimage/_vendored/_ndimage_interpolation.py` 中 `batch` 关键字命中数为 0，判定未迁移。

---

## 3. 【中优先级｜后续迭代】

- [ ] **M1 `filters.rank` 模块（滑窗直方图 + 通用归约双后端）** `关联PR: #1115, #485, #521`
  - **任务简述**：阶段 A 通用逐元素后端（N-D、任意 footprint、mask/shift、原生整型与浮点 dtype）；阶段 B uint8 2D 滑窗直方图后端（仅全填充奇数矩形 footprint），实现 median/mean/min/max/entropy/percentile/sum/uniform 等；阶段 C `filters.median(behavior='rank')` 代理。
  - **核心算法 & GPU 算子难点**：滑窗直方图需按行滑动复用（删除/加入列），LDS 中 256 bin 直方图 + 前缀和求第 k 大；边界 reflect 扩展 vs scikit-image 裁切差异需显式对齐；直方图冲突用 wave 内串行化规避。
  - **空天算力场景收益**：遥感去噪、形态学排序滤波、海量小目标预处理；大窗口（15×15 以上）相比逐元素快路显著领先。
  - **交付 & 验证指标**：与 scikit-image `filters.rank` 参考结果比对（2D 全 filter + 3D 通用 filter）；基准 `(8192,8192) uint8`、`(33792,33792)` 分块、footprint 3→31。
  - **HIP/DCU移植风险**：LDS 容量（若需 64K bin 或 float 直方图）超出 64KB 限制；`atomicAdd` 到 LDS 在 wave64 下冲突倍增；`warpSize` 假设影响 bin 分片。
  - **备注**：`【待填写：进度、测试数据、问题】`；初始核查：hipcim 仅有 `_median_hist.py`（中值直方图），无 `filters/rank` 包。

- [ ] **M2 形态学极值/重建 GPU 化（`local_maxima`/`h_maxima`/`reconstruct`）** `关联PR: #1061, #967`
  - **任务简述**：`local_maxima/local_minima` 用 `maximum_filter`（批量）+ `ndi.label`（高原连通域）+ 校验 三阶段替代 CPU 串行 flood-fill；`reconstruct` 改为 GPU 迭代（形态学重建按 `min(rec, dilate(rec))` 迭代至收敛），保留 CPU 回退开关；uint 输入先提升 dtype。
  - **核心算法 & GPU 算子难点**：迭代重建收敛轮数不确定（最坏 O(直径)），需以“活动集/前沿”收敛判定减少轮次；`maximum_filter` 大 footprint 需 separable/van Herk 分解；高原（plateau）判定需连通域 label + 邻域极值双校验避免伪极值。
  - **空天算力场景收益**：DEM/高程图的峰谷提取、云检测、遥感背景估计前置步骤；百万级候选峰值的批量筛选。
  - **交付 & 验证指标**：与 scikit-image 逐元素比对（含 allow_borders、connectivity=1/2、uint8/float32/float64）；基准 `(512,512)`→`(16384,16384)`，记录迭代轮数与总耗时；病态输入（细长梯度图）需给出性能回退告警。
  - **HIP/DCU移植风险**：迭代重建设在长条形/通道状图像上轮数爆炸（比 CPU 慢）；`maximum_filter` 的 separable 自定义核在部分平台有问题（参见 #770）；`ndi.label` 依赖 H1 的 64 位改造。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **M3 `restoration.rolling_ball` 背景估计** `关联PR: #1040`
  - **任务简述**：复用灰度形态学内核实现 `rolling_ball`，新增球/椭圆结构元素生成内核，并实现非 scikit-image 的 `downsample` 选项（结构元素幅值与尺寸同步缩放）。
  - **核心算法 & GPU 算子难点**：非平坦（非 0/1）大结构元素无法分解为 3×3 序列，计算量随半径平方/立方增长；需分块 + LDS 缓存结构元素、按半径自适应选择“逐元素”或“位移叠加（van Herk 变体）”。
  - **空天算力场景收益**：大幅面遥感影像光照不均/云影校正（背景减除），1920×1080 半径 40 时上游实测 ~217×，超大图收益更大。
  - **交付 & 验证指标**：与 scikit-image `rolling_ball` 比对（uint8/float32、不同 radius、nansafe 未支持需显式报错）；基准 `(1920,1080)`、`(20000,20000)` radius 5/10/20/40 与 downsample=2/4。
  - **HIP/DCU移植风险**：大结构元素导致每线程上千次比较，寄存器/指令缓存压力；LDS 存放结构元素时尺寸超限需回退 global（L2 命中依赖）；
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **M4 `label2rgb` 逐元素内核化** `关联PR: #839`
  - **任务简述**：用自定义 elementwise kernel 替代多次 map/索引/合成 kernel，覆盖 `mode ∈ {overlay, avg, bg_label}`、`image` 存在与否、`saturation`/`kind` 分支；`avg` 模式改 label 直方图归约。
  - **核心算法 & GPU 算子难点**：颜色表（colormap）查找 + HSV/RGB 转换 + alpha 混合一次完成；`avg` 需 label→颜色累加（原子或分块 hist）。
  - **空天算力场景收益**：海量分割目标（10^6 标签）可视化/落盘，避免显存多次往返。
  - **交付 & 验证指标**：与 scikit-image 比对（全 mode/kind 组合）；基准 `(512,512)`、`(3840,2160)`、`(192,192,192)`，目标较现实现 ≥2×。
  - **HIP/DCU移植风险**：colormap 表走 constant memory 在 HIP 上退化为 global；uint8 输出饱和运算需与 numpy 语义一致。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **M5 color distance 内核融合** `关联PR: #809`
  - **任务简述**：`deltaE_cie76/ciede94/ciede2000/cmc` 全部融合为单趟 elementwise kernel，中间量（LCh、色相角、权重）全程寄存器级。
  - **核心算法 & GPU 算子难点**：ciede2000 含大量分支与三角函数（`atan2`/`sqrt`/`pow`），SIMD 分支发散严重；建议无分支化形式（用 `select`/条件表达式）与快速数学近似并评估精度。
  - **空天算力场景收益**：多光谱变化检测、地物分类后处理；大图（3840×2160）上游实测 130×~250×。
  - **交付 & 验证指标**：与 scikit-image 比对（rtol 1e-5）；基准 `(512,512,3)`、`(3840,2160,3)`。
  - **HIP/DCU移植风险**：`powf`/`atan2f` 精度与吞吐差异（ROCm 上 `--use_fast_math` 影响），需逐函数校准；寄存器溢出导致 spill。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **M6 二值形态学/rank 滤波核开销消除（footprint/weights/tuple 结构元素）** `关联PR: #485, #517, #521, #728, #836, #842`
  - **任务简述**：footprint 全 1 时跳过权重分配与读取；支持 `structure=(h,w)`/`(d,h,w)` tuple 直通内核；修正非均匀 footprint 下 rank 取值索引；二值腐蚀/膨胀/填洞快路与 `mode`/`cval` 边界语义对齐 scikit-image 0.23+。
  - **核心算法 & GPU 算子难点**：内核需两个特化实例（uniform/非均匀）避免运行时分支；tuple 结构元素要求半径计算与边界处理正确；偶数尺寸 footprint 的非对称处理。
  - **空天算力场景收益**：小结构元素（3×3/5×5）在海量目标预处理中占主导，上游实测约 2× 提升。
  - **交付 & 验证指标**：与 scikit-image 比对（含偶数 footprint、非对称 structure、各 mode/cval）；基准 3×3/5×5/3×3×3 与 15×15。
  - **HIP/DCU移植风险**：模板实例翻倍导致编译体积；`__constant__` 边界值传递方式差异。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **M7 transform 裁剪路径与 `peak_local_max` 回退开销** `关联PR: #516, #782, #1055`
  - **任务简述**：`_clip_warp_output` 复用已算得的 (min,max) 避免整图重复归约，`clip` 默认值按 order 自适应；`peak_local_max` 在 `min_distance<=1` 时跳过 `ensure_spacing`（避免整图坐标回传 CPU）。
  - **核心算法 & GPU 算子难点**：减少全图归约 kernel 次数属“显存往返消除”类优化；`ensure_spacing` 若必须运行，应改为 GPU 端网格/KD 结构而非 CPU 回退。
  - **空天算力场景收益**：大图 resize/rotate 流水线（重采样 + 裁剪）省一次完整读写；blob/角点检测在大图上避免 O(N) 坐标回传。
  - **交付 & 验证指标**：与 scikit-image 比对 clip 语义（order 0/1 与高阶、带 cval）；性能基准 `(20000,20000) uint8 resize`、peak_local_max 在 10^5 峰值图。
  - **HIP/DCU移植风险**：默认值变更属 API 破坏性调整，需在 hipcim 侧评估兼容；归约融合后精度（float32 min/max）无影响。
  - **备注**：`【待填写：进度、测试数据、问题】`

- [ ] **M8 大图 ROI 解码与 tile cache 的 GPU 路径** `关联PR: #1007, #1028, #1034, #1145, #1077, #1143`
  - **任务简述**：属 I/O/解码层，但与“大图 + 海量 tile”吞吐直接相关，作为中优先级储备：批量 ROI 单次提交、调度/等待分离 + 自定义 stream 流水线、host/device 双 tile cache 恢复 direct-to-device 解码、堆溢出与 ROI 越界防护。
  - **核心算法 & GPU 算子难点**：非自定义算子，重点是 stream 流水线、异步内存生命周期（RAII/pimpl）、缓存淘汰与显存预算；DCU 侧需评估替代 nvJPEG/nvImageCodec 的解码栈（如 hipJPEG/自研）能力边界。
  - **空天算力场景收益**：遥感瓦片服务/训练样本生成（千万级 tile）时解码与拷贝重叠。
  - **交付 & 验证指标**：吞吐（tile/s）、端到端时延、cache 命中率；GPU 输出路径在 cache 开启后不得慢于关闭（上游已定位的反模式）。
  - **HIP/DCU移植风险**：nvImageCodec 为 NVIDIA 专有，DCU 上无对等实现，需替换解码后端并保持 batch/stream 抽象；`cudaMalloc` 语义差异。
  - **备注**：`【待填写：进度、测试数据、问题】`

---

## 4. 【低优先级｜调研学习（仅研读，暂不开发）】

- [ ] **L1 vendored `pad` 逐元素内核** `关联PR: #482`
  - **研读点**：edge/symmetric/reflect/wrap 的坐标映射如何在一趟 kernel 内完成全轴 padding；host 侧 kernel launch 开销对比（小图 >5×，4K 图约 10%）。
  - **收益预估**：chan_vese 等内部多次 pad 的算法整体 ~25% 降耗；对 hipcim 属“顺手优化”，优先度低于内核主体改造。
  - **备注**：`【待填写：调研结论、是否值得移植】`

- [ ] **L2 2D 距离变换越界与 PBA 内核** `关联PR: #540`
  - **研读点**：`_pba_2d` 的 `kernelColor` 负坐标访问根因（边界扩展缺失/索引 clamp 方向），以及 parcel-based 精确欧氏距离变换的分块传播策略。
  - **收益预估**：大图距离变换（水域/道路宽度分析）稳定性；防御性修复成本低。
  - **备注**：`【待填写：调研结论】`

- [ ] **L3 chan_vese fused kernel 标量/dtype 处理** `关联PR: #764, #856, #1142`
  - **研读点**：CuPy fused kernel 的常量传递（host scalar vs device scalar）与 dtype 提升规则；float32 归约数值稳健性技巧（逐行平移后再求均值）。
  - **收益预估**：分割算法在 DCU/CuPy 版本升级下的稳定性，避免静默精度退化。
  - **备注**：`【待填写：调研结论】`

- [ ] **L4 vendored ndimage `axes` 支持与 separable 卷积核平台差异** `关联PR: #813, #770`
  - **研读点**：子集轴运算的内核轴映射与 stride 处理；自定义 2D 可分离卷积在非 CUDA 平台的失败模式（对 DCU 移植是直接警示）。
  - **收益预估**：为 hipcim 内核在 AMD 后端上的正确性排查提供参照。
  - **备注**：`【待填写：调研结论】`

- [ ] **L5 colocalization 归约内核** `关联PR: #488, #577, #578`
  - **研读点**：manders/pearson 的 fused kernel 写法与 mask 处理；kernel fusion 失败时的回退策略。
  - **收益预估**：多通道遥感相关性/变化检测统计，收益中等，暂不排期。
  - **备注**：`【待填写：调研结论】`

- [ ] **L6 scikit-image 0.23/0.26 语义同步清单** `关联PR: #727, #728, #1038, #1088, #849`
  - **研读点**：morphology 边界语义（mode/cval）、偶数 footprint 修复、regionprops 输出格式、`intensity_median` 待补批量内核；作为 H2/M2 的正确性基线参考。
  - **备注**：`【待填写：调研结论】`

---

## 5. 【历史记录区（预留）】

> 完成任务后在此追加版本记录（日期 / 任务编号 / 关联 PR / 结论 / 性能数据）。Agent 读取时会解析本节。

| 日期 | 任务编号 | 关联 PR | 状态 | 结论 / 性能数据 |
|---|---|---|---|---|
| 2026-11-08 | — | — | 基线建立 | 依据 cuCIM main @ 2026-11-07 的 909 个 PR 完成筛选，保留 43 项、过滤 866 项 |

---

## 附录 A　被过滤 PR 全量编号

**A1 CI / 构建流水线（197）**：
1, 7, 21, 28, 31, 39, 40, 42, 45, 46, 50, 51, 52, 53, 63, 70, 74, 76, 77, 78, 80, 81, 83, 88, 111, 115, 117, 118, 154, 155, 157, 159, 160, 161, 166, 167, 169, 173, 174, 178, 179, 180, 185, 198, 200, 201, 202, 204, 206, 211, 215, 217, 236, 238, 239, 240, 242, 245, 250, 253, 254, 257, 261, 281, 282, 285, 287, 288, 298, 299, 300, 301, 304, 306, 344, 345, 347, 348, 351, 358, 361, 366, 368, 369, 371, 373, 376, 377, 380, 381, 384, 390, 391, 403, 414, 416, 437, 438, 439, 440, 442, 444, 445, 447, 448, 449, 450, 453, 456, 457, 458, 459, 460, 465, 467, 468, 471, 501, 505, 510, 511, 515, 538, 545, 550, 551, 576, 613, 614, 619, 666, 675, 676, 680, 690, 702, 715, 739, 741, 749, 760, 772, 780, 791, 792, 793, 795, 797, 798, 803, 814, 817, 818, 822, 824, 826, 833, 835, 868, 870, 879, 881, 896, 897, 903, 925, 946, 959, 979, 986, 1003, 1022, 1023, 1024, 1032, 1052, 1078, 1081, 1091, 1098, 1103, 1113, 1116, 1119, 1131, 1132, 1133, 1140, 1141, 1160, 1161, 1172, 1178, 1181, 1194, 1199, 1200

**A2 Forward-merge（135）**：
57, 493, 495, 496, 498, 499, 500, 502, 512, 532, 533, 534, 537, 543, 554, 565, 566, 568, 571, 583, 588, 589, 591, 594, 597, 600, 602, 604, 612, 633, 636, 646, 649, 652, 658, 678, 679, 681, 684, 687, 688, 691, 697, 701, 718, 720, 723, 737, 752, 758, 783, 784, 787, 790, 802, 804, 816, 819, 821, 825, 832, 857, 860, 861, 862, 863, 866, 875, 876, 878, 880, 882, 885, 888, 909, 910, 911, 913, 916, 924, 940, 942, 943, 948, 950, 951, 953, 955, 956, 972, 973, 981, 982, 984, 985, 987, 988, 993, 994, 1008, 1010, 1019, 1021, 1048, 1050, 1053, 1057, 1059, 1063, 1067, 1068, 1070, 1072, 1086, 1089, 1092, 1095, 1097, 1100, 1101, 1121, 1123, 1124, 1125, 1126, 1129, 1155, 1162, 1164, 1165, 1167, 1168, 1171, 1174, 1175

**A3 打包 / 依赖 / 版本（93）**：
6, 22, 36, 41, 58, 69, 84, 164, 175, 205, 232, 268, 409, 480, 497, 522, 524, 525, 557, 558, 607, 610, 634, 638, 639, 643, 644, 650, 654, 665, 671, 672, 682, 683, 699, 716, 719, 722, 743, 745, 747, 751, 753, 757, 765, 774, 776, 801, 811, 815, 820, 834, 841, 854, 858, 864, 867, 877, 887, 889, 894, 917, 923, 926, 930, 934, 941, 961, 977, 989, 995, 999, 1000, 1020, 1026, 1027, 1054, 1056, 1058, 1080, 1083, 1085, 1099, 1102, 1104, 1114, 1118, 1130, 1147, 1148, 1176, 1188, 1193

**A4 文档 / 品牌 / 许可证（84）**：
4, 5, 8, 15, 30, 66, 79, 87, 127, 131, 132, 138, 142, 147, 182, 218, 220, 226, 227, 249, 275, 289, 311, 314, 315, 356, 360, 367, 383, 394, 396, 404, 415, 452, 475, 481, 552, 553, 560, 567, 570, 587, 605, 615, 616, 617, 622, 623, 630, 631, 632, 648, 653, 667, 668, 670, 695, 714, 724, 725, 726, 733, 734, 738, 785, 786, 806, 823, 830, 874, 898, 914, 927, 960, 1082, 1093, 1112, 1135, 1136, 1139, 1156, 1170, 1179, 1203

**A5 Python 版本兼容（10）**：
704, 773, 873, 1016, 1033, 1046, 1049, 1062, 1177, 1202

**A6 绑定层迁移（3）**：
519, 618, 1152

**A7 CI 测试跳过 / 网络（2）**：
1138, 1190

**A8 其他：无 GPU kernel 改动或单行低复杂度修复（342）**：
9, 11, 12, 13, 14, 18, 19, 20, 26, 27, 29, 32, 37, 43, 47, 48, 54, 55, 56, 59, 62, 65, 72, 73, 75, 82, 85, 95, 100, 106, 107, 108, 110, 120, 121, 124, 125, 128, 129, 141, 144, 145, 148, 150, 153, 156, 158, 165, 171, 172, 176, 177, 183, 186, 188, 189, 190, 191, 195, 196, 197, 203, 207, 208, 212, 214, 216, 229, 231, 234, 246, 248, 252, 258, 260, 267, 271, 272, 273, 274, 276, 278, 280, 284, 286, 290, 291, 293, 294, 295, 297, 302, 307, 308, 310, 312, 316, 317, 318, 322, 323, 324, 327, 328, 338, 339, 340, 341, 342, 343, 349, 355, 357, 359, 362, 365, 374, 378, 385, 386, 388, 393, 399, 401, 406, 407, 411, 413, 418, 420, 421, 422, 423, 424, 425, 426, 429, 432, 433, 434, 443, 451, 455, 461, 464, 472, 474, 476, 486, 491, 492, 494, 503, 506, 507, 508, 509, 528, 535, 536, 541, 542, 546, 547, 548, 549, 555, 556, 563, 564, 569, 572, 573, 574, 575, 578, 579, 580, 590, 593, 596, 599, 601, 603, 606, 609, 611, 620, 621, 624, 628, 635, 640, 642, 647, 651, 657, 669, 673, 674, 685, 689, 692, 693, 694, 705, 708, 711, 712, 713, 717, 721, 731, 735, 736, 740, 744, 746, 754, 756, 759, 761, 762, 766, 769, 777, 781, 788, 799, 805, 808, 812, 827, 831, 837, 840, 851, 852, 865, 883, 886, 890, 891, 893, 901, 902, 905, 906, 907, 908, 915, 919, 920, 921, 922, 931, 935, 936, 939, 944, 945, 947, 949, 952, 954, 957, 958, 962, 963, 965, 966, 968, 969, 970, 971, 975, 976, 978, 980, 983, 990, 991, 992, 996, 997, 998, 1001, 1002, 1004, 1005, 1006, 1009, 1015, 1031, 1035, 1036, 1037, 1041, 1042, 1047, 1071, 1075, 1079, 1084, 1096, 1105, 1106, 1107, 1108, 1109, 1110, 1111, 1117, 1120, 1122, 1127, 1143, 1144, 1146, 1149, 1150, 1153, 1154, 1158, 1169, 1173, 1182, 1183, 1184, 1185, 1186, 1187, 1196, 1197, 1198, 1201, 1205, 1206, 1207, 1208, 1209, 1210
