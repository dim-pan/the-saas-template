import logging
import os
import sys


def configure_engine_logging() -> None:
    """Ensure ``engine.*`` loggers emit under Uvicorn.

    Uvicorn applies ``logging.config.dictConfig`` before the app module finishes loading,
    after which ``logging.basicConfig`` is often a no-op and the root logger may stay at
    WARNING — so INFO logs from ``engine.gateway`` / ``engine.shared`` disappear.
    Attach a handler directly to the ``engine`` logger instead.
    """
    level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    level = logging.getLevelNamesMapping().get(level_name, logging.INFO)

    eng = logging.getLogger('engine')
    eng.setLevel(level)
    if eng.handlers:
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    eng.addHandler(handler)
    eng.propagate = False
