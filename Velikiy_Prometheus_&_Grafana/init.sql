DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100),
    age INTEGER,
    town VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (name, surname, age, town) VALUES
('Alice', 'Smith', 25, 'Moscow'),
('Bob', 'Johnson', 30, 'Saint Petersburg'),
('Charlie', 'Brown', 35, 'Kazan');