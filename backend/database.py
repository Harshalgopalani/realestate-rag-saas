# database.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

# 1. The Database URL
# For local development, we use SQLite. It will create a file called 'leads.db'
# In production, we will simply change this to: "postgresql://user:password@host/dbname"
SQLALCHEMY_DATABASE_URL = "sqlite:///./leads.db"

# 2. Create the Database Engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 3. Define the SQL Table Structure
class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True) # <-- THE NEW LOCK
    name = Column(String, index=True)
    phone = Column(String, index=True)
    email = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# 4. Generate the Tables
# This automatically creates the file and the tables if they don't exist
Base.metadata.create_all(bind=engine)