"""
Batch Upload Feature Demo
Demonstrates the enhanced batch upload feature with comprehensive resume analysis
including ATS scores, grammar checking, clarity analysis, and intelligent ranking.
"""

import pandas as pd
import json
import os
from datetime import datetime

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
        • Led development of microservices architecture serving 10M+ daily users, improving system uptime by 45%
        • Designed and implemented machine learning pipeline processing 500M+ records daily with 99.9% accuracy
        • Managed team of 8 engineers, mentoring 3 junior developers through career progression
        • Reduced deployment time by 60% through CI/CD pipeline optimization
        
        Software Engineer | StartupXYZ | Jun 2018 - Dec 2019
        • Architected REST APIs serving 50M+ requests monthly handling billions in transactions
        • Implemented database optimization reducing query latency by 70%, saving $200K annually
        • Built real-time data processing system handling 1M+ events per second
        
        Junior Developer | WebSolutions Inc | Jun 2017 - May 2018
        • Developed full-stack web applications using Python, JavaScript, and React
        • Participated in agile development with 2-week sprints
        
        EDUCATION
        Bachelor of Engineering in Computer Science | University of Technology | 2017
        GPA: 3.8/4.0 | Honors: Cum Laude
        
        SKILLS
        Technical: Python, Java, Go, JavaScript, SQL, AWS, Docker, Kubernetes, Apache Kafka, PostgreSQL
        Frameworks: Django, Spring Boot, React, Node.js, Flask
        Cloud: AWS (EC2, S3, Lambda), Google Cloud Platform, Azure
        Soft Skills: Leadership, System Design, Problem Solving, Communication, Agile, Code Review
        
        CERTIFICATIONS
        • AWS Solutions Architect Associate - 2021
        • Docker Certified Associate - 2020
        
        PROJECTS
        • Built distributed payment processing system handling $100M+ annually
        • Created machine learning recommendation engine improving user engagement by 35%
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
        - Did product stuff
        - Worked with teams
        - Launched features
        
        Associate at Company2 (2019-2021)
        - Analyzed products
        - Wrote requirements
        
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
        • Architected Kubernetes cluster serving 50+ microservices with 99.95% uptime SLA
        • Automated infrastructure provisioning using Terraform across AWS and GCP, reducing deployment time by 75%
        • Implemented comprehensive monitoring and alerting using Prometheus and Grafana covering 500+ metrics
        • Led migration of workloads to Kubernetes, reducing infrastructure costs by $500K annually
        • Mentored 4 junior DevOps engineers on cloud best practices and Kubernetes operations
        
        DevOps Engineer | TechScale Ltd | 2018 - 2021
        • Built and maintained CI/CD pipelines using Jenkins and GitLab CI processing 10,000+ deployments/day
        • Implemented infrastructure-as-code practices using Terraform managing 200+ resources across environments
        • Designed disaster recovery solution with RTO of 1 hour and RPO of 15 minutes
        • Reduced infrastructure costs by 40% through resource optimization and reserved instances
        
        Systems Administrator | StartupGrow | 2017 - 2018
        • Managed Linux and Windows server infrastructure for 100+ users
        • Implemented backup and disaster recovery solutions
        
        EDUCATION
        Bachelor of Science in Information Technology | Tech University | 2017
        
        SKILLS
        Cloud Platforms: AWS, Google Cloud, Azure
        Container Orchestration: Kubernetes, Docker Swarm
        Infrastructure as Code: Terraform, CloudFormation, Ansible
        CI/CD: Jenkins, GitHub Actions, GitLab CI, CircleCI
        Monitoring: Prometheus, Grafana, ELK Stack, Datadog
        Databases: PostgreSQL, MongoDB, Redis
        Scripting: Bash, Python, Go
        
        CERTIFICATIONS
        • Certified Kubernetes Administrator (CKA) - 2022
        • AWS Certified Solutions Architect Professional - 2021
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
        • Designed mobile app interface used by 2M+ monthly active users with 4.8 star rating
        • Conducted user research with 200+ participants improving feature adoption by 40%
        • Created comprehensive design system reducing design-to-development time by 50%
        • Led redesign of flagship product improving user satisfaction score from 3.5 to 4.6 out of 5
        • Collaborated with 3 product managers and 10+ engineers on feature implementation
        
        UI Designer | WebDesigns Co | 2018-2020
        • Designed responsive web interfaces using Figma and Adobe XD
        • Conducted A/B testing on 15+ design variations, improving conversion by 35%
        • Created visual design guidelines for consistency across 8 products
        
        EDUCATION
        Bachelor of Fine Arts in Graphic Design | Creative University | 2018
        
        SKILLS
        Design Tools: Figma, Adobe Creative Suite, Sketch, Axure
        UX Research: User Testing, Interviews, Surveys, Analytics
        Prototyping: High-fidelity wireframes, Interactive Prototypes
        Frontend: HTML, CSS, Basic JavaScript
        Soft Skills: Communication, Collaboration, Problem Solving, Empathy
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
    import sys
    sys.path.insert(0, 'src')
    
    from src.inference import ResumeClassifier
    from src.resume_analyzer import ResumeAnalyzer
    
    print("\n" + "="*80)
    print("BATCH UPLOAD FEATURE DEMO - COMPREHENSIVE RESUME ANALYSIS")
    print("="*80 + "\n")
    
    # Initialize models
    print("🔄 Initializing models...")
    classifier = ResumeClassifier()
    analyzer = ResumeAnalyzer()
    
    results = []
    
    print(f"\n📋 Analyzing {len(SAMPLE_RESUMES)} resumes...\n")
    
    for idx, resume_data in enumerate(SAMPLE_RESUMES):
        print(f"\n{'─'*80}")
        print(f"Resume #{resume_data['ID']}: {resume_data['Category']}")
        print(f"{'─'*80}")
        
        resume_text = resume_data['Resume']
        
        # Get ML prediction
        print("\n🤖 ML Classification...")
        try:
            prediction = classifier.predict_single(resume_text)
            pred_category = prediction.get('predicted_category', 'Unknown')
            conf_score = prediction.get('confidence_score', 0)
            if conf_score is None:
                conf_score = 0
            print(f"   Predicted Category: {pred_category}")
            print(f"   Confidence Score: {float(conf_score):.1f}%")
            skills = prediction.get('extracted_skills', [])
            if skills:
                print(f"   Top Skills: {', '.join(skills[:5])}")
        except Exception as e:
            print(f"   ⚠ Classification error: {e}")
            prediction = {'predicted_category': 'Unknown', 'confidence_score': 0, 'extracted_skills': []}
        
        # Get comprehensive analysis
        print("\n📊 Quality Analysis...")
        analysis = analyzer.analyze_resume(resume_text)
        
        scores = analysis['scores']
        print(f"   Overall Score: {analysis['overall_score']:.1f}/100")
        print(f"   • ATS Score: {scores['ats']:.1f}/100")
        print(f"   • Grammar Score: {scores['grammar']:.1f}/100")
        print(f"   • Clarity Score: {scores['clarity']:.1f}/100")
        print(f"   • Structure Score: {scores['structure']:.1f}/100")
        print(f"   • Content Quality: {scores['content_quality']:.1f}/100")
        print(f"   • Format Score: {scores['format']:.1f}/100")
        
        # Analysis details
        print(f"\n📈 Resume Details...")
        metrics = analysis['metrics']
        print(f"   Word Count: {metrics['word_count']}")
        print(f"   Action Verbs: {metrics['action_verbs']}")
        print(f"   Has Quantified Results: {'✓ Yes' if metrics['has_metrics'] else '✗ No'}")
        print(f"   Skills Mentioned: {metrics['skills_count']}")
        
        # Sections
        print(f"\n📑 Resume Structure...")
        sections = analysis['sections']
        print(f"   Found Sections ({len(sections['found'])}): {', '.join(sections['found'])}")
        if sections['missing']:
            print(f"   Missing Sections: {', '.join(sections['missing'])}")
        
        # Grammar
        print(f"\n✍️ Grammar Analysis...")
        grammar_issues = analysis['issues']
        print(f"   Grammar Errors Found: {grammar_issues['grammar_errors']}")
        if grammar_issues['grammar_details']:
            for error in grammar_issues['grammar_details'][:2]:
                print(f"   • {error.get('error', 'N/A')} → {error.get('correction', 'N/A')}")
        
        # Recommendations
        print(f"\n💡 Recommendations...")
        if analysis['recommendations']:
            for i, rec in enumerate(analysis['recommendations'][:3], 1):
                print(f"   {i}. [{rec.get('priority', 'N/A')}] {rec.get('suggestion', 'N/A')}")
                print(f"      Potential Gain: +{rec.get('potential_gain', 0)} points")
        
        # Build composite result
        result = {
            'rank': 0,  # Will be set after sorting
            'row_id': resume_data['ID'],
            'provided_category': resume_data['Category'],
            'ml_prediction': {
                'predicted_category': prediction.get('predicted_category'),
                'confidence_score': round(prediction.get('confidence_score', 0), 1),
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
    
    # Sort results by composite score (40% overall + 30% ml_confidence + 30% ats)
    print("\n" + "="*80)
    print("RANKING RESULTS")
    print("="*80 + "\n")
    
    for result in results:
        conf_score = result['ml_prediction'].get('confidence_score', 0)
        if conf_score is None:
            conf_score = 0
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
    print(f"{'Rank':<6} {'ID':<5} {'Category':<20} {'Overall':<8} {'ATS':<8} {'Grammar':<8} {'ML Conf':<8} {'Composite':<10}")
    print("-" * 85)
    
    for result in results:
        print(f"{result['rank']:<6} "
              f"{result['row_id']:<5} "
              f"{result['provided_category']:<20} "
              f"{result['quality_scores']['overall_score']:<8} "
              f"{result['quality_scores']['ats_score']:<8} "
              f"{result['quality_scores']['grammar_score']:<8} "
              f"{result['ml_prediction']['confidence_score']:<8} "
              f"{result['composite_score']:<10}")
    
    print("\n" + "="*80)
    print("DETAILED RANKING VIEW")
    print("="*80 + "\n")
    
    for result in results:
        print(f"\n🏆 RANK #{result['rank']} - Resume ID: {result['row_id']}")
        print(f"   Category: {result['provided_category']}")
        print(f"   Predicted As: {result['ml_prediction']['predicted_category']} ({result['ml_prediction']['confidence_score']}%)")
        print(f"   \n   Quality Scores:")
        print(f"   • Overall Score: {result['quality_scores']['overall_score']}/100")
        print(f"   • ATS Score: {result['quality_scores']['ats_score']}/100")
        print(f"   • Grammar Score: {result['quality_scores']['grammar_score']}/100")
        print(f"   • Clarity Score: {result['quality_scores']['clarity_score']}/100")
        print(f"   • Composite Rank Score: {result['composite_score']}/100")
        print(f"   \n   Details: {result['analysis']['word_count']} words, "
              f"{result['analysis']['action_verbs']} action verbs, "
              f"{result['sections_found']} sections found")
        if result['recommendations']:
            print(f"   Top Recommendation: {result['recommendations'][0].get('suggestion', 'N/A')}")
    
    # Save results to file
    output_file = f"batch_upload_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'metadata': {
                'total_analyzed': len(results),
                'analysis_timestamp': datetime.now().isoformat(),
                'sorting_method': 'Composite (40% overall + 30% ML confidence + 30% ATS)'
            },
            'ranked_results': results
        }, f, indent=2)
    
    print(f"\n\n✅ Results saved to: {output_file}")
    print("\n" + "="*80)
    print("BATCH UPLOAD FEATURE DEMO COMPLETE")
    print("="*80 + "\n")
    
    return results


if __name__ == '__main__':
    # Create sample CSV
    csv_path = create_sample_csv()
    
    # Run batch analysis
    results = test_batch_upload_locally()
    
    print("\n📝 KEY FEATURES DEMONSTRATED:")
    print("   ✓ ATS Score - Shows resume compatibility with Applicant Tracking Systems")
    print("   ✓ Grammar Score - Detects spelling and grammar errors")
    print("   ✓ Clarity Score - Evaluates readability and sentence complexity")
    print("   ✓ Structure Score - Checks for proper resume organization")
    print("   ✓ Content Quality - Analyzes action verbs, metrics, skills")
    print("   ✓ Intelligent Ranking - Composite scoring for smart sorting")
    print("   ✓ Detailed Recommendations - Specific improvement suggestions")
    print("   ✓ Filter Capabilities - By ATS score, grammar, ML confidence") 
    print("\n💼 RECRUITER BENEFITS:")
    print("   • See top candidates at a glance with composite ranking")
    print("   • Filter by quality metrics (ATS, grammar, clarity)")
    print("   • Understand why resume ranked as it did")
    print("   • Get actionable insights for each resume")
    print("   • Save time by prioritizing best resumes")
