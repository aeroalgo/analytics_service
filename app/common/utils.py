import bleach

def method_cache_key(cache_prefix="cache", method="unknown", **kwargs):
    # не использовать inspect.stack()[1][3] – это очень медленно!
    sign_string = [cache_prefix, method]
    for k, v in dict(kwargs).items():
        sign_string.append("%s__%s" % (k, v))
    return "@".join(sign_string)


def clean_html(html):
    result = html.replace("<br>", "\n")
    result = result.replace("<div>", "<div>\n")
    result = result.replace("</li>", "</div>\n")
    result = result.replace("</div>", "</div>\n")
    result = bleach.clean(result, strip=True, tags=[])
    result = result.replace("&lt;", "<")
    result = result.replace("&gt;", ">")
    result = result.replace("&nbsp;", " ")
    result = result.replace("\n\n", "\n")
    result = result.strip()
    return result
