import falcon
import logging
import socket

from wsgiref import simple_server
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from prometheus_client.exposition import generate_latest

from collector import AristaMetricsCollector

class welcomePage:

    def on_get(self, req, resp):
        resp.body = '{"message": "This is the Arista eAPI exporter. Use /arista to retrieve metrics."}'

class metricHandler:
    def __init__(self, config, exclude=list):
        self._exclude = exclude
        self._config = config

    def on_get(self, req, resp):
        
        param = req.get_param("target").split(':')
        self._target = param[0]
        self._port = param[1]

        resp.set_header('Content-Type', CONTENT_TYPE_LATEST)
        if not self._target:
            msg = "No target parameter provided!"
            logging.error(msg)
            raise falcon.HTTPMissingParam('target')
        
        try:
            socket.gethostbyname(self._target)
        except socket.gaierror as excptn:
            msg = "Target does not exist in DNS: {0}".format(excptn)
            logging.error(msg)
            resp.status = falcon.HTTP_400
            resp.body = msg

        else:
            registry = AristaMetricsCollector(
                self._config,
                exclude=self._exclude,
                target=self._target,
                port=self._port
                )

            collected_metric = generate_latest(registry)
            resp.body = collected_metric
