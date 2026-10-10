from pokemon_go_collection.sources import http as http_m


def post_webhook_message(webhook_url, content):
    """Post `content` to the channel of a Discord webhook, mentioning nobody."""
    http_m.fetch_json(
        webhook_url, body={"content": content, "allowed_mentions": {"parse": []}}
    )
