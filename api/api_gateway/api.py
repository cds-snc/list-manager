from os import environ
from fastapi import Depends, FastAPI, HTTPException, Response, Request, status
from fastapi.responses import RedirectResponse
from clients.notify import NotificationsAPIClient
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.orm import Session
from database.db import db_session
from logger import log
from uuid import UUID, uuid4

from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

from models.List import List
from models.Subscription import Subscription

from typing import Optional
from pydantic import BaseModel, EmailStr, HttpUrl, validator

API_AUTH_TOKEN = environ.get("API_AUTH_TOKEN", uuid4())
METRICS_EMAIL_TARGET = "email"
METRICS_SMS_TARGET = "sms"
NOTIFY_KEY = environ.get("NOTIFY_KEY")
REDIRECT_ALLOW_LIST = ["valid.canada.ca", "valid.gc.ca"]
BASE_URL = environ.get("BASE_URL", "https://list-manager.alpha.canada.ca")

app = FastAPI()
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


class ListPayload(BaseModel):
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
        "subscribe_redirect_url", "confirm_redirect_url", "unsubscribe_redirect_url"
    )
    def redirect_url_in_allow_list(cls, v):
        if v.host not in REDIRECT_ALLOW_LIST:
            raise ValueError("domain must be in REDIRECT_ALLOW_LIST")
        return v

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
    list_payload: ListPayload,
    response: Response,
    session: Session = Depends(get_db),
    _authorized: bool = Depends(verify_token),
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


@app.put("/list/{list_id}")
def update_list(
    list_id,
    list_payload: ListPayload,
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
            list_payload.dict(exclude_unset=True)
        )

        session.commit()
        metrics.add_metric(name="ListUpdated", unit=MetricUnit.Count, value=1)
        metrics.add_metadata(key="list_id", value=str(list_id))
        return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
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
            confirm_link = get_confirm_link(str(subscription.id))

            notifications_client.send_email_notification(
                email_address=subscription_payload.email,
                template_id=list.subscribe_email_template_id,
                personalisation={
                    "email_address": subscription_payload.email,
                    "name": list.name,
                    "subscription_id": str(subscription.id),
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

        if list.subscribe_redirect_url is not None:
            return RedirectResponse(list.subscribe_redirect_url)
        else:
            return {"id": subscription.id}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        metrics.add_metric(
            name="UnsuccessfulSubscription", unit=MetricUnit.Count, value=1
        )
        metrics.add_metadata(key="list_id", value=str(subscription_payload.list_id))

        return {"error": "error saving subscription"}


@app.get("/subscription/{subscription_id}/confirm")
def confirm_subscription(subscription_id, response: Response, session: Session = Depends(get_db)):
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
        metrics.add_metadata(key="subscription_id", value=str(subscription_id))

        if list.unsubscribe_redirect_url is not None:
            return RedirectResponse(list.unsubscribe_redirect_url)
        else:
            return {"status": "OK"}
    except SQLAlchemyError as err:
        log.error(err)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "error deleting subscription"}


class SendPayload(BaseModel):
    list_id: UUID
    template_id: UUID
    template_type: str
    job_name: Optional[str] = "Bulk email"

    @validator("template_type")
    def template_type_email_or_phone(cls, v):
        if v.lower() not in ["email", "phone"]:
            raise ValueError("must be either email or phone")
        return v

    class Config:
        extra = "forbid"


@app.post("/send")
def send(
    send_payload: SendPayload, response: Response, session: Session = Depends(get_db)
):
    try:
        q = session.query(
            Subscription.email,
            Subscription.phone,
            Subscription.id,
        ).filter(
            Subscription.list_id == send_payload.list_id,
            Subscription.confirmed.is_(True),
        )
        subscription_count = q.count()

        if subscription_count == 0:
            raise NoResultFound

        rs = q.all()
    except SQLAlchemyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "list not found"}

    sent_notifications = send_bulk_notify(subscription_count, send_payload, rs)

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

    notifications_client = get_notify_client()

    count_sent = 0
    for subscribers in notify_bulk_subscribers:
        notifications_client.send_bulk_notifications(
            send_payload.job_name, subscribers, str(send_payload.template_id)
        )
        count_sent += len(subscribers) - 1

    return count_sent


def get_notify_client():
    return NotificationsAPIClient(
        NOTIFY_KEY, base_url="https://api.notification.canada.ca"
    )


def get_confirm_link(subscription_id):
    return f"{BASE_URL}/subscription/{subscription_id}/confirm"


def get_unsubscribe_link(subscription_id):
    return f"{BASE_URL}/unsubscribe/{subscription_id}"
