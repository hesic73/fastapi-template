from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from urllib.parse import urlencode
import json

templates = Jinja2Templates(directory="templates")


templates.env.globals['min'] = min
templates.env.globals['max'] = max


def url_for_with_query_params(request: Request, name: str, path_params: dict, query_params: dict):
    url = request.url_for(name, **path_params)
    query_string = urlencode(query_params)
    return f"{url}?{query_string}"


templates.env.globals['url_for_with_query_params'] = url_for_with_query_params


def to_json_string(data: dict):
    return json.dumps(data)


templates.env.globals['to_json_string'] = to_json_string


def merge_dicts(d: dict, *args: dict):
    merged_dict = d.copy()
    for arg in args:
        merged_dict.update(arg)
    return merged_dict


templates.env.globals['merge_dicts'] = merge_dicts
