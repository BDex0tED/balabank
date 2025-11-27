To run project:
Replace database connection in files:
  database:
  ```
  DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://user:password@localhost:5433/family_db"
)
```
  docker-compose.yml:
  ```
      DATABASE_URL: postgresql+asyncpg://user:password@db:5432/family_db
      environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: family_db
```
  
Then just simply paste in the directory with project in terminal:
```
sudo docker compose up --build
```
