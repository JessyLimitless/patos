# PATOS 시스템 아키텍처
**Predictive Agentic Triage OS — System Architecture**
`v4.4 / 2026-04-24`

---

## 1. 전체 구조 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                        PATOS v4.4                               │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  외부 데이터   │    │  추론 엔진    │    │   프론트엔드     │  │
│  │  수집 계층    │───▶│  처리 계층   │───▶│   표현 계층      │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

외부 데이터 수집:  KMA/Open-Meteo API, GPS 동의 데이터, 고흥군 DB
추론 엔진 처리:   TypeDB 온톨로지, MockTypeDB, 화재전파 시뮬레이터
프론트엔드 표현:   Vanilla JS SPA, SVG 마을 지도, 4-Step 시퀀스
```

---

## 2. 컴포넌트 구성

### 2.1 파일 구조

```
patos/
├── app.py                  # 메인 서버 + 시뮬레이션 엔진
├── weather.py              # 기상청 API 연동 모듈
├── fire_spread.py          # 화재 전파 물리 시뮬레이터
├── typedb_client.py        # TypeDB 실제 연결 클라이언트
├── data_generator.py       # 초기 데이터셋 생성기
├── schema.tql              # TypeDB 스키마 정의
├── index.html              # 프론트엔드 SPA (단일 파일)
├── data/
│   └── goheung_dataset.json    # 주민·건물·시나리오 원본 데이터
├── simulation_result.json      # 실행 결과 (서버 기동 시 재생성)
└── docs/
    ├── 01_scenario.md
    ├── 02_system_architecture.md
    └── 03_data_architecture.md
```

### 2.2 컴포넌트별 책임

| 컴포넌트 | 언어 | 책임 |
|----------|------|------|
| `app.py` | Python 3.11 | HTTP 서버, 시뮬레이션 오케스트레이션, JSON 출력 |
| `weather.py` | Python | Open-Meteo API 호출, NFDRS 화재위험지수 산출 |
| `fire_spread.py` | Python | NFPA 72 기반 물리 화재 전파 모델 |
| `typedb_client.py` | Python | TypeDB TQL 쿼리, MockDB 폴백 |
| `data_generator.py` | Python | 소록마을 합성 데이터 생성 |
| `index.html` | Vanilla JS | 4-Step 애니메이션 SPA, SVG 지도 |

---

## 3. 레이어별 상세 설명

### 3.1 데이터 수집 계층

```
┌─────────────────────────────────────────────────────┐
│                 외부 데이터 소스                      │
│                                                     │
│  Open-Meteo API          고흥군 행정 DB              │
│  (KMA 프록시)             (주민·건물 대장)            │
│  latitude=34.6101        [동의 기반 접근]             │
│  longitude=127.2893      ↓                          │
│        ↓                 GPS 동의 데이터              │
│   weather.py             (PERSON-ID → lat/lon)      │
│        ↓                        ↓                  │
│   live_weather dict      goheung_dataset.json       │
└─────────────────────────────────────────────────────┘
```

**weather.py 처리 흐름:**
1. `fetch_live()` — Open-Meteo HTTP GET (timeout 6초)
2. WMO 기상 코드 → 한국어 기상 상태 변환
3. `_fire_risk_index(wind_ms, humidity, temp)` — NFDRS 단순화 지수 (0~100)
4. 타임아웃 시 고흥 4월 심야 평년값으로 폴백

### 3.2 추론 엔진 계층

```
┌─────────────────────────────────────────────────────────┐
│                   추론 엔진 (app.py)                     │
│                                                         │
│  goheung_dataset.json                                   │
│         ↓                                               │
│  ┌──────────────────────────────┐                       │
│  │  TypeDBClient                │                       │
│  │  ├─ TypeDB Core (localhost:1729) ── 연결 성공 시     │
│  │  └─ MockTypeDB               ── 폴백 (현재 모드)     │
│  │      ├─ rule_cognitive_vulnerability()               │
│  │      └─ rule_physical_isolation()                    │
│  └──────────────────────────────┘                       │
│         ↓                                               │
│  run_all_scenarios(db, live_weather)                    │
│  ├─ 시나리오별 priority_targets 산출                    │
│  ├─ fire_spread.simulate(building, weather)             │
│  └─ _attach_consented_location()                        │
│         ↓                                               │
│  simulation_result.json  (UTF-8, ensure_ascii=False)    │
└─────────────────────────────────────────────────────────┘
```

**우선순위 산출 (MockTypeDB):**
```python
# TypeDB 추론 규칙을 Python으로 구현
cognitive = age >= 80 OR 난청 OR 치매     → score 0~100
isolation  = 접근로 < 3m OR 가연성 자재   → score 0~100
priority   = cognitive × 0.6 + isolation × 0.4
```

### 3.3 화재 전파 시뮬레이션

```
fire_spread.simulate(building, weather)
    │
    ├─ 자재별 기본 확산속도 (MATERIAL_PROPS)
    │   비닐하우스    15.0 m²/min
    │   샌드위치 패널  8.0 m²/min
    │   경량 목구조    6.0 m²/min
    │   조적조         1.5 m²/min
    │
    ├─ 환경 보정 계수
    │   wind_factor     = 1.0 + (wind_ms / 10.0)
    │   humidity_factor = 1.0 + max(0, (55 - humidity)) / 100
    │   temp_factor     = 1.0 + max(0, (temp - 10)) / 50
    │
    ├─ 시간 산출
    │   effective_rate  = base_rate × wind × humidity × temp
    │   time_engulf     = 85m² / effective_rate
    │   time_flashover  = props.flashover / (wind_factor × 0.8)
    │   time_structural = time_engulf × structural_fail_factor
    │   neighbor_risk   = 방사열 기반 (간격 5m 가정)
    │
    └─ SpreadResult (dataclass)
        └─ as_dict() → JSON 직렬화
```

### 3.4 프론트엔드 계층

```
index.html (단일 파일 SPA)
│
├─ 외부 의존성 (CDN)
│   ├─ Tailwind CSS  — 유틸리티 스타일링
│   └─ Lucide Icons  — 아이콘 (로드 실패 시 safeIcons()로 보호)
│
├─ 초기화 흐름
│   DOMContentLoaded
│   └─ safeIcons() → loadData()
│       ├─ fetch("simulation_result.json")  성공 시 서버 데이터 사용
│       └─ catch → FALLBACK 내장 데이터    실패 시 오프라인 동작
│
├─ 4-Step 시퀀스 (타이머 기반)
│   tick(400ms)   → modal1 (2.5s 자동닫힘)
│   tick(3000ms)  → STT 타이핑 애니메이션
│   tick(4000ms)  → Step 2 지식 그래프 카드 렌더링
│   tick(5000ms)  → modal2 (2.2s 자동닫힘)
│   tick(7500ms)  → Step 3 추론 엔진 활성화
│   tick(7800ms)  → modal3 (2.8s 자동닫힘)
│   tick(10700ms) → 로직 노드 순차 등장
│   tick(13500ms) → 구조 대상 카드 + 화재전파 타임라인
│   tick(15000ms) → Step 4 디스패치 카드
│   tick(15800ms) → modal4 (4.0s 자동닫힘)
│
├─ SVG 마을 지도
│   BLDG_POS  — 12개 건물 좌표 (SVG viewBox 520×110)
│   BLDG_INFO — 건물 자재·도로폭 툴팁
│   fire-ring CSS animation — 발화 건물 펄스 표시
│
└─ 화재 전파 타임라인 바
    renderSpreadTimeline(spread)
    └─ 이벤트 점 위치 = (t_min / maxT) × 100%
```

---

## 4. 서버 실행 흐름

```
python app.py
    │
    ├─ 1. 데이터셋 로드 (data/goheung_dataset.json)
    │      없으면 data_generator.py 자동 실행
    │
    ├─ 2. TypeDB 연결 시도 (localhost:1729)
    │      실패 → MockTypeDB 자동 폴백
    │
    ├─ 3. 기상 데이터 수집 (weather.fetch_live)
    │      실패 → 고흥 평년값 폴백
    │
    ├─ 4. 시나리오 시뮬레이션 실행
    │      run_all_scenarios(db, live_weather)
    │
    ├─ 5. simulation_result.json 저장 (UTF-8)
    │
    └─ 6. HTTP 서버 기동 (ReusableTCPServer, port 8000)
           브라우저 자동 오픈 (threading.Timer 1.2s)
```

---

## 5. 기술 스택

| 영역 | 기술 | 버전 | 비고 |
|------|------|------|------|
| 서버 런타임 | Python | 3.11+ | 표준 라이브러리만 사용 (http.server) |
| 지식 그래프 | TypeDB Core | 2.x | localhost:1729, MockDB 폴백 포함 |
| 기상 API | Open-Meteo | — | 무료, 키 불필요, KMA 프록시 역할 |
| 화재 모델 | NFPA 72 / NFDRS | — | 단순화 구현 |
| 프론트엔드 | Vanilla JavaScript | ES2020+ | 프레임워크 없음 |
| CSS | Tailwind CSS | CDN | 유틸리티 클래스 |
| 아이콘 | Lucide | CDN | safeIcons() 보호 래퍼 |
| 직렬화 | JSON | UTF-8 | ensure_ascii=False |

---

## 6. 폴백(Fallback) 전략

PATOS는 외부 의존성 전체가 실패해도 동작하도록 설계되었다.

| 의존성 | 실패 조건 | 폴백 |
|--------|-----------|------|
| TypeDB 서버 | 미설치 / 포트 불통 | MockTypeDB (Python 추론 규칙) |
| 기상 API | 타임아웃 / 네트워크 단절 | 고흥 4월 심야 평년값 |
| simulation_result.json | fetch 실패 (file:// 프로토콜 등) | FALLBACK 내장 데이터 (index.html) |
| Lucide CDN | 네트워크 차단 | safeIcons() try-catch, 아이콘만 미표시 |

---

## 7. 보안 고려사항

- GPS 위치 데이터: 주민 동의서 작성자만 활용 (`consented: true`)
- 주민 DB: 행정 내부망 전제, 외부 API 미노출
- HTTP 서버: 로컬 전용 (0.0.0.0:8000, 공개망 배포 시 인증 계층 필요)
- TypeDB 쿼리: 파라미터 바인딩 방식으로 인젝션 방지
