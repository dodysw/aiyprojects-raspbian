import json
import requests
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

import hipchat_config

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


class HChat:
    def __init__(self, token=hipchat_config.token, room=hipchat_config.room, host=hipchat_config.host):
        self.default_token = token
        self.default_room = room
        self.host = host

    def send_file(self, filepath, msg=None, token=None, room=None):
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
        if room is None:
            room = self.default_room
        if not os.path.isfile(filepath):
            raise ValueError("File '{0}' does not exist".format(filepath))

        url = "https://{0}/v2/room/{1}/share/file".format(self.host, room)
        headers = {
            'Authorization': 'Bearer {}'.format(token),
            'Accept-Charset': 'UTF-8',
            'Content-Type': 'multipart/related',
        }
        raw_body = MIMEMultipart('related')
        with open(filepath, 'rb') as fin:
            try:
                img = MIMEImage(fin.read())
            except TypeError as ex:
                img = MIMEText(fin.read())
            img.add_header(
                'Content-Disposition',
                'attachment',
                name='file',
                filename=filepath.split('/')[-1]
            )
            raw_body.attach(img)
        if msg is not None:
            payload = MIMEText(json.dumps(dict(message=msg)))
            payload.add_header('Content-Type', 'application/json')
            raw_body.attach(payload)
        raw_headers, body = raw_body.as_string().split('\n\n', 1)
        boundary = re.search('boundary="([^"]*)"', raw_headers).group(1)
        headers['Content-Type'] = 'multipart/related; boundary="{}"'.format(boundary)
        try:
            r = requests.post(url, data=body, headers=headers)
            return r
        except requests.RequestException as e:
            print("Send file error:", e)
            return None

    @limit(1, 5)  # limit 1 call every 5 seconds
    def notify(self, msg, color=None, token=None, room=None, data=None):
        if data is not None:
            with open('hchat_notify_data.json', 'w') as f:
                json.dump(data, f)
        if token is None:
            token = self.default_token
        if room is None:
            room = self.default_room
        url = "https://{0}/v2/room/{1}/notification?".format(self.host, room)
        headers = {'Authorization': "Bearer " + token}
        payload = {
            "color": color,
            "message": msg,
            "notify": True,
            "message_format": "text"
        }
        try:
            r = requests.post(url, data=payload, headers=headers)
            return r
        except requests.RequestException as e:
            print("Notify error:", e)
            return None
