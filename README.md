# satop-gsc
The SatOP Ground Station Client (SatOP-GSC) is a linux based ground station implementation for the SatOP Platform (ref satop repo). The SatOP-GSC has been developed with CSP (insert ref?) in mind, in the form of the AutoCSH module (is it called this?).

To run the SatOP-GSC on OS'es differing from linux, a dockerfile is included to build an image of this repo.

## Run in docker
Open a terminal window and move into your copy of this directory, and run the following two commands: 
```
docker build -t satop_gs .
docker run --name satop_gs satop_gs --host [platform host IP] --port [platform port (default 7890)]
```

Note that ```[platform host IP]``` and ``[platform port (default 7890)]``` are the the IP and port where the SatOP platform is accessible.
