# PATOS 데이터 아키텍처
**Predictive Agentic Triage OS — Data Architecture**
`v4.4 / 2026-04-24`

---

## 1. 데이터 전체 흐름

```
┌──────────────────────────────────────────────────────────────┐
│                     데이터 소스 계층                          │
│                                                              │
│  고흥군 건물 대장    주민 등록 DB      기상청 API    GPS 동의  │
│  (행정 내부망)      (동의 기반)      (Open-Meteo)   (동의자)  │
└──────────┬──────────────┬──────────────┬────────────┬───────┘
           │              │              │            │
           ▼              ▼              ▼            ▼
┌──────────────────────────────────────────────────────────────┐
│                    정규화·저장 계층                           │
│                                                              │
│   data_generator.py      weather.py        GPS mapping      │
│         ↓                    ↓                  ↓           │
│   goheung_dataset.json   live_weather{}    consented_loc{}  │
└──────────┬──────────────────┬──────────────────────────────-┘
           │                  │
           ▼                  ▼
┌──────────────────────────────────────────────────────────────┐
│                    추론·결합 계층                             │
│                                                              │
│   TypeDB / MockTypeDB       fire_spread.simulate()          │
│   (온톨로지 추론)            (물리 모델)                     │
│         ↓                        ↓                          │
│              run_all_scenarios()                             │
│                     ↓                                       │
│             simulation_result.json                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    표현 계층                                  │
│   index.html fetch() → 렌더링 → 사용자 인터페이스             │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. TypeDB 온톨로지 스키마

### 2.1 엔티티 정의

```
person
  ├─ person-id   (string, @key)
  ├─ name        (string)
  ├─ age         (long)
  ├─ phone       (string)
  ├─ lives-alone (boolean)
  ├─ hearing-impaired   (boolean)
  ├─ has-dementia       (boolean)
  ├─ chronic-condition  (string, 복수)
  └─ cognitive-vulnerability (boolean) ← 추론 규칙으로 자동 설정

building
  ├─ building-id        (string, @key)
  ├─ address            (string)
  ├─ material           (string)
  ├─ access-road-width  (double, 단위: m)
  ├─ has-fire-detector  (boolean)
  └─ physical-isolation (boolean) ← 추론 규칙으로 자동 설정

fire-event
  ├─ event-id     (string, @key)
  ├─ call-content (string)
  ├─ severity     (string)
  └─ fire-origin  (string)

resource
  ├─ resource-id (string, @key)
  ├─ name        (string)
  └─ type        (string)
```

### 2.2 관계(Relation) 정의

```
residence       : (resident: person) ↔ (dwelling: building)
incident        : (event: fire-event) ↔ (site: building) ↔ (victim: person)
deployment      : (resource: resource) ↔ (site: building)
rescue-priority : (victim: person) ↔ (event: fire-event)
```

### 2.3 추론 규칙 (Inference Rules)

```
# 인지취약성 규칙 (3개)
rule cognitive-vulnerability-by-age:
  when { $p isa person, has age $a; $a >= 80; }
  then { $p has cognitive-vulnerability true; };

rule cognitive-vulnerability-by-hearing:
  when { $p isa person, has hearing-impaired true; }
  then { $p has cognitive-vulnerability true; };

rule cognitive-vulnerability-by-dementia:
  when { $p isa person, has has-dementia true; }
  then { $p has cognitive-vulnerability true; };

# 물리적 고립 규칙 (4개)
rule physical-isolation-by-narrow-road:
  when { $b isa building, has access-road-width $w; $w < 3.0; }
  then { $b has physical-isolation true; };

rule physical-isolation-by-sandwich-panel:
  when { $b isa building, has material "샌드위치 패널"; }
  then { $b has physical-isolation true; };

rule physical-isolation-by-vinyl:
  when { $b isa building, has material "비닐하우스"; }
  then { $b has physical-isolation true; };

rule physical-isolation-by-light-wood:
  when { $b isa building, has material "경량 목구조"; }
  then { $b has physical-isolation true; };
```

---

## 3. 원본 데이터셋 구조 (`goheung_dataset.json`)

```json
{
  "residents": [
    {
      "person_id":   "PERSON-001",
      "name":        "마순례",
      "age":         84,
      "phone":       "010-xxxx-xxxx",
      "lives_alone": true,
      "conditions":  ["난청", "거동불편", "당뇨"],
      "building_id": "BLDG-007"
    }
    // ... 15명
  ],

  "buildings": [
    {
      "building_id":        "BLDG-007",
      "address":            "전남 고흥군 도양읍 소록마을 23-7",
      "material":           "샌드위치 패널",
      "access_road_width_m": 1.8,
      "has_fire_detector":  false
    }
    // ... 12동
  ],

  "resources": [
    {
      "resource_id": "RES-001",
      "name":        "고흥소방서 펌프차 1호",
      "type":        "fire_truck"
    }
    // ... 5개
  ],

  "fire_scenarios": [
    {
      "scenario_id": "FIRE-2026-001",
      "label":       "시나리오 A — 초임계 / CRITICAL",
      "severity":    "CRITICAL",
      "incident": {
        "timestamp":   "2026-04-24T02:15:34",
        "location":    "전남 고흥군 도양읍 소록마을 23-7",
        "building_id": "BLDG-007",
        "call_content": "불이야! 소록마을 안쪽 마 노인네 집에 불이 났어요!",
        "fire_origin": "전기 합선"
      }
      // ...
    }
    // ... 5개 시나리오
  ],

  "call_samples": [
    // 7개 119 신고 텍스트 샘플
  ]
}
```

---

## 4. 시뮬레이션 결과 구조 (`simulation_result.json`)

```json
{
  "generated_at":  "2026-04-24T17:36:21+09:00",
  "live_weather": {
    "source":         "KMA / Open-Meteo",
    "station":        "고흥 관측소 (ASOS 165)",
    "observed_at":    "2026-04-24 17:36:21 KST",
    "temperature_c":  11.5,
    "humidity_pct":   61,
    "wind_speed_ms":  1.64,
    "wind_direction": "남서",
    "conditions":     "맑음",
    "fire_risk": {
      "index": 10.5,
      "level": "낮음",
      "color": "#16a34a"
    },
    "is_live": true
  },

  "scenarios": [
    {
      "scenario_id": "FIRE-2026-001",
      "severity":    "CRITICAL",
      "confidence":  99.4,

      "incident": {
        "timestamp":    "2026-04-24T02:15:34",
        "location":     "전남 고흥군 도양읍 소록마을 23-7",
        "building_id":  "BLDG-007",
        "call_content": "불이야! ...",
        "weather": { "wind_speed_ms": 7.2, "humidity_pct": 22 }
      },

      "knowledge_lineage": [
        { "label": "Building Code", "val": "샌드위치 패널 / 1.8m", "trust": 99.2, "icon": "home" },
        { "label": "Demography",    "val": "84세 / 난청 / 거동불편", "trust": 97.5, "icon": "user-x" },
        { "label": "Dynamics",      "val": "풍속 7.2m/s / 습도 22%", "trust": 94.8, "icon": "wind" }
      ],

      "reasoning_chain": [
        {
          "step":    1,
          "type":    "physical_hazard",
          "label":   "Physical Hazard",
          "content": "샌드위치 패널 및 1.8m 접근로 — 소방력 접근 지연 임계치 초과.",
          "score":   90
        },
        {
          "step":    2,
          "type":    "cognitive_reliability",
          "label":   "Cognitive Reliability",
          "content": "난청 — 표준 대피 가이드 도달률 미달.",
          "score":   100
        }
      ],

      "priority_targets": [
        {
          "rank":   1,
          "name":   "마순례",
          "age":    84,
          "conditions": ["난청", "거동불편", "당뇨"],
          "lives_alone": true,
          "cognitive_vulnerability_score": 100,
          "physical_isolation_score":      90,
          "total_priority_score":          96.0,
          "location": {
            "lat":       34.6112,
            "lon":       127.2901,
            "consented": true
          },
          "rescue_actions": ["이장단 ARS", "들것 지참", "도보 진입 특화 분대"]
        }
      ],

      "fire_spread": {
        "material":              "샌드위치 패널",
        "effective_rate_m2_min": 14.2,
        "time_flashover_min":    2.5,
        "time_engulf_min":       4.5,
        "time_structural_min":   3.2,
        "neighbor_risk_min":     6.0,
        "rescue_window_min":     2.0,
        "rescue_before_eta":     false,
        "produces_toxic_gas":    true,
        "heat_release_kw":       6000,
        "fire_service_eta_min":  12,
        "risk_label":            "극위험 — 즉시 대응",
        "risk_color":            "#7f1d1d",
        "timeline": [
          { "t_min": 0.0, "label": "신고 접수",    "icon": "phone",          "color": "#6b7280" },
          { "t_min": 0.8, "label": "유독가스 발생", "icon": "wind",           "color": "#7c3aed" },
          { "t_min": 2.5, "label": "플래시오버",   "icon": "flame",          "color": "#dc2626" },
          { "t_min": 6.0, "label": "인접 건물 위험","icon": "alert-triangle", "color": "#f97316" },
          { "t_min": 12,  "label": "소방차 도착",  "icon": "truck",          "color": "#2563eb" },
          { "t_min": 3.2, "label": "구조 붕괴",    "icon": "building-2",     "color": "#1a1a1a" },
          { "t_min": 4.5, "label": "전소",         "icon": "x-circle",       "color": "#374151" }
        ]
      },

      "weather_live": {
        "wind_speed_ms": 7.2,
        "humidity_pct":  22,
        "conditions":    "건조",
        "fire_risk": { "level": "매우 위험", "color": "#dc2626", "index": 78.4 }
      },

      "action_protocol": {
        "ars_message":       "[긴급] 마순례(84세) 어르신 댁 화재. 난청으로 인지 불가. 즉시 방문 구조.",
        "mdt_message":       "접근로 1.8m 협로 경보. 도보 진입 특화 분대. 샌드위치 패널 유독가스 주의.",
        "village_broadcast": "소록마을 23-7 화재 발생. 전 주민 대피. 이장단 즉시 집결."
      },

      "rescue_critical_min": 2.0
    }
    // ... 4개 시나리오 동일 구조
  ]
}
```

---

## 5. 건축 자재별 화재 특성 데이터

| 자재 | 확산속도 (m²/min) | 열방출률 (kW) | 유독가스 | 플래시오버 (분) | 구조붕괴 계수 |
|------|-------------------|---------------|----------|-----------------|---------------|
| 비닐하우스 | 15.0 | 8,500 | O (PVC) | 2.0 | 0.60 |
| 샌드위치 패널 | 8.0 | 6,000 | O (HCN·CO) | 3.5 | 0.70 |
| 경량 목구조 | 6.0 | 4,000 | X | 5.0 | 0.80 |
| 슬레이트+조적 | 3.0 | 2,500 | O (석면) | 8.0 | 0.85 |
| 조적조 | 1.5 | 1,500 | X | 12.0 | 0.90 |
| 철근콘크리트 | 0.5 | 800 | X | 25.0 | 0.95 |

*기준: 단층 단독주택 연면적 85m², 간격 5m 인접 건물 방사열 기반*

---

## 6. 화재위험지수 (NFDRS 단순화)

```
fire_risk_index = 건조도(0~40) + 풍속(0~40) + 기온(0~20)

건조도 = max(0, (30 - humidity) / 30) × 40
풍속   = min(wind_ms / 15, 1.0) × 40
기온   = max(0, (temp_c - 10) / 25) × 20

등급:
  index ≥ 70 → 매우 위험  (#dc2626)
  index ≥ 50 → 위험       (#ea580c)
  index ≥ 30 → 보통       (#eab308)
  index <  30 → 낮음      (#16a34a)
```

---

## 7. GPS 동의 데이터 구조

```python
CONSENTED_LOCATIONS = {
    "PERSON-001": {"lat": 34.6112, "lon": 127.2901, "consented": True},
    "PERSON-003": {"lat": 34.6098, "lon": 127.2887, "consented": True},
    # ... 동의자만 포함 (미동의자는 키 없음)
}
```

- 동의 여부는 별도 동의서 DB에서 조회
- 프론트엔드에서 `consented: true`인 대상에만 "GPS" 배지 표시
- 위치 정밀도: 소수점 4자리 (약 11m 반경)

---

## 8. 데이터 품질 및 신뢰도

| 데이터 | 신뢰도 | 갱신 주기 | 비고 |
|--------|--------|-----------|------|
| 건물 자재·도로폭 | 99.2% | 연 1회 (건물 대장 기준) | 증축·개축 즉시 반영 필요 |
| 주민 인적 사항 | 97.5% | 월 1회 (주민 등록 기준) | 전입·전출 시차 발생 가능 |
| 기상 데이터 | 94.8% | 실시간 (1시간 단위) | API 타임아웃 시 평년값 |
| GPS 위치 | 95.0% | 실시간 (동의자 기기) | 배터리·통신 장애 미대응 |

---

## 9. 데이터 라이프사이클

```
[생성]                  [처리]                  [소비]                [폐기]
data_generator.py  →  app.py 시뮬레이션  →  index.html 렌더링  →  세션 종료
goheung_dataset.json   simulation_result.json  (브라우저 메모리)    (서버 재기동 시 갱신)
     ↑                         ↑
  수동 업데이트             자동 재생성
  (행정 DB 연동 시)        (서버 기동마다)
```

**simulation_result.json은 서버 기동 시마다 최신 기상 데이터로 재생성된다.**
**goheung_dataset.json은 행정 DB 연동 전까지 수동 관리 대상이다.**
