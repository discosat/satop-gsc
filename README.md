# satop-gsc
Ground Station Client for the SatOP Platform


## Run in docker

```
docker build -t satop_gs .
docker run --name satop_gs satop_gs --host [platform host IP] --port [platform port (default 7890)]
```