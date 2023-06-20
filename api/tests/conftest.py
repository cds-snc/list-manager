# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import os
import pytest
from unittest.mock import MagicMock

from alembic.config import Config
from alembic import command

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.List import List
from models.Subscription import Subscription

from fastapi.testclient import TestClient
from typing import Generator, Any
from api_gateway import api


@pytest.fixture
def assert_new_model_saved():
    def f(model):
        assert model.id is not None
        assert model.created_at is not None
        assert model.updated_at is None

    return f


@pytest.fixture
def context_fixture():
    context = MagicMock()
    context.function_name = "api"
    return context


@pytest.fixture(scope="session")
def list_fixture(session):
    list = List(
        name="fixture_name",
        language="fixture_language",
        service_id="fixture_service_id",
        subscribe_email_template_id="97375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="a6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="02427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="dae60d25-0c83-45b7-b2ba-db208281e4e4",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="function")
def list_fixture_required_data_only(session):
    list = List(
        name="fixture_name_required",
        language="fixture_language_required",
        service_id="fixture_service_id_required",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="session")
def list_count_fixture_0(session):
    list = List(
        name="list_count_fixture_0",
        language="en",
        service_id="fixture_service_id_0",
        subscribe_email_template_id="87375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="b6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="42427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="rae60d25-0c83-45b7-b2ba-db208281e4e4",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="session")
def list_count_fixture_1(session):
    list = List(
        name="list_count_fixture_1",
        language="en",
        service_id="fixture_service_id_1",
        subscribe_email_template_id="87375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="b6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="42427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="rae60d25-0c83-45b7-b2ba-db208281e4e4",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="session")
def list_count_fixture_2(session):
    list = List(
        name="list_count_fixture_2",
        language="en",
        service_id="fixture_service_id_1",
        subscribe_email_template_id="87375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="b6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="42427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="rae60d25-0c83-45b7-b2ba-db208281e4e4",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="session")
def list_reset_fixture_0(session):
    list = List(
        name="list_reset_0",
        language="en",
        service_id="fixture_reset_service_id_0",
        subscribe_email_template_id="87375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="b6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="42427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="rae60d25-0c83-45b7-b2ba-db208281e4e4",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="session")
def list_fixture_with_redirects(session):
    list = List(
        name="fixture_name_with_redirects",
        language="fixture_language",
        service_id="fixture_with_redirects_service_id",
        subscribe_email_template_id="97375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="a6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="02427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="dae60d25-0c83-45b7-b2ba-db208281e4e4",
        subscribe_redirect_url="http://localhost_test/subscribe",
        confirm_redirect_url="http://localhost_test/confirm",
        unsubscribe_redirect_url="http://localhost_test/unsubscribe",
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


@pytest.fixture(scope="function")
def subscription_fixture(session, list_fixture):
    subscription = Subscription(
        email="fixture_email", phone="fixture_phone", list=list_fixture
    )
    session.add(subscription)
    session.commit()
    return subscription


@pytest.fixture(scope="function")
def subscription_fixture_with_redirects(session, list_fixture_with_redirects):
    subscription = Subscription(
        email="fixture_email", phone="fixture_phone", list=list_fixture_with_redirects
    )
    session.add(subscription)
    session.commit()
    return subscription


@pytest.fixture(scope="session")
def list_fixture_with_duplicates(session):
    list_fixture = List(
        name="fixture_name_duplicates",
        language="fixture_language",
        service_id="fixture_service_id",
        subscribe_email_template_id="97375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="a6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="02427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="dae60d25-0c83-45b7-b2ba-db208281e4e4",
    )
    session.add(list_fixture)
    subscription = Subscription(
        email="fixture_email", phone="fixture_phone", list=list_fixture, confirmed=True
    )
    session.add(subscription)

    subscription2 = Subscription(
        email="fixture_email", list=list_fixture, confirmed=True
    )
    session.add(subscription2)

    subscription3 = Subscription(
        email="fixture_email_unique", list=list_fixture, confirmed=True
    )
    session.add(subscription3)

    subscription4 = Subscription(
        email="fixture_email_unique",
        phone="fixture_phone_unique",
        list=list_fixture,
        confirmed=True,
    )
    session.add(subscription4)

    subscription5 = Subscription(
        phone="fixture_phone", list=list_fixture, confirmed=True
    )
    session.add(subscription5)

    session.commit()
    return list_fixture


@pytest.fixture(scope="session")
def list_to_be_updated_fixture(session):
    list = List(
        name="list_import",
        language="en",
        service_id="fixture_list_import_service_id_0",
        subscribe_email_template_id="87375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="b6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="42427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="rae60d25-0c83-45b7-b2ba-db208281e4e4",
    )
    session.add(list)
    session.commit()
    return list


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, Any, None]:
    with TestClient(api.app) as client:
        yield client


@pytest.fixture(scope="function")
def api_verify_token():
    return api.verify_token


@pytest.fixture(scope="function")
def metrics():
    from aws_lambda_powertools.metrics import MetricUnit

    metric_list = [
        "ListCreated",
        "ListDeleted",
        "SuccessfulSubscription",
        "UnsubscriptionError",
        "ConfirmationError",
        "UnsubscriptionNotificationError",
        "SuccessfulConfirmation",
        "SuccessfulUnsubscription",
        "BulkNotificationError",
        "SubscriptionNotificationError",
        "ListDeleteError",
        "ListUpdateError",
        "ListUpdated",
        "ListCreateError",
    ]
    for metric in metric_list:
        api.metrics.add_metric(name=metric, unit=MetricUnit.Count, value=0)


@pytest.fixture(scope="function")
def list_with_subscribers(session):
    list1 = List(
        name="sub_list_counter1",
        language="en",
        service_id="fixture_service_id_sub_counter1",
        subscribe_email_template_id="87375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="b6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="42427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="rae60d25-0c83-45b7-b2ba-db208281e4e4",
    )

    list2 = List(
        name="sub_list_counter2",
        language="en",
        service_id="fixture_service_id_sub_counter1",
        subscribe_email_template_id="87375f47-0fb1-4459-ab36-97a5c1ba358f",
        unsubscribe_email_template_id="b6ea8854-3f45-4f5c-808f-61612d920eb3",
        subscribe_phone_template_id="42427c7f-d041-411d-9b92-5890cade3d9a",
        unsubscribe_phone_template_id="rae60d25-0c83-45b7-b2ba-db208281e4e4",
    )

    session.add(list1)
    session.add(list2)
    session.commit()

    user_list = [
        {"email": "list1+0@example.com", "confirmed": True},
        {"email": "list1+1@example.com", "confirmed": True},
        {"email": "list2+0@example.com", "confirmed": True},
        {"email": "list2+1@example.com", "confirmed": False},
    ]

    for user in user_list:
        subscription = Subscription(
            email=user["email"],
            list=list1 if "list1" in user["email"] else list2,
            confirmed=user["confirmed"],
        )
        session.add(subscription)
        session.commit()

    return (list1, list2)
