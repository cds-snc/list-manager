import os
import pytest

from alembic.config import Config
from alembic import command


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.List import List
from models.Subscription import Subscription


@pytest.fixture
def assert_new_model_saved():
    def f(model):
        assert model.id is not None
        assert model.created_at is not None
        assert model.updated_at is None

    return f


@pytest.fixture(scope="session")
def list_fixture(session):
    list = List(
        name="fixture_name",
        language="fixture_language",
        service_id="fixture_service_id",
        subscribe_email_template_id="fixture_subscribe_email_template_id",
        unsubscribe_email_template_id="fixture_unsubscribe_email_template_id",
        subscribe_phone_template_id="fixture_subscribe_phone_template_id",
        unsubscribe_phone_template_id="fixture_unsubscribe_phone_template_id",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="session")
def session():
    db_engine = create_engine(os.environ.get("SQLALCHEMY_DATABASE_TEST_URI"))
    Session = sessionmaker(bind=db_engine)
    return Session()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    os.environ["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "SQLALCHEMY_DATABASE_TEST_URI"
    )
    alembic_cfg = Config("./db_migrations/alembic.ini")
    alembic_cfg.set_main_option("script_location", "./db_migrations")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    yield


@pytest.fixture(scope="session")
def subscription_fixture(session, list_fixture):
    subscription = Subscription(
        email="fixture_email", phone="fixture_phone", list=list_fixture
    )
    session.add(subscription)
    session.commit()
    return subscription
