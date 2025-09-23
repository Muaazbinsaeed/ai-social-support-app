# Frontend Fix Guide - AI Social Support App

## 🎯 Overview

This guide provides comprehensive instructions for fixing frontend issues, managing deprecation warnings, and maintaining optimal frontend performance for the AI Social Support App.

**Latest Updates (v4.8.0)**: All 42 Streamlit deprecation warnings have been fixed, and the frontend is now fully compatible with Streamlit 1.38.0+.

## 🔧 Recently Fixed Issues (v4.8.0)

### ✅ Fixed: Streamlit `use_container_width` Deprecation Warnings

**Issue**: Streamlit displayed deprecation warnings:
```
Please replace `use_container_width` with `width`.
`use_container_width` will be removed after 2025-12-31.
For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
```

**Solution**: Successfully replaced all 42 occurrences across 8 frontend component files:

#### Files Updated:
- ✅ `frontend/components/processing_status.py` (1 occurrence)
- ✅ `frontend/components/application_panel.py` (11 occurrences)
- ✅ `frontend/components/document_panel.py` (2 occurrences)
- ✅ `frontend/components/status_panel.py` (3 occurrences)
- ✅ `frontend/components/auth_component.py` (4 occurrences)
- ✅ `frontend/components/document_management.py` (12 occurrences)
- ✅ `frontend/components/results_panel.py` (4 occurrences)
- ✅ `frontend/components/navigation.py` (5 occurrences)

#### Change Applied:
```python
# Before (deprecated):
st.button("🔄 Refresh", use_container_width=True)

# After (fixed):
st.button("🔄 Refresh", width='stretch')
```

**Result**: Zero deprecation warnings, full Streamlit 1.38.0+ compatibility.

## 🚀 Frontend Flow Management

### Service Architecture
```
┌─────────────────────────────────────┐
│     Streamlit Frontend (8005)       │
│   Real-Time Three-Panel Interface  │
└──────────────┬──────────────────────┘
               │ HTTP API Calls
┌──────────────▼──────────────────────┐
│     FastAPI Backend (8000)          │
│   58+ API Endpoints                 │
└─────────────────────────────────────┘
```

### Port Standardization (v4.7.0+)
- **Frontend**: http://localhost:8005 (Streamlit)
- **Backend**: http://localhost:8000 (FastAPI)
- **API Documentation**: http://localhost:8000/docs

## 🛠️ Common Frontend Issues & Solutions

### 1. Multiple Service Conflicts

**Symptoms**:
- Port already in use errors
- Duplicate services running
- Inconsistent behavior

**Diagnosis**:
```bash
# Check running processes
ps aux | grep -E "(uvicorn|streamlit|celery)"

# Check PID files
ls -la .*.pid
```

**Solution**:
```bash
# Clean shutdown
./scripts/stop_all_services.sh

# Clean restart
./scripts/start_all_services_local.sh
```

### 2. Frontend Not Loading / Connection Refused

**Symptoms**:
- Browser shows "This site can't be reached"
- Connection refused errors
- Frontend not starting

**Diagnosis**:
```bash
# Check if Streamlit is running
curl http://localhost:8005

# Check backend connectivity
curl http://localhost:8000/health
```

**Solution**:
```bash
# Restart frontend only
pkill -f "streamlit"
source venv/bin/activate
streamlit run frontend/dashboard_app.py --server.port=8005 --server.address=0.0.0.0
```

### 3. API Connection Issues

**Symptoms**:
- Frontend loads but API calls fail
- 404 or connection errors in browser console
- No data displaying

**Diagnosis**:
```bash
# Verify backend is running on correct port
curl http://localhost:8000/health

# Check API client configuration
grep -n "API_BASE_URL" frontend/utils/api_client.py
```

**Solution**:
```bash
# Ensure backend is on port 8000
./scripts/stop_all_services.sh
./scripts/start_all_services_local.sh

# Verify in api_client.py:
# API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

### 4. Session/Authentication Issues

**Symptoms**:
- Login not persisting
- Session expired errors
- Authentication redirects

**Diagnosis**:
```bash
# Check browser cookies/local storage
# Inspect browser developer tools > Application > Storage

# Verify JWT secret configuration
grep -n "JWT_SECRET_KEY" .env
```

**Solution**:
```bash
# Clear browser data and restart
# Or programmatically clear cookies:
# st.session_state.clear()
```

## 📝 Development Workflow

### 1. Clean Development Start
```bash
# Recommended development workflow
./scripts/stop_all_services.sh
./scripts/start_all_services_local.sh

# Verify services
curl http://localhost:8000/health
curl http://localhost:8005
```

### 2. Frontend Development with Hot Reload
```bash
# Frontend runs with hot reload by default
# Any changes to frontend/ files will auto-refresh
# No restart needed for most code changes

# For environment changes, restart:
pkill -f "streamlit"
source venv/bin/activate
streamlit run frontend/dashboard_app.py --server.port=8005 --server.address=0.0.0.0
```

### 3. Testing Frontend Changes
```bash
# Quick frontend test
curl http://localhost:8005

# Full workflow test
python tests/demo_workflow_test.py

# API integration test
python tests/quick_api_test.py
```

## 🔍 Debugging Frontend Issues

### Log Locations
```bash
# Streamlit logs
tail -f logs/streamlit.log

# Browser console (F12 > Console)
# Look for JavaScript errors, API call failures

# Network tab (F12 > Network)
# Check API request/response details
```

### Common Error Patterns

#### 1. Module Import Errors
```bash
# Check Python environment
source venv/bin/activate
python -c "import streamlit; print('OK')"

# Reinstall dependencies if needed
pip install -r requirements.txt
```

#### 2. API Endpoint 404 Errors
```bash
# Verify backend is running
curl http://localhost:8000/docs

# Check specific endpoint
curl http://localhost:8000/health
```

#### 3. Authentication/CORS Issues
```bash
# Check CORS configuration in backend
grep -n "CORS" app/main.py

# Verify JWT configuration
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"password123"}'
```

## 🚀 Performance Optimization

### 1. Caching Strategies
```python
# Use appropriate Streamlit caching
@st.cache_data
def load_data():
    return api_client.get_data()

@st.cache_resource
def init_connection():
    return create_connection()
```

### 2. Component Optimization
```python
# Avoid unnecessary reruns
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    # Initialization code here
```

### 3. API Call Efficiency
```python
# Batch API calls where possible
# Use session state to cache responses
# Implement proper error handling with fallbacks
```

## 📊 Monitoring & Validation

### Health Check Commands
```bash
# Full system health check
curl http://localhost:8000/health

# Frontend accessibility
curl -I http://localhost:8005

# Service status
ps aux | grep -E "(uvicorn|streamlit|celery)" | wc -l
# Should return 3 (one each for uvicorn, streamlit, celery)
```

### Performance Metrics
- **Frontend Load Time**: < 3 seconds
- **API Response Time**: < 500ms
- **Page Navigation**: < 1 second
- **Document Upload**: < 10 seconds

## 🔄 Maintenance Schedule

### Daily
- Check service health: `curl http://localhost:8000/health`
- Monitor error logs: `tail logs/streamlit.log`

### Weekly
- Update dependencies: `pip install -r requirements.txt --upgrade`
- Clear browser cache and test full workflow
- Review and clean up session data

### Monthly
- Review and update Streamlit version
- Audit frontend performance metrics
- Update this guide with new issues/solutions

## 📞 Emergency Troubleshooting

### When Everything Fails
```bash
# Nuclear option - complete reset
./scripts/stop_all_services.sh
docker-compose down
pkill -f "uvicorn"
pkill -f "streamlit"
pkill -f "celery"

# Clean restart
docker-compose up -d postgres redis qdrant ollama
./scripts/start_all_services_local.sh

# Verify everything works
python tests/demo_workflow_test.py
```

### Contact Information
- **Developer**: [Muaaz Bin Saeed](https://github.com/Muaazbinsaeed/)
- **Repository**: [AI Social Support App](https://github.com/Muaazbinsaeed/ai-social-support-app)
- **Issues**: Report at GitHub Issues

---

**Last Updated**: September 22, 2025 (v4.8.0)
**Status**: All deprecation warnings fixed, frontend fully operational