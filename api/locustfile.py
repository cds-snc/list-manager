from locust import HttpUser, task
import uuid
import json
from os import environ


class APIUser(HttpUser):
    @task
    def run_flow(self):
        list = {
            "name": str(str(uuid.uuid4())),
            "language": "en",
            "service_id": str(uuid.uuid4()),
        }
        response = self.client.post(
            "/list",
            data=json.dumps(list),
            headers={"Authorization": environ.get("API_AUTH_TOKEN")},
        )
        list = response.json()
        subscription = {
            "list_id": list["id"],
            "email": "success@simulator.amazonses.com",
        }
        response = self.client.post(
            "/subscription",
            data=json.dumps(subscription),
            headers={"Authorization": environ.get("API_AUTH_TOKEN")},
        )
        subscription = response.json()
        self.client.get(f"/subscription/{subscription['id']}")
        self.client.delete(f"/subscription/{subscription['id']}")
        self.client.delete(f"/list/{list['id']}")
