"""
전라남도 취약지역 화재예측 + 대응 POC
Layer 1 시맨틱: TypeDB 온톨로지 정의
Layer 2 키네틱: 취약도 계산 + 커버리지 갭
Layer 3 다이나믹: 화재 이벤트 컨텍스트 조립 → 출력 (추론은 Claude Code)

실행: python poc_jeonnam.py
"""

import json
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "jeonnam_sample.json")
DIV  = "=" * 65
DIV2 = "-" * 65


# ══════════════════════════════════════════════════════════════
# LAYER 1 — 시맨틱
# ══════════════════════════════════════════════════════════════

TYPEQL_SCHEMA = """define

  region-id      sub attribute, value string;
  region-name    sub attribute, value string;
  old-bldg-ratio sub attribute, value double;
  fire-count-5y  sub attribute, value long;
  avg-response   sub attribute, value double;
  island-yn      sub attribute, value boolean;
  forest-yn      sub attribute, value boolean;
  vuln-score     sub attribute, value double;

  station-id     sub attribute, value string;
  station-name   sub attribute, value string;
  truck-count    sub attribute, value long;

  region sub entity,
    owns region-id,   owns region-name,
    owns old-bldg-ratio, owns fire-count-5y,
    owns avg-response,   owns island-yn,
    owns forest-yn,      owns vuln-score,
    plays jurisdiction:area,
    plays adjacency:neighbor;

  fire-station sub entity,
    owns station-id, owns station-name, owns truck-count,
    plays jurisdiction:station;

  jurisdiction sub relation, relates station, relates area;
  adjacency    sub relation, relates neighbor;

  rule reachable-by-neighbor:
    when {
      (station: $s, area: $a) isa jurisdiction;
      (neighbor: $a, neighbor: $b) isa adjacency;
    } then {
      (station: $s, area: $b) isa jurisdiction;
    };"""


def load_data() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════
# LAYER 2 — 키네틱
# ══════════════════════════════════════════════════════════════

WEIGHTS = {
    "old_building" : 0.30,
    "response_time": 0.30,
    "fire_density" : 0.15,
    "island"       : 0.15,
    "forest"       : 0.10,
}


def _normalize(values: list) -> list:
    mn, mx = min(values), max(values)
    return [(v - mn) / (mx - mn) if mx != mn else 0.5 for v in values]


def calc_vulnerability(regions: list) -> list:
    n_old  = _normalize([r["old_building_ratio"] for r in regions])
    n_resp = _normalize([r["avg_response_min"]   for r in regions])
    n_fire = _normalize([r["fire_count_5y"] / r["area_km2"] for r in regions])

    scored = []
    for i, r in enumerate(regions):
        score = (
            WEIGHTS["old_building"]  * n_old[i]  +
            WEIGHTS["response_time"] * n_resp[i] +
            WEIGHTS["fire_density"]  * n_fire[i] +
            WEIGHTS["island"]        * (1.0 if r["island_district"] else 0.0) +
            WEIGHTS["forest"]        * (1.0 if r["forest_adjacent"] else 0.0)
        )
        scored.append({**r, "vuln_score": round(score, 3)})

    return sorted(scored, key=lambda x: x["vuln_score"], reverse=True)


def find_station(region_id: str, stations: list) -> dict:
    return next((s for s in stations if region_id in s["covers"]), None)


def find_adjacent(region_id: str, adjacency: list, regions: list) -> list:
    adj_ids = set()
    for pair in adjacency:
        if pair[0] == region_id: adj_ids.add(pair[1])
        if pair[1] == region_id: adj_ids.add(pair[0])
    return [r for r in regions if r["region_id"] in adj_ids]


# ══════════════════════════════════════════════════════════════
# LAYER 3 — 다이나믹: 컨텍스트 조립
# ══════════════════════════════════════════════════════════════

def build_fire_context(target: dict, data: dict) -> dict:
    station = find_station(target["region_id"], data["fire_stations"])
    weather = data["weather_current"]["by_region"].get(target["region_id"], {})
    adj     = find_adjacent(target["region_id"], data["adjacency"], data["regions"])

    return {
        "화재발생지역"  : target["name"],
        "취약도점수"   : target["vuln_score"],
        "노후건물비율"  : f"{target['old_building_ratio']*100:.0f}%",
        "평균출동시간"  : f"{target['avg_response_min']}분",
        "도서지역"     : target["island_district"],
        "산림인접"     : target["forest_adjacent"],
        "현재기상"     : {
            "습도"        : f"{weather.get('humidity_pct','?')}%",
            "풍속"        : f"{weather.get('wind_speed_ms','?')}m/s",
            "건조주의보"  : weather.get("dry_alert", False),
        },
        "관할소방서"   : {
            "이름"  : station["name"] if station else "미배정",
            "차량수": station["trucks"] if station else 0,
            "인원"  : station["personnel"] if station else 0,
        },
        "인접지역"     : [
            {
                "이름"      : r["name"],
                "노후건물"  : f"{r['old_building_ratio']*100:.0f}%",
                "산림인접"  : r["forest_adjacent"],
                "출동시간"  : f"{r['avg_response_min']}분",
            }
            for r in adj
        ],
    }


# ══════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════

def main():
    data   = load_data()
    ranked = calc_vulnerability(data["regions"])

    # ── Layer 1 출력 ──
    print(DIV)
    print("LAYER 1 — 시맨틱: TypeQL 스키마")
    print(DIV)
    print(TYPEQL_SCHEMA)
    reg = data["regions"]
    sta = data["fire_stations"]
    adj = data["adjacency"]
    print(f"\n  엔티티: region {len(reg)}개 | fire-station {len(sta)}개")
    print(f"  관계  : jurisdiction {len(sta)}건 | adjacency {len(adj)}쌍")
    print(f"  추론  : reachable-by-neighbor 규칙")

    # ── Layer 2 출력 ──
    print()
    print(DIV)
    print("LAYER 2 — 키네틱: 취약도 순위 (전라남도 22개 시군)")
    print(DIV)
    print(f"\n  {'순위':<4} {'지역':<8} {'점수':>5}  {'노후건물':>6}  {'출동(분)':>7}  특이사항")
    print(f"  {DIV2}")
    for i, r in enumerate(ranked):
        flags = []
        if r["island_district"]:          flags.append("도서")
        if r["forest_adjacent"]:          flags.append("산림")
        if r["old_building_ratio"] >= 0.6: flags.append("노후多")
        if r["avg_response_min"]   >= 20:  flags.append("출동지연")
        print(f"  {i+1:<4} {r['name']:<8} {r['vuln_score']:>5.3f}"
              f"  {r['old_building_ratio']*100:>5.0f}%"
              f"  {r['avg_response_min']:>7.1f}분"
              f"  {' | '.join(flags) if flags else '—'}")

    # 커버리지 갭
    print(f"\n  [커버리지 갭 — 출동 20분↑ + 차량 2대↓]")
    for r in ranked[:10]:
        s = find_station(r["region_id"], data["fire_stations"])
        if r["avg_response_min"] >= 20 and s and s["trucks"] <= 2:
            print(f"  ⚠  {r['name']}: 출동 {r['avg_response_min']}분, 차량 {s['trucks']}대")

    # ── Layer 3 출력 ──
    print()
    print(DIV)
    print("LAYER 3 — 다이나믹: 화재 이벤트 컨텍스트 (취약도 1위 지역)")
    print(DIV)
    context = build_fire_context(ranked[0], data)
    print(json.dumps(context, ensure_ascii=False, indent=2))

    print()
    print(DIV)
    print("완료 — 위 컨텍스트를 Claude Code에 붙여 추론 요청")
    print(DIV)


if __name__ == "__main__":
    main()
