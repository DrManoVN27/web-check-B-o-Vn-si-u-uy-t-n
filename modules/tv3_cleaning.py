"""
============================================================
THÀNH VIÊN 3 - LÀM SẠCH DỮ LIỆU (12 bước pipeline + import MySQL)
============================================================
Đây là code GỐC của TV3 (file data_cleaning_pipeline.py), giữ
NGUYÊN VẸN 100% logic xử lý 12 bước (khảo sát, xóa trùng, fill
missing bằng TF-IDF, chuẩn hóa kiểu/định dạng, IQR outlier,
scaling, encoding...) — chỉ bọc thêm hàm clean_data(df) ở cuối
để Web App (app.py) gọi qua nút bấm.

Hàm import_to_mysql() (đẩy data sạch vào bảng "news") cũng được
giữ nguyên ở đây — TV2 (tv2_database.py) sẽ gọi sang hàm này khi
bấm nút "Đẩy vào MySQL", để tránh viết trùng logic đẩy DB.
============================================================
"""

import os
import re
import warnings
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler, LabelEncoder

warnings.filterwarnings("ignore")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RAW_PATH = os.path.join(DATA_DIR, "raw_news.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "cleaned_news.csv")

COLS = {"title": ["title", "tieu_de"], "publish_date": ["publish_date", "ngay_dang"],
        "author": ["author", "tac_gia"], "content": ["content", "noi_dung"],
        "comments": ["comments", "so_binh_luan"], "source": ["source", "nguon"],
        "url": ["url", "link"]}


def C(df, k):
    return next((c for c in COLS.get(k, []) if c in df.columns), None)


# report được tạo mới mỗi lần gọi clean_data() để tránh cộng dồn
# giữa nhiều lần chạy (khác bản gốc dùng biến toàn cục report)
def _new_report(rows_before):
    return {"rows_before": rows_before, "deleted": 0, "filled": 0, "issues": [],
            "normalized": [], "encoded": [], "scaled": []}


# ── BƯỚC 1: KHẢO SÁT ─────────────────────────────────────────
def step1_survey(df, report):
    print("=" * 55, "\n  BƯỚC 1: KHẢO SÁT\n" + "=" * 55)
    print(f"Kích thước : {df.shape}")
    print(f"Các cột    : {df.columns.tolist()}")
    print(f"Kiểu DL    :\n{df.dtypes}")
    miss = df.isnull().sum()
    miss = miss[miss > 0]
    print(f"Giá trị thiếu:\n{miss if len(miss) else '  Không có'}")
    print(f"Dòng trùng : {df.duplicated().sum()}")
    for c in df.select_dtypes("object").columns:
        print(f"  [{c}] {df[c].nunique()} unique | vd: {df[c].dropna().unique()[:3].tolist()}")


# ── BƯỚC 2: XÓA TRÙNG ────────────────────────────────────────
def step2_dedup(df, report):
    b = len(df)
    df = df.drop_duplicates()
    url = C(df, "url")
    if url:
        df = df.drop_duplicates(subset=[url], keep="first")
    d = b - len(df)
    report["deleted"] += d
    print(f"\n✅ Bước 2 | Xóa trùng: -{d} dòng → còn {len(df)}")
    return df.reset_index(drop=True)


# ── BƯỚC 3: XỬ LÝ THIẾU ─────────────────────────────────────
def _tfidf_fill(df, key, cols, report, thr=0.2):
    if key not in df.columns:
        return df
    df = df.reset_index(drop=True)
    mat = TfidfVectorizer(min_df=1, ngram_range=(1, 2)).fit_transform(
        df[key].fillna("").astype(str))
    for col in [c for c in cols if c in df.columns]:
        null_pos = df[df[col].isnull()].index.tolist()
        filled = 0
        for i in null_pos:
            sc = cosine_similarity(mat[i], mat).flatten()
            sc[i] = 0
            for j in np.argsort(sc)[::-1]:
                if sc[j] < thr:
                    break
                v = df.iloc[j][col]
                if v and str(v).strip() not in ["", "nan", "None", "NULL"]:
                    df.iloc[i, df.columns.get_loc(col)] = v
                    filled += 1
                    break
        report["filled"] += filled
        print(f"   [{col}] TF-IDF fill {filled}/{len(null_pos)}")
    return df


def step3_missing(df, report):
    for c in df.columns:
        df[c] = df[c].replace({"nan": np.nan, "None": np.nan, "NULL": np.nan, "": np.nan})
    critical = [c for c in [C(df, "title"), C(df, "content")] if c]
    b = len(df)
    df = df.dropna(subset=critical).reset_index(drop=True)
    d = b - len(df)
    report["deleted"] += d
    print(f"\n✅ Bước 3 | Thiếu title/content: -{d} dòng")
    df = _tfidf_fill(df, C(df, "title") or "",
                      [c for c in [C(df, "author"), C(df, "source")] if c], report)
    for k, default in [("author", "Không rõ tác giả"), ("source", "Không rõ nguồn")]:
        col = C(df, k)
        if col:
            n = df[col].isnull().sum()
            if n:
                mv = df[col].mode()
                fv = mv[0] if len(mv) else default
                df[col].fillna(fv, inplace=True)
                report["filled"] += n
                print(f"   [{col}] Fallback mode: fill {n} ô → '{fv}'")
    for k, fn in [("comments", lambda s: int(pd.to_numeric(s, errors="coerce").median() or 0)),
                  ("publish_date", lambda _: pd.Timestamp.today().strftime("%Y-%m-%d"))]:
        col = C(df, k)
        if col:
            n = df[col].isnull().sum()
            if n:
                df[col].fillna(fn(df[col]), inplace=True)
                report["filled"] += n
                print(f"   [{col}] Fill {n} ô rỗng")
    df = df.dropna(how="all").reset_index(drop=True)
    return df


# ── BƯỚC 4: CHUẨN HÓA KIỂU ──────────────────────────────────
def step4_dtypes(df, report):
    col = C(df, "comments")
    if col:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        report["normalized"].append(col)
    for k in ["author", "source"]:
        col = C(df, k)
        if col:
            df[col] = df[col].astype("category")
            report["normalized"].append(col)
    print(f"\n✅ Bước 4 | Chuẩn hóa kiểu: {report['normalized']}")
    return df


# ── BƯỚC 5: CHUẨN HÓA ĐỊNH DẠNG ─────────────────────────────
def step5_formats(df, report):
    col = C(df, "publish_date")
    if col:
        def to_date(x):
            if pd.isnull(x):
                return None
            s = str(x).strip()
            m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
            if m:
                d, mo, y = m.groups()
                return f"{y}-{int(mo):02d}-{int(d):02d}"
            m2 = re.search(r"(\d{4}-\d{2}-\d{2})", s)
            if m2:
                return m2.group(0)
            return None
        df[col] = df[col].apply(to_date)
    for c in [c for c in [C(df, "title"), C(df, "author"), C(df, "source")] if c]:
        df[c] = df[c].astype(str).str.strip().replace(
            {"None": np.nan, "nan": np.nan, "": np.nan}).fillna("Không xác định")
        df[c] = df[c].str.title()
    cc = C(df, "comments")
    if cc:
        def parse_unit(v):
            s = str(v).strip().upper()
            try:
                if s.endswith("K"):
                    return float(s[:-1]) * 1000
                if s.endswith("M"):
                    return float(s[:-1]) * 1e6
                return float(s)
            except Exception:
                return np.nan
        df[cc] = df[cc].apply(parse_unit)
    print(f"\n✅ Bước 5 | Chuẩn hóa định dạng ngày, text, đơn vị K/M")
    return df


# ── BƯỚC 6: DỮ LIỆU SAI THUỘC TÍNH ─────────────────────────
def step6_invalid(df, report):
    cc = C(df, "comments")
    if cc:
        df[cc] = pd.to_numeric(df[cc], errors="coerce")
        n = (df[cc] < 0).sum()
        if n:
            df.loc[df[cc] < 0, cc] = 0
            report["issues"].append(f"{cc}: {n} giá trị âm→0")
    uc = C(df, "url")
    if uc:
        bad = ~df[uc].astype(str).str.match(r"^https?://") & df[uc].notna()
        n = bad.sum()
        if n:
            df.loc[bad, uc] = np.nan
            report["issues"].append(f"{uc}: {n} URL sai→NaN")
    dc = C(df, "publish_date")
    if dc:
        df[dc] = pd.to_datetime(df[dc], format="%Y-%m-%d", errors="coerce")
        report["normalized"].append(dc)
        fut = df[dc] > pd.Timestamp.today()
        n = fut.sum()
        if n:
            df.loc[fut, dc] = np.nan
            report["issues"].append(f"{dc}: {n} ngày tương lai→NaN")
    print(f"\n✅ Bước 6 | Sai thuộc tính: {report['issues'] or 'Không phát hiện vấn đề'}")
    return df


# ── BƯỚC 7: NGOẠI LAI IQR ────────────────────────────────────
def step7_outliers(df, report, factor=1.5):
    print(f"\n✅ Bước 7 | Ngoại lai (IQR factor={factor}):")
    for col in df.select_dtypes(include=np.number).columns:
        q1, q3 = df[col].quantile(.25), df[col].quantile(.75)
        iqr = q3 - q1
        lo, hi = q1 - factor * iqr, q3 + factor * iqr
        n = ((df[col] < lo) | (df[col] > hi)).sum()
        df[col] = df[col].clip(lo, hi)
        print(f"   [{col}] {n} ngoại lai → clip [{lo:.1f}, {hi:.1f}]")
    return df


# ── BƯỚC 8: MELT ─────────────────────────────────────────────
def step8_melt(df, report):
    wide = [c for c in df.columns if re.match(
        r".+_(jan|feb|mar|q[1-4]|\d{4}|\d{1,2})$", c, re.I)]
    if wide:
        id_vars = [c for c in df.columns if c not in wide]
        df = pd.melt(df, id_vars=id_vars, value_vars=wide,
                     var_name="metric_name", value_name="metric_value")
        print(f"\n✅ Bước 8 | melt() áp dụng: {len(wide)} cột wide → {df.shape}")
    else:
        print(f"\n✅ Bước 8 | Dataset dạng LONG → không cần melt()")
    return df


# ── BƯỚC 9: SCALING ──────────────────────────────────────────
def step9_scale(df, report):
    cols = [c for c in df.select_dtypes(np.number).columns if c.lower() != "id"]
    if not cols:
        print(f"\n✅ Bước 9 | Không có cột số để scale")
        return df
    df[cols] = df[cols].fillna(df[cols].median())
    sc = MinMaxScaler()
    for c in cols:
        df[c + "_scaled"] = sc.fit_transform(df[[c]])
        report["scaled"].append(c)
    print(f"\n✅ Bước 9 | MinMaxScaler → {cols}")
    return df


# ── BƯỚC 10: ENCODING ────────────────────────────────────────
def step10_encode(df, report):
    sc = C(df, "source")
    if sc:
        le = LabelEncoder()
        df[sc + "_encoded"] = le.fit_transform(df[sc].astype(str))
        report["encoded"].append(sc)
        print(f"\n✅ Bước 10 | [{sc}] Label Encoding (nhiều giá trị)")
    ac = C(df, "author")
    if ac:
        n = df[ac].nunique()
        if n <= 50:
            df = pd.concat([df, pd.get_dummies(df[ac].astype(str), prefix="author", drop_first=True)], axis=1)
            print(f"   [{ac}] One-Hot ({n}≤50 giá trị)")
        else:
            le2 = LabelEncoder()
            df[ac + "_encoded"] = le2.fit_transform(df[ac].astype(str))
            print(f"   [{ac}] Label Encoding ({n}>50 giá trị)")
        report["encoded"].append(ac)
    return df


# ── BƯỚC 11: CÂN BẰNG DỮ LIỆU ───────────────────────────────
def step11_balance(df, report):
    print(f"\n✅ Bước 11 | Không có cột nhãn phân loại → không dùng SMOTE/class_weight")
    sc = C(df, "source")
    if sc:
        print(f"   Phân phối nguồn:\n{df[sc].value_counts().to_string()}")
    return df


# ── BƯỚC 12: LƯU + BÁO CÁO ──────────────────────────────────
def step12_save(df, report, out_path=OUTPUT_PATH):
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n{'='*55}")
    print(f"  BÁO CÁO CUỐI")
    print(f"{'='*55}")
    print(f"  Gốc  : {report['rows_before']} dòng")
    print(f"  Sau  : {df.shape[0]} dòng x {df.shape[1]} cột")
    print(f"  Xóa  : {report['deleted']} dòng")
    print(f"  Fill : {report['filled']} ô")
    print(f"  Vấn đề: {report['issues'] or 'Không có'}")
    print(f"  Chuẩn hóa : {report['normalized']}")
    print(f"  Mã hóa    : {report['encoded']}")
    print(f"  Scale     : {report['scaled']}")
    print(f"  File lưu  : {out_path}")


# ── IMPORT MYSQL (logic gốc của TV3, TV2 sẽ gọi sang hàm này) ──
def import_to_mysql(df):
    import mysql.connector
    conn = mysql.connector.connect(host="localhost", user="root",
                                    password="09112007", database="news_db")
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("TRUNCATE TABLE keywords")
    cur.execute("TRUNCATE TABLE news")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    for _, r in df.iterrows():
        try:
            cm = int(float(r.get(C(df, "comments"), 0)))
        except Exception:
            cm = 0
        raw_date = r.get(C(df, "publish_date"), "")
        if pd.isnull(raw_date):
            date_val = None
        else:
            date_val = str(raw_date)[:10]
        cur.execute(
            "INSERT INTO news(title,publish_date,author,content,comments,source,url)"
            " VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (
                str(r.get(C(df, "title"), ""))[:500],
                date_val,
                str(r.get(C(df, "author"), ""))[:100],
                str(r.get(C(df, "content"), "")),
                cm,
                str(r.get(C(df, "source"), ""))[:50],
                str(r.get(C(df, "url"), ""))[:500],
            ),
        )
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Import {len(df)} dòng vào MySQL xong!")


# ─────────────────────────────────────────────
# HÀM VỎ — để app.py / main.py gọi được
# ─────────────────────────────────────────────

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hàm vỏ để Web App gọi ở Bước 3 (Làm sạch & NLP).

    Bên trong chạy đúng 12 bước pipeline gốc của TV3
    (step1_survey ... step12_save), KHÔNG đổi logic xử lý.

    Args:
        df: DataFrame thô (từ TV1, cột: nguon, tieu_de, ngay_dang,
            tac_gia, noi_dung, so_binh_luan, link)

    Returns:
        pd.DataFrame: dữ liệu đã làm sạch (12 bước), thêm các cột
        *_scaled, *_encoded do bước Scaling/Encoding tạo ra
    """
    report = _new_report(rows_before=len(df))
    print("=" * 55, "\n  PIPELINE LÀM SẠCH DỮ LIỆU TIN TỨC\n" + "=" * 55)
    step1_survey(df, report)
    df = step2_dedup(df, report)
    df = step3_missing(df, report)
    df = step4_dtypes(df, report)
    df = step5_formats(df, report)
    df = step6_invalid(df, report)
    df = step7_outliers(df, report)
    df = step8_melt(df, report)
    df = step9_scale(df, report)
    df = step10_encode(df, report)
    df = step11_balance(df, report)
    print(f"\n🎉 XONG! {df.shape[0]} dòng x {df.shape[1]} cột")
    return df


def save_clean_csv(df: pd.DataFrame, path: str = OUTPUT_PATH):
    """Lưu lại file CSV đã làm sạch (dùng đúng tên cũ TV3 đã đặt:
    cleaned_news.csv, nhưng app.py tìm theo clean_news.csv — xem
    chú ý trong app.py phần đường dẫn CLEAN_PATH)."""
    report = _new_report(rows_before=len(df))
    step12_save(df, report, out_path=path)
    return path


if __name__ == "__main__":
    df = pd.read_csv(RAW_PATH)
    clean_df = clean_data(df)
    save_clean_csv(clean_df)
    import_to_mysql(clean_df)
