import logging


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("my_first_bot")
    logger.setLevel(log_level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
    return logger
