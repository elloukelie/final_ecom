# backend/app/ml/data_generator.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json

def generate_training_dataset(num_customers=1000):
    """
    Generate a realistic e-commerce training dataset for ML models
    
    Features:
    - Customer demographics and behavior
    - Purchase history and patterns
    - Website interaction data
    - Target variables: churn probability and spending prediction
    """
    
    np.random.seed(42)  # For reproducible results
    random.seed(42)
    
    # Customer demographics
    customer_ids = range(1, num_customers + 1)
    
    # Age distribution (realistic e-commerce demographics)
    ages = np.random.normal(35, 12, num_customers).astype(int)
    ages = np.clip(ages, 18, 80)
    
    # Gender distribution
    genders = np.random.choice(['M', 'F', 'Other'], num_customers, p=[0.45, 0.52, 0.03])
    
    # Geographic regions (affects shipping costs and behavior)
    regions = np.random.choice(['North', 'South', 'East', 'West', 'Central'], 
                              num_customers, p=[0.2, 0.25, 0.2, 0.25, 0.1])
    
    # Account tenure (days since registration)
    tenure_days = np.random.exponential(180, num_customers).astype(int)
    tenure_days = np.clip(tenure_days, 1, 1095)  # Max 3 years
    
    # Purchase behavior features
    total_orders = np.random.poisson(8, num_customers)  # Average 8 orders per customer
    total_orders = np.clip(total_orders, 0, 50)
    
    # Total spent (correlated with number of orders)
    base_spending = total_orders * np.random.normal(75, 25, num_customers)
    total_spent = np.maximum(base_spending, 0)
    
    # Average order value
    avg_order_value = np.where(total_orders > 0, total_spent / total_orders, 0)
    
    # Days since last order
    days_since_last_order = np.random.exponential(30, num_customers).astype(int)
    days_since_last_order = np.clip(days_since_last_order, 0, 365)
    
    # Website engagement metrics
    total_sessions = total_orders + np.random.poisson(15, num_customers)  # More sessions than orders
    avg_session_duration = np.random.normal(8.5, 4, num_customers)  # Minutes
    avg_session_duration = np.maximum(avg_session_duration, 0.5)
    
    # Pages per session
    pages_per_session = np.random.gamma(2, 2, num_customers)
    pages_per_session = np.clip(pages_per_session, 1, 20)
    
    # Cart abandonment rate
    cart_abandonment_rate = np.random.beta(3, 2, num_customers)  # Typically higher
    
    # Customer service interactions
    support_tickets = np.random.poisson(1.5, num_customers)
    
    # Product preferences (simplified)
    preferred_categories = np.random.choice(['Electronics', 'Clothing', 'Home', 'Books', 'Sports'], 
                                           num_customers)
    
    # Seasonal activity (0-1 scale)
    seasonal_activity = np.random.beta(2, 2, num_customers)
    
    # Marketing channel (how they found us)
    marketing_channels = np.random.choice(['Organic', 'Paid_Search', 'Social', 'Email', 'Direct'], 
                                         num_customers, p=[0.3, 0.25, 0.2, 0.15, 0.1])
    
    # Create target variables
    
    # CHURN PREDICTION (will customer be inactive in next 3 months?)
    # Factors that increase churn probability:
    churn_probability = 0.1  # Base probability
    
    # Higher churn if:
    churn_probability += 0.3 * (days_since_last_order > 90) / 100  # Long time since last order
    churn_probability += 0.2 * (total_orders < 3) / 100  # Few total orders
    churn_probability += 0.15 * (avg_session_duration < 3) / 100  # Short sessions
    churn_probability += 0.2 * (cart_abandonment_rate > 0.7) / 100  # High abandonment
    churn_probability += 0.1 * (support_tickets > 3) / 100  # Many support issues
    
    # Lower churn if:
    churn_probability -= 0.3 * (total_spent > 500) / 100  # High value customers
    churn_probability -= 0.2 * (total_orders > 10) / 100  # Frequent buyers
    churn_probability -= 0.1 * (tenure_days > 365) / 100  # Long-term customers
    
    # Convert to binary outcome
    will_churn = np.random.binomial(1, np.clip(churn_probability, 0, 1), num_customers)
    
    # SPENDING PREDICTION (how much will customer spend in next 3 months?)
    # Base spending based on historical behavior
    future_spending_base = avg_order_value * np.random.poisson(2, num_customers)  # Expected 2 orders
    
    # Adjustments based on customer behavior
    spending_multiplier = 1.0
    spending_multiplier += 0.5 * (total_spent > 1000)  # High spenders continue
    spending_multiplier += 0.3 * (tenure_days > 365)  # Loyal customers
    spending_multiplier += 0.2 * (avg_session_duration > 10)  # Engaged users
    spending_multiplier -= 0.6 * will_churn  # Churning customers spend less
    spending_multiplier -= 0.3 * (days_since_last_order > 60)  # Inactive customers
    
    predicted_spending = future_spending_base * spending_multiplier
    predicted_spending = np.maximum(predicted_spending, 0)
    
    # Add some noise for realism
    predicted_spending *= np.random.normal(1, 0.2, num_customers)
    predicted_spending = np.maximum(predicted_spending, 0)
    
    # Create the dataset
    dataset = pd.DataFrame({
        'customer_id': customer_ids,
        'age': ages,
        'gender': genders,
        'region': regions,
        'tenure_days': tenure_days,
        'total_orders': total_orders,
        'total_spent': total_spent.round(2),
        'avg_order_value': avg_order_value.round(2),
        'days_since_last_order': days_since_last_order,
        'total_sessions': total_sessions,
        'avg_session_duration': avg_session_duration.round(2),
        'pages_per_session': pages_per_session.round(2),
        'cart_abandonment_rate': cart_abandonment_rate.round(3),
        'support_tickets': support_tickets,
        'preferred_category': preferred_categories,
        'seasonal_activity': seasonal_activity.round(3),
        'marketing_channel': marketing_channels,
        'will_churn': will_churn,
        'predicted_spending_3months': predicted_spending.round(2)
    })
    
    return dataset

def save_dataset(dataset, filepath):
    """Save the dataset to CSV and JSON formats"""
    # Save as CSV
    csv_path = filepath.replace('.json', '.csv')
    dataset.to_csv(csv_path, index=False)
    print(f"Dataset saved to {csv_path}")
    
    # Save as JSON for API usage
    dataset_dict = dataset.to_dict('records')
    with open(filepath, 'w') as f:
        json.dump(dataset_dict, f, indent=2)
    print(f"Dataset saved to {filepath}")
    
    return csv_path, filepath

if __name__ == "__main__":
    # Generate training dataset
    print("Generating training dataset...")
    dataset = generate_training_dataset(1500)  # 1500 customers for good training
    
    # Display basic statistics
    print("\nDataset Statistics:")
    print(f"Total customers: {len(dataset)}")
    print(f"Churn rate: {dataset['will_churn'].mean():.2%}")
    print(f"Average predicted spending: ${dataset['predicted_spending_3months'].mean():.2f}")
    print(f"Average total spent: ${dataset['total_spent'].mean():.2f}")
    
    # Save the dataset
    csv_path, json_path = save_dataset(dataset, "ml_training_dataset.json")
    
    print(f"\nDataset ready for training!")
    print(f"Features: {len(dataset.columns) - 2}")  # Excluding target variables
    print(f"Samples: {len(dataset)}")
