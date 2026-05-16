import pandas as pd

# -----------------------------------------------
# 검색 유형별 카테고리 매핑
# -----------------------------------------------
TYPE_RULES = {
    "카페":      {"strong": ["카페"], "medium": ["디저트", "베이커리", "커피"]},
    "맛집":      {"strong": ["음식점", "맛집", "한식", "양식", "일식", "중식", "분식", "치킨", "고기", "파인다이닝"], "medium": ["브런치"]},
    "브런치":    {"strong": ["브런치"], "medium": ["카페", "양식"]},
    "디저트":    {"strong": ["디저트"], "medium": ["카페", "베이커리"]},
    "베이커리":  {"strong": ["베이커리"], "medium": ["디저트", "카페"]},
    "파인다이닝":{"strong": ["파인다이닝"], "medium": ["양식", "음식점"]},
    "한식":      {"strong": ["한식"], "medium": ["음식점", "맛집"]},
    "양식":      {"strong": ["양식"], "medium": ["브런치", "파인다이닝", "음식점"]},
    "일식":      {"strong": ["일식"], "medium": ["일본식주점", "음식점"]},
    "중식":      {"strong": ["중식"], "medium": ["음식점"]},
    "술집":      {"strong": ["술집", "호프", "와인바", "칵테일바", "일본식주점"], "medium": ["주점"]},
    "호프":      {"strong": ["호프"], "medium": ["술집", "주점"]},
    "와인바":    {"strong": ["와인바"], "medium": ["술집", "바"]},
    "칵테일바":  {"strong": ["칵테일바"], "medium": ["술집", "바"]},
    "일본식주점":{"strong": ["일본식주점"], "medium": ["일식", "술집"]},
}

# -----------------------------------------------
# 검색 특징별 키워드 매핑
# -----------------------------------------------
FEATURE_RULES = {
    "핸드드립":   ["핸드드립"],
    "로스터리":   ["로스터리"],
    "스페셜티":   ["스페셜티"],
    "뷰맛집":     ["오션뷰", "시티뷰", "리버뷰", "전망", "루프탑", "테라스"],
    "루프탑":     ["루프탑"],
    "테라스":     ["테라스"],
    "북카페":     ["북카페"],
    "대형카페":   ["대형카페"],
    "애견동반":   ["애견동반"],
    "24시":       ["24시"],
    "호프":       ["호프"],
    "와인바":     ["와인바"],
    "칵테일바":   ["칵테일바"],
    "일본식주점": ["일본식주점"],
}

# -----------------------------------------------
# 매장 특성 신호 키워드 (보너스, 최대 10점)
# -----------------------------------------------
GENERAL_SIGNALS = {
    "루프탑":   4,
    "브런치":   4,
    "스페셜티": 4,
    "로스터리": 4,
    "핸드드립": 3,
    "오션뷰":   4,
    "테라스":   3,
    "와인바":   4,
    "칵테일바": 4,
    "애견동반": 2,
    "24시":     2,
    "수제":     2,
}


# -----------------------------------------------
# 유틸
# -----------------------------------------------
def clean_text(value):
    if pd.isna(value):
        return ""
    value = str(value).strip()
    return "" if value.lower() == "nan" else value


def has_any(text, keywords):
    return any(kw in text for kw in keywords if kw)


def valid_coord(x, y):
    try:
        lon, lat = float(x), float(y)
        return 120 < lon < 135 and 30 < lat < 40
    except Exception:
        return False


def parse_query_intent(query):
    q = clean_text(query)
    q_types    = [k for k in TYPE_RULES    if k in q]
    q_features = [k for k in FEATURE_RULES if k in q]
    return q_types, q_features


# -----------------------------------------------
# 카카오 정확도 순위 → 점수 (20점)
# -----------------------------------------------
def get_api_rank_score(rank):
    try:
        rank = int(rank)
    except Exception:
        return 0
    if rank <= 3:   return 20
    if rank <= 5:   return 18
    if rank <= 10:  return 15
    if rank <= 20:  return 10
    return 6


# -----------------------------------------------
# 핵심 채점 함수
# -----------------------------------------------
def calculate_score_detail(row, query=""):
    score, reasons = 0, []

    place_name = clean_text(row.get("place_name", ""))
    category   = clean_text(row.get("category_name", ""))
    address    = clean_text(row.get("address_name", ""))
    road       = clean_text(row.get("road_address_name", ""))
    phone      = clean_text(row.get("phone", ""))
    place_url  = clean_text(row.get("place_url", ""))
    x          = clean_text(row.get("x", ""))
    y          = clean_text(row.get("y", ""))

    text = f"{place_name} {category}"
    q_types, q_features = parse_query_intent(query)

    # ── 1) 카카오 검색 정확도 순위 (최대 20점) ──────────────────
    api_rank   = row.get("_api_rank", "")
    rank_score = get_api_rank_score(api_rank)
    if rank_score:
        score += rank_score
        reasons.append(f"카카오 정확도 순위 {api_rank}위 +{rank_score}")

    # ── 2) 검색 유형 일치도 (최대 30점) ────────────────────────
    if q_types:
        best_type, best_type_score = None, 0
        for t in q_types:
            rule = TYPE_RULES[t]
            if has_any(text, rule["strong"]):
                cand = 30
            elif has_any(text, rule.get("medium", [])):
                cand = 20
            elif category:
                cand = 8
            else:
                cand = 0
            if cand > best_type_score:
                best_type, best_type_score = t, cand

        score += best_type_score
        reasons.append(f"검색 유형 '{best_type}' 일치 +{best_type_score}")
    elif category:
        score += 15
        reasons.append("카테고리 정보 있음 +15")

    # ── 3) 검색 특징 일치도 (최대 10점) ────────────────────────
    if q_features:
        for f in q_features:
            if has_any(text, FEATURE_RULES[f]):
                score += 10
                reasons.append(f"검색 특징 '{f}' 일치 +10")
                break

    # ── 4) 정보 완성도 (최대 25점) ─────────────────────────────
    if place_name:
        score += 4;  reasons.append("장소명 있음 +4")
    if category:
        score += 4;  reasons.append("카테고리 있음 +4")
    if address:
        score += 3;  reasons.append("지번 주소 있음 +3")
    if road:
        score += 5;  reasons.append("도로명 주소 있음 +5")
    if phone:
        score += 4;  reasons.append("전화번호 있음 +4")
    if place_url:
        score += 2;  reasons.append("카카오맵 URL 있음 +2")
    if valid_coord(x, y):
        score += 3;  reasons.append("좌표 정보 있음 +3")

    # ── 5) 카테고리 구체성 (최대 5점) ──────────────────────────
    depth = len([c.strip() for c in category.split(">") if c.strip()])
    if depth >= 3:
        score += 5;  reasons.append("세부 카테고리 3단계 이상 +5")
    elif depth == 2:
        score += 3;  reasons.append("세부 카테고리 2단계 +3")
    elif depth == 1 and category:
        score += 1;  reasons.append("세부 카테고리 1단계 +1")

    # ── 6) 매장 특성 신호 (최대 10점) ──────────────────────────
    signal_bonus = 0
    for kw, b in GENERAL_SIGNALS.items():
        if kw in text:
            added = min(b, 10 - signal_bonus)
            if added > 0:
                score        += added
                signal_bonus += added
                reasons.append(f"'{kw}' 신호 +{added}")
            if signal_bonus >= 10:
                break

    return min(round(score, 1), 100), reasons


# -----------------------------------------------
# 등급
# -----------------------------------------------
def get_grade(s):
    if s >= 80:  return "S등급"
    if s >= 68:  return "A등급"
    if s >= 50:  return "B등급"
    return "C등급"


def get_grade_description(g):
    return {
        "S등급": "강력 추천",
        "A등급": "추천",
        "B등급": "괜찮음",
        "C등급": "참고용",
    }.get(g, "")


# -----------------------------------------------
# 목적 태그
# -----------------------------------------------
def get_purpose_tags(row):
    tags       = []
    category   = clean_text(row.get("category_name", ""))
    place_name = clean_text(row.get("place_name", ""))

    if "카페"    in category:                                    tags.append("카페 ☕")
    if "베이커리" in category:                                   tags.append("베이커리 🥐")
    if "디저트"  in category:                                    tags.append("디저트 🍰")
    if "브런치"  in place_name or "브런치" in category:         tags.append("브런치 🥞")
    if "루프탑"  in place_name:                                  tags.append("루프탑 🌇")
    if "한식"    in category:                                    tags.append("한식 🍚")
    if "양식"    in category:                                    tags.append("양식 🍝")
    if "일식"    in category:                                    tags.append("일식 🍱")
    if "중식"    in category:                                    tags.append("중식 🥟")
    if "스페셜티" in place_name or "로스터리" in place_name:    tags.append("스페셜티 ✨")
    if "수제"    in place_name:                                  tags.append("수제 🤲")
    if "와인바"  in category or "와인바" in place_name:         tags.append("와인바 🍷")
    if "칵테일"  in category or "칵테일" in place_name:         tags.append("칵테일 🍸")
    if "호프"    in category or "호프"   in place_name:         tags.append("호프 🍺")

    return tags


# -----------------------------------------------
# 분석 메인
# -----------------------------------------------
def analyze_data(places_list, query=""):
    if not places_list:
        return pd.DataFrame()

    df = pd.DataFrame(places_list)

    for col in ["place_name", "category_name", "address_name",
                "road_address_name", "phone", "place_url", "x", "y"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)

    df["_api_rank"] = range(1, len(df) + 1)

    details = df.apply(lambda row: calculate_score_detail(row, query=query), axis=1)
    df["quality_score"] = details.apply(lambda x: x[0])
    df["score_reasons"] = details.apply(lambda x: x[1])
    df["grade"]         = df["quality_score"].apply(get_grade)
    df["grade_desc"]    = df["grade"].apply(get_grade_description)
    df["purpose_tags"]  = df.apply(get_purpose_tags, axis=1)

    df = df.drop_duplicates(subset=["place_name", "address_name"])
    df = df.sort_values("quality_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


# -----------------------------------------------
# 필터 / 정렬
# -----------------------------------------------
def filter_data(df, gf, tf, hp, hr):
    f = df.copy()
    if gf and gf != "전체":
        f = f[f["grade"] == gf]
    if tf and tf != "전체":
        f = f[f["purpose_tags"].apply(lambda t: any(tf in x for x in t))]
    if hp:
        f = f[f["phone"] != ""]
    if hr:
        f = f[f["road_address_name"] != ""]
    return f


def sort_data(df, sb):
    if sb == "추천순":    return df.sort_values("quality_score", ascending=False)
    if sb == "이름순":    return df.sort_values("place_name")
    if sb == "카테고리순": return df.sort_values("category_name")
    return df

import html
from textwrap import dedent
from urllib.parse import quote, unquote

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

import kakao_api
import analyzer

# -----------------------------------------------
# 페이지 설정
# -----------------------------------------------
st.set_page_config(
    page_title="카페 & 맛집 추천기",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
    /* ── 기본 ──────────────────────────────── */
    .main { background-color: #FFF8F0; }

    /* ── 태그 ──────────────────────────────── */
    .tag {
        background-color: #FFF3E0;
        color: #E65100;
        padding: 3px 10px;
        border-radius: 10px;
        font-size: 13px;
        margin: 2px;
        display: inline-block;
    }

    /* ── 점수 카드 ─────────────────────────── */
    .score-card {
        text-align: center;
        padding: 15px;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* ── TOP 뱃지 ──────────────────────────── */
    .top-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
        vertical-align: middle;
        margin-left: 8px;
    }
    .top-1 { background: #FFD700; color: #333; }
    .top-2 { background: #C0C0C0; color: #333; }
    .top-3 { background: #CD7F32; color: #fff; }

    /* ── 구분선 ────────────────────────────── */
    .card-divider {
        border: none;
        border-top: 1px solid #FFE0CC;
        margin: 16px 0;
    }

    /* ── 사이드바 즐겨찾기 카드 ────────────── */
    .fav-card {
        position: relative;
        background: linear-gradient(135deg, #FFFAF5, #FFF5EE);
        border: 1px solid #FFD9C2;
        border-radius: 16px;
        margin: 8px 0 0 0;
        padding: 12px 14px 58px 14px;
        overflow: hidden;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .fav-card:hover {
        border-color: #FFB088;
        box-shadow: 0 6px 16px rgba(230,81,0,0.10);
    }

    .fav-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 5px;
        padding-right: 54px;
    }

    .fav-grade-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }

    .fav-card-name {
        font-size: 13px;
        font-weight: 700;
        color: #333;
        line-height: 1.35;
        word-break: keep-all;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-decoration: none !important;
    }

    .fav-card-category {
        font-size: 10px;
        color: #999;
        line-height: 1.3;
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-decoration: none !important;
    }

    .fav-card-addr {
        font-size: 11px;
        color: #888;
        line-height: 1.45;
        word-break: keep-all;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-decoration: none !important;
    }

    .fav-card-score {
        position: absolute;
        top: 10px;
        right: 12px;
        font-size: 10px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 999px;
        color: #fff;
        line-height: 1.2;
    }

    /* ── 사이드바 즐겨찾기 삭제 버튼 오버레이 ───────── */
    .fav-del-wrap {
        display: flex;
        justify-content: flex-end;
        margin-top: -40px;
        margin-bottom: 10px;
        padding-right: 4px;
        position: relative;
        z-index: 30;
    }

    .fav-del-wrap .stButton {
        width: auto !important;
    }

    .fav-del-wrap button {
        width: 28px !important;
        height: 28px !important;
        min-height: 28px !important;
        padding: 0 !important;
        border-radius: 9px !important;
        background: rgba(255,255,255,0.18) !important;
        border: 1px solid rgba(255,255,255,0.28) !important;
        color: #fff !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        box-shadow: none !important;
        backdrop-filter: blur(2px);
    }

    .fav-del-wrap button:hover {
        background: rgba(255,255,255,0.26) !important;
        border-color: rgba(255,255,255,0.42) !important;
        color: #fff !important;
    }

    /* ── 사이드바 즐겨찾기 장소 버튼  ───────────────── */
    .fav-cta-shell {
        position: absolute;
        left: 14px;
        right: 14px;
        bottom: 10px;
        height: 36px;
        padding: 0 42px 0 12px;
        border-radius: 11px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        background: linear-gradient(135deg, #FF8A5B, #E96A2C);
        border: 1px solid #E46A31;
        color: #fff;
        font-size: 12px;
        font-weight: 700;
        box-sizing: border-box;
        box-shadow: 0 4px 10px rgba(233,106,44,0.22);
        z-index: 1;
        pointer-events: none;
        user-select: none;
    }

    .fav-cta-shell-disabled {
        background: linear-gradient(135deg, #F2D7C9, #EBC9B7);
        border-color: #E3B8A0;
        color: #9C7A68;
        box-shadow: none;
    }

    /* ── 큰 주황색 링크 버튼 ───────────────── */
    .fav-map-link,
    .fav-map-link:hover,
    .fav-map-link:visited,
    .fav-map-link:active {
        position: absolute;
        left: 14px;
        right: 14px;
        bottom: 10px;
        height: 36px;
        padding: 0 42px 0 12px;
        border-radius: 11px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        background: linear-gradient(135deg, #FF8A5B, #E96A2C);
        border: 1px solid #E46A31;
        color: #fff !important;
        font-size: 12px;
        font-weight: 700;
        box-sizing: border-box;
        box-shadow: 0 4px 10px rgba(233,106,44,0.22);
        z-index: 1;
        text-decoration: none !important;
        user-select: none;
    }

    .fav-map-link:hover {
        background: linear-gradient(135deg, #FF8A5B, #E96A2C);
        border: 1px solid #E46A31;
        color: #fff !important;
        text-decoration: none !important;
    }

    .fav-map-link-disabled,
    .fav-map-link-disabled:hover,
    .fav-map-link-disabled:visited,
    .fav-map-link-disabled:active {
        position: absolute;
        left: 14px;
        right: 14px;
        bottom: 10px;
        height: 36px;
        padding: 0 42px 0 12px;
        border-radius: 11px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        background: linear-gradient(135deg, #F2D7C9, #EBC9B7);
        border: 1px solid #E3B8A0;
        color: #9C7A68 !important;
        font-size: 12px;
        font-weight: 700;
        box-sizing: border-box;
        box-shadow: none;
        z-index: 1;
        text-decoration: none !important;
        pointer-events: none;
        user-select: none;
    }

    /* ── 버튼 내부 X ──────────────────────── */
    .fav-del-btn,
    .fav-del-btn:hover,
    .fav-del-btn:visited,
    .fav-del-btn:active {
        position: absolute;
        right: 18px;
        bottom: 14px;
        z-index: 3;
        width: 28px;
        height: 28px;
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.28);
        color: #fff !important;
        text-decoration: none !important;
        font-size: 14px;
        font-weight: 800;
        line-height: 1;
        box-sizing: border-box;
        transition: background-color 0.18s ease, border-color 0.18s ease;
        backdrop-filter: blur(2px);
    }

    .fav-del-btn:hover {
        background: rgba(255,255,255,0.26);
        border-color: rgba(255,255,255,0.42);
        color: #fff !important;
    }

    .fav-empty {
        text-align: center;
        padding: 24px 10px;
        color: #bbb;
        font-size: 14px;
    }

    .fav-empty-icon {
        font-size: 36px;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------
# 세션 상태 초기화
# -----------------------------------------------
defaults = {
    "results_df": None,
    "search_history": [],
    "favorites": [],
    "last_query": "",
    "_last_error": None,
    "_last_query": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -----------------------------------------------
# 상수
# -----------------------------------------------
GRADE_ORDER = ["S등급", "A등급", "B등급", "C등급"]

GRADE_COLOR = {
    "S등급": "#E63946",
    "A등급": "#F4845F",
    "B등급": "#2EC4B6",
    "C등급": "#7B8FA1",
}

GRADE_GRADIENT = {
    "S등급": ("#E63946", "#FF6B6B"),
    "A등급": ("#F4845F", "#FF9F7A"),
    "B등급": ("#2EC4B6", "#6EE7D8"),
    "C등급": ("#7B8FA1", "#A5B4C3"),
}

MARKER_COLOR = {
    "S등급": "#E63946",
    "A등급": "#F4845F",
    "B등급": "#2EC4B6",
    "C등급": "#7B8FA1",
}

# -----------------------------------------------
# 캐시 검색
# -----------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def cached_search_multi(query, total_size):
    return kakao_api.search_places_multi(query, total_size=total_size)

# -----------------------------------------------
# 즐겨찾기 유틸
# -----------------------------------------------
def make_favorite_key(item):
    if hasattr(item, "to_dict"):
        item = item.to_dict()

    if not isinstance(item, dict):
        return str(item).strip()

    place_id = str(item.get("id", "")).strip()
    if place_id:
        return f"id::{place_id}"

    place_name = str(item.get("place_name", "")).strip()
    address = str(item.get("address_name", "")).strip()
    road = str(item.get("road_address_name", "")).strip()

    return "||".join([place_name, address, road])


def toggle_favorite(row):
    row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    name = row_dict.get("place_name", "")
    row_key = make_favorite_key(row_dict)

    idx = [
        i for i, f in enumerate(st.session_state.favorites)
        if make_favorite_key(f) == row_key
    ]

    if idx:
        st.session_state.favorites.pop(idx[0])
        st.toast(f"'{name}' 즐겨찾기 해제")
    else:
        st.session_state.favorites.append(row_dict)
        st.toast(f"'{name}' 즐겨찾기 추가!")


def is_favorite(item):
    target_key = make_favorite_key(item)
    return any(make_favorite_key(f) == target_key for f in st.session_state.favorites)


def remove_favorite_by_key(target_key):
    removed = False
    new_favorites = []

    for fav in st.session_state.favorites:
        fav_key = make_favorite_key(fav)
        if not removed and fav_key == target_key:
            removed = True
            continue
        new_favorites.append(fav)

    st.session_state.favorites = new_favorites


def normalize_place_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    if url.startswith("//"):
        return "https:" + url
    return url


# -----------------------------------------------
# 검색 히스토리
# -----------------------------------------------
def add_search_history(q):
    if q and q not in st.session_state.search_history:
        st.session_state.search_history.insert(0, q)
        st.session_state.search_history = st.session_state.search_history[:5]

# -----------------------------------------------
# 렌더 헬퍼
# -----------------------------------------------
def render_rank_badge(r):
    if r == 1:
        return "<span class='top-badge top-1'>TOP 1</span>"
    if r == 2:
        return "<span class='top-badge top-2'>TOP 2</span>"
    if r == 3:
        return "<span class='top-badge top-3'>TOP 3</span>"
    return ""


def render_tags(tags):
    if not tags:
        return "<span style='color:#bbb;font-size:13px;'>태그 없음</span>"
    return " ".join([f'<span class="tag">{t}</span>' for t in tags])


def render_score_card(score, grade, gdesc):
    start, end = GRADE_GRADIENT.get(grade, ("#FF6B35", "#FF8C61"))
    return (
        f"<div class='score-card' style='background:linear-gradient(135deg,{start},{end});"
        f"border:2px solid rgba(255,255,255,0.15);'>"
        f"<div style='font-size:36px;font-weight:bold;line-height:1.1;'>{score}</div>"
        f"<div style='font-size:11px;opacity:.85;margin-top:2px;'>추천 적합도</div>"
        f"<div style='font-size:13px;margin-top:6px;font-weight:bold;'>{grade}</div>"
        f"<div style='font-size:11px;opacity:.85;'>{gdesc}</div></div>"
    )


def render_fav_card(fav):
    fav_name_raw = str(fav.get("place_name", "")).strip()
    fav_name = html.escape(fav_name_raw)
    fav_cat = html.escape(str(fav.get("category_name", "")).strip())
    fav_addr = html.escape(
        str(fav.get("road_address_name") or fav.get("address_name") or "주소 정보 없음")
    )
    fav_grade = str(fav.get("grade", "")).strip()
    fav_score = fav.get("quality_score", 0)

    fav_url = normalize_place_url(fav.get("place_url", ""))
    fav_url_html = html.escape(fav_url, quote=True)

    grade_color = MARKER_COLOR.get(fav_grade, "#7B8FA1")
    score_bg, _ = GRADE_GRADIENT.get(fav_grade, ("#FF6B35", "#FF8C61"))

    if isinstance(fav_score, float):
        score_text = f"{fav_score:.1f}점"
    else:
        score_text = f"{fav_score}점"

    parts = [
        '<div class="fav-card">',
        '<div class="fav-card-header">',
        f'<span class="fav-grade-dot" style="background:{grade_color};"></span>',
        f'<span class="fav-card-name">{fav_name}</span>',
        '</div>',
        f'<div class="fav-card-category">{fav_cat if fav_cat else "카테고리 없음"}</div>',
        f'<div class="fav-card-addr">📍 {fav_addr}</div>',
        f'<span class="fav-card-score" style="background:{score_bg};">{score_text}</span>',
    ]

    if fav_url:
        parts.append(
            f'<a class="fav-map-link" href="{fav_url_html}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'카카오맵에서 보기 ↗'
            f'</a>'
        )
    else:
        parts.append('<span class="fav-map-link-disabled">링크 없음</span>')

    parts.append('</div>')
    return "".join(parts)


# -----------------------------------------------
# 검색 실행
# -----------------------------------------------
def do_search(query, total_size=15):
    result = cached_search_multi(query, total_size)
    if result["error"]:
        st.session_state.results_df = None
        return "ERROR", result["error"]

    docs = result["documents"]
    if not docs:
        st.session_state.results_df = None
        return "EMPTY", None

    df = analyzer.analyze_data(docs, query=query)
    st.session_state.results_df = df
    st.session_state.last_query = query
    add_search_history(query)
    return ("FEW" if len(df) < 3 else "OK"), df


def run_search(query, total_size=15):
    with st.spinner(f"'{query}' 검색 중..."):
        status, extra = do_search(query, total_size=total_size)

    if status == "ERROR":
        st.session_state["_last_error"] = extra
        st.session_state["_last_query"] = None
    elif status in ("EMPTY", "FEW"):
        st.session_state["_last_error"] = None
        st.session_state["_last_query"] = query
    else:
        st.session_state["_last_error"] = None
        st.session_state["_last_query"] = None

# -----------------------------------------------
# 차트
# -----------------------------------------------
def chart_grade_distribution(df):
    if not PLOTLY_AVAILABLE:
        return None
    gc = df["grade"].value_counts()
    labels = [g for g in GRADE_ORDER if g in gc.index]
    values = [gc[g] for g in labels]
    colors = [GRADE_COLOR[g] for g in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=.55,
        marker=dict(colors=colors, line=dict(color="#fff", width=2)),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value}곳<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="등급 분포", font=dict(size=16)),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-.2),
        margin=dict(t=50, b=10, l=10, r=10),
        height=320,
    )
    return fig


def chart_category_distribution(df):
    if not PLOTLY_AVAILABLE:
        return None
    cc = df["category_name"].replace("", "없음").value_counts().head(8).reset_index()
    cc.columns = ["카테고리", "수"]
    cc = cc.sort_values("수")
    fig = px.bar(
        cc, x="수", y="카테고리", orientation="h",
        color="수", color_continuous_scale=["#FFE0CC", "#FF6B35"], text="수",
    )
    fig.update_traces(
        texttemplate="%{text}곳", textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x}곳<extra></extra>",
    )
    fig.update_layout(
        title=dict(text="카테고리 분포", font=dict(size=16)),
        xaxis_title="장소 수", yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(t=50, b=20, l=10, r=60),
        height=340,
        plot_bgcolor="#FFF8F0", paper_bgcolor="#FFF8F0",
    )
    return fig


def chart_tag_distribution(df):
    if not PLOTLY_AVAILABLE:
        return None
    at = [t for tags in df["purpose_tags"] for t in tags]
    if not at:
        return None
    tc = pd.Series(at).value_counts().reset_index()
    tc.columns = ["태그", "수"]
    fig = px.bar(
        tc, x="태그", y="수", color="태그", text="수",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(
        texttemplate="%{text}곳", textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y}곳<extra></extra>",
        showlegend=False,
    )
    fig.update_layout(
        title=dict(text="태그 분포", font=dict(size=16)),
        xaxis_title="", yaxis_title="장소 수",
        margin=dict(t=50, b=20, l=10, r=10),
        height=320,
        plot_bgcolor="#FFF8F0", paper_bgcolor="#FFF8F0",
    )
    return fig


def chart_score_histogram(df):
    if not PLOTLY_AVAILABLE:
        return None
    fig = px.histogram(
        df, x="quality_score", color="grade", nbins=15,
        category_orders={"grade": GRADE_ORDER},
        color_discrete_map=GRADE_COLOR,
        labels={"quality_score": "추천 적합도", "grade": "등급"},
        hover_data=["place_name"],
    )
    for s, l, c in [(80, "S등급", "#FF4500"), (68, "A등급", "#FF8C00"), (50, "B등급", "#32CD32")]:
        fig.add_vline(
            x=s, line_dash="dash", line_color=c, line_width=1.5,
            annotation_text=l, annotation_position="top",
            annotation_font_size=11,
        )
    fig.update_layout(
        title=dict(text="추천 적합도 분포", font=dict(size=16)),
        xaxis_title="점수", yaxis_title="장소 수",
        xaxis=dict(range=[0, 105]),
        bargap=.1, legend_title="등급",
        margin=dict(t=60, b=20, l=10, r=10),
        height=340,
        plot_bgcolor="#FFF8F0", paper_bgcolor="#FFF8F0",
        hovermode="x unified",
    )
    return fig


def chart_score_ranking(df):
    if not PLOTLY_AVAILABLE:
        return None
    top = df.nlargest(10, "quality_score").sort_values("quality_score")
    colors = [GRADE_COLOR.get(g, "#FF6B35") for g in top["grade"]]
    fig = go.Figure(go.Bar(
        x=top["quality_score"], y=top["place_name"],
        orientation="h", marker_color=colors,
        text=top["quality_score"],
        texttemplate="%{text}점", textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x}점<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="적합도 TOP 10", font=dict(size=16)),
        xaxis_title="점수", xaxis=dict(range=[0, 110]),
        yaxis_title="",
        margin=dict(t=50, b=20, l=10, r=60),
        height=380,
        plot_bgcolor="#FFF8F0", paper_bgcolor="#FFF8F0",
    )
    return fig

# -----------------------------------------------
# 앱 제목
# -----------------------------------------------
st.title("카페 & 맛집 추천기")
st.markdown("> 카카오맵 실시간 데이터로 장소를 추천해드려요!")
st.caption("추천 적합도는 검색 적합도와 정보 완성도를 기반으로 계산됩니다.")
st.divider()


# -----------------------------------------------
# 사이드바
# -----------------------------------------------
with st.sidebar:
    st.header("🔍 검색 조건")

    with st.form("search_form"):
        region = st.text_input("지역 또는 메뉴", value="성수", placeholder="예: 홍대, 강남, 제주")
        place_type = st.selectbox(
            "유형",
            ["카페", "맛집", "브런치", "디저트", "베이커리",
             "파인다이닝", "한식", "양식", "중식", "일식", "술집"],
        )
        feature = st.selectbox(
            "매장 특징 (선택)",
            ["없음", "핸드드립", "로스터리", "스페셜티", "뷰맛집",
             "루프탑", "테라스", "북카페", "대형카페", "애견동반",
             "24시", "호프", "와인바", "칵테일바", "일본식주점"],
        )
        # ✅ 수정: 중복 줄 제거
        result_size = st.selectbox(
            "결과 수",
            [15, 30, 45],
            index=0,
            help="표시할 검색 결과의 개수를 선택하세요.",
        )
        submitted = st.form_submit_button(
            "실시간 검색", type="primary", use_container_width=True,
        )

    if submitted:
        parts = [region.strip(), place_type]
        if feature != "없음":
            parts.append(feature)
        run_search(" ".join(parts), total_size=result_size)
        st.rerun()

    st.divider()

    # ── 빠른 검색 ────────────────────────────
    st.markdown("**⚡ 빠른 검색**")
    quick_searches = [
        ("성수 카페", "성수 카페"),
        ("홍대 브런치", "홍대 브런치"),
        ("강남 맛집", "강남 맛집"),
        ("연남동 디저트", "연남동 디저트"),
        ("이태원 루프탑", "이태원 루프탑"),
        ("제주 카페", "제주 카페"),
    ]
    for i, (label, q) in enumerate(quick_searches):
        if st.button(label, use_container_width=True, key=f"quick_{i}"):
            run_search(q, total_size=15)
            st.rerun()

    st.divider()

    # ── 최근 검색어 ──────────────────────────
    if st.session_state.search_history:
        st.markdown("**🕓 최근 검색어**")
        for q in st.session_state.search_history:
            if st.button(f"🔁 {q}", use_container_width=True, key=f"hist_{q}"):
                run_search(q, total_size=15)
                st.rerun()
        st.divider()

    # ── 즐겨찾기 (카드형 UI) ─────────────────
    fav_count = len(st.session_state.favorites)
    st.markdown(f"**⭐ 즐겨찾기** `{fav_count}곳`")

    if not st.session_state.favorites:
        st.markdown(
            "<div class='fav-empty'>"
            "<div class='fav-empty-icon'>⭐</div>"
            "아직 즐겨찾기한 장소가 없어요"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        for fav in st.session_state.favorites:
            st.markdown(render_fav_card(fav), unsafe_allow_html=True)

        st.markdown("")
        if st.button("🗑️ 즐겨찾기 초기화", use_container_width=True, type="secondary"):
            st.session_state.favorites = []
            st.rerun()

# -----------------------------------------------
# 메인 화면
# -----------------------------------------------
df = st.session_state.results_df
last_error = st.session_state.get("_last_error")
last_query = st.session_state.get("_last_query")

if last_error:
    st.error(last_error)

elif last_query and (df is None or len(df) < 3):
    if df is None:
        st.markdown(
            f"<div style='text-align:center;padding:50px 20px;"
            f"background:#FFF8F0;border-radius:20px;"
            f"border:2px dashed #FFB088;margin:20px 0;'>"
            f"<div style='font-size:36px;'>검색 결과 없음</div>"
            f"<div style='font-size:16px;color:#E65100;margin-top:12px;'>"
            f"'{last_query}'에 대한 결과를 찾지 못했어요</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"'{last_query}' 검색 결과가 {len(df)}건밖에 없어요.")

    parts = last_query.strip().split()
    suggestions = []
    if len(parts) >= 2:
        a, k = parts[0], parts[1]
        suggestions = [
            (f"{a} 맛집", f"'{a}' 맛집"),
            (f"{a} 음식점", f"'{a}' 음식점"),
            (a, f"'{a}' 전체"),
            (k, f"'{k}'만"),
            (f"서울 {k}", f"서울 {k}"),
            (f"{a} 디저트", f"'{a}' 디저트"),
        ]
    elif len(parts) == 1:
        a = parts[0]
        suggestions = [
            (f"{a} 카페", f"'{a}' 카페"),
            (f"{a} 맛집", f"'{a}' 맛집"),
            (f"{a} 음식점", f"'{a}' 음식점"),
        ]
    if suggestions:
        st.markdown("#### 이런 검색은 어떠세요?")
        sc = st.columns(3)
        for i, (qt, lb) in enumerate(suggestions[:6]):
            with sc[i % 3]:
                if st.button(lb, use_container_width=True, key=f"sug_{i}"):
                    run_search(qt, total_size=15)
                    st.rerun()

elif df is None:
    st.info("왼쪽에서 검색 조건을 설정하고 검색 버튼을 눌러보세요!")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### ☕ 카페 탐방\n성수, 홍대, 연남동...")
    with c2:
        st.markdown("### 🍽️ 맛집 탐방\n강남, 이태원, 을지로...")
    with c3:
        st.markdown("### 🗺️ 전국 어디든\n제주, 부산, 전주...")

# -----------------------------------------------
# 검색 결과
# -----------------------------------------------
if df is not None:
    total = len(df)
    s_cnt = len(df[df["grade"] == "S등급"])
    a_cnt = len(df[df["grade"] == "A등급"])
    top = df.iloc[0]["place_name"] if total > 0 else "-"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("찾은 장소", f"{total}곳")
    with c2:
        st.metric("1등 장소", top)
    with c3:
        st.metric("S등급", f"{s_cnt}곳")
    with c4:
        st.metric("A등급", f"{a_cnt}곳")
    st.divider()

    tab_list, tab_map, tab_fav, tab_summary = st.tabs(
        ["📋 추천 리스트", "🗺️ 지도", "⭐ 즐겨찾기", "📊 요약 분석"]
    )

    # ====== 탭 1: 추천 리스트 ======
    with tab_list:
        with st.expander("🔧 필터 & 정렬", expanded=True):
            fc1, fc2, fc3, fc4, fc5 = st.columns(5)
            with fc1:
                gf = st.selectbox("등급", ["전체"] + GRADE_ORDER, key="gf")
            with fc2:
                at = set()
                for t in df["purpose_tags"]:
                    at.update(t)
                tf = st.selectbox("태그", ["전체"] + sorted(at), key="tf")
            with fc3:
                hp = st.checkbox("전화번호 있는 곳만", key="hp")
            with fc4:
                hr = st.checkbox("도로명 주소 있는 곳만", key="hr")
            with fc5:
                sb = st.selectbox("정렬", ["추천순", "이름순", "카테고리순"], key="sb")

        fdf = analyzer.filter_data(df, gf, tf, hp, hr)
        fdf = analyzer.sort_data(fdf, sb)
        st.markdown(f"**총 {len(fdf)}곳** (전체 {len(df)}곳 중)")

        if fdf.empty:
            st.info("필터 조건에 맞는 장소가 없어요.")
        else:
            for _, row in fdf.iterrows():
                with st.container():
                    ci, cs = st.columns([4, 1])
                    with ci:
                        badge = render_rank_badge(int(row["rank"]))
                        st.markdown(
                            f"<h3 style='margin-bottom:4px;'>{row['place_name']}{badge}</h3>",
                            unsafe_allow_html=True,
                        )
                        r1, r2, r3 = st.columns(3)
                        with r1:
                            st.caption(row["category_name"] or "카테고리 없음")
                        with r2:
                            st.caption(
                                row.get("road_address_name")
                                or row.get("address_name")
                                or "주소 없음"
                            )
                        with r3:
                            st.caption(row.get("phone", "") or "전화번호 없음")

                        if row.get("place_url"):
                            st.markdown(f"[카카오맵에서 보기]({normalize_place_url(row['place_url'])})")

                        st.markdown(render_tags(row["purpose_tags"]), unsafe_allow_html=True)

                        with st.expander("점수 산정 근거 보기"):
                            for reason in row.get("score_reasons", []):
                                st.markdown(f"- {reason}")

                        fl = (
                            "⭐ 즐겨찾기 해제"
                            if is_favorite(row)
                            else "☆ 즐겨찾기 추가"
                        )
                        if st.button(fl, key=f"fav_{row['place_name']}_{row['rank']}"):
                            toggle_favorite(row)
                            st.rerun()

                    with cs:
                        st.markdown(
                            render_score_card(
                                row["quality_score"],
                                row["grade"],
                                row["grade_desc"],
                            ),
                            unsafe_allow_html=True,
                        )
                st.markdown("<hr class='card-divider'>", unsafe_allow_html=True)

    # ====== 탭 2: 지도 ======
    with tab_map:
        st.subheader("🗺️ 지도")
        st.caption("검색된 장소의 위치를 확인하세요. 마커를 클릭하면 상세 정보를 볼 수 있어요.")

        map_df = df.copy()
        map_df = map_df[(map_df["x"] != "") & (map_df["y"] != "")]

        try:
            map_df["lon"] = map_df["x"].astype(float)
            map_df["lat"] = map_df["y"].astype(float)
            map_df = map_df[
                (map_df["lat"] > 30) & (map_df["lat"] < 40)
                & (map_df["lon"] > 120) & (map_df["lon"] < 135)
            ]
        except Exception:
            map_df = pd.DataFrame()

        if map_df.empty:
            st.warning("지도에 표시할 좌표 정보가 없어요.")
        else:
            try:
                import folium
                from folium import DivIcon
                from streamlit_folium import st_folium

                center_lat = map_df["lat"].mean()
                center_lon = map_df["lon"].mean()

                m = folium.Map(
                    location=[center_lat, center_lon],
                    zoom_start=14,
                    tiles="OpenStreetMap",
                )

                for _, row in map_df.iterrows():
                    rank_num = int(row["rank"])
                    grade = row.get("grade", "")
                    color = MARKER_COLOR.get(grade, "#E63946")
                    p_name = row["place_name"]
                    addr = row.get("road_address_name") or row.get("address_name") or ""
                    score = row["quality_score"]
                    p_url = normalize_place_url(row.get("place_url", ""))

                    icon_html = f"""
                    <div style="
                        width:36px; height:36px; border-radius:50%;
                        background:{color}; color:white;
                        display:flex; align-items:center; justify-content:center;
                        font-weight:bold; font-size:16px;
                        font-family:Arial Black, sans-serif;
                        box-shadow:0 3px 8px rgba(0,0,0,0.3);
                        border:2px solid white;
                    ">{rank_num}</div>"""

                    if p_url:
                        popup_html = f"""
                        <div style="font-family:sans-serif;min-width:180px;">
                            <b style="font-size:14px;">{rank_num}. {p_name}</b><br>
                            <span style="color:#666;font-size:12px;">{grade} | 적합도 {score}점</span><br>
                            <span style="font-size:12px;">{addr}</span><br>
                            <a href="{p_url}" target="_blank"
                               style="color:#E63946;font-size:12px;font-weight:bold;">
                               카카오맵에서 보기</a>
                        </div>"""
                    else:
                        popup_html = f"""
                        <div style="font-family:sans-serif;min-width:180px;">
                            <b style="font-size:14px;">{rank_num}. {p_name}</b><br>
                            <span style="color:#666;font-size:12px;">{grade} | 적합도 {score}점</span><br>
                            <span style="font-size:12px;">{addr}</span>
                        </div>"""

                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        icon=DivIcon(html=icon_html, icon_size=(36, 36), icon_anchor=(18, 18)),
                        popup=folium.Popup(popup_html, max_width=250),
                        tooltip=f"{rank_num}. {p_name}",
                    ).add_to(m)

                st_folium(m, use_container_width=True, height=560)

                st.markdown(
                    "<div style='display:flex;gap:20px;margin:8px 0;font-size:13px;color:#555;'>"
                    "<span><span style='display:inline-block;width:14px;height:14px;"
                    "border-radius:50%;background:#E63946;vertical-align:middle;'></span> S등급</span>"
                    "<span><span style='display:inline-block;width:14px;height:14px;"
                    "border-radius:50%;background:#F4845F;vertical-align:middle;'></span> A등급</span>"
                    "<span><span style='display:inline-block;width:14px;height:14px;"
                    "border-radius:50%;background:#2EC4B6;vertical-align:middle;'></span> B등급</span>"
                    "<span><span style='display:inline-block;width:14px;height:14px;"
                    "border-radius:50%;background:#7B8FA1;vertical-align:middle;'></span> C등급</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"총 {len(map_df)}곳 표시 | 원을 클릭하면 자세한 정보를 볼 수 있어요")

            except ImportError:
                st.warning("지도 마커 표시에 추가 설치가 필요해요.\n\n```\npip install folium streamlit-folium\n```")
                st.map(map_df[["lat", "lon"]], zoom=13)
                st.caption(f"총 {len(map_df)}곳 표시")

        st.divider()
        st.markdown("#### 장소 목록")

        if not map_df.empty:
            for _, row in map_df.iterrows():
                rank_num = int(row["rank"])
                grade_c = MARKER_COLOR.get(row.get("grade", ""), "#E63946")
                p_url = normalize_place_url(row.get("place_url", ""))
                p_name = row["place_name"]
                addr = row.get("road_address_name") or row.get("address_name") or ""
                score = row["quality_score"]
                grade = row.get("grade", "")

                col_num, col_info, col_btn = st.columns([0.5, 3.8, 1])
                with col_num:
                    st.markdown(
                        f"<div style='width:34px;height:34px;border-radius:50%;"
                        f"background:{grade_c};color:#fff;"
                        f"display:flex;align-items:center;justify-content:center;"
                        f"font-weight:bold;font-size:15px;margin-top:4px;"
                        f"box-shadow:0 2px 8px rgba(0,0,0,0.15);'>{rank_num}</div>",
                        unsafe_allow_html=True,
                    )
                with col_info:
                    st.markdown(
                        f"<div style='line-height:1.25;margin-top:2px;'>"
                        f"<div><b>{p_name}</b> "
                        f"<span style='color:#888;font-size:13px;'>| {grade} | 적합도 {score}점</span></div>"
                        f"<div style='color:#999;font-size:12px;margin-top:1px;'>{addr}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if p_url:
                        st.link_button("카카오맵", p_url)

    # ====== 탭 3: 즐겨찾기 ======
    with tab_fav:
        st.subheader("⭐ 즐겨찾기")
        if not st.session_state.favorites:
            st.markdown(
                "<div style='text-align:center;padding:60px 20px;background:#FFFAF5;"
                "border-radius:20px;border:2px dashed #FFDAB9;margin:20px 0;'>"
                "<div style='font-size:48px;margin-bottom:10px;'>⭐</div>"
                "<div style='font-size:18px;color:#E65100;font-weight:600;'>아직 즐겨찾기한 장소가 없어요</div>"
                "<div style='font-size:14px;color:#999;margin-top:8px;'>"
                "추천 리스트에서 ☆ 버튼을 눌러 추가해보세요!</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**총 {len(st.session_state.favorites)}곳**")

            if st.button("📥 전체 초기화", type="secondary"):
                st.session_state.favorites = []
                st.rerun()

            # ✅ 수정: 탭 블록 안으로 들여쓰기 정렬
            for idx, fav in enumerate(st.session_state.favorites):
                st.markdown(render_fav_card(fav), unsafe_allow_html=True)
                st.markdown("<div class='fav-del-wrap'>", unsafe_allow_html=True)
                if st.button("✕", key=f"sfav_del_{idx}"):
                    remove_favorite_by_key(make_favorite_key(fav))
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ====== 탭 4: 요약 분석 ======
    with tab_summary:
        st.subheader("📊 요약 분석")
        if not PLOTLY_AVAILABLE:
            st.warning("차트 표시를 위해 plotly를 설치해주세요: pip install plotly")

        total = len(df)
        ph = len(df[df["phone"] != ""])
        rd = len(df[df["road_address_name"] != ""])
        avg = round(df["quality_score"].mean(), 1)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("총 장소 수", f"{total}곳")
        with m2:
            st.metric("평균 적합도", f"{avg}점")
        with m3:
            st.metric("전화번호 있음", f"{ph}곳")
        with m4:
            st.metric("도로명 주소 있음", f"{rd}곳")
        st.divider()

        if PLOTLY_AVAILABLE:
            st.markdown("#### 등급 분포 & 적합도 TOP 10")
            ch1, ch2 = st.columns([1, 1.6])
            with ch1:
                fig = chart_grade_distribution(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            with ch2:
                fig = chart_score_ranking(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.markdown("#### 카테고리 & 태그 분포")
            ch3, ch4 = st.columns(2)
            with ch3:
                fig = chart_category_distribution(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            with ch4:
                fig = chart_tag_distribution(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("태그 없음")

            st.divider()
            st.markdown("#### 추천 적합도 분포")
            fig = chart_score_histogram(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            st.divider()

        st.markdown("#### 전체 결과 테이블")
        sc = ["rank", "place_name", "category_name", "address_name",
              "phone", "quality_score", "grade"]
        sc = [c for c in sc if c in df.columns]
        st.dataframe(
            df[sc].rename(columns={
                "rank": "순위",
                "place_name": "장소명",
                "category_name": "카테고리",
                "address_name": "주소",
                "phone": "전화번호",
                "quality_score": "추천 적합도",
                "grade": "등급",
            }),
            use_container_width=True,
            hide_index=True,
        )