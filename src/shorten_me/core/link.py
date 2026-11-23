from typing import Tuple, Dict, Union
from urllib.parse import urlparse

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
        # Extremely fragile testing of via
        if not validate_url(long_url):
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


def validate_url(src_url: str) -> bool:
    """
    Given a url check for potential validity.

    Parameters
    ----------
    src_url
        A url as a string to validate

    Returns
    -------
    True if the given url is potentially valid
    """
    url = urlparse(src_url)
    return bool(url.hostname)
