# analyzer.py
import pandas as pd

def calculate_api_score(row):
    score = 0

    # 1. 카테고리 점수 (카페/맛집 여부)
    category = str(row.get('category_name', ''))
    if '카페' in category:
        score += 30
    elif '음식점' in category or '맛집' in category:
        score += 25
    else:
        score += 10

    # 2. 장소명 신뢰도 (이름 길이 기반)
    name = str(row.get('place_name', ''))
    if len(name) >= 2:
        score += 10

    # 3. 전화번호 있으면 +10 (실제 운영중인 가게)
    phone = str(row.get('phone', ''))
    if phone and phone != 'nan':
        score += 10

    # 4. 도로명 주소 있으면 +10
    road_address = str(row.get('road_address_name', ''))
    if road_address and road_address != 'nan':
        score += 10

    return round(score, 1)

def get_grade(score):
    if score >= 55: return "⭐ S등급 (강추)"
    elif score >= 45: return "🌟 A등급 (추천)"
    elif score >= 35: return "✅ B등급 (괜찮음)"
    else: return "🤔 C등급 (참고용)"

def get_purpose_tags(row):
    tags = []
    category = str(row.get('category_name', ''))
    place_name = str(row.get('place_name', ''))

    if '카페' in category: tags.append("☕ 카페")
    if '베이커리' in category: tags.append("🥐 베이커리")
    if '디저트' in category: tags.append("🍰 디저트")
    if '브런치' in place_name or '브런치' in category: tags.append("🥞 브런치")
    if '루프탑' in place_name: tags.append("🌇 루프탑")
    if '한식' in category: tags.append("🍚 한식")
    if '양식' in category: tags.append("🍝 양식")
    if '일식' in category: tags.append("🍱 일식")

    return tags

def analyze_data(places_list):
    """API 결과를 데이터프레임으로 변환하고 점수 매기기"""
    if not places_list:
        return pd.DataFrame()

    df = pd.DataFrame(places_list)
    df['quality_score'] = df.apply(calculate_api_score, axis=1)
    df['grade'] = df['quality_score'].apply(get_grade)
    df['purpose_tags'] = df.apply(get_purpose_tags, axis=1)
    df = df.sort_values('quality_score', ascending=False)

    return df