from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def init_db(app):
    url = app.config.get("DATABASE_URL")
    if not url or make_url(url).drivername != "postgresql+psycopg":
        raise RuntimeError("DATABASE_URL must use postgresql+psycopg")
    engine = create_engine(
        url, pool_pre_ping=True, hide_parameters=True, connect_args={"connect_timeout": 5}
    )
    app.extensions["db_engine"] = engine
    app.extensions["db_session_factory"] = sessionmaker(bind=engine)

    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()


def get_db():
    if "db" not in g:
        g.db = current_app.extensions["db_session_factory"]()
    return g.db
