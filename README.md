# SatOP Ground station Client
The SatOP Ground Station Client (SatOP-GSC) is a linux based ground station implementation for the [SatOP Platform](https://github.com/discosat/satop-platform). The SatOP-GSC has been developed with [CSH](https://github.com/discosat/csh) in mind, and CSH commands can be scheduled to run in the future.

The client requires Linux, as it uses CSH, that only has build-instructions for Linux. 

To run the SatOP-GSC on OS'es differing from linux, a dockerfile is included to build an image of this repo.

## Run locally (Linux)

### Build CSH shared object

The integration with CSH is done with Python's `ctypes` module, that allows calling functions in a C-library from Python. 

Thus we need to build CSH as a shared object (.so) instead of an executable. One is already shipped as part of the repository, but depending on your installed version of libc, you might need to build it manually against your own version.

The branch [`AutoCSHLib` at discosat/CSH](https://github.com/discosat/csh/tree/AutoCSHLib) has this included in its meson build file, so follow the instructions in the repo there to build the `libcsh.so` and replace the existing one in `satop_gsc/csh/` with this. 

Remember to build from the correct branch, otherwise you won't get the .so file built.

```
# Install requirements (Debian/Ubuntu shown here)
sudo apt install libcurl4-openssl-dev git build-essential libsocketcan-dev can-utils libzmq3-dev libyaml-dev pkg-config fonts-powerline python3-pip libelf-dev libbsd-dev libprotobuf-c-dev
sudo pip3 install meson ninja

# Download the CSH sources and build
git clone --branch AutoCSHLib --recurse-submodules https://github.com/discosat/csh.git
cd csh
./configure
./install
```

### Starting

```
python3 satop_gsc/gs_client.py --host [platform host IP] --port [platform port (default 7890)]
```

Note that `[platform host IP]` and `[platform port (default 7890)]` are the the IP and port where the SatOP platform is accessible.


## Run in Docker

The included Dockerfile helps automate the building of CSH, and also allows running the ground station client on Windows. 

Open a terminal window and move into your copy of this directory, and run the following two commands: 
```
docker build -t satop_gs .
docker run --name satop_gs satop_gs --host [platform host IP] --port [platform port (default 7890)]
```

Note that `[platform host IP]` and `[platform port (default 7890)]` are the the IP and port where the SatOP platform is accessible.
