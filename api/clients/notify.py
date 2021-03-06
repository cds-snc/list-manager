from notifications_python_client.notifications import (
    NotificationsAPIClient as BaseNotify,
)


class NotificationsAPIClient(BaseNotify):
    def send_bulk_notifications(
        self,
        job_name,
        subscriptions,
        template_id,
        scheduled_for=None,
        email_reply_to_id=None,
    ):
        notification = {
            "name": job_name,
            "template_id": template_id,
            "rows": subscriptions,
        }

        if scheduled_for:
            notification.update({"scheduled_for": scheduled_for})
        if email_reply_to_id:
            notification.update({"reply_to_id": email_reply_to_id})
        return self.post("/v2/notifications/bulk", data=notification)

    def _perform_request(self, method, url, kwargs):
        kwargs["timeout"] = 30
        return super()._perform_request(method, url, kwargs)
