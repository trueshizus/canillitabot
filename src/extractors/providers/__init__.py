from urllib.parse import urlparse
from src.extractors.providers.default import DefaultProvider
from src.extractors.providers.infobae import InfobaeProvider

PROVIDER_MAPPING = {
    "infobae.com": InfobaeProvider,
}

def get_provider(config, url: str):
    domain = urlparse(url).netloc
    if domain.startswith("www."):
        domain = domain[4:]

    provider_class = PROVIDER_MAPPING.get(domain, DefaultProvider)
    return provider_class(config)
