from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from k8s_utils import *
from metrics import number_of_requests, number_of_failures, execution_time

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    with execution_time.labels(service='/').time():
        with number_of_failures.labels(service='/').count_exceptions():
            return RedirectResponse("/docs")


@number_of_failures.labels(service='/service1/').count_exceptions()
@app.post("/service1/")
async def create_app(app_name: str, replicas: int, image_address: str, image_tag: str, domain_address: str,
                     service_port: int, resources: dict, envs: dict = None, secrets: dict = None,
                     external_access: bool = False, namespace: str = 'default'):
    with execution_time.labels(service='/service1/').time():
        with number_of_failures.labels(service='/service1/').count_exceptions():
            try:
                create_new_app(app_name, replicas, image_address, image_tag, domain_address,
                               service_port, resources, envs, secrets, external_access, namespace)
                return f"Application {app_name} created successfully!"
            except Exception as e:
                return HTTPException(status_code=400, detail=f"Error creating deployment : {str(e)}")


@app.get("/service2/")
async def deployment_status(deployment_name: str):
    with execution_time.labels(service='/service2/').time():
        with number_of_failures.labels(service='/service2/').count_exceptions():
            try:
                return get_deployment_status(deployment_name)
            except Exception as e:
                number_of_failures.labels(service='/service2/').inc()
                raise HTTPException(status_code=400, detail=f"Error retrieving deployment information: {str(e)}")


@app.get("/service3/")
async def deployments():
    with execution_time.labels(service='/service3/').time():
        with number_of_failures.labels(service='/service3').count_exceptions():
            deployments = get_all_deployments()
            res = []
            for deployment in deployments:
                deployment_name = deployment.metadata.name
                res.append(get_deployment_status(deployment_name))
            return res


@app.post("/postgres/")
async def create_postgres(app_name: str, resources: dict = None, external_access: bool = False, envs: dict = None):
    with execution_time.labels(service='/postgres/').time():
        with number_of_failures.labels(service='/postgres/').count_exceptions():
            try:
                result = create_postgres_app(app_name, resources, external_access, envs)
                return result
            except Exception as e:
                number_of_failures.labels(service='/postgres/').inc()
                return HTTPException(status_code=400, detail=f"Error creating postgres res {resources}: {str(e)}")


@app.get("/healthz/")
async def check_healtz():
    return Response(status_code=200, content='I am healthzy!')


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    number_of_requests.labels(service='/docs').inc()
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )
