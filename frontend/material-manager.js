// Material Manager JavaScript

let currentMaterials = {};
let editingMaterial = null;
let currentCategories = [];

// Filter materials based on search input
function filterMaterials() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const materialItems = document.querySelectorAll('.material-item');

    materialItems.forEach(item => {
        const name = item.querySelector('.material-name').textContent.toLowerCase();
        const desc = item.querySelector('.material-desc').textContent.toLowerCase();

        if (name.includes(searchTerm) || desc.includes(searchTerm)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}


// Notify other windows that materials have been updated
function notifyMaterialsUpdated() {
    // Update localStorage timestamp to trigger storage event in other windows
    localStorage.setItem('materials_last_updated', Date.now().toString());

    // Try to call parent window's refresh function if opened from main page
    if (window.opener && window.opener.refreshMaterials) {
        try {
            window.opener.refreshMaterials();
            console.log('Notified parent window to refresh materials');
        } catch (e) {
            console.log('Could not notify parent window:', e);
        }
    }

    // Dispatch custom event for same-window communication
    window.dispatchEvent(new CustomEvent('materials-updated'));
}

// DOM Elements
const materialList = document.getElementById('materialList');
const addMaterialBtn = document.getElementById('addMaterialBtn');
const materialModal = document.getElementById('materialModal');
const modalTitle = document.getElementById('modalTitle');
const materialName = document.getElementById('materialName');
const materialDescription = document.getElementById('materialDescription');
const materialPrompt = document.getElementById('promptTemplate');
const cancelBtn = document.getElementById('cancelBtn');
const saveBtn = document.getElementById('saveBtn');

// Load materials
async function loadMaterials() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/materials/manage');
        const data = await response.json();

        if (data.success && data.materials) {
            currentMaterials = data.materials;
            renderMaterialList();
        }
    } catch (error) {
        console.error('Failed to load materials:', error);
        materialList.innerHTML = '<p style="text-align: center; color: rgba(255,80,80,0.8);">Error loading materials</p>';
    }
}

// Render material list
function renderMaterialList() {
    if (Object.keys(currentMaterials).length === 0) {
        materialList.innerHTML = '<p style="text-align: center; color: rgba(255,255,255,0.5);">No materials configured. Click "Add Material" to get started.</p>';
        return;
    }

    materialList.innerHTML = '';

    Object.entries(currentMaterials).forEach(([name, config]) => {
        const item = document.createElement('div');
        item.className = 'material-item';

        item.innerHTML = `
            <div>
                <div class="material-name">${name}</div>
                <div class="material-desc">${config.description || ''}</div>
            </div>
            <div class="material-actions">
                <button class="btn btn-secondary btn-small" onclick="exportSingleMaterial('${name}')">📥 Export</button>
                <button class="btn btn-secondary btn-small" onclick="editMaterial('${name}')">Edit</button>
                <button class="btn btn-danger btn-small" onclick="deleteMaterial('${name}')">Delete</button>
            </div>
        `;

        materialList.appendChild(item);
    });
}

// Category management
function renderCategories() {
    const categoriesList = document.getElementById('categoriesList');
    if (currentCategories.length === 0) {
        categoriesList.innerHTML = '<p style="font-size: 11px; color: rgba(255,255,255,0.5);">No categories added yet</p>';
        return;
    }

    categoriesList.innerHTML = currentCategories.map((cat, idx) => `
        <div style="display: inline-flex; align-items: center; background: rgba(70,130,255,0.2); 
                    border: 1px solid rgba(70,130,255,0.4); border-radius: 6px; padding: 5px 10px; 
                    margin: 3px; font-size: 12px;">
            <span>${cat}</span>
            <button onclick="removeCategory(${idx})" 
                    style="background: none; border: none; color: rgba(255,100,100,0.8); 
                           cursor: pointer; margin-left: 8px; font-size: 14px; padding: 0;">×</button>
        </div>
    `).join('');
}

function addCategory() {
    const input = document.getElementById('newCategoryInput');
    const category = input.value.trim();

    if (!category) return;

    if (currentCategories.includes(category)) {
        toast.show('Category already exists', 'warning');
        return;
    }

    currentCategories.push(category);
    input.value = '';
    renderCategories();
}

function removeCategory(index) {
    currentCategories.splice(index, 1);
    renderCategories();
}

// Show add modal
function showAddModal() {
    editingMaterial = null;
    currentCategories = ["Material", "Grade", "Tradename", "Category"];
    modalTitle.textContent = 'Add New Material';
    materialName.value = '';
    materialName.disabled = false;
    materialDescription.value = '';
    materialPrompt.value = '';
    renderCategories();
    materialModal.classList.add('active');
}

// Edit material
function editMaterial(name) {
    editingMaterial = name;
    const config = currentMaterials[name];

    currentCategories = config.classification_categories || [];
    modalTitle.textContent = `Edit Material: ${name}`;
    materialName.value = name;
    materialName.disabled = true; // Can't change name when editing
    materialDescription.value = config.description || '';
    materialPrompt.value = config.prompt_template || '';
    renderCategories();

    materialModal.classList.add('active');
}

// Delete material
async function deleteMaterial(name) {
    if (!confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`http://127.0.0.1:5000/api/materials/manage/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            toast.show(`Material "${name}" deleted successfully!`, 'success');
            await loadMaterials();
            notifyMaterialsUpdated(); // Notify main page to refresh
        } else {
            toast.show(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        toast.show(`Failed to delete material: ${error.message}`, 'error');
    }
}

// Enhance prompt with AI
async function enhancePrompt() {
    const draftPrompt = materialPrompt.value.trim();
    if (!draftPrompt) {
        toast.show('Please enter a draft prompt first.', 'warning');
        return;
    }

    const enhanceBtn = document.getElementById('enhancePromptBtn');
    const originalText = enhanceBtn.innerHTML;

    // Set loading state
    enhanceBtn.disabled = true;
    enhanceBtn.innerHTML = '✨ Enhancing...';
    enhanceBtn.style.opacity = '0.7';

    try {
        const response = await fetch('http://127.0.0.1:5000/api/materials/enhance-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                draft_prompt: draftPrompt,
                categories: currentCategories,
                material_name: materialName.value.trim(),
                material_description: materialDescription.value.trim()
            })
        });

        const data = await response.json();

        if (data.success && data.enhanced_prompt) {
            materialPrompt.value = data.enhanced_prompt;
            toast.show('Prompt enhanced with material-specific context!', 'success');
        } else {
            console.error('Enhancement failed:', data);
            toast.show(`Error from server: ${data.error || 'Failed to enhance prompt'}`, 'error');
        }
    } catch (error) {
        console.error('Enhancement error:', error);
        toast.show(`Failed to connect to server: ${error.message}`, 'error');
    } finally {
        // Reset button
        enhanceBtn.disabled = false;
        enhanceBtn.innerHTML = originalText;
        enhanceBtn.style.opacity = '1';
    }
}

// Save material
async function saveMaterial() {
    const name = materialName.value.trim();
    const description = materialDescription.value.trim();
    const prompt = materialPrompt.value.trim();

    // Validation
    if (!name || !description || !prompt) {
        toast.show('Please fill in all required fields', 'warning');
        return;
    }

    if (currentCategories.length === 0) {
        toast.show('Please add at least one classification category', 'warning');
        return;
    }



    const materialConfig = {
        description: description,
        classification_categories: currentCategories,
        prompt_template: prompt,
        keywords: {
            positive: [],
            negative: []
        }
    };

    try {
        let response;

        if (editingMaterial) {
            // Update existing material
            response = await fetch(`http://127.0.0.1:5000/api/materials/manage/${encodeURIComponent(name)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(materialConfig)
            });
        } else {
            // Add new material
            response = await fetch('http://127.0.0.1:5000/api/materials/manage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    config: materialConfig
                })
            });
        }

        const data = await response.json();

        if (data.success) {
            toast.show(`Material "${name}" ${editingMaterial ? 'updated' : 'added'} successfully!`, 'success');
            materialModal.classList.remove('active');
            await loadMaterials();
            notifyMaterialsUpdated(); // Notify main page to refresh
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Save error:', error);
        toast.show(`Failed to save material: ${error.message}`, 'error');
    }
}

// Export all materials
async function exportMaterials() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/materials/export');
        const data = await response.json();

        if (data.materials) {
            // Create downloadable JSON file
            const blob = new Blob([JSON.stringify(data, null, 4)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `materials_database_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else {
            toast.show('Failed to export materials', 'error');
        }
    } catch (error) {
        console.error('Export error:', error);
        toast.show(`Failed to export materials: ${error.message}`, 'error');
    }
}

// Show import modal
function showImportModal() {
    const fileInput = document.getElementById('importFileInput');
    fileInput.click();
}

// Handle file selection
let selectedImportFile = null;

document.getElementById('importFileInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    selectedImportFile = file;

    // Show import options modal
    document.getElementById('importModal').classList.add('active');
});

// Confirm import
async function confirmImport() {
    if (!selectedImportFile) return;

    const mode = document.querySelector('input[name="importMode"]:checked').value;

    try {
        const fileContent = await selectedImportFile.text();
        const importData = JSON.parse(fileContent);

        // Validate structure
        if (!importData.materials) {
            toast.show('Invalid file format: missing "materials" key', 'error');
            return;
        }

        // Send to backend
        const response = await fetch('http://127.0.0.1:5000/api/materials/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                materials: importData.materials,
                mode: mode
            })
        });

        const data = await response.json();

        if (data.success) {
            toast.show(`${data.message}!`, 'success');
            document.getElementById('importModal').classList.remove('active');
            selectedImportFile = null;
            document.getElementById('importFileInput').value = '';
            await loadMaterials();
            notifyMaterialsUpdated(); // Notify main page to refresh
        } else {
            toast.show(`Import failed: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Import error:', error);
        toast.show(`Failed to import materials: ${error.message}`, 'error');
    }
}

// Export single material
function exportSingleMaterial(name) {
    const material = currentMaterials[name];
    if (!material) return;

    const exportData = {
        materials: {
            [name]: material
        }
    };

    const blob = new Blob([JSON.stringify(exportData, null, 4)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `material_${name.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Event Listeners
addMaterialBtn.addEventListener('click', showAddModal);
cancelBtn.addEventListener('click', () => materialModal.classList.remove('active'));
saveBtn.addEventListener('click', saveMaterial);

// Export/Import button listeners
document.getElementById('exportBtn').addEventListener('click', exportMaterials);
document.getElementById('importBtn').addEventListener('click', showImportModal);
document.getElementById('cancelImportBtn').addEventListener('click', () => {
    document.getElementById('importModal').classList.remove('active');
    selectedImportFile = null;
    document.getElementById('importFileInput').value = '';
});
document.getElementById('confirmImportBtn').addEventListener('click', confirmImport);

// Close modal on background click
materialModal.addEventListener('click', (e) => {
    if (e.target === materialModal) {
        materialModal.classList.remove('active');
    }
});

document.getElementById('importModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('importModal')) {
        document.getElementById('importModal').classList.remove('active');
        selectedImportFile = null;
        document.getElementById('importFileInput').value = '';
    }
});

// Initialize
window.addEventListener('DOMContentLoaded', loadMaterials);
