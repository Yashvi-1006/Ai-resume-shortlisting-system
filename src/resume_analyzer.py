"""
Resume Analyzer Module
Provides comprehensive analysis of resumes including:
- ATS Score (resumability for Applicant Tracking Systems)
- Grammar and Spell Check
- Clarity Analysis
- Format/Structure Analysis
- Content Quality Analysis
- Overall Resume Score (0-100)
"""

import re
from collections import Counter
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Try to import grammar checker libs
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    import language_tool_python
    LANGUAGE_TOOL_AVAILABLE = True
except ImportError:
    LANGUAGE_TOOL_AVAILABLE = False


class ResumeAnalyzer:
    """Comprehensive resume analyzer"""
    
    def __init__(self):
        self.action_verbs = [
            'Led', 'Designed', 'Implemented', 'Developed', 'Created', 'Built',
            'Managed', 'Directed', 'Oversaw', 'Supervised', 'Coordinated',
            'Improved', 'Increased', 'Decreased', 'Optimized', 'Enhanced',
            'Pioneered', 'Initiated', 'Launched', 'Established', 'Founded',
            'Achieved', 'Delivered', 'Drove', 'Accelerated', 'Transformed',
            'Automated', 'Resolved', 'Facilitated', 'Streamlined', 'Analyzed'
        ]
        
        self.ats_keywords = {
            'technical_skills': ['Python', 'Java', 'JavaScript', 'SQL', 'AWS', 'Azure',
                               'Docker', 'Kubernetes', 'React', 'Node.js', 'Django',
                               'REST API', 'Machine Learning', 'Data Science', 'DevOps'],
            'soft_skills': ['Leadership', 'Communication', 'Teamwork', 'Problem Solving',
                          'Project Management', 'Collaboration', 'Adaptability', 'Initiative'],
            'certifications': ['AWS', 'Microsoft', 'Google', 'Certified', 'Certificate'],
            'education': ['Bachelor', 'Master', 'MBA', 'B.Tech', 'M.Tech', 'PhD']
        }
        
        self.sections = {
            'contact': ['email', 'phone', 'linkedin', 'github', 'contact'],
            'summary': ['summary', 'objective', 'professional profile'],
            'experience': ['experience', 'work experience', 'employment', 'professional experience'],
            'education': ['education', 'degree', 'academic'],
            'skills': ['skills', 'technical skills', 'core competencies'],
            'projects': ['projects', 'portfolio'],
            'certifications': ['certifications', 'certifications and licenses', 'credentials']
        }
        
        if TEXTBLOB_AVAILABLE:
            self.tb_available = True
        else:
            self.tb_available = False
    
    def analyze_resume(self, resume_text):
        """
        Comprehensive resume analysis
        Returns dictionary with all scores and details
        """
        
        if not resume_text or len(resume_text.strip()) < 50:
            return self._empty_analysis("Resume text too short")
        
        # Clean text
        cleaned_text = re.sub(r'\s+', ' ', resume_text).strip()
        text_lower = cleaned_text.lower()
        
        # Calculate all scores
        ats_score = self._calculate_ats_score(cleaned_text, text_lower)
        grammar_score = self._calculate_grammar_score(cleaned_text)
        clarity_score = self._calculate_clarity_score(cleaned_text, text_lower)
        structure_score = self._calculate_structure_score(text_lower)
        content_quality_score = self._calculate_content_quality_score(cleaned_text, text_lower)
        format_score = self._calculate_format_score(cleaned_text)
        
        # Calculate overall score (weighted average)
        overall_score = (
            ats_score * 0.25 +
            grammar_score * 0.20 +
            clarity_score * 0.20 +
            structure_score * 0.15 +
            content_quality_score * 0.15 +
            format_score * 0.05
        )
        
        # Extract detailed information
        sections_found = self._extract_sections(text_lower)
        missing_sections = self._get_missing_sections(sections_found)
        skills_found = self._extract_skills(text_lower)
        action_verb_count = self._count_action_verbs(cleaned_text)
        has_metrics = self._check_metrics(cleaned_text)
        grammar_errors = self._find_grammar_errors(cleaned_text)
        
        return {
            'overall_score': round(overall_score, 1),
            'scores': {
                'ats': round(ats_score, 1),
                'grammar': round(grammar_score, 1),
                'clarity': round(clarity_score, 1),
                'structure': round(structure_score, 1),
                'content_quality': round(content_quality_score, 1),
                'format': round(format_score, 1)
            },
            'sections': {
                'found': sections_found,
                'missing': missing_sections
            },
            'metrics': {
                'word_count': len(cleaned_text.split()),
                'action_verbs': action_verb_count,
                'has_metrics': has_metrics,
                'skills_count': len(skills_found),
                'top_skills': skills_found[:5]
            },
            'issues': {
                'grammar_errors': len(grammar_errors),
                'grammar_details': grammar_errors[:3]  # Top 3 errors
            },
            'recommendations': self._generate_recommendations(
                ats_score, grammar_score, clarity_score, structure_score,
                content_quality_score, sections_found, action_verb_count, has_metrics
            )
        }
    
    def _calculate_ats_score(self, text, text_lower):
        """
        Calculate ATS (Applicant Tracking System) compatibility score
        ATS systems scan for keywords, formatting, structure
        """
        score = 0
        max_score = 100
        
        # Check for standard sections (25 points)
        section_checks = {
            'experience': 0.05,
            'education': 0.05,
            'skills': 0.05,
            'contact': 0.05,
            'summary': 0.05
        }
        for section, weight in section_checks.items():
            if section in text_lower:
                score += weight * 100
        
        # Check for specific keywords (20 points)
        keyword_count = 0
        for category, keywords in self.ats_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    keyword_count += 1
        keyword_score = min(20, (keyword_count / 10) * 20)
        score += keyword_score
        
        # Check for proper formatting (15 points)
        bullets = text.count('•') + text.count('-') + text.count('*')
        if bullets > 10:
            score += 15
        elif bullets > 5:
            score += 10
        else:
            score += 5
        
        # Check for contact info (10 points)
        has_email = '@' in text_lower and '.com' in text_lower
        has_phone = bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text))
        if has_email:
            score += 5
        if has_phone:
            score += 5
        
        # Check for proper formatting (no URL issues) (10 points)
        if 'http' not in text_lower.replace('https://', ''):
            score += 10
        else:
            score += 5
        
        # Check for file format compatibility (10 points - assuming plain text input is compatible)
        score += 10
        
        # Check for reasonable length (10 points)
        word_count = len(text.split())
        if 300 <= word_count <= 1500:
            score += 10
        elif 200 <= word_count <= 2000:
            score += 7
        else:
            score += 3
        
        return min(100, score)
    
    def _calculate_grammar_score(self, text):
        """Calculate grammar and spelling score"""
        score = 100
        
        if not TEXTBLOB_AVAILABLE:
            # Simple heuristic if TextBlob not available
            # Check for common patterns
            text_lower = text.lower()
            
            # Check for common errors
            error_patterns = [
                (r'\byour\b.*\byou are\b', 'you\'re/your'),
                (r'\bits\b.*\bit is\b', 'it\'s/its'),
                (r'thier', 'their'),
                (r'recieve', 'receive'),
                (r'occured', 'occurred'),
                (r'\byour\b', 'your'),  # In context might be you're
            ]
            
            errors_found = 0
            for pattern, error_type in error_patterns:
                if re.search(pattern, text_lower):
                    errors_found += 1
            
            score = max(60, 100 - (errors_found * 5))
            return score
        
        else:
            try:
                blob = TextBlob(text)
                errors = 0
                for sentence in blob.sentences:
                    # Simple grammar check
                    if len(sentence.words) > 0:
                        # Check for basic issues
                        text_sent = str(sentence).lower()
                        if 'thier' in text_sent or 'recieve' in text_sent:
                            errors += 1
                
                # Spelling errors (approximate)
                misspelled = len([word for word in blob.words if word not in blob.correct().words])
                errors += misspelled // 5  # Every 5 misspelled words = 1 error
                
                score = max(60, 100 - (errors * 2))
                return score
            except:
                return 85
    
    def _calculate_clarity_score(self, text, text_lower):
        """Calculate clarity and readability score"""
        score = 100
        
        # Check sentence length (shorter is better)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            avg_sentence_length = len(text.split()) / len(sentences)
            if avg_sentence_length > 20:
                score -= 5
            if avg_sentence_length > 25:
                score -= 5
        
        # Check for action verbs (should be clear and strong)
        action_verb_ratio = self._count_action_verbs(text) / max(len(sentences), 1)
        if action_verb_ratio < 0.3:
            score -= 10
        
        # Check for jargon or overly complex words
        complex_words = [w for w in text.split() if len(w) > 15]
        if len(complex_words) / len(text.split()) > 0.15:
            score -= 5
        
        # Check for passive voice (should be active)
        passive_patterns = [r'\bwas\b', r'\bwere\b', r'\bby\b(?=\s+(?:the|a|an)?)']
        passive_count = sum(len(re.findall(p, text_lower)) for p in passive_patterns)
        if passive_count > len(sentences):
            score -= 10
        
        # Check for bullet points and formatting
        bullets = text.count('•') + text.count('-') + text.count('*')
        if bullets > 10:
            score += 5
        
        return max(60, min(100, score))
    
    def _calculate_structure_score(self, text_lower):
        """Calculate structural organization score"""
        score = 50  # Start at 50
        
        # Check for required sections
        for section_name, keywords in self.sections.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += 8
                    break
        
        return min(100, score)
    
    def _calculate_content_quality_score(self, text, text_lower):
        """Calculate content quality score"""
        score = 50
        
        # Action verbs (important for impact)
        action_count = self._count_action_verbs(text)
        if action_count > 5:
            score += 15
        elif action_count > 3:
            score += 10
        else:
            score += 5
        
        # Metrics and quantifiable results
        if self._check_metrics(text):
            score += 15
        
        # Skills mentioned
        skills = self._extract_skills(text_lower)
        if len(skills) > 10:
            score += 10
        elif len(skills) > 5:
            score += 5
        
        # Years of experience calculation
        years_pattern = r'(\d+)\s*(?:years?|yrs?)'
        years_match = re.search(years_pattern, text_lower)
        if years_match:
            score += 10
        
        return min(100, score)
    
    def _calculate_format_score(self, text):
        """Calculate format and presentation score"""
        score = 70
        
        # Check for proper spacing and formatting
        lines = text.split('\n')
        if len(lines) < 3:
            score -= 10  # Too compact
        
        # Check for proper use of bullet points
        bullets = text.count('•') + text.count('-') + text.count('*')
        if 5 <= bullets <= 50:
            score += 15
        elif bullets > 50:
            score -= 5  # Too many bullets
        
        # Check for readability (line length)
        max_line_length = max(len(line) for line in lines) if lines else 0
        if max_line_length > 100:
            score -= 10
        
        return min(100, score)
    
    def _extract_sections(self, text_lower):
        """Extract what sections are present in resume"""
        found_sections = []
        for section_name, keywords in self.sections.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    found_sections.append(section_name)
                    break
        return list(set(found_sections))
    
    def _get_missing_sections(self, found_sections):
        """Get list of important missing sections"""
        important = ['contact', 'experience', 'education', 'skills']
        missing = [s for s in important if s not in found_sections]
        return missing
    
    def _extract_skills(self, text_lower):
        """Extract technical and soft skills mentioned"""
        skills = []
        for category, tech_skills in self.ats_keywords.items():
            for skill in tech_skills:
                if skill.lower() in text_lower:
                    skills.append(skill)
        return list(set(skills))
    
    def _count_action_verbs(self, text):
        """Count number of action verbs used"""
        count = 0
        for verb in self.action_verbs:
            count += len(re.findall(r'\b' + verb + r'\b', text, re.IGNORECASE))
        return count
    
    def _check_metrics(self, text):
        """Check if resume has quantifiable results"""
        metric_patterns = [
            r'\d+%',           # Percentages (30%)
            r'\$\d+[KMB]?',    # Currency ($2M)
            r'\d+x',           # Multipliers (10x)
            r'#\d+',           # Rankings (#1)
            r'Top \d+',        # Top rankings
        ]
        
        for pattern in metric_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _find_grammar_errors(self, text):
        """Find grammar and spelling errors"""
        errors = []
        
        common_errors = {
            r'\bthier\b': 'their',
            r'\byour\b\s+coming': 'you\'re coming',
            r'\brecieve\b': 'receive',
            r'\boccured\b': 'occurred',
            r'\baccomodate\b': 'accommodate',
            r'\bneccessary\b': 'necessary',
        }
        
        for pattern, correction in common_errors.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                errors.append({
                    'error': match.group(),
                    'correction': correction,
                    'position': match.start()
                })
        
        return errors
    
    def _generate_recommendations(self, ats_score, grammar_score, clarity_score,
                                 structure_score, content_quality_score, sections_found,
                                 action_verb_count, has_metrics):
        """Generate specific recommendations for improvement"""
        recommendations = []
        
        # ATS recommendations
        if ats_score < 70:
            recommendations.append({
                'category': 'ATS Optimization',
                'priority': 'High',
                'suggestion': 'Add more relevant keywords and industry terms to improve ATS compatibility',
                'potential_gain': 15
            })
        
        # Grammar recommendations
        if grammar_score < 80:
            recommendations.append({
                'category': 'Grammar & Spelling',
                'priority': 'High',
                'suggestion': 'Proofread resume for spelling and grammar errors',
                'potential_gain': 10
            })
        
        # Missing sections
        if len(sections_found) < 5:
            recommendations.append({
                'category': 'Structure',
                'priority': 'High',
                'suggestion': f'Add missing sections: {", ".join(["Professional Summary", "Core Skills"])}',
                'potential_gain': 12
            })
        
        # Action verbs
        if action_verb_count < 5:
            recommendations.append({
                'category': 'Content Quality',
                'priority': 'Medium',
                'suggestion': 'Use stronger action verbs (Led, Designed, Implemented) in achievement statements',
                'potential_gain': 10
            })
        
        # Metrics
        if not has_metrics:
            recommendations.append({
                'category': 'Quantification',
                'priority': 'Medium',
                'suggestion': 'Add quantified results (percentages, numbers, dollar amounts) to bullets',
                'potential_gain': 12
            })
        
        # Clarity
        if clarity_score < 75:
            recommendations.append({
                'category': 'Clarity',
                'priority': 'Medium',
                'suggestion': 'Use bullet points to improve readability and reduce paragraph length',
                'potential_gain': 8
            })
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _empty_analysis(self, error_msg):
        """Return empty analysis structure with error"""
        return {
            'overall_score': 0,
            'error': error_msg,
            'scores': {
                'ats': 0,
                'grammar': 0,
                'clarity': 0,
                'structure': 0,
                'content_quality': 0,
                'format': 0
            },
            'sections': {'found': [], 'missing': []},
            'metrics': {'word_count': 0},
            'recommendations': []
        }


# Quick test
if __name__ == '__main__':
    sample_resume = """
    John Doe
    Email: john@example.com | Phone: +1-555-0000 | LinkedIn: linkedin.com/in/johndoe
    
    PROFESSIONAL SUMMARY
    Results-driven Software Engineer with 5+ years of experience developing scalable applications.
    
    EXPERIENCE
    Senior Software Engineer | TechCorp | 2020-Present
    • Led development of microservices architecture, improving system performance by 40%
    • Implemented machine learning pipeline, processing 1M+ records daily
    • Managed team of 5 developers, delivering projects 15% ahead of schedule
    
    Software Engineer | StartupXYZ | 2018-2020
    • Designed and built REST APIs serving 10M+ requests monthly
    • Reduced database query time by 60% through optimization
    
    EDUCATION
    Bachelor of Computer Science | University of Technology | 2018
    
    SKILLS
    Technical: Python, Java, JavaScript, SQL, AWS, Docker, Kubernetes
    Soft Skills: Leadership, Communication, Problem Solving, Agile Methodology
    """
    
    analyzer = ResumeAnalyzer()
    result = analyzer.analyze_resume(sample_resume)
    
    print("Resume Analysis Results:")
    print(f"Overall Score: {result['overall_score']}/100")
    print(f"ATS Score: {result['scores']['ats']}/100")
    print(f"Grammar Score: {result['scores']['grammar']}/100")
    print(f"Clarity Score: {result['scores']['clarity']}/100")
    print(f"Recommendations: {len(result['recommendations'])} items")
