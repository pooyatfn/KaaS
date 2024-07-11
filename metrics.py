from prometheus_client import start_http_server, Counter, Summary

number_of_requests = Counter('number_of_requests', 'numberOfRequests', ['service'])
number_of_failures = Counter('number_of_failures', 'numberOfFailures', ['service'])
execution_time = Summary('execution_time', 'executionTime', ['service'])

start_http_server(port=8001)
