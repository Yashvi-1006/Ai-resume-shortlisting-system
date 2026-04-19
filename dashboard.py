"""
AI Resume Shortlisting System - Streamlit Dashboard
Optimized for responsiveness with cached compute paths and session-backed UI state.
"""

from __future__ import annotations

import importlib.util as util
import io
import os
import sys
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import streamlit as st

# Add root directory to path first (before src)
ROOT_DIR = os.path.dirname(__file__)
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ats_analyzer import (
    calculate_ats_score,
    check_company_compatibility,
    get_ats_improvement_suggestions,
    get_top_company_matches,
)
from batch_processor import BatchProcessor
from file_parser import extract_text_from_file
from src.inference import ResumeClassifier

# Import from root level resume_analyzer.py explicitly to avoid confusion with src/resume_analyzer.py
SPEC = util.spec_from_file_location("root_resume_analyzer", os.path.join(ROOT_DIR, "resume_analyzer.py"))
ROOT_ANALYZER = util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROOT_ANALYZER)

check_grammar_issues = ROOT_ANALYZER.check_grammar_issues
get_btech_cse_specific_suggestions = ROOT_ANALYZER.get_btech_cse_specific_suggestions
get_quality_score = ROOT_ANALYZER.get_quality_score

CLASSIFIER_CACHE_VERSION = "2026-04-19-performance-v1"
SESSION_DEFAULTS = {
    "classifier": None,
    "system_ready": False,
    "is_btech_cse": False,
    "single_resume_text": "",
    "single_analysis_bundle": None,
    "single_analysis_source": "",
    "single_upload_message": "",
    "single_upload_success": False,
    "batch_results_ready": False,
    "batch_all_results": [],
    "batch_ranked_results": [],
    "batch_filtered_results": [],
    "batch_messages": [],
    "batch_job_description": "",
}

SAMPLE_RESUMES = {
    "Data Scientist": """John Doe - Senior Data Scientist
Skills: Python, Machine Learning, TensorFlow, Scikit-learn, SQL, Pandas, NumPy
Experience: 7 years in data science and AI projects""",
    "Python Developer": """Jane Smith - Python Developer
Skills: Python, Django, FastAPI, PostgreSQL, Docker, REST APIs
Experience: 5 years in web development""",
    "Java Developer": """Mike Johnson - Java Developer
Skills: Java, Spring Boot, Microservices, REST API, MySQL
Experience: 8 years enterprise Java development""",
    "HR Manager": """Sarah Williams - HR Manager
Skills: Recruitment, Employee Relations, Compensation, Training, HRIS
Experience: 6 years in HR management""",
}

SORT_OPTIONS = {
    "Overall Score": "overall_score",
    "ATS Score": "ats_score",
    "Grammar Score": "grammar_score",
    "Clarity Score": "clarity_score",
    "Experience": "experience_years",
}


def init_session_state():
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _make_named_buffer(file_name: str, file_bytes: bytes) -> io.BytesIO:
    buffer = io.BytesIO(file_bytes)
    buffer.name = file_name
    buffer.seek(0)
    return buffer


def serialize_uploaded_file(uploaded_file) -> Tuple[str, bytes]:
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    return uploaded_file.name, file_bytes


def serialize_uploaded_files(uploaded_files) -> Tuple[Tuple[str, bytes], ...]:
    return tuple(serialize_uploaded_file(uploaded_file) for uploaded_file in (uploaded_files or []))


@st.cache_resource
def load_classifier(cache_version: str = CLASSIFIER_CACHE_VERSION):
    return ResumeClassifier()


@st.cache_resource
def get_batch_processor(cache_version: str = CLASSIFIER_CACHE_VERSION):
    return BatchProcessor()


@st.cache_data(show_spinner=False, ttl=300)
def extract_text_from_uploaded_file(file_name: str, file_bytes: bytes):
    return extract_text_from_file(_make_named_buffer(file_name, file_bytes))


@st.cache_data(show_spinner=False, ttl=300)
def analyze_resume_cached(resume_text: str, cache_version: str = CLASSIFIER_CACHE_VERSION):
    classifier = load_classifier(cache_version)
    result = classifier.predict_single(resume_text)
    if result.get("error"):
        return result

    ats_result = result.get("ats_analysis") or calculate_ats_score(
        resume_text,
        category=result.get("predicted_category"),
        extracted_skills=result.get("extracted_skills", []),
    )
    quality_result = get_quality_score(resume_text)
    grammar_result = check_grammar_issues(resume_text)

    try:
        top_companies = get_top_company_matches(resume_text, top_n=5)
    except Exception:
        top_companies = []

    return {
        "prediction": result,
        "ats_result": ats_result,
        "quality_result": quality_result,
        "grammar_result": grammar_result,
        "top_companies": top_companies,
    }


@st.cache_data(show_spinner=False, ttl=300)
def process_batch_files_cached(
    serialized_files: Tuple[Tuple[str, bytes], ...],
    job_description: str,
    cache_version: str = CLASSIFIER_CACHE_VERSION,
):
    processor = get_batch_processor(cache_version)
    uploaded_files = [_make_named_buffer(file_name, file_bytes) for file_name, file_bytes in serialized_files]
    all_results, messages = processor.process_multiple_files(
        uploaded_files,
        job_description=job_description,
        progress_callback=None,
    )
    ranked_results = processor.rank_resumes(all_results, sort_by="overall_score") if all_results else []
    return {
        "all_results": all_results,
        "ranked_results": ranked_results,
        "messages": messages,
    }


@st.cache_data(show_spinner=False, ttl=300)
def filter_batch_results_cached(
    ranked_results: List[Dict],
    min_ats: float,
    min_grammar: float,
    min_clarity: float,
    min_experience: float,
    search_term: str,
    sort_field: str,
    descending: bool,
):
    processor = get_batch_processor()
    filtered_results = processor.filter_resumes(
        list(ranked_results),
        min_ats=min_ats,
        min_grammar=min_grammar,
        min_clarity=min_clarity,
        min_experience=min_experience,
        search_term=search_term,
    )
    filtered_results = [result.copy() for result in filtered_results]
    filtered_results.sort(key=lambda item: item.get(sort_field, 0), reverse=descending)
    for idx, candidate in enumerate(filtered_results, 1):
        candidate["rank"] = idx
    return filtered_results


@st.cache_data(show_spinner=False, ttl=300)
def build_results_table_cached(filtered_results: List[Dict], cache_version: str = CLASSIFIER_CACHE_VERSION):
    processor = get_batch_processor(cache_version)
    return pd.DataFrame(processor.to_table_rows(filtered_results))


def ensure_system_ready():
    if st.session_state.system_ready:
        return

    with st.spinner("Loading AI model... This may take a moment"):
        try:
            classifier = load_classifier()
            st.session_state.classifier = classifier
            st.session_state.system_ready = True
        except Exception as exc:
            st.error(f"Error loading model: {exc}")


def clear_batch_results():
    st.session_state.batch_results_ready = False
    st.session_state.batch_all_results = []
    st.session_state.batch_ranked_results = []
    st.session_state.batch_filtered_results = []
    st.session_state.batch_messages = []
    st.session_state.batch_job_description = ""
    st.session_state.batch_job_description_input = ""


def render_sidebar():
    with st.sidebar:
        st.title("Settings")
        st.session_state.is_btech_cse = st.checkbox(
            "BTech CSE Candidate",
            value=st.session_state.is_btech_cse,
            help="Enable BTech Computer Science specific analysis",
        )

        st.divider()
        st.subheader("System Info")
        if st.session_state.system_ready:
            st.metric("Status", "Ready")
            st.metric("Model", "Logistic Regression")
            st.metric("Accuracy", "99.48%")
            st.metric("Categories", "25")
        else:
            st.warning("Loading system...")


def handle_single_file_upload(uploaded_file) -> str:
    if uploaded_file is None:
        st.session_state.single_upload_message = ""
        st.session_state.single_upload_success = False
        return ""

    file_name, file_bytes = serialize_uploaded_file(uploaded_file)
    text, _, success, message = extract_text_from_uploaded_file(file_name, file_bytes)
    st.session_state.single_upload_message = message
    st.session_state.single_upload_success = success
    return text if success else ""


def submit_single_resume_analysis(resume_text: str):
    clean_text = resume_text.strip()
    if not clean_text:
        st.session_state.single_analysis_bundle = None
        st.error("Please enter resume text, upload a file, or select a sample.")
        return

    with st.spinner("Analyzing resume..."):
        analysis_bundle = analyze_resume_cached(clean_text)
        if analysis_bundle.get("error"):
            st.session_state.single_analysis_bundle = None
            st.error(analysis_bundle["error"])
            return

    st.session_state.single_resume_text = clean_text
    st.session_state.single_analysis_source = clean_text
    st.session_state.single_analysis_bundle = analysis_bundle


def render_single_resume_tab():
    st.header("Analyze Single Resume")

    if not st.session_state.system_ready:
        st.warning("Please initialize the system first using the sidebar.")
        return

    with st.form("single_resume_form", clear_on_submit=False):
        input_method = st.radio(
            "Choose input method:",
            ["Text Input", "Upload File"],
            horizontal=True,
        )

        resume_text = ""
        if input_method == "Text Input":
            col1, col2 = st.columns([2, 1])
            with col1:
                resume_text = st.text_area(
                    "Enter Resume Text:",
                    height=300,
                    value=st.session_state.single_resume_text,
                    placeholder=(
                        "Paste resume content here...\n\nExample:\nJohn Doe - Python Developer\n"
                        "Skills: Python, Django, SQL, REST APIs\nExperience: 5 years in software development"
                    ),
                )
            with col2:
                st.subheader("Quick Actions")
                selected_sample = st.selectbox(
                    "Or use a sample resume:",
                    ["Select..."] + list(SAMPLE_RESUMES.keys()),
                )
                if selected_sample != "Select...":
                    resume_text = SAMPLE_RESUMES[selected_sample]
        else:
            st.subheader("Upload Resume File")
            uploaded_file = st.file_uploader(
                "Choose a resume file (PDF, DOCX, or TXT)",
                type=["pdf", "docx", "doc", "txt"],
                help="Supported formats: PDF, DOCX, DOC, TXT",
            )
            resume_text = handle_single_file_upload(uploaded_file)

        submitted = st.form_submit_button("Analyze Resume", use_container_width=True, type="primary")

    if st.session_state.single_upload_message:
        if st.session_state.single_upload_success:
            st.success(st.session_state.single_upload_message)
            with st.expander("Preview extracted text"):
                preview_text = resume_text or st.session_state.single_resume_text
                st.text(preview_text[:500] + "..." if len(preview_text) > 500 else preview_text)
        else:
            st.error(st.session_state.single_upload_message)

    if submitted:
        submit_single_resume_analysis(resume_text)

    analysis_bundle = st.session_state.single_analysis_bundle
    if not analysis_bundle:
        return

    render_single_resume_results(st.session_state.single_resume_text, analysis_bundle)


def render_single_resume_results(resume_text: str, analysis_bundle: Dict):
    result = analysis_bundle["prediction"]
    ats_result = analysis_bundle["ats_result"]
    quality_result = analysis_bundle["quality_result"]
    grammar_result = analysis_bundle["grammar_result"]
    top_companies = analysis_bundle["top_companies"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Best-Fit Role", result["predicted_category"], "OK")
    with col2:
        skill_score = result.get("role_match_score", result["skill_score"])
        st.metric("Role Match", f"{skill_score:.1f}%", "Match")
    with col3:
        st.metric("Skills Found", len(result["extracted_skills"]), "Skills")

    st.divider()
    st.subheader("Resume Skills Detected")
    if result["extracted_skills"]:
        st.info(f"Detected in Resume: {', '.join(result['extracted_skills'])}")
    else:
        st.warning("No role-relevant skills were detected in the resume text.")

    st.divider()
    st.header("ATS Analysis")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("ATS Score", f"{ats_result['total_score']}/100")
    with col2:
        st.metric("Resume Quality", f"{quality_result['total_score']}/100")
    with col3:
        grammar_score = max(0, 100 - grammar_result["total_issues"] * 3)
        st.metric("Grammar Score", f"{grammar_score}/100")
    with col4:
        avg_score = (ats_result["total_score"] + quality_result["total_score"] + grammar_score) / 3
        readiness = "High" if avg_score >= 80 else "Medium" if avg_score >= 60 else "Low"
        st.metric("Overall Readiness", f"{avg_score:.0f}%", readiness)

    analysis_tab1, analysis_tab2, analysis_tab3, analysis_tab4 = st.tabs(
        ["ATS Score", "Quality & Grammar", "Company Match", "Improve Resume"]
    )

    with analysis_tab1:
        st.subheader("ATS Score Breakdown")
        st.caption(f"Role used for ATS scoring: {ats_result['role_used']}")

        metric_cols = st.columns(5)
        keys = ["structure", "keywords", "skills", "experience", "education"]
        labels = ["Structure", "Keywords", "Skills", "Experience", "Education"]
        for column, key, label in zip(metric_cols, keys, labels):
            with column:
                st.metric(label, f"{ats_result['breakdown'][key]}/20")

        st.divider()
        col1, col2 = st.columns([2, 1])
        with col1:
            breakdown_data = pd.DataFrame(
                [{"Category": label, "Score": ats_result["breakdown"][key]} for label, key in zip(labels, keys)]
            )
            st.bar_chart(breakdown_data.set_index("Category"), height=400)
        with col2:
            st.markdown("### Match Summary")
            st.metric("Matched Keywords", len(ats_result["matched_keywords"]))
            st.metric("Matched Role Skills", len(ats_result["matched_skills"]))
            st.metric("Role Match", f"{result.get('role_match_score', ats_result['skill_match_pct']):.1f}%")
            st.metric("Role Skill Match", f"{ats_result['skill_match_pct']:.1f}%")
            st.metric("Keyword Match", f"{ats_result['keyword_match_pct']:.1f}%")

        st.divider()
        role_col1, role_col2 = st.columns(2)
        with role_col1:
            st.markdown("### Expected vs Matched Skills")
            st.write(f"**Expected:** {', '.join(result['expected_role_skills']) if result['expected_role_skills'] else 'N/A'}")
            st.write(f"**Matched:** {', '.join(result['matched_skills']) if result['matched_skills'] else 'None'}")
            st.write(f"**Missing:** {', '.join(result['missing_skills']) if result['missing_skills'] else 'None'}")
        with role_col2:
            st.markdown("### Expected vs Matched Keywords")
            st.write(f"**Expected:** {', '.join(result['expected_keywords']) if result['expected_keywords'] else 'N/A'}")
            st.write(f"**Matched:** {', '.join(result['matched_keywords']) if result['matched_keywords'] else 'None'}")
            st.write(f"**Missing:** {', '.join(result['missing_keywords']) if result['missing_keywords'] else 'None'}")

    with analysis_tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Resume Quality Breakdown")
            quality_breakdown = pd.DataFrame(
                [
                    {"Metric": "Completeness", "Score": quality_result["score_breakdown"]["completeness"]},
                    {"Metric": "Length", "Score": quality_result["score_breakdown"]["length"]},
                    {"Metric": "Grammar", "Score": quality_result["score_breakdown"]["grammar"]},
                    {"Metric": "Contact", "Score": quality_result["score_breakdown"]["contact"]},
                    {"Metric": "Achievements", "Score": quality_result["score_breakdown"]["achievements"]},
                    {"Metric": "Verbs", "Score": quality_result["score_breakdown"]["action_verbs"]},
                ]
            )
            st.bar_chart(quality_breakdown.set_index("Metric"))
        with col2:
            st.subheader("Resume Writing Metrics")
            metrics = quality_result["metrics"]
            st.metric("Word Count", metrics["word_count"])
            st.metric("Section Completeness", f"{metrics['sections_completeness']['score']}%")
            st.metric("Action Verbs", metrics["action_verbs_used"])
            st.metric("Quantified Achievements", metrics["quantifiable_achievements"])
            st.metric("Length", metrics["length_assessment"]["status"])

        if grammar_result["total_issues"] > 0:
            st.divider()
            st.subheader("Grammar Issues")
            for issue in grammar_result["issues"][:3]:
                st.warning(f"**{issue['type']}** (Line {issue['line']})\n\n{issue['issue']}")
                if issue.get("suggestion"):
                    st.info(f"Try: {issue['suggestion']}")

        st.divider()
        st.subheader("Why This Role Was Chosen")
        st.write(result.get("category_reason", "Highest classifier probability"))
        top_pred_df = pd.DataFrame(result.get("top_predictions", []))
        if not top_pred_df.empty:
            top_pred_df = top_pred_df.rename(
                columns={"category": "Role", "confidence_score": "Confidence %", "probability": "Probability"}
            )
            st.dataframe(top_pred_df, use_container_width=True, hide_index=True)
        if result.get("influential_features"):
            st.caption("Top model features: " + ", ".join(item["feature"] for item in result["influential_features"]))

    with analysis_tab3:
        st.subheader("Company Alignment Snapshot")
        company_data = [
            {
                "Company": company["company"],
                "Match %": company["score"],
                "Keywords": company["matched_keywords"],
            }
            for company in top_companies
        ]
        st.dataframe(pd.DataFrame(company_data), use_container_width=True, hide_index=True)

        if top_companies:
            st.divider()
            st.subheader("Detailed Analysis by Company")
            selected_company = st.selectbox(
                "Select company for details:",
                [company["company"] for company in top_companies],
                key="single_company_select",
            )
            comp_details = check_company_compatibility(resume_text, selected_company)
            col1, col2 = st.columns(2)
            with col1:
                st.metric(selected_company, f"{comp_details['compatibility_score']}%", "Match Score")
                st.markdown(comp_details["recommendation"])
            with col2:
                if comp_details["required_skills_matched"]:
                    st.success(f"Required: {', '.join(comp_details['required_skills_matched'][:3])}")
                if comp_details["nice_skills_matched"]:
                    st.info(f"Nice-to-have: {', '.join(comp_details['nice_skills_matched'][:2])}")
                if comp_details["keywords_missing"]:
                    st.warning(f"Missing: {', '.join(comp_details['keywords_missing'][:3])}")

    with analysis_tab4:
        st.subheader("How to Improve This Resume")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### ATS Improvement Actions")
            for tip in get_ats_improvement_suggestions(resume_text, ats_result):
                st.write(tip)

            if st.session_state.is_btech_cse:
                st.divider()
                st.markdown("### BTech CSE Specific")
                for tip in get_btech_cse_specific_suggestions(resume_text):
                    st.write(tip)
        with col2:
            st.markdown("### Score Summary")
            scores_dict = {
                "ATS": ats_result["total_score"],
                "Quality": quality_result["total_score"],
                "Grammar": max(0, 100 - grammar_result["total_issues"] * 3),
            }
            for metric, score in scores_dict.items():
                st.metric(metric, f"{score:.0f}")

            st.divider()
            avg_score = sum(scores_dict.values()) / len(scores_dict)
            signal = "HIGH" if avg_score >= 80 else "MEDIUM" if avg_score >= 60 else "LOW"
            st.metric("Shortlisting Signal", signal, f"{avg_score:.0f}%")

    with st.expander("Technical Debug Panel", expanded=False):
        debug = result.get("debug", {})
        st.write("**Cleaned Resume Text**")
        st.code(debug.get("cleaned_resume_text", ""), language="text")
        st.write("**Tokenized Resume**")
        st.code(", ".join(debug.get("tokenized_resume", [])), language="text")
        st.write("**Expected Role Skills**")
        st.write(debug.get("expected_role_skills", []))
        st.write("**Matched Skills**")
        st.write(debug.get("matched_skills", []))
        st.write("**Missing Skills**")
        st.write(debug.get("missing_skills", []))
        st.write("**Expected Keywords**")
        st.write(debug.get("expected_keywords", []))
        st.write("**Matched Keywords**")
        st.write(debug.get("matched_keywords", []))
        st.write("**Missing Keywords**")
        st.write(debug.get("missing_keywords", []))
        st.write("**Category Prediction Scores**")
        st.json(debug.get("category_prediction_scores", {}))
        st.write("**Influential Features**")
        st.write(debug.get("influential_features", []))
        st.write("**Experience Debug**")
        st.json(debug.get("experience_debug", {}))
        st.write("**Skill Match Scores**")
        st.json(debug.get("skill_match_scores", {}))
        st.write("**Keyword Match Scores**")
        st.json(debug.get("keyword_match_scores", {}))


def process_batch_submission(uploaded_files, job_description: str):
    if not uploaded_files:
        st.error("Please upload at least one file before processing.")
        return

    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    serialized_files = serialize_uploaded_files(uploaded_files)

    try:
        status_placeholder.info("Processing uploaded resumes. Large CSV files may take a few minutes on first run.")
        progress_bar.progress(15)
        with st.spinner("Processing resumes..."):
            payload = process_batch_files_cached(serialized_files, job_description)
        progress_bar.progress(85)
        status_placeholder.info("Scoring and ranking candidates")

        all_results = payload["all_results"]
        ranked_results = payload["ranked_results"]
        messages = payload["messages"]

        st.session_state.batch_all_results = all_results
        st.session_state.batch_ranked_results = ranked_results
        st.session_state.batch_filtered_results = ranked_results
        st.session_state.batch_messages = messages
        st.session_state.batch_job_description = job_description
        st.session_state.batch_results_ready = bool(ranked_results)

        if ranked_results:
            progress_bar.progress(100)
            status_placeholder.success("Batch processing completed")
        else:
            st.error("No resumes were processed successfully.")
    except Exception as exc:
        st.error(f"Error during batch processing: {exc}")
    finally:
        progress_bar.empty()
        status_placeholder.empty()


def render_batch_results():
    ranked_results = st.session_state.batch_ranked_results
    if not ranked_results:
        return

    if st.session_state.batch_messages:
        with st.expander("Processing Details", expanded=False):
            for message in st.session_state.batch_messages:
                lowered = message.lower()
                if "processed" in lowered or "success" in lowered:
                    st.success(message)
                elif "error" in lowered or "unsupported" in lowered:
                    st.error(message)
                else:
                    st.info(message)

    st.success(f"Successfully processed {len(ranked_results)} resumes.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Processed", len(ranked_results))
    with col2:
        avg_score = sum(result.get("overall_score", 0) for result in ranked_results) / len(ranked_results)
        st.metric("Average Score", f"{avg_score:.1f}/100")
    with col3:
        top_resume = max(ranked_results, key=lambda item: item.get("overall_score", 0))
        st.metric("Top Score", f"{top_resume.get('overall_score', 0):.1f}/100")
    with col4:
        avg_exp = sum(result.get("experience_years", 0) for result in ranked_results) / len(ranked_results)
        st.metric("Avg Experience", f"{avg_exp:.1f} years")

    st.divider()
    st.subheader("Filter & Sort Results")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        min_ats = st.slider("Min ATS Score:", 0, 100, 0, key="batch_min_ats")
    with filter_col2:
        min_grammar = st.slider("Min Grammar Score:", 0, 100, 0, key="batch_min_grammar")
    with filter_col3:
        min_clarity = st.slider("Min Clarity Score:", 0, 100, 0, key="batch_min_clarity")
    with filter_col4:
        min_experience = st.slider("Min Experience (years):", 0, 20, 0, key="batch_min_experience")

    sort_col1, sort_col2, search_col = st.columns([1, 1, 2])
    with sort_col1:
        sort_by_label = st.selectbox("Sort by:", list(SORT_OPTIONS.keys()), key="batch_sort_by")
    with sort_col2:
        sort_order = st.radio("Order:", ["Highest First", "Lowest First"], horizontal=True, key="batch_sort_order")
    with search_col:
        search_term = st.text_input("Search by name or skills:", value="", key="batch_search_term")

    filtered_results = filter_batch_results_cached(
        ranked_results,
        min_ats=min_ats,
        min_grammar=min_grammar,
        min_clarity=min_clarity,
        min_experience=min_experience,
        search_term=search_term,
        sort_field=SORT_OPTIONS[sort_by_label],
        descending=(sort_order == "Highest First"),
    )
    st.session_state.batch_filtered_results = filtered_results

    st.subheader(f"Results ({len(filtered_results)} candidates)")
    results_df = build_results_table_cached(filtered_results)
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Detailed Candidate Views")
    if not filtered_results:
        st.warning("No candidates match the selected filters.")
        return

    selected_rank = st.selectbox(
        "Select candidate to view details:",
        range(1, min(11, len(filtered_results) + 1)),
        key="batch_selected_rank",
        format_func=lambda idx: f"Rank #{idx}: {filtered_results[idx - 1].get('name', 'Unknown')}",
    )
    candidate = filtered_results[selected_rank - 1]

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"### {candidate.get('name', 'Unknown')}")
        st.write(f"**Email:** {candidate.get('email', 'N/A')}")
        st.write(f"**Phone:** {candidate.get('phone', 'N/A')}")
    with col2:
        st.metric("Education", candidate.get("education", "N/A"))
    with col3:
        st.metric("Experience", f"{candidate.get('experience_years', 0):.1f} yrs")

    st.divider()
    score_col1, score_col2, score_col3, score_col4 = st.columns(4)
    with score_col1:
        st.metric("ATS Score", f"{candidate.get('ats_score', 0):.0f}/100")
    with score_col2:
        st.metric("Grammar", f"{candidate.get('grammar_score', 0):.0f}/100")
    with score_col3:
        st.metric("Clarity", f"{candidate.get('clarity_score', 0):.0f}/100")
    with score_col4:
        st.metric("Overall", f"{candidate.get('overall_score', 0):.1f}/100")

    st.divider()
    skill_col, summary_col = st.columns(2)
    with skill_col:
        st.subheader("Skills")
        skills = candidate.get("skills", [])
        if skills:
            st.write(", ".join(skills))
            if candidate.get("relevant_keywords"):
                st.caption(f"Relevant JD keywords: {', '.join(candidate.get('relevant_keywords', []))}")
        else:
            st.info("No specific skills extracted")

    with summary_col:
        st.subheader("Summary")
        st.write(candidate.get("summary", "N/A"))

    st.divider()
    st.subheader("Improvement Suggestions")
    suggestions = candidate.get("suggestions", [])
    if suggestions:
        for suggestion in suggestions[:3]:
            st.info(suggestion)
    else:
        st.success("Great resume! Consider minor optimizations.")


def render_batch_tab():
    st.header("Advanced Batch Resume Processing")

    if not st.session_state.system_ready:
        st.warning("Please initialize the system first using the sidebar.")
        return

    st.markdown(
        """
        **Upload Support:** CSV, PDF, DOCX, DOC, TXT files
        - Process multiple resumes at once
        - Automatic ranking by overall quality
        - Filtering and sorting options
        """
    )

    with st.form("batch_upload_form", clear_on_submit=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_files = st.file_uploader(
                "Choose resume files to process",
                type=["csv", "pdf", "docx", "doc", "txt"],
                accept_multiple_files=True,
                help="Upload 1 or more files in any supported format",
            )
        with col2:
            st.metric("Files Selected", len(uploaded_files) if uploaded_files else 0)

        job_description = st.text_area(
            "Optional job description for ATS/relevance matching",
            height=140,
            key="batch_job_description_input",
            value=st.session_state.batch_job_description,
            placeholder="Paste the target job description here to match relevant keywords and improve ATS ranking fidelity.",
        )

        action_col1, action_col2 = st.columns([3, 1])
        with action_col1:
            if uploaded_files:
                st.info(f"Ready to process {len(uploaded_files)} file(s).")
            elif not st.session_state.batch_results_ready:
                st.info("Upload one or more resume files to begin batch processing.")
        with action_col2:
            clear_results = st.form_submit_button("Clear Results", use_container_width=True)

        start_processing = st.form_submit_button("Start Batch Processing", type="primary", use_container_width=True)

    if clear_results:
        clear_batch_results()

    if start_processing:
        process_batch_submission(uploaded_files, job_description)

    if st.session_state.batch_results_ready:
        render_batch_results()


def render_about_tab():
    st.header("About This System")
    st.markdown(
        """
        ## AI Resume Shortlisting System

        An intelligent resume classification and analysis platform using Machine Learning and NLP.

        ### Features
        - AI Classification - Categorizes resumes into 25+ job categories
        - Batch Processing - Process 100s of resumes efficiently
        - Skill Extraction - Automatically extracts skills from resumes
        - Advanced Analytics - ATS scores, grammar checking, company matching
        - REST API - Full API for integration

        ### System Architecture
        1. Phase 1 - Data Loading & Preprocessing
        2. Phase 2 - Model Training
        3. Phase 3 - NLP Feature Extraction
        4. Phase 4 - Inference & Predictions
        5. Phase 5 - REST API & Dashboard
        """
    )


def main():
    st.set_page_config(
        page_title="Resume Shortlisting System",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .main {
            background-color: #f8f9fa;
        }
        .stButton>button {
            width: 100%;
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
        }
        .metric-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    init_session_state()
    ensure_system_ready()
    render_sidebar()

    st.title("AI Resume Shortlisting System")
    st.markdown("### Intelligent Resume Classification & Analysis Platform")

    tab1, tab2, tab3 = st.tabs(["Single Resume", "Batch Upload", "About"])
    with tab1:
        render_single_resume_tab()
    with tab2:
        render_batch_tab()
    with tab3:
        render_about_tab()

    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 12px;'>
            <p>AI Resume Shortlisting System v1.0 | 85-90% Accuracy | 100% Open Source</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
