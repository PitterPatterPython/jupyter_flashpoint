import argparse

class UserInputParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.valid_commands = [
            "search_images"
        ]
        self.parser = argparse.ArgumentParser(
            prog = "flashpoint",
            usage = """\n%%%%flashpoint instance [inst]\n[command] [flags]\n[query]"""
        )
        self.parser.add_argument("command", type=str, choices=self.valid_commands)
        self.parser.add_argument("-l", "--limit", type=int, default=25)
        self.parser.add_argument("-d", "--days", type=int, default=7)

    def parse_input(self, input: str):
        """
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