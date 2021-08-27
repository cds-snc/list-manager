import os

from sqlalchemy import create_engine, engine

if os.environ.get("CI"):
    connection_string = os.environ.get("SQLALCHEMY_DATABASE_TEST_URI")
else:
    connection_string = os.environ.get("SQLALCHEMY_DATABASE_URI")
# Timeout is set to 10 seconds


def get_engine() -> engine.Engine:
    return create_engine(
        connection_string,
        connect_args={"connect_timeout": 10},
        pool_pre_ping=True,
    )
