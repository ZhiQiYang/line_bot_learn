// Mapping for Font Awesome icons based on material type
const MATERIAL_TYPE_ICONS = {
    "文章": "fa-file-text",
    "視頻": "fa-video",
    "書籍": "fa-book",
    "練習": "fa-pencil-alt",
    "課程": "fa-graduation-cap",
    "筆記": "fa-sticky-note",
    "測驗": "fa-check-square",
    "項目": "fa-project-diagram",
    "其他": "fa-file",
    "未分類": "fa-question-circle"
};

// DOM Elements
let searchInput, searchButton, topicsGrid, materialsList, listTitle, materialsContainer;
let backToTopics, materialModal, modalTitle, modalTopicType, modalDescription, modalLinkContainer, modalLink;
let topicsLoading, materialsLoading, noMaterialsFound;

// Cache
let topicsCache = null;
let materialsCache = {}; // Cache materials by topic

document.addEventListener('DOMContentLoaded', function() {
    // Initialize LIFF first (assuming liff-init.js handles this)
    console.log("DOM loaded, initializing materials page...");
    // liff.init({ liffId: "YOUR_LIFF_ID" }).then(() => {
        initializeMaterialsPage();
    // }).catch((err) => {
    //     console.error('LIFF Initialization failed', err);
    // });
});

function initializeMaterialsPage() {
    console.log("Initializing page elements and listeners...");
    // Get DOM elements
    searchInput = document.getElementById('searchInput');
    searchButton = document.getElementById('searchButton');
    topicsGrid = document.getElementById('topicsGrid');
    materialsList = document.getElementById('materialsList');
    listTitle = document.getElementById('listTitle');
    materialsContainer = document.getElementById('materialsContainer');
    backToTopics = document.getElementById('backToTopics');
    materialModal = document.getElementById('materialModal');
    modalTitle = document.getElementById('modalTitle');
    modalTopicType = document.getElementById('modalTopicType');
    modalDescription = document.getElementById('modalDescription');
    modalLinkContainer = document.getElementById('modalLinkContainer');
    modalLink = document.getElementById('modalLink');
    topicsLoading = document.getElementById('topicsLoading');
    materialsLoading = document.getElementById('materialsLoading');
    noMaterialsFound = document.getElementById('noMaterialsFound');

    if (!searchInput || !searchButton || !topicsGrid || !materialsList) {
        console.error("One or more essential elements not found!");
        return;
    }

    // Add event listeners
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    backToTopics.addEventListener('click', (e) => {
        e.preventDefault();
        showTopicsView();
    });

    // Load initial data (topics)
    loadTopics();
}

// --- API Fetching Functions ---

async function fetchTopics() {
    if (topicsCache) return topicsCache; // Return from cache if available
    console.log("Fetching topics from API...");
    try {
        const response = await fetch('/api/materials/topics');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const topics = await response.json();
        topicsCache = topics; // Store in cache
        console.log("Topics fetched:", topics);
        return topics;
    } catch (error) {
        console.error("Error fetching topics:", error);
        showError(topicsGrid, "無法載入主題列表，請稍後再試。", topicsLoading);
        return null;
    }
}

async function fetchMaterialsByTopic(topic) {
    if (materialsCache[topic]) return materialsCache[topic]; // Return from cache
    console.log(`Fetching materials for topic: ${topic}...`);
    try {
        const response = await fetch(`/api/materials/topic/${encodeURIComponent(topic)}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const materials = await response.json();
        materialsCache[topic] = materials; // Store in cache
        console.log(`Materials for ${topic}:`, materials);
        return materials;
    } catch (error) {
        console.error(`Error fetching materials for topic ${topic}:`, error);
        showError(materialsContainer, "無法載入學習材料，請稍後再試。", materialsLoading);
        return null;
    }
}

async function searchMaterialsAPI(keyword) {
    console.log(`Searching materials for keyword: ${keyword}...`);
    try {
        const response = await fetch(`/api/materials/search/${encodeURIComponent(keyword)}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const results = await response.json();
        console.log("Search results:", results);
        return results;
    } catch (error) {
        console.error(`Error searching materials for keyword ${keyword}:`, error);
        showError(materialsContainer, "搜索失敗，請稍後再試。", materialsLoading);
        return null;
    }
}

// --- UI Update Functions ---

async function loadTopics() {
    showLoading(topicsLoading);
    topicsGrid.innerHTML = ''; // Clear previous content
    const topics = await fetchTopics();

    hideLoading(topicsLoading);
    if (topics && topics.length > 0) {
        // Fetch material counts for each topic (optional, can be slow)
        // We can simplify for now and just display topic names
        topics.forEach(topic => {
            const card = document.createElement('div');
            card.className = 'topic-card';
            card.innerHTML = `<div class="topic-title">${topic}</div>`; // Add count later if needed
            card.onclick = () => loadMaterialsForTopic(topic);
            topicsGrid.appendChild(card);
        });
        // Adjust grid layout if few topics
        if (topics.length <= 2) topicsGrid.classList.add('full-grid');

        // Add recommended card
        const recommendedCard = document.createElement('div');
        recommendedCard.className = 'topic-card recommended-card'; // Add a specific class if needed
        recommendedCard.innerHTML = `<div class="topic-title">🌟 推薦材料</div>`;
        recommendedCard.onclick = loadRecommendedMaterials;
        topicsGrid.appendChild(recommendedCard);

    } else if (topics) { // No topics but fetch was successful
        showNoData(topicsGrid, "目前沒有任何學習主題。");
    }
}

async function loadMaterialsForTopic(topic) {
    console.log(`Loading materials view for topic: ${topic}`);
    showLoading(materialsLoading);
    showMaterialsView();
    listTitle.textContent = topic; // Set title
    materialsContainer.innerHTML = ''; // Clear previous content
    hideNoData(noMaterialsFound);

    const materials = await fetchMaterialsByTopic(topic);
    hideLoading(materialsLoading);

    if (materials && materials.length > 0) {
        displayMaterials(materials);
    } else if (materials) {
        showNoData(noMaterialsFound);
    }
}

async function loadRecommendedMaterials() {
    console.log("Loading recommended materials...");
    showLoading(materialsLoading);
    showMaterialsView();
    listTitle.textContent = "推薦材料";
    materialsContainer.innerHTML = '';
    hideNoData(noMaterialsFound);

    try {
        const response = await fetch('/api/materials/recommended');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const materials = await response.json();
        hideLoading(materialsLoading);
        if (materials && materials.length > 0) {
            displayMaterials(materials);
        } else {
            showNoData(noMaterialsFound);
        }
    } catch (error) {
        console.error("Error fetching recommended materials:", error);
        showError(materialsContainer, "無法載入推薦材料，請稍後再試。", materialsLoading);
    }
}

async function performSearch() {
    const keyword = searchInput.value.trim();
    if (!keyword) return; // Don't search if empty

    console.log(`Performing search for: ${keyword}`);
    showLoading(materialsLoading);
    showMaterialsView();
    listTitle.textContent = `搜索結果: "${keyword}"`;
    materialsContainer.innerHTML = '';
    hideNoData(noMaterialsFound);

    const results = await searchMaterialsAPI(keyword);
    hideLoading(materialsLoading);

    if (results && results.length > 0) {
        displayMaterials(results);
    } else if (results) {
        showNoData(noMaterialsFound);
    }
}

function displayMaterials(materials) {
    materialsContainer.innerHTML = ''; // Clear first
    materials.forEach(material => {
        const card = document.createElement('div');
        card.className = 'material-card';

        const type = material.類型 || '未分類';
        const iconClass = MATERIAL_TYPE_ICONS[type] || MATERIAL_TYPE_ICONS['其他'];
        const title = material.標題 || '未命名';

        card.innerHTML = `
            <div class="material-icon"><i class="fas ${iconClass}"></i></div>
            <div class="material-info">
                <div class="material-title">${title}</div>
                <div class="material-type">${type}${material.主題 ? ' - ' + material.主題 : ''}</div>
            </div>
        `;
        // Add click listener to show details
        card.onclick = () => showMaterialDetails(material);
        materialsContainer.appendChild(card);
    });
}

// --- View Switching ---

function showTopicsView() {
    console.log("Switching to topics view");
    topicsGrid.style.display = 'grid';
    materialsList.style.display = 'none';
    searchInput.value = ''; // Clear search input when going back
}

function showMaterialsView() {
    console.log("Switching to materials list view");
    topicsGrid.style.display = 'none';
    materialsList.style.display = 'block';
    materialsList.classList.add('full-list'); // Adjust class if needed
}

// --- Modal Functions ---

function showMaterialDetails(material) {
    console.log("Showing details for:", material);
    modalTitle.textContent = material.標題 || 'N/A';
    modalTopicType.textContent = `${material.主題 || 'N/A'} - ${material.類型 || 'N/A'}`;
    modalDescription.textContent = material.描述 || '沒有提供描述。';

    if (material.連結 && material.連結.trim() !== '' && material.連結.trim().toLowerCase() !== 'nan') {
        modalLink.href = material.連結;
        modalLink.textContent = material.連結;
        modalLinkContainer.style.display = 'block';
    } else {
        modalLinkContainer.style.display = 'none';
    }

    materialModal.style.display = 'block';
}

function closeModal() {
    materialModal.style.display = 'none';
}

// Close modal if clicked outside of content
window.onclick = function(event) {
    if (event.target == materialModal) {
        closeModal();
    }
}

// --- Utility Functions ---
function showLoading(element) {
    if (element) element.style.display = 'block';
}

function hideLoading(element) {
    if (element) element.style.display = 'none';
}

function showNoData(container, message = "找不到相關學習材料。") {
    container.innerHTML = `
        <div class="no-data">
            <i class="fas fa-box-open"></i>
            <p>${message}</p>
        </div>`;
}

function hideNoData(element) {
     if (element) element.style.display = 'none';
}

function showError(container, message, loadingElement) {
    hideLoading(loadingElement);
    container.innerHTML = `
        <div class="error-container">
             <i class="fas fa-exclamation-triangle"></i>
             <p>${message}</p>
        </div>`;
}


console.log("materials.js loaded");