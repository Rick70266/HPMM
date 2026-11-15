"""產生戰情室 MVP 示範資料（虛構數字，僅供測試）。執行：python3 generate_sample_data.py"""
import random
from pathlib import Path
import pandas as pd
import numpy as np

rng = np.random.default_rng(42)
random.seed(42)
BASE = Path(__file__).parent
OUT = BASE / "sample_data"
OUT.mkdir(exist_ok=True)
(BASE / "templates").mkdir(exist_ok=True)

stores = ["文心店", "復中店", "公益店", "水湳店", "忠明店", "八德店"]
store_mult = {"文心店": 1.35, "復中店": 1.10, "公益店": 1.05, "水湳店": 0.95, "忠明店": 0.85, "八德店": 1.00}
cats = {
    ("食品處", "飲料"): 320, ("食品處", "零食"): 280, ("食品處", "生鮮"): 520,
    ("日用品處", "清潔"): 240, ("日用品處", "紙品"): 180,
    ("家電處", "小家電"): 850, ("家電處", "大家電"): 4200,
    ("服飾處", "男裝"): 680, ("服飾處", "女裝"): 720,
}
products = []
pid = 1
for (dept, cat), price in cats.items():
    for i in range(4):
        products.append({
            "貨號": f"SKU{pid:04d}", "商品名稱": f"{cat}商品{chr(65+i)}-{pid}",
            "處別": dept, "課別": cat, "廠商名稱": f"廠商{pid%6+1}",
            "廠商編號": f"V{pid%6+1:03d}", "商品狀態": "正常",
            "售價": price + rng.integers(-40, 80), "成本": int(price * 0.68),
        })
        pid += 1
prod_df = pd.DataFrame(products)
prod_df.to_csv(OUT / "products.csv", index=False, encoding="utf-8-sig")

# 銷售日報：2025-01-01 ~ 2026-11-14，逐日逐店逐商品（機率性出單）
dates = pd.date_range("2025-01-01", "2026-11-14")
rows = []
for d in dates:
    year_growth = 1.08 if d.year == 2026 else 1.0
    seasonal = 1.15 if d.month in (11, 12, 1, 2) else 1.0
    weekend = 1.25 if d.weekday() >= 5 else 1.0
    for store in stores:
        # 忠明店 2026-10 起下滑，觸發異常清單
        decline = 0.70 if (store == "忠明店" and d >= pd.Timestamp("2026-10-01")) else 1.0
        for _, p in prod_df.iterrows():
            if rng.random() > 0.45:
                continue
            qty = int(rng.integers(1, 12) * weekend)
            price = float(p["售價"])
            sales = qty * price * store_mult[store] * year_growth * seasonal * decline
            # 家電毛利較低、服飾女裝毛利較低，觸發毛利異常示範
            margin_rate = 0.08 if p["課別"] in ("大家電", "女裝") else rng.uniform(0.22, 0.35)
            rows.append({
                "日期": d.strftime("%Y-%m-%d"), "店別": store, "處別": p["處別"], "課別": p["課別"],
                "貨號": p["貨號"], "商品名稱": p["商品名稱"],
                "銷售額": round(sales), "銷售量": qty,
                "毛利額": round(sales * margin_rate),
                "來客數": int(qty * rng.uniform(0.6, 1.0)),
            })
sales_df = pd.DataFrame(rows)
sales_df.to_csv(OUT / "sales_daily.csv", index=False, encoding="utf-8-sig")
print(f"sales_daily: {len(sales_df)} rows, {sales_df['日期'].min()} ~ {sales_df['日期'].max()}, total {sales_df['銷售額'].sum():,.0f}")

# 目標表：每月每店
trows = []
for ym in pd.period_range("2025-01", "2026-11", freq="M"):
    for store in stores:
        base = sales_df[(sales_df["日期"].str[:7] == str(ym)) & (sales_df["店別"] == store)]["銷售額"].sum()
        if base == 0:
            base = 2_800_000 * store_mult[store]
        trows.append({"期間": str(ym), "店別": store, "目標金額": round(base * 1.05)})
pd.DataFrame(trows).to_csv(OUT / "targets.csv", index=False, encoding="utf-8-sig")

# 促銷檔期：含一組刻意重疊（SKU0001 同時在兩個檔期）
promo = pd.DataFrame([
    {"檔期代號": "P20261101", "檔期名稱": "雙11暖身檔", "起日": "2026-11-01", "迄日": "2026-11-11", "貨號": "SKU0001", "促銷價": 259, "促銷類別": "G"},
    {"檔期代號": "P20261101", "檔期名稱": "雙11暖身檔", "起日": "2026-11-01", "迄日": "2026-11-11", "貨號": "SKU0002", "促銷價": 229, "促銷類別": "G"},
    {"檔期代號": "P20261101", "檔期名稱": "雙11暖身檔", "起日": "2026-11-01", "迄日": "2026-11-11", "貨號": "SKU0010", "促銷價": 189, "促銷類別": "S"},
    {"檔期代號": "P20261105", "檔期名稱": "會員日加碼", "起日": "2026-11-05", "迄日": "2026-11-14", "貨號": "SKU0001", "促銷價": 239, "促銷類別": "L"},
    {"檔期代號": "P20261105", "檔期名稱": "會員日加碼", "起日": "2026-11-05", "迄日": "2026-11-14", "貨號": "SKU0020", "促銷價": 699, "促銷類別": "L"},
    {"檔期代號": "P20261001", "檔期名稱": "十月慶檔", "起日": "2026-10-01", "迄日": "2026-10-14", "貨號": "SKU0003", "促銷價": 269, "促銷類別": "G"},
])
promo.to_csv(OUT / "promo.csv", index=False, encoding="utf-8-sig")

# 庫存表：每店每商品，最後異動日分佈（部分呆滯/滯銷）
maxd = pd.Timestamp("2026-11-14")
irows = []
for store in stores:
    for _, p in prod_df.iterrows():
        r = rng.random()
        if r < 0.08:
            last = maxd - pd.Timedelta(days=int(rng.integers(95, 180)))  # 呆滯
        elif r < 0.20:
            last = maxd - pd.Timedelta(days=int(rng.integers(31, 90)))  # 滯銷
        else:
            last = maxd - pd.Timedelta(days=int(rng.integers(0, 30)))
        qty = int(rng.integers(0, 120))
        irows.append({
            "貨號": p["貨號"], "商品名稱": p["商品名稱"], "店別": store,
            "庫存量": qty, "庫存金額": qty * int(p["成本"]),
            "最後異動日": last.strftime("%Y-%m-%d"),
        })
pd.DataFrame(irows).to_csv(OUT / "inventory.csv", index=False, encoding="utf-8-sig")

# 空白範本（只有表頭）
for name, cols in {
    "sales_daily_template.csv": ["日期", "店別", "處別", "課別", "貨號", "商品名稱", "銷售額", "銷售量", "毛利額", "來客數"],
    "targets_template.csv": ["期間", "店別", "目標金額"],
    "products_template.csv": ["貨號", "商品名稱", "處別", "課別", "廠商名稱", "廠商編號", "商品狀態", "售價", "成本"],
    "promo_template.csv": ["檔期代號", "檔期名稱", "起日", "迄日", "貨號", "促銷價", "促銷類別"],
    "inventory_template.csv": ["貨號", "商品名稱", "店別", "庫存量", "庫存金額", "最後異動日"],
}.items():
    pd.DataFrame(columns=cols).to_csv(BASE / "templates" / name, index=False, encoding="utf-8-sig")
print("done")
