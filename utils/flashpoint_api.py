import requests
import json

class FlashpointAPI:
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

    def escape_query(self, query: str):
        query = query.replace('"', r'\"')

        return query
    
    def handler(self, command: str, limit: int, days: str, query: str):
        return getattr(self,command)(query, limit, days)
    
    def search_images(self, query: str, limit: int, days: str):
        url = f"https://{self.host}/all/search"
        
        query = self.escape_query(query)

        payload = {
            "size": limit,
            "query": fr"+({query}) +sort_date:[now-{days}d TO now] +basetypes:((chat AND message)) +_exists_:media.storage_uri +_exists_:media.image_enrichment.enrichments.v1.image-analysis"
        }
        
        payload = {**self.payload_template, **payload}
        
        return self.session.post(url, data=json.dumps(payload))
        