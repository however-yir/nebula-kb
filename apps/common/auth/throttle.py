from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonRateThrottleCustom(AnonRateThrottle):
    scope = 'anon'


class UserRateThrottleCustom(UserRateThrottle):
    scope = 'user'


class KnowledgeSearchThrottle(AnonRateThrottle):
    scope = 'knowledge_search'
