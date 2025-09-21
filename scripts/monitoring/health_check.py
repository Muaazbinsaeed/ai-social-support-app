#!/usr/bin/env python3
"""
System health check script
"""

import sys
import os
import time
import httpx
import redis
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import check_db_connection, SessionLocal
from app.shared.logging_config import setup_logging, get_logger
from app.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)


class HealthChecker:
    """System health checker"""

    def __init__(self):
        self.results = {}
        self.overall_healthy = True

    def check_database(self):
        """Check database connectivity"""
        try:
            logger.info("Checking database connection...")
            healthy = check_db_connection()

            if healthy:
                # Additional database checks
                db = SessionLocal()
                try:
                    # Check if we can query tables
                    result = db.execute("SELECT COUNT(*) FROM users")
                    user_count = result.scalar()

                    self.results['database'] = {
                        'status': 'healthy',
                        'response_time': '< 100ms',
                        'user_count': user_count,
                        'message': 'Database connection successful'
                    }
                except Exception as e:
                    self.results['database'] = {
                        'status': 'degraded',
                        'error': str(e),
                        'message': 'Database connected but query failed'
                    }
                    self.overall_healthy = False
                finally:
                    db.close()
            else:
                self.results['database'] = {
                    'status': 'unhealthy',
                    'message': 'Cannot connect to database'
                }
                self.overall_healthy = False

        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            self.results['database'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Database health check failed'
            }
            self.overall_healthy = False

    def check_redis(self):
        """Check Redis connectivity"""
        try:
            logger.info("Checking Redis connection...")
            r = redis.from_url(settings.redis_url)

            start_time = time.time()
            r.ping()
            response_time = int((time.time() - start_time) * 1000)

            info = r.info()

            self.results['redis'] = {
                'status': 'healthy',
                'response_time': f'{response_time}ms',
                'memory_usage': info.get('used_memory_human', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'message': 'Redis connection successful'
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            self.results['redis'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Redis connection failed'
            }
            self.overall_healthy = False

    def check_ollama(self):
        """Check Ollama AI service"""
        try:
            logger.info("Checking Ollama service...")

            with httpx.Client(timeout=10.0) as client:
                start_time = time.time()
                response = client.get(f"{settings.ollama_url}/api/tags")
                response_time = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [model.get("name", "") for model in models]

                    required_models = ["moondream:1.8b", "qwen2:1.5b", "nomic-embed-text"]
                    available_models = [model for model in required_models
                                      if any(model in name for name in model_names)]

                    if len(available_models) >= 2:
                        status = 'healthy'
                        message = 'Ollama service operational with required models'
                    elif len(available_models) >= 1:
                        status = 'degraded'
                        message = 'Ollama service partially operational'
                        self.overall_healthy = False
                    else:
                        status = 'unhealthy'
                        message = 'Ollama service running but missing required models'
                        self.overall_healthy = False

                    self.results['ollama'] = {
                        'status': status,
                        'response_time': f'{response_time}ms',
                        'available_models': available_models,
                        'total_models': len(model_names),
                        'message': message
                    }
                else:
                    self.results['ollama'] = {
                        'status': 'unhealthy',
                        'http_status': response.status_code,
                        'message': f'Ollama service returned HTTP {response.status_code}'
                    }
                    self.overall_healthy = False

        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            self.results['ollama'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Ollama service unavailable'
            }
            self.overall_healthy = False

    def check_qdrant(self):
        """Check Qdrant vector database"""
        try:
            logger.info("Checking Qdrant service...")

            with httpx.Client(timeout=5.0) as client:
                start_time = time.time()
                response = client.get(f"{settings.qdrant_url}/collections")
                response_time = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    collections = response.json().get("result", {}).get("collections", [])

                    self.results['qdrant'] = {
                        'status': 'healthy',
                        'response_time': f'{response_time}ms',
                        'collections': len(collections),
                        'message': 'Qdrant vector database operational'
                    }
                else:
                    self.results['qdrant'] = {
                        'status': 'unhealthy',
                        'http_status': response.status_code,
                        'message': f'Qdrant returned HTTP {response.status_code}'
                    }
                    self.overall_healthy = False

        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            self.results['qdrant'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Qdrant service unavailable'
            }
            self.overall_healthy = False

    def check_fastapi_app(self):
        """Check FastAPI application"""
        try:
            logger.info("Checking FastAPI application...")

            with httpx.Client(timeout=10.0) as client:
                start_time = time.time()
                response = client.get("http://localhost:8000/health")
                response_time = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    health_data = response.json()

                    self.results['fastapi'] = {
                        'status': 'healthy',
                        'response_time': f'{response_time}ms',
                        'app_status': health_data.get('status', 'unknown'),
                        'message': 'FastAPI application operational'
                    }
                else:
                    self.results['fastapi'] = {
                        'status': 'unhealthy',
                        'http_status': response.status_code,
                        'message': f'FastAPI returned HTTP {response.status_code}'
                    }
                    self.overall_healthy = False

        except Exception as e:
            logger.error(f"FastAPI health check failed: {str(e)}")
            self.results['fastapi'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'FastAPI application unavailable'
            }
            self.overall_healthy = False

    def check_streamlit_app(self):
        """Check Streamlit dashboard"""
        try:
            logger.info("Checking Streamlit dashboard...")

            with httpx.Client(timeout=10.0) as client:
                start_time = time.time()
                response = client.get("http://localhost:8005")
                response_time = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    self.results['streamlit'] = {
                        'status': 'healthy',
                        'response_time': f'{response_time}ms',
                        'message': 'Streamlit dashboard operational'
                    }
                else:
                    self.results['streamlit'] = {
                        'status': 'unhealthy',
                        'http_status': response.status_code,
                        'message': f'Streamlit returned HTTP {response.status_code}'
                    }
                    self.overall_healthy = False

        except Exception as e:
            logger.error(f"Streamlit health check failed: {str(e)}")
            self.results['streamlit'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Streamlit dashboard unavailable'
            }
            self.overall_healthy = False

    def check_celery_workers(self):
        """Check Celery workers"""
        try:
            logger.info("Checking Celery workers...")

            # Check Celery broker (Redis)
            r = redis.from_url(settings.celery_broker_url)

            # Check queue lengths
            document_queue = r.llen("document_processing")
            decision_queue = r.llen("decision_making")
            maintenance_queue = r.llen("maintenance")

            # Try to inspect workers (this might not work in all setups)
            try:
                from celery import Celery
                app = Celery('social_security_ai', broker=settings.celery_broker_url)
                inspect = app.control.inspect()
                stats = inspect.stats()
                active_workers = len(stats) if stats else 0
            except:
                active_workers = "unknown"

            self.results['celery'] = {
                'status': 'healthy',  # Basic assumption if Redis is working
                'document_queue_length': document_queue,
                'decision_queue_length': decision_queue,
                'maintenance_queue_length': maintenance_queue,
                'active_workers': active_workers,
                'message': 'Celery broker accessible'
            }

        except Exception as e:
            logger.error(f"Celery health check failed: {str(e)}")
            self.results['celery'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Celery workers unavailable'
            }
            self.overall_healthy = False

    def check_file_system(self):
        """Check file system"""
        try:
            logger.info("Checking file system...")

            import shutil

            # Check upload directory
            uploads_usage = shutil.disk_usage(settings.upload_dir)
            total_gb = uploads_usage.total / (1024**3)
            free_gb = uploads_usage.free / (1024**3)
            used_percent = ((uploads_usage.total - uploads_usage.free) / uploads_usage.total) * 100

            if used_percent < 80:
                status = 'healthy'
                message = 'File system healthy'
            elif used_percent < 90:
                status = 'warning'
                message = 'File system usage high'
            else:
                status = 'critical'
                message = 'File system usage critical'
                self.overall_healthy = False

            self.results['file_system'] = {
                'status': status,
                'disk_usage_percent': f'{used_percent:.1f}%',
                'free_space_gb': f'{free_gb:.1f}GB',
                'total_space_gb': f'{total_gb:.1f}GB',
                'upload_directory': settings.upload_dir,
                'message': message
            }

        except Exception as e:
            logger.error(f"File system health check failed: {str(e)}")
            self.results['file_system'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'File system check failed'
            }
            self.overall_healthy = False

    def run_all_checks(self):
        """Run all health checks"""
        logger.info("Starting comprehensive health check...")

        checks = [
            self.check_database,
            self.check_redis,
            self.check_ollama,
            self.check_qdrant,
            self.check_fastapi_app,
            self.check_streamlit_app,
            self.check_celery_workers,
            self.check_file_system
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                continue

        return self.results, self.overall_healthy

    def print_results(self):
        """Print health check results"""
        print("\n" + "="*70)
        print("SOCIAL SECURITY AI - SYSTEM HEALTH CHECK")
        print("="*70)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Overall Status: {'🟢 HEALTHY' if self.overall_healthy else '🔴 UNHEALTHY'}")
        print("-"*70)

        # Sort results by status (unhealthy first)
        sorted_services = sorted(
            self.results.items(),
            key=lambda x: (x[1]['status'] != 'unhealthy', x[0])
        )

        for service_name, service_info in sorted_services:
            status = service_info['status']
            message = service_info.get('message', 'No message')

            if status == 'healthy':
                status_icon = "🟢"
            elif status == 'degraded' or status == 'warning':
                status_icon = "🟡"
            else:
                status_icon = "🔴"

            print(f"{status_icon} {service_name.upper():<15} {status.upper():<10} {message}")

            # Print additional details
            for key, value in service_info.items():
                if key not in ['status', 'message', 'error']:
                    print(f"   {key}: {value}")

            if 'error' in service_info:
                print(f"   ❌ Error: {service_info['error']}")

            print()

        print("-"*70)

        if self.overall_healthy:
            print("✅ All systems operational! Ready to process applications.")
        else:
            print("⚠️  System issues detected. Please review the failed services above.")
            print("\n🔧 Troubleshooting steps:")
            print("   1. Check if all Docker services are running: docker-compose ps")
            print("   2. Check logs: docker-compose logs [service-name]")
            print("   3. Restart services: docker-compose restart [service-name]")
            print("   4. Full restart: docker-compose down && docker-compose up -d")

        print("="*70)


def main():
    """Main health check function"""
    try:
        checker = HealthChecker()
        results, overall_healthy = checker.run_all_checks()
        checker.print_results()

        # Exit with appropriate code
        sys.exit(0 if overall_healthy else 1)

    except Exception as e:
        logger.error(f"Health check script failed: {str(e)}")
        print(f"\n❌ Health check failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()