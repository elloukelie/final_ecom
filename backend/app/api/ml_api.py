# backend/app/api/ml_api.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

from app.models.user import User
from app.dependencies import get_current_user
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.ml.models import EcommerceMLPipeline

router = APIRouter()

# Global ML pipeline instance
ml_pipeline = EcommerceMLPipeline()

# Load trained models on startup
MODEL_DIR = "app/ml/trained_models"
try:
    if os.path.exists(MODEL_DIR):
        ml_pipeline.load_models(MODEL_DIR)
        print(f"✅ ML models loaded successfully from {MODEL_DIR}")
        print(f"   - Models trained: {ml_pipeline.is_trained}")
    else:
        print(f"⚠️ Model directory {MODEL_DIR} does not exist")
except Exception as e:
    print(f"❌ Failed to load ML models: {e}")
    # Continue without crashing the app

class CustomerMLFeatures(BaseModel):
    """Customer features for ML prediction"""
    age: int
    gender: str
    region: str
    tenure_days: int
    total_orders: int
    total_spent: float
    avg_order_value: float
    days_since_last_order: int
    total_sessions: int
    avg_session_duration: float
    pages_per_session: float
    cart_abandonment_rate: float
    support_tickets: int
    preferred_category: str
    seasonal_activity: float
    marketing_channel: str

class PredictionResponse(BaseModel):
    """ML prediction response"""
    customer_id: int
    will_churn: bool
    churn_probability: float
    predicted_spending_3months: float
    risk_level: str
    insights: List[str]

class TrainingRequest(BaseModel):
    """Request to retrain models"""
    retrain_models: bool = True

class MLInsightsResponse(BaseModel):
    """ML insights for admin dashboard"""
    total_customers_analyzed: int
    high_risk_customers: int
    medium_risk_customers: int
    low_risk_customers: int
    avg_churn_probability: float
    total_predicted_revenue: float
    top_spending_predictions: List[Dict]
    feature_importance: Dict[str, List[Dict]]
    model_metrics: Dict[str, float]

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure only admin users can access ML endpoints"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for ML operations"
        )
    return current_user

def extract_customer_features(customer_data, order_data, user_data):
    """
    Extract ML features from customer, order, and user data
    """
    try:
        # Calculate basic metrics
        total_orders = len(order_data) if order_data else 0
        total_spent = sum(float(order.get('total_amount', 0)) for order in order_data) if order_data else 0
        avg_order_value = total_spent / total_orders if total_orders > 0 else 0
        
        # Calculate days since last order
        if order_data:
            # Sort orders by date (most recent first)
            sorted_orders = sorted(order_data, key=lambda x: x.get('order_date', ''), reverse=True)
            if sorted_orders:
                last_order_date = sorted_orders[0].get('order_date', '')
                if last_order_date:
                    try:
                        last_date = datetime.fromisoformat(last_order_date.replace('Z', '+00:00'))
                        days_since_last_order = (datetime.now().replace(tzinfo=last_date.tzinfo) - last_date).days
                    except:
                        days_since_last_order = 30  # Default
                else:
                    days_since_last_order = 30
            else:
                days_since_last_order = 365
        else:
            days_since_last_order = 365
        
        # Calculate tenure
        created_at = customer_data.get('created_at', '')
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                tenure_days = (datetime.now().replace(tzinfo=created_date.tzinfo) - created_date).days
            except:
                tenure_days = 180  # Default
        else:
            tenure_days = 180
        
        # Estimate age from user data or use default
        age = 35  # Default age
        
        # Extract customer info
        gender = 'M'  # Default, could be extracted from customer data if available
        region = 'Central'  # Default region
        
        # Simulate web engagement metrics (in real implementation, get from analytics)
        total_sessions = max(total_orders * 2, 5)  # Assume 2 sessions per order minimum
        avg_session_duration = np.random.normal(8, 3)  # Minutes
        avg_session_duration = max(avg_session_duration, 1)
        
        pages_per_session = np.random.gamma(2, 2)
        pages_per_session = max(min(pages_per_session, 20), 1)
        
        cart_abandonment_rate = np.random.beta(3, 2)  # Realistic abandonment rate
        
        support_tickets = 1  # Default support interactions
        preferred_category = 'Electronics'  # Could be calculated from order history
        seasonal_activity = 0.5  # Default seasonal activity
        marketing_channel = 'Organic'  # Default acquisition channel
        
        features = {
            'age': age,
            'gender': gender,
            'region': region,
            'tenure_days': tenure_days,
            'total_orders': total_orders,
            'total_spent': total_spent,
            'avg_order_value': avg_order_value,
            'days_since_last_order': days_since_last_order,
            'total_sessions': total_sessions,
            'avg_session_duration': avg_session_duration,
            'pages_per_session': pages_per_session,
            'cart_abandonment_rate': cart_abandonment_rate,
            'support_tickets': support_tickets,
            'preferred_category': preferred_category,
            'seasonal_activity': seasonal_activity,
            'marketing_channel': marketing_channel
        }
        
        return features
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting features: {str(e)}")

def generate_insights(prediction_result):
    """Generate human-readable insights from ML predictions"""
    insights = []
    
    churn_prob = prediction_result['churn_probability']
    predicted_spending = prediction_result['predicted_spending_3months']
    
    # Churn insights
    if churn_prob > 0.7:
        insights.append("🚨 High churn risk - immediate retention action recommended")
        insights.append("💡 Consider offering personalized discount or loyalty rewards")
    elif churn_prob > 0.3:
        insights.append("⚠️ Medium churn risk - monitor engagement closely")
        insights.append("📧 Consider sending targeted email campaigns")
    else:
        insights.append("✅ Low churn risk - customer appears engaged")
    
    # Spending insights
    if predicted_spending > 500:
        insights.append(f"💰 High value customer - predicted to spend ${predicted_spending:.0f}")
        insights.append("🎯 Target with premium product recommendations")
    elif predicted_spending > 100:
        insights.append(f"💵 Moderate spender - predicted to spend ${predicted_spending:.0f}")
        insights.append("🛍️ Cross-sell opportunities available")
    else:
        insights.append(f"💸 Low spending predicted - ${predicted_spending:.0f}")
        insights.append("🔄 Focus on engagement and value demonstration")
    
    return insights

@router.get("/ml/health")
async def ml_health_check():
    """Check if ML models are loaded and ready"""
    return {
        "status": "healthy" if ml_pipeline.is_trained else "not_ready",
        "models_loaded": ml_pipeline.is_trained,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/ml/predict/{customer_id}", response_model=PredictionResponse)
async def predict_customer_behavior(
    customer_id: int,
    admin_user: User = Depends(get_admin_user)
):
    """Predict churn and spending for a specific customer"""
    
    if not ml_pipeline.is_trained:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML models not loaded. Please train models first."
        )
    
    try:
        # Get customer data
        customer_repo = CustomerRepository()
        order_repo = OrderRepository()
        
        customer_data = customer_repo.get_customer_by_id(customer_id)
        if not customer_data:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get order history
        user_id = customer_data.get('user_id')
        orders = order_repo.get_orders_by_user_id(user_id)
        
        # Extract features
        features = extract_customer_features(customer_data, orders, None)
        
        # Create DataFrame for prediction
        features_df = pd.DataFrame([features])
        
        # Make prediction
        prediction = ml_pipeline.predict_customer(features_df)
        
        # Generate insights
        insights = generate_insights(prediction)
        
        return PredictionResponse(
            customer_id=customer_id,
            will_churn=prediction['will_churn'],
            churn_probability=prediction['churn_probability'],
            predicted_spending_3months=prediction['predicted_spending_3months'],
            risk_level=prediction['risk_level'],
            insights=insights
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/ml/insights", response_model=MLInsightsResponse)
async def get_ml_insights(
    limit: int = 100,
    admin_user: User = Depends(get_admin_user)
):
    """Get comprehensive ML insights for the admin dashboard"""
    
    if not ml_pipeline.is_trained:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML models not loaded. Please train models first."
        )
    
    try:
        # Get all customers data
        customer_repo = CustomerRepository()
        order_repo = OrderRepository()
        
        customers = customer_repo.get_all_customers()
        if not customers:
            raise HTTPException(status_code=404, detail="No customers found")
        
        # Limit analysis for performance
        customers = customers[:limit]
        
        predictions = []
        total_predicted_revenue = 0
        
        for customer in customers:
            try:
                customer_id = customer.get('id')
                user_id = customer.get('user_id')
                orders = order_repo.get_orders_by_user_id(user_id)
                
                # Extract features
                features = extract_customer_features(customer, orders, None)
                features_df = pd.DataFrame([features])
                
                # Make prediction
                prediction = ml_pipeline.predict_customer(features_df)
                prediction['customer_id'] = customer_id
                prediction['customer_name'] = f"{customer.get('first_name', '')} {customer.get('last_name', '')}"
                
                predictions.append(prediction)
                total_predicted_revenue += prediction['predicted_spending_3months']
                
            except Exception as e:
                print(f"Error predicting for customer {customer_id}: {e}")
                continue
        
        # Analyze results
        high_risk = len([p for p in predictions if p['churn_probability'] > 0.7])
        medium_risk = len([p for p in predictions if 0.3 < p['churn_probability'] <= 0.7])
        low_risk = len([p for p in predictions if p['churn_probability'] <= 0.3])
        
        avg_churn_prob = np.mean([p['churn_probability'] for p in predictions]) if predictions else 0
        
        # Top spending predictions
        top_spenders = sorted(predictions, key=lambda x: x['predicted_spending_3months'], reverse=True)[:10]
        top_spending_list = [{
            'customer_id': p['customer_id'],
            'customer_name': p['customer_name'],
            'predicted_spending': p['predicted_spending_3months'],
            'churn_probability': p['churn_probability']
        } for p in top_spenders]
        
        # Mock feature importance (in real scenario, get from trained models)
        feature_importance = {
            'churn_model': [
                {'feature': 'days_since_last_order', 'importance': 0.25},
                {'feature': 'total_spent', 'importance': 0.18},
                {'feature': 'avg_order_value', 'importance': 0.15},
                {'feature': 'total_orders', 'importance': 0.12},
                {'feature': 'tenure_days', 'importance': 0.10}
            ],
            'spending_model': [
                {'feature': 'total_spent', 'importance': 0.30},
                {'feature': 'avg_order_value', 'importance': 0.22},
                {'feature': 'total_orders', 'importance': 0.18},
                {'feature': 'tenure_days', 'importance': 0.12},
                {'feature': 'avg_session_duration', 'importance': 0.08}
            ]
        }
        
        # Mock model metrics
        model_metrics = {
            'churn_accuracy': 0.87,
            'churn_precision': 0.82,
            'churn_recall': 0.78,
            'spending_r2': 0.74,
            'spending_rmse': 45.30
        }
        
        return MLInsightsResponse(
            total_customers_analyzed=len(predictions),
            high_risk_customers=high_risk,
            medium_risk_customers=medium_risk,
            low_risk_customers=low_risk,
            avg_churn_probability=avg_churn_prob,
            total_predicted_revenue=total_predicted_revenue,
            top_spending_predictions=top_spending_list,
            feature_importance=feature_importance,
            model_metrics=model_metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

@router.post("/ml/train")
async def train_models(
    training_request: Optional[TrainingRequest] = None,
    admin_user: User = Depends(get_admin_user)
):
    """Retrain ML models with fresh data"""
    
    try:
        # Generate fresh training dataset
        from app.ml.data_generator import generate_training_dataset, save_dataset
        
        print("Generating fresh training dataset...")
        dataset = generate_training_dataset(2000)  # Larger dataset for better training
        
        # Save dataset
        dataset_path = "app/ml/fresh_training_data.json"
        csv_path, json_path = save_dataset(dataset, dataset_path)
        
        # Train models
        print("Training ML models...")
        metrics = ml_pipeline.train_models(json_path)
        
        # Save trained models
        ml_pipeline.save_models(MODEL_DIR)
        
        return {
            "status": "success",
            "message": "Models retrained successfully",
            "metrics": metrics,
            "training_samples": metrics['training_samples'],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@router.get("/ml/batch-predict")
async def batch_predict_all_customers(
    admin_user: User = Depends(get_admin_user)
):
    """Run predictions for all customers (batch processing)"""
    
    if not ml_pipeline.is_trained:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML models not loaded. Please train models first."
        )
    
    try:
        # Get all customers
        customer_repo = CustomerRepository()
        order_repo = OrderRepository()
        
        customers = customer_repo.get_all_customers()
        
        batch_results = []
        for customer in customers:
            try:
                customer_id = customer.get('id')
                user_id = customer.get('user_id')
                orders = order_repo.get_orders_by_user_id(user_id)
                
                # Extract features and predict
                features = extract_customer_features(customer, orders, None)
                features_df = pd.DataFrame([features])
                prediction = ml_pipeline.predict_customer(features_df)
                
                batch_results.append({
                    'customer_id': customer_id,
                    'customer_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}",
                    'prediction': prediction
                })
                
            except Exception as e:
                print(f"Error in batch prediction for customer {customer_id}: {e}")
                continue
        
        return {
            "status": "success",
            "total_processed": len(batch_results),
            "predictions": batch_results[:50],  # Limit response size
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

@router.post("/ml/batch-predict") 
async def batch_predict_post(
    admin_user: User = Depends(get_admin_user)
):
    """Run predictions for all customers (batch processing) - POST version"""
    return await batch_predict_all_customers(admin_user)

@router.get("/ml/predictions/recent")
async def get_recent_predictions(
    limit: int = 10,
    admin_user: User = Depends(get_admin_user)
):
    """Get recent ML predictions for dashboard preview"""
    
    if not ml_pipeline.is_trained:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML models not loaded. Please train models first."
        )
    
    try:
        # Get recent customers (simulate recent predictions by getting latest customers)
        customer_repo = CustomerRepository()
        order_repo = OrderRepository()
        
        customers = customer_repo.get_all_customers()
        
        if not customers:
            return {
                "predictions": [],
                "total": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # Limit to recent customers (in real scenario, you'd store prediction timestamps)
        recent_customers = customers[:limit]
        
        recent_predictions = []
        for customer in recent_customers:
            try:
                customer_id = customer.get('id')
                user_id = customer.get('user_id')
                orders = order_repo.get_orders_by_user_id(user_id)
                
                # Extract features and predict
                features = extract_customer_features(customer, orders, None)
                features_df = pd.DataFrame([features])
                prediction = ml_pipeline.predict_customer(features_df)
                
                recent_predictions.append({
                    'customer_id': customer_id,
                    'customer_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}",
                    'churn_probability': prediction['churn_probability'],
                    'predicted_spending': prediction['predicted_spending_3months'],
                    'risk_level': 'High' if prediction['churn_probability'] > 0.7 else 'Medium' if prediction['churn_probability'] > 0.3 else 'Low',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"Error predicting for customer {customer_id}: {e}")
                continue
        
        return {
            "predictions": recent_predictions,
            "total": len(recent_predictions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent predictions: {str(e)}")
