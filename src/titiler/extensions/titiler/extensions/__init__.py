"""titiler.extensions"""

__version__ = "0.19.2"

from .cogeo import cogValidateExtension  # noqa
from .stac import stacExtension  # noqa
from .viewer import cogViewerExtension, stacViewerExtension  # noqa
from .wms import wmsExtension  # noqa
from .ogcmaps import ogcmapsExtension  # noqa
