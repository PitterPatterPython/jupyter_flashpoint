from argparse import ArgumentParser, BooleanOptionalAction
import re
from flashpoint_utils.flashpoint_api import FlashpointAPI

class UserInputParser(ArgumentParser):
    """
    A class to parse a user's cell magic from Jupyter.

    Attributes
    ----------
    None

    Methods
    -------
    parse_input(input):
        Parses the user's cell magic from Jupyter
    """
    def __init__(self, *args, **kwargs):
        self.valid_commands = list(filter(lambda func : not func.startswith('_') and hasattr(getattr(FlashpointAPI,func),'__call__') , dir(FlashpointAPI)))
        self.parser = ArgumentParser(prog=r"%%flashpoint <instance>")
        
        self.subparsers = self.parser.add_subparsers(dest="command")
        
        # Subparser for "search_media" command
        self.parser_search_media = self.subparsers.add_parser("search_media", help="Search Flashpoint for images and videos that match your query")
        self.parser_search_media.add_argument("-l", "--limit", type=int, default=25, required=False, help="limit the number of results returned to this number")
        self.parser_search_media.add_argument("-d", "--days", type=int, default=7, required=False, help="how far back to look for results in number of days")
        self.parser_search_media.add_argument("--images", action=BooleanOptionalAction, required=False, help="include image thumbnails in results")
        
        # Subparser for "get_image" command
        self.parser_get_image = self.subparsers.add_parser("get_image", help="Get an image from the Flashpoint API by the _source.media.storage_uri JSON path")
        
    def display_help(self, command):
        self.parser.parse_args([command, "--help"])
        
    def parse_input(self, input: str):
        """ Parses the user's cell magic from Jupyter

            Keyword Arguments:
            input -- the entire contents of the cell from Jupyter

            Returns:
            parsed_input -- an object containing an error status, a message,
                and parsed command from argparse.parse()
        """

        # Prepare the response object to return to the calling function
        parsed_input = {
            "error" : False,
            "message" : None,
            "input" : {}
        }

        # Split the cell magic by newline
        split_user_input = input.strip().split("\n")

        try:
            if len(split_user_input) == 1:
                parsed_user_command = self.parser.parse_args(split_user_input[0].split())
                parsed_input["input"].update(vars(parsed_user_command))
                parsed_input["error"] = True
                parsed_input["message"] = "Expected to get 2 lines in your cell magic, but got 1. Try `--help` or `-h`"
                
            elif len(split_user_input) == 2:
                parsed_user_command = self.parser.parse_args(split_user_input[0].split())
                parsed_user_query = split_user_input[1]
            
                parsed_input["input"].update(vars(parsed_user_command))
                parsed_input["input"].update({"query" : parsed_user_query})
            
            else:
                parsed_input["error"] = True
                parsed_input["message"] = f"Expected to get 2 lines in your cell magic, but got {len(split_user_input)}. Try `--help` or `-h`"
                return parsed_input

            # Display help instead if the user included --help or -h in the 1st line of their cell magic
            if re.search(r"(\-h|\-\-help)", split_user_input[0]):
                self.display_help(parsed_input["input"]["command"])
        
        except SystemExit:
            parsed_input["error"] = True
            parsed_input["message"] = "Invalid input received, see the output above. Try `--help` or `-h`"

        return parsed_input