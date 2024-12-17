"""OGC Coverage API Extension."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from geojson_pydantic.geometries import Polygon
from rio_tiler.models import BandStatistics
from titiler.core.factory import TilerFactory, FactoryExtension
from fastapi import Depends, Query
from starlette.requests import Request
from starlette.responses import Response


class CoverageMetadata(BaseModel):
    """Coverage Metadata model."""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    extent: Dict[str, Any]
    crs: str
    bands: List[str]
    spatial_resolution: Optional[float] = None
    temporal_resolution: Optional[str] = None
    links: List[Dict] = Field(default_factory=list)


class CoverageList(BaseModel):
    """Coverage List model."""
    coverages: List[CoverageMetadata] = Field(default_factory=list)
    links: List[Dict] = Field(default_factory=list)


class CoverageExtension(FactoryExtension):
    """OGC Coverage API Extension."""

    def register(self, factory: TilerFactory):
        """Register Coverage endpoints."""

        @factory.router.get(
            "/collections",
            response_model=CoverageList,
            response_model_exclude_none=True,
            summary="List available coverages",
        )
        def list_coverages(request: Request):
            """List available coverages."""
            base_url = str(request.base_url)
            
            # For now treat each dataset as a coverage
            coverage_id = "default"
            
            return CoverageList(
                coverages=[
                    CoverageMetadata(
                        id=coverage_id,
                        title="Default Coverage",
                        links=[
                            {
                                "href": f"{base_url}collections/{coverage_id}",
                                "rel": "self",
                                "type": "application/json",
                            },
                            {
                                "href": f"{base_url}collections/{coverage_id}/coverage",
                                "rel": "coverage",
                                "type": "image/tiff",
                            },
                        ],
                    )
                ],
                links=[
                    {
                        "href": f"{base_url}collections",
                        "rel": "self",
                        "type": "application/json",
                    }
                ],
            )

        @factory.router.get(
            "/collections/{coverage_id}",
            response_model=CoverageMetadata,
            response_model_exclude_none=True,
            summary="Get coverage metadata",
        )
        def get_coverage(
            request: Request,
            coverage_id: str,
            src_path=Depends(factory.path_dependency),
        ):
            """Get coverage metadata."""
            base_url = str(request.base_url)
            
            with rasterio.Env(**env):
                with factory.reader(src_path) as src_dst:
                    bounds = src_dst.bounds
                    stats = src_dst.statistics()
                    
                    return CoverageMetadata(
                        id=coverage_id,
                        title=src_dst.name,
                        extent={
                            "spatial": {
                                "bbox": [bounds],
                                "crs": str(src_dst.crs or "EPSG:4326"),
                            }
                        },
                        crs=str(src_dst.crs or "EPSG:4326"),
                        bands=src_dst.bands,
                        spatial_resolution=src_dst.pixel_size,
                        links=[
                            {
                                "href": f"{base_url}collections/{coverage_id}",
                                "rel": "self",
                                "type": "application/json",
                            },
                            {
                                "href": f"{base_url}collections/{coverage_id}/coverage",
                                "rel": "coverage",
                                "type": "image/tiff",
                            },
                        ],
                    )

        @factory.router.get(
            "/collections/{coverage_id}/coverage",
            response_class=Response,
            summary="Get coverage data",
        )
        def get_coverage_data(
            coverage_id: str,
            bbox: Optional[str] = Query(
                None, description="Bounding box: 'minx,miny,maxx,maxy'"
            ),
            datetime: Optional[str] = Query(
                None, description="Datetime filter"
            ),
            properties: Optional[str] = Query(
                None, description="Filter by properties"
            ),
            src_path=Depends(factory.path_dependency),
            layer_params=Depends(factory.layer_dependency),
            dataset_params=Depends(factory.dataset_dependency),
            image_params=Depends(factory.img_preview_dependency),
            render_params=Depends(factory.render_dependency),
            env=Depends(factory.environment_dependency),
        ):
            """Get coverage data."""
            with rasterio.Env(**env):
                with factory.reader(src_path) as src_dst:
                    if bbox:
                        bounds = [float(x) for x in bbox.split(",")]
                        image = src_dst.part(bounds, **layer_params.as_dict())
                    else:
                        image = src_dst.preview(**layer_params.as_dict())

                    content, media_type = render_image(
                        image,
                        **render_params.as_dict(),
                    )

                    return Response(content, media_type=media_type) 