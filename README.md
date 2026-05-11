# Steam Achievement Tracker

[![Pipelines](https://github.com/DenZen1988/steam-achievement-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/DenZen1988/steam-achievement-tracker/actions/workflows/ci.yml)

## Table Of Content

* [Quickstart](#quickstart)
  * [Requirements](#requirements)
  * [Run the app](#run-the-app)
  * [Known Limitations](#known-limitations)
* [Development](#development)
  * [Needed packages](#needed-packages)
  * [Run the app locally](#run-the-app-locally)
* [Feature Requests & Bugs](#feature-requests--bugs)
* [License](#license)
* [Author](#author)
* [Versioning](#versioning)
* [Contribution](#contribution)

## Quickstart

### Requirements

* A steam API key - get it from [steam](https://steamcommunity.com/dev/apikey)!
* Your steam64 user ID - get it [via this site](https://steamid.xyz/)!
* docker
* docker compose
* docker buildx plugin
* nginx (as optional reverse proxy)

### Run the app

1. Make sure you installed the [requirements](#requirements)
2. Copy the `docker-compose.yml`, `Dockerfile` and the `app` folder onto your machine (server, raspberry pi, workstation)
3. Copy the example `.env` file into the same directory and rename it to `.env`
4. Adjust the settings within the `.env` file to your needs
5. Start the container with `docker compose up -d`
6. Setup nginx as reverse proxy (optional: see examples/nginx/vhost.conf.example)

After the setup is done the app will listen on port 8080 by default. You can switch that by using nginx as reverse proxy or by setting the
port differently in the `docker-compose.yml`.

### Known Limitations

> [!WARNING]
> Be aware that the steam api has a rate limiting og 100k requests per day!
> This might affect you if you have an extreme steam library (10k+ games) or if you setup the sync interval too frequently.

## Development

### Needed packages

The following packages are need for running the app locally for development:

* [python3](https://www.python.org/downloads/)
* [nicegui](https://nicegui.io/)
* [requests](https://pypi.org/project/requests/)
* [python-dotenv](https://pypi.org/project/dotenv/)

To install the requirements use this command:

Mac OS X:

```bash
pip3 install -r requirements.txt --break-system-packages
```

Linux:

```bash
pip3 install -r requirements.txt
```

### Run the app locally

To run the app locally for testing use this command:

```bash

python3 -m apps/dashboard.py
```

## Feature Requests & Bugs

If you have feature requests or want to report a bug please use the [github issues](https://github.com/DenZen1988/steam-achievement-tracker/issues).
This is a one-man-project so far and I do it my free time.

I will try to look at the github issues as soon as possible. :)

## License

[MIT](./LICENSE)

## Author

Denis Walther — [GitHub](https://github.com/DenZen1988)

## Versioning

The versioning follows the simple pattern of counting up from 0.0.1. Nothing fancy here.

## Contribution

You are more than welcome to create pull requests for new features and functions:

1. Create a new branch
2. Adjust or add the code desired
3. Ensure the pipelines are green
4. Create a PR
