import jsonpath_ng as jp
from flashpoint_utils.helper_functions import create_b64_image_string, format_b64_image_for_dataframe
import jupyter_integrations_utility as jiu


class ResponseParser:
    """
    A class to parse API responses from the Flashpoint API.
    Note: I follow this simple idiom: APIs return data. Formatting
        and parsing for use in the application happen separately (here)

    Attributes
    ----------
    None

    Methods
    -------
    _handler(issued_command, response):
        Brokers response parsing on behalf of the calling function.
    _find_value_by_path(path, json):
        Look up a value of a JSON object via JSONPath (jsonpath_ng)
    search_media(response):
        Flatten a media search API response from the Flashpoint API
        to be used in a dataframe.
    get_image(response):
        Convert a raw image bytes object to a hot-n-ready $5 HTML-ready object
    """
    def __init__(self):
        pass

    def _handler(self, issued_command: str, response: dict):
        """ Brokers response parsing on behalf of the calling function

            Keyword arguments:
            issued_command -- the command that the user executed, which
                represents a function name below (isn't that cool?)
            response -- the response object from the API call, which is
                a dict containing the original query, and response object

            Returns:
            Whatever is passed back to it. It's a broker. It don't care.

        """
        return getattr(self, issued_command)(response)

    def _find_value_by_path(self, path: str, json: dict):
        """ Look up a value of a JSON object via JSONPath (jsonpath_ng)
            Note: just going to leave this here for reference, if your JSON legitimately
                has special characters in it, like '/':
                https://stackoverflow.com/questions/62006612/jsonpath-ng-lexer-jsonpathlexererror-error-on-line-1-col-8-unexpected-charact

            Keyword arguments:
            path -- the JSON path to find in the JSON
            json -- the JSON to search through

            Returns:
            A string that represents one or more matches, separated by a comma
        """
        query = jp.parse(path)
        return (", ").join(match.value for match in query.find(json))

    def search_media(self, response):
        """ Flatten a media search API response from the Flashpoint API
            to be used in a dataframe.

            Keyword arguments:
            response -- the response object from the API call, which is
                a dict containing the original query, and response object

            Returns:
            flattened_response -- a flattened list of dictionaries to be
                used in a dataframe
        """

        original_query = response[0]
        response_json = response[1].json()
        hits = response_json["hits"]["hits"]

        flattened_response = []

        paths_to_extract = [
            "image_content",
            "_source.sort_date",
            "_source.title",
            "_source.media.fpid",
            "_source.body.['text/plain']",
            "_source.enrichments.v1.social_media[*].handle",
            "_source.enrichments.v1.social_media[*].site",
            "_source.enrichments.v1.urls[*].domain",
            "_source.media.md5",
            "_source.media.sha1",
            "_source.media.phash",
            "_source.container.fpid",
            "_source.media.storage_uri",
            "_source.site_actor.names.aliases[*]",
            "_source.site_actor.native_id",
            "_source.media_v2[0].image_enrichment.enrichments.v1.image-analysis.text[0].value"
        ]

        for hit in hits:
            row_to_add = {}
            for path in paths_to_extract:
                row_to_add.update({"query_term": original_query,
                                   path: self._find_value_by_path(path, hit)})
            flattened_response.append(row_to_add)

        return flattened_response

    def get_image(self, response):
        """ Convert a raw image bytes object to a hot-n-ready $5 HTML-ready object

            Keyword arguments:
            response -- the response object from the API call, which is
                a dict containing the original query, and response object

            Returns:
            An HTML-ready b64 string of the image
        """

        b64_img_data = create_b64_image_string(response[1].content)
        formatted_image = format_b64_image_for_dataframe(b64_img_data)

        return [b64_img_data, formatted_image]

    def search_chat(self, responses):

        response_list = []
        failed_requests = []

        for response in responses:
            if response[1].status_code == 200:
                results = response[1].json()

                # Flatten the response for dataframe purposes
                hits = results["hits"]["hits"]
                flattened_response = []
                paths_to_extract = [
                    "_source.fpid",
                    "_source.sort_date",
                    "_source.title",
                    "_source.body.['text/plain']",
                    "_source.enrichments.v1.social_media[*].handle",
                    "_source.enrichments.v1.social_media[*].site",
                    "_source.enrichments.v1.urls[*].domain",
                    "_source.container.fpid",
                    "_source.site_actor.names.aliases[*]",
                    "_source.site_actor.native_id",
                    "_source.site_actor.username",
                    "_source.container.native_id"
                ]

                for hit in hits:
                    row_to_add = {"search term": response[0]}
                    for path in paths_to_extract:
                        row_to_add.update({path: self._find_value_by_path(path, hit)})
                    flattened_response.append(row_to_add)

                response_list.extend(flattened_response)

            else:
                failed_requests.append(response[0])

        if failed_requests:
            jiu.display_error("The following requests failed and need to be resubmitted:")
            jiu.displayMD(str(failed_requests))

        return response_list
