/**
 * Table Manager - Unified JavaScript module for table operations
 * Handles: filtering, pagination, selection, and bulk operations
 */

// ========================================
// SELECTION MANAGER
// ========================================
class SelectionManager {
    constructor(config) {
        this.tableId = config.tableId;
        this.checkboxClass = config.checkboxClass;
        this.selectAllId = config.selectAllId || 'selectAllCheckbox';
        this.rowDataAttr = config.rowDataAttr; // e.g., 'data-host-name'
        this.discoveredAttr = config.discoveredAttr || 'data-is-discovered';
        this.onSelectionChange = config.onSelectionChange || (() => {});

        this._init();
    }

    _init() {
        // Add event listeners to checkboxes
        document.querySelectorAll(`.${this.checkboxClass}`).forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateSelectAllCheckbox());
        });
    }

    updateSelectAllCheckbox() {
        const visibleCheckboxes = [];
        document.querySelectorAll(`#${this.tableId} tr`).forEach(row => {
            if (row.style.display !== 'none' && !row.classList.contains('d-none')) {
                const checkbox = row.querySelector(`.${this.checkboxClass}`);
                if (checkbox) {
                    visibleCheckboxes.push(checkbox);
                }
            }
        });

        const checkedVisible = visibleCheckboxes.filter(cb => cb.checked);
        const selectAllCheckbox = document.getElementById(this.selectAllId);

        if (!selectAllCheckbox) return;

        if (visibleCheckboxes.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedVisible.length === visibleCheckboxes.length) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedVisible.length > 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }

        this.onSelectionChange();
    }

    selectAll() {
        document.querySelectorAll(`#${this.tableId} tr`).forEach(row => {
            if (row.style.display !== 'none' && !row.classList.contains('d-none')) {
                const checkbox = row.querySelector(`.${this.checkboxClass}`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            }
        });
        const selectAllCheckbox = document.getElementById(this.selectAllId);
        if (selectAllCheckbox) selectAllCheckbox.checked = true;
        this.onSelectionChange();
    }

    deselectAll() {
        document.querySelectorAll(`#${this.tableId} tr`).forEach(row => {
            if (row.style.display !== 'none' && !row.classList.contains('d-none')) {
                const checkbox = row.querySelector(`.${this.checkboxClass}`);
                if (checkbox) {
                    checkbox.checked = false;
                }
            }
        });
        const selectAllCheckbox = document.getElementById(this.selectAllId);
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
        this.onSelectionChange();
    }

    toggleAll() {
        const selectAllCheckbox = document.getElementById(this.selectAllId);
        if (!selectAllCheckbox) return;

        const shouldSelect = selectAllCheckbox.checked;
        document.querySelectorAll(`#${this.tableId} tr`).forEach(row => {
            if (row.style.display !== 'none' && !row.classList.contains('d-none')) {
                const checkbox = row.querySelector(`.${this.checkboxClass}`);
                if (checkbox) {
                    checkbox.checked = shouldSelect;
                }
            }
        });
        this.onSelectionChange();
    }

    getSelectedValues() {
        return Array.from(document.querySelectorAll(`.${this.checkboxClass}:checked`)).map(cb => cb.value);
    }

    getSelectedCount() {
        let count = 0;
        let discoveredCount = 0;

        document.querySelectorAll(`#${this.tableId} tr`).forEach(row => {
            if (row.style.display !== 'none' && !row.classList.contains('d-none')) {
                const checkbox = row.querySelector(`.${this.checkboxClass}`);
                if (checkbox && checkbox.checked) {
                    count++;
                    if (row.getAttribute(this.discoveredAttr) === 'true') {
                        discoveredCount++;
                    }
                }
            }
        });

        return { count, discoveredCount };
    }
}

// ========================================
// PAGINATION MANAGER
// ========================================
class PaginationManager {
    constructor(config) {
        this.tableId = config.tableId;
        this.rowDataAttr = config.rowDataAttr; // e.g., 'data-host-name'
        this.itemsPerPage = config.itemsPerPage || 50;
        this.containerTopId = config.containerTopId || 'paginationContainerTop';
        this.containerBottomId = config.containerBottomId || 'paginationContainerBottom';
        this.entityName = config.entityName || 'items'; // 'hosts', 'triggers', 'items'
        this.onPageChange = config.onPageChange || (() => {});

        this.currentPage = 1;
        this.allRows = [];

        this._init();
    }

    _init() {
        this.allRows = Array.from(document.querySelectorAll(`#${this.tableId} tr`));
        if (this.allRows.length > 0) {
            this.renderPagination();
            this.showPage(1);
        }
    }

    refreshRows() {
        this.allRows = Array.from(document.querySelectorAll(`#${this.tableId} tr`));
    }

    showPage(pageNum) {
        this.currentPage = pageNum;

        // Filter out hidden rows (by search/filter)
        const visibleRows = this.allRows.filter(row => {
            return row.style.display !== 'none' && row.getAttribute(this.rowDataAttr);
        });

        const totalVisible = visibleRows.length;
        const totalPages = Math.ceil(totalVisible / this.itemsPerPage);

        // Validate page number
        if (pageNum < 1) pageNum = 1;
        if (pageNum > totalPages && totalPages > 0) pageNum = totalPages;
        this.currentPage = pageNum;

        const start = (pageNum - 1) * this.itemsPerPage;
        const end = start + this.itemsPerPage;

        // Hide all rows first
        this.allRows.forEach(row => {
            if (row.getAttribute(this.rowDataAttr)) {
                row.classList.add('d-none');
            }
        });

        // Show only rows for current page
        visibleRows.slice(start, end).forEach(row => {
            row.classList.remove('d-none');
        });

        this.renderPagination();
        this.onPageChange();
    }

    renderPagination() {
        const containerTop = document.getElementById(this.containerTopId);
        const containerBottom = document.getElementById(this.containerBottomId);

        // Filter visible rows
        const visibleRows = this.allRows.filter(row => {
            return row.style.display !== 'none' && row.getAttribute(this.rowDataAttr);
        });

        const totalItems = visibleRows.length;
        const totalPages = Math.ceil(totalItems / this.itemsPerPage);

        // Don't show pagination if only one page or no items
        if (totalPages <= 1) {
            if (containerTop) containerTop.innerHTML = '';
            if (containerBottom) containerBottom.innerHTML = '';
            return;
        }

        const start = (this.currentPage - 1) * this.itemsPerPage + 1;
        const end = Math.min(this.currentPage * this.itemsPerPage, totalItems);

        let html = `<nav aria-label="${this.entityName} pagination"><ul class="pagination justify-content-center">`;

        // Previous button
        html += `<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="paginationManager.showPage(${this.currentPage - 1}); return false;">
                <i class="fas fa-chevron-left"></i> Previous
            </a>
        </li>`;

        // First page
        if (this.currentPage > 3) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="paginationManager.showPage(1); return false;">1</a></li>`;
            if (this.currentPage > 4) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        // Pages around current
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(totalPages, this.currentPage + 2);

        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="paginationManager.showPage(${i}); return false;">${i}</a>
            </li>`;
        }

        // Last page
        if (this.currentPage < totalPages - 2) {
            if (this.currentPage < totalPages - 3) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
            html += `<li class="page-item"><a class="page-link" href="#" onclick="paginationManager.showPage(${totalPages}); return false;">${totalPages}</a></li>`;
        }

        // Next button
        html += `<li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="paginationManager.showPage(${this.currentPage + 1}); return false;">
                Next <i class="fas fa-chevron-right"></i>
            </a>
        </li>`;

        html += '</ul></nav>';

        // Pagination info
        html += `<div class="text-center text-muted">
            <small>
                Page ${this.currentPage} of ${totalPages}
                (${start} - ${end} of ${totalItems} ${this.entityName})
            </small>
        </div>`;

        // Update both containers
        if (containerTop) containerTop.innerHTML = html;
        if (containerBottom) containerBottom.innerHTML = html;
    }

    changePerPage(newPerPage) {
        this.itemsPerPage = parseInt(newPerPage);
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('per_page', newPerPage);
        window.location.href = currentUrl.toString();
    }
}

// ========================================
// BULK OPERATIONS MANAGER
// ========================================
class BulkOperationsManager {
    constructor(config) {
        this.apiEndpoint = config.apiEndpoint; // e.g., '/api/hosts/tags/bulk'
        this.entityName = config.entityName || 'items';
        this.entityIdField = config.entityIdField; // e.g., 'host_ids', 'trigger_ids', 'item_ids'
        this.tagNameInputId = config.tagNameInputId || 'bulkTagName';
        this.tagValueInputId = config.tagValueInputId || 'bulkTagValue';
        this.statusElementId = config.statusElementId || 'bulkStatus';
        this.clearButtonId = config.clearButtonId || 'clearBulkBtn';
        this.storageKeyPrefix = config.storageKeyPrefix || 'bulk';
        this.getSelectedItems = config.getSelectedItems; // Function to get selected items
        this.getSelectionInfo = config.getSelectionInfo || null; // Optional function for more info
        this.onOperationComplete = config.onOperationComplete || (() => location.reload());

        this.cancelOperation = false;

        this._init();
    }

    _init() {
        const tagNameInput = document.getElementById(this.tagNameInputId);
        const tagValueInput = document.getElementById(this.tagValueInputId);

        if (tagNameInput) {
            tagNameInput.addEventListener('input', () => this.updateClearButton());
        }
        if (tagValueInput) {
            tagValueInput.addEventListener('input', () => this.updateClearButton());
        }
    }

    updateClearButton() {
        const tagName = document.getElementById(this.tagNameInputId).value.trim();
        const tagValue = document.getElementById(this.tagValueInputId).value.trim();
        const clearBtn = document.getElementById(this.clearButtonId);

        if (clearBtn) {
            clearBtn.style.display = (tagName || tagValue) ? '' : 'none';
        }

        this.updateStatus();
    }

    updateStatus() {
        const statusElement = document.getElementById(this.statusElementId);
        if (!statusElement) return;

        const tagName = document.getElementById(this.tagNameInputId).value.trim();
        const tagValue = document.getElementById(this.tagValueInputId).value.trim();
        const hasInput = tagName || tagValue;

        let count = 0;
        let discoveredCount = 0;
        let statusText = '';

        if (this.getSelectionInfo) {
            const info = this.getSelectionInfo();
            count = info.count || info.total || 0;
            discoveredCount = info.discoveredCount || info.discovered || 0;
        } else {
            const selected = this.getSelectedItems();
            count = selected.length;
        }

        if (count > 0 || hasInput) {
            if (count === 0) {
                statusText = `No ${this.entityName} selected`;
            } else {
                const singular = this.entityName.replace(/s$/, '');
                statusText = count === 1 ? `1 ${singular} selected` : `${count} ${this.entityName} selected`;
                if (discoveredCount > 0) {
                    statusText += ` - ${discoveredCount} discovered (may fail)`;
                }
            }
        }

        statusElement.textContent = statusText;
    }

    clearFields() {
        document.getElementById(this.tagNameInputId).value = '';
        document.getElementById(this.tagValueInputId).value = '';

        const clearBtn = document.getElementById(this.clearButtonId);
        if (clearBtn) clearBtn.style.display = 'none';

        // Clear from localStorage
        localStorage.removeItem(`${this.storageKeyPrefix}TagName`);
        localStorage.removeItem(`${this.storageKeyPrefix}TagValue`);

        this.updateStatus();
    }

    saveToStorage() {
        const tagName = document.getElementById(this.tagNameInputId).value;
        const tagValue = document.getElementById(this.tagValueInputId).value;
        localStorage.setItem(`${this.storageKeyPrefix}TagName`, tagName);
        localStorage.setItem(`${this.storageKeyPrefix}TagValue`, tagValue);
    }

    restoreFromStorage() {
        const tagName = localStorage.getItem(`${this.storageKeyPrefix}TagName`) || '';
        const tagValue = localStorage.getItem(`${this.storageKeyPrefix}TagValue`) || '';

        if (tagName || tagValue) {
            document.getElementById(this.tagNameInputId).value = tagName;
            document.getElementById(this.tagValueInputId).value = tagValue;
            this.updateClearButton();
        }
    }

    addTags() {
        const tagName = document.getElementById(this.tagNameInputId).value.trim();
        const tagValue = document.getElementById(this.tagValueInputId).value.trim();

        if (!tagName) {
            alert('Please provide a tag name');
            return;
        }

        const selectedItems = this.getSelectedItems();
        if (selectedItems.length === 0) {
            alert(`Please select at least one ${this.entityName.replace(/s$/, '')}`);
            return;
        }

        if (confirm(`Are you sure you want to add tag "${tagName}" to ${selectedItems.length} ${this.entityName}?`)) {
            this.performOperation('add', selectedItems, tagName, tagValue);
        }
    }

    removeTags() {
        const tagName = document.getElementById(this.tagNameInputId).value.trim();

        if (!tagName) {
            alert('Please provide a tag name');
            return;
        }

        const selectedItems = this.getSelectedItems();
        if (selectedItems.length === 0) {
            alert(`Please select at least one ${this.entityName.replace(/s$/, '')}`);
            return;
        }

        if (confirm(`Are you sure you want to remove tag "${tagName}" from ${selectedItems.length} ${this.entityName}?`)) {
            this.performOperation('remove', selectedItems, tagName, '');
        }
    }

    cancelCurrentOperation() {
        if (confirm('Are you sure you want to cancel? Tags already processed will remain.')) {
            this.cancelOperation = true;
            const cancelBtn = document.getElementById('cancelBulkBtn');
            if (cancelBtn) cancelBtn.disabled = true;
            const progressText = document.getElementById('progressText');
            if (progressText) progressText.textContent = 'Canceling operation...';
        }
    }

    async performOperation(operation, itemIds, tagName, tagValue) {
        this.cancelOperation = false;

        const progressModal = new bootstrap.Modal(document.getElementById('progressModal'));
        const progressBar = document.querySelector('.progress-bar');
        const progressText = document.getElementById('progressText');
        const progressCount = document.getElementById('progressCount');
        const progressPercent = document.getElementById('progressPercent');
        const progressTitle = document.getElementById('progressModalTitle');
        const cancelBtn = document.getElementById('cancelBulkBtn');

        const singular = this.entityName.replace(/s$/, '');
        progressTitle.textContent = operation === 'add' ? 'Adding Tags' : 'Removing Tags';
        progressText.textContent = `${operation === 'add' ? 'Adding' : 'Removing'} tag "${tagName}" ${operation === 'add' ? 'to' : 'from'} ${this.entityName}...`;
        progressCount.textContent = `0 / ${itemIds.length}`;
        progressPercent.textContent = '0%';
        progressBar.style.width = '0%';
        if (cancelBtn) cancelBtn.disabled = false;

        progressModal.show();

        try {
            const batchSize = 10;
            let processed = 0;
            let successful = 0;
            let failed = 0;

            for (let i = 0; i < itemIds.length; i += batchSize) {
                if (this.cancelOperation) {
                    progressModal.hide();
                    setTimeout(() => {
                        let message = `Operation canceled. ${operation === 'add' ? 'Added' : 'Removed'} tag ${operation === 'add' ? 'to' : 'from'} ${successful} of ${itemIds.length} ${this.entityName}.`;
                        if (failed > 0) {
                            message += `\n${failed} ${this.entityName} failed (likely discovered/read-only).`;
                        }
                        alert(message);
                        this.onOperationComplete();
                    }, 500);
                    return;
                }

                const batch = itemIds.slice(i, i + batchSize);
                const payload = {
                    operation: operation,
                    [this.entityIdField]: batch,
                    tag: tagName,
                    value: tagValue
                };

                try {
                    const response = await fetch(this.apiEndpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    const data = await response.json();
                    if (data.success && data.details) {
                        successful += data.details.success_count || 0;
                        failed += data.details.failed_count || 0;
                    } else if (data.success) {
                        successful += batch.length;
                    }
                    processed += batch.length;

                    const percent = Math.round((processed / itemIds.length) * 100);
                    progressBar.style.width = `${percent}%`;
                    progressCount.textContent = `${processed} / ${itemIds.length}`;
                    progressPercent.textContent = `${percent}%`;

                } catch (error) {
                    console.error('Error in batch:', error);
                    processed += batch.length;
                    failed += batch.length;
                }

                await new Promise(resolve => setTimeout(resolve, 100));
            }

            progressModal.hide();

            setTimeout(() => {
                let message = `Operation completed. ${operation === 'add' ? 'Added' : 'Removed'} tag ${operation === 'add' ? 'to' : 'from'} ${successful} ${this.entityName}.`;
                if (failed > 0) {
                    message += `\n\n${failed} ${this.entityName} failed (likely discovered/read-only).`;
                }
                alert(message);
                this.onOperationComplete();
            }, 500);

        } catch (error) {
            progressModal.hide();
            console.error('Error in bulkOperation:', error);
            setTimeout(() => {
                alert('An error occurred during the operation');
            }, 500);
        }
    }
}

// ========================================
// FILTER MANAGER
// ========================================
class FilterManager {
    constructor(config) {
        this.tableId = config.tableId;
        this.searchInputId = config.searchInputId;
        this.tagFilterInputId = config.tagFilterInputId || 'filterByTag';
        this.typeFilterId = config.typeFilterId || 'filterByType';
        this.statusElementId = config.statusElementId || 'filterStatus';
        this.clearButtonId = config.clearButtonId || 'clearFiltersBtn';
        this.rowDataAttr = config.rowDataAttr; // e.g., 'data-host-name'
        this.rowTagsAttr = config.rowTagsAttr; // e.g., 'data-host-tags'
        this.discoveredAttr = config.discoveredAttr || 'data-is-discovered';
        this.checkboxClass = config.checkboxClass;
        this.entityName = config.entityName || 'items';
        this.onFilter = config.onFilter || (() => {});
        this.customFilter = config.customFilter || null; // Optional custom filtering function

        this._init();
    }

    _init() {
        const searchInput = document.getElementById(this.searchInputId);
        const tagFilterInput = document.getElementById(this.tagFilterInputId);

        if (searchInput) {
            searchInput.addEventListener('input', () => this.filter());
        }
        if (tagFilterInput) {
            tagFilterInput.addEventListener('input', () => this.filter());
        }
    }

    initializeOnLoad() {
        const searchTerm = document.getElementById(this.searchInputId).value.trim();
        const tagFilter = document.getElementById(this.tagFilterInputId).value.trim();

        if (searchTerm || tagFilter) {
            this.filter();
        } else {
            const clearBtn = document.getElementById(this.clearButtonId);
            if (clearBtn) clearBtn.style.display = 'none';
        }
    }

    filter() {
        const searchTerm = document.getElementById(this.searchInputId).value.toLowerCase();
        const tagFilter = document.getElementById(this.tagFilterInputId).value.toLowerCase();
        const typeFilterEl = document.getElementById(this.typeFilterId);
        const typeFilter = typeFilterEl ? typeFilterEl.value : 'all';
        const rows = document.querySelectorAll(`#${this.tableId} tr`);

        let visibleCount = 0;
        let totalCount = 0;

        rows.forEach(row => {
            const name = row.getAttribute(this.rowDataAttr);
            const tags = row.getAttribute(this.rowTagsAttr);
            const isDiscovered = row.getAttribute(this.discoveredAttr) === 'true';

            if (name && tags !== null) {
                totalCount++;

                const matchesSearch = !searchTerm || name.includes(searchTerm);
                const matchesTag = !tagFilter || (tags && tags.includes(tagFilter));

                let matchesType = true;
                if (typeFilter === 'editable') {
                    matchesType = !isDiscovered;
                } else if (typeFilter === 'discovered') {
                    matchesType = isDiscovered;
                }

                // Apply custom filter if provided
                let matchesCustom = true;
                if (this.customFilter) {
                    matchesCustom = this.customFilter(row, { searchTerm, tagFilter, typeFilter });
                }

                if (matchesSearch && matchesTag && matchesType && matchesCustom) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                    const checkbox = row.querySelector(`.${this.checkboxClass}`);
                    if (checkbox) {
                        checkbox.checked = false;
                    }
                }
            }
        });

        this.updateStatus(searchTerm, tagFilter, visibleCount, totalCount, typeFilter);
        this.onFilter();
    }

    updateStatus(searchTerm, tagFilter, visibleCount, totalCount, typeFilter = 'all') {
        const statusElement = document.getElementById(this.statusElementId);
        const clearBtn = document.getElementById(this.clearButtonId);

        if (!statusElement) return;

        const hasFilters = searchTerm || tagFilter || typeFilter !== 'all';

        if (hasFilters) {
            let statusParts = [];
            if (searchTerm) statusParts.push(`name: "${searchTerm}"`);
            if (tagFilter) statusParts.push(`tag: "${tagFilter}"`);
            if (typeFilter === 'editable') statusParts.push('editable only');
            if (typeFilter === 'discovered') statusParts.push('discovered only');

            statusElement.textContent = `Showing ${visibleCount} of ${totalCount} ${this.entityName} (filtered by ${statusParts.join(', ')})`;
            if (clearBtn) clearBtn.style.display = '';
        } else {
            statusElement.textContent = '';
            if (clearBtn) clearBtn.style.display = 'none';
        }
    }

    clear() {
        document.getElementById(this.searchInputId).value = '';
        document.getElementById(this.tagFilterInputId).value = '';

        const typeFilterEl = document.getElementById(this.typeFilterId);
        if (typeFilterEl) typeFilterEl.value = 'all';

        const rows = document.querySelectorAll(`#${this.tableId} tr`);
        let totalCount = 0;

        rows.forEach(row => {
            const name = row.getAttribute(this.rowDataAttr);
            if (name) {
                totalCount++;
            }
            row.style.display = '';
        });

        this.updateStatus('', '', totalCount, totalCount, 'all');
        this.onFilter();
    }
}
