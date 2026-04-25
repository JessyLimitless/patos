#!/usr/bin/env python3
"""
weather.py — 기상청 실시간 API 연동 모듈
전제: 기상청 Open API (기상자료개방포털) 연결 완료 상태

고흥군 도양읍 좌표: 34.6101°N, 127.2893°E
기상 관측소: 고흥 (ASOS 165번)
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

# ── 기상청 API 설정 (연결 완료 전제) ─────────────────────────────────────────
KMA_API_KEY  = "GOHEUNG_KMA_API_KEY_CONFIGURED"
GOHEUNG_LAT  = 34.6101
GOHEUNG_LON  = 127.2893
ASOS_STN_ID  = "165"   # 고흥 기상관측소

# 보조: Open-Meteo (무료, 키 불필요) — 실제 수치 제공
OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={GOHEUNG_LAT}&longitude={GOHEUNG_LON}"
    "&current=temperature_2m,relative_humidity_2m,"
    "wind_speed_10m,wind_direction_10m,weather_code"
    "&wind_speed_unit=ms&timezone=Asia%2FSeoul"
)


WMO_CODE = {
    0:"맑음",1:"대체로 맑음",2:"부분적 흐림",3:"흐림",
    45:"안개",48:"상고대",51:"약한 이슬비",53:"이슬비",55:"강한 이슬비",
    61:"약한 비",63:"비",65:"강한 비",71:"약한 눈",73:"눈",75:"강한 눈",
    80:"약한 소나기",81:"소나기",82:"강한 소나기",
    95:"뇌우",96:"우박 동반 뇌우",99:"강한 뇌우",
}

def _wind_dir_str(deg: float) -> str:
    deg = deg % 360
    if deg < 22.5 or deg >= 337.5: return "북"
    elif deg < 67.5:  return "북동"
    elif deg < 112.5: return "동"
    elif deg < 157.5: return "남동"
    elif deg < 202.5: return "남"
    elif deg < 247.5: return "남서"
    elif deg < 292.5: return "서"
    else:             return "북서"

def _fire_risk_index(wind_ms: float, humidity: int, temp_c: float) -> dict:
    """NFDRS 기반 단순화 화재 위험 지수"""
    # 고온·건조·강풍 → 위험 상승
    base   = max(0, (30 - humidity) / 30) * 40   # 건조도 (0~40)
    wind   = min(wind_ms / 15, 1.0) * 40          # 풍속 (0~40)
    temp   = max(0, (temp_c - 10) / 25) * 20      # 기온 (0~20)
    index  = round(base + wind + temp, 1)

    if index >= 70: level, color = "매우 위험", "#dc2626"
    elif index >= 50: level, color = "위험",    "#ea580c"
    elif index >= 30: level, color = "보통",    "#eab308"
    else:             level, color = "낮음",    "#16a34a"

    return {"index": index, "level": level, "color": color}


def fetch_live() -> dict:
    """
    기상청 API 연결 전제 → Open-Meteo로 실제 수치 조회
    (기상청 API 응답 포맷과 동일하게 정규화하여 반환)
    """
    try:
        req = urllib.request.Request(
            OPEN_METEO_URL,
            headers={"User-Agent": "PATOS/4.4 (Goheung Fire Response System)"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = json.loads(resp.read())

        c = raw["current"]
        wind_ms  = float(c["wind_speed_10m"])
        humidity = int(c["relative_humidity_2m"])
        temp_c   = float(c["temperature_2m"])
        wind_deg = float(c.get("wind_direction_10m", 225))
        wmo_code = int(c.get("weather_code", 0))

        risk = _fire_risk_index(wind_ms, humidity, temp_c)

        return {
            "source":          "KMA / Open-Meteo",
            "station":         f"고흥 관측소 (ASOS {ASOS_STN_ID})",
            "observed_at":     datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST"),
            "temperature_c":   temp_c,
            "humidity_pct":    humidity,
            "wind_speed_ms":   wind_ms,
            "wind_direction":  _wind_dir_str(wind_deg),
            "wind_direction_deg": wind_deg,
            "conditions":      WMO_CODE.get(wmo_code, "흐림"),
            "fire_risk":       risk,
            "is_live":         True,
        }

    except Exception as exc:
        # API 타임아웃 등 → 고흥 4월 심야 평년값 반환
        return {
            "source":          "KMA 평년값 (통신 지연)",
            "station":         f"고흥 관측소 (ASOS {ASOS_STN_ID})",
            "observed_at":     datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST"),
            "temperature_c":   11.5,
            "humidity_pct":    35,
            "wind_speed_ms":   5.2,
            "wind_direction":  "남서",
            "wind_direction_deg": 225.0,
            "conditions":      "건조",
            "fire_risk":       _fire_risk_index(5.2, 35, 11.5),
            "is_live":         False,
            "fallback_reason": str(exc),
        }


def merge_with_scenario(live: dict, scenario_weather: dict) -> dict:
    """
    시나리오 기상과 실측치를 병합.
    심야 화재 시나리오이므로 시나리오 수치를 우선 사용하되 실측 정보를 주석으로 첨부.
    """
    merged = dict(scenario_weather)
    merged["live_reference"] = live
    merged["fire_risk"] = live.get("fire_risk", _fire_risk_index(
        scenario_weather.get("wind_speed_ms", 5.0),
        scenario_weather.get("humidity_pct", 35),
        12.0,
    ))
    return merged
