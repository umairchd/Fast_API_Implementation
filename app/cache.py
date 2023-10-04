from cachetools import TTLCache

response_cache = TTLCache(maxsize=1000, ttl=300)
