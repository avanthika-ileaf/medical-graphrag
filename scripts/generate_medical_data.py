"""
scripts/generate_medical_data.py

Generates synthetic medical data: patients, drugs, conditions,
drug interactions, patient-drug assignments, and patient-condition
assignments. Saves everything to data/ as JSON and CSV files
ready for Neo4j LOAD CSV import.
"""

import json
import random
import csv
import os
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)

# ─────────────────────────────────────────────
# Static medical reference data
# ─────────────────────────────────────────────

DRUGS = [
    {"name": "Warfarin",       "class": "Anticoagulant",       "fda": True,  "indications": "Blood clot prevention, atrial fibrillation", "side_effects": "Bleeding, bruising", "contraindications": "Pregnancy, active bleeding"},
    {"name": "Aspirin",        "class": "NSAID",                "fda": True,  "indications": "Pain, fever, cardiovascular prophylaxis",    "side_effects": "GI upset, bleeding",  "contraindications": "Peptic ulcer disease"},
    {"name": "Metformin",      "class": "Antidiabetic",         "fda": True,  "indications": "Type 2 Diabetes",                           "side_effects": "GI upset, lactic acidosis", "contraindications": "Renal impairment"},
    {"name": "Lisinopril",     "class": "ACE Inhibitor",        "fda": True,  "indications": "Hypertension, heart failure",                "side_effects": "Cough, hyperkalemia", "contraindications": "Pregnancy, angioedema"},
    {"name": "Atorvastatin",   "class": "Statin",               "fda": True,  "indications": "High cholesterol, cardiovascular disease",   "side_effects": "Myopathy, liver enzyme elevation", "contraindications": "Active liver disease"},
    {"name": "Amlodipine",     "class": "Calcium Channel Blocker","fda": True,"indications": "Hypertension, angina",                       "side_effects": "Edema, flushing",     "contraindications": "Severe aortic stenosis"},
    {"name": "Omeprazole",     "class": "Proton Pump Inhibitor","fda": True,  "indications": "GERD, peptic ulcer",                         "side_effects": "Headache, diarrhea",  "contraindications": "Hypersensitivity"},
    {"name": "Metoprolol",     "class": "Beta Blocker",         "fda": True,  "indications": "Hypertension, heart failure, angina",         "side_effects": "Fatigue, bradycardia","contraindications": "Severe bradycardia, cardiogenic shock"},
    {"name": "Levothyroxine",  "class": "Thyroid Hormone",      "fda": True,  "indications": "Hypothyroidism",                             "side_effects": "Palpitations, insomnia","contraindications": "Uncorrected adrenal insufficiency"},
    {"name": "Gabapentin",     "class": "Anticonvulsant",       "fda": True,  "indications": "Epilepsy, neuropathic pain",                  "side_effects": "Drowsiness, dizziness","contraindications": "Hypersensitivity"},
    {"name": "Hydrochlorothiazide","class": "Diuretic",         "fda": True,  "indications": "Hypertension, edema",                         "side_effects": "Electrolyte imbalance, gout","contraindications": "Anuria"},
    {"name": "Sertraline",     "class": "SSRI",                 "fda": True,  "indications": "Depression, anxiety, OCD",                   "side_effects": "Nausea, insomnia, sexual dysfunction","contraindications": "MAO inhibitor use"},
    {"name": "Fluoxetine",     "class": "SSRI",                 "fda": True,  "indications": "Depression, OCD, panic disorder",            "side_effects": "Nausea, insomnia",    "contraindications": "MAO inhibitor use"},
    {"name": "Amoxicillin",    "class": "Antibiotic",           "fda": True,  "indications": "Bacterial infections",                        "side_effects": "Diarrhea, rash",      "contraindications": "Penicillin allergy"},
    {"name": "Azithromycin",   "class": "Antibiotic",           "fda": True,  "indications": "Respiratory infections, STIs",               "side_effects": "GI upset, QT prolongation","contraindications": "Liver disease, QT prolongation"},
    {"name": "Clopidogrel",    "class": "Antiplatelet",         "fda": True,  "indications": "ACS, stroke prevention",                     "side_effects": "Bleeding",            "contraindications": "Active bleeding, hypersensitivity"},
    {"name": "Furosemide",     "class": "Loop Diuretic",        "fda": True,  "indications": "Heart failure, edema",                        "side_effects": "Electrolyte loss, dehydration","contraindications": "Anuria"},
    {"name": "Prednisone",     "class": "Corticosteroid",       "fda": True,  "indications": "Inflammation, autoimmune conditions",         "side_effects": "Weight gain, hyperglycemia","contraindications": "Systemic fungal infection"},
    {"name": "Allopurinol",    "class": "Xanthine Oxidase Inhibitor","fda": True,"indications": "Gout",                                    "side_effects": "Rash, GI upset",     "contraindications": "Hypersensitivity"},
    {"name": "Insulin Glargine","class": "Insulin",             "fda": True,  "indications": "Type 1 & 2 Diabetes",                        "side_effects": "Hypoglycemia, weight gain","contraindications": "Hypoglycemia"},
    {"name": "Sitagliptin",    "class": "DPP-4 Inhibitor",     "fda": True,  "indications": "Type 2 Diabetes",                            "side_effects": "Nasopharyngitis",     "contraindications": "Type 1 Diabetes, DKA"},
    {"name": "Losartan",       "class": "ARB",                  "fda": True,  "indications": "Hypertension, diabetic nephropathy",          "side_effects": "Hyperkalemia, dizziness","contraindications": "Pregnancy"},
    {"name": "Spironolactone", "class": "Aldosterone Antagonist","fda": True, "indications": "Heart failure, hypertension, hyperaldosteronism","side_effects": "Hyperkalemia, gynecomastia","contraindications": "Hyperkalemia, Addison's disease"},
    {"name": "Tramadol",       "class": "Opioid Analgesic",     "fda": True,  "indications": "Moderate-severe pain",                        "side_effects": "Drowsiness, nausea, seizures","contraindications": "MAO inhibitor use, severe respiratory depression"},
    {"name": "Ciprofloxacin",  "class": "Fluoroquinolone",      "fda": True,  "indications": "Bacterial infections, UTIs",                  "side_effects": "Tendinopathy, QT prolongation","contraindications": "QT prolongation, myasthenia gravis"},
    {"name": "Digoxin",        "class": "Cardiac Glycoside",    "fda": True,  "indications": "Heart failure, atrial fibrillation",          "side_effects": "Arrhythmia, GI upset","contraindications": "Ventricular fibrillation"},
    {"name": "Carvedilol",     "class": "Beta Blocker",         "fda": True,  "indications": "Heart failure, hypertension",                 "side_effects": "Dizziness, fatigue",  "contraindications": "Severe bradycardia, bronchospasm"},
    {"name": "Duloxetine",     "class": "SNRI",                 "fda": True,  "indications": "Depression, anxiety, neuropathic pain",       "side_effects": "Nausea, dry mouth",   "contraindications": "MAO inhibitor use, uncontrolled glaucoma"},
    {"name": "Pantoprazole",   "class": "Proton Pump Inhibitor","fda": True,  "indications": "GERD, Zollinger-Ellison syndrome",            "side_effects": "Headache, diarrhea",  "contraindications": "Hypersensitivity"},
    {"name": "Tamsulosin",     "class": "Alpha Blocker",        "fda": True,  "indications": "BPH",                                        "side_effects": "Orthostatic hypotension","contraindications": "Severe hepatic impairment"},
]

CONDITIONS = [
    {"name": "Type 2 Diabetes",           "icd10": "E11", "category": "Chronic", "symptoms": "Polyuria, polydipsia, fatigue", "risk_factors": "Obesity, sedentary lifestyle"},
    {"name": "Hypertension",              "icd10": "I10", "category": "Chronic", "symptoms": "Headache, dizziness, epistaxis", "risk_factors": "Obesity, high salt diet, age"},
    {"name": "Chronic Kidney Disease",    "icd10": "N18", "category": "Chronic", "symptoms": "Fatigue, edema, decreased urine output", "risk_factors": "Diabetes, hypertension"},
    {"name": "Heart Failure",             "icd10": "I50", "category": "Chronic", "symptoms": "Dyspnea, edema, fatigue", "risk_factors": "Hypertension, CAD, cardiomyopathy"},
    {"name": "Atrial Fibrillation",       "icd10": "I48", "category": "Chronic", "symptoms": "Palpitations, dyspnea, fatigue", "risk_factors": "Age, hypertension, heart disease"},
    {"name": "Coronary Artery Disease",   "icd10": "I25", "category": "Chronic", "symptoms": "Chest pain, dyspnea, fatigue", "risk_factors": "Hypertension, diabetes, hyperlipidemia"},
    {"name": "Hypothyroidism",            "icd10": "E03", "category": "Chronic", "symptoms": "Fatigue, weight gain, cold intolerance", "risk_factors": "Autoimmune disease, radiation"},
    {"name": "Hyperlipidemia",            "icd10": "E78", "category": "Chronic", "symptoms": "Usually asymptomatic", "risk_factors": "Diet, genetics, obesity"},
    {"name": "COPD",                      "icd10": "J44", "category": "Chronic", "symptoms": "Dyspnea, chronic cough, wheezing", "risk_factors": "Smoking, air pollution"},
    {"name": "Asthma",                    "icd10": "J45", "category": "Chronic", "symptoms": "Wheezing, shortness of breath, chest tightness", "risk_factors": "Allergies, genetics"},
    {"name": "Depression",                "icd10": "F32", "category": "Chronic", "symptoms": "Low mood, anhedonia, fatigue, sleep changes", "risk_factors": "Genetics, stress, trauma"},
    {"name": "Anxiety Disorder",          "icd10": "F41", "category": "Chronic", "symptoms": "Excessive worry, palpitations, restlessness", "risk_factors": "Genetics, trauma, stress"},
    {"name": "Gout",                      "icd10": "M10", "category": "Chronic", "symptoms": "Acute joint pain, swelling, redness", "risk_factors": "High purine diet, alcohol, obesity"},
    {"name": "Osteoporosis",              "icd10": "M81", "category": "Chronic", "symptoms": "Usually asymptomatic until fracture", "risk_factors": "Age, female sex, low calcium intake"},
    {"name": "Type 1 Diabetes",           "icd10": "E10", "category": "Chronic", "symptoms": "Polyuria, polydipsia, weight loss", "risk_factors": "Autoimmune, genetics"},
    {"name": "Peptic Ulcer Disease",      "icd10": "K27", "category": "Chronic", "symptoms": "Epigastric pain, nausea, bloating", "risk_factors": "H. pylori, NSAIDs, stress"},
    {"name": "Chronic Liver Disease",     "icd10": "K74", "category": "Chronic", "symptoms": "Jaundice, fatigue, ascites", "risk_factors": "Alcohol, hepatitis, NASH"},
    {"name": "Epilepsy",                  "icd10": "G40", "category": "Chronic", "symptoms": "Seizures, postictal confusion", "risk_factors": "Head trauma, genetics, brain tumors"},
    {"name": "Rheumatoid Arthritis",      "icd10": "M05", "category": "Chronic", "symptoms": "Joint pain, swelling, morning stiffness", "risk_factors": "Female sex, genetics"},
    {"name": "Peripheral Neuropathy",     "icd10": "G60", "category": "Chronic", "symptoms": "Numbness, tingling, burning pain", "risk_factors": "Diabetes, alcohol, chemotherapy"},
    {"name": "Pneumonia",                 "icd10": "J18", "category": "Acute",   "symptoms": "Fever, cough, dyspnea, chest pain", "risk_factors": "Immunosuppression, age"},
    {"name": "Urinary Tract Infection",   "icd10": "N39", "category": "Acute",   "symptoms": "Dysuria, frequency, urgency", "risk_factors": "Female sex, catheterization, diabetes"},
    {"name": "Acute Myocardial Infarction","icd10":"I21", "category": "Acute",   "symptoms": "Chest pain, diaphoresis, dyspnea", "risk_factors": "CAD, hypertension, diabetes"},
    {"name": "Cellulitis",                "icd10": "L03", "category": "Acute",   "symptoms": "Skin redness, warmth, swelling, pain", "risk_factors": "Skin breach, immunosuppression"},
    {"name": "Deep Vein Thrombosis",      "icd10": "I82", "category": "Acute",   "symptoms": "Leg swelling, pain, erythema", "risk_factors": "Immobility, surgery, malignancy"},
]

DRUG_INTERACTIONS = [
    {"drug1": "Warfarin",      "drug2": "Aspirin",         "severity": 0.90, "mechanism": "Additive anticoagulation increases bleeding risk"},
    {"drug1": "Warfarin",      "drug2": "Ciprofloxacin",   "severity": 0.85, "mechanism": "CYP2C9 inhibition increases warfarin levels"},
    {"drug1": "Warfarin",      "drug2": "Fluoxetine",      "severity": 0.80, "mechanism": "CYP2C9 inhibition increases warfarin exposure"},
    {"drug1": "Warfarin",      "drug2": "Sertraline",      "severity": 0.75, "mechanism": "Serotonin effects on platelets + CYP inhibition"},
    {"drug1": "Warfarin",      "drug2": "Amoxicillin",     "severity": 0.70, "mechanism": "Gut flora disruption reduces vitamin K production"},
    {"drug1": "Warfarin",      "drug2": "Azithromycin",    "severity": 0.72, "mechanism": "Inhibits warfarin metabolism via P-gp"},
    {"drug1": "Metformin",     "drug2": "Furosemide",      "severity": 0.65, "mechanism": "Increased lactic acidosis risk with reduced renal clearance"},
    {"drug1": "Metformin",     "drug2": "Prednisone",      "severity": 0.70, "mechanism": "Corticosteroids cause hyperglycemia opposing metformin"},
    {"drug1": "Lisinopril",    "drug2": "Spironolactone",  "severity": 0.80, "mechanism": "Additive hyperkalemia risk — potentially fatal"},
    {"drug1": "Lisinopril",    "drug2": "Hydrochlorothiazide","severity": 0.30, "mechanism": "Additive antihypertensive effect — usually intentional"},
    {"drug1": "Lisinopril",    "drug2": "Losartan",        "severity": 0.75, "mechanism": "Dual RAAS blockade increases hyperkalemia and AKI risk"},
    {"drug1": "Atorvastatin",  "drug2": "Azithromycin",    "severity": 0.65, "mechanism": "CYP3A4 inhibition increases statin concentration → myopathy"},
    {"drug1": "Atorvastatin",  "drug2": "Ciprofloxacin",   "severity": 0.60, "mechanism": "Moderate CYP3A4 inhibition raises statin levels"},
    {"drug1": "Digoxin",       "drug2": "Amiodarone",      "severity": 0.88, "mechanism": "P-gp inhibition increases digoxin to toxic levels"},
    {"drug1": "Digoxin",       "drug2": "Azithromycin",    "severity": 0.78, "mechanism": "P-gp inhibition elevates digoxin → arrhythmia"},
    {"drug1": "Digoxin",       "drug2": "Spironolactone",  "severity": 0.55, "mechanism": "Spironolactone may reduce renal digoxin clearance"},
    {"drug1": "Sertraline",    "drug2": "Tramadol",        "severity": 0.85, "mechanism": "Serotonin syndrome risk — potentially life-threatening"},
    {"drug1": "Fluoxetine",    "drug2": "Tramadol",        "severity": 0.88, "mechanism": "Serotonin syndrome + seizure risk"},
    {"drug1": "Fluoxetine",    "drug2": "Duloxetine",      "severity": 0.80, "mechanism": "Additive serotonergic effects → serotonin syndrome"},
    {"drug1": "Sertraline",    "drug2": "Duloxetine",      "severity": 0.78, "mechanism": "Additive serotonergic and noradrenergic effects"},
    {"drug1": "Metoprolol",    "drug2": "Amlodipine",      "severity": 0.35, "mechanism": "Additive hypotensive effect — usually monitored"},
    {"drug1": "Metoprolol",    "drug2": "Carvedilol",      "severity": 0.70, "mechanism": "Additive beta blockade → bradycardia and hypotension"},
    {"drug1": "Prednisone",    "drug2": "Aspirin",         "severity": 0.65, "mechanism": "Additive GI mucosal injury risk"},
    {"drug1": "Prednisone",    "drug2": "Furosemide",      "severity": 0.55, "mechanism": "Additive hypokalemia and fluid/electrolyte disturbances"},
    {"drug1": "Allopurinol",   "drug2": "Amoxicillin",     "severity": 0.60, "mechanism": "Increased risk of maculopapular rash"},
    {"drug1": "Ciprofloxacin", "drug2": "Azithromycin",    "severity": 0.80, "mechanism": "Additive QT prolongation → torsades de pointes"},
    {"drug1": "Ciprofloxacin", "drug2": "Digoxin",         "severity": 0.72, "mechanism": "Gut flora disruption increases digoxin absorption"},
    {"drug1": "Gabapentin",    "drug2": "Tramadol",        "severity": 0.75, "mechanism": "Additive CNS depression — respiratory depression risk"},
    {"drug1": "Furosemide",    "drug2": "Digoxin",         "severity": 0.78, "mechanism": "Hypokalemia from furosemide potentiates digoxin toxicity"},
    {"drug1": "Furosemide",    "drug2": "Lisinopril",      "severity": 0.40, "mechanism": "First-dose hypotension; ACE inhibitor + volume depletion"},
    {"drug1": "Spironolactone","drug2": "Losartan",        "severity": 0.78, "mechanism": "Triple RAAS suppression → severe hyperkalemia"},
    {"drug1": "Aspirin",       "drug2": "Clopidogrel",     "severity": 0.45, "mechanism": "Dual antiplatelet — standard in ACS but increases bleeding"},
    {"drug1": "Tramadol",      "drug2": "Gabapentin",      "severity": 0.75, "mechanism": "Additive CNS/respiratory depression"},
    {"drug1": "Insulin Glargine","drug2":"Metformin",      "severity": 0.25, "mechanism": "Additive hypoglycemic effect — usually intentional combination"},
    {"drug1": "Insulin Glargine","drug2":"Prednisone",     "severity": 0.80, "mechanism": "Corticosteroids cause insulin resistance requiring dose escalation"},
    {"drug1": "Sitagliptin",   "drug2": "Insulin Glargine","severity": 0.40, "mechanism": "Additive hypoglycemia risk; monitor glucose"},
]

DRUG_CONTRAINDICATIONS = [
    {"drug": "Metformin",      "condition": "Chronic Kidney Disease"},
    {"drug": "Warfarin",       "condition": "Peptic Ulcer Disease"},
    {"drug": "Aspirin",        "condition": "Peptic Ulcer Disease"},
    {"drug": "Prednisone",     "condition": "Peptic Ulcer Disease"},
    {"drug": "Metoprolol",     "condition": "COPD"},
    {"drug": "Metoprolol",     "condition": "Asthma"},
    {"drug": "Carvedilol",     "condition": "COPD"},
    {"drug": "Carvedilol",     "condition": "Asthma"},
    {"drug": "Lisinopril",     "condition": "Chronic Kidney Disease"},
    {"drug": "Spironolactone", "condition": "Chronic Kidney Disease"},
    {"drug": "NSAIDs",         "condition": "Chronic Kidney Disease"},
    {"drug": "Ciprofloxacin",  "condition": "Epilepsy"},
    {"drug": "Tramadol",       "condition": "Epilepsy"},
    {"drug": "Furosemide",     "condition": "Gout"},
    {"drug": "Allopurinol",    "condition": "Chronic Kidney Disease"},
]

PROVIDERS = [
    {"name": "Dr. Emily Carter",    "specialty": "Cardiology"},
    {"name": "Dr. James Nguyen",    "specialty": "Endocrinology"},
    {"name": "Dr. Maria Santos",    "specialty": "Nephrology"},
    {"name": "Dr. Robert Kim",      "specialty": "General Practice"},
    {"name": "Dr. Lisa Patel",      "specialty": "Internal Medicine"},
    {"name": "Dr. David Brown",     "specialty": "Pulmonology"},
    {"name": "Dr. Sarah Wilson",    "specialty": "Neurology"},
    {"name": "Dr. Michael Chen",    "specialty": "Rheumatology"},
    {"name": "Dr. Jennifer Lee",    "specialty": "Psychiatry"},
    {"name": "Dr. Thomas Johnson",  "specialty": "General Practice"},
]

PROCEDURES = [
    {"name": "Appendectomy", "type": "Surgical"},
    {"name": "Echocardiogram", "type": "Diagnostic"},
    {"name": "Colonoscopy", "type": "Diagnostic"},
    {"name": "Coronary Artery Bypass", "type": "Surgical"},
    {"name": "MRI Brain", "type": "Diagnostic"},
    {"name": "Knee Replacement", "type": "Surgical"},
    {"name": "Cataract Surgery", "type": "Surgical"},
    {"name": "Electrocardiogram", "type": "Diagnostic"},
    {"name": "Dialysis", "type": "Therapeutic"},
    {"name": "Endoscopy", "type": "Diagnostic"},
]

CLINICAL_FINDINGS = [
    {"name": "Elevated Blood Pressure", "severity": "Moderate"},
    {"name": "Normal Sinus Rhythm", "severity": "Normal"},
    {"name": "Hyperglycemia", "severity": "High"},
    {"name": "Hypokalemia", "severity": "Moderate"},
    {"name": "Tachycardia", "severity": "High"},
    {"name": "Proteinuria", "severity": "Moderate"},
    {"name": "Leukocytosis", "severity": "High"},
    {"name": "Anemia", "severity": "Moderate"},
    {"name": "Hypoxia", "severity": "High"},
    {"name": "Fever", "severity": "Moderate"},
]

CONDITION_TREATMENTS = [
    {"condition": "Type 2 Diabetes", "drug": "Metformin"},
    {"condition": "Hypertension", "drug": "Lisinopril"},
    {"condition": "Hypertension", "drug": "Amlodipine"},
    {"condition": "Hypertension", "drug": "Losartan"},
    {"condition": "Hypertension", "drug": "Hydrochlorothiazide"},
    {"condition": "Type 2 Diabetes", "drug": "Sitagliptin"},
    {"condition": "Type 1 Diabetes", "drug": "Insulin Glargine"},
    {"condition": "Chronic Kidney Disease", "drug": "Losartan"},
    {"condition": "Heart Failure", "drug": "Lisinopril"},
    {"condition": "Heart Failure", "drug": "Carvedilol"},
    {"condition": "Heart Failure", "drug": "Furosemide"},
    {"condition": "Heart Failure", "drug": "Spironolactone"},
    {"condition": "Atrial Fibrillation", "drug": "Warfarin"},
    {"condition": "Atrial Fibrillation", "drug": "Digoxin"},
    {"condition": "Coronary Artery Disease", "drug": "Aspirin"},
    {"condition": "Coronary Artery Disease", "drug": "Atorvastatin"},
    {"condition": "Coronary Artery Disease", "drug": "Clopidogrel"},
    {"condition": "Hypothyroidism", "drug": "Levothyroxine"},
    {"condition": "Hyperlipidemia", "drug": "Atorvastatin"},
    {"condition": "Depression", "drug": "Sertraline"},
    {"condition": "Depression", "drug": "Fluoxetine"},
    {"condition": "Depression", "drug": "Duloxetine"},
    {"condition": "Anxiety Disorder", "drug": "Sertraline"},
    {"condition": "Anxiety Disorder", "drug": "Duloxetine"},
    {"condition": "Gout", "drug": "Allopurinol"},
    {"condition": "Peptic Ulcer Disease", "drug": "Omeprazole"},
    {"condition": "Peptic Ulcer Disease", "drug": "Pantoprazole"},
    {"condition": "Epilepsy", "drug": "Gabapentin"},
    {"condition": "Peripheral Neuropathy", "drug": "Gabapentin"},
    {"condition": "Peripheral Neuropathy", "drug": "Duloxetine"},
    {"condition": "Pneumonia", "drug": "Amoxicillin"},
    {"condition": "Pneumonia", "drug": "Azithromycin"},
    {"condition": "Urinary Tract Infection", "drug": "Ciprofloxacin"},
]


def random_date(start_year: int = 2015, end_year: int = 2024) -> str:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


def generate_patients(n: int = 1000) -> list[dict]:
    patients = []
    for i in range(n):
        patients.append({
            "patientID": f"P{i:05d}",
            "name": fake.name(),
            "age": random.randint(18, 90),
            "gender": random.choice(["M", "F"]),
        })
    return patients


def generate_patient_drugs(patients: list[dict], drugs: list[dict]) -> list[dict]:
    """Assign 1-6 drugs per patient; ~30% of patients get 3+."""
    assignments = []
    drug_names = [d["name"] for d in drugs]
    dosages = ["5mg", "10mg", "25mg", "50mg", "100mg", "200mg", "500mg", "1000mg"]
    frequencies = ["once daily", "twice daily", "three times daily", "as needed", "weekly"]

    for patient in patients:
        n_drugs = random.choices([1, 2, 3, 4, 5, 6], weights=[20, 25, 25, 15, 10, 5])[0]
        assigned = random.sample(drug_names, min(n_drugs, len(drug_names)))
        for drug in assigned:
            assignments.append({
                "patientID": patient["patientID"],
                "drugName": drug,
                "dosage": random.choice(dosages),
                "frequency": random.choice(frequencies),
                "startDate": random_date(),
            })
    return assignments


def generate_patient_conditions(patients: list[dict], conditions: list[dict]) -> list[dict]:
    """Assign 1-4 conditions per patient."""
    assignments = []
    condition_names = [c["name"] for c in conditions]
    severities = ["mild", "moderate", "severe"]

    for patient in patients:
        n_cond = random.choices([1, 2, 3, 4], weights=[30, 40, 20, 10])[0]
        assigned = random.sample(condition_names, min(n_cond, len(condition_names)))
        for cond in assigned:
            assignments.append({
                "patientID": patient["patientID"],
                "conditionName": cond,
                "diagnosisDate": random_date(2010, 2023),
                "severity": random.choice(severities),
            })
    return assignments


def generate_patient_providers(patients: list[dict], providers: list[dict]) -> list[dict]:
    """Assign 1-2 providers per patient."""
    assignments = []
    for patient in patients:
        n_providers = random.choices([1, 2], weights=[70, 30])[0]
        assigned = random.sample(providers, min(n_providers, len(providers)))
        for provider in assigned:
            assignments.append({
                "patientID": patient["patientID"],
                "providerName": provider["name"],
            })
    return assignments


def generate_patient_procedures(patients: list[dict], procedures: list[dict]) -> list[dict]:
    """Assign procedures to some patients."""
    assignments = []
    for patient in patients:
        n_proc = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
        assigned = random.sample(procedures, min(n_proc, len(procedures)))
        for proc in assigned:
            assignments.append({
                "patientID": patient["patientID"],
                "procedureName": proc["name"],
                "date": random_date()
            })
    return assignments


def generate_patient_observations(patients: list[dict], findings: list[dict]) -> list[dict]:
    """Assign clinical observations to patients."""
    assignments = []
    for patient in patients:
        n_obs = random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
        assigned = random.sample(findings, min(n_obs, len(findings)))
        for obs in assigned:
            assignments.append({
                "patientID": patient["patientID"],
                "findingName": obs["name"],
                "date": random_date()
            })
    return assignments


def save_json(data: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved {len(data)} records → {path}")


def save_csv(data: list[dict], path: str) -> None:
    if not data:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"  Saved {len(data)} records → {path}")


def main():
    print("Generating synthetic medical data...")

    # Always resolve data/ relative to the project root (one level above this script),
    # regardless of which directory the script is invoked from.
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")

    # Read NUM_PATIENTS from .env (or fall back to 50 for safe free-tier testing)
    _env_path = os.path.join(PROJECT_ROOT, ".env")
    _num_patients = 50
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                if _line.startswith("NUM_PATIENTS="):
                    _num_patients = int(_line.strip().split("=", 1)[1])
                    break

    patients = generate_patients(_num_patients)
    patient_drugs = generate_patient_drugs(patients, DRUGS)
    patient_conditions = generate_patient_conditions(patients, CONDITIONS)
    patient_providers = generate_patient_providers(patients, PROVIDERS)
    patient_procedures = generate_patient_procedures(patients, PROCEDURES)
    patient_observations = generate_patient_observations(patients, CLINICAL_FINDINGS)

    # Add NPI to providers
    providers_with_npi = [
        {**p, "npi": f"NPI{i:08d}"} for i, p in enumerate(PROVIDERS)
    ]

    def d(filename):
        return os.path.join(DATA_DIR, filename)

    print("\nSaving JSON files...")
    save_json(patients, d("patients.json"))
    save_json(DRUGS, d("drugs.json"))
    save_json(CONDITIONS, d("conditions.json"))
    save_json(DRUG_INTERACTIONS, d("interactions.json"))
    save_json(DRUG_CONTRAINDICATIONS, d("contraindications.json"))
    save_json(providers_with_npi, d("providers.json"))
    save_json(PROCEDURES, d("procedures.json"))
    save_json(CLINICAL_FINDINGS, d("clinical_findings.json"))
    save_json(CONDITION_TREATMENTS, d("condition_treatments.json"))
    save_json(patient_drugs, d("patient_drugs.json"))
    save_json(patient_conditions, d("patient_conditions.json"))
    save_json(patient_providers, d("patient_providers.json"))
    save_json(patient_procedures, d("patient_procedures.json"))
    save_json(patient_observations, d("patient_observations.json"))

    print("\nSaving CSV files for Neo4j LOAD CSV...")
    save_csv(patients, d("patients.csv"))
    save_csv(DRUGS, d("drugs.csv"))
    save_csv(CONDITIONS, d("conditions.csv"))
    save_csv(DRUG_INTERACTIONS, d("interactions.csv"))
    save_csv(DRUG_CONTRAINDICATIONS, d("contraindications.csv"))
    save_csv(providers_with_npi, d("providers.csv"))
    save_csv(PROCEDURES, d("procedures.csv"))
    save_csv(CLINICAL_FINDINGS, d("clinical_findings.csv"))
    save_csv(CONDITION_TREATMENTS, d("condition_treatments.csv"))
    save_csv(patient_drugs, d("patient_drugs.csv"))
    save_csv(patient_conditions, d("patient_conditions.csv"))
    save_csv(patient_providers, d("patient_providers.csv"))
    save_csv(patient_procedures, d("patient_procedures.csv"))
    save_csv(patient_observations, d("patient_observations.csv"))

    print("\nDone! Summary:")
    print(f"  {len(patients)} patients")
    print(f"  {len(DRUGS)} drugs")
    print(f"  {len(CONDITIONS)} conditions")
    print(f"  {len(DRUG_INTERACTIONS)} drug interactions")
    print(f"  {len(providers_with_npi)} providers")
    print(f"  {len(PROCEDURES)} procedures")
    print(f"  {len(CLINICAL_FINDINGS)} clinical findings")
    print(f"  {len(CONDITION_TREATMENTS)} condition treatments")
    print(f"  {len(patient_drugs)} patient-drug assignments")
    print(f"  {len(patient_conditions)} patient-condition assignments")
    print(f"  {len(patient_providers)} patient-provider assignments")
    print(f"  {len(patient_procedures)} patient-procedure assignments")
    print(f"  {len(patient_observations)} patient-observation assignments")


if __name__ == "__main__":
    main()
