// 學習材料處理函數
document.addEventListener('DOMContentLoaded', function() {
  // 檢查當前頁面是否是學習材料頁
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('feature') === 'materials') {
    initMaterialsPage();
  }
});

// 初始化學習材料頁面
function initMaterialsPage() {
  // 更新頁面標題
  document.querySelector('.page-title').textContent = '學習材料';
  
  // 獲取內容容器
  const contentContainer = document.querySelector('.container');
  
  // 顯示加載中狀態
  contentContainer.innerHTML = `
    <div class="loading">
      <div class="loading-spinner"></div>
    </div>
  `;
  
  // 獲取材料數據
  fetchMaterials()
    .then(materials => {
      // 渲染材料頁面
      renderMaterialsPage(materials, contentContainer);
    })
    .catch(error => {
      console.error('獲取學習材料失敗:', error);
      contentContainer.innerHTML = `
        <div class="error-container">
          <i class="fas fa-exclamation-circle"></i>
          <p>無法加載學習材料，請稍後再試</p>
          <button onclick="initMaterialsPage()" class="action-button">重試</button>
        </div>
      `;
    });
  
  // 將底部導航的學習按鈕設為活躍
  document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
  document.querySelectorAll('.nav-item')[1].classList.add('active');
}

// 從API獲取材料數據
async function fetchMaterials() {
  try {
    const response = await fetch('/api/materials');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('獲取材料時出錯:', error);
    throw error;
  }
}

// 渲染材料頁面
function renderMaterialsPage(materials, container) {
  // 清空容器
  container.innerHTML = '';
  
  // 創建主題選擇區
  const topicsSection = document.createElement('div');
  topicsSection.className = 'progress-section';
  topicsSection.innerHTML = `
    <div class="section-title">
      <span>學習主題</span>
      <a href="#" class="see-all" id="showAllTopics">查看全部</a>
    </div>
    <div class="topics-grid"></div>
  `;
  container.appendChild(topicsSection);
  
  // 添加主題卡片
  const topicsGrid = topicsSection.querySelector('.topics-grid');
  const topics = Object.keys(materials);
  
  // 顯示前4個主題
  const displayTopics = topics.slice(0, 4);
  displayTopics.forEach(topic => {
    const topicCard = createTopicCard(topic, materials[topic].length);
    topicsGrid.appendChild(topicCard);
  });
  
  // 創建推薦材料區
  const recommendedSection = document.createElement('div');
  recommendedSection.className = 'progress-section';
  recommendedSection.innerHTML = `
    <div class="section-title">
      <span>推薦學習材料</span>
      <a href="#" class="see-all" id="showAllRecommended">更多</a>
    </div>
    <div class="materials-list"></div>
  `;
  container.appendChild(recommendedSection);
  
  // 獲取推薦材料
  const recommendedMaterials = [];
  topics.forEach(topic => {
    materials[topic].forEach(material => {
      if (material.推薦 === true || material.推薦 === 'TRUE' || material.推薦 === 1) {
        recommendedMaterials.push({ ...material, 主題: topic });
      }
    });
  });
  
  // 添加推薦材料卡片
  const materialsList = recommendedSection.querySelector('.materials-list');
  
  if (recommendedMaterials.length > 0) {
    // 顯示前3個推薦材料
    const displayRecommended = recommendedMaterials.slice(0, 3);
    displayRecommended.forEach(material => {
      const materialCard = createMaterialCard(material);
      materialsList.appendChild(materialCard);
    });
  } else {
    materialsList.innerHTML = '<p class="no-data">暫無推薦材料</p>';
  }
  
  // 最近學習區
  const recentSection = document.createElement('div');
  recentSection.className = 'progress-section';
  recentSection.innerHTML = `
    <div class="section-title">
      <span>最近學習</span>
      <a href="#" class="see-all">更多</a>
    </div>
    <div class="materials-list"></div>
  `;
  container.appendChild(recentSection);
  
  // 獲取最近材料（這裡模擬，實際應該從用戶數據獲取）
  // 隨機選擇一些材料作為"最近學習"，實際應用中應該是基於用戶歷史的
  const recentMaterials = [];
  let count = 0;
  
  // 從每個主題隨機選擇一個材料
  topics.forEach(topic => {
    if (count < 3 && materials[topic].length > 0) {
      const randomIndex = Math.floor(Math.random() * materials[topic].length);
      recentMaterials.push({ ...materials[topic][randomIndex], 主題: topic });
      count++;
    }
  });
  
  // 添加最近材料卡片
  const recentList = recentSection.querySelector('.materials-list');
  
  if (recentMaterials.length > 0) {
    recentMaterials.forEach(material => {
      const materialCard = createMaterialCard(material);
      recentList.appendChild(materialCard);
    });
  } else {
    recentList.innerHTML = '<p class="no-data">暫無最近學習記錄</p>';
  }
  
  // 添加搜索欄
  const searchBar = document.createElement('div');
  searchBar.className = 'search-bar';
  searchBar.innerHTML = `
    <input type="text" id="materialSearch" placeholder="搜尋學習材料...">
    <button id="searchButton"><i class="fas fa-search"></i></button>
  `;
  
  // 將搜索欄插入到頁面頂部
  container.insertBefore(searchBar, container.firstChild);
  
  // 綁定事件處理器
  searchBar.querySelector('#searchButton').addEventListener('click', function() {
    const keyword = searchBar.querySelector('#materialSearch').value.trim();
    if (keyword) {
      searchMaterials(keyword, materials, container);
    }
  });
  
  searchBar.querySelector('#materialSearch').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      const keyword = e.target.value.trim();
      if (keyword) {
        searchMaterials(keyword, materials, container);
      }
    }
  });
  
  // 綁定"查看全部主題"事件
  document.getElementById('showAllTopics').addEventListener('click', function(e) {
    e.preventDefault();
    showAllTopics(topics, materials, container);
  });
  
  // 綁定"更多推薦"事件
  document.getElementById('showAllRecommended').addEventListener('click', function(e) {
    e.preventDefault();
    showAllRecommended(recommendedMaterials, container);
  });
}

// 創建主題卡片
function createTopicCard(topic, count) {
  const card = document.createElement('div');
  card.className = 'topic-card';
  card.innerHTML = `
    <div class="topic-title">${topic}</div>
    <div class="topic-count">${count}個材料</div>
  `;
  
  card.addEventListener('click', function() {
    showTopicMaterials(topic);
  });
  
  return card;
}

// 創建材料卡片
function createMaterialCard(material) {
  const card = document.createElement('div');
  card.className = 'material-card';
  
  // 獲取材料圖標
  let iconClass = 'fa-file';
  switch(material.類型) {
    case '文章':
      iconClass = 'fa-file-alt';
      break;
    case '視頻':
      iconClass = 'fa-video';
      break;
    case '書籍':
      iconClass = 'fa-book';
      break;
    case '練習':
      iconClass = 'fa-tasks';
      break;
    case '課程':
      iconClass = 'fa-graduation-cap';
      break;
    case '筆記':
      iconClass = 'fa-sticky-note';
      break;
    case '測驗':
      iconClass = 'fa-check-square';
      break;
    case '項目':
      iconClass = 'fa-project-diagram';
      break;
  }
  
  card.innerHTML = `
    <div class="material-icon">
      <i class="fas ${iconClass}"></i>
    </div>
    <div class="material-info">
      <div class="material-title">${material.標題 || '未命名'}</div>
      <div class="material-type">${material.類型 || '未分類'} · ${material.主題 || '未分類'}</div>
    </div>
  `;
  
  card.addEventListener('click', function() {
    showMaterialDetail(material);
  });
  
  return card;
}

// 顯示主題下的所有材料
function showTopicMaterials(topic) {
  // 更新URL參數，不刷新頁面
  const url = new URL(window.location);
  url.searchParams.set('feature', 'materials');
  url.searchParams.set('topic', topic);
  window.history.pushState({}, '', url);
  
  // 獲取內容容器
  const contentContainer = document.querySelector('.container');
  
  // 顯示加載中狀態
  contentContainer.innerHTML = `
    <div class="loading">
      <div class="loading-spinner"></div>
    </div>
  `;
  
  // 獲取特定主題的材料
  fetch(`/api/materials/topic/${topic}`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(materials => {
      // 清空容器
      contentContainer.innerHTML = '';
      
      // 添加返回按鈕
      const backButton = document.createElement('div');
      backButton.className = 'back-link';
      backButton.innerHTML = `<i class="fas fa-arrow-left"></i> 返回全部主題`;
      backButton.addEventListener('click', function() {
        // 回到材料主頁
        const url = new URL(window.location);
        url.searchParams.delete('topic');
        window.history.pushState({}, '', url);
        
        initMaterialsPage();
      });
      contentContainer.appendChild(backButton);
      
      // 添加主題標題
      const topicTitle = document.createElement('h2');
      topicTitle.className = 'topic-header';
      topicTitle.textContent = topic;
      contentContainer.appendChild(topicTitle);
      
      // 材料列表
      const materialsList = document.createElement('div');
      materialsList.className = 'materials-list full-list';
      contentContainer.appendChild(materialsList);
      
      // 添加材料卡片
      if (materials.length > 0) {
        materials.forEach(material => {
          const materialCard = createMaterialCard({...material, 主題: topic});
          materialsList.appendChild(materialCard);
        });
      } else {
        materialsList.innerHTML = '<p class="no-data">此主題暫無材料</p>';
      }
      
      // 更新頁面標題
      document.querySelector('.page-title').textContent = `${topic} - 學習材料`;
    })
    .catch(error => {
      console.error('獲取主題材料失敗:', error);
      contentContainer.innerHTML = `
        <div class="error-container">
          <i class="fas fa-exclamation-circle"></i>
          <p>無法加載主題材料，請稍後再試</p>
          <button onclick="initMaterialsPage()" class="action-button">返回</button>
        </div>
      `;
    });
}

// 顯示材料詳情
function showMaterialDetail(material) {
  // 獲取內容容器
  const contentContainer = document.querySelector('.container');
  
  // 保存當前滾動位置
  const scrollPosition = window.scrollY;
  
  // 創建詳情內容
  contentContainer.innerHTML = `
    <div class="back-link" id="backToMaterials">
      <i class="fas fa-arrow-left"></i> 返回
    </div>
    <div class="content-card">
      <div class="content-title">${material.標題 || '未命名'}</div>
      <div class="content-info">
        <div class="info-item">
          <i class="fas fa-book"></i>
          <span>${material.類型 || '未分類'}</span>
        </div>
        <div class="info-item">
          <i class="fas fa-folder"></i>
          <span>${material.主題 || '未分類'}</span>
        </div>
      </div>
      <div class="content-text">
        ${material.描述 || '暫無描述'}
      </div>
      <div class="action-buttons">
        <button class="action-button">開始學習</button>
        <button class="action-button secondary">加入收藏</button>
      </div>
    </div>
  `;
  
  // 如果有相關信息，添加附加信息卡片
  if (material.難度 || material.預計時間 || material.作者) {
    const infoCard = document.createElement('div');
    infoCard.className = 'content-card';
    infoCard.innerHTML = `
      <h3>材料資訊</h3>
      <ul class="material-info-list">
        ${material.難度 ? `<li><strong>難度：</strong> ${material.難度}</li>` : ''}
        ${material.預計時間 ? `<li><strong>預計學習時間：</strong> ${material.預計時間}</li>` : ''}
        ${material.作者 ? `<li><strong>作者/來源：</strong> ${material.作者}</li>` : ''}
        ${material.發布日期 ? `<li><strong>發布日期：</strong> ${material.發布日期}</li>` : ''}
      </ul>
    `;
    contentContainer.appendChild(infoCard);
  }
  
  // 為返回按鈕添加事件處理器
  document.getElementById('backToMaterials').addEventListener('click', function() {
    // 檢查URL參數判斷返回到哪個頁面
    const urlParams = new URLSearchParams(window.location.search);
    const topic = urlParams.get('topic');
    
    if (topic) {
      showTopicMaterials(topic);
    } else {
      initMaterialsPage();
    }
    
    // 恢復滾動位置
    setTimeout(() => {
      window.scrollTo(0, scrollPosition);
    }, 100);
  });
  
  // 更新頁面標題
  document.querySelector('.page-title').textContent = material.標題 || '學習材料';
}

// 顯示所有主題
function showAllTopics(topics, materials, container) {
  // 清空容器
  container.innerHTML = '';
  
  // 添加返回按鈕
  const backButton = document.createElement('div');
  backButton.className = 'back-link';
  backButton.innerHTML = `<i class="fas fa-arrow-left"></i> 返回`;
  backButton.addEventListener('click', function() {
    initMaterialsPage();
  });
  container.appendChild(backButton);
  
  // 添加頁面標題
  const pageTitle = document.createElement('h2');
  pageTitle.className = 'page-header';
  pageTitle.textContent = '所有學習主題';
  container.appendChild(pageTitle);
  
  // 創建主題網格
  const topicsGrid = document.createElement('div');
  topicsGrid.className = 'topics-grid full-grid';
  container.appendChild(topicsGrid);
  
  // 添加所有主題卡片
  topics.forEach(topic => {
    const topicCard = createTopicCard(topic, materials[topic].length);
    topicsGrid.appendChild(topicCard);
  });
  
  // 更新頁面標題
  document.querySelector('.page-title').textContent = '全部學習主題';
}

// 顯示所有推薦材料
function showAllRecommended(recommendedMaterials, container) {
  // 清空容器
  container.innerHTML = '';
  
  // 添加返回按鈕
  const backButton = document.createElement('div');
  backButton.className = 'back-link';
  backButton.innerHTML = `<i class="fas fa-arrow-left"></i> 返回`;
  backButton.addEventListener('click', function() {
    initMaterialsPage();
  });
  container.appendChild(backButton);
  
  // 添加頁面標題
  const pageTitle = document.createElement('h2');
  pageTitle.className = 'page-header';
  pageTitle.textContent = '推薦學習材料';
  container.appendChild(pageTitle);
  
  // 創建材料列表
  const materialsList = document.createElement('div');
  materialsList.className = 'materials-list full-list';
  container.appendChild(materialsList);
  
  // 添加所有推薦材料卡片
  if (recommendedMaterials.length > 0) {
    recommendedMaterials.forEach(material => {
      const materialCard = createMaterialCard(material);
      materialsList.appendChild(materialCard);
    });
  } else {
    materialsList.innerHTML = '<p class="no-data">暫無推薦材料</p>';
  }
  
  // 更新頁面標題
  document.querySelector('.page-title').textContent = '推薦學習材料';
}

// 搜索材料
function searchMaterials(keyword, allMaterials, container) {
  // 清空容器
  container.innerHTML = '';
  
  // 添加搜索欄
  const searchBar = document.createElement('div');
  searchBar.className = 'search-bar';
  searchBar.innerHTML = `
    <input type="text" id="materialSearch" value="${keyword}" placeholder="搜尋學習材料...">
    <button id="searchButton"><i class="fas fa-search"></i></button>
  `;
  container.appendChild(searchBar);
  
  // 綁定搜索欄事件
  searchBar.querySelector('#searchButton').addEventListener('click', function() {
    const newKeyword = searchBar.querySelector('#materialSearch').value.trim();
    if (newKeyword) {
      searchMaterials(newKeyword, allMaterials, container);
    }
  });
  
  searchBar.querySelector('#materialSearch').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      const newKeyword = e.target.value.trim();
      if (newKeyword) {
        searchMaterials(newKeyword, allMaterials, container);
      }
    }
  });
  
  // 添加返回按鈕
  const backButton = document.createElement('div');
  backButton.className = 'back-link';
  backButton.innerHTML = `<i class="fas fa-arrow-left"></i> 返回`;
  backButton.addEventListener('click', function() {
    initMaterialsPage();
  });
  container.appendChild(backButton);
  
  // 添加搜索結果標題
  const searchTitle = document.createElement('h2');
  searchTitle.className = 'page-header';
  searchTitle.textContent = `「${keyword}」的搜索結果`;
  container.appendChild(searchTitle);
  
  // 準備搜索結果
  const results = [];
  
  // 搜索所有材料
  Object.keys(allMaterials).forEach(topic => {
    allMaterials[topic].forEach(material => {
      // 檢查標題、描述和主題是否包含關鍵詞
      const title = (material.標題 || '').toLowerCase();
      const description = (material.描述 || '').toLowerCase();
      const searchKeyword = keyword.toLowerCase();
      
      if (title.includes(searchKeyword) || 
          description.includes(searchKeyword) || 
          topic.toLowerCase().includes(searchKeyword)) {
        results.push({...material, 主題: topic});
      }
    });
  });
  
  // 創建結果列表
  const resultsList = document.createElement('div');
  resultsList.className = 'materials-list full-list';
  container.appendChild(resultsList);
  
  // 添加搜索結果
  if (results.length > 0) {
    results.forEach(material => {
      const materialCard = createMaterialCard(material);
      resultsList.appendChild(materialCard);
    });
  } else {
    resultsList.innerHTML = '<p class="no-data">沒有找到符合「' + keyword + '」的學習材料</p>';
  }
  
  // 更新頁面標題
  document.querySelector('.page-title').textContent = '搜索結果';
} 