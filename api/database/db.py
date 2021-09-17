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
    pool_recycle=3600,
    pool_pre_ping=True,
    pool_use_lifo=True,
)
db_session = sessionmaker(bind=db_engine)
