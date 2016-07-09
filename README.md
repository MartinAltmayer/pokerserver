# Pokerserver for our Python Workshop at TNG Technology Consulting

[![Build Status](https://travis-ci.org/MartinAltmayer/pokerserver.png)](https://travis-ci.org/MartinAltmayer/pokerserver)
## Requirements

The server has several external dependencies for database access and message queuing:

- unixodbc (used by aioodbc via pyodbc).
- sqliteodbc (SQLite3 driver).

### Installation of Dependencies Under Max OS X

    brew update
    brew install unixodbc sqliteodbc

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

Create the required SQLite database by running
    
    createpokerdb [<database file>]
    
You can omit the database file parameter to create a database with the default name `poker.db`.

Simply call the pokerserver script that was generated during package installation:
    
    pokerserver
    
Use `pokerserver --help` to see a full list of available parameters.
    
## Development Setup

Make sure you have virtualenvwrapper installed. The following command creates a virtual environment called pokerserver 
and installs the whole package including its requirements:

    ./mkvenv.sh
    
Afterwards you can activate the environment using

    workon pokerserver
    
