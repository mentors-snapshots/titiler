"""Test OGC Coverage Extension."""

from fastapi import FastAPI
from starlette.testclient import TestClient

from titiler.core.factory import TilerFactory
from titiler.extensions.coverage import CoverageExtension
from .conftest import DATA_DIR


def test_coverage_extension():
    """Test CoverageExtension."""
    app = FastAPI()
    cog = TilerFactory(extensions=[CoverageExtension()])
    app.include_router(cog.router)
    client = TestClient(app)

    response = client.get("/collections")
    assert response.status_code == 200
    resp = response.json()
    assert len(resp["coverages"]) == 1
    assert resp["coverages"][0]["id"] == "default"

    coverage_id = resp["coverages"][0]["id"]
    response = client.get(
        f"/collections/{coverage_id}?url={DATA_DIR}/cog.tif"
    )
    assert response.status_code == 200
    resp = response.json()
    assert resp["id"] == coverage_id
    assert "extent" in resp
    assert "crs" in resp
    assert "bands" in resp

    response = client.get(
        f"/collections/{coverage_id}/coverage?url={DATA_DIR}/cog.tif"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/tiff; application=geotiff"

    # Test bbox parameter
    response = client.get(
        f"/collections/{coverage_id}/coverage?url={DATA_DIR}/cog.tif&bbox=-180,-90,180,90"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/tiff; application=geotiff" 