
from queueflow.db.models import Base
from queueflow.db.sessions import engine

# create_all creates the table that does not exists 
Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")
