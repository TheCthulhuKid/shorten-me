"""
Simple bijective conversion (https://en.wikipedia.org/wiki/Bijection) for
generating urls and retrieving their IDs.

One potential problem is that as the db is fairly empty the initial URLs will
be very short.

Ambiguous characters (0, 1, I, l, o, O) have been removed from the alphabet to
avoid confusion.
"""
# "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ" shuffled
ALPHABET: str = "DpYvf5uRng8kKAbrZXUH23cPdhzqam9xQB4ywjGEVtWiFMTJCse6LS7N"
BASE: int = len(ALPHABET)


def shorten(url_id: int) -> str:
    """
    Create a short url based off of the URLs db ID

    Parameters
    ----------
    url_id
        Database ID of given URL

    Returns
    -------
    Short string representation of the db ID
    """
    short_url: str = ""
    while url_id > 0:
        short_url = ALPHABET[url_id % BASE] + short_url
        url_id //= BASE

    return short_url


def embiggen(short_url: str) -> int:
    """
    Given a short URL return a potential db ID

    Parameters
    ----------
    short_url
        Short string which identifies the database ID

    Returns
    -------
    Integer of potential database ID
    """
    url_id: int = 0
    try:
        for char in short_url:
            url_id = url_id * BASE + ALPHABET.index(char)
    except ValueError:  # if a character not in the alphabet is in the url
        pass

    return url_id
