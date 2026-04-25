#!/usr/bin/env python3
"""
PATOS 시나리오 실시간 시뮬레이션
터미널에서 119 신고부터 대응 발령까지 상황을 실시간으로 재현한다.
"""

import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdin  = io.TextIOWrapper(sys.stdin.buffer,  encoding='utf-8', errors='replace')

def p(text="", delay=0.03):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def slow(text, delay=0.05):
    p(text, delay)

def line():
    p("─" * 62, 0.005)

def blank():
    print()

def pause(sec):
    time.sleep(sec)

def blink(text, n=3):
    for _ in range(n):
        sys.stdout.write(f"\r  {text}")
        sys.stdout.flush()
        time.sleep(0.4)
        sys.stdout.write(f"\r  {'':40}")
        sys.stdout.flush()
        time.sleep(0.3)
    sys.stdout.write(f"\r  {text}\n")
    sys.stdout.flush()

def header(title, sub=""):
    blank()
    line()
    slow(f"  {title}")
    if sub:
        p(f"  {sub}", 0.02)
    line()
    blank()

def typing(label, text, char_delay=0.07):
    sys.stdout.write(f"  {label} ")
    sys.stdout.flush()
    time.sleep(0.3)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(char_delay)
    print()

def status(icon, msg, delay=0.8):
    pause(delay)
    p(f"  {icon}  {msg}", 0.02)

def run_scenario_a():
    header("PATOS  v4.4  —  실시간 대응 시뮬레이션", "전남 고흥군 도양읍 소록마을 / 심야 화재 대응")

    slow("  ■ 시나리오 A  |  FIRE-2026-001  |  CRITICAL")
    blank()
    pause(1)

    # ── 신호 수신 ──────────────────────────────────────────
    slow("  [ 02:15:34 ]  119 신고 접수", 0.04)
    blank()
    pause(0.8)

    p("  ┌─ 수신 음성 ──────────────────────────────────┐", 0.01)
    pause(0.3)
    typing("  │", "불이야!  소록마을 안쪽 마 노인네 집에 불이 났어요!")
    pause(0.5)
    typing("  │", "빨리요!  거기 어르신 귀가 어두우셔서 모르실 것 같아요!")
    pause(0.3)
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(1)

    # ── Step 1 ─────────────────────────────────────────────
    status("▶", "[ STEP 1 ]  STT 변환 및 위치·키워드 추출 중...", 0.5)
    pause(1.2)
    status("·", "위치 추출     →  '소록마을 안쪽'")
    status("·", "대상 추출     →  '마 노인네'  →  PERSON-001 매핑")
    status("·", "위험 키워드   →  '귀가 어두워'  →  난청 플래그")
    blank()
    pause(0.8)

    # ── Step 2 ─────────────────────────────────────────────
    status("▶", "[ STEP 2 ]  지식 그래프 조회 중...", 0.5)
    pause(1.5)

    p("  ┌─ 건물 데이터  BLDG-007 ──────────────────────┐", 0.01)
    status("│", "주소       소록마을 23-7  (샌드위치 패널)")
    status("│", "접근로     1.8m  ←  소방차 진입 불가 ✗")
    status("│", "화재감지기 없음  │  가로등  없음")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(0.5)

    p("  ┌─ 거주자  PERSON-001  마순례 ─────────────────┐", 0.01)
    status("│", "연령       84세  │  여  │  독거")
    status("│", "조건       난청  +  거동불편  +  당뇨")
    status("│", "이동능력   mobility_score = 0.16  (매우 낮음)")
    status("│", "비상연락   마씨 자녀  —  서울")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(0.5)

    p("  ┌─ 기상  실시간 ────────────────────────────────┐", 0.01)
    status("│", "풍속  7.2 m/s   │  습도  22%  │  기온  11.5°C")
    status("│", "상태  건조  ←  화재 위험지수  VERY HIGH")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(1)

    # ── Step 3 ─────────────────────────────────────────────
    status("▶", "[ STEP 3 ]  온톨로지 추론 실행 중...", 0.5)
    pause(1.8)

    status("·", "인지취약성   난청(+40) + 연령 84세(+35) + 독거(+10)  →  85점")
    status("·", "물리적고립   접근로 1.8m(+50) + 샌드위치패널(+40)   →  90점")
    status("·", "우선순위점수 85×0.6 + 90×0.4 = 87점  →  최우선 구조 대상")
    blank()
    pause(0.8)

    status("·", "화재전파 시뮬레이션...")
    pause(1.5)

    p("  ┌─ 화재 전파 예측 ──────────────────────────────┐", 0.01)
    status("│", "플래시오버까지   약 2.5분  ←  샌드위치패널 + 풍속 7.2")
    status("│", "구조물 붕괴까지  약 8.1분")
    status("│", "소방차 ETA       12분")
    status("│", "")
    status("│", "생존 가능 공백   9.5분  ←  표준 대응으로 해결 불가")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(1)

    # ── Step 4 ─────────────────────────────────────────────
    blink("[ STEP 4 ]  자율 대응 발령 !", 4)
    blank()
    pause(0.5)

    status("→", "[ 02:15:49 ]  마을방송 자동 송출", 0.3)
    pause(0.5)
    p("             ┌────────────────────────────────────┐", 0.01)
    p("             │  소록마을 주민 여러분께 알립니다.   │", 0.02)
    p("             │  23-7번지 화재 발생.               │", 0.02)
    p("             │  이장님, 인근 주민 즉시 출동 요망.  │", 0.02)
    p("             └────────────────────────────────────┘", 0.01)
    blank()

    status("→", "[ 02:15:50 ]  이장단 ARS 발송", 0.5)
    status("→", "[ 02:15:52 ]  고흥소방서 MDT 전술정보 송출", 0.5)
    blank()
    pause(0.8)

    p("  ┌─ 소방서 MDT 수신 정보 ───────────────────────┐", 0.01)
    status("│", "발화   소록마을 23-7  샌드위치패널  접근로 1.8m")
    status("│", "구조대상  마순례 84세  난청  거동불편  독거")
    status("│", "⚠  소방차 진입 불가  —  도보 접근 필수")
    status("│", "⚠  플래시오버 02:18경 예상  —  2분 30초 남음")
    status("│", "⚠  비상연락(서울) 실효 없음  —  이장 직접 연락 권장")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(1)

    line()
    slow("  [ 02:15:49 ]  대응 완료  —  신고 접수 후 15초")
    line()
    blank()


def run_scenario_d():
    header("PATOS  v4.4  —  실시간 대응 시뮬레이션", "전남 고흥군 도양읍 소록마을 / 심야 화재 대응")

    slow("  ■ 시나리오 D  |  FIRE-2026-004  |  CRITICAL  ←  가장 극단적", 0.04)
    blank()
    pause(1)

    slow("  [ 01:52:07 ]  119 신고 접수", 0.04)
    blank()
    pause(0.8)

    p("  ┌─ 수신 음성 ──────────────────────────────────┐", 0.01)
    pause(0.3)
    typing("  │", "소록마을인데요, 지금 조 할머니 댁에서 불꽃이 보여요!")
    pause(0.5)
    typing("  │", "비닐하우스 쪽이요. 심야에 혼자 계실 텐데!")
    pause(0.5)
    typing("  │", "치매도 있으셔서 어디 계신지도 몰라요!")
    pause(0.3)
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(1)

    status("▶", "[ STEP 1 ]  STT 변환 및 위치·키워드 추출 중...", 0.5)
    pause(1.2)
    status("·", "위치 추출     →  '소록마을'  +  '비닐하우스'")
    status("·", "대상 추출     →  '조 할머니'  →  PERSON-015 매핑")
    status("·", "위험 키워드   →  '치매'  '어디 계신지 모름'  →  위치 불명 플래그")
    blank()
    pause(0.8)

    status("▶", "[ STEP 2 ]  지식 그래프 조회 중...", 0.5)
    pause(1.5)

    p("  ┌─ 건물 데이터  BLDG-008 ──────────────────────┐", 0.01)
    status("│", "주소       소록마을 27-2  (비닐하우스)")
    status("│", "접근로     1.5m  ←  차량 완전 불가 ✗✗")
    status("│", "화재감지기 없음  │  가로등  없음")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()

    p("  ┌─ 거주자  PERSON-015  조옥순 ─────────────────┐", 0.01)
    status("│", "연령       88세  │  여  │  독거")
    status("│", "조건       난청  +  치매  +  거동불편  +  고혈압")
    status("│", "이동능력   mobility_score = 0.40")
    status("│", "비상연락   조씨 자녀  —  여수  (30~40분 거리)")
    status("│", "현재 위치  불명  ←  비닐하우스 내? 본채?")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()

    p("  ┌─ 기상  실시간 ────────────────────────────────┐", 0.01)
    status("│", "풍속  6.8 m/s   │  습도  18%  ←  최저")
    status("│", "상태  극건조  ←  화재 위험지수  CRITICAL")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(1)

    status("▶", "[ STEP 3 ]  온톨로지 추론 실행 중...", 0.5)
    pause(1.8)

    status("·", "화재전파 시뮬레이션...")
    pause(1.5)

    p("  ┌─ 화재 전파 예측 ──────────────────────────────┐", 0.01)
    status("│", "자재  비닐하우스  →  기본 확산속도 15.0 m²/min")
    status("│", "환경  풍속 6.8  습도 18  →  보정계수 ×2.1")
    status("│", "")
    status("│", "플래시오버까지   약 1분 30초  ←  신고 후 75초")
    status("│", "소방차 ETA       12분")
    status("│", "")
    blank()
    pause(0.3)
    blink("  │  ⚠  경고: 추론 완료 시점에 이미 플래시오버 가능 !", 3)
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(0.8)

    status("·", "인접 건물 연소 위험 분석...")
    pause(1.2)
    status("·", "BLDG-009  소록마을 31-6  경량목구조  접근로 3.0m")
    status("·", "         풍속 6.8m/s 기준 3분 내 연소 가능")
    status("·", "         거주자 박말순(82세) + 정순자(76세)  추가 위험")
    blank()
    pause(1)

    blink("[ STEP 4 ]  자율 대응 발령 !", 4)
    blank()

    status("→", "[ 01:52:22 ]  마을방송 자동 송출  (소록마을 27-2 + 31-6 경보)", 0.3)
    status("→", "[ 01:52:23 ]  이장단 ARS  —  비닐하우스 즉각 도보 접근 요청", 0.5)
    status("→", "[ 01:52:24 ]  여수 비상연락  (조씨 자녀)  상황 통보 발송", 0.5)
    status("→", "[ 01:52:25 ]  고흥소방서 MDT 전술정보 송출", 0.5)
    blank()
    pause(0.8)

    p("  ┌─ 소방서 MDT 수신 정보 ───────────────────────┐", 0.01)
    status("│", "발화   소록마을 27-2  비닐하우스  접근로 1.5m")
    status("│", "구조대상  조옥순 88세  난청+치매+거동불편  독거")
    status("│", "⚠  플래시오버 01:53:37 예상  —  이미 경과 가능")
    status("│", "⚠  거주자 위치 불명  —  본채 우선 수색 권장")
    status("│", "⚠  인접 31-6번지 주민 2명 추가 대피 필요")
    status("│", "⚠  차량 완전 불가  —  도보 인원 최소 3명 필요")
    p("  └──────────────────────────────────────────────┘", 0.01)
    blank()
    pause(1)

    line()
    slow("  [ 01:52:22 ]  대응 완료  —  신고 접수 후 15초")
    slow("  단, 플래시오버(1분 30초)와의 공백은 75초")
    slow("  사전 위험 등록 없이는 구조 한계 도달 불가피")
    line()
    blank()


def menu():
    header("PATOS  v4.4  —  시나리오 시뮬레이션", "소록마을 심야 화재 대응 실시간 재현")

    p("  실행할 시나리오를 선택하세요:", 0.03)
    blank()
    p("    A  │  FIRE-2026-001  │  CRITICAL  │  마순례 84세  샌드위치패널  1.8m")
    p("    B  │  FIRE-2026-002  │  HIGH      │  이봉길+김복순  경량목구조  2명 동시")
    p("    C  │  FIRE-2026-003  │  MODERATE  │  강덕현+윤금순  조적조  부부")
    p("    D  │  FIRE-2026-004  │  CRITICAL  │  조옥순 88세  비닐하우스  위치불명")
    p("    E  │  FIRE-2026-005  │  HIGH      │  박용철 85세  샌드위치패널  심장질환")
    p("    Q  │  종료")
    blank()

    while True:
        choice = input("  선택 > ").strip().upper()
        if choice == "A":
            run_scenario_a()
        elif choice == "D":
            run_scenario_d()
        elif choice == "B":
            p("  ※ 시나리오 B는 준비 중입니다.")
        elif choice == "C":
            p("  ※ 시나리오 C는 준비 중입니다.")
        elif choice == "E":
            p("  ※ 시나리오 E는 준비 중입니다.")
        elif choice == "Q":
            p("  종료합니다.")
            break
        else:
            p("  A / B / C / D / E / Q 중 선택하세요.")
        blank()
        choice2 = input("  다시 실행하시겠습니까? (Y / Q) > ").strip().upper()
        if choice2 != "Y":
            p("  종료합니다.")
            break
        menu()
        break


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        blank()
        p("  중단됨.")
