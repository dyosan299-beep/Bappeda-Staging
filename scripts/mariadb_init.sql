-- Inisialisasi idempotent database & user pengembangan (dijalankan tiap MariaDB start)
CREATE DATABASE IF NOT EXISTS sidata CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS 'sidata'@'127.0.0.1' IDENTIFIED BY 'sidata_dev_pw';
CREATE USER IF NOT EXISTS 'sidata'@'localhost' IDENTIFIED BY 'sidata_dev_pw';
GRANT ALL PRIVILEGES ON sidata.* TO 'sidata'@'127.0.0.1';
GRANT ALL PRIVILEGES ON sidata.* TO 'sidata'@'localhost';
