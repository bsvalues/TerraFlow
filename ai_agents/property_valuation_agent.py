"""
Property Valuation Agent

This agent uses AI to provide accurate property valuations based on various data points,
including comparable properties, market trends, and property attributes.
"""

import os
import logging
import json
import datetime
import time
import threading
import queue
from typing import Dict, List, Any, Optional, Union, Tuple

from app import db
from ai_agents.base_agent import AIAgent

# Import OpenAI for advanced analytics
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

class PropertyValuationAgent(AIAgent):
    """
    AI agent that analyzes property data and market trends to provide accurate
    property valuations using artificial intelligence and machine learning.
    """
    
    def __init__(self, agent_id: str, name: str = None, description: str = None,
                market_update_interval: int = 86400, **kwargs):
        """
        Initialize the Property Valuation Agent.
        
        Args:
            agent_id: Unique ID for the agent
            name: Name of the agent
            description: Description of the agent
            market_update_interval: Interval in seconds for market data updates (default: 1 day)
        """
        super().__init__(
            agent_id=agent_id,
            name=name or "PropertyValuationAgent",
            description=description or "Provides AI-powered property valuations",
            capabilities=["property_valuation", "market_analysis", "comparable_properties"]
        )
        
        # Agent configuration
        self.market_update_interval = market_update_interval
        self.last_market_update = 0
        self.agent_thread = None
        self.running = False
        self.agent_type = "property_valuation"
        
        # OpenAI client for advanced analytics
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Market data and valuation models
        self.market_trends = {}
        self.comparable_properties = {}
        self.valuation_cache = {}
        
        logger.info(f"Property Valuation Agent initialized: {self.name}")
    
    def start(self):
        """Start the agent's background processing"""
        if self.status != "initialized" and self.status != "stopped":
            logger.warning(f"Cannot start agent {self.agent_id} from status {self.status}")
            return
        
        self.running = True
        self.status = "running"
        
        # Start the main agent thread
        self.agent_thread = threading.Thread(target=self._agent_loop)
        self.agent_thread.daemon = True
        self.agent_thread.start()
        
        logger.info(f"Property Valuation Agent started: {self.name}")
    
    def stop(self):
        """Stop the agent's background processing"""
        if self.status != "running":
            logger.warning(f"Cannot stop agent {self.agent_id} from status {self.status}")
            return
        
        self.running = False
        if self.agent_thread:
            self.agent_thread.join(timeout=2.0)
        
        self.status = "stopped"
        logger.info(f"Property Valuation Agent stopped: {self.name}")
    
    def _agent_loop(self):
        """Main agent processing loop"""
        try:
            while self.running:
                # Process incoming messages
                self._process_messages()
                
                # Update market data periodically
                current_time = time.time()
                if current_time - self.last_market_update >= self.market_update_interval:
                    self._update_market_data()
                    self.last_market_update = current_time
                
                # Sleep briefly to prevent CPU overuse
                time.sleep(1.0)
                
        except Exception as e:
            logger.error(f"Error in agent loop for {self.name}: {str(e)}")
            self.status = "error"
    
    def _process_messages(self):
        """Process messages from the message queue"""
        try:
            # Check if there are messages without blocking
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                
                # Handle different message types
                if message.get("type") == "command":
                    self._handle_command(message)
                elif message.get("type") == "valuation_request":
                    self._handle_valuation_request(message)
                elif message.get("type") == "market_data":
                    self._handle_market_data(message)
                
                # Mark message as processed
                self.message_queue.task_done()
                
        except queue.Empty:
            # No messages in queue
            pass
        except Exception as e:
            logger.error(f"Error processing messages for {self.name}: {str(e)}")
    
    def _handle_command(self, message: Dict[str, Any]):
        """Handle command messages"""
        command = message.get("command")
        
        if command == "update_market_now":
            # Trigger immediate market data update
            self._update_market_data()
        elif command == "clear_cache":
            # Clear the valuation cache
            self.valuation_cache = {}
            logger.info("Cleared valuation cache")
    
    def _handle_valuation_request(self, message: Dict[str, Any]):
        """Handle property valuation request"""
        try:
            property_id = message.get("property_id")
            valuation_type = message.get("valuation_type", "standard")
            
            if not property_id:
                raise ValueError("Missing property_id in valuation request")
            
            # Perform valuation
            if valuation_type == "detailed":
                valuation = self._perform_detailed_valuation(property_id)
            elif valuation_type == "quick":
                valuation = self._perform_quick_valuation(property_id)
            else:
                valuation = self._perform_standard_valuation(property_id)
            
            # Send response if callback is provided
            callback_id = message.get("callback_id")
            if callback_id:
                response = {
                    "type": "valuation_result",
                    "callback_id": callback_id,
                    "property_id": property_id,
                    "valuation": valuation,
                    "timestamp": time.time()
                }
                self._send_response(message.get("sender"), response)
        
        except Exception as e:
            logger.error(f"Error handling valuation request: {str(e)}")
            # Send error response if callback is provided
            callback_id = message.get("callback_id")
            if callback_id:
                error_response = {
                    "type": "valuation_error",
                    "callback_id": callback_id,
                    "error": str(e),
                    "timestamp": time.time()
                }
                self._send_response(message.get("sender"), error_response)
    
    def _handle_market_data(self, message: Dict[str, Any]):
        """Handle market data update message"""
        data = message.get("data")
        data_type = message.get("data_type")
        
        if data and data_type:
            if data_type == "market_trends":
                self.market_trends.update(data)
            elif data_type == "comparable_sales":
                self.comparable_properties.update(data)
            
            logger.info(f"Updated {data_type} with {len(data)} records")
    
    def _send_response(self, recipient: str, response: Dict[str, Any]):
        """Send response message to another agent"""
        from ai_agents.agent_manager import agent_manager
        if recipient and agent_manager.agent_exists(recipient):
            agent_manager.send_message_to_agent(recipient, response)
    
    def _update_market_data(self):
        """Update market trends and comparable property data"""
        try:
            # Fetch market trends
            market_trends = self._fetch_market_trends()
            if market_trends:
                self.market_trends = market_trends
            
            # Fetch recent sales data
            comparable_sales = self._fetch_comparable_sales()
            if comparable_sales:
                self.comparable_properties = comparable_sales
            
            logger.info("Updated market data successfully")
            
        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")
    
    def _fetch_market_trends(self) -> Dict[str, Any]:
        """Fetch current market trends from the database"""
        try:
            with db.session() as session:
                # Query market trend data
                # This is just a sample query - actual implementation would depend on your schema
                query = """
                SELECT 
                    property_type, 
                    AVG(price_per_sqft) as avg_price_per_sqft,
                    MAX(sale_date) as latest_date,
                    COUNT(*) as sale_count
                FROM comparable_sales
                WHERE sale_date >= :cutoff_date
                GROUP BY property_type
                """
                
                # 180 days ago
                cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=180)
                
                result = session.execute(query, {"cutoff_date": cutoff_date})
                
                # Convert to dictionary keyed by property type
                trends = {}
                for row in result.mappings():
                    property_type = row.get('property_type')
                    if property_type:
                        trends[property_type] = {
                            "avg_price_per_sqft": float(row.get('avg_price_per_sqft', 0)),
                            "latest_date": row.get('latest_date').isoformat() if row.get('latest_date') else None,
                            "sale_count": int(row.get('sale_count', 0))
                        }
                
                return trends
                
        except Exception as e:
            logger.error(f"Error fetching market trends: {str(e)}")
            return {}
    
    def _fetch_comparable_sales(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch recent comparable property sales from the database"""
        try:
            with db.session() as session:
                # Query recent sales data
                query = """
                SELECT 
                    id, property_id, address, city, state, zip_code, 
                    sale_price, sale_date, property_type, year_built,
                    bedrooms, bathrooms, total_area, lot_size
                FROM comparable_sales
                WHERE sale_date >= :cutoff_date
                ORDER BY sale_date DESC
                LIMIT 1000
                """
                
                # 365 days ago
                cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=365)
                
                result = session.execute(query, {"cutoff_date": cutoff_date})
                
                # Group by zip code for faster lookup
                comparables_by_zip = {}
                for row in result.mappings():
                    zip_code = row.get('zip_code')
                    if zip_code:
                        if zip_code not in comparables_by_zip:
                            comparables_by_zip[zip_code] = []
                        
                        # Convert to dictionary
                        comparable = dict(row)
                        
                        # Format date as ISO string
                        if comparable.get('sale_date'):
                            comparable['sale_date'] = comparable['sale_date'].isoformat()
                        
                        comparables_by_zip[zip_code].append(comparable)
                
                return comparables_by_zip
                
        except Exception as e:
            logger.error(f"Error fetching comparable sales: {str(e)}")
            return {}
    
    def _perform_standard_valuation(self, property_id: str) -> Dict[str, Any]:
        """
        Perform a standard property valuation.
        Uses comparable sales and property attributes to estimate value.
        """
        # Check cache first
        cache_key = f"standard_{property_id}"
        if cache_key in self.valuation_cache:
            cached = self.valuation_cache[cache_key]
            if time.time() - cached.get('timestamp', 0) < 86400:  # Cache for 1 day
                return cached
        
        try:
            # Fetch property data
            property_data = self._fetch_property_data(property_id)
            if not property_data:
                raise ValueError(f"Property not found: {property_id}")
            
            # Find comparable properties
            comparables = self._find_comparable_properties(property_data)
            
            # Calculate valuation based on comparables
            if comparables:
                # Calculate average price per square foot from comparables
                total_price_per_sqft = 0
                count = 0
                
                for comp in comparables:
                    if comp.get('total_area') and comp.get('total_area') > 0 and comp.get('sale_price'):
                        price_per_sqft = comp.get('sale_price') / comp.get('total_area')
                        total_price_per_sqft += price_per_sqft
                        count += 1
                
                if count > 0:
                    avg_price_per_sqft = total_price_per_sqft / count
                    
                    # Apply property area to get base valuation
                    base_valuation = avg_price_per_sqft * property_data.get('total_area', 0)
                    
                    # Apply adjustments based on property attributes
                    adjusted_valuation = self._apply_valuation_adjustments(base_valuation, property_data, comparables)
                    
                    # Create valuation result
                    valuation_result = {
                        "property_id": property_id,
                        "valuation_type": "standard",
                        "estimated_value": adjusted_valuation,
                        "confidence": min(0.9, 0.5 + (0.1 * min(count, 5))),  # More comparables = higher confidence
                        "comparable_count": count,
                        "avg_price_per_sqft": avg_price_per_sqft,
                        "valuation_date": datetime.datetime.utcnow().isoformat(),
                        "timestamp": time.time()
                    }
                    
                    # Cache the result
                    self.valuation_cache[cache_key] = valuation_result
                    
                    return valuation_result
            
            # If we don't have enough comparables, use AI to assist
            return self._perform_ai_valuation(property_data)
            
        except Exception as e:
            logger.error(f"Error performing standard valuation for {property_id}: {str(e)}")
            return {
                "property_id": property_id,
                "valuation_type": "standard",
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _perform_detailed_valuation(self, property_id: str) -> Dict[str, Any]:
        """
        Perform a detailed property valuation with more comprehensive analysis.
        Uses more factors and AI insights for a thorough valuation.
        """
        # Check cache first
        cache_key = f"detailed_{property_id}"
        if cache_key in self.valuation_cache:
            cached = self.valuation_cache[cache_key]
            if time.time() - cached.get('timestamp', 0) < 86400:  # Cache for 1 day
                return cached
        
        try:
            # Start with standard valuation
            standard_valuation = self._perform_standard_valuation(property_id)
            
            if standard_valuation.get('status') == 'error':
                return standard_valuation
            
            # Fetch property data
            property_data = self._fetch_property_data(property_id)
            if not property_data:
                raise ValueError(f"Property not found: {property_id}")
            
            # Enhance with AI analysis
            ai_analysis = self._analyze_property_with_ai(property_data, standard_valuation)
            
            # Create detailed valuation result
            detailed_valuation = {
                "property_id": property_id,
                "valuation_type": "detailed",
                "estimated_value": ai_analysis.get('adjusted_value', standard_valuation.get('estimated_value')),
                "value_range": ai_analysis.get('value_range', {
                    "low": standard_valuation.get('estimated_value') * 0.95,
                    "high": standard_valuation.get('estimated_value') * 1.05
                }),
                "confidence": ai_analysis.get('confidence', standard_valuation.get('confidence')),
                "comparable_count": standard_valuation.get('comparable_count'),
                "influencing_factors": ai_analysis.get('influencing_factors', []),
                "market_trends": ai_analysis.get('market_trends', {}),
                "recommendation": ai_analysis.get('recommendation', ''),
                "valuation_date": datetime.datetime.utcnow().isoformat(),
                "timestamp": time.time()
            }
            
            # Cache the result
            self.valuation_cache[cache_key] = detailed_valuation
            
            return detailed_valuation
            
        except Exception as e:
            logger.error(f"Error performing detailed valuation for {property_id}: {str(e)}")
            return {
                "property_id": property_id,
                "valuation_type": "detailed",
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _perform_quick_valuation(self, property_id: str) -> Dict[str, Any]:
        """
        Perform a quick property valuation with less precision but faster results.
        Uses simplified methods and fewer comparables for speed.
        """
        # Check cache first
        cache_key = f"quick_{property_id}"
        if cache_key in self.valuation_cache:
            cached = self.valuation_cache[cache_key]
            if time.time() - cached.get('timestamp', 0) < 86400:  # Cache for 1 day
                return cached
        
        try:
            # Fetch property data
            property_data = self._fetch_property_data(property_id)
            if not property_data:
                raise ValueError(f"Property not found: {property_id}")
            
            # Use market averages for quick valuation
            property_type = property_data.get('property_type')
            total_area = property_data.get('total_area', 0)
            
            if property_type in self.market_trends and total_area > 0:
                # Get average price per square foot for this property type
                avg_price_per_sqft = self.market_trends[property_type].get('avg_price_per_sqft', 0)
                
                # Calculate basic valuation
                estimated_value = avg_price_per_sqft * total_area
                
                # Apply a basic adjustment based on property age
                year_built = property_data.get('year_built', 0)
                current_year = datetime.datetime.utcnow().year
                
                if year_built > 0:
                    age = current_year - year_built
                    # Newer properties get a premium, older properties get a discount
                    if age < 5:
                        age_factor = 1.15  # 15% premium for very new
                    elif age < 10:
                        age_factor = 1.10  # 10% premium for newer
                    elif age < 20:
                        age_factor = 1.05  # 5% premium for relatively new
                    elif age < 40:
                        age_factor = 1.0   # No adjustment for average age
                    elif age < 60:
                        age_factor = 0.95  # 5% discount for older
                    else:
                        age_factor = 0.90  # 10% discount for very old
                    
                    estimated_value *= age_factor
                
                # Create quick valuation result
                valuation_result = {
                    "property_id": property_id,
                    "valuation_type": "quick",
                    "estimated_value": estimated_value,
                    "confidence": 0.7,  # Lower confidence for quick valuation
                    "avg_price_per_sqft": avg_price_per_sqft,
                    "valuation_date": datetime.datetime.utcnow().isoformat(),
                    "timestamp": time.time()
                }
                
                # Cache the result
                self.valuation_cache[cache_key] = valuation_result
                
                return valuation_result
            
            # Fallback to standard valuation if we don't have market data
            return self._perform_standard_valuation(property_id)
            
        except Exception as e:
            logger.error(f"Error performing quick valuation for {property_id}: {str(e)}")
            return {
                "property_id": property_id,
                "valuation_type": "quick",
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _fetch_property_data(self, property_id: str) -> Dict[str, Any]:
        """Fetch property data from the database"""
        try:
            with db.session() as session:
                query = """
                SELECT 
                    id, parcel_id, address, city, state, zip_code, property_type, 
                    lot_size, year_built, bedrooms, bathrooms, total_area, 
                    owner_name, purchase_date, purchase_price, features,
                    location, property_metadata
                FROM properties
                WHERE id = :property_id
                LIMIT 1
                """
                
                result = session.execute(query, {"property_id": property_id})
                property_data = result.mappings().first()
                
                if property_data:
                    # Convert to dictionary
                    property_dict = dict(property_data)
                    
                    # Parse JSON fields
                    for field in ['features', 'location', 'property_metadata']:
                        if property_dict.get(field) and isinstance(property_dict[field], str):
                            try:
                                property_dict[field] = json.loads(property_dict[field])
                            except:
                                property_dict[field] = {}
                    
                    # Format date fields
                    if property_dict.get('purchase_date'):
                        property_dict['purchase_date'] = property_dict['purchase_date'].isoformat()
                    
                    return property_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Error fetching property data for {property_id}: {str(e)}")
            return None
    
    def _find_comparable_properties(self, property_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find comparable properties for valuation"""
        if not property_data:
            return []
        
        zip_code = property_data.get('zip_code')
        property_type = property_data.get('property_type')
        
        if not zip_code or not property_type:
            return []
        
        # Get comparable sales in the same zip code
        zip_comparables = self.comparable_properties.get(zip_code, [])
        
        if not zip_comparables:
            return []
        
        # Filter by property type
        type_filtered = [comp for comp in zip_comparables 
                       if comp.get('property_type') == property_type]
        
        # If we don't have enough of the same type, include other types
        if len(type_filtered) < 3:
            type_filtered = zip_comparables
        
        # Calculate similarity scores
        scored_comparables = []
        for comp in type_filtered:
            similarity = self._calculate_property_similarity(property_data, comp)
            scored_comparables.append((similarity, comp))
        
        # Sort by similarity (highest first)
        scored_comparables.sort(reverse=True, key=lambda x: x[0])
        
        # Return top 10 most similar
        return [comp for score, comp in scored_comparables[:10]]
    
    def _calculate_property_similarity(self, property_data: Dict[str, Any], 
                                      comparable: Dict[str, Any]) -> float:
        """
        Calculate similarity score between two properties.
        Higher score means more similar.
        """
        # Start with a base similarity
        similarity = 0.5
        
        # Same property type is a big plus
        if property_data.get('property_type') == comparable.get('property_type'):
            similarity += 0.2
        
        # Compare bedrooms (if available)
        if 'bedrooms' in property_data and 'bedrooms' in comparable:
            bed_diff = abs(property_data['bedrooms'] - comparable['bedrooms'])
            if bed_diff == 0:
                similarity += 0.1
            elif bed_diff == 1:
                similarity += 0.05
        
        # Compare bathrooms (if available)
        if 'bathrooms' in property_data and 'bathrooms' in comparable:
            bath_diff = abs(property_data['bathrooms'] - comparable['bathrooms'])
            if bath_diff < 0.5:
                similarity += 0.1
            elif bath_diff < 1:
                similarity += 0.05
        
        # Compare total area (if available)
        if 'total_area' in property_data and 'total_area' in comparable and property_data['total_area'] > 0:
            area_ratio = comparable['total_area'] / property_data['total_area']
            if 0.9 <= area_ratio <= 1.1:
                similarity += 0.15  # Within 10% size
            elif 0.8 <= area_ratio <= 1.2:
                similarity += 0.1   # Within 20% size
            elif 0.7 <= area_ratio <= 1.3:
                similarity += 0.05  # Within 30% size
        
        # Compare year built (if available)
        if 'year_built' in property_data and 'year_built' in comparable and property_data['year_built'] > 0:
            year_diff = abs(property_data['year_built'] - comparable['year_built'])
            if year_diff < 5:
                similarity += 0.1  # Built within 5 years
            elif year_diff < 10:
                similarity += 0.05  # Built within 10 years
        
        # Recency of sale matters
        if 'sale_date' in comparable:
            try:
                sale_date = datetime.datetime.fromisoformat(comparable['sale_date']) \
                            if isinstance(comparable['sale_date'], str) else comparable['sale_date']
                days_since_sale = (datetime.datetime.utcnow() - sale_date).days
                
                if days_since_sale < 90:
                    similarity += 0.1  # Recent sale (< 3 months)
                elif days_since_sale < 180:
                    similarity += 0.05  # Somewhat recent (< 6 months)
            except:
                pass
        
        return similarity
    
    def _apply_valuation_adjustments(self, base_valuation: float, 
                                   property_data: Dict[str, Any],
                                   comparables: List[Dict[str, Any]]) -> float:
        """Apply adjustments to the base valuation based on property attributes"""
        adjusted_valuation = base_valuation
        
        # Apply adjustments for age of property
        year_built = property_data.get('year_built', 0)
        current_year = datetime.datetime.utcnow().year
        
        if year_built > 0:
            age = current_year - year_built
            # Calculate average age of comparables
            comp_ages = []
            for comp in comparables:
                if comp.get('year_built', 0) > 0:
                    comp_ages.append(current_year - comp.get('year_built'))
            
            if comp_ages:
                avg_comp_age = sum(comp_ages) / len(comp_ages)
                
                # Adjust based on age difference
                age_diff = age - avg_comp_age
                if age_diff < -10:
                    # Property is much newer than comparables
                    adjusted_valuation *= 1.05
                elif age_diff < -5:
                    # Property is newer than comparables
                    adjusted_valuation *= 1.025
                elif age_diff > 10:
                    # Property is much older than comparables
                    adjusted_valuation *= 0.95
                elif age_diff > 5:
                    # Property is older than comparables
                    adjusted_valuation *= 0.975
        
        # Apply adjustments for lot size
        lot_size = property_data.get('lot_size', 0)
        if lot_size > 0:
            # Calculate average lot size of comparables
            comp_lot_sizes = []
            for comp in comparables:
                if comp.get('lot_size', 0) > 0:
                    comp_lot_sizes.append(comp.get('lot_size'))
            
            if comp_lot_sizes:
                avg_comp_lot_size = sum(comp_lot_sizes) / len(comp_lot_sizes)
                
                # Adjust based on lot size difference
                lot_size_ratio = lot_size / avg_comp_lot_size if avg_comp_lot_size > 0 else 1
                
                if lot_size_ratio > 1.3:
                    # Much larger lot
                    adjusted_valuation *= 1.05
                elif lot_size_ratio > 1.15:
                    # Larger lot
                    adjusted_valuation *= 1.025
                elif lot_size_ratio < 0.7:
                    # Much smaller lot
                    adjusted_valuation *= 0.95
                elif lot_size_ratio < 0.85:
                    # Smaller lot
                    adjusted_valuation *= 0.975
        
        # Apply adjustments for special features
        features = property_data.get('features', {})
        if features:
            # Premium features
            premium_features = ['pool', 'view', 'waterfront', 'gourmet_kitchen', 
                               'smart_home', 'solar_panels', 'high_end_finishes']
            
            feature_count = sum(1 for f in premium_features if features.get(f))
            if feature_count >= 3:
                # Multiple premium features
                adjusted_valuation *= 1.08
            elif feature_count >= 1:
                # At least one premium feature
                adjusted_valuation *= 1.03
        
        # Return the adjusted valuation
        return adjusted_valuation
    
    def _perform_ai_valuation(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to perform property valuation when traditional methods lack data.
        """
        try:
            # Prepare property data for the AI prompt
            property_type = property_data.get('property_type', 'unknown')
            zip_code = property_data.get('zip_code', 'unknown')
            total_area = property_data.get('total_area', 0)
            bedrooms = property_data.get('bedrooms', 0)
            bathrooms = property_data.get('bathrooms', 0)
            year_built = property_data.get('year_built', 0)
            lot_size = property_data.get('lot_size', 0)
            
            # Get regional market data if available
            market_data = "No detailed market data available."
            if property_type in self.market_trends:
                market_data = f"Average price per square foot for {property_type} properties: ${self.market_trends[property_type].get('avg_price_per_sqft', 0):.2f}\n"
                market_data += f"Based on {self.market_trends[property_type].get('sale_count', 0)} recent sales."
            
            # Create prompt for OpenAI
            prompt = f"""
            I need a property valuation for a {property_type} property with the following details:
            - Location: ZIP code {zip_code}
            - Square footage: {total_area}
            - Bedrooms: {bedrooms}
            - Bathrooms: {bathrooms}
            - Year built: {year_built}
            - Lot size: {lot_size} square feet
            
            Current market information:
            {market_data}
            
            Property features:
            {json.dumps(property_data.get('features', {}), indent=2)}
            
            Please provide:
            1. An estimated property value
            2. Value range (minimum and maximum)
            3. Confidence level (0-1 scale)
            4. Key factors influencing the valuation
            
            Format your response as a JSON object with these keys: estimated_value, value_range, confidence, influencing_factors
            """
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {"role": "system", "content": "You are an expert real estate appraiser with deep knowledge of property valuation techniques."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            valuation = json.loads(response.choices[0].message.content)
            
            # Create AI valuation result
            valuation_result = {
                "property_id": property_data.get('id'),
                "valuation_type": "ai_assisted",
                "estimated_value": valuation.get('estimated_value'),
                "value_range": valuation.get('value_range', {
                    "low": valuation.get('estimated_value') * 0.9,
                    "high": valuation.get('estimated_value') * 1.1
                }),
                "confidence": valuation.get('confidence', 0.7),
                "influencing_factors": valuation.get('influencing_factors', []),
                "ai_assisted": True,
                "valuation_date": datetime.datetime.utcnow().isoformat(),
                "timestamp": time.time()
            }
            
            return valuation_result
            
        except Exception as e:
            logger.error(f"Error performing AI valuation: {str(e)}")
            return {
                "property_id": property_data.get('id'),
                "valuation_type": "ai_assisted",
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _analyze_property_with_ai(self, property_data: Dict[str, Any], 
                                standard_valuation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to provide enhanced property analysis beyond standard valuation.
        """
        try:
            # Prepare property data for the AI prompt
            property_type = property_data.get('property_type', 'unknown')
            zip_code = property_data.get('zip_code', 'unknown')
            total_area = property_data.get('total_area', 0)
            bedrooms = property_data.get('bedrooms', 0)
            bathrooms = property_data.get('bathrooms', 0)
            year_built = property_data.get('year_built', 0)
            lot_size = property_data.get('lot_size', 0)
            
            # Get standard valuation details
            estimated_value = standard_valuation.get('estimated_value', 0)
            
            # Get regional market data if available
            market_data = "No detailed market data available."
            if property_type in self.market_trends:
                market_data = f"Average price per square foot for {property_type} properties: ${self.market_trends[property_type].get('avg_price_per_sqft', 0):.2f}\n"
                market_data += f"Based on {self.market_trends[property_type].get('sale_count', 0)} recent sales."
            
            # Create prompt for OpenAI
            prompt = f"""
            I need a detailed property analysis for a {property_type} property with the following details:
            - Location: ZIP code {zip_code}
            - Square footage: {total_area}
            - Bedrooms: {bedrooms}
            - Bathrooms: {bathrooms}
            - Year built: {year_built}
            - Lot size: {lot_size} square feet
            - Standard valuation estimate: ${estimated_value:,.2f}
            
            Current market information:
            {market_data}
            
            Property features:
            {json.dumps(property_data.get('features', {}), indent=2)}
            
            Please provide:
            1. An adjusted property value based on your analysis
            2. Value range (minimum and maximum)
            3. Confidence level (0-1 scale)
            4. Key factors influencing the valuation
            5. Current market trends for this property type
            6. Investment recommendation (hold, sell, improve)
            
            Format your response as a JSON object with these keys: adjusted_value, value_range, confidence, influencing_factors, market_trends, recommendation
            """
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {"role": "system", "content": "You are an expert real estate analyst with deep knowledge of property valuation and market trends."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            analysis = json.loads(response.choices[0].message.content)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error performing AI property analysis: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_property_valuation(self, property_id: str, valuation_type: str = "standard") -> Dict[str, Any]:
        """
        Get a property valuation (public API method).
        
        Args:
            property_id: ID of the property to valuate
            valuation_type: Type of valuation to perform (standard, detailed, quick)
            
        Returns:
            Valuation result dictionary
        """
        if valuation_type == "detailed":
            return self._perform_detailed_valuation(property_id)
        elif valuation_type == "quick":
            return self._perform_quick_valuation(property_id)
        else:
            return self._perform_standard_valuation(property_id)