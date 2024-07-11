import random
import string

from kubernetes import client, config
from kubernetes.client import V1Pod

config.load_kube_config()
apps = client.AppsV1Api()
core = client.CoreV1Api()
networking = client.NetworkingV1Api()
batch = client.BatchV1Api()
configuration = client.Configuration()


def create_new_app(app_name, replicas, image_address, image_tag,
                   domain_address, service_port, resources=None,
                   envs: dict = None, secrets=None, external_access=False,
                   namespace='default'):
    if resources is None:
        resources = {"cpu": "500m", "memory": "512Mi"}
    create_deployment(app_name, replicas,
                      image_address, image_tag, service_port,
                      resources, envs, namespace)

    create_service(app_name, service_port)

    if external_access:
        create_ingress(app_name, domain_address, service_port)

    if secrets:
        create_secrets(app_name, secrets)


def create_stateful_set(app_name, replicas, image_address, image_tag, service_port, resources, namespace='default'):
    if resources is None:
        resources = {"cpu": "500m", "memory": "512Mi"}
    container = client.V1Container(
        env_from=[client.V1EnvFromSource(
            config_map_ref=client.V1ConfigMapEnvSource(name=f"{app_name}-configmap"),
        ), client.V1EnvFromSource(
            secret_ref=client.V1SecretEnvSource(name=f"{app_name}-secret")
        )],
        name=f"{app_name}-sfs",
        image=f"{image_address}:{image_tag}",
        image_pull_policy="IfNotPresent",
        resources=client.V1ResourceRequirements(
            limits={resource: value for resource, value in resources.items()},
        ),
        ports=[client.V1ContainerPort(container_port=service_port)],
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": app_name}),
        spec=client.V1PodSpec(containers=[container]))
    spec = client.V1StatefulSetSpec(
        replicas=replicas,
        service_name=f"{app_name}-service",
        selector=client.V1LabelSelector(
            match_labels={"app": app_name}
        ),
        template=template)
    statefulset = client.V1StatefulSet(
        api_version="apps/v1",
        kind="StatefulSet",
        metadata=client.V1ObjectMeta(name=f"{app_name}-sfs"),
        spec=spec)

    apps.create_namespaced_stateful_set(namespace=namespace, body=statefulset)


def create_postgres_app(app_name, resources, external_access, envs):
    replicas = 1
    image_address = 'localhost:5000/postgres'
    image_tag = 'latest'
    domain_address = f'postgres.{app_name}'
    service_port = 5432
    self_envs = {'shared_buffers': '128MB', 'max_connection': '100', 'postgres_db': app_name + '-db'}
    self_envs.update(envs)
    configmap_data = self_envs
    create_configmap(app_name, configmap_data)
    username = app_name + '-postgres'
    random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    secrets = {"POSTGRES_USERNAME": username, "POSTGRES_PASSWORD": random_password}
    create_secrets(app_name, secrets)
    create_stateful_set(app_name, replicas, image_address, image_tag, service_port, resources)
    create_service(app_name, service_port)
    if external_access:
        create_ingress(app_name, domain_address, service_port)

    return f"Postgres {app_name} created successfully!\nUsername: {username}\nPassword: {random_password}"


def create_deployment(app_name, replicas, image_address, image_tag, service_port, resources,
                      envs, namespace='default'):
    metadata = client.V1ObjectMeta(name=f"{app_name}-deployment")

    spec = client.V1DeploymentSpec(
        replicas=replicas,
        template=client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": app_name}),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name=app_name,
                        image=f"{image_address}:{image_tag}",
                        ports=[
                            client.V1ContainerPort(name="http", protocol="TCP",
                                                   container_port=service_port)],
                        resources=client.V1ResourceRequirements(
                            limits={resource: value for resource, value in resources.items()},
                        ),
                        env=[client.V1EnvVar(name=var_name, value=var) for var_name, var in envs.items()],
                    )
                ]
            ),
        ),
        selector={"matchLabels": {"app": app_name}},
    )
    deployment = client.V1Deployment(metadata=metadata, spec=spec)
    apps.create_namespaced_deployment(namespace=namespace, body=deployment)


##################
#
# def get_cronjob_body(app_name, image_address, image_tag, command: list, namespace='default'):
#     body = {
#         "apiVersion": "batch/v1",
#         "kind": "CronJob",
#         "metadata": {
#             "name": app_name,
#             "namespace": namespace
#         },
#         "spec": {
#             "schedule": "*/5 * * * *",
#             "concurrencyPolicy": "Allow",
#             "suspend": False,
#             "jobTemplate": {
#                 "spec": {
#                     "template": {
#                         "spec": {
#                             "containers": [
#                                 {
#                                     "name": app_name,
#                                     "image": f"{image_address}:{image_tag}",
#                                     "command": command
#                                 }
#                             ],
#                             "restartPolicy": "Never"
#                         }
#                     }
#                 }
#             },
#             # "successfulJobsHistoryLimit": 3,
#             # "failedJobsHistoryLimit": 1
#         }
#     }
#     return body
#
#
# def create_namespaced_cron_job(body, namespace='default'):
#     cronjob_json = body
#     name = body['metadata']['name']
#     v1 = client.BatchV1Api()
#     ret = v1.create_namespaced_cron_job(namespace=namespace, body=cronjob_json, pretty=True,
#                                         _preload_content=False, async_req=False)
#     ret_dict = json.loads(ret.data)
#     print(f'create succeed\n{json.dumps(ret_dict)}')


###########
def create_configmap(app_name, string_data):
    secret = client.V1Secret(
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(name=f"{app_name}-configmap"),
        string_data=string_data
    )

    core.create_namespaced_config_map(namespace="default", body=secret)


def create_cronjob(app_name, image_address, image_tag, host_name, namespace='default'):
    metadata = client.V1ObjectMeta(name=f"{app_name}-cron")

    spec = client.V1CronJobSpec(
        schedule="*/5 * * * *",
        job_template=client.V1JobTemplateSpec(
            spec=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": app_name}),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name=app_name,
                            image=f"{image_address}:{image_tag}",
                            command=["curl", host_name + ".example.com/healtz"],
                        )
                    ]
                )),
        ),
    )
    deployment = client.V1CronJob(metadata=metadata, spec=spec)
    batch.create_namespaced_cron_job(namespace=namespace, body=deployment)


def create_service(app_name, service_port, namespace='default'):
    body = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=f"{app_name}-service",
            labels={"app.kubernetes.io/name": app_name}
        ),
        spec=client.V1ServiceSpec(
            selector={"app": app_name},
            type="ClusterIP",
            ports=[client.V1ServicePort(
                protocol='TCP',
                port=service_port,
                target_port=service_port,
                name='http',
            )]
        )
    )

    core.create_namespaced_service(namespace=namespace, body=body)


def create_ingress(app_name, domain_address, service_port, namespace='default'):
    body = client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(name=f"{app_name}-ingress"),
        spec=client.V1IngressSpec(
            ingress_class_name='nginx',
            rules=[client.V1IngressRule(
                host=f"{domain_address}.example.local",
                http=client.V1HTTPIngressRuleValue(
                    paths=[client.V1HTTPIngressPath(
                        path="/",
                        path_type="Prefix",
                        backend=client.V1IngressBackend(
                            service=client.V1IngressServiceBackend(
                                port=client.V1ServiceBackendPort(
                                    number=service_port,
                                ),
                                name=f"{app_name}-service")
                        )
                    )]
                )
            )
            ]
        )
    )

    networking.create_namespaced_ingress(
        namespace=namespace,
        body=body
    )


def create_secrets(app_name, secrets: dict, namespace='default'):
    client_secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name=f"{app_name}-secret"),
        string_data=secrets,
        data={},
    )

    core.create_namespaced_secret(namespace=namespace, body=client_secret)


def get_deployment_details(deployment_name: str, namespace: str = 'default'):
    deployment = apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
    replicas = deployment.spec.replicas
    ready_replicas = deployment.status.ready_replicas
    return {"Name": deployment_name, "Replicas": replicas, "Ready Replicas": ready_replicas}


def get_pods_of_deployment(deployment_name: str, namespace: str = 'default'):
    pods = core.list_namespaced_pod(namespace=namespace).items
    res = []
    for pod in pods:
        if pod.metadata.name.startswith(deployment_name):
            res.append(pod)
    return res


def get_pod_statuses(pod: V1Pod):
    return {"Pod Name": pod.metadata.name, "Phase": pod.status.phase, "Host IP": pod.status.host_ip,
            "Pod IP": pod.status.pod_ip, "Start Time": pod.status.start_time}


def get_all_deployments(namespace: str = 'default'):
    deployments = apps.list_namespaced_deployment(namespace=namespace)
    return deployments.items


def get_deployment_status(deployment_name: str):
    deployment_details = get_deployment_details(deployment_name)

    deployment_details["Pods"] = []
    pods = get_pods_of_deployment(deployment_name)
    for pod in pods:
        pod_status = get_pod_statuses(pod)
        deployment_details["Pods"].append(pod_status)
    return deployment_details


if __name__ == "__main__":
    # Example usage
    create_new_app(
        app_name="api",
        replicas=3,
        image_address="localhost:5000/api",
        image_tag="latest",
        domain_address="example.local",
        service_port=8000,
        resources={"cpu": "500m", "memory": "512Mi"},
        envs={"MY_ENV_VAR": "my-value"},
        secrets=["PASS", "password"],
        external_access=True,
    )
