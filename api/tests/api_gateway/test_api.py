# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import json
import os
import main
import pytest
import uuid

from aws_lambda_powertools.metrics import MetricUnit
from fastapi import HTTPException, status
from unittest.mock import ANY, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from requests import HTTPError
from models.List import List
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
    session.expire_all()

    mock_client().send_bulk_notifications.assert_called_once()


def test_return_all_lists(list_fixture, list_fixture_with_redirects, client):
    response = client.get("/lists")
    data = response.json()
    assert len(data) == 2

    assert find_item_in_dict_list(data, "id", str(list_fixture.id)) is not None
    assert (
        find_item_in_dict_list(data, "id", str(list_fixture_with_redirects.id))
        is not None
    )
    assert response.status_code == 200


def test_return_all_lists_with_additional_data(
    list_fixture, list_fixture_with_redirects, client
):
    response = client.get("/lists")

    response_list = find_item_in_dict_list(response.json(), "id", str(list_fixture.id))
    response_list_with_redirects = find_item_in_dict_list(
        response.json(), "id", str(list_fixture_with_redirects.id)
    )

    assert len(response.json()) == 2

    assert response_list == json.loads(
        json.dumps(
            {
                "id": str(list_fixture.id),
                "language": list_fixture.language,
                "name": list_fixture.name,
                "service_id": list_fixture.service_id,
                "subscribe_email_template_id": list_fixture.subscribe_email_template_id,
                "unsubscribe_email_template_id": list_fixture.unsubscribe_email_template_id,
                "subscribe_phone_template_id": list_fixture.subscribe_phone_template_id,
                "unsubscribe_phone_template_id": list_fixture.unsubscribe_phone_template_id,
                "subscriber_count": 1,
            }
        )
    )

    assert response_list_with_redirects == json.loads(
        json.dumps(
            {
                "id": str(list_fixture_with_redirects.id),
                "language": list_fixture_with_redirects.language,
                "name": list_fixture_with_redirects.name,
                "service_id": list_fixture_with_redirects.service_id,
                "subscribe_email_template_id": list_fixture_with_redirects.subscribe_email_template_id,
                "unsubscribe_email_template_id": list_fixture_with_redirects.unsubscribe_email_template_id,
                "subscribe_phone_template_id": list_fixture_with_redirects.subscribe_phone_template_id,
                "unsubscribe_phone_template_id": list_fixture_with_redirects.unsubscribe_phone_template_id,
                "subscribe_redirect_url": list_fixture_with_redirects.subscribe_redirect_url,
                "confirm_redirect_url": list_fixture_with_redirects.confirm_redirect_url,
                "unsubscribe_redirect_url": list_fixture_with_redirects.unsubscribe_redirect_url,
                "subscriber_count": 0,
            }
        )
    )

    assert response.status_code == 200


def test_return_lists_with_one_containing_only_required_data(
    list_fixture_required_data_only, client
):
    response = client.get("/lists")
    assert {
        "id": str(list_fixture_required_data_only.id),
        "language": list_fixture_required_data_only.language,
        "name": list_fixture_required_data_only.name,
        "service_id": list_fixture_required_data_only.service_id,
        "subscriber_count": 0,
    } in response.json()

    assert response.status_code == 200


def test_return_lists_by_service(list_fixture, list_fixture_with_redirects, client):
    response = client.get(f"/lists/{list_fixture.service_id}")
    assert {
        "id": str(list_fixture.id),
        "language": list_fixture.language,
        "name": list_fixture.name,
        "service_id": list_fixture.service_id,
        "subscribe_email_template_id": list_fixture_with_redirects.subscribe_email_template_id,
        "unsubscribe_email_template_id": list_fixture_with_redirects.unsubscribe_email_template_id,
        "subscribe_phone_template_id": list_fixture_with_redirects.subscribe_phone_template_id,
        "unsubscribe_phone_template_id": list_fixture_with_redirects.unsubscribe_phone_template_id,
        "subscriber_count": 1,
    } in response.json()

    assert response.status_code == 200


def test_create_list(client):
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


def test_create_list_with_undeclared_parameter(client):
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


def test_create_list_with_error(client):
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
def test_create_list_with_unknown_error(mock_db_session, client):
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
def test_create_list_invalid_domain(field, value, client):
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
def test_create_list_valid_domain(field, value, client):
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


def test_delete_list_with_bad_id(client):
    response = client.delete(
        "/list/foo",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_delete_list_with_id_not_found(client):
    response = client.delete(
        f"/list/{str(uuid.uuid4())}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_delete_list_with_correct_id(session, client):
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
def test_delete_list_with_correct_id_unknown_error(
    mock_db_session, list_fixture, client
):
    mock_session = MagicMock()
    mock_session.commit.side_effect = SQLAlchemyError()
    mock_db_session.return_value = mock_session
    response = client.delete(
        f"/list/{str(list_fixture.id)}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
    )
    assert response.json() == {"error": "error deleting list"}
    assert response.status_code == 500


def test_edit_list_with_bad_id(client):
    response = client.put(
        "/list/foo",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"name": "name", "language": "language", "service_id": "service_id"},
    )
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_edit_list_with_id_not_found(client):
    response = client.put(
        f"/list/{str(uuid.uuid4())}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"name": "name", "language": "language", "service_id": "service_id"},
    )
    assert response.json() == {"error": "list not found"}
    assert response.status_code == 404


def test_edit_list_with_correct_id(session, client):
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


def test_edit_list_without_supplying_service_id_and_name(session, client):

    list = List(
        name="name_1",
        language="English",
        service_id="service_id_1",
        subscribe_email_template_id=str(uuid.uuid4()),
    )
    session.add(list)
    session.commit()
    response = client.put(
        f"/list/{str(list.id)}",
        headers={"Authorization": os.environ["API_AUTH_TOKEN"]},
        json={"subscribe_email_template_id": "ea974231-002b-4889-87f1-0b9cf48e9411"},
    )
    assert response.json() == {"status": "OK"}
    assert response.status_code == 200
    session.expire_all()
    list = session.query(List).get(list.id)
    assert list.subscribe_email_template_id == "ea974231-002b-4889-87f1-0b9cf48e9411"


@patch("api_gateway.api.db_session")
def test_edit_list_with_correct_id_unknown_error(mock_db_session, list_fixture, client):
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
def test_send_no_api_key(mock_client, client):
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
def test_send_invalid_list(mock_client, client):
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
def test_send_notify_error(mock_client, mock_db_session, client):

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
def test_send_duplicate_emails(mock_client, list_fixture_with_duplicates, client):
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
def test_send_duplicate_phones(mock_client, list_fixture_with_duplicates, client):
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
    assert data["status"] == "OK"
    assert data["sent"] == 3


@patch("api_gateway.api.get_notify_client")
def test_global_exception_handler(mock_client, list_fixture, client):
    template_id = str(uuid.uuid4())
    mock_client.side_effect = Exception("Unknown error")

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

    mock_client.assert_called_once()
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@patch("main.Mangum")
def test_metrics(mock_mangum, context_fixture, capsys, metrics):

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
def test_verify_token_throws_an_exception_if_token_is_not_correct(
    mock_metrics, api_verify_token
):
    request = MagicMock()
    request.headers = {"Authorization": "invalid"}
    with pytest.raises(HTTPException):
        assert api_verify_token(request)
    mock_metrics.add_metric.assert_called_once_with(
        name="IncorrectAuthorizationToken", unit=MetricUnit.Count, value=1
    )


def test_verify_token_returns_true_if_token_is_correct(api_verify_token):
    request = MagicMock()
    request.headers = {"Authorization": os.environ["API_AUTH_TOKEN"]}
    assert api_verify_token(request)


def subscribe_users(session, user_list, fixture):
    for user in user_list:
        subscription = Subscription(
            email=user["email"], list=fixture, confirmed=user["confirmed"]
        )
        session.add(subscription)
        session.commit()


def find_item_in_dict_list(data, identifier, value):
    return next((item for item in data if item[identifier] == value), None)


@patch("api_gateway.api.get_notify_client")
def test_counts_when_list_has_no_subscribers(mock_client, list_count_fixture_1, client):
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
    client,
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
    item = find_item_in_dict_list(data, "list_id", str(list_count_fixture_1.id))
    assert item is not None
    assert item["subscriber_count"] == 2

    # check list 2
    item = find_item_in_dict_list(data, "list_id", str(list_count_fixture_2.id))
    assert item is not None
    assert item["subscriber_count"] == 3


@patch("api_gateway.api.get_notify_client")
def test_unique_counts_for_list_subscribers(
    mock_client,
    session,
    list_count_fixture_1,
    client,
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
    item = find_item_in_dict_list(data, "list_id", str(list_count_fixture_1.id))
    assert item is not None
    assert item["subscriber_count"] == 2


@patch("api_gateway.api.get_notify_client")
def test_remove_all_subscribers_from_list(
    mock_client,
    session,
    list_reset_fixture_0,
    client,
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


def test_return_list_subscriber_count(list_with_subscribers, client, session):
    response = client.get("/lists")
    assert response.status_code == 200
    data = response.json()

    # check #1
    item = find_item_in_dict_list(data, "id", str(list_with_subscribers[0].id))
    assert item is not None
    assert item["subscriber_count"] == 2

    # checking #2 list
    item = find_item_in_dict_list(data, "id", str(list_with_subscribers[1].id))
    assert item is not None
    assert item["subscriber_count"] == 1
    # check details
    assert {
        "id": str(list_with_subscribers[0].id),
        "language": list_with_subscribers[0].language,
        "name": list_with_subscribers[0].name,
        "service_id": list_with_subscribers[0].service_id,
        "subscribe_email_template_id": list_with_subscribers[
            0
        ].subscribe_email_template_id,
        "unsubscribe_email_template_id": list_with_subscribers[
            0
        ].unsubscribe_email_template_id,
        "subscribe_phone_template_id": list_with_subscribers[
            0
        ].subscribe_phone_template_id,
        "unsubscribe_phone_template_id": list_with_subscribers[
            0
        ].unsubscribe_phone_template_id,
        "subscriber_count": 2,
    } in data

    session.expire_all()
