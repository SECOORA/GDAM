# Glider Database Alternative - Mongo (GDAM)

A MongoDB store for Teledyne Webb Gliders.

### Usage

The project watches diretories for raw data files and inserts the data into
a MongoDB and then publishes to a ZeroMQ socket that new data was found.

```
gdam-cli --help
```

You can specify the ZeroMQ docker and MongoDB connection via command line
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
