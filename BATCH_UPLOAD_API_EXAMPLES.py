"""
Batch Upload API Usage Examples
Quick reference guide for using the enhanced batch upload feature
"""

# ============================================================================
# EXAMPLE 1: Using ResumeAnalyzer Directly (Python)
# ============================================================================

from src.resume_analyzer import ResumeAnalyzer

# Initialize analyzer
analyzer = ResumeAnalyzer()

# Analyze a single resume
resume_text = """
JOHN DEVELOPER
Email: john@example.com | Phone: 555-1234

PROFESSIONAL SUMMARY
Senior Software Engineer with 5+ years experience

EXPERIENCE
Senior Software Engineer | TechCorp | 2020 - Present
Led development of microservices serving 10M+ users, improving uptime by 45%

EDUCATION
BS Computer Science | University | 2017

SKILLS
Python, Java, AWS, Kubernetes, Docker
"""

analysis = analyzer.analyze_resume(resume_text)

# Print results
print("Overall Score:", analysis['overall_score'])
print("ATS Score:", analysis['scores']['ats'])
print("Grammar Score:", analysis['scores']['grammar'])
print("Recommendations:", analysis['recommendations'])


# ============================================================================
# EXAMPLE 2: Batch Processing via API (curl)
# ============================================================================

"""
# Start Flask server
python api.py

# Send batch request via curl
curl -X POST http://localhost:5000/api/batch-predict \
  -H "Content-Type: application/json" \
  -d '{
    "resumes": [
      "RESUME_TEXT_1",
      "RESUME_TEXT_2",
      "RESUME_TEXT_3"
    ],
    "ml_confidence_threshold": 50,
    "min_ats_score": 70,
    "min_grammar_score": 80,
    "sort_by": "composite"
  }'
"""


# ============================================================================
# EXAMPLE 3: CSV Batch Upload via API (Python requests)
# ============================================================================

import requests
import pandas as pd

# Create CSV with resumes
df = pd.DataFrame({
    'ID': [1, 2, 3],
    'Category': ['Python Developer', 'Java Developer', 'DevOps'],
    'Resume': [
        'Resume text 1...',
        'Resume text 2...',
        'Resume text 3...'
    ]
})
df.to_csv('resumes.csv', index=False)

# Upload to API
with open('resumes.csv', 'rb') as f:
    files = {'file': f}
    params = {
        'ml_confidence_threshold': 50,
        'min_ats_score': 70,
        'sort_by': 'overall_score'
    }
    response = requests.post(
        'http://localhost:5000/api/upload-csv',
        files=files,
        params=params
    )

# Get results
results = response.json()
print(f"Total analyzed: {results['summary']['total_uploaded']}")
print(f"Passed filters: {results['summary']['passed_filters']}")

# List top 5 candidates
for resume in results['results'][:5]:
    print(f"\nRank #{resume['rank']}")
    print(f"  Overall Score: {resume['quality_scores']['overall_score']}")
    print(f"  ATS Score: {resume['quality_scores']['ats_score']}")
    print(f"  Grammar: {resume['quality_scores']['grammar_score']}")
    print(f"  Category: {resume['ml_prediction']['predicted_category']}")


# ============================================================================
# EXAMPLE 4: Advanced Filtering & Sorting
# ============================================================================

# Request 1: High quality candidates only (ATS >= 80, Grammar >= 90)
high_quality = {
    "resumes": resumes_list,
    "ml_confidence_threshold": 60,
    "min_ats_score": 80,
    "min_grammar_score": 90,
    "sort_by": "composite"
}

# Request 2: Filter by ATS compatibility
ats_focused = {
    "resumes": resumes_list,
    "ml_confidence_threshold": 40,
    "min_ats_score": 75,
    "sort_by": "ats_score"  # Sort by ATS, not composite
}

# Request 3: All resumes, sorted by ML confidence
all_with_predictions = {
    "resumes": resumes_list,
    "sort_by": "ml_confidence"
}


# ============================================================================
# EXAMPLE 5: Processing Results
# ============================================================================

def process_results(api_response):
    """Extract and process batch upload results"""
    
    results = api_response['results']
    
    # Get top candidates
    top_10 = results[:10]
    
    # Calculate statistics
    avg_overall = sum(r['quality_scores']['overall_score'] for r in results) / len(results)
    avg_ats = sum(r['quality_scores']['ats_score'] for r in results) / len(results)
    
    # Export to CSV
    data = []
    for resume in results:
        data.append({
            'Rank': resume['rank'],
            'Category': resume['provided_category'],
            'Predicted': resume['ml_prediction']['predicted_category'],
            'Confidence': resume['ml_prediction']['confidence_score'],
            'Overall_Score': resume['quality_scores']['overall_score'],
            'ATS_Score': resume['quality_scores']['ats_score'],
            'Grammar_Score': resume['quality_scores']['grammar_score'],
            'Clarity_Score': resume['quality_scores']['clarity_score'],
            'Word_Count': resume['analysis']['word_count'],
            'Action_Verbs': resume['analysis']['action_verbs'],
            'Skills_Found': resume['analysis']['skills_count'],
        })
    
    df = pd.DataFrame(data)
    df.to_csv('batch_results_processed.csv', index=False)
    
    # Print summary
    print(f"\nBatch Processing Summary:")
    print(f"  Total Resumes: {len(results)}")
    print(f"  Average Overall Score: {avg_overall:.1f}/100")
    print(f"  Average ATS Score: {avg_ats:.1f}/100")
    print(f"\n  Top 5 Candidates:")
    for r in top_10[:5]:
        print(f"    Rank #{r['rank']}: {r['provided_category']} ({r['quality_scores']['overall_score']}/100)")


# ============================================================================
# EXAMPLE 6: Response Structure
# ============================================================================

# Single resume analysis structure
single_analysis = {
    'overall_score': 89.8,  # Composite score
    'scores': {
        'ats': 78.0,
        'grammar': 100.0,
        'clarity': 90.0,
        'structure': 85.0,
        'content_quality': 82.0,
        'format': 88.0
    },
    'sections': {
        'found': ['contact', 'summary', 'experience', 'education', 'skills'],
        'missing': ['certifications']
    },
    'metrics': {
        'word_count': 450,
        'action_verbs': 12,
        'has_metrics': True,
        'skills_count': 15,
        'top_skills': ['Python', 'AWS', 'Docker', 'Kubernetes', 'Django']
    },
    'grammar_issues': {
        'error_count': 0,
        'errors': []
    },
    'recommendations': [
        {
            'category': 'ATS Optimization',
            'priority': 'High',
            'suggestion': 'Add more relevant keywords like machine learning, data pipeline',
            'potential_gain': 15
        },
        {
            'category': 'Content Quality',
            'priority': 'Medium',
            'suggestion': 'Add more quantified results (numbers, percentages)',
            'potential_gain': 10
        }
    ]
}

# Batch response structure
batch_response = {
    'status': 'success',
    'summary': {
        'total_uploaded': 100,
        'passed_filters': 85,
        'processing_errors': 0
    },
    'filters': {
        'ml_confidence_threshold': 50,
        'min_ats_score': 70,
        'min_grammar_score': 80,
        'sorted_by': 'composite'
    },
    'results': [
        {
            'rank': 1,
            'row_id': 45,
            'provided_category': 'Software Engineer',
            'ml_prediction': {
                'predicted_category': 'Python Developer',
                'confidence_score': 87.5,
                'top_skills': ['Python', 'Django', 'AWS']
            },
            'quality_scores': {
                'overall_score': 89.2,
                'ats_score': 85.0,
                'grammar_score': 95.0,
                'clarity_score': 90.0,
                'structure_score': 88.0,
                'content_quality': 91.0,
                'format_score': 87.0
            },
            'analysis': {
                'word_count': 520,
                'action_verbs': 14,
                'has_metrics': True,
                'skills_count': 18,
                'top_skills': ['Python', 'Django', 'PostgreSQL', 'AWS', 'Docker']
            },
            'sections_found': 6,
            'missing_sections': [],
            'grammar_errors': 0,
            'recommendations': [
                # 3-5 recommendations per resume
            ]
        }
        # ... more resumes, ranked 2-85
    ],
    'report_file': 'batch_upload_results_20260416_030647.json',
    'timestamp': '2026-04-16T03:06:47.719645'
}


# ============================================================================
# EXAMPLE 7: Filter Strategies
# ============================================================================

def create_filter_requests():
    """Generate different filter requests for different use cases"""
    
    requests_dict = {
        # For quick filtering: only show good candidates
        'quality_candidates': {
            'ml_confidence_threshold': 60,
            'min_ats_score': 75,
            'min_grammar_score': 85,
            'sort_by': 'composite'
        },
        
        # For ATS compliance checking
        'ats_focused': {
            'ml_confidence_threshold': 0,  # No ML filter
            'min_ats_score': 70,
            'sort_by': 'ats_score'
        },
        
        # For grammar/communication focused roles
        'communication_roles': {
            'ml_confidence_threshold': 50,
            'min_grammar_score': 85,
            'sort_by': 'grammar_score'
        },
        
        # For technical roles: high ATS + content quality
        'technical_roles': {
            'ml_confidence_threshold': 70,
            'min_ats_score': 75,
            'sort_by': 'composite'
        },
        
        # See all candidates
        'show_all': {
            'ml_confidence_threshold': 0,
            'sort_by': 'overall_score'
        }
    }
    
    return requests_dict


# ============================================================================
# EXAMPLE 8: Scoring Interpretation Guide
# ============================================================================

def score_interpretation():
    """Guide to understanding each score"""
    
    insights = {
        'ats_score': {
            '0-50': 'Poor ATS compatibility - likely to be filtered by ATS systems',
            '51-75': 'Moderate - good sections but missing keywords',
            '76-90': 'Good - most keywords present, well-structured',
            '91-100': 'Excellent - optimized for ATS systems'
        },
        'grammar_score': {
            '0-50': 'Multiple grammar/spelling errors present',
            '51-75': 'Some errors or awkward phrasing',
            '76-90': 'Minor issues',
            '91-100': 'Perfect or near-perfect grammar'
        },
        'clarity_score': {
            '0-50': 'Difficult to read, complex sentences',
            '51-75': 'Readable but could be clearer',
            '76-90': 'Clear and well-written',
            '91-100': 'Excellent clarity, easy to scan'
        },
        'structure_score': {
            '0-50': 'Missing key sections or poor organization',
            '51-75': 'Has most sections but formatting issues',
            '76-90': 'Well-organized with standard sections',
            '91-100': 'Excellent structure and organization'
        },
        'content_quality': {
            '0-50': 'Weak descriptions, no metrics, few action verbs',
            '51-75': 'Some metrics and impact statements',
            '76-90': 'Strong achievements with metrics and action verbs',
            '91-100': 'Excellent - specific metrics, strong verbs throughout'
        }
    }
    
    return insights


if __name__ == '__main__':
    print("Batch Upload API - Usage Examples")
    print("See examples above for different use cases")
    print("\nKey Endpoints:")
    print("  POST /api/batch-predict - Analyze multiple resumes")
    print("  POST /api/upload-csv - Batch upload from CSV")
    print("\nSort Options: composite, overall_score, ats_score, grammar_score, ml_confidence")
    print("\nFilters: ml_confidence_threshold, min_ats_score, min_grammar_score")
