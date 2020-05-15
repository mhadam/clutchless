from clutch import Client

client = Client()
response = client.torrent.accessor(fields=['id']).dict(exclude_none=True)
try:
    ids = {int(torrent['id']) for torrent in response['arguments']['torrents']}
    client.torrent.remove(ids=ids)
    print('Remove torrents successfully')
except KeyError:
    print('KeyError - probably no torrents are loaded in client')
