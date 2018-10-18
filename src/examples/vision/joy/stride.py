import json
import requests
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

import stride_config

# https://github.com/enricobacis/limit
import functools as _functools
import threading as _threading


def limit(limit, every=1):
    """This decorator factory creates a decorator that can be applied to
       functions in order to limit the rate the function can be invoked.
       The rate is `limit` over `every`, where limit is the number of
       invocation allowed every `every` seconds.
       limit(4, 60) creates a decorator that limit the function calls
       to 4 per minute. If not specified, every defaults to 1 second."""

    def limitdecorator(fn):
        """This is the actual decorator that performs the rate-limiting."""
        semaphore = _threading.Semaphore(limit)

        @_functools.wraps(fn)
        def wrapper(*args, **kwargs):
            semaphore.acquire()

            try:
                return fn(*args, **kwargs)

            finally:  # ensure semaphore release
                timer = _threading.Timer(every, semaphore.release)
                timer.setDaemon(True)  # allows the timer to be canceled on exit
                timer.start()

        return wrapper

    return limitdecorator


class Stride:
    def __init__(self, token=stride_config.token, cloud_id=stride_config.cloud_id, conversation_id=stride_config.conversation_id,host=stride_config.host):
        self.default_token = token
        self.default_cloud_id = cloud_id
        self.default_conversation_id = conversation_id
        self.host = host

    @limit(1, 5)  # limit 1 call every 5 seconds
    def send_file(self, filepath, msg=None, token=None, cloud_id=None, conversation_id=None):
        """ Send file to a HipChat room via API version 2
        Parameters
        ----------
        token : str
            HipChat API version 2 compatible token - must be token for active user
        room: str
            Name or API ID of the room to notify
        filepath: str
            Full path of file to be sent
        host: str, optional
            Host to connect to, defaults to api.hipchat.com
        """
        if token is None:
            token = self.default_token
        if cloud_id is None:
            cloud_id = self.default_cloud_id
        if conversation_id is None:
            conversation_id = self.default_conversation_id
        if not os.path.isfile(filepath):
            raise ValueError("File '{0}' does not exist".format(filepath))

        url = "https://{0}/site/{1}/conversation/{2}/media".format(self.host, cloud_id, conversation_id)
        headers = {
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/octet-stream',
        }
        with open(filepath, 'rb') as fin:
            body = fin.read()
        try:
            r = requests.post(url, data=body, headers=headers)
            return r
        except requests.RequestException as e:
            print("Send file error:", e)
            return None

    @limit(1, 5)  # limit 1 call every 5 seconds
    def notify(self, msg, color=None, token=None, cloud_id=None, conversation_id=None, data=None):
        if data is not None:
            with open('hchat_notify_data.json', 'w') as f:
                json.dump(data, f)
        if token is None:
            token = self.default_token
        if cloud_id is None:
            cloud_id = self.default_cloud_id
        if conversation_id is None:
            conversation_id = self.default_conversation_id
        url = "https://{0}/site/{1}/conversation/{2}/message".format(self.host, cloud_id, conversation_id)
        headers = {'Authorization': "Bearer " + token}
        payload = {
            "body" : {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": msg,
                            }
                        ]
                    }
                ]
            },
        }
        try:
            print("Sending request to {0} with payload {1}".format(url, payload))
            r = requests.post(url, json=payload, headers=headers)
            return r
        except requests.RequestException as e:
            print("Notify error:", e)
            return None
