# .mphbin 二进制格式与解数据段（E-028 硬骨头战报）

## 协议层（Java 反编译 BinaryManager/BinaryType，全解）
- **段命名规则**：`<binarytype小写><N>.mphbin`（solutionblock1…/xmesh1/solutionstatic1/mesh2/geometry6/geommanager1…）
- **BinaryType 枚举 17 种**：SOLUTION/SOLUTIONBLOCK(参数步数据)/SOLUTIONSTATIC/XMESH(扩展网格=DOF布局)/XMESHPART/MESH/GEOMETRY/GEOMMANAGER/POSTDATA/INTERPOLATIONMATRIX/FUNCTIONDATA/VIEWFACTORDATA/MESHIMPORTASSOC/CGHANDLER/DNNDATA/Code
- BinaryManager（nativemph，2833 行）：段生命周期/缓存/重标记/zip 管理；序列化由 native（FlNativeSerializable）执行

## 头部结构（解码确认）
`[大端u32长度+ASCII令牌]` 序列：`SOLUTION:15[0]` / `SolutionBlock` / `Geom2` / `Mesh` / `GEOMMANAGER:1[0]` —— 类名:版本[子版本] 格式；头部区约 <1MB，之后为数据区

## 解数据布局（关键发现）
- **实测布局**（amp20000 已解 1.8GB）：solutionblock×113 块=1.77GB（**每时间步一块**），xmesh 13MB，solutionstatic 7MB，其余 <3MB
- **数值编码确证**：`f8e504d6` = **magic/块类型标记**；其后是**大端 float64 数据流**（shift=4 对齐起连续合理值：4.055e4、1.372e4、6713、-0.30（过电位量级!）、1.659e4、1.311e5×4…）
- 解向量按 (场, 自由度) 排列（9 场：cCu/cH/ep/k/p/phil/rhogeff/u/phisext），每个场连续存 LE f64 数组
- xmesh 段定义 DOF↔网格映射（xmesh Java 类含 Field/DofNumbering/NodePos 结构，反编译已解概念层）
- solutionblock ~5.4MB/块：201K 合理 LE f64 / 2.1M 总槽位（含填充/对齐）；952K 非零
- 4 字节对齐分块：段内多个子块（每场/每组件），子块间由 f8e504d6 类标记分隔

## 体积工程学（对 AI 仿真直接有用）
- **1.8GB 已解模型的 99% 是 solutionblock**——"求解后瘦身"=zip 级删除 solutionblock 段（保留 dmodel+xmesh+solutionstatic）即可出"结果骨架"档（~25MB），参数/物理/求解器全保留
- 模板分发同理：unsolved 2.2MB vs solved 1.8GB = 800 倍差异全在解段

## 骨架档实测（E-028 补充）
删 solutionblock 后 **1799MB → 8MB**（225 倍），COMSOL 正常加载：物理 tcd/bf 全在、解序列 sol1-4 框架保留（数据清空）——参数/物理/求解器/研究全可读，可作为"已解模型的分发档"。

## 边界（诚实）
- magic 之后的子块索引表（场→偏移）结构未完全解出；DOF 序↔物理场映射依赖 xmesh 二进制（native FMatrix/FBlock）——完整离线取解向量属 native 级后续
