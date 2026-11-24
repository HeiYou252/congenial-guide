# -*- coding: utf-8 -*-
"""
05_visualize.py —— 第 42 课：可视化看板与专题图

作用
----
把第 41 课的 6 条结论组织成一张 2×3 综合看板，并输出 4 张报告级专题图。
"一次算完、绘图只负责画"——所有指标先算好，再交给 matplotlib。

产出：
    output/dashboard.png            2×3 综合看板（月度/品类/区域/客户/漏斗/金额分布）
    output/q1_gmv_trend.png         Q1 月度 GMV（双轴折线 + 订单量柱）
    output/q2_category.png          Q2 品类 GMV 排名（横向条形）
    output/q3_region_category.png   Q3 区域 × 品类 GMV 热力图
    output/q6_price_scatter.png     Q6 分品类 单价-件数 散点 + 回归线
    output/q4_rfm.png               Q4 客户分层：人数占比 vs GMV 占比
    output/q5_funnel.png            Q5 转化漏斗（逐级转化率）

运行
----
    python src/05_visualize.py
脚本用 Agg 后端，不会弹窗阻塞；在 Jupyter 里可删掉 matplotlib.use("Agg") 一行。
"""

import matplotlib
matplotlib.use("Agg")                    # 脚本模式，避免 plt.show() 阻塞
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
from pathlib import Path

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
OUTPUT = BASE / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

# ---------------- 1. 准备数据（一次算完，绘图只负责画） ----------------
df = pd.read_csv(PROCESSED / "clean_orders.csv",
                 encoding="utf-8-sig", parse_dates=["order_date"])
funnel = pd.read_csv(RAW / "funnel.csv", encoding="utf-8-sig")

paid = df[(df["status"] == "已完成") & (~df["is_outlier"])].copy()
paid["month"] = paid["order_date"].dt.month

month_gmv = paid.groupby("month")["amount"].sum() / 10000
month_cnt = paid.groupby("month")["order_id"].count()
cat_gmv = paid.groupby("category")["amount"].sum().sort_values() / 10000
region_gmv = paid.groupby("region")["amount"].sum() / 10000
pivot = pd.pivot_table(paid, index="region", columns="category",
                       values="amount", aggfunc="sum", fill_value=0) / 10000

# ---------------- 2. RFM 分层（复用第 41 课） ----------------
snapshot = paid["order_date"].max() + pd.Timedelta(days=1)
rfm = paid.groupby("user_id").agg(最后购买=("order_date", "max"),
                                 频次=("order_id", "count"),
                                 金额=("amount", "sum"))
rfm["R"] = (snapshot - rfm["最后购买"]).dt.days
rfm["R分"] = pd.qcut(rfm["R"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F分"] = pd.qcut(rfm["频次"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M分"] = pd.qcut(rfm["金额"], 5, labels=[1, 2, 3, 4, 5]).astype(int)


def segment(row):
    r, f, m = row["R分"], row["F分"], row["M分"]
    if r >= 4 and f >= 4 and m >= 4:
        return "重要价值"
    if r < 4 and f >= 4 and m >= 4:
        return "重要保持"
    if r >= 4 and f < 4 and m >= 4:
        return "重要发展"
    if r < 4 and f < 4 and m >= 4:
        return "重要挽留"
    if r >= 4 and f >= 4 and m < 4:
        return "一般价值"
    if r < 4 and f >= 4 and m < 4:
        return "一般保持"
    if r >= 4 and f < 4 and m < 4:
        return "一般发展"
    return "流失预警"


rfm["客户类型"] = rfm.apply(segment, axis=1)
seg_gmv = rfm.groupby("客户类型")["金额"].sum().sort_values() / 10000
funnel_sum = funnel[["view_cnt", "cart_cnt", "order_cnt", "pay_cnt"]].sum()

# ---------------- 3. 2×3 综合看板 ----------------
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle("某电商平台 2025 年度销售分析看板", fontsize=20, fontweight="bold")

# ① 月度 GMV 趋势
axes[0, 0].plot(month_gmv.index, month_gmv.values, marker="o", color="#4C72B0", linewidth=2)
axes[0, 0].set_title("月度 GMV 趋势")
axes[0, 0].set_xlabel("月份")
axes[0, 0].set_ylabel("GMV（万元）")
axes[0, 0].set_xticks(range(1, 13))
axes[0, 0].grid(alpha=0.3, linestyle="--")
peak = month_gmv.idxmax()
axes[0, 0].annotate(f"双11: {month_gmv.max():.1f}万",
                    xy=(peak, month_gmv.max()),
                    xytext=(peak - 3, month_gmv.max()),
                    arrowprops=dict(arrowstyle="->"))

# ② 品类 GMV 排名（横向条形，已按升序排，最大值在顶部）
axes[0, 1].barh(cat_gmv.index, cat_gmv.values, color="#55A868")
axes[0, 1].set_title("品类 GMV 排名")
axes[0, 1].set_xlabel("GMV（万元）")
for i, v in enumerate(cat_gmv.values):
    axes[0, 1].text(v + 1, i, f"{v:.1f}", va="center")

# ③ 区域占比环形图
axes[0, 2].pie(region_gmv.values, labels=region_gmv.index, autopct="%1.1f%%",
               startangle=90, wedgeprops=dict(width=0.4, edgecolor="white"),
               pctdistance=0.78)
axes[0, 2].set_title("区域 GMV 占比")

# ④ 客户分层 GMV 贡献
axes[1, 0].barh(seg_gmv.index, seg_gmv.values, color="#C44E52")
axes[1, 0].set_title("客户分层 GMV 贡献")
axes[1, 0].set_xlabel("GMV（万元）")

# ⑤ 漏斗（各环节量级差异大，用对数轴）
steps = ["浏览", "加购", "下单", "支付"]
vals = [funnel_sum["view_cnt"], funnel_sum["cart_cnt"],
        funnel_sum["order_cnt"], funnel_sum["pay_cnt"]]
y = np.arange(len(steps))[::-1]
axes[1, 1].barh(y, vals, color=["#8172B3", "#937860", "#DA8BC3", "#8C8C8C"])
axes[1, 1].set_yticks(y, steps)
axes[1, 1].set_xscale("log")
axes[1, 1].set_title("下单转化漏斗（对数轴）")
for yi, v in zip(y, vals):
    axes[1, 1].text(v * 1.1, yi, f"{v:,}", va="center")

# ⑥ 订单金额分布
axes[1, 2].hist(paid["amount"], bins=40, color="#4C72B0", edgecolor="white")
axes[1, 2].set_title("订单金额分布")
axes[1, 2].set_xlabel("订单金额（元）")
axes[1, 2].set_ylabel("订单数")
axes[1, 2].set_xlim(0, 8000)

plt.tight_layout()
fig.savefig(OUTPUT / "dashboard.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("已保存 output/dashboard.png")

# ---------------- 4. 专题图 ①：Q1 月度 GMV（双轴） ----------------
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(month_gmv.index, month_gmv.values, marker="o", color="#4C72B0",
         linewidth=2, label="GMV（左轴）")
ax1.set_xlabel("月份")
ax1.set_ylabel("GMV（万元）", color="#4C72B0")
ax1.set_xticks(range(1, 13))
ax1.grid(alpha=0.3, linestyle="--")

ax2 = ax1.twinx()
ax2.bar(month_gmv.index, month_cnt.values, alpha=0.25, color="#C44E52", label="订单量（右轴）")
ax2.tick_params(axis="y", colors="#8A8F98")   # 右轴只留刻度，轴标题由图例说明，避免贴边被裁

ax1.set_title("2025 年月度 GMV 与订单量", fontsize=15, fontweight="bold")
fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9))
plt.tight_layout()
fig.savefig(OUTPUT / "q1_gmv_trend.png", dpi=300, bbox_inches="tight", pad_inches=0.12)
plt.close(fig)
print("已保存 output/q1_gmv_trend.png")

# ---------------- 5. 专题图 ②：Q2 品类排名 ----------------
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(cat_gmv.index, cat_gmv.values, color="#55A868")
ax.set_title("2025 年品类 GMV 排名", fontsize=14, fontweight="bold")
ax.set_xlabel("GMV（万元）")
for b, v in zip(bars, cat_gmv.values):
    ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}", va="center")
plt.tight_layout()
fig.savefig(OUTPUT / "q2_category.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("已保存 output/q2_category.png")

# ---------------- 6. 专题图 ③：Q3 区域 × 品类热力图 ----------------
fig, ax = plt.subplots(figsize=(9, 5))
im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")
ax.set_xticks(np.arange(len(pivot.columns)), pivot.columns)
ax.set_yticks(np.arange(len(pivot.index)), pivot.index)
for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]):
        ax.text(j, i, f"{pivot.values[i, j]:.1f}", ha="center", va="center", fontsize=9)
ax.set_title("区域 × 品类 GMV 热力图（万元）", fontsize=14, fontweight="bold")
ax.set_xlabel("品类")
ax.set_ylabel("区域")
fig.colorbar(im, ax=ax, label="GMV（万元）")
plt.tight_layout()
fig.savefig(OUTPUT / "q3_region_category.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("已保存 output/q3_region_category.png")

# ---------------- 7. 专题图 ④：Q6 分品类 单价-件数 散点 ----------------
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.ravel()
for i, (c, sub) in enumerate(paid.groupby("category")):
    axes[i].scatter(sub["unit_price"], sub["quantity"], s=12, alpha=0.4)
    k, b = np.polyfit(sub["unit_price"], sub["quantity"], 1)
    xs = np.linspace(sub["unit_price"].min(), sub["unit_price"].max(), 50)
    axes[i].plot(xs, k * xs + b, color="red", linewidth=2)
    axes[i].set_title(f"{c}（r={sub['unit_price'].corr(sub['quantity']):.2f}）")
    axes[i].set_xlabel("单价（元）")
    axes[i].set_ylabel("购买件数")
axes[5].axis("off")
fig.suptitle("Q6 单价与购买件数：分品类散点 + 回归线", fontsize=15, fontweight="bold")
plt.tight_layout()
fig.savefig(OUTPUT / "q6_price_scatter.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("已保存 output/q6_price_scatter.png")

# ---------------- 8. 专题图 ⑤：Q4 客户分层（人数 vs GMV） ----------------
seg = rfm.groupby("客户类型").agg(人数=("R", "count"), 金额=("金额", "sum"))
seg["人数占比%"] = seg["人数"] / len(rfm) * 100
seg["GMV占比%"] = seg["金额"] / rfm["金额"].sum() * 100
seg = seg.sort_values("GMV占比%")

fig, ax = plt.subplots(figsize=(10, 5.5))
yy = np.arange(len(seg))
h = 0.38
ax.barh(yy - h / 2, seg["人数占比%"], height=h, color="#8C8C8C", label="人数占比")
ax.barh(yy + h / 2, seg["GMV占比%"], height=h, color="#C44E52", label="GMV 占比")
ax.set_yticks(yy, seg.index)
ax.set_xlabel("占比（%）")
ax.set_title("Q4 客户分层：人数占比 vs GMV 占比", fontsize=14, fontweight="bold")
ax.legend(loc="lower right")
for i, (a, b) in enumerate(zip(seg["人数占比%"], seg["GMV占比%"])):
    ax.text(a + 0.6, i - h / 2, f"{a:.1f}%", va="center", fontsize=9)
    ax.text(b + 0.6, i + h / 2, f"{b:.1f}%", va="center", fontsize=9)
ax.set_xlim(0, max(seg["人数占比%"].max(), seg["GMV占比%"].max()) + 8)
ax.grid(axis="x", alpha=0.3, linestyle="--")
plt.tight_layout()
fig.savefig(OUTPUT / "q4_rfm.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("已保存 output/q4_rfm.png")

# ---------------- 9. 专题图 ⑥：Q5 转化漏斗 ----------------
fvals = [funnel_sum["view_cnt"], funnel_sum["cart_cnt"],
         funnel_sum["order_cnt"], funnel_sum["pay_cnt"]]
frates = [None] + [fvals[i] / fvals[i - 1] * 100 for i in range(1, 4)]
colors = ["#8172B3", "#937860", "#DA8BC3", "#8C8C8C"]

fig, ax = plt.subplots(figsize=(10.5, 5.5))
cx = 0.5                                    # 漏斗中心线
for i, (st, v, rt) in enumerate(zip(steps, fvals, frates)):
    w = v / fvals[0]
    yi = len(steps) - 1 - i
    ax.barh(yi, w, left=cx - w / 2, height=0.62, color=colors[i], edgecolor="white")
    # 标签统一放右侧，避免窄条上文字被裁切
    ax.text(1.10, yi + 0.13, f"{st}　{v:,}", ha="left", va="center", fontsize=12.5, color="#333333")
    note = "漏斗入口（整体转化 3.82%）" if rt is None else f"环节转化率 {rt:.2f}%"
    ax.text(1.10, yi - 0.17, note, ha="left", va="center", fontsize=10, color="#777777")
ax.set_xlim(-0.3, 1.7)
ax.set_ylim(-0.6, len(steps) - 0.4)
ax.invert_yaxis()
ax.axis("off")
ax.set_title("Q5 转化漏斗：浏览 → 加购 → 下单 → 支付", fontsize=14, fontweight="bold", pad=18)
plt.tight_layout()
fig.savefig(OUTPUT / "q5_funnel.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("已保存 output/q5_funnel.png")

print("\n✅ 看板与 6 张专题图已全部输出到 output/")
