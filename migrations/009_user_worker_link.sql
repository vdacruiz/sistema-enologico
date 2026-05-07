-- Vincular usuarios con operarios
ALTER TABLE app_users ADD COLUMN worker_id INT REFERENCES workers(id);
CREATE INDEX idx_app_users_worker ON app_users(worker_id);
