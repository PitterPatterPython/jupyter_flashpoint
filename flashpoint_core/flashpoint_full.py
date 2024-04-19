#!/usr/bin/python

import pandas as pd
from integration_core import Integration
from IPython.core.display import HTML
from IPython.core.magic import (magics_class, line_cell_magic)
from IPython.display import display
from flashpoint_core._version import __desc__
import jupyter_integrations_utility as jiu
from flashpoint_utils.flashpoint_api import FlashpointAPI
from flashpoint_utils.user_input_parser import UserInputParser
from flashpoint_utils.api_response_parser import ResponseParser
from flashpoint_utils.helper_functions import format_b64_image_for_dataframe


@magics_class
class Flashpoint(Integration):
    # Static Variables
    # The name of the integration
    name_str = "flashpoint"
    instances = {}
    custom_evars = ["flashpoint_conn_default"]

    # These are the variables in the opts dict that allowed to be set by the user.
    # These are specific to this custom integration and are joined
    # with the base_allowed_set_opts from the integration base
    custom_allowed_set_opts = ["flashpoint_conn_default", "flashpoint_verify_ssl", "flashpoint_disable_ssl_warnings"]

    myopts = {}
    myopts["flashpoint_conn_default"] = ["default", "Default instance to connect with"]
    myopts["flashpoint_verify_ssl"] = [True, "Toggle this to True to verify SSL connections"]
    myopts["flashpoint_disable_ssl_warnings"] = [True, "Toggle this to False to receive warnings \
        for SSL; this will be _very_ noisy!"]
    myopts["flashpoint_max_retries"] = [3, "The number of attempts to retry a request before failing."]
    myopts["flashpoint_max_workers"] = [10, "The number of workers to use if searching for \
        multiple search terms at once"]

    # Class Init function - Obtain a reference to the get_ipython()
    def __init__(self, shell, debug=False, *args, **kwargs):
        super(Flashpoint, self).__init__(shell, debug=debug)
        self.debug = debug

        # Add local variables to opts dict
        for k in self.myopts.keys():
            self.opts[k] = self.myopts[k]

        self.API_ENDPOINTS = list(
            filter(
                lambda func: not func.startswith("_") and
                hasattr(getattr(FlashpointAPI, func), "__call__"), dir(FlashpointAPI)
                ))
        self.user_input_parser = UserInputParser()
        self.response_parser = ResponseParser()
        self.load_env(self.custom_evars)
        self.parse_instances()

    def retCustomDesc(self):
        return __desc__

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

            # Turn off SSL warnings, if the user chose to
            if self.opts["flashpoint_disable_ssl_warnings"][0] is True:
                import urllib3
                urllib3.disable_warnings()

            # Proxy variables, if any
            if inst["options"].get("useproxy", 0) == 1:
                myproxies = self.retProxy(instance)
            else:
                myproxies = None

            # SSL Verification
            ssl_verify = self.opts["flashpoint_verify_ssl"][0]
            if isinstance(ssl_verify, str) and ssl_verify.strip().lower() in ["true", "false", "1", "0"]:
                if ssl_verify.strip().lower() in ["true", "1"]:
                    ssl_verify = True
                else:
                    ssl_verify = False
            elif isinstance(ssl_verify, int) and ssl_verify in [0, 1]:
                if ssl_verify == 1:
                    ssl_verify = True
                else:
                    ssl_verify = False

            if inst["enc_pass"] is not None:
                flashpointpass = self.ret_dec_pass(inst["enc_pass"])
                inst["connect_pass"] = ""

            try:
                inst["session"] = FlashpointAPI(host=inst["host"],
                                                token=flashpointpass,
                                                proxies=myproxies,
                                                verify=ssl_verify,
                                                max_retries=self.opts["flashpoint_max_retries"][0],
                                                max_workers=self.opts["flashpoint_max_workers"][0])

                result = 0

            except Exception as e:
                jiu.display_error(f"**[ ! ]** Unable to connect to Flashpoint instance **{instance}** at \
                    **{inst['conn_url']}**: `{e}`")
                result = -2

        return result

    def customHelp(self, current_output):
        out = current_output
        out += self.retQueryHelp(None)

        return out

    def retQueryHelp(self, q_examples=None):

        magic_name = self.magic_name
        magic = f"%{magic_name}"

        cell_magic_helper_text = (f"\n## Running {magic_name} cell magics\n"
                                  "--------------------------------\n"
                                  f"\n#### When running {magic} cell magics, {magic} and the instance name \
                                      will be on the 1st of your cell, and then the command to run \
                                      will be on the 2nd line of your cell.\n"
                                  "\n### Cell magic examples\n"
                                  "-----------------------\n")

        cell_magic_table = ("| Cell Magic | Description |\n"
                            "| ---------- | ----------- |\n"
                            "| %%flashpoint prod<br>--help | Display usage syntax help for `%%flashpoint` \
                                cell magics |\n"
                            "| %%flashpoint instance<br>command --help | Display usage syntax for a specific \
                                command |\n"
                            "| %%flashpoint instance<br>search_media -l 25 -s 2024-01-01 -e 2024-01-31 --images \
                                -q \"wells fargo\" | Search Flashpoint media for the specified start and end \
                                dates for posts containing the exact phrase \"wells fargo\", limited to 25 results, \
                                and include the images in the results. The date_end parameter will default to \
                                'now' if not specified. If you'd like to do some more complex searching, \
                                like \|\"wells fargo\" \|checking, just make sure to wrap single quotes around it, \
                                like so:<br>`'\|\"wells fargo\" \|checking'` |\n"
                            "| %%flashpoint instance<br>get_image -u _source.media.storage_uri | Retrieve an image \
                                from the Flashpoint API by the `_source.media.storage_uri` field of a result. |\n"
                            "| %%flashpoint instance<br>search_chat -l 5 -s 2024-01-01 -e 2024-01-31 -q \
                                \"search term\" | Search Flashpoint chat messages for the specified start and end \
                                dates for posts containing the exact phrase \"search term\", limited to 5 results. If \
                                you'd like to do some more complex searching, like \|\"wells fargo\" \|checking, just \
                                make sure to wrap single quotes around it:<br>`'\|\"wells fargo\" \|checking'` |\n"
                            "| %%flashpoint instance<br>search_chat -l 10 -s 2024-01-01 -u list_of_search_terms | \
                                Search Flashpoint chat messages starting from 2024-01-01 until now for posts \
                                containing keywords from an existing list in Jupyter. Simply replace \
                                `list_of_search_terms` with the name of the list containing your search terms<br>\
                                **NOTE** If the list contains multiple search terms, this will run asynchronously \
                                and concurrently, so like really fast. |\n")

        help_out = cell_magic_helper_text + cell_magic_table

        return help_out

    def customQuery(self, query: str, instance: str):
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
        parsed_input = self.user_input_parser.parse_input(query, type="cell")

        if self.debug:
            jiu.displayMD(f"**[ Dbg ]** Parsed Query: `{parsed_input}`")
            jiu.displayMD(f"**[ Dbg ]** Instance: `{instance}`")

        if parsed_input["error"] is True:
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
                    display(HTML(parsed_response[1]))
                    dataframe = pd.DataFrame({"b64_image_string": parsed_response[0],
                                              "image_storage_uri": parsed_response[1]},
                                             index=[0])
                    status = "Success"

                elif (parsed_input["input"]["command"] == "search_media") and (parsed_input["input"]["images"]):
                    dataframe = pd.DataFrame(parsed_response)
                    display(HTML(dataframe.to_html(formatters={"image_content": format_b64_image_for_dataframe},
                                                   escape=False)))
                    status = "Success"

                else:
                    dataframe = pd.DataFrame(parsed_response)
                    status = "Success"

            except Exception as e:
                jiu.display_error(f"**[ ! ]** Error during execution: {e}")
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

            if not line_handled:  # We based on this we can do custom things for integrations.
                try:
                    parsed_input = self.user_input_parser.parse_input(line, type="line")

                    if self.debug:
                        jiu.displayMD(f"**[ Dbg ]** Parsed Query: `{parsed_input}`")

                    if parsed_input["error"] is True:
                        jiu.display_error(f"{parsed_input['message']}")

                    else:
                        instance = parsed_input["input"]["instance"]

                        if instance not in self.instances.keys():
                            jiu.display_error(f"Instance **{instance}** not found in instances")

                        else:
                            response = self.instances[instance]["session"]._handler(**parsed_input["input"])
                            parsed_response = self.response_parser._handler(response, **parsed_input["input"])
                            jiu.displayMD(parsed_response)

                except Exception as e:
                    jiu.display_error(f"There was an error in your line magic: {e}")

        else:  # This is run is the cell is not none, thus it's a cell to process  - For us, that means a query
            self.handleCell(cell, line)
