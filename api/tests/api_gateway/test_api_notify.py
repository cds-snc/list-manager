# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from api_gateway.api import send_bulk_notify, get_unsubscribe_link, SendPayload
from unittest.mock import patch, ANY
import uuid


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

    subscriber_arr = [["email address", "unsubscribe_link"]] + [
        [x["email"], get_unsubscribe_link(str(x["id"]))]
        for x in subscribers
        if x["email"]
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
