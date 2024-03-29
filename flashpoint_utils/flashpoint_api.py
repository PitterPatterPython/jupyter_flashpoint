import concurrent.futures
import json
import niquests
import time
from tqdm.notebook import tqdm
from flashpoint_utils.helper_functions import create_b64_image_string
import jupyter_integrations_utility as jiu


class FlashpointAPI:
    """
    A class to perform API requests to the Flashpoint API.

    Attributes
    ----------
    host -- the hostname of the Flashpoint API to be called
    token -- the API token of the user
    proxies -- a dictionary of proxies to use, if any
    verify -- whether or not to verify SSL

    Methods
    -------
    _escape_query(query):
        A general purpose function to handle certain problematic characters

    _handler(command, **kwargs):
        Brokers API calls on behalf of the calling function

    search_media(query, limit, days, images):
        Search Flashpoint for posts that contain media. Perform a subsequent query
        to retrieve the actual image, and add that to the data before returning it
        if the user asks for them.
    get_image(query, **kwargs):
        Retrieve a single image from the Flashpoint API, by _source.media.storage_uri

    """
    def __init__(self, host, token, proxies=None, verify=True, max_retries=3, max_workers=10):
        self.session = niquests.Session()
        self.max_workers = max_workers
        self.host = host
        self.token = token
        self.verify = verify
        self.session.proxies = proxies
        self.max_retries = max_retries
        self.media_assets_url = "https://fp.tools/ui/v4/media/assets"
        self.payload_template = {
            "collapse_field": "media.sha1.keyword",
            "from": 0,
            "track_total_hits": 10000,
            "traditional_query": True,
            "_source_includes": [
                "type",
                "value",
                "basetypes",
                "fpid",
                "sort_date",
                "breach",
                "domain",
                "affected_domain",
                "email",
                "password",
                "username",
                "is_fresh",
                "credential_record_fpid",
                "password_complexity",
                "ransomer.fpid",
                "ransomer.names",
                "container.fpid",
                "container.name",
                "container.title",
                "container.type",
                "container.native_id",
                "container.container.native_id",
                "container.container.title",
                "body.text/plain",
                "account_organization",
                "infected_host_attributes",
                "cookies",
                "email_domain",
                "prices",
                "site.title",
                "site.source_uri",
                "site_actor.native_id",
                "site_actor.names",
                "site_actor.username",
                "raw_href",
                "title",
                "base.title",
                "card_type",
                "bin",
                "source_uri",
                "attack_ids",
                "category",
                "geolocation",
                "media.caption",
                "media.file_name",
                "media.fpid",
                "media.media_type",
                "media.mime_type",
                "media.phash",
                "media.sha1",
                "media.size",
                "media_v2",
                "media.storage_uri",
                "enrichments.card-numbers.card-numbers.bin",
                "enrichments.v1.ip_addresses.ip_address",
                "enrichments.v1.email_addresses.email_address",
                "enrichments.v1.urls.domain",
                "enrichments.v1.monero_addresses.monero_address",
                "enrichments.v1.ethereum_addresses.ethereum_address",
                "enrichments.v1.bitcoin_addresses.bitcoin_address",
                "enrichments.v1.social_media.handle",
                "enrichments.v1.social_media.site"
            ],
            "highlight": False,
            "fields": [
                "enrichments",
                "body.text/html+sanitized",
                "body.text/plain",
                "user.names.handle",
                "site_actor.names.handle",
                "site_actor.names.aliases",
                "site_actor.fpid",
                "title",
                "container.fpid",
                "container.title",
                "container.container.title",
                "site.source_uri",
                "site.title",
                "native_id",
                "media_v2"
            ],
            "sort": [
                "sort_date:desc"
            ]
        }

    def _escape_query(self, query: str):
        """ A general purpose function to handle certain problematic characters

            Parameters:
            query -- the user's query

            Returns:
            query -- the updated query
        """
        query = query.replace('"', r'\"')

        return query

    def _handler(self, command: str, **kwargs):
        """ Brokers API calls on behalf of the calling function

            Keyword arguments:
            command -- the function of this class to run
            **kwargs -- additional arguments to pass along to functions
                (i.e. - limit, days, etc...)

            Returns:
            passes through a response object from one of the API calls executed
        """
        return getattr(self, command)(**kwargs)

    def _fetch(self, item, progress_bar=None):
        """Performs the web request on behalf of the underlying function

        Args:
            item (dict): a dictionary containing the url, query, payload, and headers
                to use in the niquests request
            progress_bar (tqdm.notebook.tqdm_notebook, optional): if the calling function is \
                using a progress bar, we can pass that object here and update it. Defaults to None.

        Returns:
            dict: a dictionary containing the original query term, and http response object
        """
        method = item["method"]
        url = item["url"]
        query = item["query"]
        payload = item["payload"]
        headers = item["headers"]

        retry_count = 0
        while retry_count <= self.max_retries:
            response = self.session.request(method,
                                            url,
                                            headers=headers,
                                            json=payload if method.lower() == "post" else None,
                                            params=payload if method.lower() == "get" else None,
                                            verify=self.verify)
            if response.status_code == 429:
                retry_count += 1
                if retry_count <= self.max_retries:
                    delay = 3 ** retry_count
                    time.sleep(delay)
                else:
                    if progress_bar:
                        progress_bar.update(1)
                    return query, response, 0
            elif response.status_code == 200:
                if "application/json" in response.headers.get("Content-Type"):
                    hits_count = len(response.json()["hits"]["hits"])
                else:
                    hits_count = 1

                if progress_bar:
                    progress_bar.update(1)
                return query, response, hits_count
            else:
                jiu.display_error(f"Request failed with status code {response.status_code} \
                    for search term {query}")
                break

    def _concurrent_fetches(self, items):
        """Asynchronously perform multiple HTTP requests

        Args:
            items (list): A list of dictionaries that include the method, url, query term \
                payload, and headers to use in each concurrent request

        Returns:
            list: a list of tuples representing the original query term and response object
                for each request
        """
        with tqdm(total=len(items),
                  unit="request",
                  desc="Processing",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} Elapsed time: {elapsed} Total Results: {postfix[0]}]",
                  postfix=[0]) as progress_bar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for item in items:
                    future = executor.submit(self._fetch, item, progress_bar)
                    futures.append(future)

                results = []
                total_hits = 0
                for future in concurrent.futures.as_completed(futures):
                    query, result, hits_count = future.result()
                    if result.status_code == 200:
                        total_hits += hits_count
                        progress_bar.postfix[0] = total_hits
                        progress_bar.update(0)
                    results.append((query, result, hits_count))
                    time.sleep(0.1)
        return results

    def search_media(self, query, limit, date_start, date_end, images, *args, **kwargs):
        """ Search Flashpoint for posts that contain media. Perform a subsequent query
            to retrieve the actual image, and add that to the data before returning it
            if the user asks for them.

            Keyword arguments:
            query -- (should be) the native Flashpoint query syntax
            limit -- the number of items to return
            date_start -- the earliest date to look for results
            date_end -- the latest date to look for results
            images -- a boolean to represent whether or not to perform a
                subsequent call to retrieve individual images.

            Returns:
            dict -- a dictionary containing the original query term, and http response object
        """

        url = f"https://{self.host}/all/search"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        payload = {
            "size": limit,
            "query": (fr"+({query}) +sort_date:[{date_start} TO {date_end}] +basetypes:((chat AND message))"
                      " +_exists_:media.storage_uri +_exists_:media.image_enrichment.enrichments.v1.image-analysis")
        }

        payload = {**self.payload_template, **payload}

        item = {
            "method": "post",
            "url": url,
            "query": query,
            "payload": payload,
            "headers": headers
        }

        with tqdm(total=1,
                  unit="request",
                  desc="Processing",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} Elapsed time:{elapsed} Total Results: {postfix[0]}]",
                  postfix=[0]) as progress_bar:

            response = self._fetch(item, progress_bar)

            # Add total hits to the progress bar and update it
            progress_bar.postfix[0] = response[2]
            progress_bar.update(0)

        if images:
            # update the response object with response.content for each image
            json_copy = response[1].json()

            # Create a list of payloads, and keep track of the index in json_copy["hits"]["hits"]
            # where the image should be associated to
            payloads = []
            for idx, hit in enumerate(json_copy["hits"]["hits"]):
                storage_uri = json_copy["hits"]["hits"][idx]["_source"]["media"]["storage_uri"]
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "image/jpeg"
                }
                payload = {
                    "asset_id": storage_uri
                }

                item = {
                    "method": "get",
                    "url": self.media_assets_url,
                    "query": idx,  # this is the current index in the ["hits"]["hits"]
                    "payload": payload,
                    "headers": headers
                }

                payloads.append(item)

            image_responses = self._concurrent_fetches(payloads)

            for img_response in image_responses:
                idx = img_response[0]
                image_content = create_b64_image_string(img_response[1].content)
                json_copy["hits"]["hits"][idx].update({"image_content": image_content})

            # Overlay the copy of the original response with the updated
            # content that contains the b64 image string for each image,
            # appropriately placed in the correct index/row of the ["hits"]["hits"]
            response[1]._content = json.dumps(json_copy).encode()

            return response

        else:
            return response

    def get_image(self, uri, **kwargs):
        """ Retrieve one or more images from the Flashpoint API by _source.media.storage_uri.

            Keyword arguments:
            uri (list) -- the items to retrieve, this will be the
                _source.media.storage_uri value from an item.

            Returns:
            (tup) -- a dictionary containing the original query term, and http response object
        """
        # We have to manually set this because Flashpoint has a
        # separate API for "UI" things. Yes, I know, and I'm sorry.
        url = self.media_assets_url

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "image/jpeg"
        }

        payloads = []
        for u in uri:
            payload = {
                "asset_id": uri
            }

            item = {
                "method": "get",
                "url": url,
                "query": uri,
                "payload": payload,
                "headers": headers
            }

            payloads.append(item)

        responses = self._concurrent_fetches(payloads)

        return responses

    def search_chat(self, query, limit, date_start, date_end, *args, **kwargs):
        """Search Flashpoint for chat messages that contain one or more keywords.

        Args:
            query (list): a list of search terms to search for
            limit (int): the number of results to return for each search term
            date_start (str): the start date represented in YYYY-MM-DD
            date_end (str): the end date represented in YYYY-MM-DD

        Returns:
            tup: (search term, response object, hit count)
        """

        url = f"https://{self.host}/all/search"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        payloads = []
        for q in query:
            payload = {
                "size": limit,
                "query": fr"+({q}) +sort_date:[{date_start} TO {date_end}] +basetypes:((chat AND message))"
            }

            payload.update(self.payload_template)

            item = {
                "method": "post",
                "url": url,
                "query": q,
                "payload": payload,
                "headers": headers
            }

            payloads.append(item)

        responses = self._concurrent_fetches(payloads)

        return responses
