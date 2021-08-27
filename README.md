# Project template

This repository provides some base files for setting up a repository at
CDS.


# Development
Recommended: `devcontainer` extension for VSCode

To bring up your local dev environment, make sure you have install the requirements & run migrations:
```
make install
make install-dev
cd api && make migrations && cd ../
```

Bring up the local dev environment:
```
make dev
```

Currently, we append the `/v1` for our deployment, but locally you don't need this. So to view the docs, you have to change `api.py` from:
```
app = FastAPI(root_path="/v1")
```
to:
```
app = FastAPI(root_path="/")
```