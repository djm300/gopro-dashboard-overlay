#!/usr/bin/env python3

import argparse

import requests

def list_versions(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    data = response.json()
    return sorted(data['releases'].keys(), reverse=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Ensure version not released")
    parser.add_argument("version", help="The Version")

    args = parser.parse_args()

    versions = list_versions('gopro-overlay')

    if args.version in versions:
        print(f"Version {args.version} already released")
        exit(1)

