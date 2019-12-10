import urllib3
from typing import Tuple, Dict, Union

import requests
from flask_restful import Resource, reqparse

from shorten_me.core.shorten import embiggen, shorten
from shorten_me.models.link import LinkModel


class Link(Resource):
    """
    Base logic for adding full links
    """
    parser = reqparse.RequestParser()
    parser.add_argument(
        "long_url",
        type=str,
        required=True,
        help="URL to shorten"
    )

    def post(self) -> Tuple[Dict[str, Union[int, str]], int]:
        data = self.parser.parse_args()
        long_url = data["long_url"]
        try:
            # Very simple way to check if a given URL is valid
            # could be more robust
            res = requests.get(url=long_url)
            if not res.status_code == 200:
                raise requests.exceptions.RequestException
        except requests.exceptions.RequestException:
            return {"message": "URL given is invalid"}, 404
        link = LinkModel.fetch_by_long_url(long_url)
        if not link:
            link = LinkModel(long_url)
            link.save_to_db()

        return {"short_url": shorten(link.id)}, 200

    @classmethod
    def get(cls) -> Tuple[Dict[str, str], int]:
        return {"message": "Sorry! No UI as yet!"}, 500


class ShortLink(Resource):
    """
    Base logic for retrieving links via the shortened url
    """

    @classmethod
    def get(cls, short_url: str) -> Tuple[Dict[str, Union[int, str]], int]:
        link_id = embiggen(short_url)
        link = LinkModel.fetch_by_id(link_id)

        if link:
            link.hit()
            link.save_to_db()
            return link.json(), 200  # Should be a redirect but fine for purpose

        return {"message": "Short URL not found."}, 404

