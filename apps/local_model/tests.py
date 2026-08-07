import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import AuthenticationFailed

from lzkb.const import CONFIG


class LocalModelAuthTests(SimpleTestCase):
    def test_missing_internal_token_is_rejected(self):
        from local_model.auth import LocalModelAuthentication

        request = MagicMock()
        request.headers.get.return_value = ""

        with self.assertRaises(AuthenticationFailed):
            LocalModelAuthentication().authenticate(request)

    def test_configured_internal_token_is_accepted(self):
        from local_model.auth import LocalModelAuthentication

        request = MagicMock()
        request.headers.get.return_value = "test-local-model-token"

        with patch.dict(CONFIG, {"LOCAL_MODEL_AUTH_TOKEN": "test-local-model-token"}):
            result = LocalModelAuthentication().authenticate(request)

        self.assertEqual(result[1], "test-local-model-token")


class LocalModelApplyTests(SimpleTestCase):
    def test_unload_delegates_to_unload_operation(self):
        from local_model.views.model_apply import LocalModelApply

        with patch("local_model.views.model_apply.ModelApplySerializers") as serializer_class:
            serializer_class.return_value.unload.return_value = True
            result = LocalModelApply.Unload().post(MagicMock(data={}), "model-1")

        serializer_class.assert_called_once_with(data={"model_id": "model-1"})
        serializer_class.return_value.unload.assert_called_once_with()
        self.assertEqual(json.loads(result.content)["code"], 200)
