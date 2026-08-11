import logging
from app.core.config import settings

def setup_logging():
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )
    # Note: Secure logging requires masking sensitive fields.
    # This will be implemented fully in subsequent phases using structural logging.
    logger = logging.getLogger("scanner_api")
    return logger

logger = setup_logging()
