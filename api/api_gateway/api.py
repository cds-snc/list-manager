from os import environ
from fastapi import Depends, FastAPI, HTTPException, Response, Request, status
from fastapi.responses import RedirectResponse
from clients.notify import NotificationsAPIClient
from requests import HTTPError
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.sql.expression import func, cast
from sqlalchemy.orm import Session
from sqlalchemy import String
from database.db import db_session
from logger import log
from uuid import UUID

from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

from models.List import List
from models.Subscription import Subscription

from typing import Optional
from pydantic import (
    BaseModel,
    BaseSettings,
    EmailStr,
    HttpUrl,
    conlist,
    validator,
)

import logging


class Settings(BaseSettings):
    openapi_url: str = environ.get("OPENAPI_URL", "")


settings = Settings()
API_AUTH_TOKEN = environ.get("API_AUTH_TOKEN")
if API_AUTH_TOKEN is None or not API_AUTH_TOKEN:
    raise Exception("error API_AUTH_TOKEN is missing")

METRICS_EMAIL_TARGET = "email"
METRICS_SMS_TARGET = "sms"
NOTIFY_KEY = environ.get("NOTIFY_KEY")
REDIRECT_ALLOW_LIST = [
    "ircc.digital.canada.ca",
    "ircc.numerique.canada.ca",
    "articles.cdssandbox.xyz",
    "articles.alpha.canada.ca",
]
BASE_URL = environ.get("BASE_URL", "https://list-manager.alpha.canada.ca")

description = """
List Manager 📝 API helps you manage your lists of subscribers and easily utilize GC Notify to send messages
"""
app = FastAPI(
    title="List Manager",
    description=description,
    version="0.0.1",
    openapi_url=settings.openapi_url,
)
metrics = Metrics(namespace="ListManager", service="api")


# Dependency
def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()


def verify_token(req: Request):
    token = req.headers.get("Authorization", None)
    if token != API_AUTH_TOKEN:
        metrics.add_metric(
            name="IncorrectAuthorizationToken", unit=MetricUnit.Count, value=1
        )
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


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


class ListCreatePayload(BaseModel):
    name: str
    language: str
    service_id: str
    subscribe_email_template_id: Optional[UUID] = None
    unsubscribe_email_template_id: Optional[UUID] = None
    subscribe_phone_template_id: Optional[UUID] = None
    unsubscribe_phone_template_id: Optional[UUID] = None
    subscribe_redirect_url: Optional[HttpUrl] = None
    confirm_redirect_url: Optional[HttpUrl] = None
    unsubscribe_redirect_url: Optional[HttpUrl] = None

    @validator(
        "subscribe_redirect_url",
        "confirm_redirect_url",
        "unsubscribe_redirect_url",
        allow_reuse=True,
    )
    def redirect_url_in_allow_list(cls, v):
        if v.host not in REDIRECT_ALLOW_LIST:
            raise ValueError("domain must be in REDIRECT_ALLOW_LIST")
        return v

    class Config:
        extra = "forbid"


class ListUpdatePayload(ListCreatePayload):
    name: Optional[str] = None
    language: Optional[str] = None
    service_id: Optional[str] = None


class ListGetPayload(ListCreatePayload):
    id: str
    count_1: str

    class Config:
        extra = "forbid"


@app.get("/lists")
def lists(session: Session = Depends(get_db)) -> list[ListGetPayload]:
    lists = (
        session.query(
            List.id.label("id"),
            List.name.label("name"),
            List.language.label("language"),
            List.service_id.label("service_id"),
            List.active.label("active"),
            List.subscribe_email_template_id.label("subscribe_email_template_id"),
            List.unsubscribe_email_template_id.label("unsubscribe_email_template_id"),
            List.subscribe_phone_template_id.label("subscribe_phone_template_id"),
            List.unsubscribe_phone_template_id.label("unsubscribe_phone_template_id"),
            List.subscribe_redirect_url.label("subscribe_redirect_url"),
            List.confirm_redirect_url.label("confirm_redirect_url"),
            List.unsubscribe_redirect_url.label("unsubscribe_redirect_url"),
            List.confirm_redirect_url.label("confirm_redirect_url"),
            func.count(Subscription.id).label("subscriber_count"),
        )
        .outerjoin(Subscription)
        .group_by(
            List.id,
            List.name,
            List.language,
            List.service_id,
            List.active,
            List.subscribe_email_template_id,
            List.unsubscribe_email_template_id,
            List.subscribe_phone_template_id,
            List.unsubscribe_phone_template_id,
            List.subscribe_redirect_url,
            List.unsubscribe_redirect_url,
            List.confirm_redirect_url,
        )
        .all()
    )

    return list(
        map(
            lambda l: {
                "id": str(l.id),
                "name": l.name,
                "language": l.language,
                "service_id": l.service_id,
                "active": l.active,
                "subscribe_email_template_id": l.subscribe_email_template_id,
                "unsubscribe_email_template_id": l.unsubscribe_email_template_id,
                "subscribe_phone_template_id": l.subscribe_phone_template_id,
                "subscribe_phone_template_id": l.subscribe_phone_template_id,
                "unsubscribe_phone_template_id": l.unsubscribe_phone_template_id,
                "subscribe_redirect_url": l.subscribe_redirect_url,
                "unsubscribe_redirect_url": l.unsubscribe_redirect_url,
                "confirm_redirect_url": l.confirm_redirect_url,
                "subscriber_count": l.subscriber_count,
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
                "service_id": l.service_id,
            },
            lists,
        )
    )


@app.get("/lists/{service_id}/subscriber-count/")
def get_list_counts(
    service_id,
    response: Response,
    unique: Optional[int] = 0,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
):
    lists = session.query(List.id).filter(List.service_id == service_id).all()

    list_ids = list(
        map(
            lambda l: str(l.id),
            lists,
        )
    )

    if unique:
        lists = (
            session.query(
                func.count(func.distinct(Subscription.email)), Subscription.list_id
            )
            .filter(
                Subscription.list_id.in_(list_ids),
                Subscription.confirmed.is_(True),
            )
            .group_by(Subscription.list_id)
            .all()
        )
    else:
        lists = (
            session.query(func.count(Subscription.email), Subscription.list_id)
            .filter(
                Subscription.list_id.in_(list_ids),
                Subscription.confirmed.is_(True),
            )
            .group_by(Subscription.list_id)
            .all()
        )

    return list(
        map(
            lambda l: {
                "list_id": l[1],
                "subscriber_count": l[0],
            },
            lists,
        )
    )


@app.post("/list")
def create_list(
    list_create_payload: ListCreatePayload,
    response: Response,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
):

    try:
        list = List(
            name=list_create_payload.name,
            language=list_create_payload.language,
            service_id=list_create_payload.service_id,
            subscribe_email_template_id=str(
                list_create_payload.subscribe_email_template_id
            ),
            unsubscribe_email_template_id=str(
                list_create_payload.unsubscribe_email_template_id
            ),
            subscribe_phone_template_id=str(
                list_create_payload.subscribe_phone_template_id
            ),
            unsubscribe_phone_template_id=str(
                list_create_payload.unsubscribe_phone_template_id
            ),
            subscribe_redirect_url=str(list_create_payload.subscribe_redirect_url),
            confirm_redirect_url=str(list_create_payload.confirm_redirect_url),
            unsubscribe_redirect_url=str(list_create_payload.unsubscribe_redirect_url),
        )
        session.add(list)
        session.commit()

        metrics.add_metric(name="ListCreated", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list.id))
        return {"id": list.id}
    except SQLAlchemyError as err:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        metrics.add_metric(name="ListCreateError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=list_create_payload.name)
        return {"error": f"error saving list: {err}"}


@app.put("/list/{list_id}")
def update_list(
    list_id,
    list_update_payload: ListUpdatePayload,
    response: Response,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
):
    try:
        list = session.query(List).get(list_id)
        if list is None:
            raise NoResultFound
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}

    try:

        session.query(List).filter(List.id == list.id).update(
            list_update_payload.dict(exclude_unset=True)
        )

        session.commit()
        metrics.add_metric(name="ListUpdated", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list_id))
        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        metrics.add_metric(name="ListUpdateError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list_id))
        return {"error": "error updating list"}


@app.delete("/list/{list_id}")
def delete_list(
    list_id,
    response: Response,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
):
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
        metrics.add_metric(name="ListDeleteError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list_id))

        return {"error": "error deleting list"}


@app.put("/list/{list_id}/reset")
def reset_list(
    list_id,
    response: Response,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
):
    try:
        list = session.query(List).get(list_id)
        if list is None:
            raise NoResultFound
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}

    try:
        session.query(Subscription).filter(Subscription.list_id == list_id).delete()
        session.commit()
    except SQLAlchemyError:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error resetting list"}

    return {"status": "OK"}


class SubscriptionEvent(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    list_id: str
    service_api_key: Optional[str]

    class Config:
        extra = "forbid"


@app.post("/subscription")
def create_subscription(
    subscription_payload: SubscriptionEvent,
    response: Response,
    session: Session = Depends(get_db),
):
    if subscription_payload.service_api_key:
        notifications_client = get_notify_client(subscription_payload.service_api_key)
    else:
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
            confirm_link = get_confirm_link(str(subscription.id))

            notifications_client.send_email_notification(
                email_address=subscription_payload.email,
                template_id=list.subscribe_email_template_id,
                personalisation={
                    "name": list.name,
                    "confirm_link": confirm_link,
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
                    "name": list.name,
                },
            )
            metrics.add_metric(
                name="SuccessfulSubscription", unit=MetricUnit.Count, value=1
            )
            metrics.add_metadata(key="list_id", value=str(list.id))
            metrics.add_metadata(key="language", value=list.language)
            metrics.add_metadata(key="target", value=METRICS_SMS_TARGET)

        if list.subscribe_redirect_url is not None:
            return RedirectResponse(list.subscribe_redirect_url)
        else:
            return {"id": subscription.id}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        metrics.add_metric(name="SubscriptionSaveError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(subscription_payload.list_id))

        return {"error": "error saving subscription"}
    except HTTPError as err:
        log.error(err)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        metrics.add_metric(
            name="SubscriptionNotificationError", unit=MetricUnit.Count, value=1
        )
        metrics.add_metadata(key="list_id", value=str(subscription_payload.list_id))

        return {"error": "error sending subscription notification"}


@app.get("/subscription/{subscription_id}/confirm")
def confirm_subscription(
    subscription_id, response: Response, session: Session = Depends(get_db)
):
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

        if subscription.list.confirm_redirect_url is not None:
            return RedirectResponse(subscription.list.confirm_redirect_url)
        else:
            return {"status": "OK"}

    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        metrics.add_metric(name="ConfirmationError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="subscription_id", value=str(subscription_id))
        return {"error": "error confirming subscription"}


@app.delete("/subscription/{subscription_id}")
@app.get("/unsubscribe/{subscription_id}")
def unsubscribe(
    subscription_id, response: Response, session: Session = Depends(get_db)
):
    notifications_client = get_notify_client()

    try:
        subscription = session.query(Subscription).get(subscription_id)
        if subscription is None:
            raise NoResultFound
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "subscription not found"}

    try:
        list = session.query(List).get(subscription.list_id)

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
        metrics.add_metadata(key="subscription_id", value=str(subscription_id))

        if list.unsubscribe_redirect_url is not None:
            return RedirectResponse(list.unsubscribe_redirect_url)
        else:
            return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        metrics.add_metric(name="UnsubscriptionError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="subscription_id", value=str(subscription_id))

        return {"error": "error deleting subscription"}
    except HTTPError as err:
        log.error(err)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        metrics.add_metric(
            name="UnsubscriptionNotificationError", unit=MetricUnit.Count, value=1
        )
        metrics.add_metadata(key="subscription_id", value=str(subscription_id))

        return {"error": "error sending unsubscription notification"}


class SendPayload(BaseModel):
    list_id: UUID
    template_id: UUID
    template_type: str
    service_api_key: Optional[str]
    job_name: Optional[str] = "Bulk email"
    unique: Optional[bool] = True

    @validator("template_type", allow_reuse=True)
    def template_type_email_or_phone(cls, v):
        if v.lower() not in ["email", "phone"]:
            raise ValueError("must be either email or phone")
        return v

    class Config:
        extra = "forbid"


@app.post("/send")
def send(
    send_payload: SendPayload,
    response: Response,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
):
    try:
        template_type = send_payload.template_type
        cols = [getattr(Subscription, template_type)]
        if send_payload.unique:
            cols.append(func.max(cast(Subscription.id, String)).label("id"))
        else:
            cols.append(Subscription.id)

        q = session.query(*cols)

        if send_payload.unique:
            q = q.group_by(template_type)

        q = q.filter(
            Subscription.list_id == send_payload.list_id,
            Subscription.confirmed.is_(True),
        )

        subscription_count = q.count()

        if subscription_count == 0:
            raise NoResultFound

        rs = q.all()
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list with confirmed subscribers not found"}

    try:
        sent_notifications = send_bulk_notify(subscription_count, send_payload, rs)

    except HTTPError as err:
        log.error(err)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        metrics.add_metric(name="BulkNotificationError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="subscription_count", value=str(subscription_count))

        return {"error": "error sending bulk notifications"}

    return {"status": "OK", "sent": sent_notifications}


def send_bulk_notify(subscription_count, send_payload, rows, recipient_limit=50000):
    notify_bulk_subscribers = []
    subscription_rows = []

    template_type = send_payload.template_type.lower()
    # Split notifications into separate calls based on limit
    for i, row in enumerate(rows):
        if i > 0 and (i % recipient_limit == 0):
            notify_bulk_subscribers.append(subscription_rows)

        if i % recipient_limit == 0:
            # Reset and add headers
            subscription_rows = []
            if template_type == "email":
                subscription_rows.append(["email address", "subscription id"])
            elif template_type == "phone":
                subscription_rows.append(["phone number", "subscription id"])

        if row[template_type]:
            subscription_rows.append([row[template_type], str(row["id"])])

        if i == subscription_count - 1:
            notify_bulk_subscribers.append(subscription_rows)

    notifications_client = get_notify_client(send_payload.service_api_key)

    count_sent = 0
    for subscribers in notify_bulk_subscribers:
        notifications_client.send_bulk_notifications(
            send_payload.job_name, subscribers, str(send_payload.template_id)
        )
        count_sent += len(subscribers) - 1

    return count_sent


def get_notify_client(api_key=NOTIFY_KEY):
    return NotificationsAPIClient(
        api_key, base_url="https://api.notification.canada.ca"
    )


def get_confirm_link(subscription_id):
    return f"{BASE_URL}/subscription/{subscription_id}/confirm"


def get_unsubscribe_link(subscription_id):
    return f"{BASE_URL}/unsubscribe/{subscription_id}"


class ListImportPayload(BaseModel):
    list_id: UUID
    emails: conlist(EmailStr, min_items=1, max_items=10000)

    class Config:
        extra = "forbid"


@app.post("/listimport")
def email_list_import(
    list_import_payload: ListImportPayload,
    response: Response,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
):
    """Imports a list"""
    try:
        _ = session.query(List).filter(List.id == list_import_payload.list_id).one()
        session.add_all(
            [
                Subscription(
                    email=email, confirmed=True, list_id=list_import_payload.list_id
                )
                for email in list_import_payload.emails
            ]
        )
        session.commit()
    except NoResultFound:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}
    except SQLAlchemyError as error:
        metrics.add_metric(name="ListEmailImportError", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list_import_payload.list_id))
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": f"error importing list: {error}"}
    else:
        return {"status": "OK"}
