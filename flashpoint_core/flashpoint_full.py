#!/usr/bin/python

import pandas as pd
from integration_core import Integration
from IPython.core.display import HTML
from IPython.core.magic import (magics_class, line_cell_magic)
from IPython.display import display
from flashpoint_core._version import __desc__

import jupyter_integrations_utility as jiu
from utils.flashpoint_api import FlashpointAPI
from utils.user_input_parser import UserInputParser
from utils.api_response_parser import ResponseParser
from utils.helper_functions import format_b64_image_for_dataframe


@magics_class
class Flashpoint(Integration):
    # Static Variables
    # The name of the integration
    name_str = "flashpoint"
    instances = {} 
    custom_evars = ["flashpoint_conn_default"]

    # These are the variables in the opts dict that allowed to be set by the user. These are specific to this custom integration and are joined
    # with the base_allowed_set_opts from the integration base
    custom_allowed_set_opts = ["flashpoint_conn_default"]


    myopts = {}
    myopts["flashpoint_conn_default"] = ["default", "Default instance to connect with"]
    myopts["flashpoint_verify_ssl"] = [False, "Toggle this to True to verify SSL connections"]


    # Class Init function - Obtain a reference to the get_ipython()
    def __init__(self, shell, debug=False, *args, **kwargs):
        super(Flashpoint, self).__init__(shell, debug=debug)
        self.debug = debug

        #Add local variables to opts dict
        for k in self.myopts.keys():
            self.opts[k] = self.myopts[k]
        
        self.API_ENDPOINTS = list(filter(lambda func: not func.startswith("_") and hasattr(getattr(FlashpointAPI, func), "__call__"), dir(FlashpointAPI)))
        self.user_input_parser = UserInputParser()
        self.response_parser = ResponseParser()
        self.load_env(self.custom_evars)
        self.parse_instances()

    def req_username(self, instance):
        """See integration_base.py where this function is inherited from \
            and why it's overriden here. We're returning False to say "don't
            prompt for a username"
        """
        return False
    
    def customAuth(self, instance):
        result = -1
        inst = None

        if instance not in self.instances.keys():
            result = -3
            jiu.displayMD(f"**[ ! ]** Instance **{instance}** not found in instances: Connection Failed")
        else:
            inst = self.instances[instance]
            
        if inst is not None:
            flashpointpass = ""

            if inst['options'].get('useproxy', 0) == 1:
                myproxies = self.retProxy(instance)
            else:
                myproxies = None

            if inst['enc_pass'] is not None:
                flashpointpass = self.ret_dec_pass(inst['enc_pass'])
                inst['connect_pass'] = ""

            try:
                inst['session'] = FlashpointAPI(host=inst['host'], token=flashpointpass, proxies=myproxies)
                result = 0
            except Exception as e:
                jiu.displayMD(f"**[ ! ]** Unable to connect to Flashpoint instance **{instance}** at **{inst['conn_url']}**: `{e}`")
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
        qexamples.append(["prod", "search_media\nyour-flashpoint-query", "Perform an image search against the Flashpoint API that matches a query."])
        qexamples.append(["prod", "get_image\nstorage_uri", "Retrieve an image from the Flashpoint API by `_source.media.storage_uri`"])

        out += self.retQueryHelp(qexamples)

        return out
    
    def customQuery(self, query : str, instance : str):
        """ Execute a custom cell magic against the Flashpoint API.
            
            START HERE -- General flow of this function:
            1.  We need to parse the user's cell magic via ../utils/user_input_parser. We
                construct an object there that has metadata. We use that object to drive
                the rest of this function.
            2.  We'll display errors if there were any obvious ones during parsing.
            3.  Using the parsed input's "input" object, we'll send those to the Flashpoint
                API's _handler function via ../utils/flashpoint_api. The _handler function
                plays traffic cop for every API call. 
            4.  I follow this simple idiom: the API is there to retrieve data, not format it.
                That's why I delegate parsing the API response to ../utils/api_response_parser.
                Just like the API, we pass the response to the _handler function of our response
                parser, and it takes care of the rest. It's basically magic.
            5.  We choose how to handle the parsed data based on the type of data we're
                handling. That's what those if/elif/else statements are for.
            
            Keyword Arguments:
            query -- this is what the user types in the cell
            instance -- this is the instance/connection we'll run the query against

            Returns:
            dataframe -- a pandas dataframe, or None
            status -- sent back to jupyter_integration_base
        """
        
        # Parse the supplied user input via the cell magic using
        # the user_input_parser utility in ../utils
        parsed_input = self.user_input_parser.parse_input(query)
        
        if self.debug:
            jiu.displayMD(f"**[ Dbg ]** Parsed Query: `{parsed_input}`")
            jiu.displayMD(f"**[ Dbg ]** Instance: `{instance}`")

        if parsed_input["error"] == True:
            jiu.displayMD(f"**[ ! ]** {parsed_input['message']}")
            dataframe = None
            status = f"Failure: {parsed_input['message']}"

        else:
            try:
                # Execute the query to the Flashpoint API by sending the user's parsed input
                response = self.instances[instance]["session"]._handler(**parsed_input["input"])
                
                # Pass the response to the response parser, which is responsible for 
                # transforming API responses from Flashpoint into a structure that can 
                # move into a dataframe
                parsed_response = self.response_parser._handler(parsed_input["input"]["command"], response)

                if parsed_input["input"]["command"] == "get_image":
                    display(HTML(parsed_response))
                    dataframe = None
                    status = "Success - No Results"

                elif (parsed_input["input"]["command"] == "search_media") and (parsed_input["input"]["images"]):
                    dataframe = pd.DataFrame(parsed_response)
                    display(HTML(dataframe.to_html(formatters={"image_content": format_b64_image_for_dataframe}, escape=False)))
                    status = "Success"
                
                else:
                    dataframe = pd.DataFrame(parsed_response)
                    status = "Success"
            
            except Exception as e:
                jiu.displayMD(f"**[ ! ]** Error during execution: {e}")
                dataframe = None
                status = f"Failure - {e}"

        return dataframe, status

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