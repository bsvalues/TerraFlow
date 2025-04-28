/**
 * TerraFusion Form Validation System
 * Provides a consistent approach to form validation across the application
 */

class FormValidationSystem {
  constructor() {
    this.forms = new Map();
    this.defaultOptions = {
      validateOnInput: true,
      validateOnBlur: true,
      validateOnSubmit: true,
      showValidationMessages: true,
      preventSubmitOnError: true,
      scrollToFirstError: true,
      customErrorContainer: null,
      errorClass: 'is-invalid',
      successClass: 'is-valid',
      errorMessageClass: 'invalid-feedback',
      successMessageClass: 'valid-feedback'
    };
    
    this.defaultValidators = {
      required: {
        validate: function(value) {
          if (Array.isArray(value)) {
            return value.length > 0;
          }
          return value !== null && value !== undefined && value.toString().trim() !== '';
        },
        message: 'This field is required'
      },
      email: {
        validate: function(value) {
          if (!value) return true; // Skip empty values, use required for those
          const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
          return emailRegex.test(value);
        },
        message: 'Please enter a valid email address'
      },
      minLength: {
        validate: function(value, length) {
          if (!value) return true; // Skip empty values, use required for those
          return value.toString().length >= length;
        },
        message: function(length) {
          return `Please enter at least ${length} characters`;
        }
      },
      maxLength: {
        validate: function(value, length) {
          if (!value) return true; // Skip empty values
          return value.toString().length <= length;
        },
        message: function(length) {
          return `Please enter no more than ${length} characters`;
        }
      },
      pattern: {
        validate: function(value, pattern) {
          if (!value) return true; // Skip empty values, use required for those
          const regex = new RegExp(pattern);
          return regex.test(value);
        },
        message: 'Please match the requested format'
      },
      numeric: {
        validate: function(value) {
          if (!value) return true; // Skip empty values, use required for those
          return !isNaN(parseFloat(value)) && isFinite(value);
        },
        message: 'Please enter a valid number'
      },
      integer: {
        validate: function(value) {
          if (!value) return true; // Skip empty values, use required for those
          return /^-?\d+$/.test(value);
        },
        message: 'Please enter a valid integer'
      },
      min: {
        validate: function(value, min) {
          if (!value) return true; // Skip empty values, use required for those
          const num = parseFloat(value);
          return !isNaN(num) && num >= min;
        },
        message: function(min) {
          return `Please enter a value greater than or equal to ${min}`;
        }
      },
      max: {
        validate: function(value, max) {
          if (!value) return true; // Skip empty values, use required for those
          const num = parseFloat(value);
          return !isNaN(num) && num <= max;
        },
        message: function(max) {
          return `Please enter a value less than or equal to ${max}`;
        }
      },
      equalTo: {
        validate: function(value, targetSelector) {
          if (!value) return true; // Skip empty values, use required for those
          const targetElement = document.querySelector(targetSelector);
          return targetElement && value === targetElement.value;
        },
        message: function(targetSelector) {
          const targetElement = document.querySelector(targetSelector);
          const targetLabel = targetElement ? 
            targetElement.previousElementSibling?.textContent || 'specified field' : 
            'specified field';
          return `This field must match the ${targetLabel}`;
        }
      },
      date: {
        validate: function(value) {
          if (!value) return true; // Skip empty values, use required for those
          return !isNaN(Date.parse(value));
        },
        message: 'Please enter a valid date'
      }
    };
  }
  
  /**
   * Register a form for validation
   * @param {string} formId - The ID of the form to validate
   * @param {object} options - Validation options
   * @param {object} rules - Validation rules for form fields
   * @returns {object} - The validation interface for this form
   */
  register(formId, options = {}, rules = {}) {
    const form = document.getElementById(formId);
    if (!form) {
      console.error(`Form with ID ${formId} not found`);
      return null;
    }
    
    // Merge default and custom options
    const mergedOptions = { ...this.defaultOptions, ...options };
    
    // Set up validation rules
    const validationRules = rules;
    
    // Store form info
    const formInfo = {
      element: form,
      options: mergedOptions,
      rules: validationRules,
      errors: new Map(),
      validators: { ...this.defaultValidators }
    };
    
    this.forms.set(formId, formInfo);
    
    // Set up event listeners
    this._setupEventListeners(formId);
    
    // Create validation interface for this form
    const validationInterface = this._createValidationInterface(formId);
    
    return validationInterface;
  }
  
  /**
   * Set up event listeners for a form
   * @param {string} formId - The ID of the form to set up
   * @private
   */
  _setupEventListeners(formId) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return;
    
    const { element, options, rules } = formInfo;
    
    // Handle form submission
    if (options.validateOnSubmit) {
      element.addEventListener('submit', (event) => {
        const isValid = this.validateForm(formId);
        
        if (!isValid && options.preventSubmitOnError) {
          event.preventDefault();
          
          if (options.scrollToFirstError) {
            const firstErrorField = element.querySelector('.' + options.errorClass);
            if (firstErrorField) {
              firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
              firstErrorField.focus();
            }
          }
        }
      });
    }
    
    // Add validation handlers to individual fields
    for (const fieldName in rules) {
      if (rules.hasOwnProperty(fieldName)) {
        const field = element.querySelector(`[name="${fieldName}"]`);
        if (!field) continue;
        
        // Validate on input change
        if (options.validateOnInput) {
          field.addEventListener('input', () => {
            this.validateField(formId, fieldName);
          });
        }
        
        // Validate on blur
        if (options.validateOnBlur) {
          field.addEventListener('blur', () => {
            this.validateField(formId, fieldName);
          });
        }
      }
    }
  }
  
  /**
   * Create a validation interface for a specific form
   * @param {string} formId - The ID of the form
   * @returns {object} - The validation interface
   * @private
   */
  _createValidationInterface(formId) {
    return {
      validate: () => this.validateForm(formId),
      validateField: (fieldName) => this.validateField(formId, fieldName),
      getErrors: () => this.getFormErrors(formId),
      hasErrors: () => this.hasFormErrors(formId),
      reset: () => this.resetValidation(formId),
      clearErrors: () => this.clearFormErrors(formId),
      setRules: (rules) => this.setValidationRules(formId, rules),
      addValidator: (name, validator) => this.addCustomValidator(formId, name, validator)
    };
  }
  
  /**
   * Validate an entire form
   * @param {string} formId - The ID of the form to validate
   * @returns {boolean} - True if the form is valid, false otherwise
   */
  validateForm(formId) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return false;
    
    const { rules } = formInfo;
    let isValid = true;
    
    // Clear previous errors
    this.clearFormErrors(formId);
    
    // Validate each field
    for (const fieldName in rules) {
      if (rules.hasOwnProperty(fieldName)) {
        const fieldIsValid = this.validateField(formId, fieldName);
        isValid = isValid && fieldIsValid;
      }
    }
    
    // Show errors in custom container if specified
    if (!isValid && formInfo.options.customErrorContainer) {
      const errors = this.getFormErrors(formId);
      this._displayCustomErrors(formId, errors);
    }
    
    // If integrated with our error handling system, show errors there
    if (!isValid && window.terraFusionErrors && !formInfo.options.customErrorContainer) {
      const errors = this.getFormErrors(formId);
      const errorObj = {};
      
      errors.forEach((error, field) => {
        errorObj[field] = error;
      });
      
      window.terraFusionErrors.showValidationError(formId, errorObj);
    }
    
    return isValid;
  }
  
  /**
   * Validate a specific field
   * @param {string} formId - The ID of the form
   * @param {string} fieldName - The name of the field to validate
   * @returns {boolean} - True if the field is valid, false otherwise
   */
  validateField(formId, fieldName) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return false;
    
    const { element, rules, validators, options } = formInfo;
    const field = element.querySelector(`[name="${fieldName}"]`);
    
    if (!field || !rules[fieldName]) return true;
    
    // Get field value
    let fieldValue;
    if (field.type === 'checkbox') {
      fieldValue = field.checked;
    } else if (field.type === 'radio') {
      const checkedRadio = element.querySelector(`[name="${fieldName}"]:checked`);
      fieldValue = checkedRadio ? checkedRadio.value : '';
    } else if (field.type === 'file') {
      fieldValue = field.files;
    } else if (field.multiple) {
      fieldValue = Array.from(field.selectedOptions).map(option => option.value);
    } else {
      fieldValue = field.value;
    }
    
    // Run validation rules
    const fieldRules = rules[fieldName];
    let isValid = true;
    let errorMessage = '';
    
    for (const ruleKey in fieldRules) {
      if (!fieldRules.hasOwnProperty(ruleKey)) continue;
      
      const ruleValue = fieldRules[ruleKey];
      const validator = validators[ruleKey];
      
      if (!validator) continue;
      
      let isRuleValid;
      if (ruleKey === 'custom' && typeof ruleValue === 'function') {
        // Custom validator function
        isRuleValid = ruleValue(fieldValue, field);
      } else if (validator.validate) {
        // Standard validator
        isRuleValid = validator.validate(fieldValue, ruleValue);
      } else {
        isRuleValid = true;
      }
      
      if (!isRuleValid) {
        isValid = false;
        
        if (typeof ruleValue === 'object' && ruleValue.message) {
          // Custom message in the rule
          errorMessage = ruleValue.message;
        } else if (typeof validator.message === 'function') {
          // Dynamic message from validator
          errorMessage = validator.message(ruleValue);
        } else {
          // Static message from validator
          errorMessage = validator.message;
        }
        
        break;
      }
    }
    
    // Update field state and error message
    this._updateFieldState(formId, fieldName, field, isValid, errorMessage);
    
    return isValid;
  }
  
  /**
   * Update the visual state of a field based on validation
   * @param {string} formId - The ID of the form
   * @param {string} fieldName - The name of the field
   * @param {HTMLElement} field - The field element
   * @param {boolean} isValid - Whether the field is valid
   * @param {string} errorMessage - The error message, if any
   * @private
   */
  _updateFieldState(formId, fieldName, field, isValid, errorMessage) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return;
    
    const { options, errors } = formInfo;
    
    // Remove previous state
    field.classList.remove(options.errorClass, options.successClass);
    
    // Remove previous message
    const parent = field.parentElement;
    const existingMessage = parent.querySelector(`.${options.errorMessageClass}, .${options.successMessageClass}`);
    if (existingMessage) {
      parent.removeChild(existingMessage);
    }
    
    if (isValid) {
      // Valid state
      field.classList.add(options.successClass);
      errors.delete(fieldName);
      
      // Add success message if desired
      if (options.showValidationMessages && field.getAttribute('data-success-message')) {
        const successMessage = document.createElement('div');
        successMessage.className = options.successMessageClass;
        successMessage.textContent = field.getAttribute('data-success-message');
        parent.appendChild(successMessage);
      }
    } else {
      // Invalid state
      field.classList.add(options.errorClass);
      errors.set(fieldName, errorMessage);
      
      // Add error message if desired
      if (options.showValidationMessages) {
        const errorElement = document.createElement('div');
        errorElement.className = options.errorMessageClass;
        errorElement.textContent = errorMessage;
        parent.appendChild(errorElement);
      }
    }
  }
  
  /**
   * Display errors in a custom container
   * @param {string} formId - The ID of the form
   * @param {Map} errors - The errors to display
   * @private
   */
  _displayCustomErrors(formId, errors) {
    const formInfo = this.forms.get(formId);
    if (!formInfo || !formInfo.options.customErrorContainer) return;
    
    const container = document.querySelector(formInfo.options.customErrorContainer);
    if (!container) return;
    
    // Clear previous errors
    container.innerHTML = '';
    
    if (errors.size === 0) {
      container.style.display = 'none';
      return;
    }
    
    // Create error list
    container.style.display = 'block';
    const errorList = document.createElement('ul');
    errorList.className = 'tf-validation-error-list';
    
    errors.forEach((message, fieldName) => {
      const listItem = document.createElement('li');
      
      // Try to get a more friendly field name
      const field = formInfo.element.querySelector(`[name="${fieldName}"]`);
      let friendlyName = fieldName;
      
      if (field) {
        // Try to get label text
        const label = document.querySelector(`label[for="${field.id}"]`);
        if (label) {
          friendlyName = label.textContent;
        } else {
          // Try to get from placeholder
          friendlyName = field.getAttribute('placeholder') || field.getAttribute('aria-label') || fieldName;
        }
      }
      
      listItem.innerHTML = `<strong>${friendlyName}:</strong> ${message}`;
      errorList.appendChild(listItem);
    });
    
    container.appendChild(errorList);
  }
  
  /**
   * Get all errors for a form
   * @param {string} formId - The ID of the form
   * @returns {Map} - Map of field names to error messages
   */
  getFormErrors(formId) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return new Map();
    
    return new Map(formInfo.errors);
  }
  
  /**
   * Check if a form has any validation errors
   * @param {string} formId - The ID of the form
   * @returns {boolean} - True if the form has errors, false otherwise
   */
  hasFormErrors(formId) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return false;
    
    return formInfo.errors.size > 0;
  }
  
  /**
   * Clear all validation errors for a form
   * @param {string} formId - The ID of the form
   */
  clearFormErrors(formId) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return;
    
    const { element, options, errors } = formInfo;
    
    // Clear error map
    errors.clear();
    
    // Remove error/success classes and messages
    const fields = element.querySelectorAll(`.${options.errorClass}, .${options.successClass}`);
    fields.forEach(field => {
      field.classList.remove(options.errorClass, options.successClass);
      
      const parent = field.parentElement;
      const message = parent.querySelector(`.${options.errorMessageClass}, .${options.successMessageClass}`);
      if (message) {
        parent.removeChild(message);
      }
    });
    
    // Clear custom error container if specified
    if (options.customErrorContainer) {
      const container = document.querySelector(options.customErrorContainer);
      if (container) {
        container.innerHTML = '';
        container.style.display = 'none';
      }
    }
    
    // Clear errors in error handling system if integrated
    if (window.terraFusionErrors) {
      window.terraFusionErrors.clearErrors(formId);
    }
  }
  
  /**
   * Reset form validation to initial state
   * @param {string} formId - The ID of the form
   */
  resetValidation(formId) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return;
    
    this.clearFormErrors(formId);
    
    // Reset the form itself
    formInfo.element.reset();
  }
  
  /**
   * Set validation rules for a form
   * @param {string} formId - The ID of the form
   * @param {object} rules - The validation rules
   */
  setValidationRules(formId, rules) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return;
    
    formInfo.rules = rules;
    
    // Clear existing errors
    this.clearFormErrors(formId);
  }
  
  /**
   * Add a custom validator
   * @param {string} formId - The ID of the form
   * @param {string} name - The name of the validator
   * @param {object} validator - The validator object with validate and message properties
   */
  addCustomValidator(formId, name, validator) {
    const formInfo = this.forms.get(formId);
    if (!formInfo) return;
    
    formInfo.validators[name] = validator;
  }
}

// Create global instance
const terraFusionForms = new FormValidationSystem();

// Add to window for global access
window.terraFusionForms = terraFusionForms;