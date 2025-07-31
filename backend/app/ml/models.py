# backend/app/ml/models.py

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime
import json

class EcommerceMLPipeline:
    """
    Machine Learning pipeline for e-commerce predictions
    Includes both churn prediction and spending prediction models
    """
    
    def __init__(self):
        self.churn_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        self.spending_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_split=5,
            random_state=42
        )
        
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = None
        self.is_trained = False
        
    def preprocess_data(self, df, is_training=True):
        """
        Preprocess the data for machine learning
        """
        df_processed = df.copy()
        
        # Encode categorical variables
        categorical_cols = ['gender', 'region', 'preferred_category', 'marketing_channel']
        
        for col in categorical_cols:
            if col in df_processed.columns:
                if is_training:
                    # Create and fit label encoder
                    le = LabelEncoder()
                    df_processed[col] = le.fit_transform(df_processed[col].astype(str))
                    self.label_encoders[col] = le
                else:
                    # Use existing label encoder
                    if col in self.label_encoders:
                        # Handle unseen categories
                        le = self.label_encoders[col]
                        df_processed[col] = df_processed[col].astype(str)
                        unknown_mask = ~df_processed[col].isin(le.classes_)
                        if unknown_mask.any():
                            # Assign unknown categories to the most common class
                            most_common = le.classes_[0]
                            df_processed.loc[unknown_mask, col] = most_common
                        df_processed[col] = le.transform(df_processed[col])
        
        # Select features for training
        feature_cols = [
            'age', 'gender', 'region', 'tenure_days', 'total_orders',
            'total_spent', 'avg_order_value', 'days_since_last_order',
            'total_sessions', 'avg_session_duration', 'pages_per_session',
            'cart_abandonment_rate', 'support_tickets', 'preferred_category',
            'seasonal_activity', 'marketing_channel'
        ]
        
        # Keep only available features
        available_features = [col for col in feature_cols if col in df_processed.columns]
        X = df_processed[available_features]
        
        if is_training:
            self.feature_names = X.columns.tolist()
            # Fit scaler on training data
            X_scaled = self.scaler.fit_transform(X)
        else:
            # Use existing scaler
            X_scaled = self.scaler.transform(X)
        
        return pd.DataFrame(X_scaled, columns=X.columns, index=X.index)
    
    def train_models(self, dataset_path):
        """
        Train both churn and spending prediction models
        """
        print("Loading training dataset...")
        
        # Load dataset (support both CSV and JSON)
        if dataset_path.endswith('.csv'):
            df = pd.read_csv(dataset_path)
        elif dataset_path.endswith('.json'):
            with open(dataset_path, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
        else:
            raise ValueError("Dataset must be CSV or JSON format")
        
        print(f"Dataset loaded: {len(df)} samples, {len(df.columns)} features")
        
        # Preprocess features
        X = self.preprocess_data(df, is_training=True)
        
        # Extract target variables
        y_churn = df['will_churn']
        y_spending = df['predicted_spending_3months']
        
        print(f"Features after preprocessing: {X.shape[1]}")
        print(f"Churn distribution: {y_churn.value_counts(normalize=True)}")
        
        # Split data for training and testing
        X_train, X_test, y_churn_train, y_churn_test, y_spending_train, y_spending_test = train_test_split(
            X, y_churn, y_spending, test_size=0.2, random_state=42, stratify=y_churn
        )
        
        print(f"Training set: {X_train.shape[0]} samples")
        print(f"Test set: {X_test.shape[0]} samples")
        
        # Train churn prediction model
        print("\n🔄 Training Churn Prediction Model...")
        self.churn_model.fit(X_train, y_churn_train)
        
        # Evaluate churn model
        churn_train_score = self.churn_model.score(X_train, y_churn_train)
        churn_test_score = self.churn_model.score(X_test, y_churn_test)
        churn_cv_scores = cross_val_score(self.churn_model, X_train, y_churn_train, cv=5)
        
        print(f"Churn Model - Train Accuracy: {churn_train_score:.3f}")
        print(f"Churn Model - Test Accuracy: {churn_test_score:.3f}")
        print(f"Churn Model - CV Score: {churn_cv_scores.mean():.3f} (+/- {churn_cv_scores.std() * 2:.3f})")
        
        # Train spending prediction model
        print("\n💰 Training Spending Prediction Model...")
        self.spending_model.fit(X_train, y_spending_train)
        
        # Evaluate spending model
        spending_train_pred = self.spending_model.predict(X_train)
        spending_test_pred = self.spending_model.predict(X_test)
        
        spending_train_r2 = r2_score(y_spending_train, spending_train_pred)
        spending_test_r2 = r2_score(y_spending_test, spending_test_pred)
        spending_rmse = np.sqrt(mean_squared_error(y_spending_test, spending_test_pred))
        
        print(f"Spending Model - Train R²: {spending_train_r2:.3f}")
        print(f"Spending Model - Test R²: {spending_test_r2:.3f}")
        print(f"Spending Model - RMSE: ${spending_rmse:.2f}")
        
        # Feature importance analysis
        print("\n📊 Feature Importance (Churn Model):")
        churn_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.churn_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for _, row in churn_importance.head(10).iterrows():
            print(f"  {row['feature']}: {row['importance']:.3f}")
        
        print("\n📊 Feature Importance (Spending Model):")
        spending_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.spending_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for _, row in spending_importance.head(10).iterrows():
            print(f"  {row['feature']}: {row['importance']:.3f}")
        
        # Mark as trained
        self.is_trained = True
        
        # Return training metrics
        return {
            'churn_accuracy': churn_test_score,
            'churn_cv_score': churn_cv_scores.mean(),
            'spending_r2': spending_test_r2,
            'spending_rmse': spending_rmse,
            'feature_importance_churn': churn_importance.to_dict('records'),
            'feature_importance_spending': spending_importance.to_dict('records'),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }
    
    def predict_churn(self, customer_data):
        """
        Predict if a customer will churn
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Preprocess the data
        X = self.preprocess_data(customer_data, is_training=False)
        
        # Make predictions
        churn_probability = self.churn_model.predict_proba(X)[:, 1]  # Probability of churn
        churn_prediction = self.churn_model.predict(X)
        
        return churn_prediction, churn_probability
    
    def predict_spending(self, customer_data):
        """
        Predict future spending for customers
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Preprocess the data
        X = self.preprocess_data(customer_data, is_training=False)
        
        # Make predictions
        spending_prediction = self.spending_model.predict(X)
        
        return spending_prediction
    
    def predict_customer(self, customer_data):
        """
        Make both churn and spending predictions for a customer
        """
        churn_pred, churn_prob = self.predict_churn(customer_data)
        spending_pred = self.predict_spending(customer_data)
        
        return {
            'will_churn': bool(churn_pred[0]),
            'churn_probability': float(churn_prob[0]),
            'predicted_spending_3months': float(spending_pred[0]),
            'risk_level': 'High' if churn_prob[0] > 0.7 else 'Medium' if churn_prob[0] > 0.3 else 'Low'
        }
    
    def save_models(self, model_dir):
        """
        Save trained models and preprocessors
        """
        if not self.is_trained:
            raise ValueError("Models must be trained before saving")
        
        os.makedirs(model_dir, exist_ok=True)
        
        # Save models
        joblib.dump(self.churn_model, os.path.join(model_dir, 'churn_model.pkl'))
        joblib.dump(self.spending_model, os.path.join(model_dir, 'spending_model.pkl'))
        
        # Save preprocessors
        joblib.dump(self.label_encoders, os.path.join(model_dir, 'label_encoders.pkl'))
        joblib.dump(self.scaler, os.path.join(model_dir, 'scaler.pkl'))
        
        # Save metadata
        metadata = {
            'feature_names': self.feature_names,
            'trained_at': datetime.now().isoformat(),
            'is_trained': self.is_trained
        }
        
        with open(os.path.join(model_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Models saved to {model_dir}")
    
    def load_models(self, model_dir):
        """
        Load trained models and preprocessors
        """
        try:
            # Load models
            self.churn_model = joblib.load(os.path.join(model_dir, 'churn_model.pkl'))
            self.spending_model = joblib.load(os.path.join(model_dir, 'spending_model.pkl'))
            
            # Load preprocessors
            self.label_encoders = joblib.load(os.path.join(model_dir, 'label_encoders.pkl'))
            self.scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))
            
            # Load metadata
            with open(os.path.join(model_dir, 'metadata.json'), 'r') as f:
                metadata = json.load(f)
            
            self.feature_names = metadata['feature_names']
            self.is_trained = metadata['is_trained']
            
            print(f"Models loaded from {model_dir}")
            print(f"Trained at: {metadata['trained_at']}")
            return True
            
        except Exception as e:
            print(f"Error loading models: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    pipeline = EcommerceMLPipeline()
    
    # Train the models (assuming dataset is generated)
    from data_generator import generate_training_dataset, save_dataset
    
    print("Generating training dataset...")
    dataset = generate_training_dataset(1500)
    csv_path, json_path = save_dataset(dataset, "ml_training_dataset.json")
    
    print("\nTraining ML models...")
    metrics = pipeline.train_models(json_path)
    
    print(f"\n✅ Training Complete!")
    print(f"Churn Model Accuracy: {metrics['churn_accuracy']:.2%}")
    print(f"Spending Model R²: {metrics['spending_r2']:.3f}")
    
    # Save the trained models
    pipeline.save_models("trained_models")
    
    print("\n🎯 Models ready for deployment!")
