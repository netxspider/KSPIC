"""Create a deterministic, relationally valid Karnataka Police demo database.

The core table and column names follow Police_FIR_ER_Diagram.pdf.  Evidence,
vehicle, phone and witness tables are explicitly marked as intelligence-layer
extensions; they do not replace or alter the FIR source schema.
"""
from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "ksp_crime.db"
RNG = random.Random(20260726)

DISTRICTS = [
    (443, "Bengaluru Urban", 12.9716, 77.5946), (442, "Mysuru", 12.2958, 76.6394),
    (441, "Dakshina Kannada", 12.9141, 74.8560), (440, "Belagavi", 15.8497, 74.4977),
    (439, "Hubballi-Dharwad", 15.3647, 75.1240), (438, "Kalaburagi", 17.3297, 76.8343),
    (437, "Shivamogga", 13.9299, 75.5681), (436, "Udupi", 13.3409, 74.7421),
    (435, "Tumakuru", 13.3379, 77.1173), (434, "Vijayapura", 16.8302, 75.7100),
]
STATION_SUFFIXES = ["Central", "East", "West", "North", "South", "Rural"]
FIRST = ["Arjun", "Priya", "Kiran", "Meera", "Ravi", "Nandini", "Faisal", "Divya", "Manoj", "Asha", "Rahul", "Shreya", "Naveen", "Farah", "Vikram", "Lakshmi"]
LAST = ["Rao", "Sheikh", "Gowda", "Patil", "Kumar", "Bhat", "Naik", "Reddy", "Iyer", "Khan", "Shetty", "Das", "Jain", "Poojary"]
CRIME_TYPES = [
    (1, 1, "Property Crime", "Burglary", "IPC", "454", "Theft", "A house burglary involving forced entry"),
    (1, 1, "Property Crime", "Theft", "IPC", "379", "Theft", "A reported theft of personal property"),
    (1, 1, "Property Crime", "Robbery", "IPC", "392", "Robbery", "A robbery reported by the complainant"),
    (1, 2, "Cyber Crime", "Investment Fraud", "IT", "66D", "Cyber Fraud", "An online investment fraud using a deceptive application"),
    (1, 2, "Cyber Crime", "Identity Fraud", "IT", "66C", "Cyber Fraud", "A digital identity misuse complaint"),
    (1, 3, "Crimes Against Body", "Assault", "IPC", "323", "Assault", "An assault reported after a local dispute"),
    (1, 3, "Crimes Against Body", "Missing Person", "IPC", "365", "Missing Person", "A missing-person report requiring investigation"),
    (3, 2, "Unnatural Death", "UDR", "CrPC", "174", "Unnatural Death", "An unnatural death report under enquiry"),
]

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE State (StateID INTEGER PRIMARY KEY, StateName TEXT NOT NULL, NationalityID INTEGER, Active INTEGER NOT NULL);
CREATE TABLE District (DistrictID INTEGER PRIMARY KEY, DistrictName TEXT NOT NULL, StateID INTEGER NOT NULL REFERENCES State(StateID), Active INTEGER NOT NULL);
CREATE TABLE UnitType (UnitTypeID INTEGER PRIMARY KEY, UnitTypeName TEXT NOT NULL, CityDistState TEXT, Hierarchy INTEGER, Active INTEGER NOT NULL);
CREATE TABLE Unit (UnitID INTEGER PRIMARY KEY, UnitName TEXT NOT NULL, TypeID INTEGER NOT NULL REFERENCES UnitType(UnitTypeID), ParentUnit INTEGER, NationalityID INTEGER, StateID INTEGER NOT NULL REFERENCES State(StateID), DistrictID INTEGER NOT NULL REFERENCES District(DistrictID), Active INTEGER NOT NULL);
CREATE TABLE Rank (RankID INTEGER PRIMARY KEY, RankName TEXT NOT NULL, Hierarchy INTEGER, Active INTEGER NOT NULL);
CREATE TABLE Designation (DesignationID INTEGER PRIMARY KEY, DesignationName TEXT NOT NULL, Active INTEGER NOT NULL, SortOrder INTEGER);
CREATE TABLE Employee (EmployeeID INTEGER PRIMARY KEY, DistrictID INTEGER NOT NULL REFERENCES District(DistrictID), UnitID INTEGER NOT NULL REFERENCES Unit(UnitID), RankID INTEGER NOT NULL REFERENCES Rank(RankID), DesignationID INTEGER NOT NULL REFERENCES Designation(DesignationID), KGID TEXT UNIQUE NOT NULL, FirstName TEXT NOT NULL, EmployeeDOB DATE, GenderID INTEGER, BloodGroupID INTEGER, PhysicallyChallenged INTEGER, AppointmentDate DATE);
CREATE TABLE CaseCategory (CaseCategoryID INTEGER PRIMARY KEY, LookupValue TEXT NOT NULL);
CREATE TABLE GravityOffence (GravityOffenceID INTEGER PRIMARY KEY, LookupValue TEXT NOT NULL);
CREATE TABLE CrimeHead (CrimeHeadID INTEGER PRIMARY KEY, CrimeGroupName TEXT NOT NULL, Active INTEGER NOT NULL);
CREATE TABLE CrimeSubHead (CrimeSubHeadID INTEGER PRIMARY KEY, CrimeHeadID INTEGER NOT NULL REFERENCES CrimeHead(CrimeHeadID), CrimeHeadName TEXT NOT NULL, SeqID INTEGER);
CREATE TABLE CaseStatusMaster (CaseStatusID INTEGER PRIMARY KEY, CaseStatusName TEXT NOT NULL);
CREATE TABLE Court (CourtID INTEGER PRIMARY KEY, CourtName TEXT NOT NULL, DistrictID INTEGER NOT NULL REFERENCES District(DistrictID), StateID INTEGER NOT NULL REFERENCES State(StateID), Active INTEGER NOT NULL);
CREATE TABLE OccupationMaster (OccupationID INTEGER PRIMARY KEY, OccupationName TEXT NOT NULL);
CREATE TABLE ReligionMaster (ReligionID INTEGER PRIMARY KEY, ReligionName TEXT NOT NULL);
CREATE TABLE CasteMaster (caste_master_id INTEGER PRIMARY KEY, caste_master_name TEXT NOT NULL);
CREATE TABLE Act (ActCode TEXT PRIMARY KEY, ActDescription TEXT NOT NULL, ShortName TEXT NOT NULL, Active INTEGER NOT NULL);
CREATE TABLE Section (ActCode TEXT NOT NULL REFERENCES Act(ActCode), SectionCode TEXT NOT NULL, SectionDescription TEXT NOT NULL, Active INTEGER NOT NULL, PRIMARY KEY(ActCode, SectionCode));
CREATE TABLE CrimeHeadActSection (CrimeHeadID INTEGER NOT NULL REFERENCES CrimeHead(CrimeHeadID), ActCode TEXT NOT NULL REFERENCES Act(ActCode), SectionCode TEXT NOT NULL, PRIMARY KEY(CrimeHeadID, ActCode, SectionCode));
CREATE TABLE CaseMaster (CaseMasterID INTEGER PRIMARY KEY, CrimeNo TEXT UNIQUE NOT NULL, CaseNo TEXT NOT NULL, CrimeRegisteredDate DATE NOT NULL, PolicePersonID INTEGER NOT NULL REFERENCES Employee(EmployeeID), PoliceStationID INTEGER NOT NULL REFERENCES Unit(UnitID), CaseCategoryID INTEGER NOT NULL REFERENCES CaseCategory(CaseCategoryID), GravityOffenceID INTEGER NOT NULL REFERENCES GravityOffence(GravityOffenceID), CrimeMajorHeadID INTEGER NOT NULL REFERENCES CrimeHead(CrimeHeadID), CrimeMinorHeadID INTEGER NOT NULL REFERENCES CrimeSubHead(CrimeSubHeadID), CaseStatusID INTEGER NOT NULL REFERENCES CaseStatusMaster(CaseStatusID), CourtID INTEGER NOT NULL REFERENCES Court(CourtID), IncidentFromDate DATETIME NOT NULL, IncidentToDate DATETIME NOT NULL, InfoReceivedPSDate DATETIME NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, BriefFacts TEXT NOT NULL);
CREATE TABLE ComplainantDetails (ComplainantID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), ComplainantName TEXT NOT NULL, AgeYear INTEGER, OccupationID INTEGER REFERENCES OccupationMaster(OccupationID), ReligionID INTEGER REFERENCES ReligionMaster(ReligionID), CasteID INTEGER REFERENCES CasteMaster(caste_master_id), GenderID INTEGER);
CREATE TABLE Victim (VictimMasterID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), VictimName TEXT NOT NULL, AgeYear INTEGER, GenderID INTEGER, VictimPolice TEXT);
CREATE TABLE Accused (AccusedMasterID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), AccusedName TEXT NOT NULL, AgeYear INTEGER, GenderID INTEGER, PersonID TEXT NOT NULL);
CREATE TABLE ArrestSurrender (ArrestSurrenderID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), ArrestSurrenderTypeID INTEGER, ArrestSurrenderDate DATE, ArrestSurrenderStateId INTEGER REFERENCES State(StateID), ArrestSurrenderDistrictId INTEGER REFERENCES District(DistrictID), PoliceStationID INTEGER REFERENCES Unit(UnitID), IOID INTEGER REFERENCES Employee(EmployeeID), CourtID INTEGER REFERENCES Court(CourtID), AccusedMasterID INTEGER REFERENCES Accused(AccusedMasterID), IsAccused INTEGER, IsComplainantAccused INTEGER);
CREATE TABLE ActSectionAssociation (CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), ActID TEXT NOT NULL REFERENCES Act(ActCode), SectionID TEXT NOT NULL, ActOrderID INTEGER, SectionOrderID INTEGER, PRIMARY KEY(CaseMasterID, ActID, SectionID));
CREATE TABLE ChargesheetDetails (CSID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), csdate DATETIME, cstype TEXT, PolicePersonID INTEGER REFERENCES Employee(EmployeeID));
CREATE TABLE inv_arrestsurrenderaccused (ArrestSurrenderID INTEGER NOT NULL REFERENCES ArrestSurrender(ArrestSurrenderID), AccusedMasterID INTEGER NOT NULL REFERENCES Accused(AccusedMasterID), PRIMARY KEY(ArrestSurrenderID, AccusedMasterID));
-- Intelligence extensions for retrieval and graph visualisation.
CREATE TABLE Evidence (EvidenceID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), EvidenceType TEXT NOT NULL, EvidenceLabel TEXT NOT NULL, EvidenceText TEXT NOT NULL, Confidence REAL NOT NULL, CollectedAt DATETIME NOT NULL);
CREATE TABLE CaseVehicle (CaseVehicleID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), RegistrationNo TEXT NOT NULL, VehicleMake TEXT, VehicleColor TEXT, RelationshipType TEXT NOT NULL, Confidence REAL NOT NULL);
CREATE TABLE CasePhone (CasePhoneID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), PhoneNumber TEXT NOT NULL, RelationshipType TEXT NOT NULL, Confidence REAL NOT NULL);
CREATE TABLE WitnessStatement (WitnessID INTEGER PRIMARY KEY, CaseMasterID INTEGER NOT NULL REFERENCES CaseMaster(CaseMasterID), WitnessName TEXT NOT NULL, StatementText TEXT NOT NULL, RecordedAt DATETIME NOT NULL);
CREATE VIRTUAL TABLE CaseSearch USING fts5(CrimeNo, DistrictName, StationName, CrimeType, BriefFacts, EvidenceText, tokenize='porter unicode61');
CREATE INDEX idx_case_station_date ON CaseMaster(PoliceStationID, CrimeRegisteredDate);
CREATE INDEX idx_case_type_status ON CaseMaster(CrimeMinorHeadID, CaseStatusID);
CREATE INDEX idx_vehicle_registration ON CaseVehicle(RegistrationNo);
CREATE INDEX idx_evidence_case ON Evidence(CaseMasterID);
"""

def name(): return f"{RNG.choice(FIRST)} {RNG.choice(LAST)}"
def iso(dt): return dt.strftime("%Y-%m-%d %H:%M:%S")

def seed_reference(cur):
    cur.execute("INSERT INTO State VALUES (1, 'Karnataka', 1, 1)")
    cur.executemany("INSERT INTO District VALUES (?, ?, 1, 1)", [(d[0], d[1]) for d in DISTRICTS])
    cur.executemany("INSERT INTO UnitType VALUES (?, ?, ?, ?, 1)", [(1, "Police Station", "District", 3), (2, "Commissionerate", "City", 2)])
    unit_rows=[]; station_by_district={}; uid=1
    for did, dname, *_ in DISTRICTS:
        station_by_district[did]=[]
        for suffix in STATION_SUFFIXES:
            unit_rows.append((uid, f"{dname.replace(' Urban','').replace('Hubballi-Dharwad','Hubballi')} {suffix} PS", 1, None, 1, 1, did, 1))
            station_by_district[did].append(uid); uid+=1
    cur.executemany("INSERT INTO Unit VALUES (?, ?, ?, ?, ?, ?, ?, ?)", unit_rows)
    cur.executemany("INSERT INTO Rank VALUES (?, ?, ?, 1)", [(1,"Constable",6),(2,"Sub-Inspector",4),(3,"Inspector",3),(4,"DSP",2)])
    cur.executemany("INSERT INTO Designation VALUES (?, ?, 1, ?)", [(1,"Station House Officer",1),(2,"Investigating Officer",2),(3,"Crime Records Officer",3)])
    employee_rows=[]; eid=1
    for station in unit_rows:
        for _ in range(4):
            employee_rows.append((eid,station[6],station[0],RNG.choice([2,2,3]),RNG.choice([1,2,2,3]),f"KG{20260000+eid}",RNG.choice(FIRST),"1985-07-12",RNG.choice([1,2]),RNG.randint(1,8),0,"2010-06-01"));eid+=1
    cur.executemany("INSERT INTO Employee VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", employee_rows)
    cur.executemany("INSERT INTO CaseCategory VALUES (?, ?)", [(1,"FIR"),(3,"UDR"),(4,"PAR"),(8,"Zero FIR")])
    cur.executemany("INSERT INTO GravityOffence VALUES (?, ?)", [(1,"Non-Heinous"),(2,"Heinous"),(3,"Special & Local Law")])
    heads={}; sub_rows=[]; subid=1
    for _, _, head, sub, *_ in CRIME_TYPES:
        if head not in heads: heads[head]=len(heads)+1
        if not any(row[2]==sub for row in sub_rows): sub_rows.append((subid,heads[head],sub,subid));subid+=1
    cur.executemany("INSERT INTO CrimeHead VALUES (?, ?, 1)", [(v,k) for k,v in heads.items()])
    cur.executemany("INSERT INTO CrimeSubHead VALUES (?, ?, ?, ?)", sub_rows)
    cur.executemany("INSERT INTO CaseStatusMaster VALUES (?, ?)", [(1,"Under Investigation"),(2,"Charge Sheeted"),(3,"Closed"),(4,"Undetected"),(5,"Pending Trial")])
    courts=[]
    for i,(did,dname,*_) in enumerate(DISTRICTS,1): courts.append((i,f"{dname} District Court",did,1,1))
    cur.executemany("INSERT INTO Court VALUES (?, ?, ?, ?, ?)",courts)
    cur.executemany("INSERT INTO OccupationMaster VALUES (?, ?)",list(enumerate(["Student","Private Employee","Farmer","Business","Homemaker","Driver","Government Employee"],1)))
    cur.executemany("INSERT INTO ReligionMaster VALUES (?, ?)",[(1,"Hindu"),(2,"Muslim"),(3,"Christian"),(4,"Jain"),(5,"Other")])
    cur.executemany("INSERT INTO CasteMaster VALUES (?, ?)",[(1,"General"),(2,"OBC"),(3,"SC"),(4,"ST"),(5,"Not recorded")])
    acts=[("IPC","Indian Penal Code","IPC",1),("IT","Information Technology Act","IT Act",1),("CrPC","Code of Criminal Procedure","CrPC",1)]
    cur.executemany("INSERT INTO Act VALUES (?, ?, ?, ?)",acts)
    sections={(x[4],x[5]):x[6] for x in CRIME_TYPES}
    cur.executemany("INSERT INTO Section VALUES (?, ?, ?, 1)",[(act,sec,desc) for (act,sec),desc in sections.items()])
    return station_by_district, unit_rows, employee_rows, heads, {r[2]:r[0] for r in sub_rows}

def generate(db_path: Path, count: int):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists(): db_path.unlink()
    con=sqlite3.connect(db_path); cur=con.cursor(); cur.executescript(SCHEMA)
    stations, unit_rows, employees, heads, subheads=seed_reference(cur)
    case_rows=[]; complainants=[]; victims=[]; accused=[]; arrests=[]; associations=[]; charges=[]; evidence=[]; vehicles=[]; phones=[]; witnesses=[]; fts=[]
    start=datetime(2025,1,1); serials={}; complaint_id=victim_id=accused_id=arrest_id=cs_id=evidence_id=vehicle_id=phone_id=witness_id=1
    for cid in range(1,count+1):
        linked_cluster = cid <= min(70,count)
        district = DISTRICTS[0] if linked_cluster else RNG.choice(DISTRICTS)
        did,dname,base_lat,base_lon=district; station=stations[did][(cid if linked_cluster else RNG.randrange(20))%len(stations[did])]
        type_row = CRIME_TYPES[0] if linked_cluster else RNG.choice(CRIME_TYPES)
        category, gravity, head, sub, act, section, section_desc, template = type_row
        registered=start+timedelta(days=RNG.randrange(570),minutes=RNG.randrange(1440))
        if linked_cluster: incident=registered.replace(hour=RNG.randint(2,3),minute=RNG.randrange(60))-timedelta(days=RNG.randrange(1,12))
        else: incident=registered-timedelta(hours=RNG.randrange(1,120))
        incident_end=incident+timedelta(minutes=RNG.randrange(10,180)); received=incident_end+timedelta(minutes=RNG.randrange(15,600))
        key=(category,did,station,registered.year); serials[key]=serials.get(key,0)+1
        crime_no=f"{category}{did:04d}{station:04d}{registered.year:04d}{serials[key]:05d}"; case_no=f"{registered.year}{serials[key]:05d}"
        status=1 if linked_cluster else RNG.choices([1,2,3,4,5],[38,21,15,12,14])[0]
        court=[c for c in range(1,len(DISTRICTS)+1) if c==DISTRICTS.index(district)+1][0]
        employee=next(e[0] for e in employees if e[2]==station)
        lat=base_lat+RNG.uniform(-.065,.065); lon=base_lon+RNG.uniform(-.075,.075)
        vehicle_text=" A white Maruti Swift KA-03-MR-4821 was observed by CCTV." if linked_cluster else ""
        facts=f"{template} reported in {dname}. {vehicle_text}".strip()
        case_rows.append((cid,crime_no,case_no,registered.date().isoformat(),employee,station,category,gravity,heads[head],subheads[sub],status,court,iso(incident),iso(incident_end),iso(received),lat,lon,facts))
        associations.append((cid,act,section,1,1));
        complainants.append((complaint_id,cid,name(),RNG.randint(22,67),RNG.randint(1,7),RNG.randint(1,5),RNG.randint(1,5),RNG.choice([1,2])));complaint_id+=1
        victims.append((victim_id,cid,name(),RNG.randint(18,75),RNG.choice([1,2]),"0"));victim_id+=1
        evidence_text=f"Case {crime_no}: {('CCTV visual review identifies a white Swift at '+incident.strftime('%H:%M')+'.' if linked_cluster else 'Officer evidence note: '+template.lower()+'.')}"
        evidence.append((evidence_id,cid,"CCTV" if linked_cluster else RNG.choice(["Document","Digital","CCTV","Forensic"]),f"EVD-{20260000+evidence_id}",evidence_text,.89 if linked_cluster else round(RNG.uniform(.58,.93),2),iso(received)));evidence_id+=1
        if linked_cluster or RNG.random()<.35:
            reg="KA-03-MR-4821" if linked_cluster else f"KA-{RNG.randint(1,20):02d}-{RNG.choice(['AB','CD','MN','PX'])}-{RNG.randint(1000,9999)}"
            vehicles.append((vehicle_id,cid,reg,"Maruti Swift" if linked_cluster else RNG.choice(["Honda Activa","Hyundai i20","Tata Nexon","Maruti Baleno"]),"White" if linked_cluster else RNG.choice(["White","Grey","Blue","Black"]),"Observed" if linked_cluster else "Mentioned",.94 if linked_cluster else round(RNG.uniform(.5,.85),2)));vehicle_id+=1
        if linked_cluster or RNG.random()<.28:
            phone="+91 98450 4418" if linked_cluster else f"+91 9{RNG.randint(100000000,999999999)}"
            phones.append((phone_id,cid,phone,"Suspect contact" if linked_cluster else "Witness contact",.83 if linked_cluster else round(RNG.uniform(.5,.8),2)));phone_id+=1
        if linked_cluster or RNG.random()<.45:
            witnesses.append((witness_id,cid,name(),"Witness reports a white hatchback leaving the location." if linked_cluster else f"Witness statement recorded for {sub.lower()}.",iso(received+timedelta(hours=2))));witness_id+=1
        if linked_cluster or RNG.random()<.42:
            accused.append((accused_id,cid,"Rahul Sheikh" if linked_cluster else name(),RNG.randint(20,52),1,"A1"));
            if RNG.random()<.6:
                arrests.append((arrest_id,cid,1,(registered+timedelta(days=RNG.randint(2,80))).date().isoformat(),1,did,station,employee,court,accused_id,1,0));arrest_id+=1
            accused_id+=1
        if status in (2,3,5): charges.append((cs_id,cid,iso(registered+timedelta(days=RNG.randint(40,190))),"A",employee));cs_id+=1
        fts.append((crime_no,dname,next(u[1] for u in unit_rows if u[0]==station),sub,facts,evidence_text))
    for row in case_rows:
        try:
            cur.execute("INSERT INTO CaseMaster VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",row)
        except sqlite3.IntegrityError as exc:
            raise RuntimeError(f"CaseMaster FK failure for {row[1]}: {row}") from exc
    cur.executemany("INSERT INTO ComplainantDetails VALUES (?, ?, ?, ?, ?, ?, ?, ?)",complainants);cur.executemany("INSERT INTO Victim VALUES (?, ?, ?, ?, ?, ?)",victims)
    cur.executemany("INSERT INTO Accused VALUES (?, ?, ?, ?, ?, ?)",accused);cur.executemany("INSERT INTO ArrestSurrender VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",arrests)
    cur.executemany("INSERT INTO ActSectionAssociation VALUES (?, ?, ?, ?, ?)",associations);cur.executemany("INSERT INTO ChargesheetDetails VALUES (?, ?, ?, ?, ?)",charges)
    cur.executemany("INSERT INTO Evidence VALUES (?, ?, ?, ?, ?, ?, ?)",evidence);cur.executemany("INSERT INTO CaseVehicle VALUES (?, ?, ?, ?, ?, ?, ?)",vehicles);cur.executemany("INSERT INTO CasePhone VALUES (?, ?, ?, ?, ?)",phones);cur.executemany("INSERT INTO WitnessStatement VALUES (?, ?, ?, ?, ?)",witnesses);cur.executemany("INSERT INTO CaseSearch VALUES (?, ?, ?, ?, ?, ?)",fts)
    con.commit();con.execute("PRAGMA foreign_key_check");con.close()
    print(f"Generated {count:,} CaseMaster records at {db_path}")

if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--count",type=int,default=5000,choices=range(1000,10001));parser.add_argument("--database",type=Path,default=DEFAULT_DB)
    args=parser.parse_args();generate(args.database,args.count)
