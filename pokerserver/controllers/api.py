from tornado.web import RequestHandler

from pokerserver.api import API_SPECIFICATION


class ApiController(RequestHandler):
    route = r'/swagger.json'

    async def get(self):
        """Endpoint for OpenAPI specification.
        ---
        description: Returns the OpenAPI/Swagger specification.
        responses:
            200:
                description: Successful operation.
        """
        self.write(API_SPECIFICATION.to_dict())


class ApiDocsController(RequestHandler):
    route = r'/?$'

    async def get(self):
        """Root endpoint.
        ---
        description: Root endpoint.
        responses:
            301:
                description: Redirects to API documentation.
        """
        self.redirect('/static/api-docs/index.html?url=/swagger.json')
