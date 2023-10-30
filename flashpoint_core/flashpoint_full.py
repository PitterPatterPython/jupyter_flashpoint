#!/usr/bin/python

# Base imports for all integrations, only remove these at your own risk!
import json
import sys
import os
import time
import pandas as pd
from collections import OrderedDict
import re
from integration_core import Integration
import datetime
from IPython.core.magic import (Magics, magics_class, line_magic, cell_magic, line_cell_magic)
from IPython.core.display import HTML
from flashpoint_core._version import __desc__

# Your Specific integration imports go here, make sure they are in requirements!
import jupyter_integrations_utility as jiu


@magics_class
class Flashpoint(Integration):
    # Static Variables
    # The name of the integration
    name_str = "flashpoint"
    instances = {} 
    custom_evars = ["flashpoint_conn_default"]
    # These are the variables in the opts dict that allowed to be set by the user. These are specific to this custom integration and are joined
    # with the base_allowed_set_opts from the integration base

    # These are the variables in the opts dict that allowed to be set by the user. These are specific to this custom integration and are joined
    # with the base_allowed_set_opts from the integration base
    custom_allowed_set_opts = ["flashpoint_conn_default"]


    myopts = {}
    myopts['flashpoint_conn_default'] = ["default", "Default instance to connect with"]


    # Class Init function - Obtain a reference to the get_ipython()
    def __init__(self, shell, debug=False, *args, **kwargs):
        super(Flashpoint, self).__init__(shell, debug=debug)
        self.debug = debug

        #Add local variables to opts dict
        for k in self.myopts.keys():
            self.opts[k] = self.myopts[k]

        self.load_env(self.custom_evars)
        self.parse_instances()

    def customAuth(self, instance):
        result = -1
        inst = None
        if instance not in self.instances.keys():
            result = -3
            jiu.displayMD(f"**[ ! ]** Instance **{instance}** not found in instances: Connection Failed")
        else:
            inst = self.instances[instance]
        if inst is not None:
            inst['session'] = None
            mypass = ""
            if inst['enc_pass'] is not None:
                mypass = self.ret_dec_pass(inst['enc_pass'])
                inst['connect_pass'] = ""
            try:
                inst['session'] = splclient.connect(host=inst['host'], port=inst['port'], username=inst['user'], password=mypass, autologin=self.opts['splunk_autologin'][0])
                result = 0
            except:
                jiu.displayMD(f"**[ ! ]** Unable to connect to Splunk instance **{instance}** at **{inst['conn_url']}**")
                result = -2  

        return result

    def retCustomDesc(self):
        return __desc__


    def customHelp(self, curout):
        n = self.name_str
        mn = self.magic_name
        m = "%" + mn
        mq = "%" + m
        table_header = "| Magic | Description |\n"
        table_header += "| -------- | ----- |\n"
        out = curout
        qexamples = []
        qexamples.append(["myinstance", "search term='MYTERM'", "Run a SPL (Splunk) query against myinstance"])
        qexamples.append(["", "search term='MYTERM'", "Run a SPL (Splunk) query against the default instance"])
        qexamples.append(["wtf", "wtf=wtf", "WTF'ing WTF F"])
        out += self.retQueryHelp(qexamples)

        return out




    # This is the magic name.
    @line_cell_magic
    def flashpoint(self, line, cell=None):
        if cell is None:
            line = line.replace("\r", "")
            line_handled = self.handleLine(line)
            if self.debug:
                jiu.displayMD(f"**[ Dbg ]** line: {line}")
                jiu.displayMD(f"**[ Dbg ]** cell: {cell}")
            if not line_handled: # We based on this we can do custom things for integrations. 
                if line.lower() == "testintwin":
                    jiu.displayMD("You've found the custom testint winning line magic!")
                else:
                    jiu.displayMD(f"I'm sorry, I don't know what you want to do with your line magic, try just %{self.name_str} for help options")
        else: # This is run is the cell is not none, thus it's a cell to process  - For us, that means a query
            self.handleCell(cell, line)