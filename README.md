# shorten-me
Simple url shortener.

## Implementation
Flask is used to serve the requests. This was chosen for its simplicity and
ease of use. SQLAlchemy was chosen to handle the models for the same reasons.
A bijective conversion was used to generate the shortened urls; for details
see: https://en.wikipedia.org/wiki/Bijection

## Endpoints
Two simple endpoints:
* "/" - [POST] which must be passed a "long_url" in the data. If the URL is 
valid it will be added to the database and a short URL generated.
* "/<str:short_url>" - [GET] the "short_url" is used to determine the database 
ID of the relevant link.

## Testing
Only basic unit tests have been included
