from apispec import APISpec

from ..version import DESCRIPTION, NAME, VERSION

API_SPECIFICATION = APISpec(
    title=NAME,
    version=VERSION,
    info=dict(
        description=DESCRIPTION
    ),
    plugins=['apispec.ext.tornado']
)
