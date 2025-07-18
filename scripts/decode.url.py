#!/usr/bin/env python3
import urllib.parse

def decode_url(url):
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Extract query parameters
    params = urllib.parse.parse_qs(parsed_url.query)

    # Print results
    print("Decoded URL Parameters:")
    for key, value in params.items():
        # parse_qs returns list of values per key
        print(f"{key} = {', '.join(value)}")

# Example usage
if __name__ == "__main__":
    test_url = input("Enter the URL to decode: ")
    decode_url(test_url)

