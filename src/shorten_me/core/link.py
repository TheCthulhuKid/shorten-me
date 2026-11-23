from typing import Tuple, Dict, Union

from flask_restful import Resource, reqparse

from shorten_me.codec import InvalidShortCode, decode, encode
from shorten_me.models.link import LinkModel
from shorten_me.urls import InvalidUrl, validate_long_url


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
            validate_long_url(long_url)
        except InvalidUrl:
            return {"message": "URL given is invalid"}, 404
        link = LinkModel.fetch_by_long_url(long_url)
        if not link:
            link = LinkModel(long_url)
            link.save_to_db()

        return {"short_url": encode(link.id)}, 200

    @classmethod
    def get(cls) -> Tuple[Dict[str, str], int]:
        return {"message": "Sorry! No UI as yet!"}, 500


class ShortLink(Resource):
    """
    Base logic for retrieving links via the shortened url
    """

    @classmethod
    def get(cls, short_url: str) -> Tuple[Dict[str, Union[int, str]], int]:
        try:
            link = LinkModel.fetch_by_id(decode(short_url))
        except InvalidShortCode:
            link = None

        if link:
            link.hit()
            link.save_to_db()
            return link.json(), 200  # Should be a redirect but fine for purpose

        return {"message": "Short URL not found."}, 404

