"""
============================================================
THÀNH VIÊN 1 - CRAWLER (VnExpress bằng requests + Tuổi Trẻ bằng Selenium)
============================================================
File này gộp 2 crawler GỐC của TV1:
  - crawler_vnexpress.py  (requests + BeautifulSoup, KHÔNG cần Chrome)
  - crawler_fixed.py      (Selenium, CẦN Google Chrome)

Toàn bộ logic xử lý của TV1 được giữ NGUYÊN VẸN — chỉ đổi tên vài
hàm trùng nhau giữa 2 nguồn (vd get_soup, parse_article) để gộp
chung 1 file không bị đè lẫn, và bọc thêm hàm crawl_news() ở cuối
để Web App (app.py) gọi qua nút bấm.

Cài trước khi chạy:
    pip install selenium pandas beautifulsoup4 lxml requests
VnExpress chạy được mọi nơi (cả server cloud).
Tuổi Trẻ cần có Google Chrome cài trên máy.
============================================================
"""

import time
import re
import os
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Bọc import selenium trong try/except: trên server cloud (Streamlit
# Community Cloud) không có Chrome/Selenium, nếu import lỗi ngay từ
# đầu sẽ làm SẬP TOÀN BỘ app. Với cách này, app vẫn mở được bình
# thường; phần VnExpress (không cần Selenium) vẫn chạy tốt trên cloud,
# chỉ riêng phần Tuổi Trẻ sẽ báo lỗi nhẹ nếu thiếu Selenium/Chrome.
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT = os.path.join(DATA_DIR, "raw_news.csv")

TARGET_VNE     = 3500   # số bài VnExpress muốn đạt
TARGET_TUOITRE = 3500   # số bài Tuổi Trẻ muốn đạt
SAVE_EVERY     = 50     # lưu tạm sau mỗi N bài

VNEXPRESS_CATEGORIES = [
    "https://vnexpress.net/so-hoa",
    "https://vnexpress.net/kinh-doanh",
    "https://vnexpress.net/thoi-su",
    "https://vnexpress.net/the-gioi",
    "https://vnexpress.net/phap-luat",
    "https://vnexpress.net/giao-duc",
    "https://vnexpress.net/suc-khoe",
    "https://vnexpress.net/du-lich",
    "https://vnexpress.net/khoa-hoc",
    "https://vnexpress.net/giai-tri",
    "https://vnexpress.net/the-thao",
    "https://vnexpress.net/xe",
    "https://vnexpress.net/oto-xe-may",
    "https://vnexpress.net/bat-dong-san",
    "https://vnexpress.net/y-kien",
    "https://vnexpress.net/tam-su",
    "https://vnexpress.net/cuoi",
]

TUOITRE_CATEGORIES = [
    "https://tuoitre.vn/thoi-su.htm",
    "https://tuoitre.vn/the-gioi.htm",
    "https://tuoitre.vn/kinh-doanh.htm",
    "https://tuoitre.vn/cong-nghe.htm",
    "https://tuoitre.vn/the-thao.htm",
    "https://tuoitre.vn/giao-duc.htm",
    "https://tuoitre.vn/suc-khoe.htm",
    "https://tuoitre.vn/van-hoa.htm",
    "https://tuoitre.vn/giai-tri.htm",
    "https://tuoitre.vn/phap-luat.htm",
    "https://tuoitre.vn/du-lich.htm",
    "https://tuoitre.vn/khoa-hoc.htm",
    "https://tuoitre.vn/xe.htm",
    "https://tuoitre.vn/nha-dat.htm",
    "https://tuoitre.vn/moi-truong.htm",
    "https://tuoitre.vn/goc-nhin.htm",
    "https://tuoitre.vn/nhip-song-tre.htm",
    "https://tuoitre.vn/gia-dinh.htm",
]


# ════════════════════════════════════════════════════════════
# PHẦN A — VNEXPRESS (requests + BeautifulSoup, KHÔNG cần Chrome)
# Nguyên bản từ file crawler_vnexpress.py
# ════════════════════════════════════════════════════════════

def _vne_get_soup(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            print(f"    Lỗi tải {url}: {e} (thử {attempt+1}/{retries})")
            time.sleep(2)
    return None


def _vne_get_links_from_category(cat_url, quota, max_pages=300):
    """Lật trang VnExpress (-p2, -p3...) cho tới khi đủ quota."""
    links = []
    for page in range(1, max_pages + 1):
        url = cat_url if page == 1 else f"{cat_url}-p{page}"
        soup = _vne_get_soup(url)
        if not soup:
            break
        found_any = False
        for a in soup.select(
            "article.item-news-common h4.title-news a, "
            "article.item-news h3.title-news a, "
            "article.item-news h2.title-news a"
        ):
            href = a.get("href")
            if href and href.startswith("http") and href not in links:
                links.append(href)
                found_any = True
            if len(links) >= quota:
                return links
        if not found_any:
            break
        time.sleep(0.3)
    return links


def _vne_collect_all_links(existing_links, quota):
    """Gom link từ nhiều chuyên mục VnExpress cho tới khi đủ quota link MỚI."""
    new_links = []
    n = len(VNEXPRESS_CATEGORIES)
    for idx, cat_url in enumerate(VNEXPRESS_CATEGORIES):
        if len(new_links) >= quota:
            break
        remaining_total = quota - len(new_links)
        remaining_cats = n - idx
        cat_quota = -(-remaining_total // remaining_cats)  # làm tròn lên
        print(f"\n  Chuyên mục: {cat_url} (mục tiêu ~{cat_quota} bài)")
        cat_links = _vne_get_links_from_category(cat_url, cat_quota + 20)
        added = 0
        for link in cat_links:
            if link not in existing_links and link not in new_links:
                new_links.append(link)
                added += 1
        print(f"  --> {added} bài mới, tổng tích lũy: {len(new_links)}/{quota}")
    return new_links


def _vne_get_comment_count(url):
    """Lấy số bình luận thật qua API VnExpress."""
    try:
        match = re.search(r"-(\d+)\.html$", url)
        if not match:
            return "0"
        article_id = match.group(1)
        api = (f"https://usi-saas.vnexpress.net/index/get"
               f"?offset=0&limit=1&sort=&objectid={article_id}"
               f"&objecttype=1&siteid=1000000")
        r = requests.get(api, headers={**HEADERS, "Referer": url}, timeout=8)
        data = r.json()
        total = (data.get("data") or {}).get("total_count", 0)
        return str(total)
    except Exception:
        return "0"


def _vne_parse_article(url):
    soup = _vne_get_soup(url)
    if not soup:
        return None
    try:
        title = soup.select_one("h1.title-detail")
        title = title.get_text(strip=True) if title else ""

        date = soup.select_one("span.date")
        date = date.get_text(strip=True) if date else ""

        paras = soup.select("article.fck_detail p.Normal")
        content = " ".join(p.get_text(strip=True) for p in paras)

        author = soup.select_one("p.Normal strong")
        author = author.get_text(strip=True) if author else ""

        num_comments = _vne_get_comment_count(url)

        return {
            "nguon": "VnExpress",
            "tieu_de": title,
            "ngay_dang": date,
            "tac_gia": author,
            "noi_dung": content,
            "so_binh_luan": num_comments,
            "link": url,
        }
    except Exception as e:
        print(f"    Lỗi parse {url}: {e}")
        return None


def _run_crawl_vnexpress(all_data, existing_links):
    """Logic gốc của TV1 (crawler_vnexpress.py), y nguyên, chỉ chuyển
    từ khối if __name__ == "__main__": thành 1 hàm dùng chung biến
    all_data/existing_links với phần Tuổi Trẻ."""
    vne_existing = len([d for d in all_data if d.get("nguon") == "VnExpress"])
    need = TARGET_VNE - vne_existing
    if need <= 0:
        print(f"Đã đủ {TARGET_VNE} bài VnExpress rồi, không cần chạy thêm.")
        return all_data

    print(f"\nCần thêm {need} bài VnExpress.")
    print("\n[BƯỚC 1] Gom link VnExpress...")
    new_links = _vne_collect_all_links(existing_links, need)
    print(f"\nTổng link VnExpress mới gom được: {len(new_links)}")

    if not new_links:
        print("Không gom được link VnExpress nào, dừng.")
        return all_data

    print(f"\n[BƯỚC 2] Cào nội dung {len(new_links)} bài VnExpress...")
    for i, link in enumerate(new_links, 1):
        print(f"  [VNE {i}/{len(new_links)}] {link}")
        data = _vne_parse_article(link)
        if data:
            all_data.append(data)
            existing_links.add(link)
        if i % SAVE_EVERY == 0:
            df_tmp = pd.DataFrame(all_data).drop_duplicates(subset=["link"])
            df_tmp.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
            print(f"  --> Lưu tạm: {len(df_tmp)} bài tổng cộng")
        time.sleep(0.5)

    return all_data


# ════════════════════════════════════════════════════════════
# PHẦN B — TUỔI TRẺ (Selenium, CẦN Google Chrome)
# Nguyên bản từ file crawler_fixed.py
# ════════════════════════════════════════════════════════════

def _tt_make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")
    opts.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    return driver


_TT_ARTICLE_URL_RE = re.compile(r"-\d{10,}\.htm$")


def _tt_get_links_from_category(driver, cat_url, quota, max_clicks=80):
    """Mở trang chuyên mục Tuổi Trẻ, click 'Xem thêm' liên tục cho tới khi đủ quota hoặc hết nút."""
    links = []
    print(f"    Mở: {cat_url}")
    try:
        driver.get(cat_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='.htm']"))
        )
    except Exception as e:
        print(f"    Timeout/lỗi khi tải trang: {e}")
        return links

    no_new_streak = 0
    for click_i in range(max_clicks + 1):
        soup = BeautifulSoup(driver.page_source, "lxml")
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.startswith("/"):
                href = "https://tuoitre.vn" + href
            if (href.startswith("https://tuoitre.vn")
                    and _TT_ARTICLE_URL_RE.search(href)
                    and href not in links):
                links.append(href)
        print(f"      [click {click_i}] tổng tích lũy: {len(links)}")

        if len(links) >= quota:
            print(f"      Đủ {quota} bài, dừng click.")
            break

        clicked = False
        try:
            btns = driver.find_elements(By.XPATH,
                "//*[contains(text(),'Xem thêm') or contains(text(),'xem thêm')]"
                "[not(ancestor::*[@style='display:none'])]"
            )
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.4)
                    driver.execute_script("arguments[0].click();", btn)
                    clicked = True
                    print(f"      [click {click_i}] Đã click 'Xem thêm'")
                    break
        except Exception as e:
            print(f"      [click {click_i}] Lỗi click: {e}")

        if not clicked:
            no_new_streak += 1
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            if no_new_streak >= 3:
                print(f"      Không tìm thấy nút 'Xem thêm' 3 lần liên tiếp, dừng.")
                break
        else:
            no_new_streak = 0

        time.sleep(1.5)

    return links[:quota]


def _tt_collect_all_links(existing_links, quota):
    """Chạy Selenium qua các chuyên mục Tuổi Trẻ cho tới khi gom đủ quota link mới."""
    all_links = []
    driver = _tt_make_driver()
    try:
        for cat_url in TUOITRE_CATEGORIES:
            if len(all_links) >= quota:
                break
            remaining = quota - len(all_links)
            print(f"\n  Chuyên mục: {cat_url} (cần thêm ~{remaining} bài)")
            cat_links = _tt_get_links_from_category(driver, cat_url, remaining + 20)
            added = 0
            for link in cat_links:
                if link not in existing_links and link not in all_links:
                    all_links.append(link)
                    added += 1
            print(f"  --> {added} bài mới, tổng tích lũy: {len(all_links)}/{quota}")
    finally:
        driver.quit()
    return all_links


def _tt_get_soup(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            print(f"    Lỗi tải {url}: {e} (thử {attempt+1}/{retries})")
            time.sleep(2)
    return None


def _tt_get_comment_count(url):
    """Lấy số bình luận Tuổi Trẻ qua API JSON."""
    try:
        match = re.search(r"-(\d{10,})\.htm$", url)
        if not match:
            return "0"
        article_id = match.group(1)
        api = (f"https://id.tuoitre.vn/api/getlist-comment.api"
               f"?pageindex=1&pagesize=500&objId={article_id}&objType=1&sort=2")
        r = requests.get(api, headers={**HEADERS, "Referer": url}, timeout=8)
        data = r.json()
        if isinstance(data, dict):
            raw = data.get("Data", "[]")
            if isinstance(raw, str):
                raw = json.loads(raw)
            if isinstance(raw, list):
                total = sum(1 + (c.get("child_count") or 0) for c in raw if isinstance(c, dict))
                return str(total)
    except Exception:
        pass
    return "0"


def _tt_parse_article(url):
    soup = _tt_get_soup(url)
    if not soup:
        return None
    try:
        title = (soup.select_one("h1.detail-title") or
                 soup.select_one("h1[data-role='title']"))
        title = title.get_text(strip=True) if title else ""

        date = soup.select_one("time[data-role='publishdate']")
        date = date.get_text(strip=True) if date else ""

        paras = soup.select("div.detail-content.afcbc-body p")
        content = " ".join(p.get_text(strip=True) for p in paras)

        author = soup.select_one("div.detail-author-bot a.name")
        author = author.get_text(strip=True) if author else ""

        num_comments = _tt_get_comment_count(url)

        return {
            "nguon": "Tuổi Trẻ",
            "tieu_de": title,
            "ngay_dang": date,
            "tac_gia": author,
            "noi_dung": content,
            "so_binh_luan": num_comments,
            "link": url,
        }
    except Exception as e:
        print(f"    Lỗi parse {url}: {e}")
        return None


def _run_crawl_tuoitre(all_data, existing_links):
    """Logic gốc của TV1 (crawler_fixed.py), y nguyên, chỉ chuyển
    từ khối if __name__ == "__main__": thành 1 hàm dùng chung biến
    all_data/existing_links với phần VnExpress."""
    tt_existing = len([d for d in all_data if d.get("nguon") == "Tuổi Trẻ"])
    need = TARGET_TUOITRE - tt_existing
    if need <= 0:
        print(f"Đã đủ {TARGET_TUOITRE} bài Tuổi Trẻ rồi, không cần chạy thêm.")
        return all_data

    print(f"\nCần thêm {need} bài Tuổi Trẻ.")
    print("\n[BƯỚC 1] Gom link Tuổi Trẻ bằng Selenium...")
    new_links = _tt_collect_all_links(existing_links, need)
    print(f"\nTổng link Tuổi Trẻ mới gom được: {len(new_links)}")

    if not new_links:
        print("Không gom được link Tuổi Trẻ nào, dừng.")
        return all_data

    print(f"\n[BƯỚC 2] Cào nội dung {len(new_links)} bài Tuổi Trẻ...")
    for i, link in enumerate(new_links, 1):
        print(f"  [TT {i}/{len(new_links)}] {link}")
        data = _tt_parse_article(link)
        if data:
            all_data.append(data)
            existing_links.add(link)
        if i % SAVE_EVERY == 0:
            df_tmp = pd.DataFrame(all_data).drop_duplicates(subset=["link"])
            df_tmp.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
            print(f"  --> Lưu tạm: {len(df_tmp)} bài tổng cộng")
        time.sleep(0.5)

    return all_data


# ════════════════════════════════════════════════════════════
# PHẦN C — LOGIC CHUNG: chạy VnExpress trước, Tuổi Trẻ sau
# ════════════════════════════════════════════════════════════

def _run_crawl_pipeline():
    """Chạy lần lượt VnExpress (không cần Chrome) rồi Tuổi Trẻ (cần
    Chrome). Nếu không có Selenium/Chrome, vẫn chạy được phần
    VnExpress, chỉ bỏ qua phần Tuổi Trẻ với cảnh báo rõ ràng."""
    try:
        df_old = pd.read_csv(OUTPUT, encoding="utf-8-sig")
        all_data = df_old.to_dict("records")
        existing_links = set(df_old["link"].tolist())
        print(f"Load {len(all_data)} bài cũ từ {OUTPUT}")
    except FileNotFoundError:
        all_data = []
        existing_links = set()
        print("Chưa có file CSV, bắt đầu mới.")

    # Phần A: VnExpress — luôn chạy được (không cần Chrome)
    all_data = _run_crawl_vnexpress(all_data, existing_links)

    # Phần B: Tuổi Trẻ — chỉ chạy nếu có Selenium/Chrome
    if SELENIUM_AVAILABLE:
        all_data = _run_crawl_tuoitre(all_data, existing_links)
    else:
        print("\n[BỎ QUA] Không có Selenium/Chrome — bỏ qua phần cào Tuổi Trẻ.")
        print("Chạy lại bước này trên máy có Chrome để cào thêm Tuổi Trẻ.")

    df_final = pd.DataFrame(all_data).drop_duplicates(subset=["link"])
    df_final.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    vne = len(df_final[df_final["nguon"] == "VnExpress"])
    tt = len(df_final[df_final["nguon"] == "Tuổi Trẻ"])
    print(f"\n{'='*50}")
    print(f"HOÀN TẤT! Tổng {len(df_final)} bài")
    print(f"  VnExpress : {vne}")
    print(f"  Tuổi Trẻ  : {tt}")

    return df_final.to_dict("records")


# ─────────────────────────────────────────────
# HÀM VỎ — để app.py / main.py gọi được
# ─────────────────────────────────────────────

def crawl_news(keyword: str = None, limit: int = None) -> list:
    """
    Hàm vỏ để Web App gọi. Chạy VnExpress (requests, luôn chạy được,
    cả trên server cloud) trước, sau đó Tuổi Trẻ (Selenium, cần
    Chrome) nếu máy có sẵn Chrome.

    Returns:
        list[dict]: danh sách bài báo (cột: nguon, tieu_de, ngay_dang,
        tac_gia, noi_dung, so_binh_luan, link)
    """
    return _run_crawl_pipeline()


def save_to_csv(articles: list, path: str = OUTPUT):
    """Giữ lại để main.py gọi sau crawl_news() nếu cần lưu lại lần nữa.
    Việc lưu CSV đã được làm trong _run_crawl_pipeline(), nên hàm này
    chỉ là lưu phòng hờ (ghi đè cùng nội dung)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame(articles).to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[TV1] Đã lưu {len(articles)} bài báo vào: {path}")
    return path


if __name__ == "__main__":
    crawl_news()
