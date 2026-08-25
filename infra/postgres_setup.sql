-- One-time local setup: creates a dedicated role + database for this project
-- so we're not running everything as the postgres superuser.
--
-- Run this once the postgresql-x64-14 service is started, as the postgres
-- superuser, e.g.:
--   & "C:\Program Files\PostgreSQL\14\bin\psql.exe" -U postgres -f infra\postgres_setup.sql
-- (it will prompt for the postgres superuser password you set at install time)

CREATE ROLE tmdb_app WITH LOGIN PASSWORD 'tmdb_local_dev_pw';
CREATE DATABASE tmdb_local OWNER tmdb_app;
