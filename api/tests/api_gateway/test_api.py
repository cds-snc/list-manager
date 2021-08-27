import os

from fastapi.testclient import TestClient
from unittest.mock import ANY, MagicMock, patch

from api_gateway import api
from sqlalchemy.exc import SQLAlchemyError
import uuid

from models.List import List


client = TestClient(api.app)


def test_version_with_no_GIT_SHA():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "unknown"}


@patch.dict(os.environ, {"GIT_SHA": "foo"}, clear=True)
def test_version_with_GIT_SHA():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "foo"}


@patch("api_gateway.api.get_db_version")
def test_healthcheck_success(mock_get_db_version):
    mock_get_db_version.return_value = "foo"
    response = client.get("/healthcheck")
    assert response.status_code == 200
    expected_val = {"database": {"able_to_connect": True, "db_version": "foo"}}
    assert response.json() == expected_val


@patch("api_gateway.api.get_db_version")
@patch("api_gateway.api.log")
def test_healthcheck_failure(mock_log, mock_get_db_version):
    mock_get_db_version.side_effect = SQLAlchemyError()
    response = client.get("/healthcheck")
    assert response.status_code == 200
    expected_val = {"database": {"able_to_connect": False}}
    assert response.json() == expected_val
    # assert mock_log.error.assert_called_once_with(SQLAlchemyError())


def test_create_subscription_event_with_bad_list_id():
    response = client.post("/subscription", json={"list_id": ""})
    assert response.json() == {"error": "list id is not valid"}
    assert response.status_code == 400


def test_create_subscription_event_with_id_not_found():
    response = client.post("/subscription", json={"list_id": str(uuid.uuid4())})
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_create_subscription_event_empty_phone_and_email(list_fixture):
    response = client.post("/subscription", json={"list_id": str(list_fixture.id)})
    assert response.json() == {"error": "email and phone can not be empty"}
    assert response.status_code == 400


def test_create_succeeds_with_email(list_fixture):
    response = client.post(
        "/subscription",
        json={"email": "test@example.com", "list_id": str(list_fixture.id)},
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200


def test_create_succeeds_with_phone(list_fixture):
    response = client.post(
        "/subscription", json={"phone": "123456789", "list_id": str(list_fixture.id)}
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200


def test_create_succeeds_with_email_and_phone(list_fixture):
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "phone": "123456789",
            "list_id": str(list_fixture.id),
        },
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200


@patch("api_gateway.api.db_session")
def test_create_succeeds_with_email_and_phone_unknown_error(
    mock_db_session, list_fixture
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "phone": "123456789",
            "list_id": str(list_fixture.id),
        },
    )
    assert response.json() == {"error": "error saving subscription"}
    assert response.status_code == 500


def test_confirm_with_bad_id():
    response = client.get("/subscription/foo")
    assert response.json() == {"error": "subscription id is not valid"}
    assert response.status_code == 400


def test_confirm_with_id_not_found():
    response = client.get(f"/subscription/{str(uuid.uuid4())}")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


def test_confirm_with_correct_id(session, subscription_fixture):
    response = client.get(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200
    session.refresh(subscription_fixture)
    assert subscription_fixture.confirmed is True


@patch("api_gateway.api.db_session")
def test_confirm_with_correct_id_unknown_error(mock_db_session, subscription_fixture):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.get(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error confirming subscription"}
    assert response.status_code == 500


def test_unsubscribe_event_with_bad_id():
    response = client.delete("/subscription/foo")
    assert response.json() == {"error": "subscription id is not valid"}
    assert response.status_code == 400


def test_unsubscribe_event_with_id_not_found():
    response = client.delete(f"/subscription/{str(uuid.uuid4())}")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


def test_unsubscribe_event_with_correct_id(subscription_fixture):
    response = client.delete(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200


@patch("api_gateway.api.db_session")
def test_unsubscribe_event_with_correct_id_unknown_error(
    mock_db_session, subscription_fixture
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.delete(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error deleting subscription"}
    assert response.status_code == 500


def test_return_all_lists(list_fixture):
    response = client.get("/lists")
    assert response.json() == [
        {
            "id": str(list_fixture.id),
            "language": list_fixture.language,
            "name": list_fixture.name,
            "service": list_fixture.service_id,
        }
    ]
    assert response.status_code == 200


def test_return_lists_by_service(list_fixture):
    response = client.get(f"/lists/{list_fixture.service_id}")
    assert response.json() == [
        {
            "id": str(list_fixture.id),
            "language": list_fixture.language,
            "name": list_fixture.name,
            "service": list_fixture.service_id,
        }
    ]
    assert response.status_code == 200


def test_create_list():
    response = client.post(
        "/list",
        json={
            "name": "new_name",
            "language": "new_language",
            "service_id": "new_service_id",
            "subscribe_email_template_id": "new_subscribe_email_template_id",
            "unsubscribe_email_template_id": "new_unsubscribe_email_template_id",
            "subscribe_phone_template_id": "new_subscribe_phone_template_id",
            "unsubscribe_phone_template_id": "new_unsubscribe_phone_template_id",
        },
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200


def test_create_list_with_error():
    response = client.post(
        "/list",
        json={
            "name": "fixture_name",
            "language": "new_language",
            "service_id": "new_service_id",
            "subscribe_email_template_id": "new_subscribe_email_template_id",
            "unsubscribe_email_template_id": "new_unsubscribe_email_template_id",
            "subscribe_phone_template_id": "new_subscribe_phone_template_id",
            "unsubscribe_phone_template_id": "new_unsubscribe_phone_template_id",
        },
    )
    assert response.json() == {"error": ANY}
    assert response.status_code == 500


def test_delete_list_with_bad_id():
    response = client.delete("/list/foo")
    assert response.json() == {"error": "list id is not valid"}
    assert response.status_code == 400


def test_delete_list_with_id_not_found():
    response = client.delete(f"/list/{str(uuid.uuid4())}")
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_delete_list_with_correct_id(session):
    list = List(
        name="delete_name",
        language="delete_language",
        service_id="delete_service_id",
        subscribe_email_template_id="delete_subscribe_email_template_id",
        unsubscribe_email_template_id="delete_unsubscribe_email_template_id",
        subscribe_phone_template_id="delete_subscribe_phone_template_id",
        unsubscribe_phone_template_id="delete_unsubscribe_phone_template_id",
    )
    session.add(list)
    session.commit()
    response = client.delete(f"/list/{str(list.id)}")
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200


@patch("api_gateway.api.db_session")
def test_delete_list_with_correct_id_unknown_error(mock_db_session, list_fixture):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.delete(f"/list/{str(list_fixture.id)}")
    assert response.json() == {"error": "error deleting list"}
    assert response.status_code == 500
