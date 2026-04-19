"""
Batch Upload Feature Demo - SIMPLIFIED VERSION
Demonstrates the enhanced batch upload feature with comprehensive resume analysis
including ATS scores, grammar checking, clarity analysis, and intelligent ranking.
"""

import pandas as pd
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, 'src')

# Sample resumes for testing batch upload feature
SAMPLE_RESUMES = [
    {
        'ID': 1,
        'Category': 'Software Engineer',
        'Resume': """
        JOHN DEVELOPER
        Email: john.dev@example.com | Phone: (555) 123-4567 | LinkedIn: linkedin.com/in/johndev
        
        PROFESSIONAL SUMMARY
        Results-driven Software Engineer with 5+ years of experience building scalable distributed systems.
        Proven track record of leading cross-functional teams and delivering mission-critical applications.
        
        EXPERIENCE
        Senior Software Engineer | TechCorp | Jan 2020 - Present
        Led development of microservices architecture serving 10M+ daily users, improving system uptime by 45%
        Designed and implemented machine learning pipeline processing 500M+ records daily with 99.9% accuracy
        Managed team of 8 engineers, mentoring 3 junior developers through career progression
        Reduced deployment time by 60% through CI/CD pipeline optimization
        
        Software Engineer | StartupXYZ | Jun 2018 - Dec 2019
        Architected REST APIs serving 50M+ requests monthly handling billions in transactions
        Implemented database optimization reducing query latency by 70%, saving 200K annually
        Built real-time data processing system handling 1M+ events per second
        
        EDUCATION
        Bachelor of Engineering in Computer Science | University of Technology | 2017
        GPA: 3.8/4.0
        
        SKILLS
        Technical: Python, Java, Go, JavaScript, SQL, AWS, Docker, Kubernetes, Apache Kafka, PostgreSQL
        Frameworks: Django, Spring Boot, React, Node.js, Flask
        Cloud: AWS, Google Cloud Platform, Azure
        Soft Skills: Leadership, System Design, Problem Solving, Communication, Agile
        """
    },
    {
        'ID': 2,
        'Category': 'Data Scientist',
        'Resume': """
        SARAH ANALYST
        Email: sarah.data@example.com | Phone: (555) 987-6543
        
        PROFESSIONAL SUMMARY
        Data Scientist with 4 years experience in machine learning and advanced analytics.
        
        EXPERIENCE
        Data Scientist | AnalyticsCorp | 2020 - Present
        Worked on predictive models and data analysis projects
        Used Python and machine learning to solve business problems
        Improved model accuracy by 25%
        
        Junior Data Analyst | DataStartup | 2019 - 2020
        Analyzed large datasets and created visualizations
        Worked with SQL and Python
        
        EDUCATION
        Master of Science in Data Science | State University | 2019
        
        SKILLS
        Python, Machine Learning, SQL, Tableau, Statistics
        """
    },
    {
        'ID': 3,
        'Category': 'Product Manager',
        'Resume': """
        ALEX MANAGER
        alex.manager@example.com
        
        SUMMARY
        I worked in product management for 3 years
        
        JOBS
        Product Manager at Company1 (2021-2023)
        Did product stuff
        Worked with teams
        Launched features
        
        Associate at Company2 (2019-2021)
        Analyzed products
        Wrote requirements
        
        DEGREE
        Bachelor in Business, University (2019)
        
        TECHNICAL SKILLS
        Excel, SQL, Tableau
        """
    },
    {
        'ID': 4,
        'Category': 'DevOps Engineer',
        'Resume': """
        MICHAEL INFRASTRUCTURE
        michael.ops@example.com | +1-555-321-0987 | GitHub: github.com/michaelops
        
        PROFESSIONAL SUMMARY
        DevOps Engineer with 6 years experience designing and maintaining cloud infrastructure.
        Expert in containerization, infrastructure automation, and CI/CD pipelines.
        
        EXPERIENCE
        Senior DevOps Engineer | CloudSystems Inc | 2021 - Present
        Architected Kubernetes cluster serving 50+ microservices with 99.95% uptime SLA
        Automated infrastructure provisioning using Terraform across AWS and GCP, reducing deployment time by 75%
        Implemented comprehensive monitoring using Prometheus and Grafana covering 500+ metrics
        Led migration of workloads to Kubernetes, reducing infrastructure costs by 500K annually
        Mentored 4 junior DevOps engineers on cloud best practices and Kubernetes operations
        
        DevOps Engineer | TechScale Ltd | 2018 - 2021
        Built and maintained CI/CD pipelines using Jenkins processing 10,000+ deployments per day
        Implemented infrastructure-as-code using Terraform managing 200+ resources
        Designed disaster recovery solution with 1 hour RTO and 15 minute RPO
        Reduced infrastructure costs by 40% through resource optimization
        
        EDUCATION
        Bachelor of Science in Information Technology | Tech University | 2017
        
        SKILLS
        Cloud Platforms: AWS, Google Cloud, Azure
        Container Orchestration: Kubernetes, Docker
        Infrastructure as Code: Terraform, Ansible
        CI/CD: Jenkins, GitHub Actions, GitLab CI
        Monitoring: Prometheus, Grafana, ELK Stack
        """
    },
    {
        'ID': 5,
        'Category': 'UI/UX Designer',
        'Resume': """
        EMMA DESIGNER
        Email: emma.design@example.com | Portfolio: behance.net/emmadesigner
        
        PROFESSIONAL SUMMARY
        User Experience Designer with 5 years creating intuitive interfaces and conducting user research.
        
        EXPERIENCE
        UX Designer | DesignStudio | 2020-Present
        Designed mobile app interface used by 2M+ monthly active users with 4.8 star rating
        Conducted user research with 200+ participants improving feature adoption by 40%
        Created comprehensive design system reducing design-to-development time by 50%
        Led redesign of flagship product improving user satisfaction from 3.5 to 4.6 out of 5
        Collaborated with 3 product managers and 10+ engineers
        
        UI Designer | WebDesigns Co | 2018-2020
        Designed responsive web interfaces using Figma and Adobe XD
        Conducted A/B testing on 15+ design variations, improving conversion by 35%
        
        EDUCATION
        Bachelor of Fine Arts in Graphic Design | Creative University | 2018
        
        SKILLS
        Design Tools: Figma, Adobe Creative Suite, Sketch
        UX Research: User Testing, Interviews, Surveys
        Frontend: HTML, CSS, JavaScript
        """
    }
]


def create_sample_csv():
    """Create sample CSV file for testing batch upload"""
    df = pd.DataFrame(SAMPLE_RESUMES)
    csv_path = 'sample_resumes_batch.csv'
    df.to_csv(csv_path, index=False)
    print("[OK] Created sample CSV: {}".format(csv_path))
    return csv_path


def test_batch_upload_locally():
    """
    Test batch upload feature locally by analyzing all sample resumes
    This demonstrates the new comprehensive analysis features
    """
    
    try:
        from src.inference import ResumeClassifier
        from src.resume_analyzer import ResumeAnalyzer
    except ImportError as e:
        print("[ERROR] Failed to import modules: {}".format(e))
        return []
    
    print("\n" + "="*80)
    print("BATCH UPLOAD FEATURE DEMO - COMPREHENSIVE RESUME ANALYSIS")
    print("="*80 + "\n")
    
    # Initialize models
    print("[*] Initializing models...")
    try:
        classifier = ResumeClassifier()
        analyzer = ResumeAnalyzer()
    except Exception as e:
        print("[ERROR] Failed to initialize models: {}".format(e))
        return []
    
    results = []
    
    print("[*] Analyzing {} resumes...\n".format(len(SAMPLE_RESUMES)))
    
    for idx, resume_data in enumerate(SAMPLE_RESUMES):
        try:
            print("\n" + "-"*80)
            print("Resume ID: {} | Category: {}".format(resume_data['ID'], resume_data['Category']))
            print("-"*80)
            
            resume_text = resume_data['Resume']
            
            # Get ML prediction
            print("\n[ML] Classification...")
            try:
                prediction = classifier.predict_single(resume_text)
                pred_category = prediction.get('predicted_category', 'Unknown')
                conf_score = prediction.get('confidence_score', 0)
                if conf_score is None:
                    conf_score = 0
                print("  Predicted Category: {}".format(pred_category))
                print("  Confidence Score: {:.1f}%".format(float(conf_score)))
                skills = prediction.get('extracted_skills', [])
                if skills:
                    print("  Top Skills: {}".format(", ".join(skills[:5])))
            except Exception as e:
                print("  [WARNING] Classification error: {}".format(e))
                prediction = {'predicted_category': 'Unknown', 'confidence_score': 0, 'extracted_skills': []}
            
            # Get comprehensive analysis
            print("\n[ANALYSIS] Quality Scores...")
            try:
                analysis = analyzer.analyze_resume(resume_text)
                
                scores = analysis['scores']
                print("  Overall Score: {:.1f}/100".format(analysis['overall_score']))
                print("  + ATS Score: {:.1f}/100".format(scores['ats']))
                print("  + Grammar Score: {:.1f}/100".format(scores['grammar']))
                print("  + Clarity Score: {:.1f}/100".format(scores['clarity']))
                print("  + Structure Score: {:.1f}/100".format(scores['structure']))
                print("  + Content Quality: {:.1f}/100".format(scores['content_quality']))
                print("  + Format Score: {:.1f}/100".format(scores['format']))
                
                # Analysis details
                print("\n[DETAILS] Resume Metrics...")
                metrics = analysis['metrics']
                print("  Word Count: {}".format(metrics['word_count']))
                print("  Action Verbs: {}".format(metrics['action_verbs']))
                print("  Has Metrics: {}".format("YES" if metrics['has_metrics'] else "NO"))
                print("  Skills Mentioned: {}".format(metrics['skills_count']))
                
                # Sections
                print("\n[STRUCTURE] Resume Organization...")
                sections = analysis['sections']
                print("  Found Sections ({}): {}".format(len(sections['found']), ", ".join(sections['found'])))
                if sections['missing']:
                    print("  Missing Sections: {}".format(", ".join(sections['missing'])))
                
                # Grammar
                print("\n[GRAMMAR] Error Check...")
                grammar_issues = analysis['issues']
                print("  Errors Found: {}".format(grammar_issues['grammar_errors']))
                if grammar_issues['grammar_details']:
                    for error in grammar_issues['grammar_details'][:2]:
                        print("    - {} --> {}".format(error.get('error', 'N/A'), error.get('correction', 'N/A')))
                
                # Recommendations
                print("\n[RECOMMENDATIONS] Improvement Suggestions...")
                if analysis['recommendations']:
                    for i, rec in enumerate(analysis['recommendations'][:3], 1):
                        print("  {}. [{}] {}".format(i, rec.get('priority', 'N/A'), rec.get('suggestion', 'N/A')))
                        print("     Potential Gain: +{} points".format(rec.get('potential_gain', 0)))
                
                # Build composite result
                conf_score_float = float(prediction.get('confidence_score', 0)) if prediction.get('confidence_score') else 0
                
                result = {
                    'rank': 0,
                    'row_id': resume_data['ID'],
                    'provided_category': resume_data['Category'],
                    'ml_prediction': {
                        'predicted_category': prediction.get('predicted_category'),
                        'confidence_score': round(conf_score_float, 1),
                        'top_skills': prediction.get('extracted_skills', [])[:5]
                    },
                    'quality_scores': {
                        'overall_score': round(analysis.get('overall_score', 0), 1),
                        'ats_score': round(scores.get('ats', 0), 1),
                        'grammar_score': round(scores.get('grammar', 0), 1),
                        'clarity_score': round(scores.get('clarity', 0), 1),
                        'structure_score': round(scores.get('structure', 0), 1),
                        'content_quality': round(scores.get('content_quality', 0), 1),
                        'format_score': round(scores.get('format', 0), 1)
                    },
                    'analysis': metrics,
                    'sections_found': len(sections['found']),
                    'missing_sections': sections['missing'],
                    'grammar_errors': grammar_issues['grammar_errors'],
                    'recommendations': analysis['recommendations'][:3]
                }
                
                results.append(result)
            except Exception as e:
                print("[ERROR] Analysis failed: {}".format(e))
                continue
        
        except Exception as e:
            print("[ERROR] Resume {} failed: {}".format(idx + 1, e))
            continue
    
    # Sort results by composite score
    print("\n" + "="*80)
    print("RANKING RESULTS - SORTED BY COMPOSITE SCORE")
    print("="*80 + "\n")
    
    for result in results:
        conf_score = result['ml_prediction'].get('confidence_score', 0) or 0
        composite_score = (
            result['quality_scores'].get('overall_score', 0) * 0.4 +
            float(conf_score) * 0.3 +
            result['quality_scores'].get('ats_score', 0) * 0.3
        )
        result['composite_score'] = round(composite_score, 1)
    
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    
    # Assign ranks
    for i, result in enumerate(results, 1):
        result['rank'] = i
    
    # Display ranking table
    print("{:<6} {:<5} {:<20} {:<8} {:<8} {:<8} {:<8} {:<10}".format(
        'Rank', 'ID', 'Category', 'Overall', 'ATS', 'Grammar', 'ML Conf', 'Composite'))
    print("-" * 85)
    
    for result in results:
        print("{:<6} {:<5} {:<20} {:<8} {:<8} {:<8} {:<8} {:<10}".format(
            result['rank'],
            result['row_id'],
            result['provided_category'],
            result['quality_scores']['overall_score'],
            result['quality_scores']['ats_score'],
            result['quality_scores']['grammar_score'],
            result['ml_prediction']['confidence_score'],
            result['composite_score']))
    
    print("\n" + "="*80)
    print("DETAILED RANKING - TOP 5 RESUMES")
    print("="*80 + "\n")
    
    for result in results[:5]:
        print("\n[RANK #{}] Resume ID: {}".format(result['rank'], result['row_id']))
        print("  Category: {}".format(result['provided_category']))
        print("  Predicted As: {} ({}%)".format(
            result['ml_prediction']['predicted_category'],
            result['ml_prediction']['confidence_score']))
        print("\n  Quality Scores:")
        print("  - Overall Score: {}/100".format(result['quality_scores']['overall_score']))
        print("  - ATS Score: {}/100".format(result['quality_scores']['ats_score']))
        print("  - Grammar Score: {}/100".format(result['quality_scores']['grammar_score']))
        print("  - Clarity Score: {}/100".format(result['quality_scores']['clarity_score']))
        print("  - Composite Rank Score: {}/100".format(result['composite_score']))
        print("\n  Details: {} words, {} action verbs, {} sections found".format(
            result['analysis']['word_count'],
            result['analysis']['action_verbs'],
            result['sections_found']))
        if result['recommendations']:
            print("  Top Recommendation: {}".format(result['recommendations'][0].get('suggestion', 'N/A')))
    
    # Save results to file
    output_file = "batch_upload_results_{}.json".format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    with open(output_file, 'w') as f:
        json.dump({
            'metadata': {
                'total_analyzed': len(results),
                'analysis_timestamp': datetime.now().isoformat(),
                'sorting_method': 'Composite (40% overall + 30% ML confidence + 30% ATS)'
            },
            'ranked_results': results
        }, f, indent=2)
    
    print("\n\n[SUCCESS] Results saved to: {}".format(output_file))
    print("\n" + "="*80)
    print("BATCH UPLOAD FEATURE DEMO COMPLETE")
    print("="*80 + "\n")
    
    return results


if __name__ == '__main__':
    # Create sample CSV
    csv_path = create_sample_csv()
    
    # Run batch analysis
    results = test_batch_upload_locally()
    
    print("\n[INFO] KEY FEATURES DEMONSTRATED:")
    print("  [+] ATS Score - Shows resume compatibility with Applicant Tracking Systems")
    print("  [+] Grammar Score - Detects spelling and grammar errors")
    print("  [+] Clarity Score - Evaluates readability and sentence complexity")
    print("  [+] Structure Score - Checks for proper resume organization")
    print("  [+] Content Quality - Analyzes action verbs, metrics, skills")
    print("  [+] Intelligent Ranking - Composite scoring for smart sorting")
    print("  [+] Detailed Recommendations - Specific improvement suggestions")
    print("  [+] Filter Capabilities - By ATS score, grammar, ML confidence") 
    print("\n[INFO] RECRUITER BENEFITS:")
    print("  * See top candidates at a glance with composite ranking")
    print("  * Filter by quality metrics (ATS, grammar, clarity)")
    print("  * Understand why resume ranked as it did")
    print("  * Get actionable insights for each resume")
    print("  * Save time by prioritizing best resumes")
