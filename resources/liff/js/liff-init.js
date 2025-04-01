// LIFF ID
const liffId = '2007183662-oq3j8zg8';
let userData = null;

// LIFF 初始化
document.addEventListener('DOMContentLoaded', function() {
  // 顯示載入中狀態
  const loading = document.getElementById('loading');
  const container = document.getElementById('container');

  // 初始化 LIFF
  liff.init({
    liffId: liffId,
    withLoginOnExternalBrowser: true
  })
  .then(() => {
    console.log('LIFF initialized!');
    
    // 檢查用戶是否登入
    if (liff.isLoggedIn()) {
      // 獲取用戶資料
      return liff.getProfile();
    } else {
      // 未登入時重定向到LINE登入頁面
      liff.login();
    }
  })
  .then(profile => {
    if (profile) {
      userData = profile;
      
      // 將用戶名稱顯示在頁面上
      const userNameElement = document.getElementById('userName');
      if (userNameElement) {
        userNameElement.textContent = profile.displayName;
      }
      
      // 根據 URL 參數決定顯示哪個功能
      handleUrlParams();
      
      // 顯示主要內容
      if (loading) loading.style.display = 'none';
      if (container) container.style.display = 'block';
    }
  })
  .catch(err => {
    console.error('LIFF initialization failed', err);
    alert('初始化失敗，請稍後再試');
  });
});

// 處理 URL 參數
function handleUrlParams() {
  // 獲取 URL 參數
  const urlParams = new URLSearchParams(window.location.search);
  const feature = urlParams.get('feature');
  
  // 根據參數顯示不同功能
  switch (feature) {
    case 'cards':
      loadCardsFeature();
      break;
    case 'report':
      loadReportFeature();
      break;
    default:
      // 默認顯示主頁
      loadDashboard();
  }
}

// 載入不同功能模塊
function loadDashboard() {
  console.log('Loading dashboard...');
  // 默認已載入
}

function loadCardsFeature() {
  console.log('Loading cards feature...');
  // 這裡可以動態載入卡片功能的 JS 和更新 UI
  document.querySelector('title').textContent = '記憶卡片 | 學習助手';
  document.querySelector('.header-title').textContent = '記憶卡片';
  
  // 將底部導航的卡片按鈕設為活躍
  document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
  document.querySelectorAll('.nav-item')[2].classList.add('active');
}

function loadReportFeature() {
  console.log('Loading report feature...');
  // 這裡可以動態載入報告功能的 JS 和更新 UI
  document.querySelector('title').textContent = '學習報告 | 學習助手';
  document.querySelector('.header-title').textContent = '學習報告';
  
  // 將底部導航的報告按鈕設為活躍
  document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
  document.querySelectorAll('.nav-item')[3].classList.add('active');
}

// 關閉 LIFF
function closeLiff() {
  liff.closeWindow();
} 