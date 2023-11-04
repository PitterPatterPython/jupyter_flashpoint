import json
import requests
from utils.helper_functions import create_b64_image_string

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
    def __init__(self, host : str, token : str, proxies : dict = None, verify : bool = False):
        self.session = requests.Session()
        self.host = host
        self.session.verify = verify
        self.session.proxies = proxies
        self.session.headers = { 
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.payload_template = {
            "collapse_field": "media.sha1.keyword",
            "from": 0,
            "highlight_size": 250,
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
                "nist",
                "mitre",
                "source_uri",
                "Event.date",
                "Event.uuid",
                "Event.Attribute",
                "Event.Tag",
                "Event.attribute_count",
                "Event.RelatedEvent",
                "attack_ids",
                "category",
                "geolocation",
                "media.caption",
                "media.file_name",
                "media.md5",
                "media.fpid",
                "media.media_type",
                "media.mime_type",
                "media.phash",
                "media.sha1",
                "media.size",
                "media.storage_uri",
                "enrichments.card-numbers.card-numbers.bin",
                "enrichments.v1.ip_addresses.ip_address",
                "enrichments.v1.email_addresses.email_address",
                "enrichments.v1.urls.domain",
                "enrichments.v1.monero_addresses.monero_address",
                "enrichments.v1.ethereum_addresses.ethereum_address",
                "enrichments.v1.bitcoin_addresses.bitcoin_address",
                "enrichments.v1.social_media.handle",
                "enrichments.v1.social_media.site",
                "cve.nist",
                "cve.mitre",
                "cve.title",
                "enrichments.v1.vulnerability.cve.vulnerability"
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
            "native_id"
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
        return getattr(self,command)(**kwargs)
    
    def search_media(self, query, limit, days, images):
        """ Search Flashpoint for posts that contain media. Perform a subsequent query
            to retrieve the actual image, and add that to the data before returning it
            if the user asks for them.

            Keyword arguments:
            query -- (should be) the native Flashpoint query syntax
            limit -- the number of items to return
            days -- how many days to look back
            images -- a boolean to represent whether or not to perform a
                subsequent call to retrieve individual images.

            Returns:
            response -- a requests.Response object
        """
        
        url = f"https://{self.host}/all/search"
        
        query = self._escape_query(query)

        payload = {
            "size": limit,
            "query": fr"+({query}) +sort_date:[now-{days}d TO now] +basetypes:((chat AND message)) +_exists_:media.storage_uri +_exists_:media.image_enrichment.enrichments.v1.image-analysis"
        }
        
        payload = {**self.payload_template, **payload}
        
        response = self.session.post(url, data=json.dumps(payload))

        if images:
            # update the response object with response.content for each image
            json_copy = response.json()
            
            for idx, hit in enumerate(json_copy["hits"]["hits"]):
                image_download_response = self.get_image(json_copy["hits"]["hits"][idx]["_source"]["media"]["storage_uri"])
                image_content = create_b64_image_string(image_download_response.content)
                json_copy["hits"]["hits"][idx].update({"image_content": image_content})

            response._content = json.dumps(json_copy).encode()
            
            return response

        else:
            return response

    def get_image(self, query: str, **kwargs):
        """ Retrieve a single image from the Flashpoint API, 
            by _source.media.storage_uri.

            Keyword arguments:
            query -- the item to retrieve, this will be the 
                _source.media.storage_uri value from an item.

            Returns:
            response -- a requests.Response object
        """
        # We have to manually set this because Flashpoint has a 
        # separate API for "UI" things. Yes, I know, and I'm sorry.
        url = "https://fp.tools/ui/v4/media/assets"

        custom_headers = self.session.headers
        custom_headers["Content-Type"] = "image/jpeg"

        payload = {
            "asset_id" : query
        }

        return self.session.get(url, params=payload)
        