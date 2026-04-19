"""
Resume Quality Analyzer
Grammar check, metrics, and improvement suggestions
"""

import re
from collections import Counter

def check_grammar_issues(resume_text):
    """
    Check common grammar and writing issues in resume.
    
    Args:
        resume_text: Resume text
    
    Returns:
        dict: Issues found and suggestions
    """
    issues = []
    
    lines = resume_text.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        # Check for incomplete sentences
        if line.strip() and not line.strip().endswith(('.', ':', '-', '•', ')', ']')):
            if len(line.strip()) > 10:
                issues.append({
                    'line': line_num,
                    'type': 'Incomplete Sentence',
                    'issue': f'"{line.strip()[:50]}..." may be incomplete',
                    'severity': 'low'
                })
        
        # Check for tense consistency
        if re.search(r'\b(is|are|was|were|be)\s+\w+ing\b', line):
            if 'managed' not in line and 'developed' not in line:
                issues.append({
                    'line': line_num,
                    'type': 'Tense',
                    'issue': 'Use past tense for past roles',
                    'severity': 'medium'
                })
        
        # Check for weak verbs
        weak_verbs = ['helps', 'helped', 'make', 'made', 'works', 'worked', 'do', 'did', 'handles', 'responsible for']
        for verb in weak_verbs:
            if f' {verb} ' in line.lower():
                issues.append({
                    'line': line_num,
                    'type': 'Weak Verb',
                    'issue': f'Replace "{verb}" with stronger action verb',
                    'suggestion': 'Use: developed, designed, implemented, led, achieved',
                    'severity': 'low'
                })
                break
        
        # Check for personal pronouns
        if re.search(r'\b(I|me|my|we|our)\b', line):
            issues.append({
                'line': line_num,
                'type': 'Personal Pronoun',
                'issue': 'Avoid personal pronouns in resume',
                'severity': 'medium'
            })
        
        # Check for unnecessary words
        unnecessary = ['very', 'really', 'quite', 'somewhat', 'basically', 'essentially']
        for word in unnecessary:
            if f' {word} ' in line.lower():
                issues.append({
                    'line': line_num,
                    'type': 'Unnecessary Word',
                    'issue': f'Remove unnecessary word: "{word}"',
                    'severity': 'low'
                })
    
    return {
        'total_issues': len(issues),
        'issues': issues,
        'severity_breakdown': get_severity_breakdown(issues)
    }


def get_severity_breakdown(issues):
    """Get count of issues by severity."""
    severity_count = Counter(issue['severity'] for issue in issues)
    return {
        'critical': severity_count.get('critical', 0),
        'high': severity_count.get('high', 0),
        'medium': severity_count.get('medium', 0),
        'low': severity_count.get('low', 0)
    }


def calculate_resume_metrics(resume_text, predicted_category=''):
    """
    Calculate various resume quality metrics.
    
    Args:
        resume_text: Resume text
        predicted_category: Predicted job category
    
    Returns:
        dict: Various metrics
    """
    # Basic metrics
    word_count = len(resume_text.split())
    line_count = len(resume_text.split('\n'))
    
    # Section analysis
    sections = {
        'contact': bool(re.search(r'(email|phone|linkedin|github)', resume_text, re.IGNORECASE)),
        'summary': bool(re.search(r'(summary|objective|profile)', resume_text, re.IGNORECASE)),
        'experience': bool(re.search(r'(experience|work experience|employment)', resume_text, re.IGNORECASE)),
        'skills': bool(re.search(r'(skills|technical|proficiencies)', resume_text, re.IGNORECASE)),
        'education': bool(re.search(r'(education|b\.tech|bachelor|master|degree)', resume_text, re.IGNORECASE)),
        'certifications': bool(re.search(r'(certification|certified|certificate)', resume_text, re.IGNORECASE))
    }
    
    sections_score = (sum(sections.values()) / len(sections)) * 100
    
    # Quantifiable achievements
    achievements = len(re.findall(r'(\d+%|\d+\+?k|\d+\+?\s*(million|thousand))', resume_text, re.IGNORECASE))
    
    # Action verbs
    action_verbs = [
        'led', 'managed', 'implemented', 'developed', 'designed', 'optimized',
        'achieved', 'increased', 'reduced', 'improved', 'created', 'built',
        'engineered', 'architected', 'orchestrated', 'spearheaded', 'pioneered'
    ]
    action_verb_count = sum(1 for verb in action_verbs if re.search(rf'\b{verb}\b', resume_text, re.IGNORECASE))
    
    # Length assessment
    ideal_length = 400  # words
    length_score = min(100, int((word_count / ideal_length) * 100))
    if word_count > 1000:
        length_score = max(0, 100 - (word_count - 1000) // 100)
    
    # Email presence
    has_email = bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resume_text))
    has_phone = bool(re.search(r'\+?\d{1,3}[\s.\-()]?\d{3,}[\s.\-()]?\d{3,}[\s.\-()]?\d{4,}', resume_text))
    
    return {
        'word_count': word_count,
        'line_count': line_count,
        'sections_completeness': {
            'score': int(sections_score),
            'sections': sections
        },
        'quantifiable_achievements': achievements,
        'action_verbs_used': action_verb_count,
        'contact_info': {
            'has_email': has_email,
            'has_phone': has_phone
        },
        'length_assessment': {
            'word_count': word_count,
            'score': length_score,
            'status': 'Good' if 400 <= word_count <= 1000 else ('Too short' if word_count < 400 else 'Too long')
        }
    }


def get_btech_cse_specific_suggestions(resume_text):
    """
    Get specific suggestions for BTech CSE candidates.
    
    Args:
        resume_text: Resume text
    
    Returns:
        list: BTech CSE specific recommendations
    """
    suggestions = []
    text_lower = resume_text.lower()
    
    # Check for key CSE skills
    cse_skills = {
        'core': ['dsa', 'algorithms', 'data structures', 'oops', 'databases'],
        'web': ['html', 'css', 'javascript', 'react', 'django', 'node.js'],
        'backend': ['python', 'java', 'c++', 'spring', 'microservices'],
        'devops': ['docker', 'kubernetes', 'jenkins', 'git', 'linux'],
        'cloud': ['aws', 'azure', 'gcp', 'lambda', 'ec2']
    }
    
    found_categories = []
    for category, skills in cse_skills.items():
        category_skills = [s for s in skills if s in text_lower]
        if category_skills:
            found_categories.append(category)
    
    # Suggestions based on missing areas
    if 'core' not in found_categories:
        suggestions.append("📚 Add core CSE fundamentals: Data Structures, Algorithms, OOPS")
    
    if 'web' not in found_categories and 'backend' not in found_categories:
        suggestions.append("💻 Add development skills: Python, Java, JavaScript, React, Django, etc.")
    
    if 'devops' not in found_categories:
        suggestions.append("🔧 Add DevOps skills: Docker, Kubernetes, Git, Linux")
    
    if 'cloud' not in found_categories:
        suggestions.append("☁️ Add Cloud skills: AWS, Azure, GCP")
    
    # Check for projects
    if not re.search(r'(project|built|developed|created)', text_lower):
        suggestions.append("🎯 Add projects section with technical projects and implementations")
    
    # Check for certifications
    if not re.search(r'(certification|certified|award)', text_lower):
        suggestions.append("🏆 Add relevant certifications or achievements")
    
    # Check for GitHub/portfolio
    if not re.search(r'(github|gitlab|portfolio|website)', text_lower):
        suggestions.append("🔗 Add GitHub profile or portfolio link")
    
    if not suggestions:
        suggestions.append("✅ Great resume for BTech CSE! Keep it updated with recent projects.")
    
    return suggestions


def get_quality_score(resume_text, predicted_category=''):
    """
    Calculate overall resume quality score.
    
    Args:
        resume_text: Resume text
        predicted_category: Predicted job category
    
    Returns:
        dict: Quality score with breakdown
    """
    metrics = calculate_resume_metrics(resume_text, predicted_category)
    grammar = check_grammar_issues(resume_text)
    
    scores = {
        'completeness': metrics['sections_completeness']['score'],
        'length': metrics['length_assessment']['score'],
        'grammar': max(0, 100 - (grammar['total_issues'] * 3)),  # Deduct 3 points per issue
        'contact': int((metrics['contact_info']['has_email'] and metrics['contact_info']['has_phone']) * 100),
        'achievements': min(100, (metrics['quantifiable_achievements'] * 10)),
        'action_verbs': min(100, (metrics['action_verbs_used'] * 5))
    }
    
    # Calculate weighted score
    weights = {
        'completeness': 0.25,
        'length': 0.15,
        'grammar': 0.20,
        'contact': 0.10,
        'achievements': 0.15,
        'action_verbs': 0.15
    }
    
    total_score = sum(scores[k] * v for k, v in weights.items())
    
    return {
        'total_score': int(total_score),
        'score_breakdown': scores,
        'feedback': get_quality_feedback(int(total_score)),
        'metrics': metrics,
        'grammar_issues': grammar['total_issues']
    }


def get_quality_feedback(score):
    """Get feedback based on quality score."""
    if score >= 85:
        return "🟢 Excellent! Your resume is well-structured and professional."
    elif score >= 70:
        return "🟡 Good! Make a few improvements to increase impact."
    elif score >= 50:
        return "🟠 Fair. Significant improvements recommended."
    else:
        return "🔴 Needs major improvements. Follow suggestions to enhance quality."
