/**
 * TerraFlow Map Utilities
 * 
 * Provides helper functions for map operations and data transformations
 */

const MapUtils = {
    /**
     * Converts an XML configuration to a JavaScript object
     * 
     * @param {string} xmlString - The XML string to convert
     * @return {Object} - The parsed configuration object
     */
    parseXmlConfig: function(xmlString) {
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlString, "text/xml");
        
        return this.xmlToJson(xmlDoc);
    },
    
    /**
     * Recursively converts an XML node to a JavaScript object
     * 
     * @param {Node} xml - XML node to convert
     * @return {Object} - Converted JavaScript object
     */
    xmlToJson: function(xml) {
        // Create the return object
        let obj = {};
        
        if (xml.nodeType === 1) { // element
            // Process attributes
            if (xml.attributes.length > 0) {
                obj["@attributes"] = {};
                for (let i = 0; i < xml.attributes.length; i++) {
                    const attribute = xml.attributes.item(i);
                    obj["@attributes"][attribute.nodeName] = attribute.nodeValue;
                }
            }
        } else if (xml.nodeType === 3) { // text
            return xml.nodeValue.trim();
        }
        
        // Process children
        if (xml.hasChildNodes()) {
            for (let i = 0; i < xml.childNodes.length; i++) {
                const item = xml.childNodes.item(i);
                const nodeName = item.nodeName;
                
                // Skip text nodes (whitespace)
                if (item.nodeType === 3 && item.nodeValue.trim() === "") {
                    continue;
                }
                
                if (typeof(obj[nodeName]) === "undefined") {
                    if (nodeName === "#text") {
                        if (item.nodeValue.trim() !== "") {
                            return item.nodeValue.trim();
                        }
                    } else {
                        const value = this.xmlToJson(item);
                        if (Object.keys(value).length > 0) {
                            obj[nodeName] = value;
                        }
                    }
                } else {
                    if (!Array.isArray(obj[nodeName])) {
                        const oldObj = obj[nodeName];
                        obj[nodeName] = [];
                        obj[nodeName].push(oldObj);
                    }
                    const value = this.xmlToJson(item);
                    if (Object.keys(value).length > 0 || typeof value === "string") {
                        obj[nodeName].push(value);
                    }
                }
            }
        }
        
        return obj;
    },
    
    /**
     * Converts ESRI map configuration from XML to TerraFlow format
     * 
     * @param {string} xmlString - XML configuration string
     * @return {Object} - Configuration in TerraFlow format
     */
    convertEsriConfig: function(xmlString) {
        const config = this.parseXmlConfig(xmlString);
        const esriConfig = config.EsriMapModuleSettings || {};
        
        // Extract base layers
        const baseLayers = [];
        if (esriConfig.BaseLayers && esriConfig.BaseLayers.BaseLayerModel) {
            const layers = Array.isArray(esriConfig.BaseLayers.BaseLayerModel) 
                ? esriConfig.BaseLayers.BaseLayerModel 
                : [esriConfig.BaseLayers.BaseLayerModel];
                
            layers.forEach(layer => {
                baseLayers.push({
                    name: layer.Name,
                    url: layer.URL,
                    type: layer.Type,
                    visible: layer.Visible === "true",
                    spatialReferenceID: parseInt(layer.SpatialReferenceID || "0", 10)
                });
            });
        }
        
        // Extract viewable layers
        const viewableLayers = [];
        if (esriConfig.ViewableLayers && esriConfig.ViewableLayers.CciLayerModel) {
            const layers = Array.isArray(esriConfig.ViewableLayers.CciLayerModel) 
                ? esriConfig.ViewableLayers.CciLayerModel 
                : [esriConfig.ViewableLayers.CciLayerModel];
                
            layers.forEach(layer => {
                viewableLayers.push({
                    name: layer.Name,
                    url: layer.URL,
                    type: layer.Type,
                    visible: layer.Visible === "true",
                    enableSelection: layer.EnableSelection === "true",
                    selectionLayerID: parseInt(layer.SelectionLayerID || "0", 10),
                    order: parseInt(layer.Order || "0", 10)
                });
            });
        }
        
        // Extract map extent
        let mapExtent = null;
        if (esriConfig.MapExtent) {
            mapExtent = {
                spatialReferenceWKID: parseInt(esriConfig.MapExtent.SpatialReferenceWKID || "3857", 10),
                xMin: parseFloat(esriConfig.MapExtent.XMin || "-180"),
                yMin: parseFloat(esriConfig.MapExtent.YMin || "-90"),
                xMax: parseFloat(esriConfig.MapExtent.XMax || "180"),
                yMax: parseFloat(esriConfig.MapExtent.YMax || "90")
            };
        }
        
        // Return converted config
        return {
            baseLayers,
            viewableLayers,
            mapExtent,
            gisFieldName: esriConfig.GISPINFieldName || "Prop_ID",
            geometryServerURL: esriConfig.ESRIGeometryServerURL || "",
            spatialFilter: esriConfig.SpatialFilter || "",
            selectionFillOpacity: parseFloat(esriConfig.SelectionFillOpacity || "0.15"),
            selectionBorderThickness: parseInt(esriConfig.SelectedBorderThickness || "1", 10),
            selectionBorderColor: esriConfig.SelectionBorderColor || "0,255,255",
            showScaleBar: esriConfig.ShowScaleBar === "true",
            legalText: esriConfig.LegalText || "",
            mapTitle: esriConfig.MapTitle || "TerraFlow Map"
        };
    },
    
    /**
     * Converts Google map configuration from XML to TerraFlow format
     * 
     * @param {string} xmlString - XML configuration string
     * @return {Object} - Configuration in TerraFlow format
     */
    convertGoogleConfig: function(xmlString) {
        const config = this.parseXmlConfig(xmlString);
        const googleConfig = config.GoogleMapModuleSettings || {};
        
        return {
            apiKey: googleConfig.GoogleAPIKey || "",
            allowDevTools: googleConfig.AllowDevTools === "true"
        };
    },
    
    /**
     * Formats a coordinate for display
     * 
     * @param {number} coord - The coordinate value
     * @param {string} type - Either 'lat' or 'lng'
     * @param {string} format - Format to use ('dms' for degrees, minutes, seconds or 'dd' for decimal degrees)
     * @return {string} - Formatted coordinate string
     */
    formatCoordinate: function(coord, type, format = 'dms') {
        if (format === 'dd') {
            return coord.toFixed(6) + '°' + (type === 'lat' ? (coord >= 0 ? 'N' : 'S') : (coord >= 0 ? 'E' : 'W'));
        }
        
        // Convert to degrees, minutes, seconds
        const absolute = Math.abs(coord);
        const degrees = Math.floor(absolute);
        const minutesNotTruncated = (absolute - degrees) * 60;
        const minutes = Math.floor(minutesNotTruncated);
        const seconds = ((minutesNotTruncated - minutes) * 60).toFixed(2);
        
        const direction = type === 'lat' 
            ? (coord >= 0 ? 'N' : 'S') 
            : (coord >= 0 ? 'E' : 'W');
            
        return `${degrees}° ${minutes}' ${seconds}" ${direction}`;
    },
    
    /**
     * Calculate the area of a polygon in square meters
     * 
     * @param {Array<Array<number>>} coordinates - Array of [lng, lat] coordinate pairs
     * @return {number} - Area in square meters
     */
    calculatePolygonArea: function(coordinates) {
        // Implementation of the Shoelace formula (Gauss's area formula)
        if (coordinates.length < 3) {
            return 0;
        }
        
        let area = 0;
        for (let i = 0; i < coordinates.length; i++) {
            const j = (i + 1) % coordinates.length;
            area += coordinates[i][0] * coordinates[j][1];
            area -= coordinates[j][0] * coordinates[i][1];
        }
        
        area = Math.abs(area) / 2;
        
        // Convert to meters using approximate conversion factor
        // This is a simplified estimation and works best for small areas
        const lat = coordinates.reduce((sum, coord) => sum + coord[1], 0) / coordinates.length;
        const lonPerMeter = 0.000009;
        const latPerMeter = 0.000009;
        const metersPerDegree = 111319.9; // at the equator
        
        const latRadians = lat * Math.PI / 180;
        const areaMeters = area * Math.pow(metersPerDegree, 2) * Math.cos(latRadians);
        
        return areaMeters;
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapUtils;
}