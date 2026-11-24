# -*- coding: utf-8 -*-
"""
02_clean.py —— 第 39 课：数据清洗（本项目最核心的工程环节）

作用
----
按"去重 → 类型转换 → 业务规则 → 缺失处理 → 格式统一 → 离群标记 → 落盘+日志"
的正确顺序清洗订单表，每一步都记录"删了多少行、为什么删"，产出：

    data/processed/clean_orders.csv   清洗后订单表（4800 行 × 12 列，含 is_outlier）
    output/clean_log.txt              可追溯的清洗日志

清洗完成后脚本会自动跑 8 条验收断言，全部通过才打印 ✅。

运行
----
    python src/02_clean.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

pd.set_option("display.unicode.east_asian_width", True)

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
OUTPUT = BASE / "output"
PROCESSED.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RAW / "orders.csv", encoding="utf-8-sig")
log = ["清洗日志 | 源文件 data/raw/orders.csv | 顺序：去重→类型→业务规则→缺失→格式→离群标记"]
n0 = len(df)
log.append(f"原始数据: {n0} 行 × {df.shape[1]} 列")

# ---------- ① 去重 ----------
d = df.drop_duplicates(subset=["order_id"], keep="first").copy()
log.append(f"① 按 order_id 去重: {n0} → {len(d)}（删除 {n0 - len(d)} 行）")

# ---------- ② 日期类型转换，非法转 NaT 后剔除 ----------
d["order_date"] = pd.to_datetime(d["order_date"], errors="coerce", format="%Y-%m-%d")
n_before = len(d)
d = d.dropna(subset=["order_date"]).copy()
log.append(f"② 非法日期转 NaT 并剔除: {n_before} → {len(d)}（删除 {n_before - len(d)} 行）")

# ---------- ③ 金额缺失剔除 ----------
n_before = len(d)
d = d.dropna(subset=["amount"]).copy()
log.append(f"③ 金额缺失剔除: {n_before} → {len(d)}（删除 {n_before - len(d)} 行）")

# ---------- ④ 区域格式统一 + 缺失填"未知" ----------
d["region"] = (d["region"].astype("string")
               .str.strip()
               .str.replace("区", "", regex=False)
               .fillna("未知"))

# ---------- ⑤ 单价、数量异常剔除 ----------
n_before = len(d)
d = d[d["unit_price"] > 0].copy()
log.append(f"④ 单价<=0 剔除: {n_before} → {len(d)}（删除 {n_before - len(d)} 行）")

n_before = len(d)
d = d[d["quantity"] > 0].copy()
log.append(f"⑤ 数量<=0 剔除: {n_before} → {len(d)}（删除 {n_before - len(d)} 行）")

# ---------- ⑥ 金额与单价×数量一致性校验 ----------
calc = d["unit_price"] * d["quantity"]
dev = (d["amount"] - calc).abs() / calc
n_before = len(d)
d = d[dev <= 0.01].copy()
log.append(f"⑥ 金额与单价×数量偏差>1% 剔除: {n_before} → {len(d)}（删除 {n_before - len(d)} 行）")

# ---------- ⑦ 离群金额：log1p 后再算 IQR（金额右偏，先取对数） ----------
log_amt = np.log1p(d["amount"])
q1, q3 = log_amt.quantile([0.25, 0.75])
iqr = q3 - q1
d["is_outlier"] = log_amt > q3 + 1.5 * iqr
log.append(f"⑦ IQR 标记离群金额: {int(d['is_outlier'].sum())} 行（不删除）")

log.append(f"最终规模: {d.shape[0]} 行 × {d.shape[1]} 列（新增 is_outlier 列）")

for line in log:
    print(line)

print("\n清洗后 region 取值分布：")
print(d["region"].value_counts().to_string())
print("\n清洗后字段类型：")
print(d.dtypes.to_string())

# ---------- ⑧ 落盘 ----------
clean_path = PROCESSED / "clean_orders.csv"
d.to_csv(clean_path, index=False, encoding="utf-8-sig")
(OUTPUT / "clean_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
print(f"\n已写入 {clean_path}")
print(f"已写入 {OUTPUT / 'clean_log.txt'}")

# ---------- 阶段验收：8 条断言全过才放行 ----------
chk = pd.read_csv(clean_path, encoding="utf-8-sig", parse_dates=["order_date"])
assert len(chk) == 4800, f"行数不对：{len(chk)}"
assert chk["order_id"].duplicated().sum() == 0, "还有重复订单"
assert chk["amount"].isna().sum() == 0, "金额仍有缺失"
assert chk["region"].isna().sum() == 0, "区域仍有缺失"
assert set(chk["region"].unique()) <= {"华东", "华南", "华北", "西南", "西北", "东北", "未知"}, "区域格式未统一"
assert (chk["unit_price"] > 0).all(), "单价仍有异常"
assert (chk["quantity"] > 0).all(), "数量仍有异常"
assert chk["order_date"].dtype.kind == "M", "日期类型未转换"
print("\n✅ 清洗验收通过")
