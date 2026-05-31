import pandas as pd
import numpy as np
import os
import joblib
import json
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

def train_model():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, 'synthetic_network_traffic.csv')
    
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Please run dataset_generator.py first.")
        return
        
    print("Loading dataset...")
    df = pd.read_csv(data_path)
    
    X = df.drop('label', axis=1)
    y = df['label']
    
    print("Splitting dataset...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("Hyperparameter tuning with GridSearchCV...")
    # Defining a param grid to find the absolute best Random Forest configuration
    param_grid = {
        'n_estimators': [50, 100],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 5],
        'class_weight': ['balanced', 'balanced_subsample']
    }
    
    rf = RandomForestClassifier(random_state=42)
    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, scoring='f1_macro', n_jobs=-1)
    
    print("Fitting Grid Search...")
    grid_search.fit(X_train_scaled, y_train)
    
    best_clf = grid_search.best_estimator_
    print(f"Best Hyperparameters: {grid_search.best_params_}")
    
    print("Evaluating model...")
    y_pred = best_clf.predict(X_test_scaled)
    
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    # Calculate detailed class metrics
    precision, recall, f1, support = precision_recall_fscore_support(y_test, y_pred)
    class_names = ['Normal', 'DDoS', 'Port Scan']
    
    metrics_by_class = {}
    for i, name in enumerate(class_names):
        metrics_by_class[name] = {
            'precision': float(precision[i]),
            'recall': float(recall[i]),
            'f1_score': float(f1[i]),
            'support': int(support[i])
        }
    
    print("\n--- Model Evaluation ---")
    print(f"Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=class_names))
    
    print("\nConfusion Matrix:")
    print(cm)
    
    # Calculate feature importances
    importances = best_clf.feature_importances_
    features = list(X.columns)
    feature_importances = {features[i]: float(importances[i]) for i in range(len(features))}
    
    # Save the model and scaler
    model_path = os.path.join(current_dir, 'rf_model.pkl')
    scaler_path = os.path.join(current_dir, 'scaler.pkl')
    stats_path = os.path.join(current_dir, 'model_stats.json')
    
    joblib.dump(best_clf, model_path)
    joblib.dump(scaler, scaler_path)
    
    # Structure metrics JSON
    model_stats = {
        'accuracy': float(acc),
        'best_params': grid_search.best_params_,
        'metrics_by_class': metrics_by_class,
        'confusion_matrix': cm.tolist(),
        'feature_importances': feature_importances,
        'features_order': features
    }
    
    with open(stats_path, 'w') as f:
        json.dump(model_stats, f, indent=4)
        
    print(f"\nModel saved to {model_path}")
    print(f"Scaler saved to {scaler_path}")
    print(f"Model stats saved to {stats_path}")

if __name__ == "__main__":
    train_model()
