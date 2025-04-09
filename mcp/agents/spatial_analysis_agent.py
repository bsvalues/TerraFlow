"""
Spatial Analysis Agent Module

This module implements a specialized agent for GIS spatial analysis tasks
including buffer creation, overlays, and spatial queries.
"""

import logging
import time
import os
import json
import tempfile
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from ..core import mcp_instance

# Import GIS libraries only if available
try:
    import geopandas as gpd
    from shapely.geometry import mapping, shape, Point, LineString, Polygon
    import numpy as np
    HAS_GIS_LIBS = True
except ImportError:
    HAS_GIS_LIBS = False
    # Create dummy classes for type checking
    np = None
    class Point:
        def __init__(self, *args):
            pass
        def distance(self, other):
            return 0

class SpatialAnalysisAgent(BaseAgent):
    """
    Agent responsible for GIS spatial analysis tasks
    """
    
    def __init__(self):
        """Initialize the spatial analysis agent"""
        super().__init__()
        self.capabilities = [
            "buffer_creation",
            "spatial_intersection",
            "spatial_union",
            "spatial_difference",
            "distance_calculation",
            "area_calculation"
        ]
        self.logger.info("Spatial Analysis Agent initialized")
    
    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a spatial analysis task"""
        self.last_activity = time.time()
        
        if not task_data or "task_type" not in task_data:
            return {"error": "Invalid task data, missing task_type"}
        
        task_type = task_data["task_type"]
        
        if task_type == "buffer_creation":
            return self.create_buffer(task_data)
        elif task_type == "spatial_intersection":
            return self.perform_spatial_intersection(task_data)
        elif task_type == "spatial_union":
            return self.perform_spatial_union(task_data)
        elif task_type == "spatial_difference":
            return self.perform_spatial_difference(task_data)
        elif task_type == "distance_calculation":
            return self.calculate_distance(task_data)
        elif task_type == "area_calculation":
            return self.calculate_area(task_data)
        else:
            return {"error": f"Unsupported task type: {task_type}"}
    
    def create_buffer(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create buffer zones around features"""
        self.set_status("buffering")
        
        # Required parameters
        if "input_file" not in task_data or "buffer_distance" not in task_data:
            return {"error": "Missing required parameters for buffer creation"}
        
        input_file = task_data["input_file"]
        buffer_distance = float(task_data["buffer_distance"])
        
        # Optional parameters
        output_file = task_data.get("output_file")
        if not output_file:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_buffer.geojson"
        
        # Distance units (default: meters)
        distance_units = task_data.get("distance_units", "meters")
        
        # Validate parameters
        if not os.path.exists(input_file):
            return {"error": f"Input file does not exist: {input_file}"}
        
        # Perform buffer operation
        try:
            start_time = time.time()
            
            # Read the input data
            gdf = gpd.read_file(input_file)
            
            # Convert buffer distance to meters if needed
            if distance_units == "kilometers":
                buffer_distance = buffer_distance * 1000
            elif distance_units == "miles":
                buffer_distance = buffer_distance * 1609.34
            elif distance_units == "feet":
                buffer_distance = buffer_distance * 0.3048
            
            # Create buffer
            gdf_buffer = gdf.copy()
            gdf_buffer['geometry'] = gdf.geometry.buffer(buffer_distance)
            
            # Save to output file
            gdf_buffer.to_file(output_file, driver="GeoJSON")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "status": "success",
                "output_file": output_file,
                "processing_time": processing_time,
                "feature_count": len(gdf_buffer),
                "buffer_distance": buffer_distance,
                "distance_units": "meters"  # Output is always in meters
            }
            
        except Exception as e:
            self.logger.error(f"Buffer creation error: {str(e)}")
            return {"error": f"Buffer creation failed: {str(e)}"}
        finally:
            self.set_status("idle")
    
    def perform_spatial_intersection(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform spatial intersection between two layers"""
        self.set_status("intersecting")
        
        # Required parameters
        if "input_file1" not in task_data or "input_file2" not in task_data:
            return {"error": "Missing required parameters for spatial intersection"}
        
        input_file1 = task_data["input_file1"]
        input_file2 = task_data["input_file2"]
        
        # Optional parameters
        output_file = task_data.get("output_file")
        if not output_file:
            base_name1 = os.path.splitext(os.path.basename(input_file1))[0]
            base_name2 = os.path.splitext(os.path.basename(input_file2))[0]
            output_file = f"{base_name1}_{base_name2}_intersection.geojson"
        
        # Validate parameters
        if not os.path.exists(input_file1):
            return {"error": f"Input file 1 does not exist: {input_file1}"}
        
        if not os.path.exists(input_file2):
            return {"error": f"Input file 2 does not exist: {input_file2}"}
        
        # Perform intersection
        try:
            start_time = time.time()
            
            # Read the input data
            gdf1 = gpd.read_file(input_file1)
            gdf2 = gpd.read_file(input_file2)
            
            # Ensure same CRS
            if gdf1.crs != gdf2.crs:
                gdf2 = gdf2.to_crs(gdf1.crs)
            
            # Perform spatial intersection
            intersection = gpd.overlay(gdf1, gdf2, how='intersection')
            
            # Save to output file
            intersection.to_file(output_file, driver="GeoJSON")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "status": "success",
                "output_file": output_file,
                "processing_time": processing_time,
                "feature_count": len(intersection)
            }
            
        except Exception as e:
            self.logger.error(f"Spatial intersection error: {str(e)}")
            return {"error": f"Spatial intersection failed: {str(e)}"}
        finally:
            self.set_status("idle")
    
    def perform_spatial_union(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform spatial union of features"""
        self.set_status("unioning")
        
        # Required parameters
        if "input_file" not in task_data:
            return {"error": "Missing required parameter: input_file"}
        
        input_file = task_data["input_file"]
        
        # Optional parameters
        output_file = task_data.get("output_file")
        if not output_file:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_union.geojson"
        
        group_by = task_data.get("group_by")
        
        # Validate parameters
        if not os.path.exists(input_file):
            return {"error": f"Input file does not exist: {input_file}"}
        
        # Perform union
        try:
            start_time = time.time()
            
            # Read the input data
            gdf = gpd.read_file(input_file)
            
            if group_by and group_by in gdf.columns:
                # Union by group
                result = gdf.dissolve(by=group_by)
                result = result.reset_index()
            else:
                # Union all features
                result = gdf.unary_union
                result = gpd.GeoDataFrame(geometry=[result], crs=gdf.crs)
            
            # Save to output file
            result.to_file(output_file, driver="GeoJSON")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "status": "success",
                "output_file": output_file,
                "processing_time": processing_time,
                "feature_count": len(result)
            }
            
        except Exception as e:
            self.logger.error(f"Spatial union error: {str(e)}")
            return {"error": f"Spatial union failed: {str(e)}"}
        finally:
            self.set_status("idle")
    
    def perform_spatial_difference(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform spatial difference between two layers"""
        self.set_status("differencing")
        
        # Required parameters
        if "input_file1" not in task_data or "input_file2" not in task_data:
            return {"error": "Missing required parameters for spatial difference"}
        
        input_file1 = task_data["input_file1"]
        input_file2 = task_data["input_file2"]
        
        # Optional parameters
        output_file = task_data.get("output_file")
        if not output_file:
            base_name1 = os.path.splitext(os.path.basename(input_file1))[0]
            base_name2 = os.path.splitext(os.path.basename(input_file2))[0]
            output_file = f"{base_name1}_minus_{base_name2}.geojson"
        
        # Validate parameters
        if not os.path.exists(input_file1):
            return {"error": f"Input file 1 does not exist: {input_file1}"}
        
        if not os.path.exists(input_file2):
            return {"error": f"Input file 2 does not exist: {input_file2}"}
        
        # Perform difference
        try:
            start_time = time.time()
            
            # Read the input data
            gdf1 = gpd.read_file(input_file1)
            gdf2 = gpd.read_file(input_file2)
            
            # Ensure same CRS
            if gdf1.crs != gdf2.crs:
                gdf2 = gdf2.to_crs(gdf1.crs)
            
            # Perform spatial difference
            difference = gpd.overlay(gdf1, gdf2, how='difference')
            
            # Save to output file
            difference.to_file(output_file, driver="GeoJSON")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "status": "success",
                "output_file": output_file,
                "processing_time": processing_time,
                "feature_count": len(difference)
            }
            
        except Exception as e:
            self.logger.error(f"Spatial difference error: {str(e)}")
            return {"error": f"Spatial difference failed: {str(e)}"}
        finally:
            self.set_status("idle")
    
    def calculate_distance(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate distances between features or coordinates"""
        self.set_status("calculating_distance")
        
        # Check input type
        if "input_file" in task_data:
            # Distance between features in a file
            return self._calculate_distance_between_features(task_data)
        elif "coordinates1" in task_data and "coordinates2" in task_data:
            # Distance between two coordinates
            return self._calculate_distance_between_coords(task_data)
        else:
            return {"error": "Invalid input for distance calculation"}
    
    def _calculate_distance_between_coords(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate distance between two coordinates"""
        try:
            coord1 = task_data["coordinates1"]
            coord2 = task_data["coordinates2"]
            
            # Create points
            point1 = Point(coord1[0], coord1[1])
            point2 = Point(coord2[0], coord2[1])
            
            # Calculate distance
            if "crs" in task_data:
                # Create GeoDataFrame with specified CRS
                crs = task_data["crs"]
                gdf = gpd.GeoDataFrame(geometry=[point1, point2], crs=crs)
                
                # Convert to meters-based CRS if needed
                if not crs.startswith('EPSG:326') and not crs.startswith('EPSG:327'):
                    gdf = gdf.to_crs('EPSG:3857')  # Web Mercator
                
                # Recalculate points after projection
                point1 = gdf.geometry.iloc[0]
                point2 = gdf.geometry.iloc[1]
            
            # Calculate distance in meters
            distance = point1.distance(point2)
            
            # Convert distance based on requested units
            units = task_data.get("units", "meters")
            distance_value = distance
            
            if units == "kilometers":
                distance_value = distance / 1000
            elif units == "miles":
                distance_value = distance / 1609.34
            elif units == "feet":
                distance_value = distance / 0.3048
            
            return {
                "status": "success",
                "distance": distance_value,
                "units": units,
                "coordinates1": coord1,
                "coordinates2": coord2
            }
            
        except Exception as e:
            self.logger.error(f"Distance calculation error: {str(e)}")
            return {"error": f"Distance calculation failed: {str(e)}"}
        finally:
            self.set_status("idle")
    
    def _calculate_distance_between_features(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate distances between features in a file"""
        try:
            input_file = task_data["input_file"]
            feature_id1 = task_data.get("feature_id1")
            feature_id2 = task_data.get("feature_id2")
            id_field = task_data.get("id_field", "id")
            
            # Validate parameters
            if not os.path.exists(input_file):
                return {"error": f"Input file does not exist: {input_file}"}
            
            # Read the input data
            gdf = gpd.read_file(input_file)
            
            # Handle different cases
            if feature_id1 and feature_id2:
                # Distance between two specific features
                feature1 = gdf[gdf[id_field] == feature_id1]
                feature2 = gdf[gdf[id_field] == feature_id2]
                
                if len(feature1) == 0:
                    return {"error": f"Feature with ID {feature_id1} not found"}
                
                if len(feature2) == 0:
                    return {"error": f"Feature with ID {feature_id2} not found"}
                
                # Calculate distance
                distance = feature1.geometry.iloc[0].distance(feature2.geometry.iloc[0])
                
                # Convert distance based on requested units
                units = task_data.get("units", "meters")
                distance_value = distance
                
                if units == "kilometers":
                    distance_value = distance / 1000
                elif units == "miles":
                    distance_value = distance / 1609.34
                elif units == "feet":
                    distance_value = distance / 0.3048
                
                return {
                    "status": "success",
                    "distance": distance_value,
                    "units": units,
                    "feature_id1": feature_id1,
                    "feature_id2": feature_id2
                }
            else:
                # Distance matrix between all features
                distances = {}
                feature_ids = gdf[id_field].unique()
                
                for i, id1 in enumerate(feature_ids):
                    distances[str(id1)] = {}
                    feature1 = gdf[gdf[id_field] == id1].geometry.iloc[0]
                    
                    for id2 in feature_ids[i+1:]:
                        feature2 = gdf[gdf[id_field] == id2].geometry.iloc[0]
                        distance = feature1.distance(feature2)
                        
                        # Convert distance based on requested units
                        units = task_data.get("units", "meters")
                        distance_value = distance
                        
                        if units == "kilometers":
                            distance_value = distance / 1000
                        elif units == "miles":
                            distance_value = distance / 1609.34
                        elif units == "feet":
                            distance_value = distance / 0.3048
                        
                        distances[str(id1)][str(id2)] = distance_value
                
                return {
                    "status": "success",
                    "distances": distances,
                    "units": task_data.get("units", "meters")
                }
                
        except Exception as e:
            self.logger.error(f"Distance calculation error: {str(e)}")
            return {"error": f"Distance calculation failed: {str(e)}"}
        finally:
            self.set_status("idle")
    
    def calculate_area(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate areas of features"""
        self.set_status("calculating_area")
        
        # Required parameters
        if "input_file" not in task_data:
            return {"error": "Missing required parameter: input_file"}
        
        input_file = task_data["input_file"]
        feature_id = task_data.get("feature_id")
        id_field = task_data.get("id_field", "id")
        
        # Validate parameters
        if not os.path.exists(input_file):
            return {"error": f"Input file does not exist: {input_file}"}
        
        # Perform area calculation
        try:
            # Read the input data
            gdf = gpd.read_file(input_file)
            
            # Convert to equal-area projection if needed
            if gdf.crs and gdf.crs.is_geographic:
                # Convert to a suitable equal-area projection
                gdf = gdf.to_crs("EPSG:3857")  # Web Mercator
            
            # Units
            units = task_data.get("units", "square_meters")
            
            # Calculate areas
            if feature_id:
                # Area of a specific feature
                feature = gdf[gdf[id_field] == feature_id]
                
                if len(feature) == 0:
                    return {"error": f"Feature with ID {feature_id} not found"}
                
                # Calculate area
                area = feature.geometry.iloc[0].area
                
                # Convert area based on requested units
                area_value = area  # Default: square meters
                
                if units == "square_kilometers":
                    area_value = area / 1000000
                elif units == "hectares":
                    area_value = area / 10000
                elif units == "square_miles":
                    area_value = area / 2589988.11
                elif units == "acres":
                    area_value = area / 4046.86
                
                return {
                    "status": "success",
                    "area": area_value,
                    "units": units,
                    "feature_id": feature_id
                }
            else:
                # Areas of all features
                areas = {}
                
                for _, row in gdf.iterrows():
                    feature_id = str(row[id_field])
                    area = row.geometry.area
                    
                    # Convert area based on requested units
                    area_value = area  # Default: square meters
                    
                    if units == "square_kilometers":
                        area_value = area / 1000000
                    elif units == "hectares":
                        area_value = area / 10000
                    elif units == "square_miles":
                        area_value = area / 2589988.11
                    elif units == "acres":
                        area_value = area / 4046.86
                    
                    areas[feature_id] = area_value
                
                # Calculate total area
                total_area = sum(areas.values())
                
                return {
                    "status": "success",
                    "areas": areas,
                    "total_area": total_area,
                    "units": units
                }
                
        except Exception as e:
            self.logger.error(f"Area calculation error: {str(e)}")
            return {"error": f"Area calculation failed: {str(e)}"}
        finally:
            self.set_status("idle")

# Register this agent with the MCP
mcp_instance.register_agent("spatial_analysis", SpatialAnalysisAgent())