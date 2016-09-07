# Glider Database Alternative - Mongo (GDAM)

Watches a directory for new *db flight/science files and inserts the data into a MongoDB instance and then publishes the data to a ZeroMQ socket.


## Installation

#### CLI

Available through [`conda`](http://conda.pydata.org/docs/install/quick.html). This library requires Python 3.5 or above.

```
conda create -n sgs python=3.5
source activate sgs
conda install -c axiom-data-science gdam
```

#### Docker

Available through [`axiom/GDAM`](#).


## Basic Usage

#### CLI

```bash
$ gdam-cli --help
```

You can specify the ZeroMQ socket and MongoDB connection via command line
arguments or environmental variables:

```bash
$ gdam-cli -d /data --zmg_url tcp://127.0.0.1:9000 --mongo_url mongodb://localhost:27017
Watching /data
Inserting into mongodb://localhost:27017
Publishing to tcp://127.0.0.1:9000
```

```bash
$ export ZMQ_URL="tcp://127.0.0.1:9000"
$ export MONGO_URL="mongodb://localhost:27017"
$ gdam-cli -d /data
Watching /data
Inserting into mongodb://localhost:27017
Publishing to tcp://127.0.0.1:9000
```

```bash
$ ZMQ_URL="tcp://127.0.0.1:9000" MONGO_URL="mongodb://localhost:27017" gdam-cli -d /data
Watching /data
Inserting into mongodb://localhost:27017
Publishing to tcp://127.0.0.1:9000
```

#### Docker

The docker image uses `gdam-cli` internally. Set the `ZMQ_URL` and `MONGO_URL` variables as needed when calling `docker run`. You most likely want to keep `ZQM_URL` to the default unless you want to change the default port from `44444`.

```bash
$ docker run -it \
    -name sgs-gdam \
    -v "ZMQ_URL=tcp://127.0.0.1:9000" \
    -v "MONGO_URL=mongodb://localhost:27017" \
    axiom/gdam
Watching /data
Inserting into mongodb://localhost:27017
Publishing to tcp://127.0.0.1:9000
```

See the `docker-compose.yml` file in the source root for a working MongoDB/GDAM stack.


# SECOORA Glider System (SGS)

This package is part of the SECOORA Glider System (SGS) and was originally developed by the [CMS Ocean Technology Group](http://www.marine.usf.edu/COT/) at the University of South Florida. It is now maintained by [SECOORA](http://secoora.org) and [Axiom Data Science](http://axiomdatascience.com).

##### SGS Libraries

* [GDBR](https://github.com/axiom-data-science/GBDR): Reads and merges Teledyne Webb Slocum Glider data from *bd flight and science files.
* [GUTILS](https://github.com/axiom-data-science/GUTILS): A set of Python utilities for post processing glider data.
* [GNCW](https://github.com/axiom-data-science/GNCW): A library for creating NetCDF files for Teledyne Slocum Glider datasets.

##### SGS Applications

* [GSPS](https://github.com/axiom-data-science/GSPS): Watches a directory for new *db flight/science files and publishes the data to a ZeroMQ socket.
* [GDAM](https://github.com/axiom-data-science/GDAM): Watches a directory for new *db flight/science files and inserts the data into a MongoDB instance and then publishes the data to a ZeroMQ socket.
* [GSPS2NC](https://github.com/axiom-data-science/GSPS2NC): Subscribes to a  GSPS publishing socket and outputs NetCDF files.
