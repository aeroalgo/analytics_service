def method_cache_key(cache_prefix="cache", method="unknown", **kwargs):
    # не использовать inspect.stack()[1][3] – это очень медленно!
    sign_string = [cache_prefix, method]
    for k, v in dict(kwargs).items():
        sign_string.append("%s__%s" % (k, v))
    return "@".join(sign_string)
