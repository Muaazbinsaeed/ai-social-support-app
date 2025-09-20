-- Social Security AI Database Initialization Script
-- This script sets up the database with proper extensions and initial configuration

-- Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
-- These will be created automatically by SQLAlchemy, but we can add custom ones here

-- Add any custom database configuration here
-- For example, custom functions, triggers, or additional indexes

-- Set timezone for all timestamp operations
SET timezone = 'UTC';