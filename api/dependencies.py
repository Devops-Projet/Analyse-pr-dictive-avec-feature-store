from functools import lru_cache

from sqlalchemy import Engine

from feature_store.db import get_engine as create_store_engine
from models.common.serving import ModelLoader


@lru_cache
def get_engine() -> Engine:
    return create_store_engine()


@lru_cache
def get_model_loader() -> ModelLoader:
    return ModelLoader()
