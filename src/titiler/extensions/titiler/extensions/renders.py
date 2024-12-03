"""Renders Extension."""

from typing import Optional, Union
from urllib.parse import urlencode

from attrs import define
from fastapi import Depends, Query, Request

from titiler.core.factory import FactoryExtension, TilerFactory
from titiler.core.models.mapbox import TileJSON, RenderParams

@define
class rendersExtension(FactoryExtension):
    """Add /renders endpoint to handle render parameters."""

    def register(self, factory: TilerFactory):
        """Register endpoints to the tiler factory."""

        @factory.router.get(
            "/renders",
            response_model=TileJSON,
            responses={200: {"description": "Return a TileJSON with rendering parameters"}},
            name="Renders",
        )
        def renders(
            request: Request,
            src_path=Depends(factory.path_dependency),
            rescale=Depends(factory.rescale_dependency),
            color_formula=Depends(factory.color_formula_dependency),
            colormap=Depends(factory.colormap_dependency),
            bands: Optional[str] = Query(None, description="Band indexes"),
            range: Optional[str] = Query(None, description="Min,max range for data"),
            nodata: Optional[Union[str, int, float]] = Query(None, description="Nodata value"),
        ) -> TileJSON:
            """Create a TileJSON with custom rendering parameters."""
            tilejson_url = factory.url_for(
                request, "tile", z="{z}", x="{x}", y="{y}", tileMatrixSetId="WebMercatorQuad"
            )

            # Add query parameters
            params = {}
            if src_path:
                params["url"] = src_path
            if bands:
                params["bands"] = bands
            if range:
                params["range"] = range
            if nodata is not None:
                params["nodata"] = str(nodata)
            if rescale:
                params["rescale"] = ",".join(map(str, rescale))
            if color_formula:
                params["color_formula"] = color_formula
            if colormap and hasattr(colormap, "name"):
                params["colormap_name"] = colormap.name

            if params:
                tilejson_url = f"{tilejson_url}?{urlencode(params)}"

            # Create render params for TileJSON
            render_params_dict = {}
            if bands:
                render_params_dict["bands"] = [int(b) for b in bands.split(",")]
            if range:
                min_val, max_val = map(float, range.split(","))
                render_params_dict["range"] = [min_val, max_val]
            if nodata is not None:
                render_params_dict["nodata"] = float(nodata) if isinstance(nodata, (int, float)) else nodata
            if rescale:
                render_params_dict["rescale"] = rescale
            if color_formula:
                render_params_dict["color_formula"] = color_formula
            if colormap and hasattr(colormap, "name"):
                render_params_dict["colormap_name"] = colormap.name

            render_instance = None
            if render_params_dict:
                render_instance = RenderParams(**render_params_dict)

            bounds = [-180, -85.051129, 180, 85.051129]
            return {
                "tilejson": "2.2.0",
                "name": "Custom Renders TileJSON",
                "version": "1.0.0",
                "tiles": [tilejson_url],
                "minzoom": 0,
                "maxzoom": 24,
                "bounds": bounds,
                "center": [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, 12],
                "render": render_instance
            }
