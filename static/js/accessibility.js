/**
 * Accessibility Controls for GeoAssessmentPro
 * Handles the accessibility panel and user preference storage
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize accessibility panel
  initAccessibilityPanel();
  
  // Load saved preferences
  loadAccessibilityPreferences();
});

/**
 * Initialize the accessibility panel functionality
 */
function initAccessibilityPanel() {
  const panel = document.querySelector('.a11y-panel');
  const toggleButton = document.getElementById('toggle-a11y-panel');
  const highContrastButton = document.getElementById('toggle-high-contrast');
  const largeTextButton = document.getElementById('toggle-large-text');
  const reduceMotionButton = document.getElementById('toggle-reduce-motion');
  
  if (!panel || !toggleButton) return;
  
  // Toggle panel visibility
  toggleButton.addEventListener('click', function() {
    panel.classList.toggle('active');
    
    // Set ARIA expanded state
    const isExpanded = panel.classList.contains('active');
    toggleButton.setAttribute('aria-expanded', isExpanded);
    
    // Focus on first option when opening
    if (isExpanded && highContrastButton) {
      setTimeout(() => {
        highContrastButton.focus();
      }, 100);
    }
  });
  
  // Close panel when clicking outside
  document.addEventListener('click', function(event) {
    if (panel.classList.contains('active') && 
        !panel.contains(event.target) && 
        event.target !== toggleButton) {
      panel.classList.remove('active');
      toggleButton.setAttribute('aria-expanded', false);
    }
  });
  
  // Handle high contrast toggle
  if (highContrastButton) {
    highContrastButton.addEventListener('click', function() {
      document.body.classList.toggle('high-contrast-mode');
      highContrastButton.classList.toggle('active');
      
      // Save preference
      localStorage.setItem('high-contrast-mode', 
                           document.body.classList.contains('high-contrast-mode'));
                           
      // Dispatch event for other components to react
      document.dispatchEvent(new CustomEvent('toggleContrast'));
    });
  }
  
  // Handle large text toggle
  if (largeTextButton) {
    largeTextButton.addEventListener('click', function() {
      document.body.classList.toggle('large-text-mode');
      largeTextButton.classList.toggle('active');
      
      // Save preference
      localStorage.setItem('large-text-mode', 
                          document.body.classList.contains('large-text-mode'));
    });
  }
  
  // Handle reduce motion toggle
  if (reduceMotionButton) {
    reduceMotionButton.addEventListener('click', function() {
      document.body.classList.toggle('reduced-motion-mode');
      reduceMotionButton.classList.toggle('active');
      
      // Save preference
      localStorage.setItem('reduced-motion-mode', 
                          document.body.classList.contains('reduced-motion-mode'));
    });
  }
  
  // Handle Escape key to close panel
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && panel.classList.contains('active')) {
      panel.classList.remove('active');
      toggleButton.setAttribute('aria-expanded', false);
      toggleButton.focus();
    }
  });
  
  // Add proper ARIA attributes
  toggleButton.setAttribute('aria-controls', 'a11y-panel-content');
  toggleButton.setAttribute('aria-expanded', false);
  toggleButton.setAttribute('aria-haspopup', true);
}

/**
 * Load saved accessibility preferences from localStorage
 */
function loadAccessibilityPreferences() {
  // High contrast mode
  if (localStorage.getItem('high-contrast-mode') === 'true') {
    document.body.classList.add('high-contrast-mode');
    const highContrastButton = document.getElementById('toggle-high-contrast');
    if (highContrastButton) {
      highContrastButton.classList.add('active');
    }
  }
  
  // Large text mode
  if (localStorage.getItem('large-text-mode') === 'true') {
    document.body.classList.add('large-text-mode');
    const largeTextButton = document.getElementById('toggle-large-text');
    if (largeTextButton) {
      largeTextButton.classList.add('active');
    }
  }
  
  // Reduced motion mode
  if (localStorage.getItem('reduced-motion-mode') === 'true') {
    document.body.classList.add('reduced-motion-mode');
    const reduceMotionButton = document.getElementById('toggle-reduce-motion');
    if (reduceMotionButton) {
      reduceMotionButton.classList.add('active');
    }
  }
  
  // Honor user's system preference for reduced motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion && localStorage.getItem('reduced-motion-mode') !== 'false') {
    document.body.classList.add('reduced-motion-mode');
    const reduceMotionButton = document.getElementById('toggle-reduce-motion');
    if (reduceMotionButton) {
      reduceMotionButton.classList.add('active');
    }
  }
}

/**
 * Update the map for accessibility options
 * Call this when initializing maps
 */
function updateMapAccessibility(map) {
  if (!map) return;
  
  // Listen for high contrast mode changes
  document.addEventListener('toggleContrast', function() {
    if (document.body.classList.contains('high-contrast-mode')) {
      // Update map tiles for high contrast
      if (map.getStyle) { // Mapbox
        map.setStyle('mapbox://styles/mapbox/high-contrast-v1');
      } else if (map.getPane) { // Leaflet
        // Add higher contrast borders to features
        const mapPanes = document.querySelectorAll('.leaflet-pane path, .leaflet-pane circle');
        mapPanes.forEach(el => {
          el.style.stroke = '#000';
          el.style.strokeWidth = '2px';
        });
      }
    } else {
      // Revert to default style
      if (map.getStyle) { // Mapbox
        map.setStyle('mapbox://styles/mapbox/streets-v11');
      } else if (map.getPane) { // Leaflet
        // Remove high contrast styles
        const mapPanes = document.querySelectorAll('.leaflet-pane path, .leaflet-pane circle');
        mapPanes.forEach(el => {
          el.style.stroke = '';
          el.style.strokeWidth = '';
        });
      }
    }
  });
}