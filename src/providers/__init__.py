from urllib.parse import urlparse
from providers.default import DefaultProvider
from providers.infobae import InfobaeProvider

PROVIDER_MAPPING = {
    "infobae.com": InfobaeProvider,
}

def get_provider(config, url: str):
    domain = urlparse(url).netloc
    if domain.startswith("www."):
        domain = domain[4:]

    provider_class = PROVIDER_MAPPING.get(domain, DefaultProvider)
    return provider_class(config)
