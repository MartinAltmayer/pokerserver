from tornado.web import RequestHandler


class IndexController(RequestHandler):
    route = r'/'

    async def get(self):
        self.write(HTML)


HTML = """<!doctype html>
<html>
  <head>
  </head>
  <body>
    <div class="app"></div>
    <script src="static/client-bundle.js"></script>
  </body>
</html>"""
