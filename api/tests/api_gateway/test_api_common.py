# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from importlib import reload
import os
from unittest.mock import patch
import uuid
from api_gateway import api
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError


def test_version_with_no_GIT_SHA(client):
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "unknown"}


@patch.dict(os.environ, {"GIT_SHA": "foo"}, clear=True)
def test_version_with_GIT_SHA(client):
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "foo"}


@patch("api_gateway.api.get_db_version")
def test_healthcheck_success(mock_get_db_version, client):
    mock_get_db_version.return_value = "foo"
    response = client.get("/healthcheck")
    assert response.status_code == 200
    expected_val = {"database": {"able_to_connect": True, "db_version": "foo"}}
    assert response.json() == expected_val


@patch("api_gateway.api.get_db_version")
@patch("api_gateway.api.log")
def test_healthcheck_failure(mock_log, mock_get_db_version, client):
    mock_get_db_version.side_effect = SQLAlchemyError()
    response = client.get("/healthcheck")
    assert response.status_code == 200
    expected_val = {"database": {"able_to_connect": False}}
    assert response.json() == expected_val
    # assert mock_log.error.assert_called_once_with(SQLAlchemyError())


@patch.dict(
    os.environ, {"OPENAPI_URL": "", "API_AUTH_TOKEN": str(uuid.uuid4())}, clear=True
)
def test_api_docs_disabled_via_environ():
    reload(api)

    my_client = TestClient(api.app)
    response = my_client.get("/docs")
    assert response.status_code == 404

    response = my_client.get("/redoc")
    assert response.status_code == 404

    response = my_client.get("/openapi.json")
    assert response.status_code == 404


@patch.dict(
    os.environ,
    {"OPENAPI_URL": "/openapi.json", "API_AUTH_TOKEN": str(uuid.uuid4())},
    clear=True,
)
def test_api_docs_enabled_via_environ():
    reload(api)

    my_client = TestClient(api.app)
    response = my_client.get("/docs")
    assert response.status_code == 200

    response = my_client.get("/redoc")
    assert response.status_code == 200

    response = my_client.get("/openapi.json")
    assert response.status_code == 200


@patch.dict(os.environ, clear=True)
@pytest.mark.xfail(raises=Exception)
def test_api_auth_token_not_set():

    reload(api)
