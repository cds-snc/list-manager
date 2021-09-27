import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if os.environ.get("CI"):
    connection_string = os.environ.get("SQLALCHEMY_DATABASE_TEST_URI")
else:
    connection_string = os.environ.get("SQLALCHEMY_DATABASE_URI")
# Timeout is set to 10 seconds
db_engine = create_engine(
    connection_string,
    pool_size=1,
    max_overflow=0,
    pool_pre_ping=True,  # Check that a connection is still active before attempting to use
    pool_recycle=1500,  # Prune connections older than 25 minutes (RDS Proxy has a timeout of 30 minutes)
    pool_use_lifo=True,  # Always re-use last connection used (allows server-side timeouts to remove unused connections)
)
db_session = sessionmaker(bind=db_engine)
