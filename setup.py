from setuptools import setup, find_packages

from pokerserver.version import NAME, VERSION

requirements = [
    'tornado>=4.3',
    'aioodbc==0.0.2'
]

setup(
    name=NAME,
    version=VERSION,
    packages=find_packages(),
    author="Andreas Malecki",
    author_email="Andreas.Malecki@tngtech.com",
    description='Poker server for our Python workshop at TNG Technology Consulting.',
    license="GPLv3",
    url="https://github.com/MartinAltmayer/pokerserver",
    entry_points={
        'console_scripts': [
            'pokerserver=pokerserver.applications.server:main',
            'createpokerdb=pokerserver.applications.create_database:main'

        ]
    },
    install_requires=requirements,
    test_suite='nose.collector'
)
