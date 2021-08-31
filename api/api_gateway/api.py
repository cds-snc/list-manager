from os import environ
from fastapi import Depends, FastAPI, Response, status
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.orm import Session
from database.db import db_session
from logger import log
from uuid import UUID

from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

from models.List import List
from models.Subscription import Subscription

from typing import Optional
from pydantic import BaseModel, EmailStr
from notifications_python_client.notifications import NotificationsAPIClient


NOTIFY_KEY = environ.get("NOTIFY_KEY")
METRICS_EMAIL_TARGET = "email"
METRICS_SMS_TARGET = "sms"

app = FastAPI(root_path="/v1")
metrics = Metrics(namespace="ListManager", service="api")


# Dependency
def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()


@app.get("/version")
def version():
    return {"version": environ.get("GIT_SHA", "unknown")}


def get_db_version(session):

    query = "SELECT version_num FROM alembic_version"
    full_name = session.execute(query).fetchone()[0]
    return full_name


@app.get("/healthcheck")
def healthcheck(session: Session = Depends(get_db)):
    try:
        full_name = get_db_version(session)
        db_status = {"able_to_connect": True, "db_version": full_name}
    except SQLAlchemyError as err:
        log.error(err)
        db_status = {"able_to_connect": False}

    return {"database": db_status}


class ListPayload(BaseModel):
    name: str
    language: str
    service_id: str
    subscribe_email_template_id: Optional[UUID] = None
    unsubscribe_email_template_id: Optional[UUID] = None
    subscribe_phone_template_id: Optional[UUID] = None
    unsubscribe_phone_template_id: Optional[UUID] = None

    class Config:
        extra = "forbid"


@app.get("/lists")
def lists(session: Session = Depends(get_db)):
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
def lists_by_service(service_id, session: Session = Depends(get_db)):
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
def create_list(
    list_payload: ListPayload, response: Response, session: Session = Depends(get_db)
):

    try:
        list = List(
            name=list_payload.name,
            language=list_payload.language,
            service_id=list_payload.service_id,
            subscribe_email_template_id=str(list_payload.subscribe_email_template_id),
            unsubscribe_email_template_id=str(
                list_payload.unsubscribe_email_template_id
            ),
            subscribe_phone_template_id=str(list_payload.subscribe_phone_template_id),
            unsubscribe_phone_template_id=str(
                list_payload.unsubscribe_phone_template_id
            ),
        )
        session.add(list)
        session.commit()

        metrics.add_metric(name="ListCreated", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list.id))

        return {"id": list.id}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": f"error saving list: {err}"}


@app.delete("/list/{list_id}")
def delete_list(list_id, response: Response, session: Session = Depends(get_db)):
    try:
        list = session.query(List).get(list_id)
        if list is None:
            raise NoResultFound
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}

    try:
        session.delete(list)
        session.commit()
        metrics.add_metric(name="ListDeleted", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list_id))

        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error deleting list"}


class SubscriptionEvent(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    list_id: str

    class Config:
        extra = "forbid"


@app.post("/subscription")
def create_subscription(
    subscription_payload: SubscriptionEvent,
    response: Response,
    session: Session = Depends(get_db),
):
    notifications_client = get_notify_client()
    try:
        list = session.query(List).get(subscription_payload.list_id)
        if list is None:
            raise NoResultFound
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}

    if subscription_payload.email is None and subscription_payload.phone is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "email and phone can not be empty"}

    try:
        subscription = Subscription(
            email=subscription_payload.email,
            phone=subscription_payload.phone,
            list=list,
        )
        session.add(subscription)
        session.commit()
        if (
            subscription_payload.email is not None
            and len(list.subscribe_email_template_id) == 36
        ):
            notifications_client.send_email_notification(
                email_address=subscription_payload.email,
                template_id=list.subscribe_email_template_id,
                personalisation={
                    "email_address": subscription_payload.email,
                    "name": list.name,
                    "subscription_id": str(subscription.id),
                },
            )
            metrics.add_metric(
                name="SuccessfulSubscription", unit=MetricUnit.Count, value=1
            )
            metrics.add_metadata(key="list_id", value=str(subscription_payload.list_id))
            metrics.add_metadata(key="language", value=list.language)
            metrics.add_metadata(key="target", value=METRICS_EMAIL_TARGET)

        if (
            subscription_payload.phone is not None
            and len(list.subscribe_phone_template_id) == 36
        ):
            notifications_client.send_sms_notification(
                phone_number=subscription_payload.phone,
                template_id=list.subscribe_phone_template_id,
                personalisation={
                    "phone_number": subscription_payload.phone,
                    "name": list.name,
                },
            )
            metrics.add_metric(
                name="SuccessfulSubscription", unit=MetricUnit.Count, value=1
            )
            metrics.add_metadata(key="list_id", value=str(list.id))
            metrics.add_metadata(key="language", value=list.language)
            metrics.add_metadata(key="target", value=METRICS_SMS_TARGET)

        return {"id": subscription.id}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        metrics.add_metric(
            name="UnsuccessfulSubscription", unit=MetricUnit.Count, value=1
        )
        metrics.add_metadata(key="list_id", value=str(subscription_payload.list_id))

        return {"error": "error saving subscription"}


@app.get("/subscription/{subscription_id}")
def confirm(subscription_id, response: Response, session: Session = Depends(get_db)):
    try:
        subscription = session.query(Subscription).get(subscription_id)
        if subscription is None:
            raise NoResultFound

    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "subscription not found"}

    try:
        subscription.confirmed = True
        session.commit()

        metrics.add_metric(
            name="SuccessfulConfirmation", unit=MetricUnit.Count, value=1
        )
        metrics.add_metadata(key="subscription_id", value=str(subscription_id))

        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error confirming subscription"}


@app.delete("/subscription/{unsubscription_id}")
def unsubscribe(
    unsubscription_id, response: Response, session: Session = Depends(get_db)
):
    notifications_client = get_notify_client()

    try:
        subscription = session.query(Subscription).get(unsubscription_id)
        if subscription is None:
            raise NoResultFound
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "subscription not found"}

    list = session.query(List).get(subscription.list_id)

    try:
        email = subscription.email
        phone = subscription.phone
        session.delete(subscription)
        session.commit()

        if email is not None and len(list.unsubscribe_email_template_id) == 36:
            notifications_client.send_email_notification(
                email_address=email,
                template_id=list.unsubscribe_email_template_id,
                personalisation={"email_address": email, "name": list.name},
            )

        if phone is not None and len(list.unsubscribe_phone_template_id) == 36:
            notifications_client.send_sms_notification(
                phone_number=phone,
                template_id=list.unsubscribe_phone_template_id,
                personalisation={"phone_number": phone, "name": list.name},
            )

        metrics.add_metric(
            name="SuccessfulUnsubscription", unit=MetricUnit.Count, value=1
        )
        metrics.add_metadata(key="unsubscription_id", value=str(unsubscription_id))

        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error deleting subscription"}


def get_notify_client():
    return NotificationsAPIClient(
        NOTIFY_KEY, base_url="https://api.notification.canada.ca"
    )
