"""
PHASE 5: REST API
Flask-based REST API for Resume Shortlisting System
"""

from flask import Flask, request, jsonify, render_template
import os
import sys
import json
from datetime import datetime
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.inference import ResumeClassifier
from src.resume_analyzer import ResumeAnalyzer
import pandas as pd
from batch_processor import BatchProcessor

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'txt', 'pdf', 'doc', 'docx'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

classifier = None
analyzer = None
batch_processor = BatchProcessor()


def init_classifier():
    global classifier
    if classifier is None:
        try:
            classifier = ResumeClassifier()
        except Exception as e:
            print(f"Error initializing classifier: {e}")
            return False
    return True


def init_analyzer():
    global analyzer
    if analyzer is None:
        try:
            analyzer = ResumeAnalyzer()
        except Exception as e:
            print(f"Error initializing analyzer: {e}")
            return False
    return True


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_batch_filters(source):
    if hasattr(source, "get"):
        return {
            "min_ats": float(source.get("min_ats_score", source.get("min_ats", 0)) or 0),
            "min_grammar": float(source.get("min_grammar_score", source.get("min_grammar", 0)) or 0),
            "min_clarity": float(source.get("min_clarity_score", source.get("min_clarity", 0)) or 0),
            "min_experience": float(source.get("min_experience", 0) or 0),
            "search_term": str(source.get("search", source.get("search_term", "")) or ""),
            "sort_by": str(source.get("sort_by", "overall_score") or "overall_score"),
            "job_description": str(source.get("job_description", "") or ""),
        }
    return {
        "min_ats": 0.0,
        "min_grammar": 0.0,
        "min_clarity": 0.0,
        "min_experience": 0.0,
        "search_term": "",
        "sort_by": "overall_score",
        "job_description": "",
    }


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'Resume Shortlisting API',
        'version': '1.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/initialize', methods=['POST'])
def initialize():
    try:
        success = init_classifier()
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Classifier initialized successfully',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'status': 'error', 'message': 'Failed to initialize'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        if not init_classifier():
            return jsonify({'status': 'error', 'message': 'Classifier not available'}), 500
        
        data = request.json
        if not data or 'resume_text' not in data:
            return jsonify({'status': 'error', 'message': 'Missing resume_text'}), 400
        
        resume_text = data['resume_text']
        result = classifier.predict_single(resume_text)
        
        return jsonify({
            'status': 'success',
            'data': result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/batch-predict', methods=['POST'])
def batch_predict():
    try:
        if not init_classifier():
            return jsonify({'status': 'error', 'message': 'Classifier not available'}), 500
        if not init_analyzer():
            return jsonify({'status': 'error', 'message': 'Analyzer not available'}), 500
        
        data = request.json
        if not data or 'resumes' not in data:
            return jsonify({'status': 'error', 'message': 'Missing resumes list'}), 400
        
        resumes = data['resumes']
        if not isinstance(resumes, list) or len(resumes) == 0:
            return jsonify({'status': 'error', 'message': 'resumes must be non-empty list'}), 400
        
        threshold = data.get('confidence_threshold', 50)
        min_ats_score = data.get('min_ats_score', 0)
        min_grammar_score = data.get('min_grammar_score', 0)
        
        results = []
        
        for idx, resume_text in enumerate(resumes):
            try:
                # Get ML prediction
                prediction = classifier.predict_single(resume_text)
                
                # Get comprehensive analysis
                analysis = analyzer.analyze_resume(resume_text)
                
                # Combine results
                result = {
                    'id': idx + 1,
                    'ml_prediction': {
                        'category': prediction.get('predicted_category'),
                        'confidence_score': prediction.get('confidence_score'),
                        'all_scores': prediction.get('all_scores'),
                        'extracted_skills': prediction.get('extracted_skills', [])
                    },
                    'quality_analysis': {
                        'overall_score': analysis.get('overall_score'),
                        'ats_score': analysis['scores'].get('ats'),
                        'grammar_score': analysis['scores'].get('grammar'),
                        'clarity_score': analysis['scores'].get('clarity'),
                        'structure_score': analysis['scores'].get('structure'),
                        'content_quality_score': analysis['scores'].get('content_quality'),
                        'format_score': analysis['scores'].get('format')
                    },
                    'analysis_details': {
                        'word_count': analysis['metrics'].get('word_count'),
                        'action_verbs': analysis['metrics'].get('action_verbs'),
                        'has_metrics': analysis['metrics'].get('has_metrics'),
                        'skills_count': analysis['metrics'].get('skills_count'),
                        'top_skills': analysis['metrics'].get('top_skills', [])
                    },
                    'sections': {
                        'found': analysis['sections'].get('found', []),
                        'missing': analysis['sections'].get('missing', [])
                    },
                    'grammar_issues': {
                        'error_count': analysis['issues'].get('grammar_errors', 0),
                        'errors': analysis['issues'].get('grammar_details', [])
                    },
                    'recommendations': analysis.get('recommendations', [])
                }
                
                results.append(result)
            except Exception as e:
                print(f"Error analyzing resume {idx + 1}: {e}")
                continue
        
        # Filter based on criteria
        filtered = results
        
        # Apply confidence threshold
        if threshold > 0:
            filtered = [r for r in filtered 
                       if r['ml_prediction'].get('confidence_score', 0) >= threshold]
        
        # Apply ATS score filter
        if min_ats_score > 0:
            filtered = [r for r in filtered 
                       if r['quality_analysis'].get('ats_score', 0) >= min_ats_score]
        
        # Apply grammar score filter
        if min_grammar_score > 0:
            filtered = [r for r in filtered 
                       if r['quality_analysis'].get('grammar_score', 0) >= min_grammar_score]
        
        # Sort by overall quality score (highest to lowest)
        filtered.sort(
            key=lambda x: (
                x['quality_analysis'].get('overall_score', 0) * 0.4 +
                x['ml_prediction'].get('confidence_score', 0) * 0.3 +
                x['quality_analysis'].get('ats_score', 0) * 0.3
            ),
            reverse=True
        )
        
        return jsonify({
            'status': 'success',
            'total_processed': len(results),
            'passed_filters': len(filtered),
            'filters_applied': {
                'confidence_threshold': threshold,
                'min_ats_score': min_ats_score,
                'min_grammar_score': min_grammar_score
            },
            'data': filtered,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        if file.filename.rsplit('.', 1)[-1].lower() != 'csv':
            return jsonify({'status': 'error', 'message': 'This endpoint only accepts CSV files'}), 400
        filters = _parse_batch_filters(request.form)
        raw_results = batch_processor.process_csv_file(file, source_name=file.filename, job_description=filters["job_description"])
        ranked_results = batch_processor.rank_resumes(raw_results, sort_by=filters["sort_by"])
        filtered_results = batch_processor.filter_resumes(
            ranked_results,
            min_ats=filters["min_ats"],
            min_grammar=filters["min_grammar"],
            min_clarity=filters["min_clarity"],
            min_experience=filters["min_experience"],
            search_term=filters["search_term"],
        )
        for rank, result in enumerate(filtered_results, 1):
            result["rank"] = rank

        response_payload = batch_processor.build_response(
            ranked_results=filtered_results,
            raw_results=raw_results,
            filters=filters,
            job_description=filters["job_description"],
        )
        report_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        batch_processor.generate_report(response_payload, os.path.join("data", report_file))

        return jsonify({
            "status": "success",
            "summary": response_payload["metadata"],
            "table": response_payload["table"],
            "results": response_payload["results"],
            "errors": response_payload["errors"],
            "report_file": report_file,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/batch-upload', methods=['POST'])
def batch_upload():
    try:
        if 'files' not in request.files:
            return jsonify({'status': 'error', 'message': 'No files uploaded'}), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({'status': 'error', 'message': 'No files selected'}), 400

        invalid_files = [file.filename for file in files if file.filename and not allowed_file(file.filename)]
        if invalid_files:
            return jsonify({
                'status': 'error',
                'message': f'Unsupported file types: {", ".join(invalid_files)}'
            }), 400

        filters = _parse_batch_filters(request.form)
        raw_results, messages = batch_processor.process_multiple_files(
            files,
            job_description=filters["job_description"],
        )
        ranked_results = batch_processor.rank_resumes(raw_results, sort_by=filters["sort_by"])
        filtered_results = batch_processor.filter_resumes(
            ranked_results,
            min_ats=filters["min_ats"],
            min_grammar=filters["min_grammar"],
            min_clarity=filters["min_clarity"],
            min_experience=filters["min_experience"],
            search_term=filters["search_term"],
        )
        for rank, result in enumerate(filtered_results, 1):
            result["rank"] = rank

        response_payload = batch_processor.build_response(
            ranked_results=filtered_results,
            raw_results=raw_results,
            messages=messages,
            filters=filters,
            job_description=filters["job_description"],
        )

        return jsonify({
            'status': 'success',
            'summary': response_payload['metadata'],
            'messages': response_payload['messages'],
            'table': response_payload['table'],
            'results': response_payload['results'],
            'errors': response_payload['errors'],
            'timestamp': datetime.now().isoformat(),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        if not init_classifier():
            return jsonify({'status': 'error', 'message': 'Classifier not available'}), 500
        
        categories = list(classifier.le.classes_)
        return jsonify({
            'status': 'success',
            'count': len(categories),
            'categories': sorted(categories),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        if not init_classifier():
            return jsonify({'status': 'error', 'message': 'Classifier not available'}), 500
        
        return jsonify({
            'status': 'success',
            'total_categories': len(classifier.le.classes_),
            'categories': list(classifier.le.classes_),
            'model_file': 'data/model.pkl',
            'tfidf_file': 'data/tfidf.pkl',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("PHASE 5: REST API & WEB SERVICE")
    print("="*70 + "\n")
    print("Starting Flask Development Server...")
    print("Access at: http://localhost:5000")
    print("\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
