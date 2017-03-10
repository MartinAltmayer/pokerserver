# Pokerserver for our Python Workshop at TNG Technology Consulting

[![Build Status](https://travis-ci.org/MartinAltmayer/pokerserver.png)](https://travis-ci.org/MartinAltmayer/pokerserver)

## Building the Frontend

    npm install
    gulp build

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
   
## Attributions
We use card images from https://github.com/notpeter/Vector-Playing-Cards which are released into the public domain.
