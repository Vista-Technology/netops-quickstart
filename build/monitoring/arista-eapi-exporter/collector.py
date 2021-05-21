from prometheus_client.core import GaugeMetricFamily

import pyeapi
import ssl
import socket
import logging
import os
import errno
import json
import time
import re
import pprint

class AristaMetricsCollector(object):
    def __init__(self, config, target, port, exclude=list):
        self._exclude = exclude
        self._username = os.getenv('ARISTA_USERNAME',config['username'])
        self._password = os.getenv('ARISTA_PASSWORD',config['password'])
        self._protocol = config['protocol'] or "https"
        self._timeout = int(os.getenv('TIMEOUT', config['timeout']))
        self._job = config['job']
        self._target = target
        self._port = port
        self._labels = {}
        self._switch_up = 0
        self._responstime = 0
        self._memtotal = 0
        self._memfree = 0
        self._get_labels()


    def connect_switch(self, command):
        # switch off certificate validation
        ssl._create_default_https_context = ssl._create_unverified_context

        switch_result = ""

        # set the default timeout 
        logging.debug("setting timeout to %s", self._timeout)

        connection = pyeapi.connect(transport=self._protocol, port=self._port, host=self._target, username=self._username, password=self._password, timeout=self._timeout)
        logging.info("Connecting to switch %s", self._target)

        data = {
            "jsonrpc": "2.0",
            "method": "runCmds",
            "params": {
                "format": "json",
                "timestamps": "true",
                "autoComplete": "false",
                "expandAliases": "false",
                "cmds": [command],
                "version": 1
            },
            "id": "EapiExplorer-1"
        }

        try:
            logging.debug("Running command %s", command) 
            switch_result = connection.send(json.dumps(data))
        except (pyeapi.eapilib.ConnectionError, socket.timeout) as pyeapi_connect_except:
            logging.error("----------------------------------------------")
            logging.error("PYEAPI Client Connection Exception: %s", pyeapi_connect_except)
            logging.error("While connecting to switch %s", self._target)
            logging.error("----------------------------------------------")
        except pyeapi.eapilib.CommandError as pyeapi_command_except:
            logging.error("----------------------------------------------")
            logging.error("PYEAPI Client Command Exception: %s", pyeapi_command_except)
            logging.error("While connecting to switch %s", self._target)
            logging.error("----------------------------------------------")
        finally:
            return switch_result
    
    def _get_labels(self):

        start = time.time()
        # Get the switch info for the labels
        switch_info = self.connect_switch (command="show version")
        if switch_info:
            logging.debug("Received a result from switch %s", self._target)
            labels_switch = {'job': self._job, 'instance': self._target, 'model': switch_info['result'][0]['modelName'], 'serial': switch_info['result'][0]['serialNumber'], 'version': switch_info['result'][0]['version']}
            self._memtotal = switch_info['result'][0]['memTotal']
            self._memfree = switch_info['result'][0]['memFree']
            self._switch_up = 1
        else:
            logging.debug("No result received from switch %s", self._target)
            labels_switch = {'job': self._job, 'instance': self._target, 'model': "unknown", 'serial': "unknown"}
            self._switch_up = 0

        end = time.time()
        self._responstime = end - start
        self._labels.update(labels_switch)

    def collect(self):

        # Export the up and response metrics
        info_metrics = GaugeMetricFamily('arista_monitoring_info','Arista Switch Monitoring',labels=self._labels)
        info_metrics.add_sample('arista_up', value=self._switch_up, labels=self._labels)
        info_metrics.add_sample('arista_response', value=self._responstime, labels=self._labels)
        
        yield info_metrics

        if self._switch_up == 1:

            logging.debug("Switch is rechable.")
            # Export the memory usage data
            mem_metrics = GaugeMetricFamily('switch_monitoring_memdata','Arista Switch Monitoring Memory Usage Data',labels=self._labels)
            mem_metrics.add_sample('arista_mem_total', value=self._memtotal, labels=self._labels)
            mem_metrics.add_sample('arista_mem_free', value=self._memfree, labels=self._labels)
            logging.debug("Exporting metrics arista_mem_total=%s", self._memtotal)
            logging.debug("Exporting metrics arista_mem_free=%s", self._memfree)
            yield mem_metrics

            # Get the tcam usage data
            switch_tcam = self.connect_switch (command="show hardware capacity")

            if switch_tcam:
                tcam_metrics = GaugeMetricFamily('switch_monitoring_data','Arista Switch Monitoring TCAM Usage Data',labels=self._labels)
                for entry in switch_tcam['result'][0]['tables']:
                    # add the chip and feature names as labels to the switch info labels
                    labels = {}
                    labels = ({'table': entry['table'], 'chip':entry["chip"], 'feature':entry["feature"]})
                    if entry['table'] not in self._exclude:
                        #logging.debug("Adding: table=%s value=%s labels=%s", entry['table'], entry["usedPercent"], labels)
                        labels.update(self._labels)
                        tcam_metrics.add_sample('arista_tcam', value=entry["usedPercent"], labels=labels)
                    else:
                        logging.debug("Excluding: table=%s value=%s labels=%s", entry['table'], entry["usedPercent"], labels)

                yield tcam_metrics
            
            else:
                pass

            switch_port_stats = self.connect_switch(command="show interfaces counters rates")
            regex_pattern = re.compile('.*reserved.*', re.IGNORECASE)

            if switch_port_stats:
                port_stats_metrics = GaugeMetricFamily('switch_monitoring_ports','Arista Switch Monitoring Port Statistics',labels=self._labels)
                for port_entry in switch_port_stats['result'][0]['interfaces']:
                    port_values = switch_port_stats['result'][0]['interfaces'][port_entry]
                    port_description = port_values['description'].replace("-> ","")
                    for port_value in port_values:
                        if port_value != "description" and port_value != 'interval' and not regex_pattern.match(port_description):
                            labels = {}
                            labels = ({'port': port_entry, 'stat': port_value, 'description': port_description})
                            labels.update(self._labels)
                            #logging.debug("Adding: port=%s stat=%s value=%s labels=%s", port_entry, port_value, port_values[port_value], labels)
                            port_stats_metrics.add_sample('arista_port_stats', value=float(port_values[port_value]), labels=labels)

                yield port_stats_metrics
        else:
            pass
