#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import io
import base64
import json
import pickle
import logging
from api.utils.common import bytes_to_string, string_to_bytes


def serialize_b64(src, to_str=False):
    """Serialize data using JSON (safe) with base64 encoding.
    Falls back to pickle only for non-JSON-serializable objects (deprecated).
    """
    try:
        dest = base64.b64encode(json.dumps(src, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        logging.warning("SECURITY: serialize_b64 falling back to pickle for non-JSON data — migrate to JSON-safe types")
        dest = base64.b64encode(pickle.dumps(src))
    if not to_str:
        return dest
    else:
        return bytes_to_string(dest)


def deserialize_b64(src):
    """Deserialize base64-encoded data. Tries JSON first (safe), then pickle (deprecated)."""
    raw = base64.b64decode(string_to_bytes(src) if isinstance(src, str) else src)
    # Try JSON first (preferred, safe)
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    # Legacy pickle fallback — only allow safe types
    logging.warning("SECURITY: deserialize_b64 using pickle fallback — data should be migrated to JSON format")
    safe_module_whitelist = {"rag_flow"}
    class _SafeUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            if module.split('.')[0] in safe_module_whitelist:
                import importlib
                return getattr(importlib.import_module(module), name)
            raise pickle.UnpicklingError("global '%s.%s' is forbidden" % (module, name))
    return _SafeUnpickler(io.BytesIO(raw)).load()
