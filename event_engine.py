"""
PATOS v5 — Event-driven Re-planning Engine
돌발변수 발생 시 DB 상태를 재구성하고 추론을 재실행하는 핵심 엔진.

핵심 패턴:
    정적 기반 DB (불변) + 이벤트 델타 (누적) → 현재 세계 상태 → 추론 재실행
"""

from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum
import time


# ─────────────────────────────────────────
# 1. 이벤트 정의
# ─────────────────────────────────────────

class EventType(Enum):
    FIRE_SPREAD      = "fire_spread"       # 화재 인접 건물로 확산
    RESIDENT_ESCAPED = "resident_escaped"  # 거주자 자력 탈출 확인
    ROAD_BLOCKED     = "road_blocked"      # 진입 도로 차단
    RESOURCE_ARRIVED = "resource_arrived"  # 소방 자원 현장 도착


@dataclass
class Event:
    type: EventType
    target_id: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict   = field(default_factory=dict)


# ─────────────────────────────────────────
# 2. 세계 상태 (Base + Delta 병합 결과)
# ─────────────────────────────────────────

@dataclass
class WorldState:
    buildings: Dict
    residents: Dict
    fires:         Dict = field(default_factory=dict)   # {building_id: True}
    escaped:       List = field(default_factory=list)   # [resident_id, ...]
    blocked_roads: List = field(default_factory=list)   # [building_id, ...]


# ─────────────────────────────────────────
# 3. 이벤트 델타 저장소 (불변 이벤트 로그)
#
#    DB를 직접 수정하지 않는다.
#    이벤트를 순서대로 쌓고, 조회 시 base 위에 오버레이한다.
# ─────────────────────────────────────────

class EventDeltaStore:
    def __init__(self):
        self._log: List[Event] = []

    def append(self, event: Event):
        self._log.append(event)

    def apply_to(self, base_db: dict) -> WorldState:
        """base_db 위에 모든 이벤트를 순서대로 적용해 현재 세계 상태를 반환."""
        state = WorldState(
            buildings=base_db["buildings"].copy(),
            residents=base_db["residents"].copy(),
        )
        for ev in self._log:
            if ev.type == EventType.FIRE_SPREAD:
                state.fires[ev.target_id] = True
            elif ev.type == EventType.RESIDENT_ESCAPED:
                state.escaped.append(ev.target_id)
            elif ev.type == EventType.ROAD_BLOCKED:
                state.blocked_roads.append(ev.target_id)
        return state

    @property
    def history(self) -> List[Event]:
        return list(self._log)


# ─────────────────────────────────────────
# 4. 추론 엔진 (WorldState → 우선순위 목록)
# ─────────────────────────────────────────

class InferenceEngine:

    def run(self, state: WorldState) -> List[Dict]:
        results = []
        for r_id, resident in state.residents.items():
            if r_id in state.escaped:
                continue

            building_id = resident["building_id"]
            building    = state.buildings[building_id]

            fire_direct   = state.fires.get(building_id, False)
            fire_adjacent = any(
                state.fires.get(adj_id, False)
                for adj_id in building.get("adjacent_buildings", [])
            )

            cog_score  = self._cognitive_score(resident)
            phys_score = self._physical_score(building, state.blocked_roads)
            priority   = round(cog_score * 0.6 + phys_score * 0.4, 1)

            results.append({
                "resident_id":   r_id,
                "name":          resident["name"],
                "building_id":   building_id,
                "priority_score": priority,
                "fire_direct":   fire_direct,
                "fire_adjacent": fire_adjacent,
                "road_blocked":  building_id in state.blocked_roads,
            })

        return sorted(results, key=lambda x: x["priority_score"], reverse=True)

    def _cognitive_score(self, resident: dict) -> float:
        score = 0
        age = resident.get("age", 0)
        if age >= 80:   score += 40
        elif age >= 65: score += 20
        if resident.get("disability"): score += 30
        if resident.get("dementia"):   score += 30
        return min(score, 100)

    def _physical_score(self, building: dict, blocked_roads: list) -> float:
        material_base = {"vinyl": 40, "wood": 30, "brick": 15, "concrete": 5}
        score = material_base.get(building.get("material", "brick"), 15)
        if building.get("id") in blocked_roads:        score += 30
        if building.get("road_width_m", 4) < 3:        score += 20
        return min(score, 100)


# ─────────────────────────────────────────
# 5. Re-planning Loop (핵심 오케스트레이터)
#
#    이벤트 1개 → 델타 추가 → 상태 병합 → 추론 재실행 → 새 플랜 반환
# ─────────────────────────────────────────

class ReplanningLoop:

    def __init__(self, base_db: dict):
        self.base_db      = base_db
        self.delta_store  = EventDeltaStore()
        self.engine       = InferenceEngine()
        self._plan_version = 0

    def handle_event(self, event: Event) -> dict:
        t0 = time.time()

        # Step 1: 이벤트를 불변 로그에 추가
        self.delta_store.append(event)

        # Step 2: base_db + 누적 이벤트 → 현재 세계 상태
        world_state = self.delta_store.apply_to(self.base_db)

        # Step 3: 전체 추론 재실행
        new_priorities = self.engine.run(world_state)

        self._plan_version += 1
        elapsed_ms = round((time.time() - t0) * 1000, 1)

        return {
            "plan_version":    self._plan_version,
            "trigger_event":   event.type.value,
            "trigger_target":  event.target_id,
            "elapsed_ms":      elapsed_ms,
            "priority_targets": new_priorities,
            "world_snapshot": {
                "active_fires":  list(world_state.fires.keys()),
                "escaped":       world_state.escaped,
                "blocked_roads": world_state.blocked_roads,
            },
        }

    def current_state(self) -> WorldState:
        return self.delta_store.apply_to(self.base_db)


# ─────────────────────────────────────────
# 데모 실행 — "불이 옆집으로 번지는" 시나리오
# ─────────────────────────────────────────

if __name__ == "__main__":
    BASE_DB = {
        "buildings": {
            "house_A": {"id": "house_A", "material": "vinyl",   "road_width_m": 2.5, "adjacent_buildings": ["house_B"]},
            "house_B": {"id": "house_B", "material": "wood",    "road_width_m": 3.0, "adjacent_buildings": ["house_A", "house_C"]},
            "house_C": {"id": "house_C", "material": "brick",   "road_width_m": 4.0, "adjacent_buildings": ["house_B"]},
        },
        "residents": {
            "r001": {"name": "김순자", "age": 84, "disability": True,  "dementia": False, "building_id": "house_A"},
            "r002": {"name": "박정수", "age": 71, "disability": False, "dementia": False, "building_id": "house_B"},
            "r003": {"name": "이복순", "age": 88, "disability": False, "dementia": True,  "building_id": "house_C"},
        },
    }

    loop = ReplanningLoop(BASE_DB)

    print("=" * 55)
    print("PATOS v5 — Event-driven Re-planning 데모")
    print("=" * 55)

    events = [
        Event(EventType.FIRE_SPREAD,      "house_A"),
        Event(EventType.FIRE_SPREAD,      "house_B"),
        Event(EventType.RESIDENT_ESCAPED, "r002"),
        Event(EventType.ROAD_BLOCKED,     "house_C"),
    ]

    labels = [
        "최초 화재: house_A 발화",
        "화재 확산: house_B로 번짐",
        "돌발변수: 박정수 자력 탈출",
        "돌발변수: house_C 진입로 차단",
    ]

    for label, event in zip(labels, events):
        result = loop.handle_event(event)
        print(f"\n[플랜 v{result['plan_version']}] {label}  ({result['elapsed_ms']} ms)")
        print(f"  활성 화재: {result['world_snapshot']['active_fires']}")
        print(f"  탈출 확인: {result['world_snapshot']['escaped']}")
        print(f"  도로 차단: {result['world_snapshot']['blocked_roads']}")
        print("  우선 구조 순서:")
        for i, t in enumerate(result["priority_targets"], 1):
            flags = []
            if t["fire_direct"]:   flags.append("직접 화재")
            if t["fire_adjacent"]: flags.append("인접 화재")
            if t["road_blocked"]:  flags.append("도로 차단")
            print(f"    {i}. {t['name']} ({t['priority_score']}점)  {' / '.join(flags)}")
