from os import environ
from fastapi import FastAPI, Response, status
from sqlalchemy.exc import SQLAlchemyError
from database.db import db_session
from logger import log

from models.List import List
from models.Subscription import Subscription

# from crawler.crawler import crawl
# import uuid
from typing import Optional
from pydantic import BaseModel
from notifications_python_client.notifications import NotificationsAPIClient


NOTIFY_KEY = environ.get("NOTIFY_KEY")

app = FastAPI(root_path="/v1")


@app.get("/version")
async def version():
    return {"version": environ.get("GIT_SHA", "unknown")}


def get_db_version(sessionmaker):
    session = sessionmaker()

    query = "SELECT version_num FROM alembic_version"
    full_name = session.execute(query).fetchone()[0]
    return full_name


@app.get("/healthcheck")
async def healthcheck():
    try:
        full_name = get_db_version(db_session)
        db_status = {"able_to_connect": True, "db_version": full_name}
    except SQLAlchemyError as err:
        log.error(err)
        db_status = {"able_to_connect": False}

    return {"database": db_status}


class ListPayload(BaseModel):
    name: str
    language: str
    service_id: str
    subscribe_email_template_id: Optional[str] = None
    unsubscribe_email_template_id: Optional[str] = None
    subscribe_phone_template_id: Optional[str] = None
    unsubscribe_phone_template_id: Optional[str] = None


@app.get("/lists")
async def lists():
    session = db_session()
    lists = session.query(List).all()
    return list(
        map(
            lambda l: {
                "id": str(l.id),
                "language": l.language,
                "name": l.name,
                "service": l.service_id,
            },
            lists,
        )
    )


@app.get("/lists/{service_id}")
async def lists_by_service(service_id):
    session = db_session()
    lists = session.query(List).filter(List.service_id == service_id).all()
    return list(
        map(
            lambda l: {
                "id": str(l.id),
                "language": l.language,
                "name": l.name,
                "service": l.service_id,
            },
            lists,
        )
    )


@app.post("/list")
async def create_list(list_payload: ListPayload, response: Response):
    session = db_session()

    try:
        list = List(
            name=list_payload.name,
            language=list_payload.language,
            service_id=list_payload.service_id,
            subscribe_email_template_id=list_payload.subscribe_email_template_id,
            unsubscribe_email_template_id=list_payload.unsubscribe_email_template_id,
            subscribe_phone_template_id=list_payload.subscribe_phone_template_id,
            unsubscribe_phone_template_id=list_payload.unsubscribe_phone_template_id,
        )
        session.add(list)
        session.commit()
        return {"id": list.id}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": f"error saving list: {err}"}


@app.delete("/list/{list_id}")
async def delete_list(list_id, response: Response):
    session = db_session()
    try:
        list = session.query(List).get(list_id)
    except SQLAlchemyError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "list id is not valid"}

    if list is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}

    try:
        session.delete(list)
        session.commit()
        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error deleting list"}


class SubscriptionEvent(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    list_id: str


@app.post("/subscription")
async def create_subscription(list_payload: SubscriptionEvent, response: Response):
    session = db_session()
    notifications_client = get_notify_client()
    try:
        list = session.query(List).get(list_payload.list_id)
    except SQLAlchemyError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "list id is not valid"}

    if list is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}

    if list_payload.email is None and list_payload.phone is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "email and phone can not be empty"}

    try:
        subscription = Subscription(
            email=list_payload.email,
            phone=list_payload.phone,
            list=list,
        )
        session.add(subscription)
        session.commit()

        if list_payload.email is not None:
            notifications_client.send_email_notification(
                email_address=list_payload.email,
                template_id=list.subscribe_email_template_id,
            )

        if list_payload.phone is not None:
            notifications_client.send_sms_notification(
                phone_number=list_payload.phone,
                template_id=list.subscribe_phone_template_id,
            )

        return {"id": subscription.id}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error saving subscription"}


@app.get("/subscription/{subscription_id}")
async def confirm(subscription_id, response: Response):
    session = db_session()
    try:
        subscription = session.query(Subscription).get(subscription_id)
    except SQLAlchemyError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "subscription id is not valid"}

    if subscription is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "subscription not found"}

    try:
        subscription.confirmed = True
        session.commit()
        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error confirming subscription"}


@app.delete("/subscription/{unsubscription_id}")
async def unsubscribe(unsubscription_id, response: Response):
    session = db_session()
    notifications_client = get_notify_client()
    try:
        subscription = session.query(Subscription).get(unsubscription_id)
    except SQLAlchemyError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "subscription id is not valid"}

    if subscription is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "subscription not found"}

    list = session.query(List).get(subscription.list_id)

    try:
        email = subscription.email
        phone = subscription.phone
        session.delete(subscription)
        session.commit()

        if email is not None:
            notifications_client.send_email_notification(
                email_address=email,
                template_id=list.unsubscribe_email_template_id,
            )

        if phone is not None:
            notifications_client.send_sms_notification(
                phone_number=phone,
                template_id=list.unsubscribe_phone_template_id,
            )

        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error deleting subscription"}


def get_notify_client():
    return NotificationsAPIClient(
        NOTIFY_KEY, base_url="https://api.notification.canada.ca"
    )
