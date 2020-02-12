import fastapi
import starlette.requests
import starlette.responses
from starlette.staticfiles import StaticFiles

import redis
import pickle
import pprint


class RedisManager():
    _redis = None
    page_size = 20
    host = 'localhost'
    port = 34379

    def set(self, host, port, page_size):
        self.page_size = int(page_size)
        self.host = host
        self.port = port
        self._redis = redis.Redis(host, port)

    def is_set(self):
        if self._redis is None:
            return False
        try:
            self._redis.keys()
            return True
        except Exception:
            return False

    def is_ok(self):
        try:
            self._redis.keys()
            return True
        except Exception:
            return False

    def get(self):
        return self._redis


app = fastapi.FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

redis_client = RedisManager()
PAGE_SIZE = 20

with open('index.html', 'r') as file:
    TEMPLATE = file.read()


@app.get('/')
def index():
    return starlette.responses.Response(
        content=default_content(),
        status_code=200,
    )


@app.get('/set')
def set_redis(host, port, page_size):
    try:
        redis_client.set(host, port, page_size)
    except Exception:
        pass

    return starlette.responses.Response(
        content=default_content(),
        status_code=200,
    )


@app.get('/data')
def data(
    selected_key,
    page,
):
    if not redis_client.is_set():
        return index()

    updated_content = TEMPLATE
    updated_content = update_redis_paramters(updated_content)

    updated_content = updated_content.replace('#SELECTED_PAGE#', page)
    updated_content = updated_content.replace('#MAX_PAGE#', get_max_page(selected_key))
    updated_content = updated_content.replace('#STATUS#', '<span class="badge badge-success">Connected</span>')

    updated_content = replace_redis_keys(updated_content, selected_key)
    updated_content = update_key_content(updated_content, selected_key, page)

    return starlette.responses.Response(
        content=updated_content,
        status_code=200,
    )


def default_content():
    updated_content = TEMPLATE

    updated_content = updated_content.replace('#SELECTED_PAGE#', '1')
    updated_content = updated_content.replace('#MAX_PAGE#', '10')
    updated_content = update_redis_paramters(updated_content)

    if redis_client and redis_client.is_ok():
        updated_content = updated_content.replace('#STATUS#', '<span class="badge badge-success">Connected</span>')
    else:
        updated_content = updated_content.replace('#STATUS#', '<span class="badge badge-secondary">Disconnected</span>')

    updated_content = replace_redis_keys(updated_content)
    updated_content = update_key_content(updated_content)

    return updated_content


def update_redis_paramters(template):
    updated_content = template
    updated_content = updated_content.replace('#HOST#', redis_client.host)
    updated_content = updated_content.replace('#PORT#', str(redis_client.port))
    updated_content = updated_content.replace('#PAGE_SIZE#', str(redis_client.page_size))

    return updated_content


def get_max_page(
    key,
):
    key_type = redis_client.get().type(key).decode("utf-8")

    if key_type == 'string':
        return '10'
    elif key_type == 'list':
        try:
            return str((redis_client.get().llen(key) / redis_client.page_size) + 1)
        except Exception:
            return '10'


def update_key_content(
    template,
    key=None,
    page=None,
):
    content = ''

    if key:
        key_type = redis_client.get().type(key).decode("utf-8")

        if key_type == 'string':
            value = redis_client.get().get(key).decode("utf-8")
            content += f'<h2 class="text-center">{key} - {value}</h2>'
        elif key_type == 'list':
            list_len = redis_client.get().llen(key)
            start_offset = (int(page) - 1) * redis_client.page_size
            end_offset = min(int(page) * redis_client.page_size, list_len)

            content += f'<span><b>Items:</b> {start_offset} - {end_offset} from {list_len} messages</span>'

            content += '''
            <table id="dtBasicExample" class="table table-striped table-bordered table-sm" cellspacing="0" width="100%">
            <thead>
                <tr><th class="th-sm">Class</th><th class="th-sm">Message</th></tr>
            </thead>
            <tbody>
            '''

            for msg in redis_client.get().lrange(key, start_offset, end_offset):
                pickled_msg = pickle.loads(msg)
                json_data = pickled_msg.__dict__
                json_string = pprint.pformat(json_data)

                content += f'<tr><td>{str(type(pickled_msg))[8:-2]}</td><td><pre><code>{json_string}</code></pre></td></tr>'

            content += '''</tbody>
                    </table>
                    '''

    return template.replace('#CONTENT#', content)


def get_key_len(key):
    key_type = redis_client.get().type(key).decode("utf-8")

    if key_type == 'string':
        return redis_client.get().get(key).decode("utf-8")
    elif key_type == 'list':
        return redis_client.get().llen(key)


def replace_redis_keys(
    template,
    selected_key=None,
):
    if not redis_client.is_set():
        return template.replace('#KEYS_OPTIONS#', '')

    keys = redis_client.get().keys()
    keys.sort()
    keys_options = ''

    for key in keys:
        key_str = str(key.decode("utf-8"))

        if key_str == selected_key:
            keys_options += f'<option value="{key_str}" selected>{key_str}</option>\n'
        else:
            keys_options += f'<option value="{key_str}">{key_str}</option>\n'

    return template.replace('#KEYS_OPTIONS#', keys_options)
