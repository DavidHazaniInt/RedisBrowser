import fastapi
import starlette.requests
import starlette.responses


app = fastapi.FastAPI()


@app.get('/')
def index():
    return starlette.responses.Response(
        content='til',
        status_code=200,
    )
