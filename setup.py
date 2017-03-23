from setuptools import setup, find_packages

from pokerserver.version import NAME, VERSION

requirements = [
    'tornado>=4.3',
    'requests>=2.13.0',
    'apispec>=0.20.0'
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
            'createpokerdb=pokerserver.applications.create_database:main',
            'clearpokerdb=pokerserver.applications.clear_database:main',
            'simpleclient=pokerserver.applications.simple_client:main',
            'pokercli=pokerserver.applications.poker_cli:main',
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    test_suite='nose.collector'
)
