# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring


import uuid
from unittest.mock import ANY, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from requests import HTTPError


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_with_bad_list_id(mock_client, client):
    response = client.post("/subscription", json={"list_id": ""})
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_with_id_not_found(mock_client, client):
    response = client.post("/subscription", json={"list_id": str(uuid.uuid4())})
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_empty_phone_and_email(
    mock_client, list_fixture, client
):
    response = client.post("/subscription", json={"list_id": str(list_fixture.id)})
    assert response.json() == {"error": "email and phone can not be empty"}
    assert response.status_code == 400


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_event_with_bad_email(mock_client, list_fixture, client):
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
def test_create_succeeds_with_email(mock_client, list_fixture, client):
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
def test_create_succeeds_with_phone(mock_client, list_fixture, client):
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
def test_create_fails_with_email_and_phone_validation_error(
    mock_client, list_fixture, client
):
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "phone": "123456789",
            "list_id": str(list_fixture.id),
        },
    )
    assert response.json() == {"error": "Must be one of Email or Phone"}
    assert response.status_code == 422


@patch("api_gateway.api.get_notify_client")
def test_create_email_sub_succeeds_with_redirect(
    mock_client, list_fixture_with_redirects, client
):
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "list_id": str(list_fixture_with_redirects.id),
        },
    )
    assert response.status_code == 307
    assert response.headers == {
        "content-length": "0",
        "location": list_fixture_with_redirects.subscribe_redirect_url
    }


@patch("api_gateway.api.get_notify_client")
def test_create_phone_sub_succeeds_with_redirect(
    mock_client, list_fixture_with_redirects, client
):
    response = client.post(
        "/subscription",
        json={
            "phone": "14565434545",
            "list_id": str(list_fixture_with_redirects.id),
        },
    )
    assert response.status_code == 307
    assert response.headers == {
        "content-length": "0",
        "location": list_fixture_with_redirects.subscribe_redirect_url
    }


@patch("api_gateway.api.get_notify_client")
def test_create_subscription_with_undeclared_parameter(
    mock_client, list_fixture, client
):
    response = client.post(
        "/subscription",
        json={
            "email": "test@example.com",
            "list_id": str(list_fixture.id),
            "foo": "bar",
        },
    )
    assert response.json() == {"detail": ANY}
    assert response.status_code == 422


def test_confirm_with_bad_id(client):
    response = client.get("/subscription/foo/confirm")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


def test_confirm_with_id_not_found(client):
    response = client.get(f"/subscription/{str(uuid.uuid4())}/confirm")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


def test_confirm_with_correct_id(session, subscription_fixture, client):
    response = client.get(f"/subscription/{str(subscription_fixture.id)}/confirm")
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200
    session.refresh(subscription_fixture)
    assert subscription_fixture.confirmed is True


def test_confirm_with_correct_id_and_redirects(
    session, subscription_fixture_with_redirects, list_fixture_with_redirects, client
):
    response = client.get(
        f"/subscription/{str(subscription_fixture_with_redirects.id)}/confirm",
        allow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers == {
        "content-length": "0",
        "location": list_fixture_with_redirects.confirm_redirect_url
    }
    session.refresh(subscription_fixture_with_redirects)
    assert subscription_fixture_with_redirects.confirmed is True


@patch("api_gateway.api.db_session")
def test_confirm_with_correct_id_unknown_error(
    mock_db_session, subscription_fixture, client
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.get(f"/subscription/{str(subscription_fixture.id)}/confirm")
    assert response.json() == {"error": "error confirming subscription"}
    assert response.status_code == 500


@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_bad_id(mock_client, client):
    response = client.delete("/subscription/foo")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_id_not_found(mock_client, client):
    response = client.delete(f"/subscription/{str(uuid.uuid4())}")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_correct_id(mock_client, subscription_fixture, client):
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
    mock_client,
    subscription_fixture_with_redirects,
    list_fixture_with_redirects,
    client,
):
    response = client.delete(
        f"/subscription/{str(subscription_fixture_with_redirects.id)}"
    )
    assert response.status_code == 307
    assert response.headers == {
        "content-length": "0",
        "location": list_fixture_with_redirects.unsubscribe_redirect_url
    }


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_unsubscribe_event_with_correct_id_unknown_error(
    mock_client, mock_db_session, subscription_fixture, client
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.delete(f"/subscription/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error deleting subscription"}
    assert response.status_code == 500


@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_bad_id(mock_client, client):
    response = client.get("/unsubscribe/foo")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_id_not_found(mock_client, client):
    response = client.get(f"/unsubscribe/{str(uuid.uuid4())}")
    assert response.json() == {"error": "subscription not found"}
    assert response.status_code == 404


@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_correct_id(
    mock_client, subscription_fixture, client
):
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
    mock_client,
    subscription_fixture_with_redirects,
    list_fixture_with_redirects,
    client,
):
    response = client.get(
        f"/unsubscribe/{str(subscription_fixture_with_redirects.id)}",
        allow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers == {
        "content-length": "0",
        "location": list_fixture_with_redirects.unsubscribe_redirect_url
    }


@patch("api_gateway.api.db_session")
@patch("api_gateway.api.get_notify_client")
def test_get_unsubscribe_event_with_correct_id_unknown_error(
    mock_client, mock_db_session, subscription_fixture, client
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
    mock_client, mock_db_session, subscription_fixture, client
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = HTTPError()
    mock_db_session.return_value = mock_session
    response = client.get(f"/unsubscribe/{str(subscription_fixture.id)}")
    assert response.json() == {"error": "error sending unsubscription notification"}
    assert response.status_code == 502
