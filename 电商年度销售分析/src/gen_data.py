# -*- coding: utf-8 -*-
"""
gen_data.py —— 第 37 课：生成可复现的模拟数据（数据源脚本）

作用
----
用 NumPy 的 random 模块 + Pandas，造出三张"像真数据"的表，并故意植入
7 类质量问题，为后面的质量体检、清洗、特征、分析提供素材：

    data/raw/orders.csv   订单表 5050 行 × 11 列
    data/raw/users.csv    用户表 1200 行 × 5 列
    data/raw/funnel.csv   漏斗表 30 行 × 5 列（2025-11-01 ~ 11-30）

可复现性
--------
固定 np.random.seed(42)，并把"搞破坏"的随机过程交给独立随机源
np.random.default_rng(7)，因此全班的数字完全一致、可对照讲评。

运行
----
    python src/gen_data.py
（脚本内部用 __file__ 定位项目根目录，在任意工作目录下运行都能跑通）
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ---------- 0. 路径：统一写在文件头部，换目录只改这一行 ----------
BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# ---------- 1. 骨架与季节性 ----------
np.random.seed(42)                       # ★ 固定随机种子，保证全班数据一致

N = 5000                                 # 订单总数
START = pd.Timestamp("2025-01-01")
DAYS = 365

# 给每一天一个"被抽中的权重"：6 月（618）1.3 倍、11 月（双11）1.9 倍、12 月 1.2 倍
day_weight = np.ones(DAYS)
day_weight[151:181] = 1.3
day_weight[304:334] = 1.9
day_weight[334:365] = 1.2
day_weight = day_weight / day_weight.sum()

day_idx = np.random.choice(DAYS, size=N, p=day_weight)      # 按权重抽日期
order_date = START + pd.to_timedelta(day_idx, unit="D")     # 第几天 → 具体日期
print("[1] 抽样日期前 5 条：")
print(order_date[:5])

# ---------- 2. 品类、价格、数量、金额 ----------
# 品类：电子 18%、服饰 28%、家居 20%、美妆 20%、食品 14%
category = np.random.choice(
    ["电子", "服饰", "家居", "美妆", "食品"],
    size=N, p=[0.18, 0.28, 0.20, 0.20, 0.14]
)

# 每个品类一个基准价，再用对数正态分布造"有高有低"的单价
base_price = {"电子": 2000, "服饰": 260, "家居": 480, "美妆": 180, "食品": 60}
base = np.array([base_price[c] for c in category])
unit_price = np.round(base * np.random.lognormal(0, 0.35, N), 2)

# 数量：1 件占 55%，越多越少见
quantity = np.random.choice([1, 2, 3, 4, 5], size=N, p=[0.55, 0.25, 0.12, 0.05, 0.03])

# 服饰、食品是"价格敏感"品类：单价越高，买得越少（为 Q6 埋下真实关系）
price_ratio = unit_price / base
q_sensitive = np.clip(np.round(6 - 3 * price_ratio + np.random.normal(0, 1.0, N)), 1, 5).astype(int)
sensitive = np.isin(category, ["服饰", "食品"])
quantity[sensitive] = q_sensitive[sensitive]

amount = np.round(unit_price * quantity, 2)
print("\n[2] 单价 / 数量 / 金额前 5 条：")
print(unit_price[:5], quantity[:5], amount[:5])

# ---------- 3. 拼成订单表 ----------
product_map = {
    "电子": ["蓝牙耳机", "智能手表", "机械键盘"],
    "服饰": ["纯棉T恤", "牛仔裤", "羽绒服"],
    "家居": ["乳胶枕", "收纳柜", "四件套"],
    "美妆": ["精华液", "口红", "面膜"],
    "食品": ["坚果礼盒", "咖啡豆", "零食大礼包"],
}
product_name = [np.random.choice(product_map[c]) for c in category]

region = np.random.choice(
    ["华东", "华南", "华北", "西南", "西北", "东北"],
    size=N, p=[0.31, 0.22, 0.18, 0.13, 0.08, 0.08]
)
channel = np.random.choice(["App", "小程序", "PC", "H5"], size=N, p=[0.45, 0.30, 0.15, 0.10])
status = np.random.choice(["已完成", "已取消", "退款"], size=N, p=[0.82, 0.10, 0.08])
user_id = np.random.randint(1001, 2201, size=N)

orders = pd.DataFrame({
    "order_id": [f"O{100001 + i}" for i in range(N)],
    "user_id": [f"U{u}" for u in user_id],
    "order_date": order_date.strftime("%Y-%m-%d"),
    "category": category,
    "product_name": product_name,
    "unit_price": unit_price,
    "quantity": quantity,
    "amount": amount,
    "region": region,
    "channel": channel,
    "status": status,
})
print("\n[3] 订单表规模与前 3 行：")
print(orders.shape)
print(orders.head(3).to_string())

# ---------- 4. 造用户表与漏斗表 ----------
M = 1200
users = pd.DataFrame({
    "user_id": [f"U{u}" for u in range(1001, 1001 + M)],
    "register_date": (pd.Timestamp("2024-01-01")
                      + pd.to_timedelta(np.random.randint(0, 730, M), unit="D")).strftime("%Y-%m-%d"),
    "city": np.random.choice(["上海", "广州", "北京", "成都", "西安", "沈阳"], size=M),
    "age": np.random.randint(18, 66, size=M).astype(float),
    "gender": np.random.choice(["男", "女", "未知"], size=M, p=[0.48, 0.48, 0.04]),
})
print("\n[4] 用户表规模与前 3 行：")
print(users.shape)
print(users.head(3).to_string())

view = np.random.randint(20000, 40001, 30)
cart = (view * np.random.uniform(0.08, 0.12, 30)).astype(int)
order = (cart * np.random.uniform(0.40, 0.55, 30)).astype(int)
pay = (order * np.random.uniform(0.70, 0.85, 30)).astype(int)

funnel = pd.DataFrame({
    "date": pd.date_range("2025-11-01", periods=30).strftime("%Y-%m-%d"),
    "view_cnt": view, "cart_cnt": cart, "order_cnt": order, "pay_cnt": pay,
})
print("\n[5] 漏斗表规模与前 3 行：")
print(funnel.shape)
print(funnel.head(3).to_string())

# ---------- 5. 植入 7 类脏数据 ----------
rng = np.random.default_rng(7)          # 另一个独立随机源，只负责"搞破坏"
idx = rng.choice(N, 150, replace=False)

# 1) 缺失值：amount 3%、region 2%
orders.loc[idx[:150], "amount"] = np.nan
orders.loc[idx[:100], "region"] = np.nan
users.loc[rng.choice(M, int(M * 0.08), replace=False), "age"] = np.nan

# 2) 格式不统一：region 混入 " 华东 "、"华东区" 等写法
fmt_idx = rng.choice(N, 200, replace=False)
variants = [" 华东 ", "华东区", "华南 ", " 华北", "西南区"]
for i, j in zip(fmt_idx, rng.choice(len(variants), 200)):
    orders.loc[i, "region"] = variants[j]

# 3) 单价异常：15 条（0 或负数）
bad_price = rng.choice(N, 15, replace=False)
orders.loc[bad_price[:8], "unit_price"] = 0
orders.loc[bad_price[8:], "unit_price"] = -19.9

# 4) 逻辑矛盾：10 条 quantity=0 但 amount>0
logic_bad = rng.choice(N, 10, replace=False)
orders.loc[logic_bad, "quantity"] = 0

# 5) 离群值：8 条极端大额（×200）
out_idx = rng.choice(N, 8, replace=False)
orders.loc[out_idx, "amount"] = orders.loc[out_idx, "amount"] * 200

# 6) 类型错误：20 条非法日期
bad_date = rng.choice(N, 20, replace=False)
orders["order_date"] = orders["order_date"].astype(object)
orders.loc[bad_date, "order_date"] = "2025/13/45"

# 7) 重复行：追加 50 条完全重复的订单，再打乱行序
dup = orders.sample(50, random_state=1)
orders = pd.concat([orders, dup], ignore_index=True)
orders = orders.sample(frac=1, random_state=2).reset_index(drop=True)
print("\n[6] 植入脏数据后规模:", orders.shape)

# ---------- 6. 写盘 ----------
# utf-8-sig：带 BOM，Windows 上用 Excel 双击打开中文不乱码
orders.to_csv(RAW / "orders.csv", index=False, encoding="utf-8-sig")
users.to_csv(RAW / "users.csv", index=False, encoding="utf-8-sig")
funnel.to_csv(RAW / "funnel.csv", index=False, encoding="utf-8-sig")

print(f"\n[7] 已写入 {RAW}")
print("orders", orders.shape, "| users", users.shape, "| funnel", funnel.shape)

# ---------- 7. 课堂检查点（三条断言全过才算生成正确）----------
chk = pd.read_csv(RAW / "orders.csv", encoding="utf-8-sig")
assert chk.shape == (5050, 11), f"订单表规模应为 (5050, 11)，实际 {chk.shape}"
assert chk["amount"].isna().sum() == 153, "amount 缺失数应为 153"
assert chk["order_id"].duplicated().sum() == 50, "order_id 重复数应为 50"
assert (chk["order_date"] == "2025/13/45").sum() == 20, "非法日期应为 20 条"
print("\n✅ 数据生成正确")
