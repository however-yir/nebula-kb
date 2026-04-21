# coding=utf-8

import base64
import os
from typing import Dict

from tencentcloud.asr.v20190614 import asr_client, models
from tencentcloud.common import credential

from models_provider.base_model_provider import LZKBBaseModel
from models_provider.impl.base_stt import BaseSpeechToText

_SUPPORTED_VOICE_FORMATS = {'wav', 'pcm', 'ogg-opus', 'speex', 'silk', 'mp3', 'm4a', 'aac', 'amr'}


class TencentSpeechToText(LZKBBaseModel, BaseSpeechToText):
    hunyuan_secret_id: str
    hunyuan_secret_key: str
    region: str
    model: str
    params: dict

    @staticmethod
    def is_cache_model():
        return False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hunyuan_secret_id = kwargs.get('hunyuan_secret_id')
        self.hunyuan_secret_key = kwargs.get('hunyuan_secret_key')
        self.region = kwargs.get('region') or 'ap-guangzhou'
        self.model = kwargs.get('model')
        self.params = kwargs.get('params') or {}

    @staticmethod
    def new_instance(model_type, model_name, model_credential: Dict[str, object], **model_kwargs):
        optional_params = LZKBBaseModel.filter_optional_params(model_kwargs)
        return TencentSpeechToText(
            model=model_name,
            hunyuan_secret_id=model_credential.get('hunyuan_secret_id'),
            hunyuan_secret_key=model_credential.get('hunyuan_secret_key'),
            region=model_credential.get('region', 'ap-guangzhou'),
            params=optional_params,
        )

    def _build_client(self):
        cred = credential.Credential(self.hunyuan_secret_id, self.hunyuan_secret_key)
        return asr_client.AsrClient(cred, self.region)

    @staticmethod
    def _safe_int(value, default_value):
        if value is None:
            return default_value
        try:
            return int(value)
        except (TypeError, ValueError):
            return default_value

    def _detect_voice_format(self, audio_file):
        voice_format = self.params.get('voice_format')
        if isinstance(voice_format, str) and voice_format.lower() in _SUPPORTED_VOICE_FORMATS:
            return voice_format.lower()

        filename = getattr(audio_file, 'name', '')
        if isinstance(filename, str) and '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            if ext in _SUPPORTED_VOICE_FORMATS:
                return ext

        content_type = getattr(audio_file, 'content_type', '')
        if isinstance(content_type, str) and '/' in content_type:
            subtype = content_type.split('/', 1)[1].lower()
            if subtype in _SUPPORTED_VOICE_FORMATS:
                return subtype

        return 'mp3'

    def _build_sentence_request(self, audio_data: bytes, voice_format: str):
        request = models.SentenceRecognitionRequest()
        request.EngSerViceType = self.params.get('eng_service_type', '16k_zh')
        request.SourceType = 1
        request.VoiceFormat = voice_format
        request.Data = base64.b64encode(audio_data).decode('utf-8')
        request.DataLen = len(audio_data)

        request.WordInfo = self._safe_int(self.params.get('word_info'), 0)
        request.FilterDirty = self._safe_int(self.params.get('filter_dirty'), 0)
        request.FilterPunc = self._safe_int(self.params.get('filter_punc'), 0)
        request.ConvertNumMode = self._safe_int(self.params.get('convert_num_mode'), 1)
        request.ProjectId = 0
        return request

    def check_auth(self):
        client = self._build_client()
        request = models.GetAsrVocabListRequest()
        request.Offset = 0
        request.Limit = 1
        client.GetAsrVocabList(request)

    def speech_to_text(self, audio_file):
        if audio_file is None:
            raise ValueError('audio_file is required')

        if hasattr(audio_file, 'seek'):
            audio_file.seek(0)

        audio_data = audio_file.read()
        if not audio_data:
            raise ValueError('audio_file is empty')

        voice_format = self._detect_voice_format(audio_file)
        request = self._build_sentence_request(audio_data, voice_format)
        response = self._build_client().SentenceRecognition(request)
        return (response.Result or '').strip()
