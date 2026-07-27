"""Safe, provenance-preserving retrieval for the KSP Intelligence Copilot.

Models never execute SQL or establish case facts. This module first produces an
allow-listed query plan, executes parameterized SQL, then optionally lets a model
write a non-authoritative narrative around immutable database facts.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Optional
from backend import vector_search

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "ksp_crime.db"

BASE_SELECT = """
SELECT c.CaseMasterID,c.CrimeNo,c.CaseNo,c.CrimeRegisteredDate,c.IncidentFromDate,c.IncidentToDate,
 c.latitude,c.longitude,c.BriefFacts,d.DistrictName,u.UnitName AS StationName,
 sh.CrimeHeadName AS CrimeType,st.CaseStatusName,
 COALESCE((SELECT RegistrationNo FROM CaseVehicle cv WHERE cv.CaseMasterID=c.CaseMasterID LIMIT 1),'') AS Vehicle,
 COALESCE((SELECT EvidenceLabel FROM Evidence e WHERE e.CaseMasterID=c.CaseMasterID LIMIT 1),'') AS EvidenceID
FROM CaseMaster c
JOIN Unit u ON u.UnitID=c.PoliceStationID
JOIN District d ON d.DistrictID=u.DistrictID
JOIN CrimeSubHead sh ON sh.CrimeSubHeadID=c.CrimeMinorHeadID
JOIN CaseStatusMaster st ON st.CaseStatusID=c.CaseStatusID
"""

def connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def normalize_query(query: str) -> str:
    """Normalise only well-known spoken/typing variants, retaining original text."""
    q = query.lower().strip()
    aliases = {
        r"\bbulgary\b": "burglary", r"\bburglery\b": "burglary",
        r"\bbangalore\b": "bengaluru", r"\bmangalore\b": "mangaluru",
        r"\bmysore\b": "mysuru", r"\bhubli\b": "hubballi",
    }
    for pattern, replacement in aliases.items():
        q = re.sub(pattern, replacement, q)
    return re.sub(r"\s+", " ", q)

def needs_investigative_retrieval(query: str, plan: dict) -> bool:
    """Route only explicit case-data requests to retrieval; never use vectors as a fallback chat engine."""
    if plan["filters"]:
        return True
    q = plan["normalized_query"]
    action = r"\b(show|find|search|list|retrieve|display|compare|trace|map|how many|number of|count|total|give)\b"
    subject = r"\b(fir|firs|case|cases|crime|crimes|evidence|suspect|vehicle|district|districts|timeline|graph|incident|incidents)\b"
    return bool(re.search(action, q) and re.search(subject, q))

def conversational_response(query: str) -> dict:
    """Use the configured model for chat, while making the no-retrieval boundary explicit."""
    from backend import bedrock
    q = normalize_query(query)
    try:
        answer = bedrock.conversation(query)
        provider = "Amazon Bedrock conversational response"
        status = "model conversation; no database query"
    except Exception as exc:
        answer = "Conversational mode is unavailable because the Bedrock model is not currently reachable. No crime-record search was performed."
        provider = f"Conversation unavailable: {type(exc).__name__}"
        status = "no database query"
    return {
        "answer": answer, "confidence": 0, "confidence_label": "Not database-derived",
        "reasoning": [{"label": "Conversational request routed away from crime-record retrieval", "status": status, "weight": 0}],
        "citations": [], "provider": provider, "results": [], "total_matches": 0,
        "query_plan": {"original_query": query, "normalized_query": q, "intent": "conversation", "filters": [], "sql_template": "No database query", "scope_warning": None},
        "rag_context": [], "vector_search": {"enabled": False, "reason": "No record retrieval for conversational input"}, "aggregation": None,
    }

def sql_plan(query: str) -> dict:
    """Create a bounded query plan. No generated SQL reaches this layer."""
    q = normalize_query(query)
    filters, params, applied = [], [], []
    types = {
        "burglary": "Burglary", "theft": "Theft", "robbery": "Robbery",
        "investment": "Investment Fraud", "fraud": "Investment Fraud", "cyber": "Investment Fraud",
        "missing": "Missing Person", "assault": "Assault", "udr": "UDR",
    }
    for token, crime_type in types.items():
        if re.search(rf"\b{re.escape(token)}\b", q):
            filters.append("sh.CrimeHeadName = ?"); params.append(crime_type)
            applied.append({"field": "CrimeType", "operator": "=", "value": crime_type, "source": token})
            break
    districts = {
        "bengaluru": "Bengaluru Urban", "mysuru": "Mysuru", "mangaluru": "Dakshina Kannada",
        "udupi": "Udupi", "belagavi": "Belagavi", "hubballi": "Hubballi-Dharwad",
        "kalaburagi": "Kalaburagi", "shivamogga": "Shivamogga", "tumakuru": "Tumakuru", "vijayapura": "Vijayapura",
    }
    for token, district in districts.items():
        if re.search(rf"\b{re.escape(token)}\b", q):
            filters.append("d.DistrictName = ?"); params.append(district)
            applied.append({"field": "DistrictName", "operator": "=", "value": district, "source": token})
            break
    if "swift" in q:
        filters.append("EXISTS (SELECT 1 FROM CaseVehicle cv WHERE cv.CaseMasterID=c.CaseMasterID AND cv.VehicleMake LIKE ?)")
        params.append("%Swift%")
        applied.append({"field": "VehicleMake", "operator": "LIKE", "value": "%Swift%", "source": "swift"})
    crime_no = re.search(r"\b[1348]\d{17}\b", q)
    if crime_no:
        filters.append("c.CrimeNo = ?"); params.append(crime_no.group(0))
        applied.append({"field": "CrimeNo", "operator": "=", "value": crime_no.group(0), "source": "case ID"})
    is_count = bool(re.search(r"\b(how many|number of|count|total)\b", q))
    by_district = bool(re.search(r"\b(by|per|each) district\b|\bdistrict[- ]?wise\b", q))
    intent = "group_count" if is_count and by_district else "count" if is_count else "search"
    where = " WHERE " + " AND ".join(filters) if filters else ""
    return {
        "original_query": query, "normalized_query": q, "intent": intent,
        "filters": applied, "where": where, "params": params,
        "sql_template": "SELECT DistrictName, COUNT(*) FROM CaseMaster + approved joins GROUP BY DistrictName" if intent == "group_count" else "SELECT COUNT(*) FROM CaseMaster + approved joins" if intent == "count" else "SELECT CaseMaster records + approved joins",
        "scope_warning": None if applied else "No supported structured filter was detected; results cover the whole generated dataset.",
    }

def run_plan(plan: dict, limit: int = 25) -> tuple[list[dict], int]:
    with connection() as con:
        count_sql = "SELECT COUNT(*) " + BASE_SELECT[BASE_SELECT.rindex("\nFROM CaseMaster"):] + plan["where"]
        total = con.execute(count_sql, plan["params"]).fetchone()[0]
        if plan["intent"] == "count":
            return [], total
        if plan["intent"] == "group_count":
            grouped_sql = "SELECT d.DistrictName, COUNT(*) AS FIRCount " + BASE_SELECT[BASE_SELECT.rindex("\nFROM CaseMaster"):] + plan["where"] + " GROUP BY d.DistrictName ORDER BY FIRCount DESC, d.DistrictName"
            rows = [dict(row) for row in con.execute(grouped_sql, plan["params"])]
            return rows, total
        sql = BASE_SELECT + plan["where"] + " ORDER BY c.CrimeRegisteredDate DESC LIMIT ?"
        rows = [dict(row) for row in con.execute(sql, [*plan["params"], min(limit, 500)])]
    return rows, total

def safe_sql_search(query: str, limit: int = 25) -> list[dict]:
    return run_plan(sql_plan(query), limit)[0]

def records_by_crime_numbers(crime_numbers: list[str]) -> list[dict]:
    if not crime_numbers:
        return []
    placeholders = ",".join("?" for _ in crime_numbers)
    with connection() as con:
        unordered = [dict(row) for row in con.execute(BASE_SELECT + f" WHERE c.CrimeNo IN ({placeholders})", crime_numbers)]
    by_id = {row["CrimeNo"]: row for row in unordered}
    return [by_id[number] for number in crime_numbers if number in by_id]

def rag_search(query: str, limit: int = 12) -> list[dict]:
    """FTS is a candidate finder only; the SQL plan remains the source of truth."""
    plan = sql_plan(query)
    if plan["filters"]:
        return run_plan(plan, limit)[0]
    tokens = [token for token in re.findall(r"[a-zA-Z0-9]+", plan["normalized_query"]) if len(token) > 2]
    if not tokens:
        return []
    with connection() as con:
        try:
            return [dict(row) for row in con.execute(
                "SELECT CrimeNo,DistrictName,StationName,CrimeType,BriefFacts,EvidenceText,rank FROM CaseSearch WHERE CaseSearch MATCH ? ORDER BY rank LIMIT ?",
                (" OR ".join(tokens), min(limit, 50)),
            )]
        except sqlite3.OperationalError:
            return []

def case_detail(crime_no: str):
    with connection() as con:
        record = con.execute(BASE_SELECT + " WHERE c.CrimeNo=?", (crime_no,)).fetchone()
        if not record:
            return None
        row = dict(record); case_id = row["CaseMasterID"]
        row["evidence"] = [dict(x) for x in con.execute("SELECT EvidenceID,EvidenceType,EvidenceLabel,EvidenceText,Confidence,CollectedAt FROM Evidence WHERE CaseMasterID=? ORDER BY CollectedAt", (case_id,))]
        row["vehicles"] = [dict(x) for x in con.execute("SELECT RegistrationNo,VehicleMake,VehicleColor,RelationshipType,Confidence FROM CaseVehicle WHERE CaseMasterID=?", (case_id,))]
        row["accused"] = [dict(x) for x in con.execute("SELECT AccusedName,PersonID,AgeYear,GenderID FROM Accused WHERE CaseMasterID=?", (case_id,))]
        row["witnesses"] = [dict(x) for x in con.execute("SELECT WitnessID,WitnessName,StatementText,RecordedAt FROM WitnessStatement WHERE CaseMasterID=? ORDER BY RecordedAt", (case_id,))]
        row["arrests"] = [dict(x) for x in con.execute("SELECT a.ArrestSurrenderDate,a.ArrestSurrenderTypeID,a.IsAccused,ac.AccusedName,u.UnitName FROM ArrestSurrender a LEFT JOIN Accused ac ON ac.AccusedMasterID=a.AccusedMasterID LEFT JOIN Unit u ON u.UnitID=a.PoliceStationID WHERE a.CaseMasterID=? ORDER BY a.ArrestSurrenderDate", (case_id,))]
        row["chargesheet"] = [dict(x) for x in con.execute("SELECT csdate,cstype FROM ChargesheetDetails WHERE CaseMasterID=? ORDER BY csdate DESC", (case_id,))]
        court = con.execute("SELECT co.CourtName FROM CaseMaster c JOIN Court co ON co.CourtID=c.CourtID WHERE c.CaseMasterID=?", (case_id,)).fetchone()
        row["CourtName"] = court["CourtName"] if court else "Not assigned"
        return row

def timeline(crime_no: str):
    detail = case_detail(crime_no)
    if not detail:
        return None
    events = [{"stage":"Incident", "date":detail["IncidentFromDate"], "title":detail["CrimeType"], "description":detail["BriefFacts"], "source":"CaseMaster"}]
    events += [{"stage":"Witness", "date":x["RecordedAt"], "title":x["WitnessName"], "description":x["StatementText"], "source":f"WitnessStatement #{x['WitnessID']}"} for x in detail["witnesses"]]
    events += [{"stage":"Evidence", "date":x["CollectedAt"], "title":f"{x['EvidenceType']} · {x['EvidenceLabel']}", "description":x["EvidenceText"], "source":f"Evidence #{x['EvidenceID']}"} for x in detail["evidence"]]
    events += [{"stage":"Arrest", "date":x["ArrestSurrenderDate"], "title":x["AccusedName"] or "Arrest event", "description":f"Recorded by {x['UnitName'] or 'assigned station'}.", "source":"ArrestSurrender"} for x in detail["arrests"]]
    status_date = detail["chargesheet"][0]["csdate"] if detail["chargesheet"] else detail["CrimeRegisteredDate"]
    events.append({"stage":"Court Status", "date":status_date, "title":detail["CaseStatusName"], "description":f"Court: {detail['CourtName']}.", "source":"CaseMaster / Court"})
    return {"case":detail, "events":events}

def graph(crime_no: str):
    detail = case_detail(crime_no)
    if not detail:
        return None
    with connection() as con:
        cid = detail["CaseMasterID"]
        nodes = [{"id":crime_no, "label":crime_no, "type":"case", "confidence":1, "data":{"district":detail["DistrictName"], "type":detail["CrimeType"], "status":detail["CaseStatusName"], "brief":detail["BriefFacts"]}}]
        edges = []
        for vehicle in detail["vehicles"]:
            vehicle_id = "vehicle:" + vehicle["RegistrationNo"]
            nodes.append({"id":vehicle_id, "label":vehicle["RegistrationNo"], "type":"vehicle", "confidence":vehicle["Confidence"], "data":vehicle})
            edges.append({"source":crime_no,"target":vehicle_id,"label":"observed in"})
            linked = con.execute("SELECT c.CrimeNo,sh.CrimeHeadName,d.DistrictName FROM CaseVehicle cv JOIN CaseMaster c ON c.CaseMasterID=cv.CaseMasterID JOIN CrimeSubHead sh ON sh.CrimeSubHeadID=c.CrimeMinorHeadID JOIN Unit u ON u.UnitID=c.PoliceStationID JOIN District d ON d.DistrictID=u.DistrictID WHERE cv.RegistrationNo=? AND cv.CaseMasterID<>? LIMIT 20", (vehicle["RegistrationNo"],cid)).fetchall()
            for item in linked:
                nodes.append({"id":item["CrimeNo"],"label":item["CrimeNo"],"type":"case","confidence":.88,"data":{"district":item["DistrictName"],"type":item["CrimeHeadName"],"relationship":"Shared vehicle registration"}})
                edges.append({"source":vehicle_id,"target":item["CrimeNo"],"label":"same vehicle"})
        for accused in detail["accused"]:
            accused_id = "person:" + accused["AccusedName"]
            nodes.append({"id":accused_id,"label":accused["AccusedName"],"type":"person","confidence":.8,"data":accused})
            edges.append({"source":crime_no,"target":accused_id,"label":"accused"})
        for evidence in detail["evidence"][:3]:
            evidence_id = evidence["EvidenceLabel"]
            nodes.append({"id":evidence_id,"label":evidence_id,"type":"evidence","confidence":evidence["Confidence"],"data":evidence})
            edges.append({"source":crime_no,"target":evidence_id,"label":evidence["EvidenceType"]})
    unique = {node["id"]:node for node in nodes}
    return {"nodes":list(unique.values()), "edges":edges}

def all_records(query: str, limit: int = 500):
    plan = sql_plan(query)
    cases, total = run_plan({**plan, "intent":"search"}, limit)
    ids = [x["CaseMasterID"] for x in cases]
    if not ids:
        return {"plan":public_plan(plan), "total_matches":total, "tables":{"CaseMaster":[],"Evidence":[],"Accused":[],"WitnessStatement":[],"ArrestSurrender":[]}}
    placeholders = ",".join("?" for _ in ids)
    with connection() as con:
        tables = {
            "CaseMaster":cases,
            "Evidence":[dict(x) for x in con.execute(f"SELECT EvidenceID,CaseMasterID,EvidenceType,EvidenceLabel,EvidenceText,Confidence,CollectedAt FROM Evidence WHERE CaseMasterID IN ({placeholders}) ORDER BY CollectedAt DESC", ids)],
            "Accused":[dict(x) for x in con.execute(f"SELECT AccusedMasterID,CaseMasterID,AccusedName,PersonID,AgeYear,GenderID FROM Accused WHERE CaseMasterID IN ({placeholders})", ids)],
            "WitnessStatement":[dict(x) for x in con.execute(f"SELECT WitnessID,CaseMasterID,WitnessName,StatementText,RecordedAt FROM WitnessStatement WHERE CaseMasterID IN ({placeholders})", ids)],
            "ArrestSurrender":[dict(x) for x in con.execute(f"SELECT ArrestSurrenderID,CaseMasterID,ArrestSurrenderDate,ArrestSurrenderTypeID,IsAccused FROM ArrestSurrender WHERE CaseMasterID IN ({placeholders})", ids)],
        }
    return {"plan":public_plan(plan), "total_matches":total, "tables":tables}

def analytics():
    with connection() as con:
        total=con.execute("SELECT count(*) FROM CaseMaster").fetchone()[0]
        by_type=[dict(x) for x in con.execute("SELECT sh.CrimeHeadName AS label,count(*) AS value FROM CaseMaster c JOIN CrimeSubHead sh ON sh.CrimeSubHeadID=c.CrimeMinorHeadID GROUP BY 1 ORDER BY 2 DESC")]
        by_district=[dict(x) for x in con.execute("SELECT d.DistrictName AS label,count(*) AS value FROM CaseMaster c JOIN Unit u ON u.UnitID=c.PoliceStationID JOIN District d ON d.DistrictID=u.DistrictID GROUP BY 1 ORDER BY 2 DESC")]
        return {"total_cases":total,"by_type":by_type,"by_district":by_district}

def map_cases(crime_type=None,district=None,status=None,limit=700):
    where=[];params=[]
    if crime_type:where.append("sh.CrimeHeadName=?");params.append(crime_type)
    if district:where.append("d.DistrictName=?");params.append(district)
    if status:where.append("st.CaseStatusName=?");params.append(status)
    sql=BASE_SELECT+(" WHERE "+" AND ".join(where) if where else "")+" ORDER BY c.CrimeRegisteredDate DESC LIMIT ?";params.append(min(limit,1000))
    with connection() as con:return [dict(x) for x in con.execute(sql,params)]

def public_plan(plan: dict) -> dict:
    return {key:plan[key] for key in ("original_query","normalized_query","intent","filters","sql_template","scope_warning")}

def deterministic_response(query: str, plan: dict, rows: list[dict], total: int, rag_rows: list[dict], vector: Optional[dict] = None) -> dict:
    scope = ", ".join(f"{x['field']} {x['operator']} {x['value']}" for x in plan["filters"]) or "no structured filter"
    citations=[{"crime_no":row["CrimeNo"],"title":row.get("CrimeType","Case record"),"source":"CaseMaster + linked evidence"} for row in rows[:6] if row.get("CrimeNo")]
    reasoning=[{"label":f"SQL agent applied: {scope}","status":"parameterized query","weight":0},{"label":"FIR count and citations are database-derived","status":"not model-derived","weight":0}]
    aggregation = None
    if plan["intent"] == "count":
        answer=f"The generated database contains {total:,} matching FIR record{'s' if total != 1 else ''}."
        label="Complete database count"
        confidence=100
    elif plan["intent"] == "group_count":
        crime_type = next((item["value"] for item in plan["filters"] if item["field"] == "CrimeType"), "FIR")
        answer=f"The generated database contains {total:,} {crime_type} FIR records across {len(rows):,} districts. The district-wise totals are shown below."
        label="Complete district aggregation"
        confidence=100
        aggregation = {"title": f"{crime_type} FIRs by district", "columns": ["District", "FIR count"], "rows": [{"District": row["DistrictName"], "FIR count": row["FIRCount"]} for row in rows], "source": "CaseMaster grouped by DistrictName"}
        reasoning.insert(1, {"label": "District totals are grouped by DistrictName in the approved SQL query", "status": "database aggregation", "weight": 0})
    elif total == 0:
        answer="No FIR records match the approved filters in the generated database. No unrelated records were substituted."
        label="No matching records"
        confidence=0
    else:
        answer=f"I found {total:,} matching FIR records. Showing the first {len(rows):,} most recently registered records; choose Show all results to inspect linked tables."
        label="Retrieved record coverage"
        confidence=min(100, round(len(rows) / total * 100))
    return {"answer":answer,"confidence":confidence,"confidence_label":label,"reasoning":reasoning,"citations":citations,"provider":"SQL agent + deterministic evidence engine","results":rows[:15],"total_matches":total,"query_plan":public_plan(plan),"rag_context":rag_rows[:5],"vector_search":vector or vector_search.status(),"aggregation":aggregation}

def bedrock_narrative(query: str, response: dict) -> dict:
    """Bedrock can add a non-factual narrative only; it cannot overwrite facts."""
    from backend import bedrock
    if not bedrock.configured() or response["query_plan"]["intent"] != "search":
        return response
    facts={"answer":response["answer"],"total_matches":response["total_matches"],"filters":response["query_plan"]["filters"],"citations":response["citations"]}
    prompt=("Write one neutral, non-factual investigation note of at most 45 words. Do not state any count, confidence, identity, guilt, or fact not in this immutable evidence bundle. Return plain text only. Bundle: "+json.dumps(facts))
    try:
        note=bedrock.narrative(prompt)
        if note:response["narrative_note"]=note;response["provider"]="SQL agent + deterministic evidence engine + Amazon Bedrock narrative"
    except Exception as exc:
        response["provider"]=f"SQL agent + deterministic evidence engine (Bedrock unavailable: {type(exc).__name__})"
    return response

def assistant(query: str):
    plan = sql_plan(query)
    if not needs_investigative_retrieval(query, plan):
        return conversational_response(query)
    rows,total=run_plan(plan,100 if plan["intent"] == "search" else 0); rag_rows=rag_search(query) if plan["intent"] == "search" else []
    vector = vector_search.status()
    # Open-ended questions may use vectors to locate candidate FIRs. Structured
    # SQL filters and all counts remain untouched by vector similarity.
    if plan["intent"] == "search" and not plan["filters"]:
        numbers, vector = vector_search.semantic_candidate_numbers(query)
        if numbers:
            rows = records_by_crime_numbers(numbers)
            total = len(rows)
            plan = {**plan, "scope_warning": "Semantic candidates are shown; inspect cited FIR records before relying on them."}
    return bedrock_narrative(query, deterministic_response(query,plan,rows,total,rag_rows,vector))
