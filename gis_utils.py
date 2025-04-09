import os
import json
import logging
from typing import Dict, Any, Optional
import tempfile
import zipfile
import shutil

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    import shapely
    from shapely.geometry import shape
    HAS_GIS_LIBS = True
except ImportError:
    logger.warning("GIS libraries not available. Some functionality may be limited.")
    HAS_GIS_LIBS = False

def extract_gis_metadata(file_path: str, file_type: str) -> Optional[Dict[str, Any]]:
    """Extract metadata from GIS files based on file type"""
    metadata = {}
    
    try:
        if file_type in ['geojson', 'json']:
            return extract_geojson_metadata(file_path)
        elif file_type == 'shp':
            return extract_shapefile_metadata(file_path)
        elif file_type in ['zip'] and HAS_GIS_LIBS:
            # Check if zip contains shapefiles
            return extract_zipped_shapefile_metadata(file_path)
        elif file_type in ['kml', 'kmz'] and HAS_GIS_LIBS:
            return extract_kml_metadata(file_path)
        elif file_type in ['gpkg'] and HAS_GIS_LIBS:
            return extract_geopackage_metadata(file_path)
    except Exception as e:
        logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
    
    return None

def extract_geojson_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from GeoJSON file"""
    with open(file_path, 'r') as f:
        try:
            geojson = json.load(f)
            
            # Extract basic metadata
            metadata = {
                "type": "GeoJSON",
                "feature_count": len(geojson.get('features', [])),
                "geometry_types": set(),
                "properties": set(),
                "crs": geojson.get('crs', {}).get('properties', {}).get('name', 'Unknown')
            }
            
            # Extract geometry types and property fields
            for feature in geojson.get('features', []):
                if 'geometry' in feature and 'type' in feature['geometry']:
                    metadata['geometry_types'].add(feature['geometry']['type'])
                
                if 'properties' in feature:
                    for prop in feature['properties'].keys():
                        metadata['properties'].add(prop)
            
            # Convert sets to lists for JSON serialization
            metadata['geometry_types'] = list(metadata['geometry_types'])
            metadata['properties'] = list(metadata['properties'])
            
            # Calculate bounding box if using shapely
            if HAS_GIS_LIBS and len(geojson.get('features', [])) > 0:
                try:
                    # Create a list of shapely geometries
                    geometries = []
                    for feature in geojson['features']:
                        if feature.get('geometry'):
                            geom = shape(feature['geometry'])
                            geometries.append(geom)
                    
                    # Calculate union of all geometries and get bounding box
                    if geometries:
                        union = shapely.unary_union(geometries)
                        bounds = union.bounds
                        metadata['bounds'] = {
                            'minx': bounds[0],
                            'miny': bounds[1],
                            'maxx': bounds[2],
                            'maxy': bounds[3]
                        }
                except Exception as e:
                    logger.warning(f"Could not calculate bounds: {str(e)}")
            
            return metadata
        
        except json.JSONDecodeError:
            logger.error(f"Invalid GeoJSON file: {file_path}")
            return {"type": "GeoJSON", "error": "Invalid GeoJSON format"}

def extract_shapefile_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from Shapefile"""
    if not HAS_GIS_LIBS:
        return {"type": "Shapefile", "note": "GIS libraries not available for detailed metadata"}
    
    try:
        # Read shapefile with geopandas
        gdf = gpd.read_file(file_path)
        
        metadata = {
            "type": "Shapefile",
            "feature_count": len(gdf),
            "geometry_types": gdf.geom_type.unique().tolist(),
            "properties": gdf.columns.drop('geometry').tolist(),
            "crs": str(gdf.crs),
        }
        
        # Get bounding box
        bounds = gdf.total_bounds
        metadata['bounds'] = {
            'minx': bounds[0],
            'miny': bounds[1],
            'maxx': bounds[2],
            'maxy': bounds[3]
        }
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error reading shapefile: {str(e)}")
        return {"type": "Shapefile", "error": str(e)}

def extract_zipped_shapefile_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from zipped shapefile"""
    if not HAS_GIS_LIBS:
        return {"type": "Zipped Shapefile", "note": "GIS libraries not available for detailed metadata"}
    
    # Create temporary directory to extract files
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Extract zip contents
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find shapefile in the extracted directory
        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
        
        if not shp_files:
            return {"type": "Zipped Archive", "contents": os.listdir(temp_dir)}
        
        # Get metadata from the first shapefile
        shapefile_path = os.path.join(temp_dir, shp_files[0])
        metadata = extract_shapefile_metadata(shapefile_path)
        metadata['type'] = "Zipped Shapefile"
        metadata['shapefile_name'] = shp_files[0]
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error processing zipped shapefile: {str(e)}")
        return {"type": "Zipped Archive", "error": str(e)}
    
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir)

def extract_kml_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from KML/KMZ file"""
    if not HAS_GIS_LIBS:
        return {"type": "KML/KMZ", "note": "GIS libraries not available for detailed metadata"}
    
    try:
        # For KMZ files, extract to temp directory first
        temp_dir = None
        kml_path = file_path
        
        if file_path.lower().endswith('.kmz'):
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            # Find main KML file
            kml_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.kml')]
            if kml_files:
                kml_path = os.path.join(temp_dir, kml_files[0])
        
        # Read KML with geopandas
        gdf = gpd.read_file(kml_path, driver='KML')
        
        metadata = {
            "type": "KML" if file_path.lower().endswith('.kml') else "KMZ",
            "feature_count": len(gdf),
            "geometry_types": gdf.geom_type.unique().tolist(),
            "properties": gdf.columns.drop('geometry').tolist()
        }
        
        # Get bounding box if there are features
        if len(gdf) > 0:
            bounds = gdf.total_bounds
            metadata['bounds'] = {
                'minx': bounds[0],
                'miny': bounds[1],
                'maxx': bounds[2],
                'maxy': bounds[3]
            }
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error reading KML/KMZ file: {str(e)}")
        return {"type": "KML/KMZ", "error": str(e)}
    
    finally:
        # Clean up temp directory if created
        if temp_dir:
            shutil.rmtree(temp_dir)

def extract_geopackage_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from GeoPackage"""
    if not HAS_GIS_LIBS:
        return {"type": "GeoPackage", "note": "GIS libraries not available for detailed metadata"}
    
    try:
        # List all layers in the GeoPackage
        available_layers = fiona.listlayers(file_path)
        
        metadata = {
            "type": "GeoPackage",
            "layers": available_layers,
            "layer_details": []
        }
        
        # Extract information for each layer
        for layer in available_layers:
            gdf = gpd.read_file(file_path, layer=layer)
            
            layer_info = {
                "name": layer,
                "feature_count": len(gdf),
                "geometry_types": gdf.geom_type.unique().tolist(),
                "properties": gdf.columns.drop('geometry').tolist(),
                "crs": str(gdf.crs)
            }
            
            # Get bounding box
            if len(gdf) > 0:
                bounds = gdf.total_bounds
                layer_info['bounds'] = {
                    'minx': bounds[0],
                    'miny': bounds[1],
                    'maxx': bounds[2],
                    'maxy': bounds[3]
                }
            
            metadata['layer_details'].append(layer_info)
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error reading GeoPackage: {str(e)}")
        return {"type": "GeoPackage", "error": str(e)}

def validate_geojson(file_path: str) -> bool:
    """Validate a GeoJSON file"""
    try:
        with open(file_path, 'r') as f:
            geojson = json.load(f)
            
        # Check required GeoJSON structure
        if 'type' not in geojson:
            return False
        
        if geojson['type'] == 'FeatureCollection' and 'features' not in geojson:
            return False
        
        return True
    except:
        return False

def get_shapefile_info(file_path: str) -> Dict[str, Any]:
    """Get information about a shapefile"""
    if not HAS_GIS_LIBS:
        return {"error": "GIS libraries not available"}
    
    try:
        gdf = gpd.read_file(file_path)
        
        return {
            "feature_count": len(gdf),
            "columns": gdf.columns.drop('geometry').tolist(),
            "geometry_type": gdf.geom_type.iloc[0] if len(gdf) > 0 else None,
            "crs": str(gdf.crs),
            "has_data": len(gdf) > 0
        }
    except Exception as e:
        return {"error": str(e)}
