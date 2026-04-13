"""
Query Expansion using Law Terms Dictionary
법률 용어 사전을 활용한 쿼리 확장 모듈
"""

import json
import logging
from pathlib import Path
from google.genai import types
from .ai.handler import generate_with_fallback

def load_law_terms_dictionary(file_path=None):
    """법률 용어 사전 로드"""
    if file_path is None:
        # 기본 경로: 프로젝트 루트의 law_terms_dictionary.json
        project_root = Path(__file__).parent.parent
        file_path = project_root / "law_terms_dictionary.json"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("용어_목록", [])
    except Exception as e:
        logging.error(f"법률 용어 사전 로드 실패: {str(e)}")
        return []


def generate_similar_questions(client, user_query, law_terms):
    """Gemini 2.5 Flash를 사용하여 유사질문 3개 생성"""
    # 용어 목록을 문자열로 변환 (너무 길면 일부만 사용)
    terms_str = ", ".join(law_terms[:200])  # 처음 200개만 사용하여 프롬프트 크기 제한

    prompt = f"""# 역할
당신은 관세법 전문가입니다. 사용자의 질문을 분석하여 유사한 질문을 생성하는 역할을 합니다.

# 작업
사용자 질문과 동일한 의도를 가진 유사질문 3개를 생성하세요.

# 제약사항
1. 반드시 아래 '법률 용어 목록'에서 관련 용어를 선택하여 사용하세요
2. 유사질문은 원래 질문과 의도는 같지만 표현 방식을 다르게 해야 합니다
3. 각 질문은 한 줄로 작성하세요
4. 번호나 불릿 없이 질문만 작성하세요
5. 정확히 3개의 질문만 생성하세요

# 법률 용어 목록
{terms_str}

# 사용자 질문
{user_query}

# 출력 형식 (예시)
질문1
질문2
질문3

위 형식으로 3개 질문만 출력하세요."""

    try:
        # Fallback 모델 리스트 정의
        models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
        
        response = generate_with_fallback(
            client=client,
            models=models,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                top_k=10,
                top_p=0.9,
                max_output_tokens=500
            )
        )

        # 디버그: 원본 응답 출력
        logging.info(f"[DEBUG] Gemini 원본 응답 (유사질문): {response.text[:500]}")

        # 응답 파싱 (줄바꿈으로 분리하여 3개 질문 추출)
        similar_questions = []
        lines = response.text.strip().split('\n')
        logging.info(f"[DEBUG] 파싱 전 줄 수: {len(lines)}")

        for line in lines:
            line = line.strip()
            # 번호 제거 (1. 2. 3. 또는 - 등)
            if line and not line.startswith('#'):
                # 숫자와 점 제거
                cleaned = line.lstrip('0123456789.-) ').strip()
                if cleaned:
                    similar_questions.append(cleaned)

        # 정확히 3개만 반환
        similar_questions = similar_questions[:3]

        # 3개 미만이면 원본 질문으로 채움
        while len(similar_questions) < 3:
            similar_questions.append(user_query)

        logging.info(f"유사질문 생성 완료: {similar_questions}")
        return similar_questions

    except Exception as e:
        logging.error(f"유사질문 생성 실패: {str(e)}")
        # 실패 시 원본 질문 3번 반복
        return [user_query, user_query, user_query]


def extract_key_terms(client, user_query, law_terms):
    """Gemini 2.5 Flash를 사용하여 핵심어 5개 이내 추출"""
    terms_str = ", ".join(law_terms)

    prompt = f"""# 역할
당신은 관세법 전문가입니다. 사용자의 질문에서 핵심 법률 용어를 추출하는 역할을 합니다.

# 작업
사용자 질문에서 핵심이 되는 법률 용어를 추출하세요.

# 제약사항
1. 아래 '법률 용어 목록'을 참고하여 관련 용어를 선택하세요
2. 사용자 질문과 직접 관련된 용어만 선택하세요
3. 최대 5개까지 선택하세요 (적어도 2-3개는 선택하세요)
4. 각 용어는 한 줄에 하나씩 작성하세요
5. 번호나 불릿, 설명 없이 용어만 작성하세요

# 법률 용어 목록
{terms_str}

# 사용자 질문
{user_query}

# 출력 형식 (예시)
용어1
용어2
용어3

위 형식으로 핵심 용어만 출력하세요. 반드시 2개 이상 선택하세요."""

    try:
        # Fallback 모델 리스트 정의
        models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

        response = generate_with_fallback(
            client=client,
            models=models,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                top_k=5,
                top_p=0.8,
                max_output_tokens=300
            )
        )

        # 디버그: 원본 응답 출력
        logging.info(f"[DEBUG] Gemini 원본 응답 (핵심어): {response.text[:500]}")

        # 응답 파싱
        key_terms = []
        lines = response.text.strip().split('\n')
        logging.info(f"[DEBUG] 파싱 전 줄 수: {len(lines)}")

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 숫자와 점 제거
                cleaned = line.lstrip('0123456789.-) ').strip()
                if cleaned:
                    key_terms.append(cleaned)

        # 최대 5개만 반환
        key_terms = key_terms[:5]

        logging.info(f"핵심어 추출 완료: {key_terms}")
        return key_terms

    except Exception as e:
        logging.error(f"핵심어 추출 실패: {str(e)}")
        return []


def expand_query(client, user_query, law_terms):
    """
    쿼리 확장: 사용자 질문 + 유사질문 3개 + 핵심어 5개 이내

    Returns:
        dict: {
            "original_query": str,
            "similar_questions": [str, str, str],
            "key_terms": [str, ...],
            "keyword_group": [str, ...]  # 전체 키워드 그룹
        }
    """
    logging.info(f"쿼리 확장 시작: {user_query}")

    # 1. 유사질문 3개 생성
    similar_questions = generate_similar_questions(client, user_query, law_terms)

    # 2. 핵심어 5개 이내 추출
    key_terms = extract_key_terms(client, user_query, law_terms)

    # 3. 키워드 그룹 구성
    keyword_group = [user_query] + similar_questions + key_terms

    result = {
        "original_query": user_query,
        "similar_questions": similar_questions,
        "key_terms": key_terms,
        "keyword_group": keyword_group
    }

    logging.info(f"쿼리 확장 완료 - 총 키워드 수: {len(keyword_group)}")
    logging.info(f"  - 유사질문: {len(similar_questions)}개")
    logging.info(f"  - 핵심어: {len(key_terms)}개")

    return result
