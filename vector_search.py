"""
============================================================
VECTOR_SEARCH.PY — TÌM KIẾM NGỮ NGHĨA BẰNG VECTOR DATABASE (ChromaDB)
============================================================
Đây là VECTOR DATABASE THẬT (không phải tự chế bằng numpy thuần).

ChromaDB là 1 cơ sở dữ liệu chuyên lưu trữ và tìm kiếm vector,
mã nguồn mở, MIỄN PHÍ, chạy local (lưu vào thư mục trên máy/server,
không cần internet hay server riêng sau khi cài).

CÁCH HOẠT ĐỘNG:
    1. Mỗi bài báo (title + summary) được AI Embedding "dịch" thành
       1 vector số đại diện cho NGHĨA của câu.
    2. Vector đó được LƯU VÀO ChromaDB (1 database chuyên dụng cho
       vector, có index tối ưu để tìm kiếm nhanh — khác với việc
       tự so sánh từng vector bằng vòng lặp).
    3. Khi tìm kiếm, câu query cũng được mã hóa thành vector, rồi
       ChromaDB tự tìm các vector "gần nghĩa nhất" bằng thuật toán
       index (HNSW), không cần duyệt tuần tự toàn bộ dữ liệu.

MODEL EMBEDDING: 'paraphrase-multilingual-MiniLM-L12-v2'
    - Miễn phí, không cần API key, hỗ trợ tiếng Việt.

CÀI TRƯỚC KHI DÙNG:
    pip install chromadb sentence-transformers
============================================================
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_DIR = os.path.join(BASE_DIR, "data", "chroma_db")
COLLECTION_NAME = "articles"

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model = None
_client = None
_collection = None


def get_model():
    """Load model AI Embedding (chỉ load 1 lần, dùng lại nhiều lần)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"Đang tải model '{MODEL_NAME}' (lần đầu có thể mất 1-2 phút)...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_client():
    """Khởi tạo ChromaDB client (lưu dữ liệu vào thư mục local
    data/chroma_db, tự động tạo nếu chưa có)."""
    global _client
    if _client is None:
        import chromadb
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    return _client


def get_collection(reset: bool = False):
    """Lấy (hoặc tạo mới) collection 'articles' trong ChromaDB —
    collection giống như 1 'bảng' trong Vector DB.

    Args:
        reset: nếu True, xóa collection cũ và tạo lại từ đầu
            (dùng khi muốn xây dựng lại toàn bộ index)
    """
    global _collection
    client = get_client()

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        _collection = None

    if _collection is None:
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # dùng cosine similarity
        )
    return _collection


def collection_exists_and_has_data() -> bool:
    """Kiểm tra ChromaDB đã có dữ liệu (index) sẵn sàng để tìm kiếm chưa."""
    try:
        collection = get_collection()
        return collection.count() > 0
    except Exception:
        return False


def build_vector_index(df: pd.DataFrame, text_cols=("title", "summary"),
                        batch_size: int = 200) -> int:
    """
    Xây dựng Vector Index: tính embedding cho TOÀN BỘ bài báo và
    LƯU VÀO ChromaDB. Chỉ cần chạy 1 LẦN — ChromaDB tự lưu trữ
    bền vững (persistent) vào thư mục local, các lần mở app sau
    không cần tính lại.

    Args:
        df: DataFrame chứa các bài báo, cần có cột "title" (bắt buộc)
        text_cols: các cột sẽ ghép lại làm văn bản để tính embedding
        batch_size: số bài xử lý mỗi đợt (tránh quá tải RAM)

    Returns:
        int: số bài báo đã được đưa vào Vector DB
    """
    model = get_model()
    collection = get_collection(reset=True)  # xây lại từ đầu cho sạch

    total = len(df)
    print(f"Đang xây dựng Vector Index cho {total} bài báo...")

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = df.iloc[start:end]

        texts = []
        ids = []
        metadatas = []
        for idx, row in batch.iterrows():
            parts = [str(row.get(c, "")) for c in text_cols if c in df.columns]
            text = ". ".join(p for p in parts if p and p != "nan")
            texts.append(text if text else "Không có nội dung")
            ids.append(str(idx))
            metadatas.append({"row_index": int(idx)})

        embeddings = model.encode(texts, convert_to_numpy=True).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        print(f"  Đã xử lý {end}/{total} bài...")

    print(f"Hoàn tất! Đã đưa {total} bài báo vào Vector DB (ChromaDB).")
    return total


def vector_search(query: str, df: pd.DataFrame, top_k: int = 20,
                   max_distance: float = 0.75) -> pd.DataFrame:
    """
    Tìm kiếm ngữ nghĩa thật sự bằng Vector Database: trả về các bài
    báo GẦN NGHĨA với câu query, dù không trùng chữ. Ví dụ:
    query="thuốc bổ ích" có thể trả về các bài về vitamin, sức khỏe,
    y học dù tiêu đề không chứa đúng cụm "thuốc bổ ích".

    ChromaDB tự dùng thuật toán index (HNSW) để tìm nhanh, không
    cần so sánh tuần tự từng vector một.

    Args:
        query: câu tìm kiếm của người dùng
        df: DataFrame bài báo gốc (để lấy lại thông tin đầy đủ sau
            khi ChromaDB trả về danh sách id liên quan)
        top_k: số lượng kết quả tối đa trả về
        max_distance: ngưỡng khoảng cách tối đa (càng nhỏ càng giống
            nhau; cosine distance từ 0 đến 2, dưới 0.75 là khá liên quan)

    Returns:
        pd.DataFrame: các bài báo liên quan, đã sắp xếp theo độ
        liên quan giảm dần, có thêm cột "similarity_score" (0-100%)
    """
    collection = get_collection()
    if collection.count() == 0:
        raise RuntimeError(
            "Vector DB chưa có dữ liệu. Cần chạy build_vector_index(df) "
            "trước (chỉ cần chạy 1 lần, sau đó tự động dùng lại)."
        )

    model = get_model()
    query_embedding = model.encode([query], convert_to_numpy=True).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
    )

    if not results["ids"] or not results["ids"][0]:
        return df.iloc[0:0]

    matched_indices = []
    scores = []
    for i, dist in zip(results["ids"][0], results["distances"][0]):
        if dist <= max_distance:
            matched_indices.append(int(i))
            # Chuyển cosine distance (0=giống hệt, 2=khác hoàn toàn)
            # thành điểm phần trăm dễ hiểu (100%=giống hệt, 0%=khác hoàn toàn)
            scores.append(max(0.0, 1 - dist / 2))

    if not matched_indices:
        return df.iloc[0:0]

    result = df.loc[df.index.isin(matched_indices)].copy()
    score_map = dict(zip(matched_indices, scores))
    result["similarity_score"] = result.index.map(score_map)
    result = result.sort_values("similarity_score", ascending=False)

    return result
