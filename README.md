# Pokerserver for our Python Workshop at TNG Technology Consulting

## Requirements

The server has several external dependencies for database access and message queuing:

- unixodbc (used by aioodbc via pyodbc).
- sqliteodbc (SQLite3 driver).
- rabbitmq.

### Installation of Dependencies Under Max OS X

    brew update
    brew install unixodbc sqliteodbc rabbitmq

Add the SQLite3 driver to `~/odbcinst.ini`:

    [SQLite3]
    Description=SQLite3 ODBC Driver
    Driver=/usr/local/lib/libsqlite3odbc.so
    Setup=/usr/local/lib/libsqlite3odbc.so
    Threading=2
    
More information with respect to the correct configuration of the odbc drivers can be found at 
<http://www.ch-werner.de/sqliteodbc/html/index.html>.

## PIP Package Installation

    python setup.py install
    
## Running the server

Ensure that the RabbitMQ server is running. On Mac OS X, you can start it via

    /usr/local/sbin/rabbitmq-server
    
The location of the server executable is valid for the Homebrew-based install on Mac OS X and may differ for other 
operating systems.

On Debian Linux the RabbitMQ is installed as a service an can be started using

    service rabbitmq-server start

Then simply call the pokerserver script that was generated during package installation:
    
    pokerserver
    
## Development Setup

Make sure you have virtualenvwrapper installed. The following command creates a virtual environment called pokerserver 
and installs the whole package including its requirements:

    ./mkvenv.sh
    
Afterwards you can activate the environment using

    workon pokerserver
    
