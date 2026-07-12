from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Cargamos las variables de entorno (.env)
load_dotenv()

# Recuperamos la URL de la base de datos
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/agrops"
)

# 1. Creamos el motor de conexión
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True, # Verifica si la conexión sigue viva antes de usarla
    pool_size=10,       # Número máximo de conexiones simultáneas en el pool
    max_overflow=20     # Conexiones adicionales permitidas en picos de tráfico
)

# 2. Creamos la fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. La función/dependencia para tus rutas
def get_db():
    """
    Generador de sesiones de base de datos.
    Abre una sesión para cada petición y la cierra al finalizar.
    """
    db = SessionLocal()
    try:
        yield db  # Cede la sesión a la ruta de FastAPI que la solicitó
    finally:
        db.close()  # Se ejecuta SIEMPRE al terminar la petición (garantiza el cierre)