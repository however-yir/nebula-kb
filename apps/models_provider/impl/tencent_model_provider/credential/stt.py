# coding=utf-8

from django.utils.translation import gettext_lazy as _, gettext

from common import forms
from common.exception.app_exception import AppApiException
from common.forms import BaseForm, TooltipLabel
from common.utils.logger import maxkb_logger
from models_provider.base_model_provider import BaseModelCredential, ValidCode


class TencentSTTModelParams(BaseForm):
    eng_service_type = forms.SingleSelect(
        TooltipLabel(
            _('ASR engine type'),
            _('Engine model for sentence recognition. Default is 16k_zh.')
        ),
        required=True,
        default_value='16k_zh',
        option_list=[
            {'value': '16k_zh', 'label': _('Chinese (General)')},
            {'value': '16k_zh-PY', 'label': _('Chinese + English + Cantonese')},
            {'value': '16k_en', 'label': _('English')},
            {'value': '16k_yue', 'label': _('Cantonese')},
            {'value': '16k_ja', 'label': _('Japanese')},
            {'value': '16k_ko', 'label': _('Korean')},
            {'value': '16k_vi', 'label': _('Vietnamese')},
            {'value': '16k_ms', 'label': _('Malay')},
            {'value': '16k_id', 'label': _('Indonesian')},
            {'value': '16k_fil', 'label': _('Filipino')},
            {'value': '16k_th', 'label': _('Thai')},
            {'value': '16k_pt', 'label': _('Portuguese')},
            {'value': '16k_tr', 'label': _('Turkish')},
            {'value': '16k_ar', 'label': _('Arabic')},
            {'value': '16k_hi', 'label': _('Hindi')},
            {'value': '16k_fr', 'label': _('French')},
            {'value': '16k_de', 'label': _('German')},
            {'value': '16k_zh_dialect', 'label': _('Chinese Dialects')},
        ],
        value_field='value',
        text_field='label'
    )
    word_info = forms.SingleSelect(
        TooltipLabel(
            _('Word timestamp'),
            _('Whether to return word-level timestamps.')
        ),
        required=True,
        default_value='0',
        option_list=[
            {'value': '0', 'label': _('Disable')},
            {'value': '1', 'label': _('Enable (without punctuation)')},
            {'value': '2', 'label': _('Enable (with punctuation)')},
        ],
        value_field='value',
        text_field='label'
    )
    filter_dirty = forms.SingleSelect(
        TooltipLabel(
            _('Dirty word filtering'),
            _('Filter dirty words in recognition result.')
        ),
        required=True,
        default_value='0',
        option_list=[
            {'value': '0', 'label': _('Disable')},
            {'value': '1', 'label': _('Enable')},
            {'value': '2', 'label': _('Replace with *')},
        ],
        value_field='value',
        text_field='label'
    )
    filter_punc = forms.SingleSelect(
        TooltipLabel(
            _('Punctuation filtering'),
            _('Filter punctuation in recognition result.')
        ),
        required=True,
        default_value='0',
        option_list=[
            {'value': '0', 'label': _('Disable')},
            {'value': '1', 'label': _('Filter sentence-ending punctuation')},
            {'value': '2', 'label': _('Filter all punctuation')},
        ],
        value_field='value',
        text_field='label'
    )
    convert_num_mode = forms.SingleSelect(
        TooltipLabel(
            _('Number conversion'),
            _('Convert Chinese numerals to Arabic numerals.')
        ),
        required=True,
        default_value='1',
        option_list=[
            {'value': '0', 'label': _('Disable')},
            {'value': '1', 'label': _('Enable')},
        ],
        value_field='value',
        text_field='label'
    )


class TencentSTTModelCredential(BaseForm, BaseModelCredential):
    REQUIRED_FIELDS = ['hunyuan_secret_id', 'hunyuan_secret_key']

    @classmethod
    def _validate_model_type(cls, model_type, provider, raise_exception=False):
        if not any(mt['value'] == model_type for mt in provider.get_model_type_list()):
            if raise_exception:
                raise AppApiException(
                    ValidCode.valid_error.value,
                    gettext('{model_type} Model type is not supported').format(model_type=model_type)
                )
            return False
        return True

    @classmethod
    def _validate_credential_fields(cls, model_credential, raise_exception=False):
        missing_keys = [key for key in cls.REQUIRED_FIELDS if key not in model_credential]
        if missing_keys:
            if raise_exception:
                raise AppApiException(
                    ValidCode.valid_error.value,
                    gettext('{keys} is required').format(keys=', '.join(missing_keys))
                )
            return False
        return True

    def is_valid(self, model_type, model_name, model_credential, model_params, provider, raise_exception=False):
        if not (
            self._validate_model_type(model_type, provider, raise_exception)
            and self._validate_credential_fields(model_credential, raise_exception)
        ):
            return False

        try:
            model = provider.get_model(model_type, model_name, model_credential, **model_params)
            model.check_auth()
        except Exception as e:
            maxkb_logger.error(f'Exception: {e}', exc_info=True)
            if raise_exception:
                raise AppApiException(
                    ValidCode.valid_error.value,
                    gettext('Verification failed, please check whether the parameters are correct: {error}').format(
                        error=str(e)
                    )
                )
            return False
        return True

    def encryption_dict(self, model):
        return {**model, 'hunyuan_secret_key': super().encryption(model.get('hunyuan_secret_key', ''))}

    hunyuan_secret_id = forms.PasswordInputField('SecretId', required=True)
    hunyuan_secret_key = forms.PasswordInputField('SecretKey', required=True)
    region = forms.TextInputField(
        TooltipLabel(_('Region'), _('Tencent Cloud region for ASR service.')),
        required=True,
        default_value='ap-guangzhou'
    )

    def get_model_params_setting_form(self, model_name):
        return TencentSTTModelParams()
