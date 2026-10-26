# 电化学（bfc）默认求解器配方（反编译 com.comsol.bfc.util.a 蒸馏，6.3）

> 与 CFD_solver_recipe.md 姊妹篇；来源 src_bfc/com/comsol/bfc/util/a.java（2112 行包）
> 对象：你的 tcd（TertiaryCurrentDistributionNernstPlanck）等电化学接口

## 全耦合非线性（fullycoupled）
- **dtech=auto 阻尼，initstep=1（初始阻尼 1 = 无阻尼起步！）**
- 瞬态研究：minstep=1e-4、**maxiter=5**（每时间步最多 5 次牛顿——瞬态靠时间步当阻尼）
- 稳态/初始化研究：minstep=1e-6、**maxiter=25**
- 变量分组：c("Current_distribution_variables")——电流分布专用变量组进入分离策略

## 线性求解器（main，ls1）
- **linsolver=pardiso（默认直解）**，pivotperturb=1e-13
- **Corrosion/Electrodeposition 全系**（CorrosionPrimary/Secondary/TertiaryNP、Electrodeposition 同）→ mumpsalloc=**2**（MUMPS 分配因子翻倍——腐蚀/电积矩阵更难分解）
- 其他电化学若满足条件 c() → mumpsalloc=**1.3**
- Battery 初始化（BfcAnalysisID.a）→ rhob=1（误差估计因子）

## 与 CFD 配方对照（你的 tcd+bf 耦合模型两侧默认值）
| | 电化学侧(tcd) | 流体侧(bf/cfd) |
|---|---|---|
| 阻尼 | auto, init=1 | auto, init=0.01 / const 0.8 |
| 瞬态 maxiter | **5** | 50 |
| 线性 | pardiso+mumpsalloc 1.3~2 | 迭代+预条件子族 |
| 伪时间推进 | 无 | CFL 5→10000+PID |

**排障含义**：你的耦合模型同时吃到两套配方；tcd 侧牛顿失败先查阻尼/initstep（默认 1 很激进）与 mumpsalloc；bf 侧查 CFL/segaacc。
