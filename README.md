# Pokerserver for our Python Workshop at TNG Technology Consulting

## Requirements

The server has several external dependencies for database access:

- unixodbc (used by aioodbc via pyodbc).
- sqliteodbc (SQLite3 driver).

### Installation of Dependencies Under Max OS X

    brew install unixodbc
    brew install sqliteodbc

Add the SQLite3 driver to `~/odbcinst.ini`:

    [SQLite3]
    Description=SQLite3 ODBC Driver
    Driver=/usr/local/lib/libsqlite3odbc.so
    Setup=/usr/local/lib/libsqlite3odbc.so
    Threading=2
    
More information with respect to the correct configuration of the odbc drivers can be found at 
<http://www.ch-werner.de/sqliteodbc/html/index.htm>.

## PIP Package Installation

    python setup.py install
    
## Running the server

Simply call the generated script:
    
    pokerserver
    
## Development Setup

Make sure you have virtualenvwrapper installed. The following command creates a virtual environment called pokerserver 
and installs the whole package including its requirements:

    ./mkvenv.sh
    
Afterwards you can activate the environment using

    workon pokerserver
    
