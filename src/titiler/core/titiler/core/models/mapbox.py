"""Common response models."""

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, model_validator
from pyparsing import Union

class RenderParams(BaseModel):
    """Rendering parameters model."""

    bands: Optional[List[int]] = None
    color_formula: Optional[str] = None
    range: Optional[List[float]] = None
    rescale: Optional[List[float]] = None
    nodata: Optional[Union[int, float]] = None
    colormap_name: Optional[str] = None

class TileJSON(BaseModel):
    """
    TileJSON model.

    Based on https://github.com/mapbox/tilejson-spec/tree/master/2.2.0

    """

    tilejson: str = "2.2.0"
    name: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0.0"
    attribution: Optional[str] = None
    template: Optional[str] = None
    legend: Optional[str] = None
    scheme: Literal["xyz", "tms"] = "xyz"
    tiles: List[str]
    grids: Optional[List[str]] = None
    data: Optional[List[str]] = None
    minzoom: int = Field(0, ge=0, le=30)
    maxzoom: int = Field(30, ge=0, le=30)
    bounds: List[float] = [-180, -90, 180, 90]
    center: Optional[Tuple[float, float, int]] = None
    render: Optional[RenderParams] = None


    @model_validator(mode="after")
    def compute_center(self):
        """Compute center if it does not exist."""
        bounds = self.bounds
        if not self.center:
            self.center = (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2,
                self.minzoom,
            )
        return self
    