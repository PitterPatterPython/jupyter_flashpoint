import argparse
from utils.flashpoint_api import FlashpointAPI

class UserInputParser(argparse.ArgumentParser):
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
        self.parser = argparse.ArgumentParser(
            prog = "flashpoint",
            usage = f"""\n%%%%flashpoint instance [inst]\n[command] [flags]\n[query]"""
        )
        self.parser.add_argument("command", type=str, choices=self.valid_commands)
        self.parser.add_argument("-l", "--limit", type=int, default=25)
        self.parser.add_argument("-d", "--days", type=int, default=7)
        self.parser.add_argument("--images", action=argparse.BooleanOptionalAction)

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

        if len(split_user_input) != 2:
            parsed_input["error"] = True
            parsed_input["message"] = "Didn't receive the expected number of lines in your cell magic"

        else:
            try:
                parsed_user_command = self.parser.parse_args(split_user_input[0].split())
                parsed_user_query = split_user_input[1]

                parsed_input["input"].update(vars(parsed_user_command))
                parsed_input["input"].update({"query" : parsed_user_query})

            except SystemExit:
                parsed_input["error"] = True
                parsed_input["message"] = "Invalid input received."

        return parsed_input