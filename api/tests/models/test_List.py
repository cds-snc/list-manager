import pytest

from sqlalchemy.exc import IntegrityError

from models.List import List


def test_list_model():
    list = List(
        name="name",
        language="language",
        service_id="service_id",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )
    assert list.name == "name"
    assert list.language == "language"
    assert list.subscribe_email_template_id == "subscribe_email_template_id"
    assert list.unsubscribe_email_template_id == "unsubscribe_email_template_id"
    assert list.subscribe_phone_template_id == "subscribe_phone_template_id"
    assert list.unsubscribe_phone_template_id == "unsubscribe_phone_template_id"


def test_list_model_saved(assert_new_model_saved, session):
    list = List(
        name="name",
        language="language",
        service_id="service_id",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )
    session.add(list)
    session.commit()
    assert list.name == "name"
    assert_new_model_saved(list)
    session.delete(list)
    session.commit()


def test_list_model_downcases_language(session):
    list = List(
        name="name",
        language="LANGUAGE",
        service_id="service_id",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )
    session.add(list)
    session.commit()
    assert list.language == "language"
    session.delete(list)
    session.commit()


def test_list_empty_name_fails(session):
    list = List(
        language="language",
        service_id="service_id",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )
    session.add(list)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_list_empty_language_fails(session):
    list = List(
        name="name",
        service_id="service_id",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )
    session.add(list)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_list_empty_service_id_fails(session):
    list = List(
        name="name",
        language="language",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )
    session.add(list)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_list_duplicate_name_fails(assert_new_model_saved, session):
    list = List(
        name="name",
        language="language",
        service_id="service_id",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )

    session.add(list)
    session.commit()

    assert list.name == "name"
    assert_new_model_saved(list)

    list_two = List(
        name="name",
        language="language",
        service_id="service_id",
        subscribe_email_template_id="subscribe_email_template_id",
        unsubscribe_email_template_id="unsubscribe_email_template_id",
        subscribe_phone_template_id="subscribe_phone_template_id",
        unsubscribe_phone_template_id="unsubscribe_phone_template_id",
    )

    session.add(list_two)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    session.delete(list)
    session.commit()
