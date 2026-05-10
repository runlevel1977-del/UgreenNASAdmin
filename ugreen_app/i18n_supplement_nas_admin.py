# -*- coding: utf-8 -*-
"""NAS-Verwaltung (nas_admin.*) für Locales außerhalb der vollständigen de/en-Basis."""

from __future__ import annotations

from ugreen_app.i18n_nas_locale_es import NAS_ADMIN_ES
from ugreen_app.i18n_nas_locale_fr import NAS_ADMIN_FR
from ugreen_app.i18n_nas_locale_hr import NAS_ADMIN_HR
from ugreen_app.i18n_nas_locale_it import NAS_ADMIN_IT
from ugreen_app.i18n_nas_locale_ko import NAS_ADMIN_KO
from ugreen_app.i18n_nas_locale_pl import NAS_ADMIN_PL
from ugreen_app.i18n_nas_locale_ru import NAS_ADMIN_RU
from ugreen_app.i18n_nas_locale_tr import NAS_ADMIN_TR
from ugreen_app.i18n_nas_locale_zh import NAS_ADMIN_ZH

NAS_ADMIN_SUPPLEMENT: dict[str, dict[str, str]] = {
    "hr": NAS_ADMIN_HR,
    "fr": NAS_ADMIN_FR,
    "es": NAS_ADMIN_ES,
    "it": NAS_ADMIN_IT,
    "pl": NAS_ADMIN_PL,
    "ru": NAS_ADMIN_RU,
    "tr": NAS_ADMIN_TR,
    "ko": NAS_ADMIN_KO,
    "zh": NAS_ADMIN_ZH,
}
