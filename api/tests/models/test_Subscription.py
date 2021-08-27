from models.Subscription import Subscription


def test_subscription_belongs_to_a_list(list_fixture, session):
    subscription = Subscription(
        email="email",
        phone="phone",
        list=list_fixture,
    )
    session.add(subscription)
    session.commit()
    assert list_fixture.subscriptions[-1].id == subscription.id
    session.delete(subscription)
    session.commit()


def test_subscription_model(list_fixture):
    subscription = Subscription(
        email="email",
        phone="phone",
        confirmed=True,
        list=list_fixture,
    )
    assert subscription.email == "email"
    assert subscription.phone == "phone"
    assert subscription.confirmed is True


def test_subscription_model_saved(assert_new_model_saved, list_fixture, session):
    subscription = Subscription(
        email="email",
        phone="phone",
        list=list_fixture,
    )
    session.add(subscription)
    session.commit()
    assert subscription.email == "email"
    assert_new_model_saved(subscription)
    session.delete(subscription)
    session.commit()
