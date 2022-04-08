import uuid

from unittest.mock import patch
from requests import HTTPError
from models.Subscription import Subscription


@patch("api_gateway.api.get_notify_client")
def test_send_email(mock_client, list_fixture, client, session):
    subscription0 = Subscription(
        email="fixture_email_101", list=list_fixture, confirmed=True
    )
    session.add(subscription0)
    session.commit()

    template_id = str(uuid.uuid4())
    response = client.post(
        "/send",
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(list_fixture.id),
            "template_id": template_id,
            "template_type": "email",
            "job_name": "Job Name",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "OK"
    assert data["sent"] == 1
    session.expire_all()

    mock_client().send_bulk_notifications.assert_called_once()


@patch("api_gateway.api.get_notify_client")
def test_send_no_api_key(mock_client, client):
    response = client.post(
        "/send",
        headers={"Authorization": ""},
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
def test_send_invalid_list(mock_client, client):
    response = client.post(
        "/send",
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
def test_send_notify_error(mock_client, mock_db_session, client):

    mock_client.side_effect = HTTPError()
    response = client.post(
        "/send",
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
def test_send_duplicate_emails(mock_client, list_fixture_with_duplicates, client):
    template_id = str(uuid.uuid4())
    response = client.post(
        "/send",
        json={
            "service_api_key": str(uuid.uuid4()),
            "list_id": str(list_fixture_with_duplicates.id),
            "template_id": template_id,
            "template_type": "email",
            "job_name": "Job Name",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "OK"
    assert data["sent"] == 2

    response = client.post(
        "/send",
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
def test_send_duplicate_phones(mock_client, list_fixture_with_duplicates, client):
    template_id = str(uuid.uuid4())
    response = client.post(
        "/send",
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
    assert data["status"] == "OK"
    assert data["sent"] == 3
