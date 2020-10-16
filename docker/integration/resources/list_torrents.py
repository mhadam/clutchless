from clutch import Client
from pprint import pprint

client = Client()
pprint(
    client.torrent.accessor(fields=["id", "name", "download_dir", "percent_done"]).dict(
        exclude_none=True
    )
)
