import os
import json
import main
import pytest
import uuid

from aws_lambda_powertools.metrics import MetricUnit
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import ANY, MagicMock, patch
from importlib import reload

from api_gateway import api
from sqlalchemy.exc import SQLAlchemyError
from requests import HTTPError

from models.List import List
from models.Subscription import Subscription

from api_gateway.api import send_bulk_notify, SendPayload

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
            "name": "fixture_name",
            "confirm_link": ANY,
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
        personalisation={"name": "fixture_name"},
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


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_create_succeeds_with_email_and_phone_notify_error(
    mock_client, mock_db_session, list_fixture
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = HTTPError()
    mock_db_session.return_value = mock_session
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "phone": "123456789",
            "list_id": str(list_fixture.id),
        },
    )
    assert response.json() == {"error": "error sending subscription notification"}
    assert response.status_code == 502


def test_confirm_with_bad_id():
    response = client.get("/subscription/foo/confirm")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


def test_confirm_with_id_not_found():
    response = client.get(f"/subscription/{str(uuid.uuid4())}/confirm")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


def test_confirm_with_correct_id(session, subscription_fixture):
    response = client.get(f"/subscription/{str(subscription_fixture.id)}/confirm")
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200
    session.refresh(subscription_fixture)
    assert subscription_fixture.confirmed is True


def test_confirm_with_correct_id_and_redirects(
    session, subscription_fixture_with_redirects, list_fixture_with_redirects
):
    response = client.get(
        f"/subscription/{str(subscription_fixture_with_redirects.id)}/confirm",
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
    response = client.get(f"/subscription/{str(subscription_fixture.id)}/confirm")
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
        personalisation={
            "email_address": "fixture_email",
            "name": "fixture_name",
        },
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


@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_bad_id(mock_client):
    response = client.get("/unsubscribe/foo")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_id_not_found(mock_client):
    response = client.get(f"/unsubscribe/{str(uuid.uuid4())}")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_correct_id(mock_client, subscription_fixture):
    response = client.get(f"/unsubscribe/{str(subscription_fixture.id)}")
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
        personalisation={
            "email_address": "fixture_email",
            "name": "fixture_name",
        },
    )


@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_correct_id_and_redirect(
    mock_client, subscription_fixture_with_redirects, list_fixture_with_redirects
):
    response = client.get(
        f"/unsubscribe/{str(subscription_fixture_with_redirects.id)}",
        allow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers == {
        "location": list_fixture_with_redirects.unsubscribe_redirect_url
    }


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_correct_id_unknown_error(
    mock_client, mock_db_session, subscription_fixture
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.get(f"/unsubscribe/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error deleting subscription"}
    assert response.status_code == 500


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_correct_id_notify_error(
    mock_client, mock_db_session, subscription_fixture
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = HTTPError()
    mock_db_session.return_value = mock_session
    response = client.get(f"/unsubscribe/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error sending unsubscription notification"}
    assert response.status_code == 502


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
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
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
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
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
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"detail": ANY}
    assert response.status_code == 422


@patch("api_gateway.api.db_session")
def test_create_list_with_unknown_error(mock_db_session):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError("fakeerror")
    mock_db_session.return_value = mock_session
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
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"error": "error saving list: fakeerror"}
    assert response.status_code == 500


@pytest.mark.parametrize(
    "field,value",
    [
        ("subscribe_redirect_url", "https://example.com/redirect_target"),
        ("confirm_redirect_url", "https://example.com/redirect_target"),
        ("unsubscribe_redirect_url", "https://example.com/redirect_target"),
    ],
)
def test_create_list_invalid_domain(field, value):
    response = client.post(
        "/list",
        json={
            "name": f"new_name_{uuid.uuid4()}",
            "language": "new_language",
            "service_id": "new_service_id",
            "subscribe_email_template_id": str(uuid.uuid4()),
            "unsubscribe_email_template_id": str(uuid.uuid4()),
            "subscribe_phone_template_id": str(uuid.uuid4()),
            "unsubscribe_phone_template_id": str(uuid.uuid4()),
            field: value,
        },
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", field],
                "msg": "domain must be in REDIRECT_ALLOW_LIST",
                "type": "value_error",
            }
        ]
    }
    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("subscribe_redirect_url", "https://ircc.digital.canada.ca/redirect_target"),
        ("confirm_redirect_url", "https://ircc.digital.canada.ca/redirect_target"),
        ("unsubscribe_redirect_url", "https://ircc.digital.canada.ca/redirect_target"),
        ("subscribe_redirect_url", "https://ircc.digital.canada.ca/redirect_target"),
        ("confirm_redirect_url", "https://ircc.digital.canada.ca/redirect_target"),
        ("unsubscribe_redirect_url", "https://ircc.digital.canada.ca/redirect_target"),
    ],
)
def test_create_list_valid_domain(field, value):
    response = client.post(
        "/list",
        json={
            "name": f"new_name_{uuid.uuid4()}",
            "language": "new_language",
            "service_id": "new_service_id",
            "subscribe_email_template_id": str(uuid.uuid4()),
            "unsubscribe_email_template_id": str(uuid.uuid4()),
            "subscribe_phone_template_id": str(uuid.uuid4()),
            "unsubscribe_phone_template_id": str(uuid.uuid4()),
            field: value,
        },
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"id": ANY}
    assert response.status_code == 200


def test_delete_list_with_bad_id():
    response = client.delete(
        "/list/foo",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_delete_list_with_id_not_found():
    response = client.delete(
        f"/list/{str(uuid.uuid4())}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
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
    response = client.delete(
        f"/list/{str(list.id)}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200


@patch("api_gateway.api.db_session")
def test_delete_list_with_correct_id_unknown_error(mock_db_session, list_fixture):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.delete(
        f"/list/{str(list_fixture.id)}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"error": "error deleting list"}
    assert response.status_code == 500


def test_edit_list_with_bad_id():
    response = client.put(
        "/list/foo",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"name": "name", "language": "language", "service_id": "service_id"},
    )
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_edit_list_with_id_not_found():
    response = client.put(
        f"/list/{str(uuid.uuid4())}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"name": "name", "language": "language", "service_id": "service_id"},
    )
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_edit_list_with_correct_id(session):
    list = List(
        name="edit_name",
        language="edit_language",
        service_id="edit_service_id",
        subscribe_email_template_id="edit_subscribe_email_template_id",
        unsubscribe_email_template_id="edit_unsubscribe_email_template_id",
        subscribe_phone_template_id="edit_subscribe_phone_template_id",
        unsubscribe_phone_template_id="edit_unsubscribe_phone_template_id",
    )
    session.add(list)
    session.commit()
    response = client.put(
        f"/list/{str(list.id)}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "name": "edited_name",
            "language": "edited_language",
            "service_id": "edited_service_id",
        },
    )
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200
    session.expire_all()
    list = session.query(List).get(list.id)
    assert list.name == "edited_name"
    assert list.language == "edited_language"
    assert list.service_id == "edited_service_id"


@patch("api_gateway.api.db_session")
def test_edit_list_with_correct_id_unknown_error(mock_db_session, list_fixture):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.put(
        f"/list/{str(list_fixture.id)}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "name": "edited_name",
            "language": "edited_language",
            "service_id": "edited_service_id",
        },
    )
    assert response.json() == {"error": "error updating list"}
    assert response.status_code == 500


@patch("api_gateway.api.get_notify_client")
def test_send_no_api_key(mock_client):
    response = client.post(
        "/send",
        json={
            "list_id": str(uuid.uuid4()),
            "template_id": str(uuid.uuid4()),
            "template_type": "email",
        },
    )
    data = response.json()
    assert data == {"detail": "Unauthorized"}
    assert response.status_code == 401


@patch("api_gateway.api.get_notify_client")
def test_send_invalid_list(mock_client):
    response = client.post(
        "/send",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(uuid.uuid4()),
            "template_id": str(uuid.uuid4()),
            "template_type": "email",
        },
    )
    data = response.json()
    assert "error" in data
    assert "not found" in data["error"]
    assert response.status_code == 404


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_send_notify_error(mock_client, mock_db_session):

    mock_client.side_effect = HTTPError()
    response = client.post(
        "/send",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(uuid.uuid4()),
            "template_id": str(uuid.uuid4()),
            "template_type": "email",
        },
    )
    assert response.json() == {"error": "error sending bulk notifications"}
    assert response.status_code == 502


@patch("api_gateway.api.get_notify_client")
def test_send_email(mock_client, list_fixture):
    template_id = str(uuid.uuid4())
    response = client.post(
        "/send",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(list_fixture.id),
            "template_id": template_id,
            "template_type": "email",
            "job_name": "Job Name",
        },
    )
    data = response.json()
    assert data["status"] == "OK"
    assert data["sent"] == 1
    assert response.status_code == 200

    mock_client().send_bulk_notifications.assert_called_once()


@patch("api_gateway.api.get_notify_client")
def test_send_more_than_limit(mock_client):
    limit = 50000
    items = 50001
    calls_to_make = -(-items // limit)  # Ceil of items / limit

    emails = [{"email": "t@s.t", "id": x} for x in range(items)]

    send_payload = SendPayload(
        list_id=str(uuid.uuid4()),
        template_type="email",
        template_id=str(uuid.uuid4()),
        job_name="Job Name",
    )

    calls = [ANY for x in range(calls_to_make)]

    emails_sent = send_bulk_notify(len(emails), send_payload, emails, limit)
    mock_client().send_bulk_notifications.assert_has_calls(calls)
    assert emails_sent == items


@patch("api_gateway.api.get_notify_client")
def test_send_emails_only(mock_client):
    subscribers = [
        {"email": "one@two.com", "phone": None, "id": "1"},
        {"email": None, "phone": "1234567890", "id": "1"},
        {"email": "one@three.com", "phone": None, "id": "1"},
    ]

    template_id = str(uuid.uuid4())
    send_payload = SendPayload(
        list_id=str(uuid.uuid4()),
        template_type="email",
        template_id=template_id,
        job_name="Job Name",
    )

    subscriber_arr = [["email address", "subscription id"]] + [
        [x["email"], x["id"]] for x in subscribers if x["email"]
    ]

    emails_sent = send_bulk_notify(len(subscribers), send_payload, subscribers)
    mock_client().send_bulk_notifications.assert_called_once_with(
        "Job Name", subscriber_arr, template_id
    )
    assert emails_sent == 2


@patch("api_gateway.api.get_notify_client")
def test_send_sms_only(mock_client):
    subscribers = [
        {"email": "one@two.com", "phone": None, "id": "1"},
        {"email": None, "phone": "1234567890", "id": "1"},
        {"email": "one@three.com", "phone": None, "id": "1"},
    ]

    template_id = str(uuid.uuid4())
    send_payload = SendPayload(
        list_id=str(uuid.uuid4()),
        template_type="phone",
        template_id=template_id,
        job_name="Job Name",
    )

    subscriber_arr = [["phone number", "subscription id"]] + [
        [x["phone"], x["id"]] for x in subscribers if x["phone"]
    ]

    emails_sent = send_bulk_notify(len(subscribers), send_payload, subscribers)
    mock_client().send_bulk_notifications.assert_called_once_with(
        "Job Name", subscriber_arr, template_id
    )
    assert emails_sent == 1


@patch("api_gateway.api.get_notify_client")
def test_send_duplicate_emails(mock_client, list_fixture_with_duplicates):
    template_id = str(uuid.uuid4())
    response = client.post(
        "/send",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(list_fixture_with_duplicates.id),
            "template_id": template_id,
            "template_type": "email",
            "job_name": "Job Name",
        },
    )
    data = response.json()

    assert data["status"] == "OK"
    assert data["sent"] == 2

    response = client.post(
        "/send",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(list_fixture_with_duplicates.id),
            "template_id": template_id,
            "template_type": "email",
            "job_name": "Job Name",
            "unique": False,
        },
    )
    data = response.json()

    assert data["status"] == "OK"
    assert data["sent"] == 4


@patch("api_gateway.api.get_notify_client")
def test_send_duplicate_phones(mock_client, list_fixture_with_duplicates):
    template_id = str(uuid.uuid4())
    response = client.post(
        "/send",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(list_fixture_with_duplicates.id),
            "template_id": template_id,
            "template_type": "phone",
            "job_name": "Job Name",
        },
    )
    data = response.json()

    assert data["status"] == "OK"
    assert data["sent"] == 2

    template_id = str(uuid.uuid4())
    response = client.post(
        "/send",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(list_fixture_with_duplicates.id),
            "template_id": template_id,
            "template_type": "phone",
            "job_name": "Job Name",
            "unique": False,
        },
    )
    data = response.json()
    print(data)
    assert data["status"] == "OK"
    assert data["sent"] == 3


@patch("main.Mangum")
def test_metrics(mock_mangum, context_fixture, capsys):

    mock_asgi_handler = MagicMock()
    mock_asgi_handler.return_value = True
    mock_mangum.return_value = mock_asgi_handler
    main.handler({"httpMethod": "GET"}, context_fixture)

    log = capsys.readouterr().out.strip()

    metrics_output = json.loads(log)

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
        assert metric in str(metrics_output["_aws"]["CloudWatchMetrics"][0]["Metrics"])


@patch("api_gateway.api.metrics")
def test_verify_token_throws_an_exception_if_token_is_not_correct(mock_metrics):
    request = MagicMock()
    request.headers = {"Authorization": "invalid"}
    with pytest.raises(HTTPException):
        assert api.verify_token(request)
    mock_metrics.add_metric.assert_called_once_with(
        name="IncorrectAuthorizationToken", unit=MetricUnit.Count, value=1
    )


def test_verify_token_returns_true_if_token_is_correct():
    request = MagicMock()
    request.headers = {"Authorization": os.environ["API_AUTH_TOKEN"]}
    assert api.verify_token(request)


def subscribe_users(session, user_list, fixture):
    for user in user_list:
        subscription = Subscription(
            email=user["email"], list=fixture, confirmed=user["confirmed"]
        )
        session.add(subscription)
        session.commit()


def find_item_by_id(data, item_id):
    item = [element for element in data if element["list_id"] == item_id]
    if len(item) == 0:
        return []

    return item[0]


@patch("api_gateway.api.get_notify_client")
def test_counts_when_list_has_no_subscribers(mock_client, list_count_fixture_1):
    response = client.get(
        f"/lists/{str(list_count_fixture_1.service_id)}/subscriber-count",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    data = response.json()

    assert len(data) == 0


@patch("api_gateway.api.get_notify_client")
def test_counts_when_list_has_subscribers(
    mock_client,
    session,
    list_count_fixture_0,
    list_count_fixture_1,
    list_count_fixture_2,
):
    # add subscribers to list 0
    # note service id doesn't match the other lists
    # i.e. these shouldn't end up in the response
    list_0_emails = [
        {"email": "list0+0@example.com", "confirmed": True},
        {"email": "list0+1@example.com", "confirmed": False},
        {"email": "list0+2@example.com", "confirmed": True},
        {"email": "list0+3@example.com", "confirmed": False},
    ]

    subscribe_users(session, list_0_emails, list_count_fixture_0)

    # add subscribers to list 1
    list_1_emails = [
        {"email": "list1+0@example.com", "confirmed": False},
        {"email": "list1+1@example.com", "confirmed": True},
        {"email": "list1+2@example.com", "confirmed": True},
    ]

    subscribe_users(session, list_1_emails, list_count_fixture_1)

    # add subscribers to list 2
    list_2_emails = [
        {"email": "list2+0@example.com", "confirmed": True},
        {"email": "list2+1@example.com", "confirmed": True},
        {"email": "list2+2@example.com", "confirmed": True},
        {"email": "list2+3@example.com", "confirmed": False},
    ]

    subscribe_users(session, list_2_emails, list_count_fixture_2)

    response = client.get(
        f"/lists/{str(list_count_fixture_1.service_id)}/subscriber-count",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )

    data = response.json()

    assert len(data) == 2

    # check list 1
    assert find_item_by_id(data, str(list_count_fixture_1.id))["subscriber_count"] == 2

    # check list 2
    assert find_item_by_id(data, str(list_count_fixture_2.id))["subscriber_count"] == 3


@patch("api_gateway.api.get_notify_client")
def test_unique_counts_for_list_subscribers(
    mock_client,
    session,
    list_count_fixture_1,
):
    # add subscribers to list 1
    list_1_emails = [
        {"email": "list1+0@example.com", "confirmed": False},
        {"email": "list1+1@example.com", "confirmed": True},
        {"email": "list1+2@example.com", "confirmed": True},
        {"email": "list1+1@example.com", "confirmed": True},
        {"email": "list1+1@example.com", "confirmed": True},
    ]

    subscribe_users(session, list_1_emails, list_count_fixture_1)

    response = client.get(
        f"/lists/{str(list_count_fixture_1.service_id)}/subscriber-count?unique=1",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )

    data = response.json()

    # check list 1
    assert find_item_by_id(data, str(list_count_fixture_1.id))["subscriber_count"] == 2


@patch("api_gateway.api.get_notify_client")
def test_remove_all_subscribers_from_list(
    mock_client,
    session,
    list_reset_fixture_0,
):
    # add subscribers to list 0
    list_0_emails = [
        {"email": "list0+0@example.com", "confirmed": True},
        {"email": "list0+1@example.com", "confirmed": False},
        {"email": "list0+2@example.com", "confirmed": True},
        {"email": "list0+3@example.com", "confirmed": True},
    ]

    subscribe_users(session, list_0_emails, list_reset_fixture_0)

    data = session.query(Subscription).filter(
        Subscription.list_id == list_reset_fixture_0.id
    )

    assert data.count() == 4

    # reset the list
    client.put(
        f"/list/{str(list_reset_fixture_0.id)}/reset",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )

    data = session.query(Subscription).filter(
        Subscription.list_id == list_reset_fixture_0.id
    )
    assert data.count() == 0

    # add one user back
    subscribe_users(
        session,
        [
            {"email": "list-new+0@example.com", "confirmed": True},
        ],
        list_reset_fixture_0,
    )

    data = session.query(Subscription).filter(
        Subscription.list_id == list_reset_fixture_0.id
    )
    assert data.count() == 1


@patch.dict(os.environ, {"OPENAPI_URL": "", "API_AUTH_TOKEN": str(uuid.uuid4())}, clear=True)
def test_api_docs_disabled_via_environ():
    reload(api)

    my_client = TestClient(api.app)
    response = my_client.get("/docs")
    assert response.status_code == 404

    response = my_client.get("/redoc")
    assert response.status_code == 404

    response = my_client.get("/openapi.json")
    assert response.status_code == 404


@patch.dict(os.environ, {"OPENAPI_URL": "/openapi.json", "API_AUTH_TOKEN": str(uuid.uuid4())}, clear=True)
def test_api_docs_enabled_via_environ():
    reload(api)

    my_client = TestClient(api.app)
    response = my_client.get("/docs")
    assert response.status_code == 200

    response = my_client.get("/redoc")
    assert response.status_code == 200

    response = my_client.get("/openapi.json")
    assert response.status_code == 200


@patch.dict(os.environ, clear=True)
@pytest.mark.xfail(raises=ValueError)
def test_api_auth_token_not_set():
    reload(api)
