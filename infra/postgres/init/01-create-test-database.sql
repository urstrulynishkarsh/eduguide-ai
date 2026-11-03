-- Runs once, the first time the database container starts with an empty volume.
-- The automated tests use their own database so they can never touch real data.
CREATE DATABASE eduguide_test OWNER eduguide;
