# -*- coding: utf-8 -*-
"""
03_feature.py —— 第 40 课：特征工程

作用
----
承接 data/processed/clean_orders.csv，把"原始字段"派生成"业务能用的字段"：

1) 时间特征：year / month / quarter / weekday / is_weekend
2) 金额分箱：amount_level（100以下 / 100-500 / 500-1000 / 1000以上）
3) 用户特征：按用户汇总 首单日期 / 末单日期 / 订单数 / 消费额 / 购买间隔天数
   （样本口径：status='已完成' 且 is_outlier=False，共 1141 位购买用户）

产出：
    data/processed/orders_feature.csv   订单特征表（4800 行 × 18 列）
    data/processed/user_feature.csv     用户特征表（1141 行 × 5 列）

运行
----
    python src/03_feature.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

pd.set_option("display.unicode.east_asian_width", True)

BASE = Path(__file__).resolve().parent.parent
PROCESSED = BASE / "data" / "processed"

df = pd.read_csv(PROCESSED / "clean_orders.csv",
                 encoding="utf-8-sig", parse_dates=["order_date"])
print("读入清洗后数据:", df.shape)

# ---------- 1. 时间特征 ----------
df["year"] = df["order_date"].dt.year
df["month"] = df["order_date"].dt.month
df["quarter"] = df["order_date"].dt.quarter
df["weekday"] = df["order_date"].dt.dayofweek       # 周一=0 ... 周日=6
df["is_weekend"] = df["weekday"] >= 5

print("\n[1] 时间特征（前 5 行）：")
print(df[["order_date", "year", "month", "quarter", "weekday", "is_weekend"]]
      .head(5).to_string())

# 验证周末效应
print("\n周末订单占比: %.2f%%" % (df["is_weekend"].mean() * 100))
print(df.groupby("is_weekend")["amount"].mean().round(2).to_string())

# ---------- 2. 金额分箱 ----------
df["amount_level"] = pd.cut(
    df["amount"],
    bins=[0, 100, 500, 1000, np.inf],
    labels=["100以下", "100-500", "500-1000", "1000以上"]
)
print("\n[2] 金额分箱分布：")
print(df["amount_level"].value_counts().sort_index().to_string())

# ---------- 3. 用户维度特征 ----------
# 分析样本 = 已完成 + 剔除离群
paid = df[(df["status"] == "已完成") & (~df["is_outlier"])].copy()
print("\n[3] 分析样本:", paid.shape)

feat = paid.groupby("user_id").agg(
    首单日期=("order_date", "min"),
    末单日期=("order_date", "max"),
    订单数=("order_id", "count"),
    消费额=("amount", "sum"),
)
feat["购买间隔天数"] = (feat["末单日期"] - feat["首单日期"]).dt.days
print("\n用户特征表（前 5 行）：")
print(feat.head(5).to_string())

print("\n用户特征统计：")
print(feat[["订单数", "消费额", "购买间隔天数"]].describe().round(1).to_string())

# ---------- 4. 落盘 ----------
feat_path = PROCESSED / "user_feature.csv"
orders_path = PROCESSED / "orders_feature.csv"
df.to_csv(orders_path, index=False, encoding="utf-8-sig")
feat.to_csv(feat_path, encoding="utf-8-sig")

print("\n特征表已保存:", df.shape, feat.shape)

# ---------- 检查点 ----------
assert df.shape == (4800, 18), f"订单特征表应为 (4800, 18)，实际 {df.shape}"
assert feat.shape == (1141, 5), f"用户特征表应为 (1141, 5)，实际 {feat.shape}"
assert set(df["amount_level"].cat.categories) == {"100以下", "100-500", "500-1000", "1000以上"}
print("✅ 特征工程完成")
