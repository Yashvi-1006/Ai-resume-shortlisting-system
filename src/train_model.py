import os
import sys
import pickle

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import prepare_training_data


def train_and_save():
    print("\n" + "=" * 60)
    print("PHASE 2: MODEL TRAINING & EVALUATION")
    print("=" * 60 + "\n")

    print("Loading data...")
    df, _ = prepare_training_data()

    le = LabelEncoder()
    df['label'] = le.fit_transform(df['Category'])
    print(f"\nCategories found: {list(le.classes_)}")

    X_train, X_test, y_train, y_test = train_test_split(
        df['cleaned_text'],
        df['label'],
        test_size=0.2,
        random_state=42,
    )
    print(f"\nTraining samples : {len(X_train)}")
    print(f"Testing samples  : {len(X_test)}")

    print("\nConverting text to TF-IDF vectors...")
    tfidf = TfidfVectorizer(max_features=1500, stop_words='english')
    X_train_tf = tfidf.fit_transform(X_train)
    X_test_tf = tfidf.transform(X_test)

    print("Training model...")
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_tf, y_train)

    y_pred = model.predict(X_test_tf)
    acc = accuracy_score(y_test, y_pred)

    print("\n" + "=" * 50)
    print(f"Model Accuracy: {acc * 100:.2f}%")
    print("=" * 50)
    print("\nDetailed Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    os.makedirs('data', exist_ok=True)
    pickle.dump(model, open('data/model.pkl', 'wb'))
    pickle.dump(tfidf, open('data/tfidf.pkl', 'wb'))
    pickle.dump(le, open('data/label_encoder.pkl', 'wb'))
    print("\nModel saved to data/ folder:")
    print("  - model.pkl")
    print("  - tfidf.pkl")
    print("  - label_encoder.pkl")

    print("\nGenerating charts...")
    plt.figure(figsize=(14, 6))
    df['Category'].value_counts().plot(kind='bar', color='steelblue')
    plt.title('Resume Distribution by Category')
    plt.xlabel('Category')
    plt.ylabel('Count')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('data/category_distribution.png')
    plt.close()
    print("Chart 1 saved: category_distribution.png")

    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(
        cm,
        annot=False,
        cmap='Blues',
        xticklabels=le.classes_,
        yticklabels=le.classes_,
    )
    plt.title('Confusion Matrix')
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('data/confusion_matrix.png')
    plt.close()
    print("Chart 2 saved: confusion_matrix.png")

    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETE!")
    print("=" * 60 + "\n")

    return model, tfidf, le


if __name__ == "__main__":
    train_and_save()
