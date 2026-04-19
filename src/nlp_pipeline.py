# src/nlp_pipeline.py
"""
NLP Pipeline for Resume Processing
Handles text cleaning, tokenization, lemmatization, and feature extraction
"""

import re

from sklearn.feature_extraction.text import TfidfVectorizer

from data_loader import AVAILABLE_NLTK, _safe_lemmatize, _safe_stopwords, _safe_tokenize


class TextPreprocessor:
    """Handles all text preprocessing operations."""

    def __init__(self):
        self.stop_words = _safe_stopwords()

    def clean_text(self, text):
        """Basic text cleaning: remove URLs, emails, special chars."""
        if not text or not isinstance(text, str):
            return ""

        text = re.sub(r'http\S+|www\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        return text.lower().strip()

    def tokenize(self, text):
        """Convert text to tokens."""
        if not text:
            return []
        return _safe_tokenize(text)

    def lemmatize_tokens(self, tokens):
        """Apply lemmatization to tokens."""
        return [_safe_lemmatize(token) for token in tokens]

    def remove_stopwords(self, tokens):
        """Filter out stopwords."""
        if AVAILABLE_NLTK['stopwords']:
            self.stop_words = _safe_stopwords()
        return [token for token in tokens if token not in self.stop_words and len(token) > 2]

    def preprocess(self, text):
        """Full preprocessing pipeline."""
        text = self.clean_text(text)
        if not text:
            return ""

        tokens = self.tokenize(text)
        tokens = self.lemmatize_tokens(tokens)
        tokens = self.remove_stopwords(tokens)

        return ' '.join(tokens)


class FeatureExtractor:
    """Handles feature extraction from text."""

    def __init__(self, max_features=1500, stop_words='english'):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=stop_words,
            min_df=2,
            max_df=0.8,
        )
        self.is_fitted = False

    def fit(self, texts):
        """Fit TF-IDF vectorizer on training texts."""
        self.vectorizer.fit(texts)
        self.is_fitted = True
        print(f"[OK] TF-IDF vectorizer fitted with {len(self.vectorizer.get_feature_names_out())} features")
        return self

    def transform(self, texts):
        """Transform texts to TF-IDF vectors."""
        if not self.is_fitted:
            raise ValueError("Vectorizer not fitted! Call fit() first.")
        return self.vectorizer.transform(texts)

    def fit_transform(self, texts):
        """Fit and transform in one step."""
        self.fit(texts)
        return self.transform(texts)

    def get_feature_names(self):
        """Get the names of features."""
        return self.vectorizer.get_feature_names_out()


class SkillMatcher:
    """Matches resume text against a skill database."""

    def __init__(self, skills_list):
        self.skills = set(skill.lower() for skill in skills_list)
        self.skill_patterns = {
            skill: re.compile(r'\b' + re.escape(skill) + r'\b', re.IGNORECASE)
            for skill in self.skills
        }

    def extract_skills(self, text):
        """Extract skills mentioned in text."""
        found_skills = set()

        for skill, pattern in self.skill_patterns.items():
            if pattern.search(text):
                found_skills.add(skill)

        return sorted(list(found_skills))

    def get_skill_score(self, text, max_points=100):
        """Calculate skill match score."""
        if not self.skills:
            return 0.0
        found = len(self.extract_skills(text))
        score = min((found / len(self.skills)) * max_points, max_points)
        return round(score, 2)


class ResumePipeline:
    """Complete NLP pipeline for resume processing."""

    def __init__(self, skills_list):
        self.preprocessor = TextPreprocessor()
        self.feature_extractor = FeatureExtractor()
        self.skill_matcher = SkillMatcher(skills_list)

    def process_resume(self, resume_text):
        """Process a single resume through the entire pipeline."""
        cleaned = self.preprocessor.clean_text(resume_text)
        processed = self.preprocessor.preprocess(resume_text)
        tokens = self.preprocessor.tokenize(cleaned)
        return {
            'original': resume_text[:200] + "..." if len(resume_text) > 200 else resume_text,
            'cleaned': cleaned,
            'processed': processed,
            'tokens': tokens,
            'skills_found': self.skill_matcher.extract_skills(resume_text),
            'skill_score': self.skill_matcher.get_skill_score(resume_text),
        }
