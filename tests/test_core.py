import unittest

from shorten_me.app import app as test_app
from shorten_me.config import TestConfig
from shorten_me.core.shorten import embiggen, shorten
from shorten_me.db import db


class LinkTest(unittest.TestCase):
    def setUp(self) -> None:
        app = test_app
        app.config.from_object(TestConfig)
        db.init_app(app)
        self.client = app.test_client()
        self._fill_db()

    def tearDown(self) -> None:
        db.session.remove()

    def _fill_db(self):
        self.client.post("/", data={"long_url": "http://google.com"})
        self.client.post("/", data={"long_url": "http://nextmatter.com"})

    def test_add_valid_link(self):
        result = self.client.post("/", data={"long_url": "http://yahoo.com"})
        self.assertEqual(200, result.status_code)
        self.assertEqual("v", result.json["short_url"])

    def test_add_invalid_link(self):
        result = self.client.post("/", data={"long_url": "http://"})
        self.assertEqual(404, result.status_code)

    def test_get_via_short_url(self):
        result = self.client.get("/p")
        self.assertEqual(200, result.status_code)
        self.assertEqual("http://google.com", result.json["long_url"])

    def test_error_via_short_url(self):
        result = self.client.get("/mwring")
        self.assertEqual(404, result.status_code)

        result = self.client.get("/Oo0")  # invalid chars
        self.assertEqual(404, result.status_code)


class ShortenTest(unittest.TestCase):

    def test_shorten(self):
        self.assertEqual("p", shorten(1))
        self.assertEqual("vcTJ", shorten(598463))

    def test_embiggen(self):
        self.assertEqual(1, embiggen("p"))
        self.assertEqual(598463, embiggen("vcTJ"))
