# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import os
from models.Subscription import Subscription

##
# New List Import endpoint
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
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
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
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
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
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"phone": phone_list},
    )
    assert response.status_code == 422


def test_email_list_import_invalid_email(list_to_be_updated_fixture, client):
    # create phone list payload
    phone_list = ["NotAnEmail", "email@example.com"]
    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"phone": phone_list},
    )
    assert response.status_code == 422


def test_import_validation_only_one(list_to_be_updated_fixture, client):
    # Can only submit one of phone<list> or email<list>
    phone_list = []
    email_list = []

    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"phone": phone_list, "email": email_list},
    )
    assert response.status_code == 422


def test_import_validation_empty_list(list_to_be_updated_fixture, client):
    # List can't be empty
    phone_list = []

    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"phone": phone_list},
    )
    assert response.status_code == 422


def test_import_validation_at_least_one(list_to_be_updated_fixture, client):
    # Must submit one of phone<list> or email<list>
    response = client.post(
        f"/list/{list_to_be_updated_fixture.id}/import",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={},
    )
    assert response.status_code == 422
