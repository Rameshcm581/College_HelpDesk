# backend/Services/HelpdeskService/configs/dev_config.py
from configs.base_config import BaseConfig


class DevConfig(BaseConfig):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
