
from queueflow.db.models import Base
from queueflow.db.sessions import engine

Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")
