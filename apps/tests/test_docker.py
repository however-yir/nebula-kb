import os
from django.test import SimpleTestCase


class DockerfileTests(SimpleTestCase):
    def _read_dockerfile(self):
        dockerfile_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'deploy', 'Dockerfile.runtime'
        )
        with open(dockerfile_path) as f:
            return f.read()

    def test_dockerfile_has_user_directive(self):
        content = self._read_dockerfile()
        self.assertIn('USER nebula', content)

    def test_dockerfile_not_root_last(self):
        content = self._read_dockerfile()
        lines = content.strip().split('\n')
        user_lines = [l.strip() for l in lines if l.strip().startswith('USER')]
        self.assertTrue(len(user_lines) > 0)
        self.assertEqual(user_lines[-1], 'USER nebula')

    def test_dockerfile_has_groupadd(self):
        content = self._read_dockerfile()
        self.assertIn('groupadd', content)
        self.assertIn('useradd', content)
