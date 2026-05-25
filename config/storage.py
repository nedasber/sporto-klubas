"""
Custom static files storage.

Pagrindinis tikslas: padaryti, kad Manifest static files storage
neišmestų klaidos, jei failas yra nuorodoje per {% static %}, bet
dėl kažkokios priežasties nepateko į staticfiles.json manifestą
(pvz., favicon.png, kuris dar tik dabar buvo pridėtas).

Su manifest_strict = False, Django/WhiteNoise tiesiog grąžins URL
be hash'o (pvz. /static/favicon.png), o ne sugriaus visą puslapį.
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    WhiteNoise CompressedManifestStaticFilesStorage variantas, kuris
    neišmeta ValueError, jei failas neegzistuoja manifeste.
    """
    manifest_strict = False
