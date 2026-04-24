import os

if os.environ.get('SERVER_NAME', 'web') == 'local_model':
    from .model import *  # noqa: F401,F403
else:
    from .web import *  # noqa: F401,F403
