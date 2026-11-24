# -*- coding: utf-8 -*-
"""
04_analysis.py —— 第 41 课：六大业务问题分析（Q1~Q6）

作用
----
在统一口径下回答运营总监提的 6 个问题，每个问题输出"数据表 + 一句话结论"：

    Q1 全年走势与季节性      月度 GMV、订单量、环比（resample('ME') + pct_change）
    Q2 品类增长引擎与拖累项  品类 GMV、占比、客单价、下半年增速
    Q3 区域差异与问题区域    区域×品类 GMV、客单价、复购率
    Q4 客户分层（RFM）       R/F/M 五分位打分 + 8 类客户 + 人数/GMV 贡献
    Q5 转化漏斗              浏览→加购→下单→支付 逐级转化率
    Q6 价格与销量关系        单价与件数的皮尔逊相关系数（分品类）

统一口径：status='已完成' 且 is_outlier=False（3845 笔）；同时打印含离群口径，
用于报告里的敏感性说明。结果同时保存到 output/analysis_summary.txt。

运行
----
    python src/04_analysis.py
"""

import contextlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
OUTPUT = BASE / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)


class Tee:
    """把 print 同时写到控制台和文件"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)

    def flush(self):
        for st in self.streams:
            st.flush()


def main():
    df = pd.read_csv(PROCESSED / "clean_orders.csv",
                     encoding="utf-8-sig", parse_dates=["order_date"])

    # ---------------- 41.0 统一分析口径 ----------------
    paid_all = df[df["status"] == "已完成"]
    paid = paid_all[~paid_all["is_outlier"]].copy()
    paid["month"] = paid["order_date"].dt.month

    print("=" * 78)
    print("统一分析口径（每次分析前先看这一段）")
    print("=" * 78)
    print("已完成订单（含离群）: %d 笔, GMV %.2f 元" % (len(paid_all), paid_all["amount"].sum()))
    print("剔除离群后分析样本: %d 笔, GMV %.2f 元" % (len(paid), paid["amount"].sum()))
    print("客单价: %.2f 元" % (paid["amount"].sum() / len(paid)))
    print("\n⚠️ 本报告采用「剔除离群」口径；含离群口径见上一行，差异来自已完成订单中的 "
          "%d 笔离群订单（全表共 %d 笔）。"
          % (int(paid_all["is_outlier"].sum()), int(df["is_outlier"].sum())))

    # ---------------- Q1 全年走势与季节性 ----------------
    print("\n" + "=" * 78)
    print("Q1 全年走势与季节性")
    print("=" * 78)
    try:
        m = paid.set_index("order_date").resample("ME").agg(
            GMV=("amount", "sum"),
            订单量=("order_id", "count"),
        )
    except ValueError:                       # 旧版 pandas 只认 "M"
        m = paid.set_index("order_date").resample("M").agg(
            GMV=("amount", "sum"),
            订单量=("order_id", "count"),
        )
    m["环比%"] = (m["GMV"].pct_change() * 100).round(2)
    m["GMV_万元"] = (m["GMV"] / 10000).round(2)
    print(m[["GMV_万元", "订单量", "环比%"]].to_string())
    print("峰值月:", int(m["GMV"].idxmax().month), " 谷值月:", int(m["GMV"].idxmin().month))

    h1 = paid[paid["month"] <= 6]["amount"].sum()
    h2 = paid[paid["month"] > 6]["amount"].sum()
    h1_wan, h2_wan = round(h1 / 10000, 2), round(h2 / 10000, 2)
    h2_growth = (h2_wan - h1_wan) / h1_wan * 100      # 用万元口径计算，和报告口径一致

    # ---------------- Q2 品类 ----------------
    print("\n" + "=" * 78)
    print("Q2 品类增长引擎与拖累项")
    print("=" * 78)
    g = paid.groupby("category").agg(
        GMV=("amount", "sum"),
        订单量=("order_id", "count"),
    )
    g["客单价"] = (g["GMV"] / g["订单量"]).round(2)
    g["GMV占比%"] = (g["GMV"] / g["GMV"].sum() * 100).round(2)

    # 用上下半年对比代替同比（本数据只有 2025 年）
    ch1 = paid[paid["month"] <= 6].groupby("category")["amount"].sum()
    ch2 = paid[paid["month"] > 6].groupby("category")["amount"].sum()
    g["下半年增速%"] = ((ch2 - ch1) / ch1 * 100).round(2)
    g["GMV_万元"] = (g["GMV"] / 10000).round(2)

    print(g[["GMV_万元", "订单量", "客单价", "GMV占比%", "下半年增速%"]]
          .sort_values("GMV_万元", ascending=False).to_string())

    # ---------------- Q3 区域 ----------------
    print("\n" + "=" * 78)
    print("Q3 区域差异与问题区域")
    print("=" * 78)
    pivot = pd.pivot_table(paid, index="region", columns="category",
                           values="amount", aggfunc="sum", fill_value=0)
    print("区域 × 品类 GMV（万元）：")
    print((pivot / 10000).round(2).to_string())

    r = paid.groupby("region").agg(
        GMV=("amount", "sum"),
        订单量=("order_id", "count"),
        用户数=("user_id", "nunique"),
    )
    r["客单价"] = (r["GMV"] / r["订单量"]).round(2)
    r["GMV占比%"] = (r["GMV"] / r["GMV"].sum() * 100).round(2)

    buy_cnt = paid.groupby(["region", "user_id"])["order_id"].count()
    r["复购率%"] = (buy_cnt.groupby(level="region")
                  .apply(lambda s: (s >= 2).mean() * 100).round(2))
    r["GMV_万元"] = (r["GMV"] / 10000).round(2)

    print("\n区域汇总：")
    print(r[["GMV_万元", "订单量", "客单价", "GMV占比%", "复购率%"]]
          .sort_values("GMV_万元", ascending=False).to_string())

    # ---------------- Q4 RFM 客户分层 ----------------
    print("\n" + "=" * 78)
    print("Q4 RFM 客户分层")
    print("=" * 78)
    snapshot = paid["order_date"].max() + pd.Timedelta(days=1)   # 观察日 = 最后一天 + 1

    rfm = paid.groupby("user_id").agg(
        最后购买=("order_date", "max"),
        频次=("order_id", "count"),
        金额=("amount", "sum"),
    )
    rfm["R"] = (snapshot - rfm["最后购买"]).dt.days
    print("观察日:", snapshot.date())
    print(rfm[["最后购买", "R", "频次", "金额"]].head(3).to_string())

    rfm["R分"] = pd.qcut(rfm["R"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F分"] = pd.qcut(rfm["频次"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M分"] = pd.qcut(rfm["金额"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["RFM总分"] = rfm["R分"] + rfm["F分"] + rfm["M分"]

    def segment(row):
        rr, ff, mm = row["R分"], row["F分"], row["M分"]
        if rr >= 4 and ff >= 4 and mm >= 4:
            return "重要价值客户"      # 最近买、买得多、花得多
        if rr < 4 and ff >= 4 and mm >= 4:
            return "重要保持客户"      # 以前很铁，最近没来
        if rr >= 4 and ff < 4 and mm >= 4:
            return "重要发展客户"      # 金额高但频次低
        if rr < 4 and ff < 4 and mm >= 4:
            return "重要挽留客户"      # 花得多但快流失
        if rr >= 4 and ff >= 4 and mm < 4:
            return "一般价值客户"
        if rr < 4 and ff >= 4 and mm < 4:
            return "一般保持客户"
        if rr >= 4 and ff < 4 and mm < 4:
            return "一般发展客户"
        return "流失预警客户"

    rfm["客户类型"] = rfm.apply(segment, axis=1)

    seg = rfm.groupby("客户类型").agg(人数=("R", "count"), 总金额=("金额", "sum"))
    seg["人数占比%"] = (seg["人数"] / len(rfm) * 100).round(2)
    seg["GMV占比%"] = (seg["总金额"] / rfm["金额"].sum() * 100).round(2)
    seg["人均消费"] = (seg["总金额"] / seg["人数"]).round(2)

    print("\n客户分层：")
    print(seg.sort_values("GMV占比%", ascending=False).to_string())
    print("购买用户数:", len(rfm))

    # ---------------- Q5 转化漏斗 ----------------
    print("\n" + "=" * 78)
    print("Q5 转化漏斗")
    print("=" * 78)
    funnel = pd.read_csv(RAW / "funnel.csv", encoding="utf-8-sig", parse_dates=["date"])
    tot = funnel[["view_cnt", "cart_cnt", "order_cnt", "pay_cnt"]].sum()
    print(tot.to_string())

    steps = ["浏览", "加购", "下单", "支付"]
    vals = tot.values
    for i in range(1, 4):
        print(f"{steps[i - 1]}→{steps[i]} 转化率: {vals[i] / vals[i - 1] * 100:.2f}%")
    print(f"整体转化率: {vals[3] / vals[0] * 100:.2f}%")

    # ---------------- Q6 价格与销量 ----------------
    print("\n" + "=" * 78)
    print("Q6 价格与销量的关系（相关系数）")
    print("=" * 78)
    r_all = paid["unit_price"].corr(paid["quantity"])
    print("整体相关系数 r = %.3f" % r_all)
    r_by_cat = {}
    for c, sub in paid.groupby("category"):
        r_by_cat[c] = sub["unit_price"].corr(sub["quantity"])
        print(f"{c}: r = {r_by_cat[c]:.3f}  (n={len(sub)})")

    # ---------------- 41.7 六大结论速览 ----------------
    peak_month = int(m["GMV"].idxmax().month)
    peak_gmv = m["GMV"].max() / 10000
    peak_mom = m["环比%"].loc[m["GMV"].idxmax()]
    trough_month = int(m["GMV"].idxmin().month)
    trough_gmv = m["GMV"].min() / 10000

    top_cat = g["GMV"].idxmax()
    top_share = g.loc[top_cat, "GMV占比%"]
    top_growth = g.loc[top_cat, "下半年增速%"]
    worst_cat = g["下半年增速%"].idxmin()
    worst_growth = g.loc[worst_cat, "下半年增速%"]

    top_region = r["GMV"].idxmax()
    top_r_share = r.loc[top_region, "GMV占比%"]
    top_r_rep = r.loc[top_region, "复购率%"]
    weak_region = r["复购率%"].idxmin()
    weak_share = r.loc[weak_region, "GMV占比%"]
    weak_rep = r.loc[weak_region, "复购率%"]
    weak_aov = r.loc[weak_region, "客单价"]

    vip_share = seg.loc["重要价值客户", "GMV占比%"]
    vip_cnt_share = seg.loc["重要价值客户", "人数占比%"]
    churn_n = int(seg.loc["流失预警客户", "人数"])
    churn_cnt_share = seg.loc["流失预警客户", "人数占比%"]
    churn_gmv_share = seg.loc["流失预警客户", "GMV占比%"]

    print("\n" + "=" * 78)
    print("41.7 六大结论速览（报告核心页）")
    print("=" * 78)
    print(f"Q1 走势：{peak_month} 月 GMV {peak_gmv:.2f} 万元（环比 {peak_mom:+.2f}%）为峰值，"
          f"{trough_month} 月 {trough_gmv:.2f} 万元为谷值；下半年比上半年 {h2_growth:+.2f}%")
    print(f"Q2 品类：{top_cat} GMV 占 {top_share:.2f}%、增速 {top_growth:+.2f}%，是第一引擎；"
          f"{worst_cat} {worst_growth:+.2f}% 为唯一下滑")
    print(f"Q3 区域：{top_region} 占 {top_r_share:.2f}% 且复购率 {top_r_rep:.2f}%；"
          f"{weak_region} GMV 占 {weak_share:.2f}%、客单价 {weak_aov:.2f} 元、复购率 {weak_rep:.2f}%，"
          f"属三重短板")
    print(f"Q4 客户：重要价值客户 {vip_cnt_share:.2f}% 贡献 {vip_share:.2f}% GMV；"
          f"流失预警 {churn_n} 人（{churn_cnt_share:.2f}%）仅贡献 {churn_gmv_share:.2f}%")
    print(f"Q5 漏斗：浏览→加购仅 {vals[1] / vals[0] * 100:.2f}%，是最大瓶颈；"
          f"整体转化 {vals[3] / vals[0] * 100:.2f}%")
    print(f"Q6 价格：服饰 r={r_by_cat['服饰']:.3f}、食品 r={r_by_cat['食品']:.3f} 强负相关；"
          f"家居/美妆接近 0（相关≠因果）")


if __name__ == "__main__":
    summary = OUTPUT / "analysis_summary.txt"
    with open(summary, "w", encoding="utf-8") as f:
        with contextlib.redirect_stdout(Tee(sys.stdout, f)):
            main()
    print(f"\n✅ 分析结果已写入 {summary}")
