from django.core.management.base import BaseCommand

from lzkb.health import health_payload_json


class Command(BaseCommand):
    help = 'Run LZKB health checks and exit non-zero when unhealthy.'

    def add_arguments(self, parser):
        parser.add_argument('--ready', action='store_true', help='Include dependency readiness checks.')
        parser.add_argument('--json', action='store_true', help='Print health payload as JSON.')

    def handle(self, *args, **options):
        payload, ok = health_payload_json(include_dependencies=options['ready'])
        if options['json']:
            self.stdout.write(payload)
        elif ok:
            self.stdout.write('ok')
        if not ok:
            raise SystemExit(1)
