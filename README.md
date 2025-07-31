# 🛒 Full-Stack E-Commerce Platform

A modern e-commerce platform with AI-powered shopping assistant, built with FastAPI, Streamlit, MySQL, and ChatGPT integration.

## ✨ Features

- 🛍️ **Complete Shopping Experience** - Product catalog, cart, favorites, order management
- 🤖 **AI Shopping Assistant** - ChatGPT-powered recommendations and analytics
- 📊 **ML Analytics Dashboard** - Customer insights and churn prediction
- 🔐 **Secure Authentication** - JWT-based auth with role management
- 📱 **Responsive Design** - Mobile-friendly Streamlit interface
- 🗄️ **Robust Backend** - FastAPI with MySQL and Redis caching

## � Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key (optional, for AI features)

### Installation

1. **Clone and navigate to project**:
   ```bash
   git clone <your-repo-url>
   cd final_ecom
   ```

2. **Set up environment** (create `.env` file):
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your values:
   # Database
   MYSQL_ROOT_PASSWORD=your_secure_password
   MYSQL_DATABASE=shopping_website
   MYSQL_USER=app_user
   MYSQL_PASSWORD=your_db_password
   
   # Optional: AI Features
   OPENAI_API_KEY=your_openai_key
   
   # Security
   JWT_SECRET_KEY=your_jwt_secret
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_admin_password
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - **🌐 Frontend**: http://localhost:8501
   - **⚡ Backend API**: http://localhost:8000
   - **📚 API Docs**: http://localhost:8000/docs

## 👥 Test Accounts

The application comes with pre-loaded test data:

### Admin Access
- **Username**: `admin` | **Password**: `admin`
- Access to ML analytics dashboard and user management

### Customer Accounts
- **Username**: `alice` | **Password**: `alice` (High-value customer)
- **Username**: `demo` | **Password**: `demo` (Demo account)
- **Username**: `sarah` | **Password**: `sarah` (High churn risk - for ML testing)

## 🤖 AI Features

### ChatGPT Shopping Assistant
- Personalized product recommendations
- Order history analysis
- Smart shopping suggestions
- Natural language product search

### ML Analytics (Admin Only)
- Customer churn prediction
- Purchase pattern analysis
- Revenue insights
- Risk assessment dashboard

## 🏗️ Architecture

```
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── models/   # Database models
│   │   ├── ml/       # Machine learning models
│   │   └── services/ # Business logic
│   └── database/     # SQL initialization
├── frontend/         # Streamlit customer app
├── ui/              # Streamlit admin interface
└── docker-compose.yml
```

## 🗄️ Database Schema

- **Users** - Authentication and role management
- **Customers** - Profile and shipping information  
- **Products** - Catalog with inventory tracking
- **Orders** - Purchase history and order items
- **Cart** - Persistent shopping cart
- **Favorites** - Saved products

## 🔧 Development

### Local Development (without Docker)

1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend**:
   ```bash
   cd frontend
   pip install -r requirements.txt
   streamlit run streamlit_app.py --server.port 8501
   ```

### API Documentation
Interactive API docs available at: http://localhost:8000/docs

## � Security

- Environment variable configuration (no hardcoded secrets)
- JWT token authentication
- Bcrypt password hashing
- SQL injection protection via SQLAlchemy ORM
- Input validation with Pydantic models

## 🚀 Deployment Notes

- All sensitive data configured via environment variables
- Docker containers for easy deployment
- Health checks for database connectivity
- Redis caching for improved performance

### Production Deployment Checklist
- [ ] Set strong passwords in `.env` (use `pre-commit-check.sh` to verify)
- [ ] Change default admin credentials
- [ ] Set `DEBUG=False` in production
- [ ] Use strong JWT secret key (minimum 32 characters)
- [ ] Configure proper firewall rules
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategy for database

## 📞 Troubleshooting

**Application not starting?**
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs

# Restart services
docker-compose restart
```

**Database connection issues?**
- Verify environment variables in `.env`
- Ensure MySQL service is healthy: `docker-compose logs db`

## 📄 License

This project is for educational and demonstration purposes.
