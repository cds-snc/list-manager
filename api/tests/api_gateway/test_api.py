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


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_with_bad_list_id(mock_client):
    response = client.post("/subscription", json={"list_id": ""})
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_with_id_not_found(mock_client):
    response = client.post("/subscription", json={"list_id": str(uuid.uuid4())})
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_empty_phone_and_email(mock_client, list_fixture):
    response = client.post("/subscription", json={"list_id": str(list_fixture.id)})
    assert response.json() == {"error": "email and phone can not be empty"}
    assert response.status_code == 400


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_with_bad_email(mock_client, list_fixture):
    response = client.post(
        "/subscription",
        json={"email": "example.com", "list_id": str(list_fixture.id)},
    )
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "email"],
                "msg": "value is not a valid email address",
                "type": "value_error.email",
            }
        ]
    }
    assert response.status_code == 422


@patch("api_gateway.api.get_notify_client")
def test_create_succeeds_with_email(mock_client, list_fixture):
    response = client.post(
        "/subscription",
        json={"email": "test@example.com", "list_id": str(list_fixture.id)},
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200
    mock_client().send_email_notification.assert_called_once_with(
        email_address="test@example.com",
        template_id="97375f47-0fb1-4459-ab36-97a5c1ba358f",
        personalisation={
            "email_address": "test@example.com",
            "name": "fixture_name",
            "subscription_id": ANY,
        },
    )


@patch("api_gateway.api.get_notify_client")
def test_create_succeeds_with_phone(mock_client, list_fixture):
    response = client.post(
        "/subscription", json={"phone": "123456789", "list_id": str(list_fixture.id)}
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200
    mock_client().send_sms_notification.assert_called_once_with(
        phone_number="123456789",
        template_id="02427c7f-d041-411d-9b92-5890cade3d9a",
        personalisation={"phone_number": "123456789", "name": "fixture_name"},
    )


@patch("api_gateway.api.get_notify_client")
def test_create_succeeds_with_email_and_phone(mock_client, list_fixture):
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


@patch("api_gateway.api.get_notify_client")
def test_create_succeeds_with_redirect(mock_client, list_fixture_with_redirects):
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "phone": "123456789",
            "list_id": str(list_fixture_with_redirects.id),
        },
    )
    assert response.status_code == 307
    assert response.headers == {
        "location": list_fixture_with_redirects.subscribe_redirect_url
    }


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_with_undeclared_parameter(mock_client, list_fixture):
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "phone": "123456789",
            "list_id": str(list_fixture.id),
            "foo": "bar",
        },
    )
    assert response.json() == {"detail": ANY}
    assert response.status_code == 422


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_create_succeeds_with_email_and_phone_unknown_error(
    mock_client, mock_db_session, list_fixture
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
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


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


def test_confirm_with_correct_id_and_redirects(
    session, subscription_fixture_with_redirects, list_fixture_with_redirects
):
    response = client.get(
        f"/subscription/{str(subscription_fixture_with_redirects.id)}",
        allow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers == {
        "location": list_fixture_with_redirects.confirm_redirect_url
    }
    session.refresh(subscription_fixture_with_redirects)
    assert subscription_fixture_with_redirects.confirmed is True


@patch("api_gateway.api.db_session")
def test_confirm_with_correct_id_unknown_error(mock_db_session, subscription_fixture):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.get(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error confirming subscription"}
    assert response.status_code == 500


@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_bad_id(mock_client):
    response = client.delete("/subscription/foo")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_id_not_found(mock_client):
    response = client.delete(f"/subscription/{str(uuid.uuid4())}")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_correct_id(mock_client, subscription_fixture):
    response = client.delete(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200

    mock_client().send_sms_notification.assert_called_once_with(
        phone_number="fixture_phone",
        template_id="dae60d25-0c83-45b7-b2ba-db208281e4e4",
        personalisation={"phone_number": "fixture_phone", "name": "fixture_name"},
    )
    mock_client().send_email_notification.assert_called_once_with(
        email_address="fixture_email",
        template_id="a6ea8854-3f45-4f5c-808f-61612d920eb3",
        personalisation={"email_address": "fixture_email", "name": "fixture_name"},
    )


@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_correct_id_and_redirect(
    mock_client, subscription_fixture_with_redirects, list_fixture_with_redirects
):
    response = client.delete(
        f"/subscription/{str(subscription_fixture_with_redirects.id)}"
    )
    assert response.status_code == 307
    assert response.headers == {
        "location": list_fixture_with_redirects.unsubscribe_redirect_url
    }


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_correct_id_unknown_error(
    mock_client, mock_db_session, subscription_fixture
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.delete(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error deleting subscription"}
    assert response.status_code == 500


def test_return_all_lists(list_fixture, list_fixture_with_redirects):
    response = client.get("/lists")
    assert response.json() == [
        {
            "id": str(list_fixture.id),
            "language": list_fixture.language,
            "name": list_fixture.name,
            "service": list_fixture.service_id,
        },
        {
            "id": str(list_fixture_with_redirects.id),
            "language": list_fixture_with_redirects.language,
            "name": list_fixture_with_redirects.name,
            "service": list_fixture_with_redirects.service_id,
        },
    ]
    assert response.status_code == 200


def test_return_lists_by_service(list_fixture, list_fixture_with_redirects):
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
            "subscribe_email_template_id": str(uuid.uuid4()),
            "unsubscribe_email_template_id": str(uuid.uuid4()),
            "subscribe_phone_template_id": str(uuid.uuid4()),
            "unsubscribe_phone_template_id": str(uuid.uuid4()),
        },
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200


def test_create_list_with_undeclared_parameter():
    response = client.post(
        "/list",
        json={
            "name": "new_name",
            "language": "new_language",
            "service_id": "new_service_id",
            "subscribe_email_template_id": str(uuid.uuid4()),
            "unsubscribe_email_template_id": str(uuid.uuid4()),
            "subscribe_phone_template_id": str(uuid.uuid4()),
            "unsubscribe_phone_template_id": str(uuid.uuid4()),
            "foo": "bar",
        },
    )
    assert response.json() == {"detail": ANY}
    assert response.status_code == 422


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
    assert response.json() == {"detail": ANY}
    assert response.status_code == 422


def test_delete_list_with_bad_id():
    response = client.delete("/list/foo")
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


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
