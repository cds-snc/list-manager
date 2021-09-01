# Project template

This repository provides some base files for setting up a repository at
CDS.


## Development
Recommended: `devcontainer` extension for VSCode

To bring up your local dev environment, make sure you have install the requirements & run migrations:
```
make install
make install-dev
make migrations
```

Bring up the local dev environment:
```
make dev
```

## Load testing
The API contains a `locust` file to test a basic workflow:

1. Create list
2. Create subscriber
3. Confirm subscriber
4. Delete subscription
5. Delete list

You can start it by running `make load-test` in the `api` directory and the visiting: `http://localhost:8089/`. If you have started the dev server locally with `make dev` you can then run the load test against the API with the URL `http://localhost:8000/`.