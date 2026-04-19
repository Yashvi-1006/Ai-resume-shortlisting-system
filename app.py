"""
Main launcher for the AI Resume Shortlisting System.

Default behavior:
- `python app.py` starts the Streamlit dashboard

Optional behavior:
- `python app.py --cli-demo` runs the original CLI demonstration flow
"""

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.inference import ResumeClassifier
from src.train_model import train_and_save


class ResumeShortlistingSystem:
    """Complete Resume Shortlisting System - All Phases Integrated"""

    def __init__(self, use_trained_model=True):
        """Initialize the system"""
        print("\n" + "=" * 70)
        print("AI RESUME SHORTLISTING SYSTEM")
        print("=" * 70 + "\n")

        self.trained_model_exists = os.path.exists('data/model.pkl')

        if use_trained_model and self.trained_model_exists:
            print("Loading existing trained model...")
            self.classifier = ResumeClassifier()
        elif use_trained_model:
            print("Training new model...")
            train_and_save()
            self.classifier = ResumeClassifier()
        else:
            self.classifier = None

    def shortlist_from_file(self, csv_path, target_category=None,
                            confidence_threshold=50, top_n=None):
        """Load resumes from CSV and perform shortlisting"""
        print("\n" + "-" * 70)
        print("FILE-BASED SHORTLISTING")
        print("-" * 70 + "\n")

        try:
            df = pd.read_csv(csv_path)
            print(f"Loaded {len(df)} resumes")

            if self.classifier is None:
                print("ERROR: Classifier not initialized!")
                return df

            predictions = []
            print("Processing resumes...")

            for idx, row in df.iterrows():
                text = row.get('Resume', row.get('resume_text', ''))
                result = self.classifier.predict_single(text)

                predictions.append({
                    'id': row.get('ID', idx),
                    'provided_category': row.get('Category', 'Unknown'),
                    'predicted_category': result.get('predicted_category', 'N/A'),
                    'confidence': result.get('confidence_score', 0),
                    'skills': result.get('extracted_skills', []),
                    'skill_score': result.get('skill_score', 0)
                })

                if (idx + 1) % 100 == 0:
                    print(f"  Processed {idx + 1}/{len(df)}")

            results_df = pd.DataFrame(predictions)

            filtered = results_df.copy()
            if target_category:
                filtered = filtered[filtered['predicted_category'] == target_category]

            filtered = filtered[filtered['confidence'] >= confidence_threshold]
            filtered = filtered.sort_values('confidence', ascending=False)

            if top_n:
                filtered = filtered.head(top_n)

            print(f"\nShortlisted: {len(filtered)} resumes (conf >= {confidence_threshold}%)")

            print("\nTop Results:")
            for i, (_, row) in enumerate(filtered.head(10).iterrows(), 1):
                print(f"\n{i}. ID: {row['id']}")
                print(f"   Category: {row['predicted_category']}")
                print(f"   Confidence: {row['confidence']:.2f}%")
                print(f"   Skills: {row['skills']}")

            return filtered

        except Exception as e:
            print(f"ERROR: {e}")
            return None

    def analyze_resume(self, resume_text):
        """Analyze a single resume"""
        print("\n" + "-" * 70)
        print("SINGLE RESUME ANALYSIS")
        print("-" * 70 + "\n")

        if self.classifier is None:
            print("ERROR: Classifier not initialized!")
            return {}

        result = self.classifier.predict_single(resume_text)

        print(f"Predicted: {result['predicted_category']}")
        print(f"Confidence: {result['confidence_score']}%")
        print(f"Skills: {', '.join(result['extracted_skills'])}")
        print("\nAll Scores:")
        for cat, score in result['all_scores'].items():
            print(f"  {cat}: {score}%")

        return result

    def generate_report(self, results_df, output_file='shortlist_report.json'):
        """Generate JSON report"""
        print(f"\nGenerating report: {output_file}")

        report = {
            'timestamp': datetime.now().isoformat(),
            'total': len(results_df),
            'summary': {
                'avg_confidence': float(results_df['confidence'].mean()),
                'categories': results_df['predicted_category'].value_counts().to_dict()
            },
            'top_10': results_df.head(10).to_dict('records')
        }

        os.makedirs('data', exist_ok=True)
        with open(f'data/{output_file}', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Report saved: data/{output_file}")


def run_cli_demo():
    """Original CLI demonstration flow."""
    print("\n" + "=" * 70)
    print("PHASE 4: COMPLETE SYSTEM - MAIN APPLICATION")
    print("=" * 70 + "\n")

    try:
        system = ResumeShortlistingSystem(use_trained_model=True)

        print("\n\n" + "=" * 70)
        print("DEMO 1: SINGLE RESUME")
        print("=" * 70)

        sample = """JOHN DOE - Senior Data Scientist
        Skills: Python, Machine Learning, TensorFlow, SQL, Pandas
        Experience: 5 years in ML and AI projects"""

        system.analyze_resume(sample)

        print("\n\n" + "=" * 70)
        print("DEMO 2: BATCH SHORTLISTING FROM FILE")
        print("=" * 70)

        csv_path = 'data/UpdatedResumeDataSet.csv'
        if os.path.exists(csv_path):
            results = system.shortlist_from_file(
                csv_path,
                confidence_threshold=50,
                top_n=20
            )
            if results is not None:
                system.generate_report(results)
        else:
            print(f"Dataset not found: {csv_path}")

        print("\n" + "=" * 70)
        print("[COMPLETE] SYSTEM DEMONSTRATION FINISHED!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


def is_port_available(port, host="127.0.0.1"):
    """Return True when a TCP port is free to bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def choose_port(preferred_port, host="127.0.0.1", max_attempts=20):
    """Find an available port starting from preferred_port."""
    for port in range(preferred_port, preferred_port + max_attempts):
        if is_port_available(port, host=host):
            return port
    raise RuntimeError(
        f"Could not find a free port between {preferred_port} and {preferred_port + max_attempts - 1}."
    )


def resolve_python_executable():
    """Prefer the project venv Python when available."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_root, "ai.venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def launch_dashboard(port=8501):
    """Start the Streamlit dashboard with a sensible port fallback."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(project_root, "dashboard.py")
    python_executable = resolve_python_executable()
    selected_port = choose_port(port)

    command = [
        python_executable,
        "-m",
        "streamlit",
        "run",
        dashboard_path,
        "--server.headless",
        "true",
        "--server.port",
        str(selected_port),
    ]

    print("\n" + "=" * 70)
    print("AI RESUME SHORTLISTING SYSTEM")
    print("=" * 70)
    print(f"Launching dashboard on http://localhost:{selected_port}")
    print("Use Ctrl+C in this terminal to stop the app.\n")

    try:
        subprocess.run(command, check=True, cwd=project_root)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Unable to start Streamlit because Python executable was not found: {python_executable}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Streamlit dashboard failed to start.") from exc


def parse_args():
    parser = argparse.ArgumentParser(description="AI Resume Shortlisting System launcher")
    parser.add_argument(
        "--cli-demo",
        action="store_true",
        help="Run the original CLI demo instead of the Streamlit dashboard.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Preferred port for the Streamlit dashboard. Defaults to 8501.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.cli_demo:
        run_cli_demo()
        return

    launch_dashboard(port=args.port)


if __name__ == "__main__":
    main()
