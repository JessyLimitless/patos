#!/usr/bin/env python3
"""
fire_spread.py — 물리 기반 화재 전파 시뮬레이션
NFPA 72 / 소방청 화재성상 모델 기반 단순화 구현
"""

import math
from dataclasses import dataclass, field
from typing import List

# ── 건축 자재별 연소 특성 ─────────────────────────────────────────────────────

MATERIAL_PROPS = {
    "비닐하우스": {
        "spread_rate_m2_min": 15.0,   # 확산 속도 (m²/min)
        "heat_release_kw":    8500,    # 열방출률 (kW)
        "toxic_gas":          True,    # 유독가스 발생
        "flashover_time_min": 2.0,     # 플래시오버까지 소요 시간
        "structural_fail_factor": 0.6, # 전소 대비 구조 붕괴 시점
        "label": "비닐하우스",
    },
    "샌드위치 패널": {
        "spread_rate_m2_min": 8.0,
        "heat_release_kw":    6000,
        "toxic_gas":          True,    # 폴리우레탄 단열재 → HCN, CO
        "flashover_time_min": 3.5,
        "structural_fail_factor": 0.7,
        "label": "샌드위치 패널",
    },
    "경량 목구조": {
        "spread_rate_m2_min": 6.0,
        "heat_release_kw":    4000,
        "toxic_gas":          False,
        "flashover_time_min": 5.0,
        "structural_fail_factor": 0.8,
        "label": "경량 목구조",
    },
    "슬레이트 지붕 + 조적조": {
        "spread_rate_m2_min": 3.0,
        "heat_release_kw":    2500,
        "toxic_gas":          True,    # 석면 슬레이트
        "flashover_time_min": 8.0,
        "structural_fail_factor": 0.85,
        "label": "슬레이트 지붕 + 조적조",
    },
    "조적조": {
        "spread_rate_m2_min": 1.5,
        "heat_release_kw":    1500,
        "toxic_gas":          False,
        "flashover_time_min": 12.0,
        "structural_fail_factor": 0.9,
        "label": "조적조",
    },
    "철근콘크리트": {
        "spread_rate_m2_min": 0.5,
        "heat_release_kw":    800,
        "toxic_gas":          False,
        "flashover_time_min": 25.0,
        "structural_fail_factor": 0.95,
        "label": "철근콘크리트",
    },
}

DEFAULT_PROPS = MATERIAL_PROPS["조적조"]
ASSUMED_AREA_M2 = 85    # 농촌 단층 단독주택 평균 연면적
ETA_FIRE_MIN    = 12    # 고흥소방서 → 소록마을 ETA (분)


@dataclass
class SpreadResult:
    material:              str
    effective_rate_m2_min: float
    time_engulf_min:       float    # 건물 전소까지
    time_flashover_min:    float    # 플래시오버 (생존 불가 상태)
    time_structural_min:   float    # 구조 붕괴
    neighbor_risk_min:     float    # 인접 건물 위험 시작
    produces_toxic_gas:    bool
    rescue_window_min:     float    # 구조 가능 시간 (플래시오버 전)
    fire_service_eta_min:  int      = ETA_FIRE_MIN
    rescue_before_eta:     bool     = False
    heat_release_kw:       float    = 0.0
    timeline:              List[dict] = field(default_factory=list)
    risk_label:            str      = ""
    risk_color:            str      = ""

    def as_dict(self) -> dict:
        return {
            "material":              self.material,
            "effective_rate_m2_min": round(self.effective_rate_m2_min, 2),
            "time_engulf_min":       round(self.time_engulf_min, 1),
            "time_flashover_min":    round(self.time_flashover_min, 1),
            "time_structural_min":   round(self.time_structural_min, 1),
            "neighbor_risk_min":     round(self.neighbor_risk_min, 1),
            "produces_toxic_gas":    self.produces_toxic_gas,
            "rescue_window_min":     round(self.rescue_window_min, 1),
            "fire_service_eta_min":  self.fire_service_eta_min,
            "rescue_before_eta":     self.rescue_before_eta,
            "heat_release_kw":       self.heat_release_kw,
            "timeline":              self.timeline,
            "risk_label":            self.risk_label,
            "risk_color":            self.risk_color,
        }


def simulate(building: dict, weather: dict) -> SpreadResult:
    """
    건물 + 기상 조건으로 화재 전파 분석.
    결과는 분 단위 타임라인 포함.
    """
    material = building.get("material", "조적조")
    props    = MATERIAL_PROPS.get(material, DEFAULT_PROPS)

    wind_ms  = weather.get("wind_speed_ms", 3.0)
    humidity = weather.get("humidity_pct", 50)
    temp_c   = weather.get("temperature_c", 12.0)

    # 환경 보정 계수
    wind_factor     = 1.0 + (wind_ms / 10.0)           # 강풍 → 빠른 확산
    humidity_factor = 1.0 + max(0, (55 - humidity)) / 100.0  # 건조 → 빠른 확산
    temp_factor     = 1.0 + max(0, (temp_c - 10)) / 50.0

    effective_rate  = props["spread_rate_m2_min"] * wind_factor * humidity_factor * temp_factor
    time_engulf     = ASSUMED_AREA_M2 / effective_rate
    time_flashover  = props["flashover_time_min"] / (wind_factor * 0.8)
    time_structural = time_engulf * props["structural_fail_factor"]

    # 인접 건물 위험 시작: 방사열 기반 (간격 5m 가정)
    gap_m           = 5.0
    radiant_flux    = props["heat_release_kw"] / (4 * math.pi * gap_m ** 2)
    ignition_delay  = max(1.0, 30.0 / (radiant_flux ** 0.5 + 0.1))
    neighbor_risk   = time_engulf * 0.6 + ignition_delay / wind_factor

    rescue_window   = min(time_flashover, time_structural) * 0.8

    # 구조 가능 여부
    rescue_before_eta = rescue_window > ETA_FIRE_MIN

    # 리스크 등급
    if time_flashover <= 5:
        risk_label, risk_color = "극위험 — 즉시 대응", "#7f1d1d"
    elif time_flashover <= ETA_FIRE_MIN:
        risk_label, risk_color = "심각 — 소방차 도착 전 플래시오버", "#dc2626"
    elif time_engulf <= ETA_FIRE_MIN:
        risk_label, risk_color = "위험 — 소방차 도착 전 전소", "#ea580c"
    else:
        risk_label, risk_color = "보통 — 소방차 도착 후 진압 가능", "#16a34a"

    # 분 단위 타임라인 생성
    timeline = _build_timeline(
        time_flashover, time_engulf, time_structural,
        neighbor_risk, ETA_FIRE_MIN, props["toxic_gas"]
    )

    return SpreadResult(
        material=material,
        effective_rate_m2_min=effective_rate,
        time_engulf_min=time_engulf,
        time_flashover_min=time_flashover,
        time_structural_min=time_structural,
        neighbor_risk_min=neighbor_risk,
        produces_toxic_gas=props["toxic_gas"],
        rescue_window_min=rescue_window,
        fire_service_eta_min=ETA_FIRE_MIN,
        rescue_before_eta=rescue_before_eta,
        heat_release_kw=float(props["heat_release_kw"]),
        timeline=timeline,
        risk_label=risk_label,
        risk_color=risk_color,
    )


def _build_timeline(
    t_flashover: float, t_engulf: float, t_structural: float,
    t_neighbor: float, t_eta: int, toxic: bool
) -> list:
    events = []

    events.append({
        "t_min": 0.0,
        "label": "신고 접수",
        "icon":  "phone",
        "color": "#6b7280",
        "desc":  "119 신고 수신 — PATOS 대응 시작",
    })

    if toxic:
        events.append({
            "t_min": round(t_flashover * 0.3, 1),
            "label": "유독가스 발생",
            "icon":  "wind",
            "color": "#7c3aed",
            "desc":  "폴리우레탄/석면 연소 → HCN·CO 발생 시작",
        })

    events.append({
        "t_min": round(t_flashover, 1),
        "label": "플래시오버",
        "icon":  "flame",
        "color": "#dc2626",
        "desc":  "실내 전체 발화 — 생존 불가 환경 도달",
    })

    events.append({
        "t_min": t_eta,
        "label": "소방차 도착",
        "icon":  "truck",
        "color": "#2563eb",
        "desc":  f"고흥소방서 도착 예상 (ETA {t_eta}분)",
    })

    events.append({
        "t_min": round(t_neighbor, 1),
        "label": "인접 건물 위험",
        "icon":  "alert-triangle",
        "color": "#f97316",
        "desc":  "방사열·비화로 인접 구조물 발화 위험 시작",
    })

    events.append({
        "t_min": round(t_structural, 1),
        "label": "구조 붕괴",
        "icon":  "building-2",
        "color": "#1a1a1a",
        "desc":  "건물 구조부 열손상 → 붕괴 위험",
    })

    events.append({
        "t_min": round(t_engulf, 1),
        "label": "전소",
        "icon":  "x-circle",
        "color": "#374151",
        "desc":  "건물 완전 소실",
    })

    events.sort(key=lambda e: e["t_min"])
    return events
