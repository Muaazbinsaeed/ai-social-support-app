# AI Social Security System - Deployment & Testing Guide

## 🔧 System Requirements & Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Tesseract OCR
- Poppler (for PDF processing)

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install postgresql redis tesseract poppler

# Install system dependencies (Ubuntu)
sudo apt-get update
sudo apt-get install postgresql redis-server tesseract-ocr poppler-utils

# Install system dependencies (Windows)
# Download and install PostgreSQL, Redis, Tesseract from official websites
```

### 2. Database Setup

```bash
# Start PostgreSQL
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Ubuntu

# Create database
createdb ai_social_db

# Create user (optional)
psql -d ai_social_db -c "CREATE USER ai_social_user WITH PASSWORD 'secure_password';"
psql -d ai_social_db -c "GRANT ALL PRIVILEGES ON DATABASE ai_social_db TO ai_social_user;"
```

### 3. Redis Setup

```bash
# Start Redis
brew services start redis  # macOS
sudo systemctl start redis-server  # Ubuntu
redis-server  # Manual start
```

### 4. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configurations
DATABASE_URL=postgresql://username:password@localhost/ai_social_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key-here
OLLAMA_URL=http://localhost:11434
```

### 5. Database Migration

```bash
# Run database migrations
source venv/bin/activate
python -m alembic upgrade head
```

### 6. Start Services

```bash
# Terminal 1: Start FastAPI server
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Celery worker
source venv/bin/activate
python -m celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Start Streamlit dashboard
source venv/bin/activate
python -m streamlit run frontend/dashboard_app.py --server.port 8005 --server.address 0.0.0.0

# Terminal 4: Start Redis (if not running as service)
redis-server
```

## 🐳 Docker Deployment (Optional)

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: ai_social_db
      POSTGRES_USER: ai_social_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://ai_social_user:secure_password@postgres/ai_social_db
      REDIS_URL: redis://redis:6379/0
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  worker:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://ai_social_user:secure_password@postgres/ai_social_db
      REDIS_URL: redis://redis:6379/0
    command: celery -A app.workers.celery_app worker --loglevel=info

  dashboard:
    build: .
    ports:
      - "8005:8005"
    depends_on:
      - api
    command: streamlit run frontend/dashboard_app.py --server.port 8005 --server.address 0.0.0.0

volumes:
  postgres_data:
```

```bash
# Start with Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🌐 Service URLs

- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Streamlit Dashboard**: http://localhost:8005
- **Database**: localhost:5432
- **Redis**: localhost:6379

## 🔍 Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check database connection
curl http://localhost:8000/health/db

# Check Redis connection
curl http://localhost:8000/health/redis

# Check Celery workers
curl http://localhost:8000/health/workers
```

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   lsof -ti:8000 | xargs kill -9  # Kill process on port 8000
   ```

2. **Database connection error**
   ```bash
   # Check if PostgreSQL is running
   brew services list | grep postgresql

   # Restart PostgreSQL
   brew services restart postgresql
   ```

3. **Redis connection error**
   ```bash
   # Check if Redis is running
   redis-cli ping

   # Start Redis
   brew services start redis
   ```

4. **Celery worker not starting**
   ```bash
   # Check Redis connection
   python -c "import redis; r=redis.Redis(); print(r.ping())"

   # Clear Celery tasks
   python -m celery -A app.workers.celery_app purge
   ```

5. **OCR/PDF processing errors**
   ```bash
   # Install missing dependencies
   brew install tesseract poppler  # macOS
   sudo apt-get install tesseract-ocr poppler-utils  # Ubuntu
   ```

## 📝 Logs & Monitoring

```bash
# View application logs
tail -f logs/app.log

# View Celery logs
tail -f logs/celery.log

# View PostgreSQL logs
tail -f /usr/local/var/log/postgres.log  # macOS
```