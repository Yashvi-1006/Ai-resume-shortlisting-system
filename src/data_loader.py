import json
import re

import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize


NLTK_RESOURCES = {
    'punkt': ('tokenizers/punkt',),
    'stopwords': ('corpora/stopwords', 'corpora/stopwords.zip'),
    'wordnet': ('corpora/wordnet', 'corpora/wordnet.zip'),
}


def ensure_nltk_resource(resource_name):
    """Use local NLTK data when available and only attempt download as fallback."""
    for resource_path in NLTK_RESOURCES[resource_name]:
        try:
            nltk.data.find(resource_path)
            return True
        except LookupError:
            continue
    try:
        return bool(nltk.download(resource_name, quiet=True))
    except Exception:
        return False


AVAILABLE_NLTK = {name: ensure_nltk_resource(name) for name in NLTK_RESOURCES}
lemmatizer = WordNetLemmatizer()


def load_resume_csv(path='data/UpdatedResumeDataSet.csv'):
    """Load resume dataset from CSV file."""
    try:
        df = pd.read_csv(path)
        print(f"[OK] Dataset 1 loaded: {len(df)} resumes, {df['Category'].nunique()} categories")
        print(f"  Categories:\n{df['Category'].value_counts()}\n")
        return df
    except FileNotFoundError:
        print(f"[ERROR] {path} not found!")
        return None


def load_ner_dataset(path='data/Entity Recognition in Resumes.json'):
    """Load NER dataset from JSON file."""
    data = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        print(f"[OK] Dataset 2 loaded: {len(data)} tagged resumes\n")
        return data
    except FileNotFoundError:
        print(f"[ERROR] {path} not found!")
        return []


def extract_skills_from_ner(ner_data):
    """Extract skill entities from NER dataset."""
    skills = set()
    for entry in ner_data:
        try:
            annotations = entry.get('annotation', [])
            for ann in annotations:
                labels = ann.get('label', [])
                has_skill_label = (
                    isinstance(labels, list) and 'Skills' in labels
                ) or (
                    isinstance(labels, str) and 'Skills' in labels
                )
                if not has_skill_label:
                    continue

                for point in ann.get('points', []):
                    skill = point.get('text', '').strip().lower()
                    if skill and len(skill) > 1:
                        skills.add(skill)
        except Exception:
            continue
    print(f"[OK] Skills extracted: {len(skills)} unique skills\n")
    return sorted(skills)


def clean_text(text):
    """Clean text: remove URLs, emails, special chars."""
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()


def _safe_tokenize(text):
    if AVAILABLE_NLTK['punkt']:
        try:
            return word_tokenize(text)
        except LookupError:
            pass
    return text.split()


def _safe_stopwords():
    if AVAILABLE_NLTK['stopwords']:
        try:
            return set(stopwords.words('english'))
        except LookupError:
            pass
    return set()


def _safe_lemmatize(token):
    if AVAILABLE_NLTK['wordnet']:
        try:
            return lemmatizer.lemmatize(token)
        except LookupError:
            pass
    return token


def preprocess_text(text):
    """Advanced preprocessing: tokenization, lemmatization, stopword removal."""
    if not text or not isinstance(text, str):
        return ""
    text = clean_text(text)
    if not text:
        return ""

    tokens = _safe_tokenize(text)
    stop_words = _safe_stopwords()
    processed = [
        _safe_lemmatize(token)
        for token in tokens
        if token not in stop_words and len(token) > 2
    ]
    return ' '.join(processed)


def prepare_training_data(clean_only=False):
    """Master function to load and prepare all datasets."""
    print("=" * 60)
    print("PHASE 1: DATA PREPARATION & NLP PREPROCESSING")
    print("=" * 60)

    df = load_resume_csv()
    if df is None:
        return None, []

    ner_data = load_ner_dataset()

    print("Cleaning text...")
    df['cleaned_text'] = df['Resume'].apply(clean_text)

    if not clean_only:
        print("Applying advanced preprocessing (tokenization + lemmatization)...")
        df['processed_text'] = df['Resume'].apply(preprocess_text)
    else:
        df['processed_text'] = df['cleaned_text']

    dynamic_skills = extract_skills_from_ner(ner_data)

    print("Data validation:")
    print(f"  [OK] Total samples: {len(df)}")
    print(f"  [OK] Categories: {df['Category'].nunique()}")
    print(f"  [OK] Skills extracted: {len(dynamic_skills)}")
    print(f"  [OK] Missing resumes: {df['Resume'].isna().sum()}")

    print("\n" + "=" * 60)
    print("[OK] All data ready for training!")
    print("=" * 60 + "\n")

    return df, dynamic_skills


if __name__ == "__main__":
    df, skills = prepare_training_data(clean_only=False)
    if df is not None:
        print("\n" + "=" * 60)
        print("SAMPLE DATA")
        print("=" * 60)
        print(df[['Resume', 'Category', 'cleaned_text']].head(2))
