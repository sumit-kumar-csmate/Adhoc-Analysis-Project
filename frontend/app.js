/**
 * Frontend JavaScript for Trade Data AI Analyzer
 * Enhanced with drag-drop, preview, real-time progress, and history
 */

let selectedFile = null;
let currentMaterial = null;
let selectedFilePath = null;
let currentJobId = null;       // Set when analysis completes, used for deferred download
let liveResultsHeaders = [];   // Column headers for live results table
let liveResultsRowCount = 0;   // Number of rows added to live table so far

// Toggle Analysis Mode
function toggleMode() {
    const mode = document.querySelector('input[name="analysisMode"]:checked').value;
    const materialContainer = document.getElementById('materialSelectContainer');
    const materialDropdownTrigger = document.getElementById('dropdownTrigger');

    if (mode === 'universal') {
        materialContainer.style.opacity = '0.5';
        materialContainer.style.pointerEvents = 'none';
        currentMaterial = 'Universal_Discovery'; // Dummy value to pass validation
        selectedMaterialText.textContent = '🌍 Universal Analysis';
        materialInfo.textContent = 'Analyzing all rows against global knowledge base...';
    } else {
        materialContainer.style.opacity = '1';
        materialContainer.style.pointerEvents = 'all';
        // Restore selection if exists
        const selectedOption = document.querySelector('.dropdown-option.selected');
        if (selectedOption) {
            currentMaterial = selectedOption.dataset.value;
            selectedMaterialText.textContent = currentMaterial;
            const fullInfo = materialsData.find(m => m.name === currentMaterial);
            if (fullInfo) {
                materialInfo.textContent = `📋 ${fullInfo.full_name || fullInfo.name}\n${fullInfo.description || ''}`;
            }
        } else {
            currentMaterial = null;
            selectedMaterialText.textContent = 'Select Material';
            materialInfo.textContent = 'Select a material to configure extraction rules';
        }
    }
}
// DOM Elements
const dropdownTrigger = document.getElementById('dropdownTrigger');
const dropdownMenu = document.getElementById('dropdownMenu');
const dropdownOptions = document.getElementById('dropdownOptions');
const dropdownSearch = document.getElementById('dropdownSearch');
const selectedMaterialText = document.getElementById('selectedMaterialText');
const materialInfo = document.getElementById('materialInfo');
const dropZone = document.getElementById('dropZone');
const fileName = document.getElementById('fileName');
const previewSection = document.getElementById('previewSection');
const previewTable = document.getElementById('previewTable');
const previewInfo = document.getElementById('previewInfo');
const analyzeBtn = document.getElementById('analyzeBtn');
const progressSection = document.getElementById('progressSection');
const status = document.getElementById('status');
const progressFill = document.getElementById('progressFill');
const progressDetails = document.getElementById('progressDetails');
const refreshMaterialsBtn = document.getElementById('refreshMaterialsBtn');
const viewHistoryBtn = document.getElementById('viewHistoryBtn');
const exportHistoryBtn = document.getElementById('exportHistoryBtn');
const historyModal = document.getElementById('historyModal');
const closeHistoryBtn = document.getElementById('closeHistoryBtn');

// ============================================
// MATERIAL MANAGEMENT
// ============================================

let materialsData = [];

async function loadMaterials() {
    try {
        const response = await fetch('/api/materials');
        const data = await response.json();

        if (data.materials && data.materials.length > 0) {
            const previousSelection = currentMaterial;
            materialsData = data.materials;

            dropdownOptions.innerHTML = '';
            data.materials.forEach(material => {
                const option = document.createElement('div');
                option.className = 'dropdown-option';
                option.dataset.value = material.name;
                option.dataset.fullName = material.full_name;
                option.dataset.description = material.description;
                option.textContent = material.name;
                option.addEventListener('click', () => selectMaterial(material));
                dropdownOptions.appendChild(option);
            });

            if (previousSelection) {
                const previousMaterial = materialsData.find(m => m.name === previousSelection);
                if (previousMaterial) {
                    selectMaterial(previousMaterial);
                } else if (materialsData.length > 0) {
                    selectMaterial(materialsData[0]);
                }
            } else if (materialsData.length > 0) {
                selectMaterial(materialsData[0]);
            }
        }
    } catch (error) {
        console.error('Failed to load materials:', error);
        toast.error(`Connection Error: ${error.message} - Loading demo data`);

        // Fallback to demo data so UI works
        const demoMaterials = [
            { name: "CAPB", full_name: "Cocamidopropyl Betaine", description: "Amphoteric surfactant" },
            { name: "SLES", full_name: "Sodium Lauryl Ether Sulfate", description: "Anionic surfactant" },
            { name: "CDEA", full_name: "Cocamide DEA", description: "Non-ionic surfactant" },
            { name: "LABSA", full_name: "Linear Alkyl Benzene Sulphonic Acid", description: "Anionic surfactant" },
            { name: "Sulphuric Acid", full_name: "H2SO4", description: "Strong mineral acid" }
        ];

        materialsData = demoMaterials;
        dropdownOptions.innerHTML = '';
        demoMaterials.forEach(material => {
            const option = document.createElement('div');
            option.className = 'dropdown-option';
            option.dataset.value = material.name;
            option.dataset.fullName = material.full_name;
            option.dataset.description = material.description;
            option.textContent = material.name;
            option.addEventListener('click', () => selectMaterial(material));
            dropdownOptions.appendChild(option);
        });

        if (demoMaterials.length > 0) {
            selectMaterial(demoMaterials[0]);
        }
    }
}

function selectMaterial(material) {
    currentMaterial = material.name;
    selectedMaterialText.textContent = material.name;

    // Update selected state
    document.querySelectorAll('.dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
        if (opt.dataset.value === material.name) {
            opt.classList.add('selected');
        }
    });

    // Update material info
    const fullName = material.full_name || material.name;
    const description = material.description || '';
    materialInfo.textContent = `📋 ${fullName}\n${description}`;

    // Close dropdown
    closeDropdown();

    // Recalculate cost if file is loaded
    if (selectedFilePath) {
        updateCostEstimate();
    }
}

// Recalculate cost based on current file and material selection
async function updateCostEstimate() {
    if (!selectedFilePath) return;

    try {
        const mode = document.querySelector('input[name="analysisMode"]:checked')?.value || 'specific';

        const response = await fetch('http://127.0.0.1:5000/api/cost/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_path: selectedFilePath,
                material: currentMaterial,
                mode: mode,
                model: document.getElementById('modelSelect') ? document.getElementById('modelSelect').value : 'claude-haiku-3'
            })
        });

        const data = await response.json();

        if (data.success && data.estimate) {
            displayCostEstimate(data.estimate);
        }
    } catch (error) {
        console.error('Error updating cost estimate:', error);
    }
}

// Dropdown toggle and search
function toggleDropdown() {
    // Retry loading materials if empty and backend connection failed previously
    if (materialsData.length === 0 && !dropdownMenu.classList.contains('show')) {
        loadMaterials();
    }

    dropdownMenu.classList.toggle('show');
    dropdownTrigger.classList.toggle('active');

    if (dropdownMenu.classList.contains('show')) {
        dropdownSearch.value = '';
        filterDropdownOptions('');
        setTimeout(() => dropdownSearch.focus(), 100);
    }
}

function closeDropdown() {
    dropdownMenu.classList.remove('show');
    dropdownTrigger.classList.remove('active');
}

function filterDropdownOptions(searchTerm) {
    const term = searchTerm.toLowerCase();
    document.querySelectorAll('.dropdown-option').forEach(option => {
        const text = option.textContent.toLowerCase();
        if (text.includes(term)) {
            option.classList.remove('hidden');
        } else {
            option.classList.add('hidden');
        }
    });
}
// ============================================
// FILE UPLOAD - DRAG & DROP
// ============================================

// Prevent default drag behaviors
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Highlight drop zone when dragging over it
['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.add('drag-over');
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove('drag-over');
    }, false);
});

// Handle dropped files
dropZone.addEventListener('drop', handleDrop, false);
dropZone.addEventListener('click', onSelectFile);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length > 0) {
        handleFileSelection(files[0]);
    }
}

// ============================================
// FILE UPLOAD - BUTTON
// ============================================

async function onSelectFile() {
    try {
        if (window.electron && window.electron.selectFile) {
            const filePath = await window.electron.selectFile();
            if (filePath) {
                selectedFilePath = filePath;
                const name = filePath.split('\\').pop().split('/').pop();
                fileName.textContent = name;
                fileName.classList.add('selected');
                toast.success(`File selected: ${name}`);

                // Load preview
                await loadFilePreview(filePath);
            }
        } else {
            toast.warning('File selection requires Electron app');
        }
    } catch (error) {
        console.error('Error selecting file:', error);
        toast.error('Error selecting file');
    }
}

function handleFileSelection(file) {
    // For web-based file input (not used in Electron, but kept for compatibility)
    selectedFile = file;
    fileName.textContent = file.name;
    fileName.classList.add('selected');
    toast.success(`File selected: ${file.name}`);
}

// ============================================
// COST ESTIMATION DISPLAY
// ============================================

function displayCostEstimate(estimate) {
    if (!estimate) return;

    // Format token numbers with K suffix for large numbers
    const formatTokens = (num) => {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(0) + 'K';
        return num.toString();
    };

    // Update token displays
    document.getElementById('inputTokens').textContent = formatTokens(estimate.tokens.input);
    document.getElementById('outputTokens').textContent = formatTokens(estimate.tokens.output);
    document.getElementById('totalTokens').textContent = formatTokens(estimate.tokens.total);

    // Update cost displays
    document.getElementById('estimatedCostINR').textContent = `₹${estimate.cost_inr.total.toFixed(2)}`;
    document.getElementById('estimatedCostUSD').textContent = `($${estimate.cost_usd.total.toFixed(4)})`;

    // Update rate info
    if (estimate.rates) {
        document.getElementById('inputRate').textContent = estimate.rates.input_per_million.toFixed(2);
        document.getElementById('outputRate').textContent = estimate.rates.output_per_million.toFixed(2);
    }

    // Update model name
    const modelMap = {
        'claude-haiku-3': 'Claude Haiku 3',
        'claude-sonnet-4.6': 'Claude Sonnet 4.6',
        'claude-opus-4.6': 'Claude Opus 4.6'
    };
    const modelDisplay = modelMap[estimate.model] || estimate.model;
    document.getElementById('modelName').textContent = modelDisplay;
}

// ============================================
// FILE PREVIEW & VALIDATION
// ============================================

async function loadFilePreview(filePath) {
    try {
        toast.info('Loading preview...');

        const response = await fetch('http://127.0.0.1:5000/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: filePath })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Show preview section
            previewSection.style.display = 'block';

            // Update preview info
            previewInfo.innerHTML = `
                <strong>Total Rows:</strong> ${data.total_rows} | 
                <strong>Total Columns:</strong> ${data.total_columns} |
                <strong>Product Description Column:</strong> ${data.has_product_description ? '✓ Found' : '✗ Not Found'}
            `;

            // Build preview table
            if (data.preview_data && data.preview_data.length > 0) {
                const headers = data.columns;
                let tableHTML = '<thead><tr>';
                headers.forEach(header => {
                    const isDesc = header.toLowerCase().includes('description');
                    const className = isDesc ? ' class="col-description"' : '';
                    tableHTML += `<th${className}>${header}</th>`;
                });
                tableHTML += '</tr></thead><tbody>';

                data.preview_data.forEach(row => {
                    tableHTML += '<tr>';
                    headers.forEach(header => {
                        const cellValue = row[header] !== null && row[header] !== undefined ? row[header] : '';
                        const isDesc = header.toLowerCase().includes('description');
                        const className = isDesc ? ' class="col-description"' : '';
                        tableHTML += `<td${className}>${cellValue}</td>`;
                    });
                    tableHTML += '</tr>';
                });
                tableHTML += '</tbody>';

                previewTable.innerHTML = tableHTML;

                // Display cost estimation
                if (data.cost_estimate) {
                    displayCostEstimate(data.cost_estimate);
                }

                if (data.has_product_description) {
                    toast.success('Preview loaded! Ready to analyze.');
                    analyzeBtn.disabled = false;
                } else {
                    toast.error('Product_Description column not found!');
                    analyzeBtn.disabled = true;
                }
            }
        } else {
            throw new Error(data.error || 'Failed to load preview');
        }
    } catch (error) {
        console.error('Preview error:', error);
        toast.error(`Preview failed: ${error.message}`);
        previewSection.style.display = 'none';
    }
}

// ============================================
// FILE ANALYSIS WITH REAL-TIME PROGRESS
// ============================================

async function onAnalyze() {
    const mode = document.querySelector('input[name="analysisMode"]:checked').value;

    if (!selectedFilePath) {
        toast.warning('Please select a file to analyze');
        return;
    }

    if (mode === 'specific' && !currentMaterial) {
        toast.warning('Please select a material type for targeted extraction');
        return;
    }

    try {
        // Disable controls
        analyzeBtn.disabled = true;
        dropdownTrigger.style.pointerEvents = 'none';
        dropdownTrigger.style.opacity = '0.7';
        document.querySelectorAll('input[name="analysisMode"]').forEach(el => el.disabled = true);

        // Show progress section
        progressSection.style.display = 'block';
        status.innerHTML = '🚀 Starting analysis...';
        progressFill.style.width = '0%';
        progressFill.classList.add('active');
        progressFill.parentElement.dataset.progress = '0%';

        const startTime = Date.now();

        // Use EventSource for real-time progress updates
        const mode = document.querySelector('input[name="analysisMode"]:checked').value;
        const eventSource = new EventSource(
            `http://127.0.0.1:5000/api/analyze/stream?` +
            new URLSearchParams({
                file_path: selectedFilePath,
                material: currentMaterial,
                mode: mode,
                model: document.getElementById('modelSelect') ? document.getElementById('modelSelect').value : 'claude-haiku-3'
            })
        );

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'partial_results') {
                // Update progress bar
                progressFill.style.width = `${data.percent}%`;
                progressFill.parentElement.dataset.progress = `${data.percent}%`;
                status.innerHTML = `⚡ Classified ${data.current} of ${data.total} rows...`;

                const elapsed = (Date.now() - startTime) / 1000;
                const speed = data.current / elapsed;
                const remaining = (data.total - data.current) / speed;
                
                let detailsHTML = `<strong>Speed:</strong> ${speed.toFixed(1)} rows/sec | <strong>ETA:</strong> ${remaining > 0 ? remaining.toFixed(0) : 0}s`;
                if (data.prompt_tokens !== undefined) {
                    detailsHTML += ` | <strong>Tokens:</strong> ${(data.prompt_tokens + data.completion_tokens).toLocaleString()}`;
                }
                progressDetails.innerHTML = detailsHTML;

                // Build live results table
                appendLiveResults(data.rows, data.current);

            } else if (data.type === 'complete') {
                eventSource.close();
                progressFill.style.width = '100%';
                progressFill.parentElement.dataset.progress = '100%';
                progressFill.classList.remove('active');
                status.innerHTML = '✓ Analysis complete!';

                const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
                progressDetails.innerHTML = `<strong>Processed:</strong> ${data.rows_processed} rows | <strong>Time:</strong> ${totalTime}s | <strong>Tokens:</strong> ${(data.prompt_tokens + data.completion_tokens).toLocaleString()} | <strong>Cost:</strong> $${data.actual_cost.toFixed(4)}`;

                // Store job_id and show Download button
                currentJobId = data.job_id;
                document.getElementById('downloadBtn').style.display = 'inline-flex';

                toast.success(`Analysis done! Processed ${data.rows_processed} rows for $${data.actual_cost.toFixed(4)}. Click Download to save.`);
                loadAnalysisHistory();

            } else if (data.type === 'error') {
                eventSource.close();
                throw new Error(data.message);
            }
        };

        eventSource.onerror = () => {
            eventSource.close();
            analyzeWithoutStream();
        };

    } catch (error) {
        console.error('Analysis error:', error);
        status.innerHTML = `❌ Error: ${error.message}`;
        progressFill.style.width = '0%';
        progressFill.classList.remove('active');
        toast.error(`Analysis failed: ${error.message}`);
    } finally {
        analyzeBtn.disabled = false;
        dropdownTrigger.style.pointerEvents = 'all';
        dropdownTrigger.style.opacity = '1';
        document.querySelectorAll('input[name="analysisMode"]').forEach(el => el.disabled = false);
        toggleMode();
    }
}

// Build / append rows to the live results table as chunks arrive
function appendLiveResults(rows, totalClassified) {
    const liveSection = document.getElementById('liveResultsSection');
    const table = document.getElementById('liveResultsTable');
    const countEl = document.getElementById('liveResultsCount');

    if (!rows || rows.length === 0) return;

    // Build header from first row if not yet done
    if (liveResultsRowCount === 0) {
        const headers = Object.keys(rows[0].data);
        liveResultsHeaders = headers;
        let thead = '<thead><tr>';
        headers.forEach(h => { thead += `<th>${h}</th>`; });
        thead += '</tr></thead><tbody id="liveResultsTbody"></tbody>';
        table.innerHTML = thead;
        liveSection.style.display = 'block';
    }

    const tbody = document.getElementById('liveResultsTbody');
    rows.forEach(r => {
        const tr = document.createElement('tr');
        liveResultsHeaders.forEach(h => {
            const td = document.createElement('td');
            td.textContent = r.data[h] !== undefined ? r.data[h] : '';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
        liveResultsRowCount++;
    });

    countEl.textContent = `(${totalClassified} rows)`;

    // Auto-scroll to bottom
    const container = liveSection.querySelector('.preview-container');
    container.scrollTop = container.scrollHeight;
}

// Called when user clicks Download — triggers deferred Excel write
async function downloadResults() {
    if (!currentJobId) {
        toast.error('No analysis job found. Please run analysis first.');
        return;
    }

    const btn = document.getElementById('downloadBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Saving file...';

    try {
        const response = await fetch(`http://127.0.0.1:5000/api/download/${currentJobId}`);
        const data = await response.json();

        if (data.success) {
            toast.success(`💾 File saved to: ${data.output_file}`);
            btn.textContent = '✓ Downloaded!';
            btn.style.background = 'rgba(34, 197, 94, 0.3)';
            currentJobId = null;

            // Reset UI after delay
            setTimeout(() => {
                progressSection.style.display = 'none';
                previewSection.style.display = 'none';
                fileName.textContent = 'No file selected';
                fileName.classList.remove('selected');
                selectedFilePath = null;
                progressFill.style.width = '0%';
                // Reset live table
                liveResultsRowCount = 0;
                liveResultsHeaders = [];
                document.getElementById('liveResultsSection').style.display = 'none';
                document.getElementById('liveResultsTable').innerHTML = '';
                document.getElementById('downloadBtn').style.display = 'none';
                document.getElementById('downloadBtn').disabled = false;
                document.getElementById('downloadBtn').textContent = '💾 Download File';
                document.getElementById('downloadBtn').style.background = '';
            }, 3000);
        } else {
            throw new Error(data.error || 'Download failed');
        }
    } catch (err) {
        toast.error(`Download failed: ${err.message}`);
        btn.disabled = false;
        btn.textContent = '💾 Download File';
    }
}

// Fallback analysis without streaming
async function analyzeWithoutStream() {
    try {
        toast.info('Using standard analysis mode...');

        const response = await fetch('http://127.0.0.1:5000/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_path: selectedFilePath,
                material: currentMaterial,
                mode: document.querySelector('input[name="analysisMode"]:checked').value,
                model: document.getElementById('modelSelect') ? document.getElementById('modelSelect').value : 'claude-haiku-3'
            })
        });

        progressFill.style.width = '50%';
        progressFill.parentElement.dataset.progress = '50%';
        status.innerHTML = '⚙️ Processing...';

        const data = await response.json();

        if (response.ok && data.success) {
            progressFill.style.width = '100%';
            progressFill.parentElement.dataset.progress = '100%';
            progressFill.classList.remove('active');
            status.innerHTML = '✓ Analysis complete!';

            let costStr = data.actual_cost !== undefined ? ` | <strong>Cost:</strong> $${data.actual_cost.toFixed(4)}` : '';
            progressDetails.innerHTML = `<strong>Processed:</strong> ${data.rows_processed} rows${costStr}`;

            toast.success(data.actual_cost !== undefined ? `Analysis completed for $${data.actual_cost.toFixed(4)}!` : `Analysis completed! Processed ${data.rows_processed} rows.`);
            loadAnalysisHistory();

            setTimeout(() => {
                progressSection.style.display = 'none';
                previewSection.style.display = 'none';
                fileName.textContent = 'No file selected';
                fileName.classList.remove('selected');
                selectedFilePath = null;
                progressFill.style.width = '0%';
            }, 3000);
        } else {
            throw new Error(data.error || 'Analysis failed');
        }
    } catch (error) {
        throw error;
    }
}

// ============================================
// ANALYSIS HISTORY
// ============================================

async function loadAnalysisHistory() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/history/stats');
        const data = await response.json();

        if (response.ok && data.success) {
            // Update stats
            const statsContainer = document.getElementById('historyStats');
            statsContainer.innerHTML = `
                <div style="background: rgba(102, 126, 234, 0.15); padding: 20px; border-radius: 12px; border-left: 3px solid #667eea;">
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">${data.stats.total_analyses}</div>
                    <div style="font-size: 12px; opacity: 0.8;">Total Analyses</div>
                </div>
                <div style="background: rgba(118, 75, 162, 0.15); padding: 20px; border-radius: 12px; border-left: 3px solid #764ba2;">
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">${data.stats.total_rows_processed.toLocaleString()}</div>
                    <div style="font-size: 12px; opacity: 0.8;">Rows Processed</div>
                </div>
                <div style="background: rgba(70, 180, 255, 0.15); padding: 20px; border-radius: 12px; border-left: 3px solid #46b4ff;">
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">${(data.stats.total_tokens_used || 0).toLocaleString()}</div>
                    <div style="font-size: 12px; opacity: 0.8;">Tokens Used</div>
                </div>
                <div style="background: rgba(34, 197, 94, 0.15); padding: 20px; border-radius: 12px; border-left: 3px solid #22c55e;">
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">$${(data.stats.total_cost || 0).toFixed(2)}</div>
                    <div style="font-size: 12px; opacity: 0.8;">Total Cost</div>
                </div>
            `;

            // Update recent history
            const recentContainer = document.getElementById('recentHistory');
            if (data.stats.recent_analyses && data.stats.recent_analyses.length > 0) {
                let recentHTML = '<strong>Recent Analyses:</strong><ul style="margin-top: 10px; padding-left: 20px;">';
                data.stats.recent_analyses.forEach(item => {
                    const date = new Date(item.timestamp).toLocaleString();
                    recentHTML += `<li>${item.material_type} - ${item.rows_processed} rows (${date})</li>`;
                });
                recentHTML += '</ul>';
                recentContainer.innerHTML = recentHTML;
            } else {
                recentContainer.innerHTML = '<em>No analyses yet</em>';
            }
        }
    } catch (error) {
        console.error('Failed to load history:', error);
        document.getElementById('recentHistory').innerHTML = '<em>Failed to load history</em>';
    }
}

async function viewFullHistory() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/history');
        const data = await response.json();

        if (response.ok && data.success) {
            const tableContainer = document.getElementById('fullHistoryTable');

            if (data.analyses && data.analyses.length > 0) {
                let tableHTML = `
                    <table class="preview-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Timestamp</th>
                                <th>File Name</th>
                                <th>Material</th>
                                <th>Rows</th>
                                <th>Tokens Used</th>
                                <th>Cost ($)</th>
                                <th>Time (s)</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                data.analyses.forEach(item => {
                    const date = new Date(item.timestamp).toLocaleString();
                    const time = item.processing_time ? item.processing_time.toFixed(1) : 'N/A';
                    const tokens = item.total_tokens ? item.total_tokens.toLocaleString() : '0';
                    const cost = item.actual_cost != null ? item.actual_cost.toFixed(4) : '0.0000';
                    tableHTML += `
                        <tr>
                            <td>${item.id}</td>
                            <td>${date}</td>
                            <td>${item.file_name}</td>
                            <td>${item.material_type}</td>
                            <td>${item.rows_processed}</td>
                            <td>${tokens}</td>
                            <td>${cost}</td>
                            <td>${time}</td>
                            <td>${item.status}</td>
                        </tr>
                    `;
                });

                tableHTML += '</tbody></table>';
                tableContainer.innerHTML = tableHTML;
            } else {
                tableContainer.innerHTML = '<p style="text-align: center; padding: 40px;">No history found</p>';
            }

            historyModal.style.display = 'block';
        }
    } catch (error) {
        console.error('Failed to load full history:', error);
        toast.error('Failed to load history');
    }
}

async function exportHistoryToCSV() {
    try {
        toast.info('Exporting history...');

        const response = await fetch('http://127.0.0.1:5000/api/history/export');
        const blob = await response.blob();

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis_history_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        toast.success('History exported successfully!');
    } catch (error) {
        console.error('Failed to export history:', error);
        toast.error('Failed to export history');
    }
}

// ============================================
// EVENT LISTENERS
// ============================================

// materialSelect.addEventListener('change', onMaterialChange); // Removed old dropdown listener
analyzeBtn.addEventListener('click', onAnalyze);
viewHistoryBtn.addEventListener('click', viewFullHistory);
exportHistoryBtn.addEventListener('click', exportHistoryToCSV);
closeHistoryBtn.addEventListener('click', () => historyModal.style.display = 'none');

// Refresh materials button
refreshMaterialsBtn.addEventListener('click', async () => {
    refreshMaterialsBtn.style.transform = 'rotate(360deg)';
    refreshMaterialsBtn.style.transition = 'transform 0.5s ease';
    toast.info('Refreshing materials...');
    await loadMaterials();
    toast.success('Materials refreshed!');
    setTimeout(() => {
        refreshMaterialsBtn.style.transform = 'rotate(0deg)';
    }, 500);
});

// Dropdown event listeners
dropdownTrigger.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleDropdown();
});

dropdownSearch.addEventListener('input', (e) => {
    filterDropdownOptions(e.target.value);
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (!dropdownTrigger.contains(e.target) && !dropdownMenu.contains(e.target)) {
        closeDropdown();
    }
});

// Close modal on outside click
historyModal.addEventListener('click', (e) => {
    if (e.target === historyModal) {
        historyModal.style.display = 'none';
    }
});

// ============================================
// INITIALIZATION
// ============================================

async function initialize() {
    await loadMaterials();
    await loadAnalysisHistory();

    // Listen for material changes from other windows
    window.addEventListener('storage', (e) => {
        if (e.key === 'materials_last_updated') {
            loadMaterials();
        }
    });

    window.addEventListener('materials-updated', () => {
        loadMaterials();
    });
}

// Expose for material manager
window.refreshMaterials = loadMaterials;

// Initialize on load
window.addEventListener('DOMContentLoaded', initialize);
