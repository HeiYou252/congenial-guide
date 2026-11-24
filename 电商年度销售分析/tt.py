import os, pandas as pd

need = [
    "D:\\实训\\大作业\\production-project\\src\\gen_data.py", "D:\\实训\\大作业\\production-project\\src\\01_quality_check.py", "D:\\实训\\大作业\\production-project\\src\\02_clean.py",
    "D:\\实训\\大作业\\production-project\\src\\03_feature.py", "D:\\实训\\大作业\\production-project\\src\\04_analysis.py", "D:\\实训\\大作业\\production-project\\src\\05_visualize.py",
    "D:\\实训\\大作业\\production-project\\data\\raw\\orders.csv", "D:\\实训\\大作业\\production-project\\data\\raw\\users.csv", "D:\\实训\\大作业\\production-project\\data\\raw\\funnel.csv",
    "D:\\实训\\大作业\\production-project\\data\\processed\\clean_orders.csv", "D:\\实训\\大作业\\production-project\\output\\clean_log.txt",
    "D:\\实训\\大作业\\production-project\\output\\dashboard.png", "D:\\实训\\大作业\\production-project\\report.md",
]
missing = [p for p in need if not os.path.exists(p)]
print("缺失文件:", missing if missing else "无 ✅")

df = pd.read_csv("D:\\实训\\大作业\\production-project\\data\\processed\\clean_orders.csv", encoding="utf-8-sig", parse_dates=["order_date"])
print("清洗后规模:", df.shape)
print("日期范围:", df["order_date"].min().date(), "~", df["order_date"].max().date())
print("GMV（剔除离群）: %.2f 元" % df.loc[(df["status"] == "已完成") & (~df["is_outlier"]), "amount"].sum())