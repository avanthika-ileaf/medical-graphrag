// scripts/import_data.cypher
// Neo4j Cypher import script.
// Run via populate_neo4j.py which copies CSV files to Neo4j import dir first.

// ─── Constraints ───────────────────────────────────────────────────────────
CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.patientID IS UNIQUE;
CREATE CONSTRAINT drug_name IF NOT EXISTS FOR (d:Drug) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT condition_name IF NOT EXISTS FOR (c:Condition) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT provider_name IF NOT EXISTS FOR (hp:HealthcareProvider) REQUIRE hp.name IS UNIQUE;
CREATE CONSTRAINT procedure_name IF NOT EXISTS FOR (proc:Procedure) REQUIRE proc.name IS UNIQUE;
CREATE CONSTRAINT finding_name IF NOT EXISTS FOR (cf:ClinicalFinding) REQUIRE cf.name IS UNIQUE;

// ─── Indexes ────────────────────────────────────────────────────────────────
CREATE INDEX patient_age IF NOT EXISTS FOR (p:Patient) ON (p.age);
CREATE INDEX patient_gender IF NOT EXISTS FOR (p:Patient) ON (p.gender);
CREATE INDEX drug_class IF NOT EXISTS FOR (d:Drug) ON (d.class);
CREATE INDEX condition_icd10 IF NOT EXISTS FOR (c:Condition) ON (c.icd10Code);
CREATE INDEX condition_category IF NOT EXISTS FOR (c:Condition) ON (c.category);

// ─── Nodes: Drugs ───────────────────────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///drugs.csv' AS row
MERGE (d:Drug {name: row.name})
SET d.class = row.class,
    d.fdaApproved = (row.fda = 'True'),
    d.indications = row.indications,
    d.sideEffects = row.side_effects,
    d.contraindications = row.contraindications;

// ─── Nodes: Conditions ──────────────────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///conditions.csv' AS row
MERGE (c:Condition {name: row.name})
SET c.icd10Code = row.icd10,
    c.category = row.category,
    c.symptoms = row.symptoms,
    c.riskFactors = row.risk_factors;

// ─── Nodes: Healthcare Providers ────────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///providers.csv' AS row
MERGE (hp:HealthcareProvider {name: row.name})
SET hp.specialty = row.specialty,
    hp.npi = row.npi;

// ─── Nodes: Patients ────────────────────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///patients.csv' AS row
MERGE (p:Patient {patientID: row.patientID})
SET p.name = row.name,
    p.age = toInteger(row.age),
    p.gender = row.gender;

// ─── Nodes: Procedures ──────────────────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///procedures.csv' AS row
MERGE (proc:Procedure {name: row.name})
SET proc.type = row.type;

// ─── Nodes: Clinical Findings ───────────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///clinical_findings.csv' AS row
MERGE (cf:ClinicalFinding {name: row.name})
SET cf.severity = row.severity;

// ─── Relationships: INTERACTS_WITH (symmetric) ──────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///interactions.csv' AS row
MATCH (d1:Drug {name: row.drug1})
MATCH (d2:Drug {name: row.drug2})
MERGE (d1)-[i:INTERACTS_WITH {mechanism: row.mechanism}]->(d2)
SET i.severity = toFloat(row.severity);

// ─── Relationships: CONTRAINDICATED_FOR ─────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///contraindications.csv' AS row
MATCH (d:Drug {name: row.drug})
MATCH (c:Condition {name: row.condition})
MERGE (d)-[:CONTRAINDICATED_FOR]->(c);

// ─── Relationships: TAKES_DRUG ──────────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///patient_drugs.csv' AS row
MATCH (p:Patient {patientID: row.patientID})
MATCH (d:Drug {name: row.drugName})
MERGE (p)-[r:TAKES_DRUG {drugName: row.drugName}]->(d)
SET r.dosage = row.dosage,
    r.frequency = row.frequency,
    r.startDate = row.startDate;

// ─── Relationships: HAS_CONDITION ───────────────────────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///patient_conditions.csv' AS row
MATCH (p:Patient {patientID: row.patientID})
MATCH (c:Condition {name: row.conditionName})
MERGE (p)-[r:HAS_CONDITION {conditionName: row.conditionName}]->(c)
SET r.diagnosisDate = row.diagnosisDate,
    r.severity = row.severity;

// ─── Relationships: TREATED_BY (Patient -> Provider) ────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///patient_providers.csv' AS row
MATCH (p:Patient {patientID: row.patientID})
MATCH (hp:HealthcareProvider {name: row.providerName})
MERGE (p)-[:TREATED_BY]->(hp);

// ─── Relationships: TREATED_BY (Condition -> Drug) ──────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///condition_treatments.csv' AS row
MATCH (c:Condition {name: row.condition})
MATCH (d:Drug {name: row.drug})
MERGE (c)-[:TREATED_BY]->(d);

// ─── Relationships: UNDERWENT (Patient -> Procedure) ────────────────────────
LOAD CSV WITH HEADERS FROM 'file:///patient_procedures.csv' AS row
MATCH (p:Patient {patientID: row.patientID})
MATCH (proc:Procedure {name: row.procedureName})
MERGE (p)-[r:UNDERWENT]->(proc)
SET r.date = row.date;

// ─── Relationships: HAS_OBSERVATION (Patient -> ClinicalFinding) ────────────
LOAD CSV WITH HEADERS FROM 'file:///patient_observations.csv' AS row
MATCH (p:Patient {patientID: row.patientID})
MATCH (cf:ClinicalFinding {name: row.findingName})
MERGE (p)-[r:HAS_OBSERVATION]->(cf)
SET r.date = row.date;
