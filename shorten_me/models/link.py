from datetime import datetime
from typing import Dict, Union

from shorten_me.db import db


class LinkModel(db.Model):
    __tablename__ = "links"

    id = db.Column(db.Integer, primary_key=True)
    long_url = db.Column(db.String(255), index=True)
    hits = db.Column(db.Integer, default=0)
    added = db.Column(db.Date, default=datetime.now())

    # Had intended to include but thought it might be overkill =)
    # is_custom = db.Column(db.Boolean, default=False)

    def __init__(self, long_url: str) -> None:
        self.long_url = long_url

    def json(self) -> Dict[str, Union[int, str]]:
        return {
            "id": self.id,
            "long_url": self.long_url,
            "hits": self.hits,
        }

    @classmethod
    def fetch_by_long_url(cls, long_url: str):
        return cls.query.filter_by(long_url=long_url).first()

    @classmethod
    def fetch_by_id(cls, link_id: int):
        return cls.query.filter_by(id=link_id).first()

    def hit(self) -> None:
        """
        Increment visits every time the URL is accessed. May be used for
        rudimentary stats.
        """
        self.hits += 1

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()
