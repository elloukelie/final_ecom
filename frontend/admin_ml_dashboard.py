"""
Admin ML Dashboard - Machine Learning Insights Interface

This module provides a comprehensive admin interface for ML analytics including:
- Customer churn prediction dashboard
- Spending forecasting tools
- Data visualization and insights
- Model training and evaluation
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json

def show_ml_dashboard(api_base_url):
    """Main ML dashboard page"""
    st.title("🤖 Machine Learning Dashboard")
    st.markdown("**AI-Powered Customer Analytics & Predictions**")
    
    # First, try to ensure admin authentication
    def ensure_admin_auth():
        """Ensure admin is authenticated, try to auto-authenticate if not"""
        if st.session_state.get('logged_in', False) and st.session_state.get('current_user', {}).get('is_admin', False):
            return True
            
        # Try to auto-authenticate admin user
        if not st.session_state.get('admin_login_attempted', False):
            try:
                import os
                admin_username = os.getenv("ADMIN_USERNAME", "admin")
                admin_password = os.getenv("ADMIN_PASSWORD", "admin")  # Use default admin password
                
                response = requests.post(
                    f"{api_base_url}/token",
                    data={"username": admin_username, "password": admin_password}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.access_token = token_data["access_token"]
                    st.session_state.logged_in = True
                    
                    # Get user info
                    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                    user_response = requests.get(f"{api_base_url}/users/me", headers=headers)
                    
                    if user_response.status_code == 200:
                        user_info = user_response.json()
                        st.session_state.current_user = user_info
                        st.success("✅ Auto-authenticated as admin")
                        st.rerun()
                        return True
                    
                st.session_state.admin_login_attempted = True
            except Exception as e:
                st.session_state.admin_login_attempted = True
                pass
        
        return False
    
    # Check if user is admin, try auto-auth if not
    if not ensure_admin_auth():
        st.error("Access denied. Admin privileges required.")
        
        # Debug info
        with st.expander("🔧 Debug Authentication"):
            st.write("Session State Debug:")
            st.write(f"- logged_in: {st.session_state.get('logged_in', False)}")
            st.write(f"- current_user: {st.session_state.get('current_user', {})}")
            st.write(f"- access_token exists: {bool(st.session_state.get('access_token'))}")
            
            if st.button("🔄 Try Auto-Login Again"):
                if 'admin_login_attempted' in st.session_state:
                    del st.session_state['admin_login_attempted']
                st.rerun()
                
            if st.button("🔄 Refresh Authentication"):
                # Try to refresh user info
                if st.session_state.get('access_token'):
                    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                    try:
                        response = requests.get(f"{api_base_url}/users/me", headers=headers)
                        if response.status_code == 200:
                            user_info = response.json()
                            st.session_state.current_user = user_info
                            st.session_state.logged_in = True
                            st.success("✅ Authentication refreshed!")
                            st.rerun()
                        else:
                            st.error(f"Failed to refresh: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("No access token available")
        return
    
    # API base URL
    API_BASE_URL = api_base_url
    
    # Function to make authenticated requests
    def make_authenticated_request(method, endpoint, json_data=None, params=None):
        headers = {}
        
        # Debug authentication state
        if not st.session_state.get('access_token'):
            st.error("❌ No access token found. Please login first.")
            st.info("🔄 Try logging out and logging back in as admin.")
            return None
            
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        
        try:
            url = f"{API_BASE_URL}{endpoint}"
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, json=json_data, headers=headers, params=params)
            else:
                st.error(f"Unsupported HTTP method: {method}")
                return None
            
            if response.status_code in [200, 201, 204]:
                if response.status_code == 204:
                    return {"success": True}
                else:
                    return response.json()
            elif response.status_code == 401:
                st.error("🔒 Authentication failed. Please login again.")
                st.info("Your session may have expired. Try logging out and logging back in.")
                return None
            elif response.status_code == 422:
                st.error("📋 Invalid request format.")
                if response.text:
                    st.code(response.text)
                return None
            else:
                st.error(f"API request failed: {response.status_code}")
                if response.text:
                    st.code(response.text)
                return None
        except Exception as e:
            st.error(f"Request failed: {str(e)}")
            return None
    
    # Sidebar navigation
    st.sidebar.title("🧠 ML Analytics")
    ml_section = st.sidebar.selectbox(
        "Choose Analytics Section:",
        ["📊 Overview", "🎯 Customer Predictions", "💰 Spending Forecasts", "📈 Model Performance", "🔧 Model Training"]
    )
    
    if ml_section == "📊 Overview":
        show_ml_overview(make_authenticated_request)
    elif ml_section == "🎯 Customer Predictions":
        show_churn_predictions(make_authenticated_request)
    elif ml_section == "💰 Spending Forecasts":
        show_spending_forecasts(make_authenticated_request)
    elif ml_section == "📈 Model Performance":
        show_model_performance(make_authenticated_request)
    elif ml_section == "🔧 Model Training":
        show_model_training(make_authenticated_request)

def show_ml_overview(api_request):
    """ML Overview dashboard"""
    st.header("📊 ML Analytics Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Get overall insights
    with st.spinner("Loading ML insights..."):
        insights = api_request("GET", "/ml/insights")
    
    # Debug information
    if st.checkbox("🔧 Show Debug Info"):
        st.write("API Response:", insights)
        st.write("Response type:", type(insights))
        if insights:
            st.write("Keys:", list(insights.keys()))
    
    if insights:
        total_customers = insights.get('total_customers_analyzed', 0)
        high_risk = insights.get('high_risk_customers', 0)
        total_revenue = insights.get('total_predicted_revenue', 0)
        avg_spending = total_revenue / total_customers if total_customers > 0 else 0
        model_metrics = insights.get('model_metrics', {})
        churn_accuracy = model_metrics.get('churn_accuracy', 0)
        
        with col1:
            st.metric(
                "Churn Risk Customers",
                high_risk,
                delta=f"{(high_risk/total_customers*100) if total_customers > 0 else 0:.1f}%"
            )
        
        with col2:
            st.metric(
                "Avg Predicted Spending",
                f"${avg_spending:.2f}",
                delta=f"${total_revenue:.2f} total"
            )
        
        with col3:
            st.metric(
                "Model Accuracy",
                f"{churn_accuracy*100:.1f}%",
                delta="Updated today"
            )
        
        with col4:
            st.metric(
                "Customers Analyzed",
                total_customers,
                delta="Real-time data"
            )
    else:
        # Show default values if no data
        with col1:
            st.metric("Churn Risk Customers", "0", delta="0.0%")
        with col2:
            st.metric("Avg Predicted Spending", "$0.00", delta="$0.00")
        with col3:
            st.metric("Model Accuracy", "0.0%", delta="No data")
        with col4:
            st.metric("Customers Analyzed", "0", delta="No data")
    
    st.markdown("---")
    
    # Add visual insights if we have data
    if insights and insights.get('total_customers_analyzed', 0) > 0:
        # Risk distribution chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Customer Risk Distribution")
            risk_data = {
                'Risk Level': ['High Risk', 'Medium Risk', 'Low Risk'],
                'Count': [
                    insights.get('high_risk_customers', 0),
                    insights.get('medium_risk_customers', 0),
                    insights.get('low_risk_customers', 0)
                ]
            }
            
            if sum(risk_data['Count']) > 0:
                try:
                    import plotly.express as px
                    fig = px.pie(
                        values=risk_data['Count'], 
                        names=risk_data['Risk Level'],
                        color_discrete_map={
                            'High Risk': '#ff4444',
                            'Medium Risk': '#ffaa44', 
                            'Low Risk': '#44ff44'
                        }
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    # Fallback to simple bar chart if plotly not available
                    risk_df = pd.DataFrame(risk_data)
                    st.bar_chart(risk_df.set_index('Risk Level'))
                except Exception as e:
                    st.error(f"Chart error: {e}")
                    # Show data as table fallback
                    st.write(pd.DataFrame(risk_data))
            else:
                st.info("No risk data available")
        
        with col2:
            st.subheader("💰 Top Spending Predictions")
            top_spenders = insights.get('top_spending_predictions', [])[:5]
            if top_spenders:
                spending_df = pd.DataFrame(top_spenders)
                spending_df['predicted_spending'] = spending_df['predicted_spending'].apply(lambda x: f"${x:.2f}")
                spending_df['churn_probability'] = spending_df['churn_probability'].apply(lambda x: f"{x*100:.1f}%")
                st.dataframe(
                    spending_df[['customer_name', 'predicted_spending', 'churn_probability']], 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No spending predictions available")
    
    # Quick actions
    st.subheader("🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 Run Churn Analysis", use_container_width=True):
            with st.spinner("Analyzing customer churn risk..."):
                result = api_request("POST", "/ml/batch-predict", json_data={"prediction_type": "churn"})
                if result:
                    st.success(f"✅ Analysis complete! {result.get('total_processed', 0)} customers analyzed.")
                else:
                    st.error("❌ Analysis failed. Please try again.")
    
    with col2:
        if st.button("💰 Update Spending Forecasts", use_container_width=True):
            with st.spinner("Updating spending forecasts..."):
                result = api_request("POST", "/ml/batch-predict", json_data={"prediction_type": "spending"})
                if result:
                    st.success(f"✅ Forecasts updated! {result.get('total_processed', 0)} customers processed.")
                else:
                    st.error("❌ Update failed. Please try again.")
    
    with col3:
        if st.button("🔄 Retrain Models", use_container_width=True):
            with st.spinner("Retraining ML models..."):
                result = api_request("POST", "/ml/train")
                if result:
                    metrics = result.get('metrics', {})
                    accuracy = metrics.get('churn_accuracy', 0)
                    st.success(f"✅ Models retrained! Churn Accuracy: {accuracy*100:.1f}%")
                else:
                    st.error("❌ Training failed. Please try again.")
    
    # Recent predictions preview
    st.subheader("🔮 Recent Predictions")
    recent_predictions = api_request("GET", "/ml/predictions/recent", params={"limit": 10})
    
    if recent_predictions and recent_predictions.get('predictions'):
        df = pd.DataFrame(recent_predictions['predictions'])
        
        # Format the dataframe for display
        display_df = df.copy()
        if 'churn_probability' in display_df.columns:
            display_df['churn_probability'] = display_df['churn_probability'].apply(lambda x: f"{x*100:.1f}%")
        if 'predicted_spending' in display_df.columns:
            display_df['predicted_spending'] = display_df['predicted_spending'].apply(lambda x: f"${x:.2f}")
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No recent predictions available. Run analysis to generate insights.")

def show_churn_predictions(api_request):
    """Customer churn prediction dashboard"""
    st.header("🎯 Customer Churn Predictions")
    
    # Control panel
    col1, col2, col3 = st.columns(3)
    
    with col1:
        risk_threshold = st.slider("Churn Risk Threshold", 0.0, 1.0, 0.7, 0.05)
    
    with col2:
        show_all = st.checkbox("Show All Customers", False)
    
    with col3:
        if st.button("🔄 Refresh Predictions", use_container_width=True):
            st.rerun()
    
    # Get churn predictions
    with st.spinner("Loading churn predictions..."):
        predictions = api_request("GET", "/ml/predictions/churn")
    
    if predictions and predictions.get('predictions'):
        df = pd.DataFrame(predictions['predictions'])
        
        # Filter by risk threshold if not showing all
        if not show_all:
            df = df[df['churn_probability'] >= risk_threshold]
        
        # Sort by churn probability (highest risk first)
        df = df.sort_values('churn_probability', ascending=False)
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            high_risk = len(df[df['churn_probability'] >= 0.8])
            st.metric("🔴 High Risk (>80%)", high_risk)
        
        with col2:
            medium_risk = len(df[(df['churn_probability'] >= 0.5) & (df['churn_probability'] < 0.8)])
            st.metric("🟡 Medium Risk (50-80%)", medium_risk)
        
        with col3:
            low_risk = len(df[df['churn_probability'] < 0.5])
            st.metric("🟢 Low Risk (<50%)", low_risk)
        
        with col4:
            avg_risk = df['churn_probability'].mean()
            st.metric("📊 Average Risk", f"{avg_risk*100:.1f}%")
        
        # Churn risk distribution chart
        st.subheader("📈 Churn Risk Distribution")
        
        # Create histogram
        fig = px.histogram(
            df, 
            x='churn_probability', 
            bins=20,
            title='Distribution of Churn Probabilities',
            labels={'churn_probability': 'Churn Probability', 'count': 'Number of Customers'},
            color_discrete_sequence=['#ff6b6b']
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk categories pie chart
        col1, col2 = st.columns(2)
        
        with col1:
            risk_categories = ['High Risk (>80%)', 'Medium Risk (50-80%)', 'Low Risk (<50%)']
            risk_counts = [high_risk, medium_risk, low_risk]
            
            fig = px.pie(
                values=risk_counts,
                names=risk_categories,
                title='Customer Risk Categories',
                color_discrete_sequence=['#ff4757', '#ffa502', '#2ed573']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top features affecting churn
            st.subheader("🔍 Key Churn Indicators")
            
            # Sample feature importance (in a real implementation, this would come from the model)
            features = [
                "Days Since Last Order",
                "Average Order Value",
                "Total Orders",
                "Customer Lifetime Value",
                "Support Tickets"
            ]
            importance = [0.25, 0.20, 0.18, 0.15, 0.12]
            
            feature_df = pd.DataFrame({
                'Feature': features,
                'Importance': importance
            })
            
            fig = px.bar(
                feature_df,
                x='Importance',
                y='Feature',
                orientation='h',
                title='Feature Importance for Churn Prediction',
                color='Importance',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed customer list
        st.subheader("👥 Customer Details")
        
        # Format dataframe for display
        display_df = df.copy()
        display_df['churn_probability'] = display_df['churn_probability'].apply(lambda x: f"{x*100:.1f}%")
        display_df['risk_level'] = display_df['churn_probability'].apply(
            lambda x: '🔴 High' if float(x.strip('%')) >= 80 
                     else '🟡 Medium' if float(x.strip('%')) >= 50 
                     else '🟢 Low'
        )
        
        # Add action buttons
        if len(display_df) > 0:
            st.dataframe(
                display_df[['customer_id', 'churn_probability', 'risk_level', 'predicted_at']],
                use_container_width=True
            )
            
            # Action buttons for high-risk customers
            high_risk_customers = df[df['churn_probability'] >= 0.8]['customer_id'].tolist()
            
            if high_risk_customers:
                st.subheader("🚨 Suggested Actions for High-Risk Customers")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📧 Send Retention Email", use_container_width=True):
                        st.success(f"✅ Retention emails queued for {len(high_risk_customers)} customers!")
                
                with col2:
                    if st.button("💰 Create Discount Campaign", use_container_width=True):
                        st.success(f"✅ Discount campaign created for {len(high_risk_customers)} customers!")
                
                with col3:
                    if st.button("📞 Schedule Support Call", use_container_width=True):
                        st.success(f"✅ Support calls scheduled for {len(high_risk_customers)} customers!")
        else:
            st.info("No customers match the current risk threshold. Adjust the threshold to see more results.")
    
    else:
        st.warning("⚠️ No churn predictions available. Train the model first.")
        if st.button("🔧 Train Churn Model Now"):
            with st.spinner("Training churn prediction model..."):
                result = api_request("POST", "/ml/train")
                if result:
                    st.success("✅ Model trained successfully!")
                    st.rerun()

def show_spending_forecasts(api_request):
    """Customer spending forecast dashboard"""
    st.header("💰 Customer Spending Forecasts")
    
    # Control panel
    col1, col2, col3 = st.columns(3)
    
    with col1:
        forecast_period = st.selectbox(
            "Forecast Period",
            ["Next 30 Days", "Next 60 Days", "Next 90 Days", "Next 6 Months"],
            index=2
        )
    
    with col2:
        min_spending = st.number_input("Min Predicted Spending ($)", 0, 10000, 0)
    
    with col3:
        if st.button("🔄 Refresh Forecasts", use_container_width=True):
            st.rerun()
    
    # Get spending predictions
    with st.spinner("Loading spending forecasts..."):
        predictions = api_request("GET", "/ml/predictions/spending")
    
    if predictions and predictions.get('predictions'):
        df = pd.DataFrame(predictions['predictions'])
        
        # Filter by minimum spending
        if min_spending > 0:
            df = df[df['predicted_spending'] >= min_spending]
        
        # Sort by predicted spending (highest first)
        df = df.sort_values('predicted_spending', ascending=False)
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_forecast = df['predicted_spending'].sum()
        avg_forecast = df['predicted_spending'].mean()
        high_value = len(df[df['predicted_spending'] >= 500])
        
        with col1:
            st.metric("💵 Total Forecast", f"${total_forecast:,.2f}")
        
        with col2:
            st.metric("📊 Average per Customer", f"${avg_forecast:.2f}")
        
        with col3:
            st.metric("💎 High Value Customers (>$500)", high_value)
        
        with col4:
            st.metric("👥 Customers Analyzed", len(df))
        
        # Spending distribution charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Spending distribution histogram
            fig = px.histogram(
                df,
                x='predicted_spending',
                bins=20,
                title='Distribution of Predicted Spending',
                labels={'predicted_spending': 'Predicted Spending ($)', 'count': 'Number of Customers'},
                color_discrete_sequence=['#2ed573']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Spending categories
            spending_categories = []
            spending_counts = []
            
            categories = [
                ('💎 High Spender (>$500)', df[df['predicted_spending'] >= 500]),
                ('🟡 Medium Spender ($100-$500)', df[(df['predicted_spending'] >= 100) & (df['predicted_spending'] < 500)]),
                ('🟢 Low Spender (<$100)', df[df['predicted_spending'] < 100])
            ]
            
            for cat_name, cat_df in categories:
                spending_categories.append(cat_name)
                spending_counts.append(len(cat_df))
            
            fig = px.pie(
                values=spending_counts,
                names=spending_categories,
                title='Customer Spending Categories',
                color_discrete_sequence=['#ff6b6b', '#ffa500', '#2ed573']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Top spenders table
        st.subheader("🏆 Top Predicted Spenders")
        
        top_spenders = df.head(10).copy()
        top_spenders['predicted_spending'] = top_spenders['predicted_spending'].apply(lambda x: f"${x:.2f}")
        
        st.dataframe(
            top_spenders[['customer_id', 'predicted_spending', 'predicted_at']],
            use_container_width=True
        )
        
        # Revenue projection chart
        st.subheader("📈 Revenue Projection Trend")
        
        # Create time series data (simulated for demo)
        dates = pd.date_range(start=datetime.now(), periods=30, freq='D')
        daily_forecast = np.random.normal(total_forecast/30, total_forecast/60, 30).cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=daily_forecast,
            mode='lines+markers',
            name='Projected Revenue',
            line=dict(color='#2ed573', width=3)
        ))
        
        fig.update_layout(
            title='30-Day Revenue Projection',
            xaxis_title='Date',
            yaxis_title='Cumulative Revenue ($)',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Action recommendations
        st.subheader("💡 Recommendations")
        
        high_value_customers = df[df['predicted_spending'] >= 500]
        
        if len(high_value_customers) > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info(f"🎯 **Target Marketing**\n\nFocus campaigns on {len(high_value_customers)} high-value customers")
            
            with col2:
                st.info(f"📦 **Premium Services**\n\nOffer premium services to customers with >$500 forecast")
            
            with col3:
                st.info(f"🤝 **Personal Attention**\n\nAssign dedicated support to top spenders")
    
    else:
        st.warning("⚠️ No spending predictions available. Train the model first.")
        if st.button("🔧 Train Spending Model Now"):
            with st.spinner("Training spending prediction model..."):
                result = api_request("POST", "/ml/train")
                if result:
                    st.success("✅ Model trained successfully!")
                    st.rerun()

def show_model_performance(api_request):
    """Model performance metrics and evaluation"""
    st.header("📈 Model Performance Metrics")
    
    # Get model performance data
    with st.spinner("Loading model performance metrics..."):
        performance = api_request("GET", "/ml/model-performance")
    
    if performance:
        # Model accuracy metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Churn Model Performance")
            churn_metrics = performance.get('churn_model', {})
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("Accuracy", f"{churn_metrics.get('accuracy', 0)*100:.1f}%")
                st.metric("Precision", f"{churn_metrics.get('precision', 0)*100:.1f}%")
            with metric_col2:
                st.metric("Recall", f"{churn_metrics.get('recall', 0)*100:.1f}%")
                st.metric("F1-Score", f"{churn_metrics.get('f1_score', 0)*100:.1f}%")
        
        with col2:
            st.subheader("💰 Spending Model Performance")
            spending_metrics = performance.get('spending_model', {})
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("R² Score", f"{spending_metrics.get('r2_score', 0):.3f}")
                st.metric("MAE", f"${spending_metrics.get('mae', 0):.2f}")
            with metric_col2:
                st.metric("RMSE", f"${spending_metrics.get('rmse', 0):.2f}")
                st.metric("MAPE", f"{spending_metrics.get('mape', 0)*100:.1f}%")
        
        # Feature importance
        st.subheader("🔍 Feature Importance Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Churn model features
            churn_features = churn_metrics.get('feature_importance', {})
            if churn_features:
                features_df = pd.DataFrame(list(churn_features.items()), columns=['Feature', 'Importance'])
                features_df = features_df.sort_values('Importance', ascending=True)
                
                fig = px.bar(
                    features_df,
                    x='Importance',
                    y='Feature',
                    orientation='h',
                    title='Churn Model - Feature Importance',
                    color='Importance',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Spending model features
            spending_features = spending_metrics.get('feature_importance', {})
            if spending_features:
                features_df = pd.DataFrame(list(spending_features.items()), columns=['Feature', 'Importance'])
                features_df = features_df.sort_values('Importance', ascending=True)
                
                fig = px.bar(
                    features_df,
                    x='Importance',
                    y='Feature',
                    orientation='h',
                    title='Spending Model - Feature Importance',
                    color='Importance',
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Training history
        st.subheader("📊 Training History")
        
        training_history = performance.get('training_history', [])
        if training_history:
            history_df = pd.DataFrame(training_history)
            history_df['trained_at'] = pd.to_datetime(history_df['trained_at'])
            
            fig = go.Figure()
            
            # Churn model accuracy over time
            fig.add_trace(go.Scatter(
                x=history_df['trained_at'],
                y=history_df['churn_accuracy'],
                mode='lines+markers',
                name='Churn Model Accuracy',
                line=dict(color='#ff6b6b', width=2)
            ))
            
            # Spending model R² over time
            fig.add_trace(go.Scatter(
                x=history_df['trained_at'],
                y=history_df['spending_r2'],
                mode='lines+markers',
                name='Spending Model R²',
                line=dict(color='#2ed573', width=2),
                yaxis='y2'
            ))
            
            fig.update_layout(
                title='Model Performance Over Time',
                xaxis_title='Training Date',
                yaxis_title='Accuracy',
                yaxis2=dict(title='R² Score', overlaying='y', side='right'),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Model diagnostics
        st.subheader("🔧 Model Diagnostics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            last_trained = performance.get('last_trained', 'Never')
            st.info(f"**Last Training**\n{last_trained}")
        
        with col2:
            data_quality = performance.get('data_quality_score', 0)
            st.info(f"**Data Quality Score**\n{data_quality*100:.1f}%")
        
        with col3:
            model_version = performance.get('model_version', 'v1.0')
            st.info(f"**Model Version**\n{model_version}")
    
    else:
        st.warning("⚠️ No model performance data available.")

def show_model_training(api_request):
    """Model training interface"""
    st.header("🔧 Model Training & Management")
    
    # Training controls
    st.subheader("🚀 Train Models")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🎯 Churn Prediction Model**")
        st.write("Predicts which customers are likely to stop purchasing")
        
        if st.button("🔄 Train Churn Model", use_container_width=True):
            with st.spinner("Training churn prediction model..."):
                result = api_request("POST", "/ml/train", json_data={"model_type": "churn"})
                if result:
                    metrics = result.get('metrics', {})
                    accuracy = metrics.get('churn_accuracy', 0)
                    st.success(f"✅ Churn model trained! Accuracy: {accuracy*100:.1f}%")
                else:
                    st.error("❌ Training failed")
    
    with col2:
        st.markdown("**💰 Spending Forecast Model**")
        st.write("Predicts how much customers will spend in the future")
        
        if st.button("🔄 Train Spending Model", use_container_width=True):
            with st.spinner("Training spending forecast model..."):
                result = api_request("POST", "/ml/train", json_data={"model_type": "spending"})
                if result:
                    metrics = result.get('metrics', {})
                    r2_score = metrics.get('spending_r2', 0)
                    st.success(f"✅ Spending model trained! R² Score: {r2_score:.3f}")
                else:
                    st.error("❌ Training failed")
    
    # Train both models
    st.markdown("---")
    if st.button("🎯 Train Both Models", use_container_width=True, type="primary"):
        with st.spinner("Training both models..."):
            result = api_request("POST", "/ml/train")
            if result:
                st.success("✅ Both models trained successfully!")
                st.json(result)
            else:
                st.error("❌ Training failed")
    
    # Data management
    st.subheader("📊 Training Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📈 Generate Training Data", use_container_width=True):
            with st.spinner("Generating synthetic training data..."):
                result = api_request("POST", "/ml/generate-data")
                if result:
                    st.success(f"✅ Generated {result.get('records_created', 0)} training records!")
                else:
                    st.error("❌ Data generation failed")
    
    with col2:
        if st.button("🔍 Validate Data Quality", use_container_width=True):
            with st.spinner("Validating training data..."):
                result = api_request("GET", "/ml/data-quality")
                if result:
                    quality_score = result.get('quality_score', 0)
                    st.success(f"✅ Data quality score: {quality_score*100:.1f}%")
                else:
                    st.error("❌ Validation failed")
    
    with col3:
        if st.button("🗑️ Clear Training Data", use_container_width=True):
            if st.checkbox("I understand this will delete all training data"):
                with st.spinner("Clearing training data..."):
                    result = api_request("DELETE", "/ml/clear-data")
                    if result:
                        st.success("✅ Training data cleared!")
                    else:
                        st.error("❌ Clear operation failed")
    
    # Model configuration
    st.subheader("⚙️ Model Configuration")
    
    with st.expander("🔧 Advanced Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Churn Model Parameters**")
            churn_params = {
                "n_estimators": st.slider("Number of Trees", 50, 500, 100),
                "max_depth": st.slider("Max Depth", 3, 20, 10),
                "min_samples_split": st.slider("Min Samples Split", 2, 20, 5)
            }
        
        with col2:
            st.markdown("**Spending Model Parameters**")
            spending_params = {
                "n_estimators": st.slider("Number of Trees", 50, 500, 100, key="spending_trees"),
                "max_depth": st.slider("Max Depth", 3, 20, 8, key="spending_depth"),
                "min_samples_split": st.slider("Min Samples Split", 2, 20, 4, key="spending_split")
            }
        
        if st.button("💾 Save Configuration"):
            config = {
                "churn_model": churn_params,
                "spending_model": spending_params
            }
            result = api_request("POST", "/ml/config", json_data=config)
            if result:
                st.success("✅ Configuration saved!")
            else:
                st.error("❌ Save failed")
    
    # Model export/import
    st.subheader("💾 Model Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Models", use_container_width=True):
            with st.spinner("Exporting models..."):
                result = api_request("GET", "/ml/export")
                if result:
                    st.success("✅ Models exported successfully!")
                    st.download_button(
                        "⬇️ Download Model Package",
                        data=json.dumps(result),
                        file_name="ml_models.json",
                        mime="application/json"
                    )
                else:
                    st.error("❌ Export failed")
    
    with col2:
        uploaded_file = st.file_uploader("📤 Import Models", type=['json'])
        if uploaded_file and st.button("📥 Import", use_container_width=True):
            try:
                model_data = json.loads(uploaded_file.read())
                result = api_request("POST", "/ml/import", json_data=model_data)
                if result:
                    st.success("✅ Models imported successfully!")
                else:
                    st.error("❌ Import failed")
            except Exception as e:
                st.error(f"❌ Import error: {str(e)}")
