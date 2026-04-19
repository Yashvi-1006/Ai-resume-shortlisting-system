"""
PHASE 3: INFERENCE/PREDICTION MODULE
Uses trained model to make predictions on new resumes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pickle
import numpy as np
from nlp_pipeline import ResumePipeline
from data_loader import prepare_training_data
from ats_analyzer import calculate_ats_score


class ResumeClassifier:
    """
    Loads trained model and makes predictions on new resumes.
    Integrates the NLP pipeline with trained model artifacts.
    """
    
    def __init__(self, model_path=None,
                 tfidf_path=None,
                 le_path=None):
        """
        Initialize classifier by loading saved model artifacts.
        
        Args:
            model_path: Path to saved LogisticRegression model
            tfidf_path: Path to saved TF-IDF vectorizer
            le_path: Path to saved LabelEncoder
        """
        print("\n" + "="*60)
        print("PHASE 3: INFERENCE & PREDICTION")
        print("="*60 + "\n")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = model_path or os.path.join(base_dir, 'data', 'model.pkl')
        tfidf_path = tfidf_path or os.path.join(base_dir, 'data', 'tfidf.pkl')
        le_path = le_path or os.path.join(base_dir, 'data', 'label_encoder.pkl')

        print("Loading model artifacts...")
        try:
            self.model = pickle.load(open(model_path, 'rb'))
            self.tfidf = pickle.load(open(tfidf_path, 'rb'))
            self.le = pickle.load(open(le_path, 'rb'))
            print("[OK] Model loaded successfully")
            print(f"[OK] Categories: {list(self.le.classes_)}\n")
        except FileNotFoundError as e:
            print(f"ERROR: Could not load model files: {e}")
            print("Make sure to run train_model.py first!")
            raise
        
        # Initialize NLP pipeline with extracted skills
        print("Loading NLP pipeline with skill extraction...")
        _, skills_list = prepare_training_data()
        self.skills_list = skills_list
        self.nlp_pipeline = ResumePipeline(skills_list)
        print(f"[OK] NLP pipeline loaded with {len(skills_list)} skills\n")

    def _get_top_feature_contributions(self, vectorized_resume, class_index, limit=5):
        if not hasattr(self.tfidf, "get_feature_names_out") or not hasattr(self.model, "coef_"):
            return []

        feature_names = self.tfidf.get_feature_names_out()
        row = vectorized_resume.tocoo()
        contributions = []
        for feature_idx, feature_value in zip(row.col, row.data):
            class_weight = self.model.coef_[class_index][feature_idx]
            contribution = feature_value * class_weight
            if contribution > 0:
                contributions.append((feature_names[feature_idx], float(contribution)))

        contributions.sort(key=lambda item: item[1], reverse=True)
        return [
            {"feature": feature, "contribution": round(score, 4)}
            for feature, score in contributions[:limit]
        ]
    
    def _build_fallback_ats(self, resume_text, predicted_category, extracted_skills, job_description=""):
        return {
            'role_used': predicted_category or "General",
            'total_score': 0.0,
            'breakdown': {'structure': 0.0, 'keywords': 0.0, 'skills': 0.0, 'experience': 0.0, 'education': 0.0},
            'expected_role_skills': [],
            'matched_skills': [],
            'missing_skills': [],
            'expected_keywords': [],
            'matched_keywords': [],
            'missing_keywords': [],
            'extracted_skills': list(extracted_skills or []),
            'skill_match_pct': 0.0,
            'role_match_pct': 0.0,
            'keyword_match_pct': 0.0,
            'experience_years': 0.0,
            'experience_debug': {'years': 0.0, 'explicit_year_mentions': [], 'date_ranges': []},
            'sections_found': {},
            'cleaned_resume_text': "",
            'tokenized_resume': [],
            'keywords_found': 0,
            'skills_count': 0,
            'job_description_used': bool(job_description.strip()),
            'skill_match_scores': {},
            'keyword_match_scores': {},
        }

    def predict_single(self, resume_text, job_description=""):
        """
        Predict category and confidence for a single resume.
        
        Args:
            resume_text (str): Raw resume text
            
        Returns:
            dict: Prediction results with category and confidence scores
        """
        try:
            # Process resume through NLP pipeline
            result = self.nlp_pipeline.process_resume(resume_text)
            processed_text = result['processed']
            
            # Vectorize using trained TF-IDF
            X = self.tfidf.transform([processed_text])
            
            # Get prediction and confidence scores
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            
            category = self.le.inverse_transform([prediction])[0]
            confidence = float(max(probabilities) * 100)
            
            # Get all class probabilities
            all_scores = {
                self.le.inverse_transform([i])[0]: float(proba * 100)
                for i, proba in enumerate(probabilities)
            }

            sorted_predictions = sorted(
                all_scores.items(),
                key=lambda item: item[1],
                reverse=True
            )
            top_predictions = [
                {"category": label, "probability": float(round(score / 100, 4)), "confidence_score": float(round(score, 2))}
                for label, score in sorted_predictions[:3]
            ]
            predicted_class_index = int(np.argmax(probabilities))
            influential_features = self._get_top_feature_contributions(X, predicted_class_index)

            try:
                ats_result = calculate_ats_score(
                    resume_text,
                    category=category,
                    extracted_skills=result['skills_found'],
                    job_description=job_description,
                )
            except Exception:
                ats_result = self._build_fallback_ats(
                    resume_text,
                    category,
                    result['skills_found'],
                    job_description=job_description,
                )
            reason_parts = []
            if ats_result['matched_skills']:
                reason_parts.append(f"matched role skills: {', '.join(ats_result['matched_skills'][:5])}")
            if ats_result['matched_keywords']:
                reason_parts.append(f"matched keywords: {', '.join(ats_result['matched_keywords'][:5])}")
            if influential_features:
                reason_parts.append(
                    "top model features: " +
                    ", ".join(item["feature"] for item in influential_features[:5])
                )
            category_reason = "; ".join(reason_parts) if reason_parts else "highest classifier probability among all categories"
            
            return {
                'resume_text': result['original'],
                'cleaned_resume_text': result['cleaned'],
                'tokenized_resume': result.get('tokens', []),
                'predicted_category': category,
                'confidence_score': float(round(confidence, 2)),
                'all_scores': {k: float(round(v, 2)) for k, v in all_scores.items()},
                'top_predictions': top_predictions,
                'extracted_skills': ats_result['extracted_skills'],
                'skill_score': ats_result.get('role_match_pct', ats_result['skill_match_pct']),
                'role_match_score': ats_result.get('role_match_pct', ats_result['skill_match_pct']),
                'role_skill_match_score': ats_result['skill_match_pct'],
                'matched_skills': ats_result['matched_skills'],
                'missing_skills': ats_result['missing_skills'],
                'expected_role_skills': ats_result['expected_role_skills'],
                'expected_keywords': ats_result['expected_keywords'],
                'matched_keywords': ats_result['matched_keywords'],
                'missing_keywords': ats_result['missing_keywords'],
                'ats_analysis': ats_result,
                'category_reason': category_reason,
                'influential_features': influential_features,
                'debug': {
                    'cleaned_resume_text': result['cleaned'],
                    'tokenized_resume': result.get('tokens', []),
                    'expected_role_skills': ats_result['expected_role_skills'],
                    'matched_skills': ats_result['matched_skills'],
                    'missing_skills': ats_result['missing_skills'],
                    'expected_keywords': ats_result['expected_keywords'],
                    'matched_keywords': ats_result['matched_keywords'],
                    'missing_keywords': ats_result['missing_keywords'],
                    'category_prediction_scores': {k: float(round(v, 2)) for k, v in sorted_predictions},
                    'influential_features': influential_features,
                    'experience_debug': ats_result['experience_debug'],
                    'skill_match_scores': ats_result.get('skill_match_scores', {}),
                    'keyword_match_scores': ats_result.get('keyword_match_scores', {}),
                }
            }
        except Exception as e:
            return {'error': f"Prediction failed: {str(e)}"}
    
    def predict_batch(self, resume_texts):
        """
        Predict categories for multiple resumes.
        
        Args:
            resume_texts (list): List of resume texts
            
        Returns:
            list: List of prediction results
        """
        predictions = []
        for i, text in enumerate(resume_texts):
            result = self.predict_single(text)
            predictions.append(result)
        return predictions
    
    def shortlist_resumes(self, resume_texts, target_category=None, confidence_threshold=50):
        """
        Shortlist resumes based on category and confidence.
        
        Args:
            resume_texts (list): List of resume texts
            target_category (str): Optional specific category to filter for
            confidence_threshold (float): Minimum confidence score (0-100)
            
        Returns:
            list: Filtered and sorted predictions
        """
        predictions = self.predict_batch(resume_texts)
        
        # Filter by target category if specified
        if target_category:
            predictions = [p for p in predictions 
                          if p.get('predicted_category') == target_category]
        
        # Filter by confidence threshold
        predictions = [p for p in predictions 
                      if p.get('confidence_score', 0) >= confidence_threshold]
        
        # Sort by confidence score (descending)
        predictions = sorted(predictions, 
                            key=lambda x: x.get('confidence_score', 0), 
                            reverse=True)
        
        return predictions


def run_inference_demo():
    """Demo function showing inference capabilities."""
    
    try:
        classifier = ResumeClassifier()
        
        # Sample resumes for testing
        sample_resumes = [
            """JOHN DOE - Python Developer
               Email: john@example.com
               Experience: 5 years in Python, Django, Flask
               Skills: Python, JavaScript, SQL, Docker, Git
               Education: BS Computer Science""",
            
            """JANE SMITH - Data Scientist
               Email: jane@example.com  
               Experience: 3 years in Machine Learning, Data Analysis
               Skills: Python, R, TensorFlow, Pandas, Scikit-learn
               Education: MS Data Science"""
        ]
        
        print("\n" + "-"*60)
        print("INDIVIDUAL PREDICTIONS")
        print("-"*60)
        
        for i, resume in enumerate(sample_resumes, 1):
            print(f"\nResume {i}:")
            result = classifier.predict_single(resume)
            
            if 'error' not in result:
                print(f"  Predicted Category: {result['predicted_category']}")
                print(f"  Confidence: {result['confidence_score']}%")
                print(f"  Skills Found: {result['extracted_skills']}")
                print(f"  All Scores:")
                for cat, score in result['all_scores'].items():
                    print(f"    - {cat}: {score}%")
        
        print("\n" + "-"*60)
        print("SHORTLISTING RESULTS")
        print("-"*60)
        
        shortlisted = classifier.shortlist_resumes(
            sample_resumes, 
            confidence_threshold=50
        )
        
        print(f"\nTotal Resumes: {len(sample_resumes)}")
        print(f"Shortlisted (conf > 50%): {len(shortlisted)}\n")
        
        for i, result in enumerate(shortlisted, 1):
            print(f"{i}. {result['predicted_category']} (Conf: {result['confidence_score']}%)")
        
        print("\n" + "="*60)
        print("[COMPLETE] PHASE 3 - INFERENCE MODULE READY!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"Error in inference demo: {e}")


if __name__ == "__main__":
    run_inference_demo()
