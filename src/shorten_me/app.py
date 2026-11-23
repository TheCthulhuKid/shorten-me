from flask import Flask
from flask_restful import Api

from shorten_me.config import DevConfig
from shorten_me.core.link import Link, ShortLink
from shorten_me.db import db

app = Flask(__name__)
app.config.from_object(DevConfig)
api = Api(app)


@app.before_first_request
def setup_db():
    db.create_all()


api.add_resource(Link, "/")
api.add_resource(ShortLink, "/<string:short_url>")


def main() -> None:
    db.init_app(app)
    app.run(port=5000, debug=True)


if __name__ == "__main__":
    main()
