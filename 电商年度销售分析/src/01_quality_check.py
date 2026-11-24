# -*- coding: utf-8 -*-
"""
01_quality_check.py —— 第 38 课：数据质量评估（数据体检）

作用
----
对 data/raw/orders.csv 做一次完整的"数据体检"，按教案规定的 8 个固定动作
逐项检查：结构规模、缺失率、重复行、类别取值、日期合法性、业务规则、
分布与离群、外键完整性；并把结果整理成一张可交付的《数据问题清单》，
写入 output/quality_report.md。

本脚本只"看病、不开刀"：不修改原始数据，所有处理决策留给 02_clean.py 执行。

运行
----
    python src/01_quality_check.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

pd.set_option("display.unicode.east_asian_width", True)

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
OUTPUT = BASE / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RAW / "orders.csv", encoding="utf-8-sig")
users = pd.read_csv(RAW / "users.csv", encoding="utf-8-sig")

print("=" * 70)
print("数据质量体检 · data/raw/orders.csv")
print("=" * 70)
print("规模:", df.shape)
print("\n字段类型：")
print(df.dtypes.to_string())
print("\n前 3 行：")
print(df.head(3).to_string())

# ---------------- ① 结构与规模 ----------------
print("\n" + "-" * 70)
print("① 结构与规模（df.info()）")
print("-" * 70)
df.info()

# ---------------- ② 缺失率 ----------------
print("\n" + "-" * 70)
print("② 缺失率（比缺失个数更有意义）")
print("-" * 70)
missing = (df.isnull().mean() * 100).round(2)
print(missing[missing > 0].to_string())
n_miss_amount = int(df["amount"].isna().sum())
n_miss_region = int(df["region"].isna().sum())

# ---------------- ③ 重复行 ----------------
print("\n" + "-" * 70)
print("③ 重复行")
print("-" * 70)
n_dup_all = int(df.duplicated().sum())
n_dup_key = int(df.duplicated(subset=["order_id"]).sum())
print("完全重复:", n_dup_all)
print("order_id 重复:", n_dup_key)

# ---------------- ④ 类别取值分布 ----------------
print("\n" + "-" * 70)
print("④ 类别取值分布（揪出格式不统一）")
print("-" * 70)
print(df["region"].value_counts(dropna=False).to_string())

VALID_REGION = {"华东", "华南", "华北", "西南", "西北", "东北"}
n_bad_fmt = int((df["region"].notna() & ~df["region"].isin(VALID_REGION)).sum())

# ---------------- ⑤ 日期合法性 ----------------
print("\n" + "-" * 70)
print("⑤ 日期合法性")
print("-" * 70)
dt = pd.to_datetime(df["order_date"], errors="coerce", format="%Y-%m-%d")
n_bad_date = int(dt.isna().sum())
print("非法日期行数:", n_bad_date)
print(df.loc[dt.isna(), "order_date"].unique().tolist())

# ---------------- ⑥ 数值业务规则 ----------------
print("\n" + "-" * 70)
print("⑥ 数值业务规则检查")
print("-" * 70)
n_bad_price = int((df["unit_price"] <= 0).sum())
n_bad_qty = int(((df["quantity"] == 0) & (df["amount"] > 0)).sum())

calc = df["unit_price"] * df["quantity"]
dev = (df["amount"] - calc).abs() / calc.replace(0, np.nan)
n_bad_amount = int((dev > 0.01).sum())
print("单价<=0:", n_bad_price)
print("数量=0 且金额>0:", n_bad_qty)
print("金额与单价×数量偏差>1%:", n_bad_amount)

# ---------------- ⑦ 分布与离群 ----------------
print("\n" + "-" * 70)
print("⑦ 分布与离群（amount.describe）")
print("-" * 70)
print(df["amount"].describe().round(2).to_string())

# 离群值按 02_clean.py 的清洗后样本再算（log1p 后 IQR），保证口径一致
c = df.drop_duplicates(subset=["order_id"], keep="first").copy()
c["order_date"] = pd.to_datetime(c["order_date"], errors="coerce", format="%Y-%m-%d")
c = c.dropna(subset=["order_date", "amount"])
c = c[(c["unit_price"] > 0) & (c["quantity"] > 0)]
_calc = c["unit_price"] * c["quantity"]
c = c[((c["amount"] - _calc).abs() / _calc) <= 0.01]
log_amt = np.log1p(c["amount"])
q1, q3 = log_amt.quantile([0.25, 0.75])
n_outlier = int((log_amt > q3 + 1.5 * (q3 - q1)).sum())
print("（按清洗后样本 log1p+IQR 复算，离群金额）:", n_outlier, "行")

# ---------------- ⑧ 交叉验证（外键完整性） ----------------
print("\n" + "-" * 70)
print("⑧ 交叉验证（外键完整性）")
print("-" * 70)
n_user_order = int(df["user_id"].nunique())
n_user_users = int(users["user_id"].nunique())
n_orphan = len(set(df["user_id"]) - set(users["user_id"]))
print("订单中的用户数:", n_user_order)
print("用户表用户数:", n_user_users)
print("订单里有、用户表没有的用户:", n_orphan)

# ---------------- 交付物：数据问题清单 ----------------
rows = [
    ("①", "完全重复", "整行 / order_id", n_dup_key, "按 order_id 去重", "一单一行，order_id 是业务主键"),
    ("②", "非法日期", "order_date", n_bad_date, "to_datetime(errors='coerce') 后剔除", "无法推断真实下单日"),
    ("③", "金额缺失", "amount", n_miss_amount, "剔除", "补齐等于编造数据，且缺失率仅 3%"),
    ("④", "区域缺失", "region", n_miss_region, "填 '未知'", "区域本身可能未填写，保留订单"),
    ("⑤", "区域格式", "region", n_bad_fmt, "strip + 去 '区'", "统一为 6 大区"),
    ("⑥", "单价异常", "unit_price", n_bad_price, "剔除", "0 或负价无业务意义"),
    ("⑦", "数量异常", "quantity", n_bad_qty, "剔除", "数量 0 却有金额，逻辑不成立"),
    ("⑧", "金额不一致", "amount", n_bad_amount, "剔除", "与单价×数量偏差 >1%"),
    ("⑨", "离群金额", "amount", n_outlier, "标记 is_outlier，分析时排除", "疑似录入错误，但保留痕迹可追溯"),
]

lines = [
    "# 数据质量体检报告（01_quality_check）",
    "",
    f"- 数据源：`data/raw/orders.csv`（{df.shape[0]} 行 × {df.shape[1]} 列）",
    f"- 用户表：`data/raw/users.csv`（{users.shape[0]} 行 × {users.shape[1]} 列，"
    f"`age` 缺失 {int(users['age'].isna().sum())} 条 / {users['age'].isna().mean()*100:.2f}%）",
    "- 生成脚本：`src/gen_data.py`（np.random.seed(42)，可复现）",
    "",
    "## 一、缺失情况",
    "",
    "| 字段 | 缺失行数 | 缺失率 |",
    "|------|----------|--------|",
]
for col in missing[missing > 0].index:
    lines.append(f"| {col} | {int(df[col].isna().sum())} | {df[col].isna().mean()*100:.2f}% |")

lines += [
    "",
    "## 二、重复行",
    "",
    f"- 完全重复：{n_dup_all} 行；order_id 重复：{n_dup_key} 行。"
    "两者相等，说明是整行复制，按 order_id 去重即可。",
    "",
    "## 三、区域取值分布（含脏写法）",
    "",
    "```",
    df["region"].value_counts(dropna=False).to_string(),
    "```",
    "",
    "## 四、数值业务规则",
    "",
    "| 检查项 | 命中行数 |",
    "|--------|----------|",
    f"| 单价 <= 0 | {n_bad_price} |",
    f"| 数量 = 0 且金额 > 0 | {n_bad_qty} |",
    f"| 金额与单价×数量偏差 > 1% | {n_bad_amount} |",
    f"| 非法日期 | {n_bad_date} |",
    "",
    "## 五、金额分布（均值骗人、中位数说实话）",
    "",
    "```",
    df["amount"].describe().round(2).to_string(),
    "```",
    "",
    f"均值被极少数大额订单拉高，中位数远低于均值；最大值 "
    f"{df['amount'].max():,.2f} 元明显异常。",
    "",
    "## 六、外键完整性",
    "",
    f"- 订单中的用户数 {n_user_order}，用户表用户数 {n_user_users}，"
    f"订单里有、用户表没有的用户 {n_orphan} 个 → 两表可以安全 merge。",
    "",
    "## 七、数据问题清单（交付物）",
    "",
    "| 编号 | 问题类型 | 涉及字段 | 实测行数 | 处理方式 | 决策理由 |",
    "|------|----------|----------|----------|----------|----------|",
]
for r in rows:
    lines.append("| " + " | ".join(str(x) for x in r) + " |")

lines += [
    "",
    "## 八、决策原则：删 / 填 / 标 / 留",
    "",
    "| 决策 | 适用场景 | 本项目例子 |",
    "|------|----------|-----------|",
    "| 删 | 无法还原真相，且占比低 | 非法日期、负单价、金额缺失 |",
    "| 填 | 缺失本身有业务含义，或可用规则安全补齐 | region 缺失 → '未知' |",
    "| 标 | 值可能真实，但会污染统计 | 离群金额 → is_outlier |",
    "| 留 | 不影响本次分析口径 | 已取消 / 退款订单留给状态分析 |",
    "",
    "> 清洗动作由 `src/02_clean.py` 执行，逐项写入 `output/clean_log.txt`。",
]

report = OUTPUT / "quality_report.md"
report.write_text("\n".join(lines), encoding="utf-8")

print("\n" + "=" * 70)
print("问题清单摘要")
print("=" * 70)
for r in rows:
    print(f"{r[0]} {r[1]}（{r[2]}）: {r[3]} 行 → {r[4]}")
print(f"\n✅ 体检完成，报告已写入 {report}")
