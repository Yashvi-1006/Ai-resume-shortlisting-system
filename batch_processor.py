"""
Batch resume processing engine.

Supports mixed batch uploads across CSV, PDF, DOC/DOCX, and TXT files.
Provides parsing, scoring, deterministic ranking, filtering, and
frontend-friendly table/JSON output.
"""

from __future__ import annotations

import math
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import BytesIO
import importlib.util as util
import json
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from ats_analyzer import collect_expected_keywords, get_ats_improvement_suggestions
from file_parser import extract_text_from_file
from src.inference import ResumeClassifier

# Import from root-level resume_analyzer.py explicitly to avoid clashing with src/resume_analyzer.py
_ROOT_DIR = os.path.dirname(__file__)
_SPEC = util.spec_from_file_location("root_resume_analyzer", os.path.join(_ROOT_DIR, "resume_analyzer.py"))
_ROOT_ANALYZER = util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ROOT_ANALYZER)
check_grammar_issues = _ROOT_ANALYZER.check_grammar_issues


ScoreWeights = Dict[str, float]
ProgressCallback = Optional[Callable[[int, int, str], None]]


class DataExtractor:
    """Extract structured candidate data from resume text or CSV rows."""

    COMMON_SKILLS = {
        "programming": [
            "python", "java", "c++", "javascript", "c#", "ruby", "golang", "rust",
            "typescript", "php", "scala", "r", "sql",
        ],
        "frameworks": [
            "django", "flask", "spring", "react", "angular", "vue", "fastapi",
            "node.js", "node", "asp.net", "tensorflow", "pytorch", "scikit-learn",
        ],
        "databases": [
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
            "oracle", "sqlite",
        ],
        "tools": [
            "git", "docker", "kubernetes", "jenkins", "github", "gitlab", "jira",
            "linux", "aws", "azure", "gcp", "tableau", "power bi",
        ],
        "soft_skills": [
            "communication", "leadership", "teamwork", "problem solving",
            "problem-solving", "analytical", "agile", "stakeholder management",
        ],
    }

    RESUME_TEXT_COLUMNS = [
        "resume", "resume_text", "resume content", "content", "profile", "cv",
        "candidate_profile", "resume_str",
    ]
    NAME_COLUMNS = ["name", "candidate_name", "full_name"]
    EMAIL_COLUMNS = ["email", "email_address", "mail"]
    PHONE_COLUMNS = ["phone", "mobile", "contact_number", "phone_number"]
    SKILLS_COLUMNS = ["skills", "technical_skills", "skillset", "core_skills"]
    EXPERIENCE_COLUMNS = ["experience", "years_experience", "experience_years", "total_experience"]
    EDUCATION_COLUMNS = ["education", "highest_education", "degree", "qualification"]

    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        normalized = df.copy()
        normalized.columns = [
            re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")
            for col in normalized.columns
        ]
        return normalized

    @staticmethod
    def clean_text(text: str) -> str:
        if text is None:
            return ""
        cleaned = str(text).replace("\x00", " ")
        cleaned = re.sub(r"\r\n?", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def find_first_value(cls, data: Dict, candidates: Iterable[str], default=""):
        for column in candidates:
            if column in data and pd.notna(data[column]):
                value = str(data[column]).strip()
                if value and value.lower() != "nan":
                    return value
        return default

    @classmethod
    def extract_name(cls, resume_text: str, row_data: Optional[Dict] = None) -> str:
        if row_data:
            row_name = cls.find_first_value(row_data, cls.NAME_COLUMNS)
            if row_name:
                return row_name

        lines = [line.strip() for line in resume_text.strip().split("\n") if line.strip()]
        for line in lines[:6]:
            if len(line) > 80:
                continue
            if any(keyword in line.lower() for keyword in ["summary", "contact", "phone", "email", "linkedin"]):
                continue
            words = line.split()
            if len(words) >= 2 and all(token[:1].isalpha() for token in words[:3]):
                return line
        return "Unknown"

    @classmethod
    def extract_email(cls, resume_text: str, row_data: Optional[Dict] = None) -> str:
        if row_data:
            email = cls.find_first_value(row_data, cls.EMAIL_COLUMNS)
            if email:
                return email
        match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", resume_text)
        return match.group(0) if match else "Not found"

    @classmethod
    def extract_phone(cls, resume_text: str, row_data: Optional[Dict] = None) -> str:
        if row_data:
            phone = cls.find_first_value(row_data, cls.PHONE_COLUMNS)
            if phone:
                return phone
        match = re.search(r"[\+]?\(?\d{1,4}\)?[-\s\.]?\d{3}[-\s\.]?\d{3,4}[-\s\.]?\d{4,6}", resume_text)
        return match.group(0) if match else "Not found"

    @classmethod
    def extract_skills(cls, resume_text: str, row_data: Optional[Dict] = None) -> List[str]:
        found_skills: List[str] = []

        if row_data:
            raw_skills = cls.find_first_value(row_data, cls.SKILLS_COLUMNS)
            if raw_skills:
                parts = [part.strip() for part in re.split(r"[,;/|]", raw_skills) if part.strip()]
                found_skills.extend(parts)

        text_lower = resume_text.lower()
        for skills_list in cls.COMMON_SKILLS.values():
            for skill in skills_list:
                if skill in text_lower and skill not in [s.lower() for s in found_skills]:
                    found_skills.append(skill)

        deduped = []
        seen = set()
        for skill in found_skills:
            normalized = skill.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(normalized.upper() if len(normalized) <= 6 else normalized.title())
        return deduped[:20]

    @classmethod
    def extract_experience_years(cls, resume_text: str, row_data: Optional[Dict] = None) -> float:
        if row_data:
            raw_exp = cls.find_first_value(row_data, cls.EXPERIENCE_COLUMNS)
            if raw_exp:
                numeric_match = re.search(r"\d+(\.\d+)?", raw_exp)
                if numeric_match:
                    return float(numeric_match.group(0))

        matches = re.findall(r"(\d{1,2}(?:\.\d+)?)\s*(?:\+|years?|yrs)", resume_text.lower())
        if matches:
            return float(max(float(match) for match in matches))
        return 0.0

    @classmethod
    def extract_education(cls, resume_text: str, row_data: Optional[Dict] = None) -> str:
        if row_data:
            education = cls.find_first_value(row_data, cls.EDUCATION_COLUMNS)
            if education:
                return education

        education_keywords = {
            "PhD": ["phd", "ph.d", "doctorate"],
            "Master": ["master", "mtech", "mba", "m.tech", "m.s", "ms"],
            "Bachelor": ["b.tech", "bachelor", "btech", "b.e", "bs", "b.s", "b.a"],
            "Diploma": ["diploma"],
            "Certificate": ["certificate", "certified"],
        }
        text_lower = resume_text.lower()
        for education_level, keywords in education_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return education_level
        return "Not specified"

    @staticmethod
    def extract_summary(resume_text: str, length: int = 220) -> str:
        summary_pattern = r"(?:summary|objective|profile)[\s\n]*[:\-]*(.*?)(?:\n\n|\n(?=[A-Z][A-Za-z ]+:?)|$)"
        match = re.search(summary_pattern, resume_text, re.IGNORECASE | re.DOTALL)
        if match:
            summary = re.sub(r"\s+", " ", match.group(1)).strip()
            return summary[:length] + ("..." if len(summary) > length else "")
        flattened = re.sub(r"\s+", " ", resume_text).strip()
        return flattened[:length] + ("..." if len(flattened) > length else "")

    @classmethod
    def extract_resume_text_from_row(cls, row_data: Dict) -> str:
        text = cls.find_first_value(row_data, cls.RESUME_TEXT_COLUMNS)
        if text:
            return cls.clean_text(text)

        fragments = []
        for value in row_data.values():
            if pd.isna(value):
                continue
            text_value = str(value).strip()
            if text_value and text_value.lower() != "nan":
                fragments.append(text_value)
        return cls.clean_text("\n".join(fragments))


class ResumeScorer:
    """Compute ATS, grammar, clarity, and overall scores."""

    DEFAULT_WEIGHTS: ScoreWeights = {
        "ats_score": 0.45,
        "grammar_score": 0.25,
        "clarity_score": 0.30,
    }

    def __init__(self, weights: Optional[ScoreWeights] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    @staticmethod
    def extract_job_keywords(job_description: str, limit: int = 20) -> List[str]:
        return collect_expected_keywords(None, job_description=job_description)[:limit]

    @classmethod
    def calculate_grammar_score(cls, resume_text: str) -> float:
        grammar_result = check_grammar_issues(resume_text)
        severity = grammar_result.get("severity_breakdown", {})
        penalty = (
            severity.get("critical", 0) * 12
            + severity.get("high", 0) * 8
            + severity.get("medium", 0) * 5
            + severity.get("low", 0) * 2
        )

        repeated_spaces_penalty = min(8, len(re.findall(r" {2,}", resume_text)) * 2)
        casing_penalty = 5 if resume_text and resume_text == resume_text.upper() else 0
        score = max(0.0, 100.0 - penalty - repeated_spaces_penalty - casing_penalty)
        return round(score, 1)

    @staticmethod
    def calculate_clarity_score(resume_text: str) -> float:
        score = 0.0
        text_lower = resume_text.lower()

        sections = ["summary", "experience", "skills", "education", "projects", "contact"]
        sections_found = sum(1 for section in sections if section in text_lower)
        score += (sections_found / len(sections)) * 30

        lines = [line.strip() for line in resume_text.split("\n") if line.strip()]
        if lines:
            avg_line_length = sum(len(line) for line in lines) / len(lines)
            if 35 <= avg_line_length <= 110:
                score += 20
            elif avg_line_length <= 140:
                score += 12

        bullet_count = len(re.findall(r"(^|\n)\s*[-*•]", resume_text))
        score += min(20, bullet_count * 2)

        action_verbs = [
            "led", "designed", "implemented", "developed", "created", "managed",
            "built", "achieved", "improved", "optimized", "delivered", "launched",
        ]
        action_verb_count = sum(1 for verb in action_verbs if re.search(rf"\b{re.escape(verb)}\b", text_lower))
        score += min(15, action_verb_count * 1.5)

        quantified = len(re.findall(r"\b\d+%|\b\d+\+|\b\d+\s*(?:million|thousand|users|clients|projects)\b", text_lower))
        score += min(15, quantified * 3)

        return round(min(100.0, score), 1)

    def calculate_overall_score(self, ats_score: float, grammar_score: float, clarity_score: float) -> float:
        overall = (
            ats_score * self.weights["ats_score"]
            + grammar_score * self.weights["grammar_score"]
            + clarity_score * self.weights["clarity_score"]
        )
        return round(min(100.0, overall), 1)


class BatchProcessor:
    """Shared batch processor for API and UI layers."""

    def __init__(self, weights: Optional[ScoreWeights] = None):
        self.extractor = DataExtractor()
        self.scorer = ResumeScorer(weights=weights)
        self._classifier: Optional[ResumeClassifier] = None

    def get_classifier(self) -> ResumeClassifier:
        if self._classifier is None:
            self._classifier = ResumeClassifier()
        return self._classifier

    def _coerce_file_to_memory(self, uploaded_file):
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        buffer = BytesIO(file_bytes)
        buffer.name = getattr(uploaded_file, "name", "uploaded_file")
        return buffer

    def _process_csv_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str,
        job_description: str = "",
    ) -> List[Dict]:
        normalized_df = self.extractor.normalize_columns(df).fillna("")
        results: List[Dict] = []

        for idx, row in normalized_df.iterrows():
            row_data = row.to_dict()
            resume_text = self.extractor.extract_resume_text_from_row(row_data)
            if len(resume_text) < 20:
                results.append({
                    "name": self.extractor.find_first_value(row_data, self.extractor.NAME_COLUMNS, default=f"Row {idx + 1}"),
                    "source": source_name,
                    "source_type": "csv",
                    "source_row": idx + 1,
                    "error": "Resume text too short or empty",
                    "overall_score": 0.0,
                })
                continue

            results.append(
                self.process_single_resume(
                    resume_text=resume_text,
                    source_name=source_name,
                    source_type="csv",
                    source_row=idx + 1,
                    job_description=job_description,
                    row_data=row_data,
                )
            )

        return results

    def process_csv_file(self, file_obj, source_name: Optional[str] = None, job_description: str = "") -> List[Dict]:
        try:
            file_obj.seek(0)
            df = pd.read_csv(file_obj)
            return self._process_csv_dataframe(df, source_name or getattr(file_obj, "name", "uploaded.csv"), job_description=job_description)
        except Exception as exc:
            raise Exception(f"Error processing CSV: {exc}") from exc

    def process_single_resume(
        self,
        resume_text: str,
        source_name: str = "",
        source_type: str = "file",
        source_row: Optional[int] = None,
        job_description: str = "",
        row_data: Optional[Dict] = None,
    ) -> Dict:
        try:
            resume_text = self.extractor.clean_text(resume_text)
            name = self.extractor.extract_name(resume_text, row_data=row_data)
            email = self.extractor.extract_email(resume_text, row_data=row_data)
            phone = self.extractor.extract_phone(resume_text, row_data=row_data)
            skills = self.extractor.extract_skills(resume_text, row_data=row_data)
            experience = self.extractor.extract_experience_years(resume_text, row_data=row_data)
            education = self.extractor.extract_education(resume_text, row_data=row_data)
            summary = self.extractor.extract_summary(resume_text)
            prediction = self.get_classifier().predict_single(resume_text, job_description=job_description)
            ats_analysis = prediction.get("ats_analysis", {})
            ats_score = float(ats_analysis.get("total_score", 0))
            ats_breakdown = dict(ats_analysis.get("breakdown", {}))
            matched_keywords = prediction.get("matched_keywords", [])
            grammar_score = self.scorer.calculate_grammar_score(resume_text)
            clarity_score = self.scorer.calculate_clarity_score(resume_text)
            overall_score = self.scorer.calculate_overall_score(ats_score, grammar_score, clarity_score)

            suggestions = get_ats_improvement_suggestions(
                resume_text,
                ats_analysis,
            )

            return {
                "rank": None,
                "name": name,
                "email": email,
                "phone": phone,
                "education": education,
                "experience_years": round(experience, 1),
                "skills": prediction.get("extracted_skills", skills),
                "summary": summary,
                "relevant_keywords": matched_keywords,
                "ats_score": ats_score,
                "grammar_score": grammar_score,
                "clarity_score": clarity_score,
                "overall_score": overall_score,
                "score_weights": self.scorer.weights.copy(),
                "ats_breakdown": ats_breakdown,
                "predicted_category": prediction.get("predicted_category"),
                "top_predictions": prediction.get("top_predictions", []),
                "skill_match_pct": prediction.get("skill_score", 0),
                "matched_skills": prediction.get("matched_skills", []),
                "missing_skills": prediction.get("missing_skills", []),
                "expected_role_skills": prediction.get("expected_role_skills", []),
                "expected_keywords": prediction.get("expected_keywords", []),
                "matched_keywords": prediction.get("matched_keywords", []),
                "missing_keywords": prediction.get("missing_keywords", []),
                "category_reason": prediction.get("category_reason", ""),
                "debug": prediction.get("debug", {}),
                "suggestions": suggestions,
                "source": source_name,
                "source_type": source_type,
                "source_row": source_row,
                "resume_text": resume_text,
            }
        except Exception as exc:
            return {
                "rank": None,
                "name": "Error",
                "source": source_name,
                "source_type": source_type,
                "source_row": source_row,
                "error": str(exc),
                "overall_score": 0.0,
            }

    def _process_uploaded_file(self, uploaded_file, job_description: str = "") -> Tuple[List[Dict], List[str]]:
        filename = getattr(uploaded_file, "name", "uploaded_file")
        file_extension = filename.split(".")[-1].lower()

        try:
            file_buffer = self._coerce_file_to_memory(uploaded_file)
            if file_extension == "csv":
                results = self.process_csv_file(file_buffer, source_name=filename, job_description=job_description)
                return results, [f"Processed CSV {filename} with {len(results)} candidate rows"]

            if file_extension in {"pdf", "docx", "doc", "txt"}:
                text, _, success, message = extract_text_from_file(file_buffer)
                if success:
                    result = self.process_single_resume(
                        resume_text=text,
                        source_name=filename,
                        source_type=file_extension,
                        job_description=job_description,
                    )
                    return [result], [message]
                return [], [message]

            return [], [f"Unsupported file type: {filename}"]
        except Exception as exc:
            return [], [f"Error processing {filename}: {exc}"]

    def process_multiple_files(
        self,
        uploaded_files,
        job_description: str = "",
        progress_callback: ProgressCallback = None,
        max_workers: int = 4,
    ) -> Tuple[List[Dict], List[str]]:
        all_results: List[Dict] = []
        messages: List[str] = []
        files = list(uploaded_files or [])
        total_files = len(files)

        if total_files == 0:
            return [], ["No files provided"]

        if progress_callback:
            progress_callback(0, total_files, "Preparing batch processing")

        worker_count = max(1, min(max_workers, total_files))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self._process_uploaded_file, uploaded_file, job_description): uploaded_file
                for uploaded_file in files
            }
            completed = 0
            for future in as_completed(futures):
                results, file_messages = future.result()
                all_results.extend(results)
                messages.extend(file_messages)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_files, f"Processed {completed}/{total_files} files")

        return all_results, messages

    @staticmethod
    def _deterministic_sort_key(result: Dict, sort_by: str) -> Tuple:
        metric_value = result.get(sort_by, 0)
        return (
            -(metric_value or 0),
            -(result.get("ats_score", 0) or 0),
            -(result.get("grammar_score", 0) or 0),
            -(result.get("clarity_score", 0) or 0),
            -(result.get("experience_years", 0) or 0),
            str(result.get("name", "")).lower(),
            str(result.get("source", "")).lower(),
            result.get("source_row") or math.inf,
        )

    def rank_resumes(self, results: List[Dict], sort_by: str = "overall_score") -> List[Dict]:
        valid_results = [result.copy() for result in results if "error" not in result]
        valid_results.sort(key=lambda result: self._deterministic_sort_key(result, sort_by))
        for rank, result in enumerate(valid_results, 1):
            result["rank"] = rank
        return valid_results

    def filter_resumes(
        self,
        results: List[Dict],
        min_ats: float = 0,
        min_grammar: float = 0,
        min_clarity: float = 0,
        min_experience: float = 0,
        search_term: str = "",
    ) -> List[Dict]:
        normalized_search = search_term.strip().lower()
        filtered: List[Dict] = []

        for result in results:
            if "error" in result:
                continue
            if result.get("ats_score", 0) < min_ats:
                continue
            if result.get("grammar_score", 0) < min_grammar:
                continue
            if result.get("clarity_score", 0) < min_clarity:
                continue
            if result.get("experience_years", 0) < min_experience:
                continue

            if normalized_search:
                haystack = " ".join(
                    [
                        str(result.get("name", "")),
                        " ".join(result.get("skills", [])),
                        str(result.get("summary", "")),
                    ]
                ).lower()
                if normalized_search not in haystack:
                    continue

            filtered.append(result)

        return filtered

    @staticmethod
    def to_table_rows(results: List[Dict]) -> List[Dict]:
        return [
            {
                "Rank": result.get("rank"),
                "Name": result.get("name", "Unknown"),
                "ATS Score": result.get("ats_score", 0),
                "Grammar Score": result.get("grammar_score", 0),
                "Clarity Score": result.get("clarity_score", 0),
                "Overall Score": result.get("overall_score", 0),
                "Skills": ", ".join(result.get("skills", [])),
                "Experience": result.get("experience_years", 0),
                "Education": result.get("education", "Not specified"),
                "Source": result.get("source", ""),
            }
            for result in results
        ]

    def build_response(
        self,
        ranked_results: List[Dict],
        raw_results: Optional[List[Dict]] = None,
        messages: Optional[List[str]] = None,
        filters: Optional[Dict] = None,
        job_description: str = "",
    ) -> Dict:
        raw_results = raw_results or ranked_results
        messages = messages or []
        filters = filters or {}
        failed_results = [result for result in raw_results if "error" in result]

        return {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_processed": len(raw_results),
                "successful": len([result for result in raw_results if "error" not in result]),
                "failed": len(failed_results),
                "job_description_keywords": self.scorer.extract_job_keywords(job_description),
                "score_weights": self.scorer.weights.copy(),
                "filters": filters,
            },
            "table": self.to_table_rows(ranked_results),
            "results": ranked_results,
            "messages": messages,
            "errors": failed_results,
        }

    def generate_report(self, response_payload: Dict, filename: Optional[str] = None) -> str:
        report_json = json.dumps(response_payload, indent=2)
        if filename:
            with open(filename, "w", encoding="utf-8") as file_handle:
                file_handle.write(report_json)
        return report_json
