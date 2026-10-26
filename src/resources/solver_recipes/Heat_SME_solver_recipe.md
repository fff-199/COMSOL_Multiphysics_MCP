# 热传递（heat）与结构力学（sme）默认求解配方（反编译蒸馏 6.3）

## 传热（heat）— 4 个建议实现类
来源：com.comsol.heat.util.{b,d,g,i}.java（共 2215 行）

### 全耦合非线性（fullycoupled）
| 参数 | 值 | 条件 |
|---|---|---|
| dtech | auto（辐射时 const 0.9） | |
| initstep | 0.01 | |
| minstep | 1e-6 | |
| maxiter | 50（瞬态 5） | |
| Jacobian | onevery（辐射 once） | |
| Anderson 加速 | aacc(5, 0.9, 延迟1) | 辐射/自然对流时 |
| termonres | off | |

### 分离解法（segregated）
- segaacc(5, 0.9, 延迟1)（Anderson）；ntolfact=0.1；segtermonres=off
- 子步 subdamp=0.7-0.8；Jacobian once（辐射时 onevery）

### 瞬态
- maxorder=2；atolmethod=自动（按场列表）；estrat=exclude
- tstepsbdf=intermediate

### 线性求解器
- **pardiso**（默认直解）+ pivotperturb=1e-13
- 大模型时 **gmres + saamg 预条件**（rhob=400）
- Geometric Multigrid (gmg) 备选
- blocksize=100（装配块）；cachepattern=true（重用稀疏模式）

### 稳态
- getStationarySettings = null（**传热无稳态专用建议**——全部走通用建议引擎）

---

## 结构力学（sme）— 0 个自定义建议实现

**发现**：sme 模块只有 IAutoSolverSuggestion 引用（9 个类全部标 REF），**无自定义实现**。

**含义**：结构力学使用 **COMSOL 通用默认求解建议**（core 模块的 AutoSolverProvider）：
- 全耦合：dtech=auto, initstep=1（与 EC 同——无阻尼起步）
- 线性：pardiso（直解）或 gmres+saamg
- 瞬态：BDF maxorder=2
- 前一组件阻尼 prevcompdamp=0.35

**排障对照**：结构力学不收敛时，参考 EC 配方中的"通用默认"参数——因为 sme 没有自己的调优。

---

## 三个模块配方对照总表

| 参数 | CFD（两相流） | EC（电化学） | Heat（传热） | SME（结构） |
|---|---|---|---|---|
| 全耦合 initstep | 0.01 | **1** | 0.01 | 1（通用） |
| 全耦合 maxiter | 50 | 25(稳态)/5(瞬态) | 50(稳态)/5(瞬态) | 25/5 |
| 阻尼策略 | const 0.8 (RANS) | auto | auto（辐射 const 0.9） | auto |
| Anderson | cflcmp(>CFL 9000) | 无 | aacc(5,0.9) 或无 | 无 |
| 线性默认 | iterative+ILU/MG | **pardiso**+mumpsalloc 1.3-2 | pardiso 或 gmres+saamg | pardiso |
| 分离法 | maxsegiter=10, segaacc | 无 | segaacc(5,0.9), subdamp 0.7-0.8 | 无自定义 |
| 瞬态 BDF | maxorder=2 | maxorder=2 | maxorder=2 | maxorder=2 |

## AI 排障快速指南
- **流体侧不收敛** → 先查 CFL/PID 参数（CFD 配方）；改 Segregated + segaacc
- **电化学侧不收敛** → initstep 从 1 降到 0.01（官方对 Corrosion 用 mumpsalloc=2）
- **传热不收敛** → 检查辐射/自然对流是否触发 aacc；非线性强时 initstep 降
- **结构不收敛** → 无模块级特殊配方；查通用建议（initstep 降/加阻尼/分离 T 与 u）
