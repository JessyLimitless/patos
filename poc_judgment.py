"""
PATOS 판단 엔진 POC
Layer 1+2+3 → 컨텍스트 조립 → Claude Code 판단 요청

실행: python poc_judgment.py
출력: judgment_prompt.txt (Claude Code에 붙여넣을 전체 프롬프트)
"""

import json, sys, os, datetime
sys.stdout.reconfigure(encoding="utf-8")

from poc_jeonnam import load_data, calc_vulnerability, build_fire_context

DIV  = "=" * 65
DIV2 = "-" * 65
TOP_N = 5


def main():
    data   = load_data()
    ranked = calc_vulnerability(data["regions"])

    contexts = []
    for region in ranked[:TOP_N]:
        ctx = build_fire_context(region, data)
        contexts.append({
            "region_id"  : region["region_id"],
            "region_name": region["name"],
            "vuln_score" : region["vuln_score"],
            "context"    : ctx,
        })

    # ── 판단 요청 프롬프트 조립 ──
    prompt = f"""# PATOS 판단 엔진 — AI 판단 요청
생성: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
파이프라인: 시맨틱(TypeDB 온톨로지) → 키네틱(취약도 산출) → 다이나믹(컨텍스트 조립)

---

## 판단 요청

전라남도 화재 취약 지역 상위 {TOP_N}개에 대해 소방 트리아지 판단을 내려주세요.

**TypeDB 추론 규칙 참조:**
- physical-isolation-by-island: 도서지역 → 물리적 고립
- reachable-by-neighbor: 인접 시군 → 지원 가능 소방서 자동 탐색
- coverage-gap: 출동 20분↑ + 차량 2대↓ → 커버리지 갭
- forest-adjacency-risk: 산림인접 + 풍속 → 확산 위험 가중
- jurisdiction-conflict: 소방서 이중 관할 → 자원 분산 위험

**에스컬레이션 기준:**
취약도 0.6↑ + 차량 2대↓ + (도서 or 산림) 중 2개 이상 동시 충족

**응답 형식 (각 지역마다):**
{{
  "region_id": "...",
  "region_name": "...",
  "judgment": {{
    "상황_요약": "2~3문장",
    "위험_등급": "CRITICAL|HIGH|MEDIUM|LOW",
    "온톨로지_추론_발동": [
      {{"규칙명": "...", "내용": "...", "판단_영향": "..."}}
    ],
    "트리아지_결정": {{
      "우선순위_근거": "...",
      "자원_배분": "..."
    }},
    "대응_프로토콜": {{
      "즉시_조치": "...",
      "지원_요청": "...",
      "에스컬레이션_여부": true/false,
      "에스컬레이션_근거": "... or null"
    }},
    "선제_경보_지역": ["..."],
    "추론_체인": "...",
    "신뢰도": 0.0~1.0
  }}
}}

---

## 조립된 컨텍스트 ({TOP_N}개 지역)

"""

    for i, item in enumerate(contexts):
        prompt += f"### [{i+1}] {item['region_name']} — 취약도 {item['vuln_score']:.3f}\n"
        prompt += json.dumps(item["context"], ensure_ascii=False, indent=2)
        prompt += "\n\n"

    prompt += "---\n\n위 5개 지역에 대해 판단을 내려주세요.\n"

    # 파일 저장
    with open("judgment_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    # 터미널 출력
    print(DIV)
    print("PATOS 판단 엔진 — 컨텍스트 조립 완료")
    print(DIV)
    print()
    print(f"  대상: {TOP_N}개 취약지역")
    for i, item in enumerate(contexts):
        print(f"  [{i+1}] {item['region_name']:<8} 취약도 {item['vuln_score']:.3f}")
    print()
    print(DIV)
    print("다음 단계 — Claude Code로 판단 요청")
    print(DIV)
    print()
    print("  방법 1 (이 대화창에 붙여넣기):")
    print("    → judgment_prompt.txt 내용을 Claude Code에 붙여넣기")
    print()
    print("  방법 2 (CLI 직접 파이프):")
    print("    → cat judgment_prompt.txt | claude")
    print()
    print(f"  저장됨: judgment_prompt.txt ({len(prompt):,} chars)")
    print()
    print("  Claude 응답을 judgment_result.json으로 저장하면")
    print("  jeonnam_fire.html 판단 엔진 뷰에 자동 표시됩니다.")
    print(DIV)


if __name__ == "__main__":
    main()
