from .celery_base import CeleryBaseService

__all__ = ['CeleryModelService']


class CeleryModelService(CeleryBaseService):
    def __init__(self, **kwargs):
        kwargs['queue'] = 'model'
        super().__init__(**kwargs)
