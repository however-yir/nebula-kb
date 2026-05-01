import logging

logger = logging.getLogger('nebula.llm')


class LLMFallbackManager:
    """Tries multiple LLM providers in order, falling back on failure."""

    def __init__(self, enabled=False):
        self.enabled = enabled

    def get_response(self, model_configs, invoke_fn, *args, **kwargs):
        if not self.enabled or not model_configs:
            return invoke_fn(model_configs[0] if model_configs else None, *args, **kwargs)

        last_error = None
        for config in model_configs:
            try:
                return invoke_fn(config, *args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning("LLM provider %s failed: %s, trying next", config.get('name', 'unknown'), e)
        raise last_error
