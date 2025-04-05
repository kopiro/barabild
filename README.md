# BaraBild

A simple web server that searches Getty Images website and returns the first image found as a direct link. Includes disk caching to improve performance and reduce requests to Getty Images.

## API

`/search/{keyword}`

Returns a redirect response to the first image found for the given keyword on Getty Images.
