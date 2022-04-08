# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import uuid
from sqlalchemy.exc import SQLAlchemyError
from models.Subscription import Subscription
from unittest.mock import MagicMock, patch

##
# Old Endpoint Tests
##


def test_email_list_import(session, list_to_be_updated_fixture, client):
    data = session.query(Subscription).filter(
        Subscription.list_id == list_to_be_updated_fixture.id
    )
    assert data.count() == 0

    # create email list payload
    email_list = [f"email{str(x)}@example.com" for x in range(10)]
    response = client.post(
        "/listimport",
        json={"list_id": str(list_to_be_updated_fixture.id), "emails": email_list},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

    data = session.query(Subscription).filter(
        Subscription.list_id == list_to_be_updated_fixture.id,
        Subscription.confirmed.is_(True),
    )
    assert data.count() == 10


def test_email_list_import_list_id_not_valid(client):
    # email payload
    email_list = [f"email{str(x)}@example.com" for x in range(1)]
    response = client.post(
        "/listimport",
        json={"list_id": "invalid_list_id", "emails": email_list},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "list_id"],
                "msg": "value is not a valid uuid",
                "type": "type_error.uuid",
            }
        ]
    }


def test_email_list_import_list_not_found(client):
    # email payload
    email_list = [f"email{str(x)}@example.com" for x in range(2)]
    response = client.post(
        "/listimport",
        json={"list_id": str(uuid.uuid4()), "emails": email_list},
    )
    assert response.status_code == 404
    assert response.json() == {"error": "list not found"}


def test_email_list_import_empty_list_of_emails(list_to_be_updated_fixture, client):
    response = client.post(
        "/listimport",
        json={"list_id": str(list_to_be_updated_fixture.id), "emails": list()},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "emails"],
                "msg": "ensure this value has at least 1 items",
                "type": "value_error.list.min_items",
                "ctx": {"limit_value": 1},
            }
        ]
    }


def test_email_list_import_max_emails_allow_is_10000(
    list_to_be_updated_fixture, client
):
    # emails payload
    email_list = [f"email{str(x)}@example.com" for x in range(10001)]
    response = client.post(
        "/listimport",
        json={"list_id": str(list_to_be_updated_fixture.id), "emails": email_list},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "emails"],
                "msg": "ensure this value has at most 10000 items",
                "type": "value_error.list.max_items",
                "ctx": {"limit_value": 10000},
            }
        ]
    }


@patch("api_gateway.api.db_session")
def test_email_list_with_unknown_error(
    mock_db_session, list_to_be_updated_fixture, client
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    email_list = [f"email{str(x)}@example.com" for x in range(1)]
    response = client.post(
        "/listimport",
        json={
            "list_id": str(list_to_be_updated_fixture.id),
            "emails": email_list,
        },
    )
    assert response.status_code == 500


##
# New Endpoint Tests
##


def test_email_list_import_new(session, list_to_be_updated_fixture, client):
    # Empty subscriptions table
    data = (
        session.query(Subscription)
        .filter(Subscription.list_id == list_to_be_updated_fixture.id)
        .delete()
    )

    # create email list payload
    email_list = [f"email{str(x)}@example.com" for x in range(10)]
    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        json={"email": email_list},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

    data = session.query(Subscription).filter(
        Subscription.list_id == list_to_be_updated_fixture.id,
        Subscription.email.is_not(None),
        Subscription.confirmed.is_(True),
    )
    assert data.count() == 10


def test_phone_list_import(session, list_to_be_updated_fixture, client):
    # Empty subscriptions table
    data = (
        session.query(Subscription)
        .filter(Subscription.list_id == list_to_be_updated_fixture.id)
        .delete()
    )

    # create phone list payload
    phone_list = [f"555-{str(x)}55-5555" for x in range(10)]
    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        json={"phone": phone_list},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

    data = session.query(Subscription).filter(
        Subscription.list_id == list_to_be_updated_fixture.id,
        Subscription.phone.is_not(None),
        Subscription.confirmed.is_(True),
    )
    assert data.count() == 10


def test_phone_list_import_invalid_number(list_to_be_updated_fixture, client):
    # create phone list payload
    phone_list = ["555-555", "555-555-5555"]
    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        json={"phone": phone_list},
    )
    assert response.status_code == 422


def test_email_list_import_invalid_email(list_to_be_updated_fixture, client):
    # create phone list payload
    phone_list = ["NotAnEmail", "email@example.com"]
    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        json={"phone": phone_list},
    )
    assert response.status_code == 422


def test_import_validation_only_one(list_to_be_updated_fixture, client):
    # Can only submit one of phone<list> or email<list>
    phone_list = []
    email_list = []

    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        json={"phone": phone_list, "email": email_list},
    )
    assert response.status_code == 422


def test_import_validation_empty_list(list_to_be_updated_fixture, client):
    # List can't be empty
    phone_list = []

    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        json={"phone": phone_list},
    )
    assert response.status_code == 422


def test_import_validation_at_least_one(list_to_be_updated_fixture, client):
    # Must submit one of phone<list> or email<list>
    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        json={},
    )
    assert response.status_code == 422
