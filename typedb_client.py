#!/usr/bin/env python3
"""
typedb_client.py — TypeDB 2.x 실제 연결 클라이언트
전제: TypeDB Core 서버 localhost:1729 구동 중, 'patos' 데이터베이스 존재

실제 TQL(TypeQL) 쿼리로 추론 규칙 실행.
"""

import json
from typing import Optional

# TypeDB Python 드라이버 (pip install typedb-driver)
try:
    from typedb.driver import TypeDB, SessionType, TransactionType
    TYPEDB_AVAILABLE = True
except ImportError:
    TYPEDB_AVAILABLE = False

TYPEDB_URI = "localhost:1729"
TYPEDB_DB  = "patos"


# ── TQL 쿼리 템플릿 ─────────────────────────────────────────────────────────

TQL_INIT_SCHEMA = """
define
  person-id sub attribute, value string;
  building-id sub attribute, value string;
  resource-id sub attribute, value string;
  event-id sub attribute, value string;
  name sub attribute, value string;
  age sub attribute, value long;
  phone sub attribute, value string;
  lives-alone sub attribute, value boolean;
  hearing-impaired sub attribute, value boolean;
  has-dementia sub attribute, value boolean;
  chronic-condition sub attribute, value string;
  cognitive-vulnerability sub attribute, value boolean;
  address sub attribute, value string;
  material sub attribute, value string;
  access-road-width sub attribute, value double;
  has-fire-detector sub attribute, value boolean;
  physical-isolation sub attribute, value boolean;
  call-content sub attribute, value string;
  severity sub attribute, value string;
  fire-origin sub attribute, value string;
  priority-score sub attribute, value double;
  rescue-action sub attribute, value string;

  person sub entity,
    owns person-id @key, owns name, owns age, owns phone,
    owns lives-alone, owns hearing-impaired, owns has-dementia,
    owns chronic-condition, owns cognitive-vulnerability,
    plays residence:resident, plays incident:victim;

  building sub entity,
    owns building-id @key, owns address, owns material,
    owns access-road-width, owns has-fire-detector, owns physical-isolation,
    plays residence:dwelling, plays incident:site;

  fire-event sub entity,
    owns event-id @key, owns call-content, owns severity, owns fire-origin,
    plays incident:event;

  residence sub relation, relates resident, relates dwelling;
  incident sub relation, relates event, relates site, relates victim;

  rule cognitive-vulnerability-by-age:
    when { $p isa person, has age $a; $a >= 80; }
    then { $p has cognitive-vulnerability true; };

  rule cognitive-vulnerability-by-hearing:
    when { $p isa person, has hearing-impaired true; }
    then { $p has cognitive-vulnerability true; };

  rule cognitive-vulnerability-by-dementia:
    when { $p isa person, has has-dementia true; }
    then { $p has cognitive-vulnerability true; };

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
"""

TQL_INSERT_PERSON = """
insert $p isa person,
  has person-id "{pid}",
  has name "{name}",
  has age {age},
  has phone "{phone}",
  has lives-alone {lives_alone},
  has hearing-impaired {hearing},
  has has-dementia {dementia}{cond_attrs};
"""

TQL_INSERT_BUILDING = """
insert $b isa building,
  has building-id "{bid}",
  has address "{address}",
  has material "{material}",
  has access-road-width {width},
  has has-fire-detector {detector};
"""

TQL_INSERT_RESIDENCE = """
match
  $p isa person, has person-id "{pid}";
  $b isa building, has building-id "{bid}";
insert (resident: $p, dwelling: $b) isa residence;
"""

TQL_INSERT_FIRE_EVENT = """
insert $e isa fire-event,
  has event-id "{eid}",
  has call-content "{call}",
  has severity "{severity}",
  has fire-origin "{origin}";
"""

TQL_QUERY_COG_VULN = """
match
  $p isa person, has person-id "{pid}", has cognitive-vulnerability $cv;
get $cv;
"""

TQL_QUERY_PHYS_ISOL = """
match
  $b isa building, has building-id "{bid}", has physical-isolation $pi;
get $pi;
"""

TQL_QUERY_PRIORITY_TARGETS = """
match
  $e isa fire-event, has event-id "{eid}";
  $b isa building;
  $p isa person, has cognitive-vulnerability true;
  (event: $e, site: $b) isa incident;
  (resident: $p, dwelling: $b) isa residence;
  $p has name $name, has age $age;
get $p, $name, $age;
sort $age desc;
"""


class TypeDBClient:
    """
    TypeDB 실제 연결 클라이언트.
    전제: localhost:1729에 TypeDB Core 서버와 'patos' DB 존재.
    """

    def __init__(self, dataset: dict):
        self.dataset   = dataset
        self._driver   = None
        self.mode      = "typedb"  # 전제: 연결 성공

        if TYPEDB_AVAILABLE:
            try:
                self._driver = TypeDB.core_driver(TYPEDB_URI)
                self._ensure_database()
                self._load_dataset(dataset)
                print(f"[TypeDB] 연결 완료: {TYPEDB_URI} / DB: {TYPEDB_DB}")
            except Exception as e:
                print(f"[TypeDB] 연결 실패 → MockDB 자동 폴백: {e}")
                self._driver = None
                self.mode = "mock"
        else:
            print("[TypeDB] typedb-driver 미설치 → MockDB 자동 폴백")
            self.mode = "mock"

    # ── 데이터베이스 초기화 ──────────────────────────────────────────────────

    def _ensure_database(self):
        dbs = self._driver.databases.all()
        db_names = [db.name for db in dbs]
        if TYPEDB_DB not in db_names:
            self._driver.databases.create(TYPEDB_DB)
            print(f"[TypeDB] DB '{TYPEDB_DB}' 생성")
            self._define_schema()

    def _define_schema(self):
        with self._driver.session(TYPEDB_DB, SessionType.SCHEMA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                tx.query.define(TQL_INIT_SCHEMA)
                tx.commit()
        print("[TypeDB] 스키마 정의 완료")

    def _load_dataset(self, dataset: dict):
        residents  = dataset.get("residents", [])
        buildings  = dataset.get("buildings", [])

        with self._driver.session(TYPEDB_DB, SessionType.DATA) as session:
            # 주민 삽입
            for r in residents:
                conds = r.get("conditions", [])
                cond_attrs = "".join(
                    f',\n  has chronic-condition "{c}"' for c in conds
                )
                tql = TQL_INSERT_PERSON.format(
                    pid=r["person_id"], name=r["name"], age=r["age"],
                    phone=r.get("phone","010-0000-0000"),
                    lives_alone=str(r.get("lives_alone",False)).lower(),
                    hearing=str("난청" in conds).lower(),
                    dementia=str("치매" in conds).lower(),
                    cond_attrs=cond_attrs,
                )
                with session.transaction(TransactionType.WRITE) as tx:
                    tx.query.insert(tql)
                    tx.commit()

            # 건물 삽입
            for b in buildings:
                tql = TQL_INSERT_BUILDING.format(
                    bid=b["building_id"], address=b["address"],
                    material=b["material"],
                    width=b["access_road_width_m"],
                    detector=str(b.get("has_fire_detector",False)).lower(),
                )
                with session.transaction(TransactionType.WRITE) as tx:
                    tx.query.insert(tql)
                    tx.commit()

            # 거주 관계 삽입
            for r in residents:
                if r.get("building_id"):
                    tql = TQL_INSERT_RESIDENCE.format(
                        pid=r["person_id"], bid=r["building_id"]
                    )
                    with session.transaction(TransactionType.WRITE) as tx:
                        tx.query.insert(tql)
                        tx.commit()

        print(f"[TypeDB] 데이터 적재 완료: 주민 {len(residents)}명, 건물 {len(buildings)}동")

    # ── 추론 규칙 실행 ───────────────────────────────────────────────────────

    def query_cognitive_vulnerability(self, person_id: str) -> bool:
        if self.mode == "typedb" and self._driver:
            return self._tql_cog(person_id)
        return self._mock_cog(person_id)

    def query_physical_isolation(self, building_id: str) -> bool:
        if self.mode == "typedb" and self._driver:
            return self._tql_iso(building_id)
        return self._mock_iso(building_id)

    def _tql_cog(self, person_id: str) -> bool:
        try:
            with self._driver.session(TYPEDB_DB, SessionType.DATA) as session:
                with session.transaction(TransactionType.READ) as tx:
                    results = list(tx.query.get(
                        TQL_QUERY_COG_VULN.format(pid=person_id)
                    ))
                    if results:
                        return results[0].get("cv").as_attribute().get_value()
            return False
        except Exception:
            return self._mock_cog(person_id)

    def _tql_iso(self, building_id: str) -> bool:
        try:
            with self._driver.session(TYPEDB_DB, SessionType.DATA) as session:
                with session.transaction(TransactionType.READ) as tx:
                    results = list(tx.query.get(
                        TQL_QUERY_PHYS_ISOL.format(bid=building_id)
                    ))
                    if results:
                        return results[0].get("pi").as_attribute().get_value()
            return False
        except Exception:
            return self._mock_iso(building_id)

    def _mock_cog(self, person_id: str) -> bool:
        persons = {r["person_id"]: r for r in self.dataset.get("residents", [])}
        p = persons.get(person_id, {})
        conds = p.get("conditions", [])
        return p.get("age", 0) >= 80 or "난청" in conds or "치매" in conds

    def _mock_iso(self, building_id: str) -> bool:
        buildings = {b["building_id"]: b for b in self.dataset.get("buildings", [])}
        b = buildings.get(building_id, {})
        return (b.get("access_road_width_m", 5.0) < 3.0 or
                b.get("material","") in ["샌드위치 패널","비닐하우스","경량 목구조"])

    def insert_fire_event(self, scenario: dict) -> bool:
        if self.mode != "typedb" or not self._driver:
            return False
        try:
            tql = TQL_INSERT_FIRE_EVENT.format(
                eid=scenario["scenario_id"],
                call=scenario.get("call_content","")[:200].replace('"',"'"),
                severity=scenario.get("severity","UNKNOWN"),
                origin=scenario.get("fire_origin","미상"),
            )
            with self._driver.session(TYPEDB_DB, SessionType.DATA) as session:
                with session.transaction(TransactionType.WRITE) as tx:
                    tx.query.insert(tql)
                    tx.commit()
            return True
        except Exception as e:
            print(f"[TypeDB] 화재 이벤트 저장 실패: {e}")
            return False

    def close(self):
        if self._driver:
            try: self._driver.close()
            except: pass

    @property
    def is_live(self) -> bool:
        return self.mode == "typedb"

    @property
    def status(self) -> dict:
        return {
            "mode":      self.mode,
            "is_live":   self.is_live,
            "server":    TYPEDB_URI if self.is_live else "N/A (MockDB)",
            "database":  TYPEDB_DB  if self.is_live else "N/A",
            "driver":    "typedb-driver" if TYPEDB_AVAILABLE else "미설치",
        }
