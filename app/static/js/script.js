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
        showNotification('danger', 'A server connection error occurred');
        return { success: false, message: 'Connection error' };
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
    if (!confirm(`Are you sure you want to remove tag "${tagName}"?`)) {
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
            showNotification('warning', 'Tag name is required');
            tagNameInput.focus();
        }
        return false;
    }

    if (tagName.length > 255) {
        if (showAlert) {
            showNotification('warning', 'Tag name is too long (max 255 characters)');
            tagNameInput.focus();
        }
        return false;
    }

    // Check for invalid characters
    const invalidChars = /[<>&"']/;
    if (invalidChars.test(tagName)) {
        if (showAlert) {
            showNotification('warning', 'Tag name contains invalid characters');
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

// ========================================
// TABLE SORTING MANAGER
// ========================================

class TableSortManager {
    constructor(tableBodyId, options = {}) {
        this.tableBodyId = tableBodyId;
        this.sortStates = {}; // column -> 'none' | 'asc' | 'desc'
        this.currentSortColumn = null;
        this.onSortCallback = options.onSort || null;
    }

    // Sort by a specific column
    sortBy(columnKey, dataAttribute, sortType = 'string') {
        // Cycle through sort states: none -> desc -> asc -> none
        const currentState = this.sortStates[columnKey] || 'none';
        let newState;

        if (currentState === 'none') {
            newState = 'desc';
        } else if (currentState === 'desc') {
            newState = 'asc';
        } else {
            newState = 'none';
        }

        // Reset all other columns
        Object.keys(this.sortStates).forEach(key => {
            if (key !== columnKey) {
                this.sortStates[key] = 'none';
                this.updateSortIcon(key, 'none');
            }
        });

        this.sortStates[columnKey] = newState;
        this.currentSortColumn = newState === 'none' ? null : columnKey;

        // Update icon
        this.updateSortIcon(columnKey, newState);

        // Perform sorting
        this.performSort(dataAttribute, sortType, newState);

        // Call callback if provided
        if (this.onSortCallback) {
            this.onSortCallback();
        }
    }

    // Perform the actual DOM sorting
    performSort(dataAttribute, sortType, direction) {
        const tbody = document.getElementById(this.tableBodyId);
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));

        if (direction === 'none') {
            // Reset to original order (by data-original-index if available)
            rows.sort((a, b) => {
                const indexA = parseInt(a.getAttribute('data-original-index') || '0');
                const indexB = parseInt(b.getAttribute('data-original-index') || '0');
                return indexA - indexB;
            });
        } else {
            rows.sort((a, b) => {
                let valueA = a.getAttribute(dataAttribute) || '';
                let valueB = b.getAttribute(dataAttribute) || '';

                let comparison = 0;

                switch (sortType) {
                    case 'number':
                        valueA = parseFloat(valueA) || 0;
                        valueB = parseFloat(valueB) || 0;
                        comparison = valueA - valueB;
                        break;
                    case 'boolean':
                        valueA = valueA === 'true' ? 1 : 0;
                        valueB = valueB === 'true' ? 1 : 0;
                        comparison = valueA - valueB;
                        break;
                    case 'string':
                    default:
                        valueA = valueA.toLowerCase();
                        valueB = valueB.toLowerCase();
                        comparison = valueA.localeCompare(valueB);
                        break;
                }

                return direction === 'desc' ? -comparison : comparison;
            });
        }

        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    }

    // Update the sort icon for a column
    updateSortIcon(columnKey, state) {
        const icon = document.getElementById(`${columnKey}SortIcon`);
        if (!icon) return;

        // Remove all sort classes
        icon.classList.remove('fa-sort', 'fa-sort-up', 'fa-sort-down');

        // Add appropriate class
        switch (state) {
            case 'asc':
                icon.classList.add('fa-sort-up');
                break;
            case 'desc':
                icon.classList.add('fa-sort-down');
                break;
            default:
                icon.classList.add('fa-sort');
        }
    }

    // Get current sort state
    getCurrentSort() {
        return {
            column: this.currentSortColumn,
            direction: this.sortStates[this.currentSortColumn] || 'none'
        };
    }

    // Reset all sorting
    reset() {
        Object.keys(this.sortStates).forEach(key => {
            this.sortStates[key] = 'none';
            this.updateSortIcon(key, 'none');
        });
        this.currentSortColumn = null;
        this.performSort('data-original-index', 'number', 'asc');
    }
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
    debounce,
    TableSortManager
};