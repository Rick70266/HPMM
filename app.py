# 戰情室 MVP · War Room MVP
# 版本 20261115-1 · 檔案上傳版（商業決策＋促銷＋異常）
# 設計原則：
# 1. 不接資料庫，先吃 RTMM / POS / ERP 撈出來的 Excel / CSV。
# 2. 只上傳銷售日報表就能跑首頁；目標、商品主檔、促銷檔期、庫存四檔是選填，缺了就顯示缺什麼、不會整頁掛掉。
# 3. 所有數字都是示範資料演算結果，上傳真實檔案後會自動取代。請勿把真實公司資料推到公開 repo / 公開 Streamlit Cloud。
# 4. 排名規則：表頭點選排序後，排名永遠從第 1 名開始重算（與寵物好事作品同一規則）。
import io
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

VERSION = "版本 20261115-1 · 戰情室 MVP（檔案上傳版）"
BASE = Path(__file__).parent

st.set_page_config(page_title="戰情室 MVP", page_icon="📊", layout="wide")

# ---------- 欄位對照：中文 / 英文 / RTMM 常見寫法都認 ----------
ALIASES = {
    "date": ["日期", "date", "營業日", "交易日", "銷售日期"],
    "store": ["店別", "店名", "分店", "store", "門市"],
    "dept": ["處別", "處", "部門", "dept", "處/課"],
    "category": ["課別", "課", "類別", "category", "大類", "小類"],
    "sku": ["貨號", "商品貨號", "sku", "商品編號", "品號"],
    "product": ["商品名稱", "品名", "product", "商品名"],
    "sales": ["銷售額", "業績", "營業額", "sales", "銷售金額", "金額"],
    "qty": ["銷售量", "數量", "qty", "銷售數量", "件數"],
    "gross_profit": ["毛利額", "毛利", "gross_profit", "毛利金額"],
    "visitors": ["來客數", "來客", "visitors", "客流", "交易筆數"],
    "target_sales": ["目標金額", "目標", "target_sales", "月目標", "業績目標"],
    "period": ["期間", "月份", "period", "年月"],
    "supplier": ["廠商名稱", "廠商", "supplier"],
    "supplier_no": ["廠商編號", "廠商代號", "supplier_no"],
    "status": ["商品狀態", "狀態", "status"],
    "price": ["售價", "單價", "price"],
    "cost": ["成本", "買價", "cost"],
    "stock_qty": ["庫存量", "庫存", "stock_qty", "庫存數量"],
    "stock_amt": ["庫存金額", "stock_amt"],
    "last_move": ["最後異動日", "最後銷售日", "last_move", "最後異動日期"],
    "promo_id": ["檔期代號", "檔期編號", "promo_id", "促銷檔期"],
    "promo_name": ["檔期名稱", "promo_name", "促銷名稱"],
    "start": ["起日", "促銷起日", "開始日", "start", "起訖起日"],
    "end": ["迄日", "促銷迄日", "結束日", "end", "起訖迄日"],
    "promo_price": ["促銷價", "促銷售價", "promo_price", "價2"],
    "promo_type": ["促銷類別", "類別", "promo_type", "促銷類型"],
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把各種欄位寫法統一成標準英文欄名，認不到的欄位原樣保留。"""
    if df is None or df.empty:
        return df
    rename = {}
    for std, names in ALIASES.items():
        for c in df.columns:
            if str(c).strip() in names and str(c).strip() != std:
                rename[c] = std
                break
    df = df.rename(columns=rename)
    for c in df.columns:
        if isinstance(c, str):
            df = df.rename(columns={c: c.strip()})
    return df


def read_uploaded(file):
    """支援 CSV（utf-8-sig / big5）與 Excel（.xlsx / .xls）。"""
    if file is None:
        return None
    name = file.name.lower()
    try:
        if name.endswith(".csv"):
            raw = file.getvalue()
            for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
                try:
                    return pd.read_csv(io.BytesIO(raw), encoding=enc)
                except Exception:
                    continue
            return pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig", errors="ignore")
        return pd.read_excel(file)
    except Exception as e:
        st.error(f"讀取 {file.name} 失敗：{e}")
        return None


def load_bundled(name: str):
    p = BASE / "sample_data" / name
    if not p.exists():
        return None
    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except Exception:
        return None


def fmt_money(x):
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "—"


def fmt_pct(x):
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "—"


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


# ---------- 側邊欄：資料來源 ----------
st.sidebar.title("📊 戰情室")
st.sidebar.caption(VERSION)
st.sidebar.caption(f"今天：{date.today().isoformat()}")
st.sidebar.divider()

page = st.sidebar.radio(
    "功能選單",
    ["🏠 首頁 · 商業決策", "🎯 促銷管理", "⚠️ 異常管理"],
    index=0,
)

st.sidebar.divider()
st.sidebar.subheader("資料來源")
use_demo = st.sidebar.toggle("使用示範資料", value=True, help="關掉後請在下方上傳檔案。示範資料為虛構數字，僅供測試版面與邏輯。")
st.sidebar.caption("⚠️ 真實公司資料請勿上傳到公開 Streamlit Cloud，先在本機或公司內網跑。")

uploads = {}
if not use_demo:
    uploads["sales"] = st.sidebar.file_uploader("1. 銷售日報表（必填）CSV / Excel", type=["csv", "xlsx", "xls"], key="up_sales")
    uploads["targets"] = st.sidebar.file_uploader("2. 目標表（選填）", type=["csv", "xlsx", "xls"], key="up_targets")
    uploads["products"] = st.sidebar.file_uploader("3. 商品主檔（選填）", type=["csv", "xlsx", "xls"], key="up_products")
    uploads["promo"] = st.sidebar.file_uploader("4. 促銷檔期表（選填）", type=["csv", "xlsx", "xls"], key="up_promo")
    uploads["inventory"] = st.sidebar.file_uploader("5. 庫存表（選填）", type=["csv", "xlsx", "xls"], key="up_inv")
    st.sidebar.info("欄位名稱可用中文或英文，程式會自動對照。範本在 templates 資料夾。")

with st.spinner("載入資料中…"):
    if use_demo:
        sales_raw = load_bundled("sales_daily.csv")
        targets_raw = load_bundled("targets.csv")
        products_raw = load_bundled("products.csv")
        promo_raw = load_bundled("promo.csv")
        inv_raw = load_bundled("inventory.csv")
        source_label = "示範資料（虛構）"
    else:
        sales_raw = read_uploaded(uploads.get("sales"))
        targets_raw = read_uploaded(uploads.get("targets"))
        products_raw = read_uploaded(uploads.get("products"))
        promo_raw = read_uploaded(uploads.get("promo"))
        inv_raw = read_uploaded(uploads.get("inventory"))
        source_label = "上傳檔案"

sales = normalize_columns(sales_raw) if sales_raw is not None else None
targets = normalize_columns(targets_raw) if targets_raw is not None else None
products = normalize_columns(products_raw) if products_raw is not None else None
promo = normalize_columns(promo_raw) if promo_raw is not None else None
inventory = normalize_columns(inv_raw) if inv_raw is not None else None

if sales is None or sales.empty:
    st.error("目前沒有銷售日報表。請開啟左側「使用示範資料」，或上傳銷售日報表（至少要有 日期、店別、銷售額 三欄）。")
    st.info("銷售日報表範本欄位：日期、店別、處別、課別、貨號、商品名稱、銷售額、銷售量、毛利額、來客數。templates 資料夾有空白範本可下載。")
    st.stop()

# 銷售表清理
sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
sales = sales.dropna(subset=["date"])
for col in ("sales", "qty", "gross_profit", "visitors"):
    if col in sales.columns:
        sales[col] = pd.to_numeric(sales[col], errors="coerce").fillna(0)
if "store" not in sales.columns:
    sales["store"] = "全店"
if "dept" not in sales.columns:
    sales["dept"] = "—"
if "category" not in sales.columns:
    sales["category"] = "—"

max_date = sales["date"].max()
min_date = sales["date"].min()
# 以資料最後一天當「今天」，MTD = 當月至今，YTD = 當年至今
mtd_start = max_date.replace(day=1)
ytd_start = max_date.replace(month=1, day=1)
ly_mtd_start = mtd_start - pd.DateOffset(years=1)
ly_mtd_end = max_date - pd.DateOffset(years=1)
ly_ytd_start = ytd_start - pd.DateOffset(years=1)
ly_ytd_end = max_date - pd.DateOffset(years=1)

# ---------- 側邊欄：篩選 ----------
st.sidebar.divider()
st.sidebar.subheader("篩選")
stores_all = sorted(sales["store"].dropna().unique().tolist())
sel_stores = st.sidebar.multiselect("店別", stores_all, default=stores_all)
depts_all = sorted(sales["dept"].dropna().unique().tolist())
sel_depts = st.sidebar.multiselect("處別", depts_all, default=depts_all)
period_mode = st.sidebar.radio("期間", ["月至今 MTD", "年至今 YTD"], index=0, horizontal=True)
if period_mode == "月至今 MTD":
    cur_start, ly_start, ly_end = mtd_start, ly_mtd_start, ly_mtd_end
    period_label = f"{max_date.strftime('%Y/%m')} 月至今（{mtd_start.date()} ~ {max_date.date()}）"
else:
    cur_start, ly_start, ly_end = ytd_start, ly_ytd_start, ly_ytd_end
    period_label = f"{max_date.strftime('%Y')} 年至今（{ytd_start.date()} ~ {max_date.date()}）"

sales_f = sales[sales["store"].isin(sel_stores) & sales["dept"].isin(sel_depts)].copy()
cur = sales_f[(sales_f["date"] >= cur_start) & (sales_f["date"] <= max_date)]
ly = sales_f[(sales_f["date"] >= ly_start) & (sales_f["date"] <= ly_end)]


def agg(df):
    return {
        "sales": float(df["sales"].sum()) if "sales" in df else 0.0,
        "gp": float(df["gross_profit"].sum()) if "gross_profit" in df else 0.0,
        "visitors": float(df["visitors"].sum()) if "visitors" in df else 0.0,
        "qty": float(df["qty"].sum()) if "qty" in df else 0.0,
    }


cur_a, ly_a = agg(cur), agg(ly)
growth = (cur_a["sales"] / ly_a["sales"] - 1) if ly_a["sales"] else None
margin = (cur_a["gp"] / cur_a["sales"]) if cur_a["sales"] else None

# 目標達成率：目標表有 period（YYYY-MM）或店別＋課別時才算
target_amt = None
if targets is not None and not targets.empty and "target_sales" in targets.columns:
    t = targets.copy()
    t["target_sales"] = pd.to_numeric(t["target_sales"], errors="coerce").fillna(0)
    if "store" in t.columns:
        t = t[t["store"].isin(sel_stores)]
    if period_mode == "月至今 MTD" and "period" in t.columns:
        t = t[t["period"].astype(str).str[:7] == max_date.strftime("%Y-%m")]
    elif period_mode == "年至今 YTD" and "period" in t.columns:
        t = t[t["period"].astype(str).str[:4] == max_date.strftime("%Y")]
    # YTD 目標要按月比例折算：已過月數 / 12 太粗糙，MVP 以「當期目標合計 × 已過天數比例」標示為約數
    target_amt = float(t["target_sales"].sum()) if len(t) else None
    if period_mode == "年至今 YTD" and target_amt:
        target_amt = target_amt * (max_date.day_of_year / 365.0)
achievement = (cur_a["sales"] / target_amt) if target_amt else None

st.sidebar.caption(f"資料期間：{min_date.date()} ~ {max_date.date()}")
st.sidebar.caption(f"資料來源：{source_label} · 銷售 {len(sales):,} 筆")

# ============================================================
# 頁 1 · 首頁：商業決策
# ============================================================
if page.startswith("🏠"):
    st.title("🏠 商業決策 · 戰情總覽")
    st.caption(f"{period_label}　｜　篩選：{len(sel_stores)} 間店、{len(sel_depts)} 處　｜　{source_label}")
    if use_demo:
        st.warning("目前為示範資料（虛構數字），僅供測試版面與邏輯。上傳真實銷售日報表後，數字會自動取代。", icon="🧪")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("營業額", fmt_money(cur_a["sales"]), f"去年同期 {fmt_money(ly_a['sales'])}" if ly_a["sales"] else None)
    c2.metric("成長率 YoY", fmt_pct(growth) if growth is not None else "—", "較去年同期" if growth is not None else "無去年資料")
    c3.metric("達成率", fmt_pct(achievement) if achievement is not None else "—", "缺目標表時不顯示" if achievement is None else f"目標約 {fmt_money(target_amt)}")
    c4.metric("毛利率", fmt_pct(margin) if margin is not None else "—", f"毛利額 {fmt_money(cur_a['gp'])}")
    c5.metric("來客數", fmt_money(cur_a["visitors"]), f"客單價 {fmt_money(cur_a['sales'] / cur_a['visitors']) if cur_a['visitors'] else '—'}")

    # 每日趨勢
    st.subheader("每日業績趨勢")
    if not cur.empty:
        daily = cur.groupby("date", as_index=False)["sales"].sum()
        fig = px.line(daily, x="date", y="sales", markers=True, labels={"date": "日期", "sales": "營業額"})
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("此篩選條件下沒有資料。")

    # 店別排行：排序後排名從第 1 名重算
    st.subheader("店別業績排行")
    st.caption("點表頭可排序，排名會跟著重算，第 1 名永遠在最上面。")
    if not cur.empty:
        rank = cur.groupby("store", as_index=False).agg(
            銷售額=("sales", "sum"), 毛利額=("gross_profit", "sum"), 來客數=("visitors", "sum")
        )
        ly_rank = ly.groupby("store", as_index=False).agg(去年銷售額=("sales", "sum")) if not ly.empty else pd.DataFrame(columns=["store", "去年銷售額"])
        rank = rank.merge(ly_rank, on="store", how="left").fillna({"去年銷售額": 0})
        rank["成長率"] = rank.apply(lambda r: (r["銷售額"] / r["去年銷售額"] - 1) if r["去年銷售額"] else None, axis=1)
        rank["毛利率"] = rank.apply(lambda r: (r["毛利額"] / r["銷售額"]) if r["銷售額"] else None, axis=1)
        rank = rank.sort_values("銷售額", ascending=False).reset_index(drop=True)
        rank.insert(0, "排名", range(1, len(rank) + 1))
        rank["達成率"] = None
        if targets is not None and not targets.empty and "target_sales" in targets.columns and "store" in targets.columns:
            tt = targets.copy()
            tt["target_sales"] = pd.to_numeric(tt["target_sales"], errors="coerce").fillna(0)
            if "period" in tt.columns:
                if period_mode == "月至今 MTD":
                    tt = tt[tt["period"].astype(str).str[:7] == max_date.strftime("%Y-%m")]
                else:
                    tt = tt[tt["period"].astype(str).str[:4] == max_date.strftime("%Y")]
            tg = tt.groupby("store", as_index=False)["target_sales"].sum()
            if period_mode == "年至今 YTD":
                tg["target_sales"] = tg["target_sales"] * (max_date.day_of_year / 365.0)
            rank = rank.merge(tg, on="store", how="left")
            rank["達成率"] = rank.apply(lambda r: (r["銷售額"] / r["target_sales"]) if pd.notna(r.get("target_sales")) and r.get("target_sales") else None, axis=1)
            rank = rank.drop(columns=["target_sales"])
        show = rank.copy()
        for col in ("銷售額", "毛利額", "來客數", "去年銷售額"):
            show[col] = show[col].map(fmt_money)
        for col in ("成長率", "毛利率", "達成率"):
            show[col] = show[col].map(lambda v: fmt_pct(v) if pd.notna(v) else "—")
        st.dataframe(show, use_container_width=True, hide_index=True)
        if len(rank) >= 3:
            st.info(f"達成率前三名：{ '、'.join(rank.head(3)['store'].tolist()) }　｜　最後兩名：{ '、'.join(rank.tail(2)['store'].tolist()) }")
        st.download_button("下載店別排行 CSV", to_csv_bytes(rank), "store_ranking.csv", "text/csv")
    else:
        st.info("此篩選條件下沒有資料。")

    # 處／課排行
    st.subheader("處／課業績排行")
    if not cur.empty:
        dept_rank = cur.groupby(["dept", "category"], as_index=False).agg(銷售額=("sales", "sum"), 毛利額=("gross_profit", "sum"))
        dept_rank["毛利率"] = dept_rank.apply(lambda r: (r["毛利額"] / r["銷售額"]) if r["銷售額"] else 0, axis=1)
        dept_rank = dept_rank.sort_values("銷售額", ascending=False).reset_index(drop=True)
        dept_rank.insert(0, "排名", range(1, len(dept_rank) + 1))
        show2 = dept_rank.copy()
        show2["銷售額"] = show2["銷售額"].map(fmt_money)
        show2["毛利額"] = show2["毛利額"].map(fmt_money)
        show2["毛利率"] = show2["毛利率"].map(fmt_pct)
        st.dataframe(show2, use_container_width=True, hide_index=True)

    # 商品 TOP
    st.subheader("商品銷售 TOP 10")
    if "sku" in cur.columns and not cur.empty:
        top = cur.groupby(["sku", "product"], as_index=False).agg(銷售額=("sales", "sum"), 銷售量=("qty", "sum")).sort_values("銷售額", ascending=False).head(10).reset_index(drop=True)
        top.insert(0, "排名", range(1, len(top) + 1))
        show3 = top.copy()
        show3["銷售額"] = show3["銷售額"].map(fmt_money)
        show3["銷售量"] = show3["銷售量"].map(fmt_money)
        st.dataframe(show3, use_container_width=True, hide_index=True)
        fig2 = px.bar(top.sort_values("銷售額"), x="銷售額", y="product", orientation="h", labels={"銷售額": "銷售額", "product": ""})
        fig2.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("銷售表沒有貨號／商品名稱欄位，無法列商品排行。")

    st.divider()
    st.caption("資料品質：銷售表共 " + f"{len(sales):,} 筆，日期 {min_date.date()} ~ {max_date.date()}。目標表" + ("已載入" if targets is not None and not targets.empty else "未上傳，達成率不顯示") + "。")

# ============================================================
# 頁 2 · 促銷管理
# ============================================================
elif page.startswith("🎯"):
    st.title("🎯 促銷管理")
    st.caption(f"{period_label}　｜　{source_label}")
    if promo is None or promo.empty:
        st.warning("尚未上傳促銷檔期表。促銷頁需要「促銷檔期表」才能算促銷業績與檔期重疊。")
        st.info("促銷檔期表範本欄位：檔期代號、檔期名稱、起日、迄日、貨號、促銷價、促銷類別（G 全區域／S 採購建議／L 分店建議）。templates 資料夾有空白範本。")
        st.stop()
    promo = promo.copy()
    for col in ("start", "end"):
        if col in promo.columns:
            promo[col] = pd.to_datetime(promo[col], errors="coerce")
    if "promo_price" in promo.columns:
        promo["promo_price"] = pd.to_numeric(promo["promo_price"], errors="coerce")
    if "sku" not in promo.columns or "start" not in promo.columns or "end" not in promo.columns:
        st.error("促銷檔期表缺少必要欄位：貨號、起日、迄日。")
        st.stop()

    # 促銷業績：銷售日落在任一檔期內、且貨號在該檔期內
    promo_sales_rows = []
    sales_p = sales_f.copy()
    for _, pr in promo.iterrows():
        m = sales_p[(sales_p["date"] >= pr["start"]) & (sales_p["date"] <= pr["end"])]
        if "sku" in m.columns:
            m = m[m["sku"].astype(str) == str(pr["sku"])]
        m = m.copy()
        m["promo_id"] = pr.get("promo_id", "—")
        m["promo_name"] = pr.get("promo_name", "—")
        m["promo_type"] = pr.get("promo_type", "—")
        promo_sales_rows.append(m)
    promo_sales = pd.concat(promo_sales_rows, ignore_index=True) if promo_sales_rows else pd.DataFrame()
    # 當期（MTD/YTD）促銷業績
    promo_cur = promo_sales[(promo_sales["date"] >= cur_start) & (promo_sales["date"] <= max_date)] if not promo_sales.empty else pd.DataFrame()
    promo_amt = float(promo_cur["sales"].sum()) if not promo_cur.empty and "sales" in promo_cur else 0.0
    promo_share = (promo_amt / cur_a["sales"]) if cur_a["sales"] else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("促銷業績（當期）", fmt_money(promo_amt))
    c2.metric("促銷佔比", fmt_pct(promo_share))
    c3.metric("檔期數", str(promo["promo_id"].nunique()) if "promo_id" in promo.columns else str(len(promo)))

    st.subheader("促銷檔期一覽")
    sched = promo.copy()
    sched["起日"] = sched["start"].dt.date.astype(str)
    sched["迄日"] = sched["end"].dt.date.astype(str)
    sched_show = sched.rename(columns={"promo_id": "檔期代號", "promo_name": "檔期名稱", "sku": "貨號", "promo_price": "促銷價", "promo_type": "促銷類別"})
    keep = [c for c in ["檔期代號", "檔期名稱", "起日", "迄日", "貨號", "促銷價", "促銷類別"] if c in sched_show.columns]
    st.dataframe(sched_show[keep], use_container_width=True, hide_index=True)

    st.subheader("各檔期促銷業績")
    if not promo_cur.empty:
        by_promo = promo_cur.groupby(["promo_id", "promo_name"], as_index=False).agg(促銷業績=("sales", "sum"), 銷售量=("qty", "sum")).sort_values("促銷業績", ascending=False)
        show_p = by_promo.copy()
        show_p["促銷業績"] = show_p["促銷業績"].map(fmt_money)
        show_p["銷售量"] = show_p["銷售量"].map(fmt_money)
        st.dataframe(show_p, use_container_width=True, hide_index=True)
        figp = px.bar(by_promo.sort_values("促銷業績"), x="促銷業績", y="promo_name", orientation="h")
        figp.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(figp, use_container_width=True)
    else:
        st.info("當期沒有促銷銷售紀錄，可能是檔期不在 MTD/YTD 期間內，或貨號對不上銷售表。")

    st.subheader("促銷商品 TOP 5")
    if not promo_cur.empty and "product" in promo_cur.columns:
        top5 = promo_cur.groupby(["sku", "product"], as_index=False).agg(促銷業績=("sales", "sum"), 銷售量=("qty", "sum")).sort_values("促銷業績", ascending=False).head(5).reset_index(drop=True)
        top5.insert(0, "排名", range(1, len(top5) + 1))
        show5 = top5.copy()
        show5["促銷業績"] = show5["促銷業績"].map(fmt_money)
        show5["銷售量"] = show5["銷售量"].map(fmt_money)
        st.dataframe(show5, use_container_width=True, hide_index=True)
    else:
        st.info("當期無促銷商品資料。")

    st.subheader("店／課促銷業績統計")
    if not promo_cur.empty:
        by_store = promo_cur.groupby("store", as_index=False).agg(促銷業績=("sales", "sum")).sort_values("促銷業績", ascending=False)
        show_s = by_store.copy()
        show_s["促銷業績"] = show_s["促銷業績"].map(fmt_money)
        st.dataframe(show_s, use_container_width=True, hide_index=True)
    else:
        st.info("當期無資料。")

    st.subheader("⚠️ 檔期重疊檢核（同一貨號）")
    st.caption("RTMM 規則：同一商品檔期重疊時（組合促銷不可重疊），系統以最低價者為生效檔期。以下列出需要人工確認的重疊。")
    overlaps = []
    for sku_val, g in promo.groupby("sku"):
        g = g.sort_values("start")
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                a, b = g.iloc[i], g.iloc[j]
                if pd.notna(a["start"]) and pd.notna(b["start"]) and pd.notna(a["end"]) and b["start"] <= a["end"]:
                    overlaps.append({
                        "貨號": sku_val,
                        "檔期 A": a.get("promo_id", "—"), "檔期 A 起迄": f"{a['start'].date()} ~ {a['end'].date()}",
                        "檔期 B": b.get("promo_id", "—"), "檔期 B 起迄": f"{b['start'].date()} ~ {b['end'].date()}",
                        "A 促銷價": a.get("promo_price"), "B 促銷價": b.get("promo_price"),
                    })
    if overlaps:
        odf = pd.DataFrame(overlaps)
        st.dataframe(odf, use_container_width=True, hide_index=True)
        st.download_button("下載重疊清單 CSV", to_csv_bytes(odf), "promo_overlap.csv", "text/csv")
    else:
        st.success("目前沒有同一貨號檔期重疊。")

# ============================================================
# 頁 3 · 異常管理
# ============================================================
else:
    st.title("⚠️ 異常管理 · 例外清單")
    st.caption(f"{period_label}　｜　{source_label}　｜　先看例外，再看總表。")
    drop_thr = st.slider("業績較去年同期跌幅超過多少算異常", 5, 50, 10, 5, format="%d%%") / 100.0
    st.caption(f"門檻：跌幅 > {drop_thr * 100:.0f}%。呆滯：最後異動 > 90 天；滯銷：31~90 天。門檻可在下一版改成每店自訂。")

    exceptions = []

    # 1. 店別業績大跌
    if not cur.empty and not ly.empty:
        cs = cur.groupby("store", as_index=False)["sales"].sum().rename(columns={"sales": "當期業績"})
        ls = ly.groupby("store", as_index=False)["sales"].sum().rename(columns={"sales": "去年同期"})
        m = cs.merge(ls, on="store", how="left").fillna({"去年同期": 0})
        m["跌幅"] = m.apply(lambda r: (r["當期業績"] / r["去年同期"] - 1) if r["去年同期"] else None, axis=1)
        bad = m[m["跌幅"].notna() & (m["跌幅"] < -drop_thr)].copy()
        if not bad.empty:
            bad["異常類型"] = "店業績大跌"
            bad["說明"] = bad.apply(lambda r: f"較去年同期 {r['跌幅'] * 100:.1f}%", axis=1)
            exceptions.append(bad[["異常類型", "store", "當期業績", "去年同期", "跌幅", "說明"]].rename(columns={"store": "對象"}))
    # 2. 課別業績大跌
    if not cur.empty and not ly.empty:
        cs = cur.groupby(["dept", "category"], as_index=False)["sales"].sum().rename(columns={"sales": "當期業績"})
        ls = ly.groupby(["dept", "category"], as_index=False)["sales"].sum().rename(columns={"sales": "去年同期"})
        m = cs.merge(ls, on=["dept", "category"], how="left").fillna({"去年同期": 0})
        m["跌幅"] = m.apply(lambda r: (r["當期業績"] / r["去年同期"] - 1) if r["去年同期"] else None, axis=1)
        bad = m[m["跌幅"].notna() & (m["跌幅"] < -drop_thr)].copy()
        if not bad.empty:
            bad["異常類型"] = "課業績大跌"
            bad["對象"] = bad["dept"] + " / " + bad["category"]
            bad["說明"] = bad.apply(lambda r: f"較去年同期 {r['跌幅'] * 100:.1f}%", axis=1)
            exceptions.append(bad[["異常類型", "對象", "當期業績", "去年同期", "跌幅", "說明"]])
    # 3. 毛利異常低（課別毛利率 < 10% 且業績 > 0）
    if not cur.empty and "gross_profit" in cur.columns:
        g = cur.groupby(["dept", "category"], as_index=False).agg(銷售額=("sales", "sum"), 毛利額=("gross_profit", "sum"))
        g["毛利率"] = g.apply(lambda r: (r["毛利額"] / r["銷售額"]) if r["銷售額"] else None, axis=1)
        low = g[g["毛利率"].notna() & (g["毛利率"] < 0.10) & (g["銷售額"] > 0)].copy()
        if not low.empty:
            low["異常類型"] = "毛利率偏低（<10%）"
            low["對象"] = low["dept"] + " / " + low["category"]
            low["說明"] = low.apply(lambda r: f"毛利率 {r['毛利率'] * 100:.1f}%，毛利額 {r['毛利額']:,.0f}", axis=1)
            exceptions.append(low[["異常類型", "對象", "銷售額", "毛利額", "毛利率", "說明"]].rename(columns={"銷售額": "當期業績"}))

    # 4. 呆滯 / 滯銷（需要庫存表）
    if inventory is not None and not inventory.empty:
        inv = inventory.copy()
        if "last_move" in inv.columns:
            inv["last_move"] = pd.to_datetime(inv["last_move"], errors="coerce")
            inv["天數"] = (max_date - inv["last_move"]).dt.days
            slow = inv[inv["天數"] > 90].copy()
            stale = inv[(inv["天數"] >= 31) & (inv["天數"] <= 90)].copy()
            if not slow.empty:
                slow["異常類型"] = "呆滯品（>90 天未異動）"
                slow["對象"] = slow["sku"].astype(str) + " " + slow.get("product", pd.Series([""] * len(slow))).astype(str) if "product" in slow.columns else slow["sku"].astype(str)
                if "store" in slow.columns:
                    slow["對象"] = slow["store"].astype(str) + " · " + slow["對象"]
                slow["說明"] = slow.apply(lambda r: f"未異動 {int(r['天數'])} 天，庫存 {r.get('stock_qty', 0):,.0f}", axis=1)
                cols = [c for c in ["異常類型", "對象", "天數", "stock_qty", "stock_amt", "說明"] if c in slow.columns]
                exceptions.append(slow[cols])
            if not stale.empty:
                stale["異常類型"] = "滯銷品（31~90 天未異動）"
                stale["對象"] = stale["sku"].astype(str)
                if "store" in stale.columns:
                    stale["對象"] = stale["store"].astype(str) + " · " + stale["對象"]
                stale["說明"] = stale.apply(lambda r: f"未異動 {int(r['天數'])} 天", axis=1)
                cols = [c for c in ["異常類型", "對象", "天數", "stock_qty", "stock_amt", "說明"] if c in stale.columns]
                exceptions.append(stale[cols])
    else:
        st.info("未上傳庫存表，呆滯／滯銷清單不顯示。庫存表範本欄位：貨號、店別、庫存量、庫存金額、最後異動日。")

    if exceptions:
        all_ex = pd.concat(exceptions, ignore_index=True, sort=False)
        c1, c2 = st.columns(2)
        c1.metric("例外總筆數", str(len(all_ex)))
        c2.metric("異常類型數", str(all_ex["異常類型"].nunique()) if "異常類型" in all_ex else "—")
        st.dataframe(all_ex, use_container_width=True, hide_index=True)
        st.download_button("下載例外清單 CSV", to_csv_bytes(all_ex), "exceptions.csv", "text/csv")
    else:
        st.success("依目前門檻，當期沒有例外事項。")

    st.divider()
    st.subheader("異常參數說明")
    st.markdown("- 店／課業績大跌：當期業績較去年同期跌幅超過門檻（預設 10%）。\n- 毛利率偏低：課別毛利率低於 10% 且有業績。\n- 呆滯品：庫存最後異動超過 90 天；滯銷品：31~90 天。定義沿用 RTMM 訓練文件與寵物好事作品的慣例，下一版可依公司定義調整。")
    st.caption("本頁數字皆為示範資料演算結果，上傳真實檔案後自動取代。")
