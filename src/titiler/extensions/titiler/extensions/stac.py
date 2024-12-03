"""rio-stac Extension."""

from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlencode

from attrs import define
from fastapi import Depends, HTTPException, Query, Request
from typing_extensions import Annotated, TypedDict

from titiler.core.factory import FactoryExtension, TilerFactory
from titiler.core.titiler.core.dependencies import ImageRenderingParams
from titiler.core.titiler.core.models.mapbox import TileJSON
from titiler.core.titiler.core.resources.enums import ImageType

try:
    import pystac
    from pystac.utils import datetime_to_str, str_to_datetime
    from rio_stac.stac import create_stac_item
except ImportError:  # pragma: nocover
    create_stac_item = None  # type: ignore
    pystac = None  # type: ignore
    str_to_datetime = datetime_to_str = None  # type: ignore


class Item(TypedDict, total=False):
    """STAC Item."""

    type: str
    stac_version: str
    stac_extensions: Optional[List[str]]
    id: str
    geometry: Dict[str, Any]
    bbox: List[float]
    properties: Dict[str, Any]
    links: List[Dict[str, Any]]
    assets: Dict[str, Any]
    collection: str


@define
class stacExtension(FactoryExtension):
    """Add /stac endpoint to a COG TilerFactory."""

    def register(self, factory: TilerFactory):
        """Register endpoint to the tiler factory."""

        assert (
            create_stac_item is not None
        ), "'rio-stac' must be installed to use stacExtension"
        assert pystac is not None, "'pystac' must be installed to use stacExtension"

        media = [m.value for m in pystac.MediaType] + ["auto"]

        @factory.router.get("/stac", response_model=Item, name="Create STAC Item")
        def create_stac(
            src_path=Depends(factory.path_dependency),
            datetime: Annotated[
                Optional[str],
                Query(
                    description="The date and time of the assets, in UTC (e.g 2020-01-01, 2020-01-01T01:01:01).",
                ),
            ] = None,
            extensions: Annotated[
                Optional[List[str]],
                Query(description="STAC extension URL the Item implements."),
            ] = None,
            collection: Annotated[
                Optional[str],
                Query(description="The Collection ID that this item belongs to."),
            ] = None,
            collection_url: Annotated[
                Optional[str],
                Query(description="Link to the STAC Collection."),
            ] = None,
            # properties: Optional[Dict] = Query(None, description="Additional properties to add in the item."),
            id: Annotated[
                Optional[str],
                Query(
                    description="Id to assign to the item (default to the source basename)."
                ),
            ] = None,
            asset_name: Annotated[
                Optional[str],
                Query(description="asset name for the source (default to 'data')."),
            ] = "data",
            asset_roles: Annotated[
                Optional[List[str]],
                Query(description="list of asset's roles."),
            ] = None,
            asset_media_type: Annotated[  # type: ignore
                Optional[Literal[tuple(media)]],
                Query(description="Asset's media type"),
            ] = "auto",
            asset_href: Annotated[
                Optional[str],
                Query(description="Asset's URI (default to source's path)"),
            ] = None,
            with_proj: Annotated[
                Optional[bool],
                Query(description="Add the `projection` extension and properties."),
            ] = True,
            with_raster: Annotated[
                Optional[bool],
                Query(description="Add the `raster` extension and properties."),
            ] = True,
            with_eo: Annotated[
                Optional[bool],
                Query(description="Add the `eo` extension and properties."),
            ] = True,
            max_size: Annotated[
                Optional[int],
                Query(
                    gt=0,
                    description="Limit array size from which to get the raster statistics.",
                ),
            ] = 1024,
            geom_densify_pts: Annotated[
                Optional[int],
                Query(
                    alias="geometry_densify",
                    ge=0,
                    description="Number of points to add to each edge to account for nonlinear edges transformation.",
                ),
            ] = 0,
            geom_precision: Annotated[
                Optional[int],
                Query(
                    alias="geometry_precision",
                    ge=-1,
                    description="Round geometry coordinates to this number of decimal.",
                ),
            ] = -1,
        ):
            """Create STAC item."""
            properties = (
                {}
            )  # or properties = properties or {} if we add properties in Query

            dt = None
            if datetime:
                if "/" in datetime:
                    start_datetime, end_datetime = datetime.split("/")
                    properties["start_datetime"] = datetime_to_str(
                        str_to_datetime(start_datetime)
                    )
                    properties["end_datetime"] = datetime_to_str(
                        str_to_datetime(end_datetime)
                    )
                else:
                    dt = str_to_datetime(datetime)

            return create_stac_item(
                src_path,
                input_datetime=dt,
                extensions=extensions,
                collection=collection,
                collection_url=collection_url,
                properties=properties,
                id=id,
                asset_name=asset_name,
                asset_roles=asset_roles,
                asset_media_type=asset_media_type,
                asset_href=asset_href or src_path,
                with_proj=with_proj,
                with_raster=with_raster,
                with_eo=with_eo,
                raster_max_size=max_size,
                geom_densify_pts=geom_densify_pts,
                geom_precision=geom_precision,
            ).to_dict()
        
        @factory.router.get("/renders", response_model=TileJSON, name="Create Rendered TileJSON")
        def create_rendered_tilejson(
            request: Request,
            src_path=Depends(factory.path_dependency),
            render_params: ImageRenderingParams = Depends(),
            asset_name: Annotated[
                Optional[str],
                Query(description="Asset name to render from STAC metadata (default to 'data')."),
            ] = "data",
            tile_format: Annotated[
                Optional[ImageType],
                Query(description="Output image type. Default is automatically determined based on mask presence."),
            ] = None,
            tile_scale: Annotated[
                int,
                Query(gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."),
            ] = 1,
            minzoom: Annotated[
                Optional[int],
                Query(description="Override automatic min zoom level"),
            ] = None,
            maxzoom: Annotated[
                Optional[int],
                Query(description="Override automatic max zoom level"),
            ] = None,
        ):
            """Create a TileJSON document with rendering parameters from STAC metadata.
            Supports rendering parameters from STAC metadata including:
            - bands
            - color_formula
            - range
            - rescale
            - nodata
            - colormap_name
            Falls back to:
            1. Parameters defined in STAC metadata
            2. Asset's own metadata
            3. TiTiler's core defaults
            """
            # Create STAC item to access metadata
            try:
                item_data = create_stac_item(
                    src_path,
                    asset_name=asset_name,
                ).to_dict()
            except Exception as e:
                if "HTTP response code: 404" in str(e):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to fetch STAC item: {str(e)}",
                    )
                raise

            # Get asset metadata
            if asset_name not in item_data["assets"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset '{asset_name}' not found in STAC metadata"
                )

            asset = item_data["assets"][asset_name]
            render_params_dict = {
                "bands": "1",  # Default to first band
                "rescale": "0,255",  # Default rescale range
            }

            # Extract render parameters from asset metadata first (lowest precedence)
            if "nodata" in asset:
                render_params_dict["nodata"] = str(asset["nodata"])
            if "bands" in asset:
                bands = asset["bands"]
                if isinstance(bands, list) and all(isinstance(b, dict) for b in bands):
                    band_indices = list(range(1, len(bands) + 1))
                    render_params_dict["bands"] = ",".join(map(str, band_indices))

            # Extract render parameters from STAC metadata (overrides asset metadata)
            if "render" in asset:
                render_metadata = asset["render"]
                for param in ["bands", "color_formula", "range", "rescale", "nodata", "colormap_name"]:
                    if param in render_metadata:
                        value = render_metadata[param]
                        if value is None and param == "bands":
                            raise HTTPException(
                                status_code=400,
                                detail="Missing required parameter: bands"
                            )
                        if value is not None:
                            if isinstance(value, (list, tuple)):
                                render_params_dict[param] = ",".join(map(str, value))
                            else:
                                render_params_dict[param] = str(value)

            # Build tiles URL with format and scale
            tiles_url = f"/tiles/{{z}}/{{x}}/{{y}}"
            if tile_format:
                tiles_url += f".{tile_format.value}"
            if tile_scale > 1:
                tiles_url += f"@{tile_scale}x"
            tiles_url += f"?url={src_path}"

            # Handle user parameters (highest precedence)
            final_params = {}

            # First, add parameters from STAC metadata
            final_params.update(render_params_dict)

            # Then, override with parameters from request query params
            for param in ["bands", "color_formula", "range", "rescale", "nodata", "colormap_name"]:
                if param in request.query_params:
                    value = request.query_params[param]
                    # Ensure consistent case for operators in color_formula
                    if param == "color_formula":
                        value = value.lower()
                    final_params[param] = value

            # Add rendering parameters to URL using urlencode for consistent encoding
            if final_params:
                # Convert all values to strings and handle lists/tuples
                encoded_params = {}
                for key, value in final_params.items():
                    if isinstance(value, (list, tuple)):
                        value = ",".join(map(str, value))
                    # Ensure consistent case for special characters
                    if key == "color_formula":
                        value = value.replace("/", "%2f")  # Force lowercase slash
                    else:
                        value = str(value)
                    encoded_params[key] = value
                tiles_url = f"{tiles_url}&{urlencode(encoded_params, safe='%')}"

            # Filter out special parameters from query string for any remaining params
            qs_key_to_remove = [
                "url",
                "tile_format",
                "tile_scale",
                "minzoom",
                "maxzoom",
                "asset_name",
                "bands",
                "color_formula",
                "range",
                "rescale",
                "nodata",
                "colormap_name",
            ]
            qs = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in qs_key_to_remove
            ]
            if qs:
                tiles_url += f"&{urlencode(qs)}"

            return {
                "tilejson": "2.2.0",
                "version": "1.0.0",
                "scheme": "xyz",
                "tiles": [tiles_url],
                "minzoom": minzoom if minzoom is not None else 0,
                "maxzoom": maxzoom if maxzoom is not None else 24,
                "bounds": item_data["bbox"],
            }