// JavaScript functions for Zabbix Tag Manager

// Utility functions
function showLoading(element) {
    if (element) {
        element.classList.add('loading');
        element.disabled = true;
    }
}

function hideLoading(element) {
    if (element) {
        element.classList.remove('loading');
        element.disabled = false;
    }
}

function showNotification(type, message, duration = 5000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';

    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;

    document.body.appendChild(alertDiv);

    // Auto remove after duration
    setTimeout(() => {
        if (alertDiv.parentElement) {
            alertDiv.remove();
        }
    }, duration);
}

// API helper functions
async function makeApiRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('API Request failed:', error);
        showNotification('danger', 'Wystąpił błąd połączenia z serwerem');
        return { success: false, message: 'Błąd połączenia' };
    }
}

// Host management functions
function filterTable(tableId, searchInputId, filterColumn = null) {
    const searchInput = document.getElementById(searchInputId);
    const table = document.getElementById(tableId);

    if (!searchInput || !table) return;

    searchInput.addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        const rows = table.getElementsByTagName('tr');

        for (let i = 1; i < rows.length; i++) {
            const row = rows[i];
            let shouldShow = false;

            if (filterColumn !== null) {
                const cell = row.getElementsByTagName('td')[filterColumn];
                if (cell) {
                    const text = cell.textContent || cell.innerText;
                    shouldShow = text.toLowerCase().indexOf(filter) > -1;
                }
            } else {
                const cells = row.getElementsByTagName('td');
                for (let j = 0; j < cells.length; j++) {
                    const text = cells[j].textContent || cells[j].innerText;
                    if (text.toLowerCase().indexOf(filter) > -1) {
                        shouldShow = true;
                        break;
                    }
                }
            }

            row.style.display = shouldShow ? '' : 'none';
        }
    });
}

// Checkbox selection functions
function toggleSelectAll(selectAllCheckbox, itemCheckboxClass) {
    const checkboxes = document.querySelectorAll('.' + itemCheckboxClass);
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}

function updateSelectAll(selectAllCheckboxId, itemCheckboxClass) {
    const selectAllCheckbox = document.getElementById(selectAllCheckboxId);
    const checkboxes = document.querySelectorAll('.' + itemCheckboxClass);
    const checkedBoxes = document.querySelectorAll('.' + itemCheckboxClass + ':checked');

    if (selectAllCheckbox) {
        selectAllCheckbox.checked = checkedBoxes.length === checkboxes.length && checkboxes.length > 0;
        selectAllCheckbox.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < checkboxes.length;
    }
}

// Tag management functions
async function addTagToHost(hostId, tagName, tagValue = '') {
    const button = event.target;
    showLoading(button);

    try {
        const result = await makeApiRequest(`/api/host/${hostId}/tags`, 'POST', {
            tag: tagName,
            value: tagValue
        });

        if (result.success) {
            showNotification('success', result.message);
            return true;
        } else {
            showNotification('danger', result.message);
            return false;
        }
    } finally {
        hideLoading(button);
    }
}

async function removeTagFromHost(hostId, tagName) {
    if (!confirm(`Czy na pewno chcesz usunąć tag "${tagName}"?`)) {
        return false;
    }

    const button = event.target;
    showLoading(button);

    try {
        const result = await makeApiRequest(`/api/host/${hostId}/tags/${encodeURIComponent(tagName)}`, 'DELETE');

        if (result.success) {
            showNotification('success', result.message);
            return true;
        } else {
            showNotification('danger', result.message);
            return false;
        }
    } finally {
        hideLoading(button);
    }
}

// Form validation
function validateTagForm(tagNameInputId, showAlert = true) {
    const tagNameInput = document.getElementById(tagNameInputId);
    if (!tagNameInput) return false;

    const tagName = tagNameInput.value.trim();

    if (!tagName) {
        if (showAlert) {
            showNotification('warning', 'Nazwa tagu jest wymagana');
            tagNameInput.focus();
        }
        return false;
    }

    if (tagName.length > 255) {
        if (showAlert) {
            showNotification('warning', 'Nazwa tagu jest zbyt długa (max 255 znaków)');
            tagNameInput.focus();
        }
        return false;
    }

    // Check for invalid characters
    const invalidChars = /[<>&"']/;
    if (invalidChars.test(tagName)) {
        if (showAlert) {
            showNotification('warning', 'Nazwa tagu zawiera niedozwolone znaki');
            tagNameInput.focus();
        }
        return false;
    }

    return true;
}

// Local storage helpers for user preferences
function saveUserPreference(key, value) {
    try {
        localStorage.setItem('zabbix_tag_manager_' + key, JSON.stringify(value));
    } catch (e) {
        console.warn('Could not save user preference:', e);
    }
}

function getUserPreference(key, defaultValue = null) {
    try {
        const item = localStorage.getItem('zabbix_tag_manager_' + key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.warn('Could not load user preference:', e);
        return defaultValue;
    }
}

// Initialize common functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentElement) {
                        alert.remove();
                    }
                }, 500);
            }
        }, 5000);
    });

    // Add click handlers for checkboxes to update select all state
    const itemCheckboxes = document.querySelectorAll('.host-checkbox');
    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateSelectAll('selectAllCheckbox', 'host-checkbox');
        });
    });

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+A to select all (when in hosts view)
        if (e.ctrlKey && e.key === 'a' && document.getElementById('selectAllCheckbox')) {
            e.preventDefault();
            document.getElementById('selectAllCheckbox').click();
        }

        // Escape to close modals/alerts
        if (e.key === 'Escape') {
            const alerts = document.querySelectorAll('.alert .btn-close');
            alerts.forEach(btn => btn.click());
        }
    });
});

// Performance optimization - debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export commonly used functions to global scope
window.ZabbixTagManager = {
    makeApiRequest,
    addTagToHost,
    removeTagFromHost,
    validateTagForm,
    showNotification,
    saveUserPreference,
    getUserPreference,
    debounce
};