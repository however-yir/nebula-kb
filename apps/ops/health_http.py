import argparse
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    server_version = 'NebulaHealth/1.0'

    def do_GET(self):
        if self.path in ('/healthz', '/healthz/'):
            self._write_health(include_dependencies=False)
            return
        if self.path in ('/readyz', '/readyz/'):
            self._write_health(include_dependencies=True)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt, *args):
        return

    def _write_health(self, include_dependencies):
        from nebula.health import health_payload_json

        body, ok = health_payload_json(include_dependencies=include_dependencies)
        status = HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE
        encoded = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main():
    parser = argparse.ArgumentParser(description='Nebula service health HTTP server')
    parser.add_argument('--host', default=os.environ.get('NEBULA_HEALTH_HOST', os.environ.get('LZKB_HEALTH_HOST', '0.0.0.0')))
    parser.add_argument('--port', type=int, default=int(os.environ.get('NEBULA_HEALTH_PORT', os.environ.get('LZKB_HEALTH_PORT', '8081'))))
    parser.add_argument('--role', default=os.environ.get('SERVER_NAME', 'worker'))
    args = parser.parse_args()

    os.environ.setdefault('SERVER_NAME', args.role)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nebula.settings')

    import django
    django.setup()

    server = ThreadingHTTPServer((args.host, args.port), HealthHandler)
    server.serve_forever()


if __name__ == '__main__':
    main()
