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
    """query 문자열에서 유형/특징 키워드 추출"""
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
        # 유형 없는 검색이라도 카테고리는 있으면 기본점
        score += 15
        reasons.append("카테고리 정보 있음 +15")

    # ── 3) 검색 특징 일치도 (최대 10점) ────────────────────────
    if q_features:
        for f in q_features:
            if has_any(text, FEATURE_RULES[f]):
                score += 10
                reasons.append(f"검색 특징 '{f}' 일치 +10")
                break   # 첫 번째 매칭만 반영

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

    # 카카오 정확도 순위 보존 (API 반환 순서 = 정확도 순)
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