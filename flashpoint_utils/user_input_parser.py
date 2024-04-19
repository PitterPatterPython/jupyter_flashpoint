from argparse import ArgumentParser, BooleanOptionalAction
import re
import shlex
from flashpoint_utils.flashpoint_api import FlashpointAPI
from flashpoint_utils.helper_functions import valid_date_format, valid_list, valid_query


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
        self.valid_commands = list(
            filter(lambda func: not func.startswith('_') and
                   hasattr(getattr(FlashpointAPI, func), '__call__'), dir(FlashpointAPI)
                   ))

        self.line_parser = ArgumentParser(prog=r"%flashpoint")
        self.cell_parser = ArgumentParser(prog=r"%%flashpoint")

        self.line_subparsers = self.line_parser.add_subparsers(dest="command")
        self.cell_subparsers = self.cell_parser.add_subparsers(dest="command")

        # CELL SUBPARSERS #
        # Subparser for "search_media" command
        self.parser_search_media = self.cell_subparsers.add_parser("search_media", help="Search Flashpoint for images \
            and videos that match your query")
        self.parser_search_media.add_argument("-l", "--limit", type=int, default=25, required=False, help="limit the \
            number of results returned to this number")
        self.parser_search_media.add_argument("-s", "--date_start", type=valid_date_format, required=True, help="the \
            earliest date to look for results")
        self.parser_search_media.add_argument("-e", "--date_end", type=valid_date_format, default="now",
                                              required=False, help="latest date to look for results; default is 'now'")
        self.parser_search_media.add_argument("-q", "--query", type=valid_query, required=True, help="your query")
        self.parser_search_media.add_argument("--images", action=BooleanOptionalAction, required=False, help="include \
            image thumbnails in results")

        # Subparser for "get_image" command
        self.parser_get_image = self.cell_subparsers.add_parser("get_image", help="Get an image from the Flashpoint \
            API by the _source.media.storage_uri JSON path")
        self.parser_get_image.add_argument("-u", "--uri", required=True, help="The value of the \
            _source.media.storage_uri field of the image to retrieve")

        # Subparser for "search_chat" command
        self.parser_search_chat = self.cell_subparsers.add_parser("search_chat", help="Search Flashpoint for chat \
            messages that contain a keyword.")
        self.parser_search_chat.add_argument("-l", "--limit", type=int, default=25, required=False, help="the amount \
            of results to return. NOTE: if the --list flag is used, it will return this amount for EACH keyword.")
        self.parser_search_chat.add_argument("-s", "--date_start", type=valid_date_format, required=True, help="the \
            earliest date to look for results")
        self.parser_search_chat.add_argument("-e", "--date_end", type=valid_date_format, default="now", required=False,
                                             help="the latest date to look for results; defaults to 'now'")
        group = self.parser_search_chat.add_mutually_exclusive_group(required=True)
        group.add_argument("-q", "--query", type=str, action="append", dest="query", help="The query term to search")
        group.add_argument("-u", "--list", type=valid_list, dest="query", help="The Python list of \
            search terms to use")

    def display_help(self, command):
        self.parser.parse_args([command, "--help"])

    def parse_input(self, input, type):
        """ Parses the user's cell magic from Jupyter

            Keyword Arguments:
            input -- the entire contents of the cell from Jupyter

            Returns:
            parsed_input -- an object containing an error status, a message,
                and parsed command from argparse.parse()
        """

        # Prepare the response object to return to the calling function
        parsed_input = {
            "type": type,
            "error": False,
            "message": None,
            "input": {}
        }
        # Process line magics
        if type == "line":
            try:
                if len(input.strip().split("\n")) > 1:
                    parsed_input["error"] = True
                    parsed_input["message"] = r"The line magic is more than one line and shouldn't be. \
                        Try `%flashpoint --help` or `%flashpoint -h` for proper formatting"

                else:
                    parsed_user_command = self.line_parser.parse_args(shlex.split(input, posix=False))
                    print(parsed_user_command)
                    parsed_input["input"].update(vars(parsed_user_command))

            except SystemExit:
                parsed_input["error"] = True
                parsed_input["message"] = r"Invalid input received, see the output above. \
                    Try `%flashpoint --help` or `%flashpoint -h`"

        # Process cell magics
        if type == "cell":
            # Split the cell magic by newline
            split_user_input = input.strip().split("\n")

            try:
                if len(split_user_input) == 1:
                    parsed_user_command = self.cell_parser.parse_args(shlex.split(split_user_input[0], posix=False))

                    parsed_input["input"].update(vars(parsed_user_command))

                else:
                    parsed_input["error"] = True
                    parsed_input["message"] = (f"Cell magic contained {len(split_user_input)} lines, but should be"
                                               "exactly 1. Try `--help` or `-h`")
                    return parsed_input

                # Display help instead if the user included --help or -h in the 1st line of their cell magic
                if re.search(r"(\-h|\-\-help)", split_user_input[0]):
                    self.display_help(parsed_input["input"]["command"])

            except SystemExit:
                parsed_input["error"] = True
                parsed_input["message"] = "Invalid input received, see the output above. Try `--help` or `-h`"

            except Exception as e:
                parsed_input["error"] = True
                parsed_input["message"] = f"Exception while parsing user input: {e}"

        return parsed_input
