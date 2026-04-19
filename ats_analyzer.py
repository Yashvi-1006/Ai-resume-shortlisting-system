"""
Role-aware ATS analysis utilities.
"""

from __future__ import annotations

import os
import re
import sys
from difflib import SequenceMatcher
from collections import Counter
from datetime import datetime
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_loader import _safe_lemmatize, _safe_stopwords, _safe_tokenize, clean_text


ROLE_PROFILES: Dict[str, Dict[str, List[str]]] = {
    "DevOps Engineer": {
        "skills": ["aws", "docker", "kubernetes", "ci cd", "jenkins", "linux", "terraform", "ansible", "git", "monitoring"],
        "keywords": ["infrastructure", "deployment", "automation", "pipeline", "container", "cloud", "observability", "sre"],
    },
    "Python Developer": {
        "skills": ["python", "django", "flask", "fastapi", "sql", "rest api", "git", "postgresql", "docker", "testing"],
        "keywords": ["backend", "api", "microservice", "automation", "web application", "integration"],
    },
    "Java Developer": {
        "skills": ["java", "spring", "spring boot", "hibernate", "sql", "rest api", "maven", "git", "microservice", "docker"],
        "keywords": ["backend", "enterprise", "api", "service", "jvm", "application"],
    },
    "Data Science": {
        "skills": ["python", "pandas", "numpy", "scikit learn", "machine learning", "sql", "tensorflow", "data visualization", "statistics", "jupyter"],
        "keywords": ["modeling", "analysis", "prediction", "feature engineering", "dataset", "insight"],
    },
    "Database": {
        "skills": ["sql", "mysql", "postgresql", "oracle", "mongodb", "database design", "etl", "performance tuning", "backup", "indexing"],
        "keywords": ["schema", "query", "optimization", "data integrity", "warehouse"],
    },
    "ETL Developer": {
        "skills": ["etl", "sql", "python", "data warehouse", "ssis", "informatica", "airflow", "spark", "oracle", "data pipeline"],
        "keywords": ["transformation", "ingestion", "pipeline", "mapping", "batch processing"],
    },
    "Hadoop": {
        "skills": ["hadoop", "hive", "spark", "hdfs", "sqoop", "pig", "kafka", "yarn", "mapreduce", "linux"],
        "keywords": ["big data", "distributed", "cluster", "data pipeline", "processing"],
    },
    "Web Designing": {
        "skills": ["html", "css", "javascript", "bootstrap", "responsive design", "figma", "photoshop", "ui", "ux", "wireframe"],
        "keywords": ["layout", "design system", "prototype", "branding", "visual design"],
    },
    "Testing": {
        "skills": ["testing", "selenium", "jira", "test case", "qa", "bug tracking", "automation", "api testing", "sql", "regression"],
        "keywords": ["quality assurance", "validation", "defect", "test plan", "coverage"],
    },
    "Automation Testing": {
        "skills": ["selenium", "java", "testng", "cucumber", "api testing", "automation", "jenkins", "jira", "git", "maven"],
        "keywords": ["framework", "regression", "qa automation", "suite", "quality engineering"],
    },
    "DotNet Developer": {
        "skills": ["c#", ".net", "asp.net", "sql server", "entity framework", "mvc", "web api", "azure", "git", "javascript"],
        "keywords": ["enterprise", "backend", "api", "integration", "application"],
    },
    "Business Analyst": {
        "skills": ["requirements gathering", "sql", "excel", "power bi", "tableau", "stakeholder management", "documentation", "process mapping", "agile", "jira"],
        "keywords": ["analysis", "requirement", "workflow", "business process", "reporting"],
    },
    "HR": {
        "skills": ["recruitment", "employee engagement", "onboarding", "performance management", "hris", "training", "communication", "ms office", "policy", "talent acquisition"],
        "keywords": ["people", "hiring", "employee relation", "compliance", "workforce"],
    },
    "Sales": {
        "skills": ["sales", "crm", "lead generation", "negotiation", "client relationship", "presentation", "forecasting", "communication", "account management", "closing"],
        "keywords": ["revenue", "target", "pipeline", "customer", "business growth"],
    },
    "Network Security Engineer": {
        "skills": ["network security", "firewall", "siem", "ids", "ips", "linux", "incident response", "vpn", "aws", "security monitoring"],
        "keywords": ["threat", "vulnerability", "security", "compliance", "risk"],
    },
    "Electrical Engineering": {
        "skills": ["electrical design", "autocad", "plc", "control system", "circuit", "maintenance", "power system", "testing", "instrumentation", "troubleshooting"],
        "keywords": ["wiring", "power", "electrical", "plant", "equipment"],
    },
    "Mechanical Engineer": {
        "skills": ["autocad", "solidworks", "cad", "manufacturing", "maintenance", "quality control", "design", "simulation", "assembly", "engineering drawing"],
        "keywords": ["mechanical", "production", "machine", "fabrication", "design"],
    },
    "Civil Engineer": {
        "skills": ["autocad", "site execution", "quantity surveying", "construction management", "estimation", "structural analysis", "project planning", "billing", "ms project", "surveying"],
        "keywords": ["construction", "site", "structure", "project", "building"],
    },
    "SAP Developer": {
        "skills": ["sap", "abap", "hana", "fiori", "bapi", "workflow", "module integration", "sql", "reporting", "debugging"],
        "keywords": ["erp", "enterprise resource planning", "sap module", "business process"],
    },
    "Blockchain": {
        "skills": ["blockchain", "solidity", "ethereum", "smart contract", "web3", "javascript", "node.js", "cryptography", "truffle", "git"],
        "keywords": ["decentralized", "ledger", "token", "dapp", "crypto"],
    },
    "PMO": {
        "skills": ["project management", "stakeholder management", "ms project", "reporting", "risk management", "governance", "budgeting", "agile", "excel", "communication"],
        "keywords": ["delivery", "timeline", "governance", "coordination", "program"],
    },
    "Operations Manager": {
        "skills": ["operations", "team management", "process improvement", "kpi", "reporting", "planning", "budgeting", "vendor management", "communication", "leadership"],
        "keywords": ["efficiency", "workflow", "delivery", "operations excellence", "process"],
    },
    "Advocate": {
        "skills": ["legal research", "drafting", "litigation", "contract review", "compliance", "negotiation", "documentation", "case law", "advisory", "client management"],
        "keywords": ["law", "legal", "case", "court", "regulation"],
    },
    "Arts": {
        "skills": ["creativity", "illustration", "design", "storytelling", "communication", "adobe photoshop", "visual design", "concept development", "presentation", "branding"],
        "keywords": ["creative", "art", "visual", "portfolio", "concept"],
    },
    "Health and fitness": {
        "skills": ["fitness", "nutrition", "coaching", "wellness", "training", "client assessment", "exercise planning", "communication", "motivation", "health"],
        "keywords": ["wellness", "health", "fitness plan", "client", "training"],
    },
}

ROLE_ALIASES = {
    "Data Scientist": "Data Science",
    "Data Engineer": "ETL Developer",
    "Backend Developer": "Python Developer",
}

GENERIC_PROFILE = {
    "skills": ["communication", "problem solving", "teamwork", "documentation", "project management"],
    "keywords": ["experience", "achievement", "responsibility", "project", "delivery"],
}

COMPANY_REQUIREMENTS = {
    "Google": {
        "keywords": ["data structures", "algorithms", "system design", "python", "java", "distributed systems", "scale", "optimization"],
        "required_skills": ["python", "algorithms"],
        "nice_skills": ["machine learning", "cloud", "kubernetes", "big data"],
    },
    "Microsoft": {
        "keywords": ["cloud", "azure", "windows", "distributed", "microservices", "devops", "infrastructure"],
        "required_skills": ["cloud", "systems"],
        "nice_skills": ["azure", "cloud", "devops"],
    },
    "Amazon": {
        "keywords": ["aws", "ec2", "s3", "lambda", "scalability", "distributed", "databases", "python", "java"],
        "required_skills": ["backend", "databases", "aws"],
        "nice_skills": ["microservices", "devops", "big data"],
    },
    "Meta": {
        "keywords": ["react", "javascript", "mobile", "machine learning", "scale", "infrastructure", "devops"],
        "required_skills": ["frontend", "backend"],
        "nice_skills": ["react", "machine learning"],
    },
}

ATS_KEYWORDS = {role: profile["keywords"] for role, profile in ROLE_PROFILES.items()}

SKILL_VARIATIONS: Dict[str, List[str]] = {
    "javascript": ["js", "ecmascript"],
    "node.js": ["nodejs", "node js"],
    "ci cd": ["ci/cd", "cicd", "continuous integration", "continuous delivery", "continuous deployment"],
    "kubernetes": ["k8s"],
    "docker": ["containerization", "containers"],
    "aws": ["amazon web services"],
    "monitoring": ["observability", "prometheus", "grafana", "elk", "logging", "alerting"],
    "terraform": ["iac", "infrastructure as code"],
    "ansible": ["configuration management"],
    "rest api": ["restful api", "api"],
    "sql": ["mysql", "postgresql", "postgres", "sql server", "oracle"],
    "machine learning": ["ml"],
    "scikit learn": ["sklearn", "scikit-learn"],
    "dotnet": [".net", "asp.net"],
    "linux": ["ubuntu", "redhat", "unix"],
    "windows": ["windows server"],
}

RELATED_SKILL_HINTS: Dict[str, List[str]] = {
    "docker": ["kubernetes", "container", "containerization"],
    "kubernetes": ["docker", "helm", "container orchestration"],
    "ci cd": ["jenkins", "github actions", "gitlab ci", "pipeline", "deployment automation"],
    "monitoring": ["observability", "prometheus", "grafana", "elk"],
    "terraform": ["iac", "cloudformation", "infrastructure as code"],
    "ansible": ["configuration management", "puppet", "chef"],
    "aws": ["cloud", "ec2", "s3", "lambda"],
    "javascript": ["frontend", "react", "node.js"],
}

STOP_WORDS = _safe_stopwords() | {
    "and", "the", "for", "with", "you", "your", "are", "our", "job", "role", "year",
    "years", "experience", "candidate", "preferred", "required", "ability", "using",
    "use", "used", "work", "working", "from", "that", "this", "have", "has", "will",
}

MAX_FUZZY_CANDIDATES = 120


def normalize_tokens(text: str) -> List[str]:
    cleaned = clean_text(text)
    raw_tokens = _safe_tokenize(cleaned)
    normalized = []
    for token in raw_tokens:
        lemma = _safe_lemmatize(token)
        if lemma and len(lemma) > 1:
            normalized.append(lemma)
    return normalized


def normalize_phrase(phrase: str) -> List[str]:
    return list(_normalize_phrase_cached(phrase))


@lru_cache(maxsize=2048)
def _normalize_phrase_cached(phrase: str) -> Tuple[str, ...]:
    return tuple(token for token in normalize_tokens(phrase) if token not in STOP_WORDS)


def canonicalize_term(term: str) -> str:
    return _canonicalize_term_cached(term)


@lru_cache(maxsize=2048)
def _canonicalize_term_cached(term: str) -> str:
    normalized = " ".join(_normalize_phrase_cached(term))
    if not normalized:
        return term.strip().lower()
    for canonical, variants in SKILL_VARIATIONS.items():
        candidate_set = {canonical, *variants}
        normalized_candidates = {" ".join(_normalize_phrase_cached(item)) for item in candidate_set}
        if normalized in normalized_candidates:
            return canonical
    return normalized


def build_ngram_set(tokens: Sequence[str], max_n: int = 3) -> set[str]:
    ngrams = set()
    for n in range(1, max_n + 1):
        for idx in range(len(tokens) - n + 1):
            ngrams.add(" ".join(tokens[idx: idx + n]))
    return ngrams


def build_ngram_index(tokens: Sequence[str], max_n: int = 3) -> Dict[int, set[str]]:
    ngram_index: Dict[int, set[str]] = {size: set() for size in range(1, max_n + 1)}
    for n in range(1, max_n + 1):
        for idx in range(len(tokens) - n + 1):
            ngram_index[n].add(" ".join(tokens[idx: idx + n]))
    return ngram_index


def unique_preserve_order(items: Iterable[str]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(item)
    return ordered


def build_term_variants(term: str) -> List[str]:
    return list(_build_term_variants_cached(term))


@lru_cache(maxsize=2048)
def _build_term_variants_cached(term: str) -> Tuple[str, ...]:
    canonical = canonicalize_term(term)
    variants = [canonical]
    if canonical in SKILL_VARIATIONS:
        variants.extend(SKILL_VARIATIONS[canonical])
    if term.lower() != canonical:
        variants.append(term)
    normalized_variants = []
    seen = set()
    for item in variants:
        normalized = " ".join(normalize_phrase(item))
        if normalized and normalized not in seen:
            seen.add(normalized)
            normalized_variants.append(normalized)
    return tuple(normalized_variants)


def get_role_profile(role_name: Optional[str]) -> Dict[str, List[str]]:
    if not role_name:
        return {k: list(v) for k, v in GENERIC_PROFILE.items()}
    canonical = ROLE_ALIASES.get(role_name, role_name)
    profile = ROLE_PROFILES.get(canonical, GENERIC_PROFILE)
    return {k: list(v) for k, v in profile.items()}


def extract_role_from_job_description(job_description: str) -> Optional[str]:
    if not job_description:
        return None
    normalized_jd = " ".join(normalize_tokens(job_description))
    best_role = None
    best_score = 0
    for role, profile in ROLE_PROFILES.items():
        score = 0
        for term in profile["skills"] + profile["keywords"]:
            normalized_term = " ".join(normalize_phrase(term))
            if normalized_term and normalized_term in normalized_jd:
                score += max(1, len(normalized_term.split()))
        if score > best_score:
            best_role = role
            best_score = score
    return best_role


def collect_expected_keywords(role_name: Optional[str], job_description: str = "") -> List[str]:
    if job_description:
        jd_tokens = [token for token in normalize_tokens(job_description) if token not in STOP_WORDS and len(token) > 2]
        jd_terms = unique_preserve_order(jd_tokens)
        role_hint = extract_role_from_job_description(job_description) or role_name
        profile = get_role_profile(role_hint)
        role_terms = unique_preserve_order(profile["skills"] + profile["keywords"])
        matched_role_terms = [
            term for term in role_terms
            if " ".join(normalize_phrase(term)) in build_ngram_set(jd_tokens)
        ]
        return unique_preserve_order(matched_role_terms + jd_terms)[:20]

    profile = get_role_profile(role_name)
    return unique_preserve_order(profile["skills"] + profile["keywords"])


def _get_fuzzy_candidates(canonical_term: str, ngram_index: Dict[int, set[str]]) -> List[str]:
    term_word_count = max(1, len(canonical_term.split()))
    term_length = len(canonical_term)
    primary_candidates = ngram_index.get(term_word_count, set())
    filtered_candidates = [
        candidate
        for candidate in primary_candidates
        if candidate[:1] == canonical_term[:1] and abs(len(candidate) - term_length) <= 4
    ]

    if len(filtered_candidates) < 8 and term_word_count > 1:
        secondary_candidates = ngram_index.get(term_word_count - 1, set()) | ngram_index.get(term_word_count + 1, set())
        filtered_candidates.extend(
            candidate
            for candidate in secondary_candidates
            if candidate[:1] == canonical_term[:1] and abs(len(candidate) - term_length) <= 4
        )

    if len(filtered_candidates) > MAX_FUZZY_CANDIDATES:
        filtered_candidates = filtered_candidates[:MAX_FUZZY_CANDIDATES]
    return filtered_candidates


def match_terms(tokens: Sequence[str], expected_terms: Sequence[str]) -> Tuple[List[str], List[str], Dict[str, float]]:
    ngram_index = build_ngram_index(tokens)
    token_ngrams = set().union(*ngram_index.values())
    matched: List[str] = []
    missing: List[str] = []
    scores: Dict[str, float] = {}
    for term in expected_terms:
        variants = build_term_variants(term)
        score = 0.0
        for variant in variants:
            if variant in token_ngrams:
                score = max(score, 1.0)

        if score < 1.0:
            canonical = canonicalize_term(term)
            for related in RELATED_SKILL_HINTS.get(canonical, []):
                related_norm = " ".join(normalize_phrase(related))
                if related_norm and related_norm in token_ngrams:
                    score = max(score, 0.7)

        if score < 1.0:
            pieces = max((variant.split() for variant in variants), key=len, default=[])
            if pieces:
                overlap = sum(1 for piece in pieces if piece in tokens)
                partial_score = overlap / len(pieces)
                if partial_score >= 0.6:
                    score = max(score, round(partial_score * 0.85, 2))

        canonical_term = canonicalize_term(term)
        if score < 0.6 and canonical_term not in token_ngrams:
            fuzzy_candidates = _get_fuzzy_candidates(canonical_term, ngram_index)
            similarity = max(
                (
                    SequenceMatcher(None, canonical_term, ngram).ratio()
                    for ngram in fuzzy_candidates
                ),
                default=0.0,
            )
            if similarity >= 0.86:
                score = max(score, 0.65)

        scores[term] = round(score, 2)
        if score >= 0.6:
            matched.append(term)
        else:
            missing.append(term)
    return unique_preserve_order(matched), unique_preserve_order(missing), scores


def extract_resume_skills(resume_text: str, skill_lexicon: Sequence[str]) -> List[str]:
    tokens = normalize_tokens(resume_text)
    token_ngrams = build_ngram_set(tokens)
    found = []
    for skill in skill_lexicon:
        variants = build_term_variants(skill)
        if any(variant in token_ngrams for variant in variants):
            found.append(skill)
            continue
        canonical = canonicalize_term(skill)
        for related in RELATED_SKILL_HINTS.get(canonical, []):
            related_norm = " ".join(normalize_phrase(related))
            if related_norm and related_norm in token_ngrams:
                found.append(skill)
                break
    return unique_preserve_order(found)


def infer_experience_years(resume_text: str) -> Dict[str, object]:
    text = resume_text.lower()
    explicit_matches = [float(match) for match in re.findall(r"(\d{1,2}(?:\.\d+)?)\s*(?:\+?\s*)?(?:years?|yrs)", text)]
    explicit_years = max(explicit_matches) if explicit_matches else 0.0

    range_matches = re.findall(r"\b(20\d{2}|19\d{2})\s*[-–to]+\s*(present|current|20\d{2}|19\d{2})\b", text)
    range_years = 0.0
    parsed_ranges = []
    current_year = datetime.now().year
    for start, end in range_matches:
        start_year = int(start)
        end_year = current_year if end in {"present", "current"} else int(end)
        if end_year >= start_year:
            duration = end_year - start_year
            parsed_ranges.append({"start": start_year, "end": end_year, "years": duration})
            range_years = max(range_years, float(duration))

    inferred_years = max(explicit_years, range_years)
    return {
        "years": round(inferred_years, 1),
        "explicit_year_mentions": explicit_matches,
        "date_ranges": parsed_ranges,
    }


def calculate_ats_score(
    resume_text: str,
    category: Optional[str] = None,
    extracted_skills: Optional[Sequence[str]] = None,
    job_description: str = "",
) -> Dict[str, object]:
    tokens = normalize_tokens(resume_text)
    token_ngrams = build_ngram_set(tokens)
    token_set = set(tokens)
    text_lower = resume_text.lower()

    role_name = extract_role_from_job_description(job_description) or category
    role_profile = get_role_profile(role_name)
    expected_role_skills = unique_preserve_order(role_profile["skills"])
    expected_keywords = collect_expected_keywords(role_name, job_description=job_description)

    resume_skill_lexicon = unique_preserve_order(list(expected_role_skills) + list(extracted_skills or []))
    extracted_skill_list = extract_resume_skills(resume_text, resume_skill_lexicon)
    matched_skills, missing_skills, skill_match_scores = match_terms(tokens, expected_role_skills)
    matched_keywords, missing_keywords, keyword_match_scores = match_terms(tokens, expected_keywords)

    sections = {
        "contact": bool(re.search(r"(email|phone|linkedin|github)", text_lower)),
        "summary": bool(re.search(r"(summary|objective|profile)", text_lower)),
        "experience": bool(re.search(r"(experience|work experience|employment)", text_lower)),
        "skills": bool(re.search(r"(skills|technical skills|expertise|proficiencies?)", text_lower)),
        "education": bool(re.search(r"(education|b\.tech|bachelor|master|degree|diploma|certificate)", text_lower)),
    }
    structure_score = round((sum(sections.values()) / len(sections)) * 20, 2)

    keyword_ratio = sum(keyword_match_scores.values()) / max(len(expected_keywords), 1)
    keywords_score = round(keyword_ratio * 20, 2)

    skill_ratio = sum(skill_match_scores.values()) / max(len(expected_role_skills), 1)
    skills_score = round(skill_ratio * 20, 2)

    experience_info = infer_experience_years(resume_text)
    years = float(experience_info["years"])
    role_min_years = 2.0 if role_name and role_name not in {"HR", "Arts", "Health and fitness"} else 1.0
    experience_ratio = min(years / max(role_min_years, 1.0), 1.0)
    experience_score = round(experience_ratio * 20, 2)

    education_keywords = ["bachelor", "btech", "b tech", "b.e", "degree", "master", "mtech", "computer science", "engineering"]
    matched_education = [term for term in education_keywords if " ".join(normalize_phrase(term)) in token_ngrams]
    education_score = 20.0 if matched_education else 0.0
    if education_score == 0.0 and any(term in token_set for term in ["diploma", "certificate", "certified"]):
        education_score = 10.0

    breakdown = {
        "structure": structure_score,
        "keywords": keywords_score,
        "skills": skills_score,
        "experience": experience_score,
        "education": education_score,
    }
    role_match_pct = round(
        min(
            100.0,
            (
                skill_ratio * 0.55
                + keyword_ratio * 0.25
                + experience_ratio * 0.10
                + (education_score / 20.0) * 0.05
                + (structure_score / 20.0) * 0.05
            ) * 100
        ),
        2,
    )
    total_score = round(min(100.0, sum(breakdown.values())), 2)

    return {
        "role_used": role_name or "General",
        "total_score": total_score,
        "breakdown": breakdown,
        "expected_role_skills": expected_role_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "expected_keywords": expected_keywords,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "extracted_skills": extracted_skill_list,
        "skill_match_pct": round(skill_ratio * 100, 2),
        "role_match_pct": role_match_pct,
        "keyword_match_pct": round(keyword_ratio * 100, 2),
        "experience_years": years,
        "experience_debug": experience_info,
        "sections_found": sections,
        "cleaned_resume_text": " ".join(tokens),
        "tokenized_resume": tokens,
        "keywords_found": len(matched_keywords),
        "skills_count": len(matched_skills),
        "job_description_used": bool(job_description.strip()),
        "skill_match_scores": skill_match_scores,
        "keyword_match_scores": keyword_match_scores,
    }


def check_company_compatibility(resume_text, company_name):
    if company_name not in COMPANY_REQUIREMENTS:
        return {"error": f"Company {company_name} not in database"}

    requirements = COMPANY_REQUIREMENTS[company_name]
    tokens = normalize_tokens(resume_text)
    expected = requirements["keywords"]
    keywords_matched, keywords_missing, keyword_scores = match_terms(tokens, expected)
    score = int((sum(keyword_scores.values()) / max(len(expected), 1)) * 100)

    required_skills_matched, _, _ = match_terms(tokens, requirements["required_skills"])
    nice_skills_matched, _, _ = match_terms(tokens, requirements["nice_skills"])

    return {
        "company": company_name,
        "compatibility_score": score,
        "keywords_matched": keywords_matched,
        "keywords_missing": keywords_missing,
        "keyword_match_scores": keyword_scores,
        "required_skills_matched": required_skills_matched,
        "nice_skills_matched": nice_skills_matched,
        "recommendation": get_company_recommendation(score),
    }


def get_company_recommendation(score):
    if score >= 80:
        return "Excellent fit! Your profile aligns well with company requirements."
    if score >= 60:
        return "Good fit. Highlight the matched technologies and outcomes more clearly."
    if score >= 40:
        return "Moderate fit. Build missing skills and add stronger evidence in the resume."
    return "Not a strong fit yet. Major keyword and skill gaps remain."


def get_top_company_matches(resume_text, top_n=5):
    results = []
    for company in COMPANY_REQUIREMENTS:
        try:
            compat = check_company_compatibility(resume_text, company)
        except Exception:
            continue
        results.append({
            "company": company,
            "score": compat["compatibility_score"],
            "matched_keywords": len(compat["keywords_matched"]),
            "recommendation": compat["recommendation"],
        })
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_n]


def get_ats_improvement_suggestions(resume_text, ats_result):
    suggestions = []
    breakdown = ats_result.get("breakdown", ats_result)

    if breakdown.get("structure", 0) < 15:
        suggestions.append("Structure: add clearly labeled sections for Summary, Experience, Skills, Education, and Contact.")
    if breakdown.get("keywords", 0) < 15:
        missing_keywords = ats_result.get("missing_keywords", [])[:6]
        if missing_keywords:
            suggestions.append(f"Keywords: add role-relevant terms such as {', '.join(missing_keywords)}.")
        else:
            suggestions.append("Keywords: align the resume language more closely with the target role or job description.")
    if breakdown.get("skills", 0) < 15:
        missing_skills = ats_result.get("missing_skills", [])[:6]
        if missing_skills:
            suggestions.append(f"Skills: strengthen the resume with evidence for {', '.join(missing_skills)}.")
        else:
            suggestions.append("Skills: add a stronger role-specific technical stack and project evidence.")
    if breakdown.get("experience", 0) < 15:
        suggestions.append("Experience: make tenure explicit with date ranges and quantify impact in projects or roles.")
    if breakdown.get("education", 0) < 15:
        suggestions.append("Education: explicitly mention degree, branch, and institution.")

    if not suggestions:
        suggestions.append("Great job. The resume aligns well with the target ATS criteria.")

    return suggestions
