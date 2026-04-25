#!/usr/bin/env python3
"""
고흥군 소록마을 가상 데이터셋 생성기
심야 화재 대응 Agentic OS MVP
"""

import json
import random
import os
from datetime import datetime

random.seed(42)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "goheung_dataset.json")

# ── 정적 참조 데이터 ──────────────────────────────────────────────────────────

RESIDENT_DATA = [
    {"name": "마순례", "age": 84, "gender": "여", "conditions": ["난청", "거동불편", "당뇨"], "lives_alone": True,  "building_id": "BLDG-007"},
    {"name": "김복순", "age": 79, "gender": "여", "conditions": ["치매", "고혈압"],              "lives_alone": True,  "building_id": "BLDG-003"},
    {"name": "이봉길", "age": 78, "gender": "남", "conditions": ["치매", "고혈압", "난청"],       "lives_alone": True,  "building_id": "BLDG-003"},
    {"name": "박말순", "age": 82, "gender": "여", "conditions": ["뇌졸중 후유증", "고혈압"],      "lives_alone": True,  "building_id": "BLDG-009"},
    {"name": "정순자", "age": 76, "gender": "여", "conditions": ["당뇨", "관절염", "거동불편"],   "lives_alone": True,  "building_id": "BLDG-009"},
    {"name": "최덕현", "age": 77, "gender": "남", "conditions": ["당뇨", "신부전"],              "lives_alone": False, "building_id": "BLDG-004"},
    {"name": "조만수", "age": 81, "gender": "남", "conditions": ["난청", "심장질환"],            "lives_alone": True,  "building_id": "BLDG-006"},
    {"name": "강덕현", "age": 75, "gender": "남", "conditions": ["당뇨", "관절염"],              "lives_alone": False, "building_id": "BLDG-010"},
    {"name": "윤금순", "age": 73, "gender": "여", "conditions": ["고혈압", "당뇨"],              "lives_alone": False, "building_id": "BLDG-010"},
    {"name": "허창호", "age": 83, "gender": "남", "conditions": ["치매", "거동불편", "요실금"],   "lives_alone": False, "building_id": "BLDG-011"},
    {"name": "마창수", "age": 80, "gender": "남", "conditions": ["만성폐쇄성폐질환", "당뇨"],    "lives_alone": True,  "building_id": "BLDG-012"},
    {"name": "김덕배", "age": 72, "gender": "남", "conditions": ["고혈압", "심장질환"],          "lives_alone": True,  "building_id": "BLDG-001"},
    {"name": "박용철", "age": 85, "gender": "남", "conditions": ["난청", "치매", "심장질환"],    "lives_alone": True,  "building_id": "BLDG-002"},
    {"name": "정기동", "age": 70, "gender": "남", "conditions": ["당뇨", "관절염"],              "lives_alone": False, "building_id": "BLDG-005"},
    {"name": "조옥순", "age": 88, "gender": "여", "conditions": ["난청", "치매", "고혈압", "거동불편"], "lives_alone": True, "building_id": "BLDG-008"},
]

BUILDING_DATA = [
    {"building_id": "BLDG-001", "address": "전남 고흥군 도양읍 소록마을 1-2",  "material": "조적조",              "access_road_width_m": 3.5, "floor_count": 1, "has_fire_detector": True,  "street_lighting": True,  "year_built": 1985},
    {"building_id": "BLDG-002", "address": "전남 고흥군 도양읍 소록마을 3-5",  "material": "샌드위치 패널",       "access_road_width_m": 2.0, "floor_count": 1, "has_fire_detector": False, "street_lighting": False, "year_built": 1998},
    {"building_id": "BLDG-003", "address": "전남 고흥군 도양읍 소록마을 12-3", "material": "경량 목구조",         "access_road_width_m": 2.5, "floor_count": 1, "has_fire_detector": False, "street_lighting": True,  "year_built": 1978},
    {"building_id": "BLDG-004", "address": "전남 고흥군 도양읍 소록마을 15-8", "material": "조적조",              "access_road_width_m": 4.0, "floor_count": 1, "has_fire_detector": False, "street_lighting": True,  "year_built": 1990},
    {"building_id": "BLDG-005", "address": "전남 고흥군 도양읍 소록마을 18-4", "material": "철근콘크리트",        "access_road_width_m": 4.0, "floor_count": 2, "has_fire_detector": True,  "street_lighting": True,  "year_built": 2003},
    {"building_id": "BLDG-006", "address": "전남 고흥군 도양읍 소록마을 7-1",  "material": "슬레이트 지붕 + 조적조", "access_road_width_m": 2.0, "floor_count": 1, "has_fire_detector": False, "street_lighting": False, "year_built": 1972},
    {"building_id": "BLDG-007", "address": "전남 고흥군 도양읍 소록마을 23-7", "material": "샌드위치 패널",       "access_road_width_m": 1.8, "floor_count": 1, "has_fire_detector": False, "street_lighting": False, "year_built": 2001},
    {"building_id": "BLDG-008", "address": "전남 고흥군 도양읍 소록마을 27-2", "material": "비닐하우스",          "access_road_width_m": 1.5, "floor_count": 1, "has_fire_detector": False, "street_lighting": False, "year_built": 2005},
    {"building_id": "BLDG-009", "address": "전남 고흥군 도양읍 소록마을 31-6", "material": "경량 목구조",         "access_road_width_m": 3.0, "floor_count": 1, "has_fire_detector": False, "street_lighting": True,  "year_built": 1981},
    {"building_id": "BLDG-010", "address": "전남 고흥군 도양읍 소록마을 35-9", "material": "조적조",              "access_road_width_m": 3.5, "floor_count": 1, "has_fire_detector": True,  "street_lighting": True,  "year_built": 1988},
    {"building_id": "BLDG-011", "address": "전남 고흥군 도양읍 소록마을 41-1", "material": "철근콘크리트",        "access_road_width_m": 5.0, "floor_count": 2, "has_fire_detector": True,  "street_lighting": True,  "year_built": 2008},
    {"building_id": "BLDG-012", "address": "전남 고흥군 도양읍 소록마을 44-3", "material": "샌드위치 패널",       "access_road_width_m": 2.2, "floor_count": 1, "has_fire_detector": False, "street_lighting": False, "year_built": 1999},
]

FIRE_CALL_SAMPLES = [
    "불이야! 소록마을 안쪽 마 노인네 집에 불이 났어요! 빨리요!",
    "여보세요 119죠? 소록마을 12번지 쪽에서 연기가 나고 있어요. 이 할아버지 혼자 사시는데 치매가 있으셔서...",
    "소록마을인데요, 지금 조 할머니 댁에서 불꽃이 보여요! 비닐하우스 쪽이요. 심야에 혼자 계실 텐데!",
    "아이고 119! 빨리요! 소록마을 23-7번지 집에서 검은 연기가 나고 있어요. 마 어르신이 귀가 어두워서 아마 모르실 거예요!",
    "소록마을이에요. 35번지 창고에서 불이 났어요. 연기가 집 안으로 들어가고 있어요.",
    "거기 박 할아버지 댁 아닌가요? 샌드위치 패널 집인데 불이 엄청 빨리 번질 것 같아요. 골목이 좁아서 차가 못 들어가요!",
    "새벽에 이러면 어떡해요. 이 어르신 치매도 있고 귀도 안 들리시는데 소리를 질러도 못 나오시겠어요!",
]

RESOURCES = [
    {"resource_id": "RES-001", "type": "마을방송",   "name": "소록마을 공동 방송 시스템",       "contact": "자동(마을회관 연동)",         "coverage_area": "소록마을 전체",       "latency_seconds": 5},
    {"resource_id": "RES-002", "type": "이장단 ARS", "name": "도양읍 이장단 긴급 ARS",          "contact": "061-830-XXXX",               "coverage_area": "도양읍 전체",         "latency_seconds": 15},
    {"resource_id": "RES-003", "type": "소방서",     "name": "고흥소방서 도양119안전센터",       "contact": "119",                        "coverage_area": "고흥군 도양읍",       "eta_minutes": 12, "vehicle_type": "펌프차 + 탱크차"},
    {"resource_id": "RES-004", "type": "이장",       "name": "소록마을 이장",                   "contact": "010-XXXX-XXXX",              "coverage_area": "소록마을",            "latency_seconds": 120},
    {"resource_id": "RES-005", "type": "자율방재단", "name": "고흥군 자율방재단 소록지역대",     "contact": "010-XXXX-XXXX",              "coverage_area": "소록마을 인근",       "latency_seconds": 180},
]

FIRE_SCENARIOS = [
    {
        "scenario_id": "FIRE-2026-001",
        "label": "시나리오 A — 초임계 / CRITICAL",
        "severity": "CRITICAL",
        "timestamp": "2026-04-24T02:15:34",
        "location": "전남 고흥군 도양읍 소록마을 23-7",
        "building_id": "BLDG-007",
        "resident_ids": ["PERSON-001"],
        "call_content": "불이야! 소록마을 안쪽 마 노인네 집에 불이 났어요! 빨리요! 거기 어르신 귀가 어두우셔서 모르실 것 같아요!",
        "fire_origin": "전기 합선 추정",
        "weather": {"wind_speed_ms": 7.2, "humidity_pct": 22, "temperature_c": 11.5, "conditions": "건조"},
        "estimated_spread_time_min": 7,
    },
    {
        "scenario_id": "FIRE-2026-002",
        "label": "시나리오 B — 고위험 / HIGH",
        "severity": "HIGH",
        "timestamp": "2026-04-24T02:43:11",
        "location": "전남 고흥군 도양읍 소록마을 12-3",
        "building_id": "BLDG-003",
        "resident_ids": ["PERSON-003", "PERSON-002"],
        "call_content": "여보세요 119죠? 소록마을 12번지 쪽에서 연기가 나고 있어요. 이 할아버지 혼자 사시는데 치매가 있으셔서 대피를 못 하실 것 같아요.",
        "fire_origin": "보일러실",
        "weather": {"wind_speed_ms": 5.5, "humidity_pct": 31, "temperature_c": 10.2, "conditions": "흐림"},
        "estimated_spread_time_min": 12,
    },
    {
        "scenario_id": "FIRE-2026-003",
        "label": "시나리오 C — 보통 / MODERATE",
        "severity": "MODERATE",
        "timestamp": "2026-04-24T03:07:22",
        "location": "전남 고흥군 도양읍 소록마을 35-9",
        "building_id": "BLDG-010",
        "resident_ids": ["PERSON-008", "PERSON-009"],
        "call_content": "소록마을이에요. 35번지 창고에서 불이 났어요. 연기가 집 안으로 들어가고 있어요. 강 씨 내외분이 계신 것 같아요.",
        "fire_origin": "주방 가스레인지",
        "weather": {"wind_speed_ms": 3.2, "humidity_pct": 45, "temperature_c": 13.0, "conditions": "맑음"},
        "estimated_spread_time_min": 18,
    },
    {
        "scenario_id": "FIRE-2026-004",
        "label": "시나리오 D — 초임계 / CRITICAL",
        "severity": "CRITICAL",
        "timestamp": "2026-04-24T01:52:07",
        "location": "전남 고흥군 도양읍 소록마을 27-2",
        "building_id": "BLDG-008",
        "resident_ids": ["PERSON-015"],
        "call_content": "소록마을인데요, 지금 조 할머니 댁에서 불꽃이 보여요! 비닐하우스 쪽이요. 심야에 혼자 계실 텐데! 치매도 있으셔서 어디 계신지도 몰라요!",
        "fire_origin": "비닐하우스 내 담뱃불 추정",
        "weather": {"wind_speed_ms": 6.8, "humidity_pct": 18, "temperature_c": 9.8, "conditions": "건조"},
        "estimated_spread_time_min": 4,
    },
    {
        "scenario_id": "FIRE-2026-005",
        "label": "시나리오 E — 고위험 / HIGH",
        "severity": "HIGH",
        "timestamp": "2026-04-24T03:31:45",
        "location": "전남 고흥군 도양읍 소록마을 3-5",
        "building_id": "BLDG-002",
        "resident_ids": ["PERSON-013"],
        "call_content": "거기 박 할아버지 댁 아닌가요? 샌드위치 패널 집인데 불이 엄청 빨리 번질 것 같아요. 골목이 좁아서 차가 못 들어가요!",
        "fire_origin": "주방",
        "weather": {"wind_speed_ms": 4.8, "humidity_pct": 27, "temperature_c": 10.8, "conditions": "건조"},
        "estimated_spread_time_min": 8,
    },
]


def build_residents():
    residents = []
    for idx, r in enumerate(RESIDENT_DATA):
        pid = f"PERSON-{idx+1:03d}"
        last = r["name"][0]
        ec_location = random.choice(["서울", "광주", "순천", "여수", "고흥읍"])
        suffix_a = f"{random.randint(1000,9999)}"
        suffix_b = f"{random.randint(1000,9999)}"
        residents.append({
            "person_id": pid,
            "name": r["name"],
            "age": r["age"],
            "gender": r["gender"],
            "conditions": r["conditions"],
            "phone": f"010-{suffix_a}-{suffix_b}",
            "lives_alone": r["lives_alone"],
            "emergency_contact": {
                "name": f"{last}씨 자녀",
                "phone": f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                "location": ec_location,
            },
            "mobility_score": round(
                random.uniform(0.1, 0.5) if "거동불편" in r["conditions"] else random.uniform(0.5, 0.9), 2
            ),
            "hearing_impaired": "난청" in r["conditions"],
            "has_dementia": "치매" in r["conditions"],
            "building_id": r["building_id"],
        })
    return residents


def build_buildings():
    material_risk = {
        "샌드위치 패널":        "VERY_HIGH",
        "경량 목구조":           "HIGH",
        "조적조":               "MEDIUM",
        "철근콘크리트":          "LOW",
        "비닐하우스":           "CRITICAL",
        "슬레이트 지붕 + 조적조": "HIGH",
    }
    buildings = []
    for b in BUILDING_DATA:
        buildings.append({
            **b,
            "fire_risk_level": material_risk.get(b["material"], "UNKNOWN"),
            "has_sprinkler": b["has_fire_detector"] and random.random() > 0.8,
        })
    return buildings


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    dataset = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "location": "전남 고흥군 도양읍 소록마을",
            "description": "고흥군 소록마을 심야 화재 대응 시뮬레이션 데이터셋",
        },
        "residents": build_residents(),
        "buildings": build_buildings(),
        "resources": RESOURCES,
        "fire_scenarios": FIRE_SCENARIOS,
        "fire_call_samples": FIRE_CALL_SAMPLES,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"[OK] 데이터셋 생성 완료: {OUTPUT_PATH}")
    print(f"     - 주민: {len(dataset['residents'])}명")
    print(f"     - 건축물: {len(dataset['buildings'])}동")
    print(f"     - 대응자원: {len(dataset['resources'])}종")
    print(f"     - 화재 시나리오: {len(dataset['fire_scenarios'])}건")


if __name__ == "__main__":
    main()
