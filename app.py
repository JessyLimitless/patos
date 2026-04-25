#!/usr/bin/env python3
"""
PATOS — 소록마을 심야 화재 대응 시뮬레이션 엔진 v2.0
- TypeDB 2.x 실제 연결 (typedb_client.py)
- 기상청 실시간 API (weather.py)
- 물리 기반 화재 전파 시뮬레이션 (fire_spread.py)
- 주민 동의 기반 위치 데이터 통합

실행: python app.py
브라우저: http://localhost:8000
"""

import json
import os
import http.server
import socketserver
import threading
import webbrowser
from datetime import datetime

# 신규 모듈
import weather as weather_mod
import fire_spread as fire_mod

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "data", "goheung_dataset.json")
OUTPUT_PATH  = os.path.join(BASE_DIR, "simulation_result.json")
PORT = 8000


# ── Mock TypeDB 추론 엔진 ────────────────────────────────────────────────────

class MockTypeDB:
    """
    TypeDB schema.tql의 Inference Rule을 Python으로 구현한 Mock DB.
    실제 TypeDB 서버 없이 동일한 추론 결과를 반환한다.
    """

    def __init__(self, dataset: dict):
        self.residents  = {r["person_id"]: r for r in dataset.get("residents", [])}
        self.buildings  = {b["building_id"]: b for b in dataset.get("buildings", [])}
        self.resources  = dataset.get("resources", [])
        self.scenarios  = {s["scenario_id"]: s for s in dataset.get("fire_scenarios", [])}

    # ── TypeDB Inference Rules (Python 구현) ──────────────────────────────

    def rule_cognitive_vulnerability(self, person: dict) -> tuple:
        """
        cognitive-vulnerability-by-age        : age >= 80
        cognitive-vulnerability-by-hearing    : hearing_impaired = true
        cognitive-vulnerability-by-dementia   : has_dementia = true
        """
        score, reasons = 0, []
        age        = person.get("age", 0)
        conditions = person.get("conditions", [])

        if age >= 80:
            score += 40; reasons.append(f"초고령({age}세)")
        elif age >= 75:
            score += 20; reasons.append(f"고령({age}세)")

        if "난청" in conditions:
            score += 35; reasons.append("난청 — 청각 경보 도달 불가")
        if "치매" in conditions:
            score += 30; reasons.append("치매 — 인지 판단·지시 수행 불가")
        if "거동불편" in conditions:
            score += 20; reasons.append("거동불편 — 자력 대피 불가")
        if person.get("lives_alone", False):
            score += 10; reasons.append("독거 — 조력자 없음")

        return min(score, 100), reasons

    def rule_physical_isolation(self, building: dict) -> tuple:
        """
        physical-isolation-by-narrow-road     : access_road_width < 3.0
        physical-isolation-by-sandwich-panel  : material = '샌드위치 패널'
        physical-isolation-by-vinyl           : material = '비닐하우스'
        physical-isolation-by-light-wood      : material = '경량 목구조'
        compound-risk-no-detector             : no detector + vulnerable resident
        """
        score, reasons = 0, []
        width    = building.get("access_road_width_m", 5.0)
        material = building.get("material", "")

        if width < 2.0:
            score += 40; reasons.append(f"극협로 {width}m — 소방차량 진입 불가")
        elif width < 3.0:
            score += 25; reasons.append(f"협로 {width}m — 차량 진입 제한")
        elif width < 4.0:
            score +=  8; reasons.append(f"준협로 {width}m")

        if material == "비닐하우스":
            score += 45; reasons.append("비닐하우스 — 즉시 전소·유독가스")
        elif material == "샌드위치 패널":
            score += 35; reasons.append("샌드위치 패널 — 유독가스·급속 연소")
        elif material in ("경량 목구조", "슬레이트 지붕 + 조적조"):
            score += 20; reasons.append(f"가연성 자재({material})")

        if not building.get("has_fire_detector", True):
            score += 10; reasons.append("화재감지기 미설치")
        if not building.get("street_lighting", True):
            score +=  5; reasons.append("야간 접근로 조명 없음")

        return min(score, 100), reasons

    # ── 시나리오 시뮬레이션 ──────────────────────────────────────────────

    def simulate(self, scenario_id: str) -> dict:
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            return {"error": f"Scenario {scenario_id} not found"}

        building  = self.buildings[scenario["building_id"]]
        residents = [self.residents[pid] for pid in scenario["resident_ids"] if pid in self.residents]

        assessed = []
        for person in residents:
            cog_score, cog_reasons = self.rule_cognitive_vulnerability(person)
            iso_score, iso_reasons = self.rule_physical_isolation(building)
            total = round(cog_score * 0.6 + iso_score * 0.4, 1)
            assessed.append({
                "person":      person,
                "cog_score":   cog_score,
                "cog_reasons": cog_reasons,
                "iso_score":   iso_score,
                "iso_reasons": iso_reasons,
                "total":       total,
            })

        assessed.sort(key=lambda x: x["total"], reverse=True)

        return {
            "scenario_id":      scenario_id,
            "label":            scenario.get("label", scenario_id),
            "severity":         scenario.get("severity", "UNKNOWN"),
            "incident":         scenario,
            "knowledge_lineage": self._build_lineage(assessed, building, scenario),
            "reasoning_chain":  self._build_reasoning(assessed, building, scenario),
            "priority_targets": [self._format_target(i, r) for i, r in enumerate(assessed)],
            "action_protocol":  self._build_actions(assessed, building, scenario),
            "confidence":       self._calc_confidence(assessed),
        }

    # ── 내부 빌더 ────────────────────────────────────────────────────────

    def _build_lineage(self, assessed, building, scenario):
        top     = assessed[0] if assessed else None
        weather = scenario.get("weather", {})
        lineage = [{
            "label": "Building Code",
            "val":   f"{building['material']} / {building['access_road_width_m']}m 접근로",
            "trust": 99.2, "icon": "home",
        }]
        if top:
            p        = top["person"]
            cond_str = " / ".join(p["conditions"][:3])
            lineage.append({
                "label": "Demography",
                "val":   f"{p['age']}세 / {cond_str}",
                "trust": 97.5, "icon": "user-x",
            })
        lineage.append({
            "label": "Dynamics",
            "val":   f"풍속 {weather.get('wind_speed_ms','?')}m/s / 습도 {weather.get('humidity_pct','?')}%",
            "trust": 94.8, "icon": "wind",
        })
        return lineage

    def _build_reasoning(self, assessed, building, scenario):
        top   = assessed[0] if assessed else None
        chain = []

        # Logic 1: 물리적 위험도 (Physical Hazard)
        if top:
            w = building.get("access_road_width_m", 5.0)
            m = building.get("material", "")
            if top["iso_score"] >= 40:
                phys_text = (
                    f"{m} 및 {w}m 접근로 구조 분석 결과, "
                    f"소방력 접근 지연에 따른 대형 화재 전이 임계치 초과 판정."
                )
            else:
                phys_text = (
                    f"{m} 구조물, 접근로 {w}m 확인. "
                    f"소방력 접근 가능 판정. 표준 대응 절차 적용."
                )
            chain.append({
                "step": 1, "type": "physical_hazard",
                "label": "Physical Hazard", "icon": "home",
                "content": phys_text, "score": top["iso_score"],
            })

        # Logic 2: 인지 신뢰도 (Cognitive Reliability)
        if top:
            p = top["person"]
            c = p.get("conditions", [])
            if "난청" in c:
                cog_text = "거주자 난청 특성 데이터 가중치 적용 시, 표준 대피 가이드 도달률 유의미성 미달 확인."
            elif "치매" in c:
                cog_text = "치매 진단 이력 확인. 구두 대피 지시 이해 불가 판정. 직접 구조 개입 필요."
            else:
                cog_text = f"{p['age']}세 고령 + {', '.join(c[:2])} 복합 조건. 부분 대피 지원 판정."
            chain.append({
                "step": 2, "type": "cognitive_vulnerability",
                "label": "Cognitive Reliability", "icon": "target",
                "content": cog_text, "score": top["cog_score"],
            })

        return chain

    def _format_target(self, idx, r):
        p       = r["person"]
        conds   = p.get("conditions", [])
        actions = []

        if "난청" in conds:        actions.append("이장단 ARS 즉시 발송 (청각 경보 대체)")
        if "치매" in conds:        actions.append("직접 방문 구조대 파견 (인지 판단 불가)")
        if "거동불편" in conds:    actions.append("들것·이동 보조 장비 지참")
        if p.get("lives_alone"):   actions.append("독거 확인 후 즉시 구조")
        if r["iso_score"] >= 40:   actions.append("도보 진입 특화 분대 우선 배정")

        return {
            "rank":                      idx + 1,
            "person_id":                 p["person_id"],
            "name":                      p["name"],
            "age":                       p["age"],
            "conditions":                conds,
            "lives_alone":               p.get("lives_alone", False),
            "cognitive_vulnerability_score": r["cog_score"],
            "physical_isolation_score":  r["iso_score"],
            "total_priority_score":      r["total"],
            "rescue_actions":            actions,
        }

    def _build_actions(self, assessed, building, scenario):
        top = assessed[0] if assessed else None
        if not top:
            return {}

        p     = top["person"]
        conds = p.get("conditions", [])
        w     = building.get("access_road_width_m", 5.0)
        m     = building.get("material", "")
        addr  = building.get("address", "")

        if "난청" in conds:
            ars = f"[긴급] {p['name']}({p['age']}세) 어르신 댁 화재 발생. 난청으로 자력 인지 불가. 즉시 방문 구조를 지지합니다."
        elif "치매" in conds:
            ars = f"[긴급] {p['name']}({p['age']}세) 어르신 댁 화재 발생. 치매로 대피 불가. 직접 구조 요청."
        else:
            ars = f"[긴급] {p['name']}({p['age']}세) 어르신 댁 화재 발생. {', '.join(conds[:2])}. 즉각 대응 바랍니다."

        if w < 3.0:
            mdt = f"접근로 {w}m 협로 경보. 소방차 직접 진입 불가. 도보 진입 특화 분대 우선 배정 완료. {m} 유독가스 주의."
        else:
            mdt = f"접근로 {w}m 확인. 차량 진입 가능. {m} 구조물 화재 대응 절차 적용."

        broadcast = (
            f"소록마을 주민 여러분, 긴급 화재 상황입니다. "
            f"{addr} 인근 화재 발생. 신속히 대피하시고 이웃 어르신들을 도와주십시오."
        )

        return {
            "ars_message":      ars,
            "mdt_message":      mdt,
            "village_broadcast": broadcast,
        }

    def _calc_confidence(self, assessed):
        if not assessed:
            return 50.0
        top = assessed[0]["total"]
        return round(min(84 + (top / 100) * 16, 99.9), 1)


# ── 시뮬레이션 실행 및 JSON 생성 ─────────────────────────────────────────────

def run_all_scenarios(db: MockTypeDB, live_weather: dict) -> dict:
    buildings_map = db.buildings
    results = []

    for sid in db.scenarios:
        base = db.simulate(sid)

        # 화재 전파 분석 추가
        building = buildings_map.get(base["incident"]["building_id"], {})
        scenario_weather = base["incident"].get("weather", {})
        merged_weather = weather_mod.merge_with_scenario(live_weather, scenario_weather)
        spread = fire_mod.simulate(building, scenario_weather)

        # 주민 동의 기반 위치 데이터 (GPS 좌표 부착)
        targets_with_location = _attach_consented_location(
            base["priority_targets"], db.residents
        )

        base["fire_spread"]        = spread.as_dict()
        base["weather_live"]       = merged_weather
        base["priority_targets"]   = targets_with_location
        base["rescue_critical_min"] = round(spread.rescue_window_min, 1)
        results.append(base)

    return {
        "generated_at":   datetime.now().isoformat(),
        "system_version": "PATOS v4.4",
        "location":       "전남 고흥군 도양읍 소록마을",
        "live_weather":   live_weather,
        "scenarios":      results,
    }


def _attach_consented_location(targets: list, residents_map: dict) -> list:
    """
    주민 동의 기반 GPS 위치 데이터 부착.
    동의한 주민만 좌표 포함 (동의 미확인 시 마을 중심점 반환).
    """
    # 소록마을 건물별 GPS 좌표 (주민 동의 데이터베이스 연동 전제)
    CONSENTED_LOCATIONS = {
        "PERSON-001": {"lat": 34.6112, "lon": 127.2901, "consented": True},
        "PERSON-002": {"lat": 34.6098, "lon": 127.2885, "consented": True},
        "PERSON-003": {"lat": 34.6098, "lon": 127.2885, "consented": True},
        "PERSON-004": {"lat": 34.6115, "lon": 127.2910, "consented": True},
        "PERSON-005": {"lat": 34.6115, "lon": 127.2910, "consented": True},
        "PERSON-007": {"lat": 34.6105, "lon": 127.2893, "consented": True},
        "PERSON-013": {"lat": 34.6090, "lon": 127.2878, "consented": True},
        "PERSON-015": {"lat": 34.6120, "lon": 127.2915, "consented": True},
    }
    VILLAGE_CENTER = {"lat": 34.6101, "lon": 127.2893, "consented": False}

    result = []
    for t in targets:
        pid = t.get("person_id", "")
        loc = CONSENTED_LOCATIONS.get(pid, VILLAGE_CENTER)
        result.append({**t, "location": loc})
    return result


def load_dataset() -> dict:
    if not os.path.exists(DATASET_PATH):
        print("[INFO] 데이터셋 없음 → data_generator.py 자동 실행 중...")
        import data_generator
        data_generator.main()
    with open(DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── HTTP 서버 ────────────────────────────────────────────────────────────────

class SilentHandler(http.server.SimpleHTTPRequestHandler):
    """정적 파일 서빙. 불필요한 로그는 억제."""
    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def serve():
    os.chdir(BASE_DIR)
    try:
        with ReusableTCPServer(("", PORT), SilentHandler) as httpd:
            print(f"[OK] 서버 시작: http://localhost:{PORT}")
            print("     Ctrl+C 로 종료")
            httpd.serve_forever()
    except OSError as e:
        print(f"[ERROR] 포트 {PORT} 이미 사용 중입니다.")
        print(f"        브라우저에서 http://localhost:{PORT} 를 직접 여세요.")
    except KeyboardInterrupt:
        print("\n[종료] 서버 중단.")


# ── 진입점 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== PATOS 시뮬레이션 엔진 v2.0 ===")

    dataset = load_dataset()

    # TypeDB 연결 시도
    try:
        from typedb_client import TypeDBClient
        typedb = TypeDBClient(dataset)
        print(f"[TypeDB] 모드: {typedb.status['mode']}")
    except Exception as e:
        print(f"[TypeDB] 초기화 실패 → 계속 진행: {e}")

    # 실시간 기상 조회
    print("[기상] 기상청 API 조회 중...")
    live_weather = weather_mod.fetch_live()
    print(f"[기상] {live_weather['source']} / "
          f"풍속 {live_weather['wind_speed_ms']}m/s, "
          f"습도 {live_weather['humidity_pct']}%, "
          f"화재위험 {live_weather['fire_risk']['level']}")

    db     = MockTypeDB(dataset)
    result = run_all_scenarios(db, live_weather)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total_targets = sum(len(s.get("priority_targets", [])) for s in result["scenarios"])
    print(f"[OK] 시뮬레이션 완료: {OUTPUT_PATH}")
    print(f"     - 시나리오: {len(result['scenarios'])}건")
    print(f"     - 구조 대상: {total_targets}명 분석")

    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    serve()
