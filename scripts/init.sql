-- PostgreSQL initialization script for Social Security AI System
-- This script creates the basic database structure

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database if it doesn't exist (redundant since it's set in docker-compose)
-- Database is already created via POSTGRES_DB environment variable

-- Grant privileges to admin user
GRANT ALL PRIVILEGES ON DATABASE social_security_ai TO admin;

-- Basic initialization complete
-- Tables will be created by SQLAlchemy models via the application