import os


def is_running_in_kubernetes():
    """
    This is a naive way to check if the service is running inside kubernetes
    :return: bool
    """
    return "KUBERNETES_SERVICE_HOST" in os.environ
